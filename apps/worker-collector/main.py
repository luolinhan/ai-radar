"""
采集Worker - 负责从各种数据源采集信息
"""

import json
import os
import time
import logging
from pathlib import Path

from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from collectors.rss_collector import RSSCollector
from collectors.github_collector import GitHubCollector
from collectors.web_collector import WebCollector
from collectors.x_collector import XCollector
from collectors.common import slugify_entity_id

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 数据库配置
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    f"postgresql://{os.getenv('POSTGRES_USER', 'ai_radar')}:"
    f"{os.getenv('POSTGRES_PASSWORD', 'ai_radar_password')}@"
    f"{os.getenv('POSTGRES_HOST', 'postgres')}:"
    f"{os.getenv('POSTGRES_PORT', '5432')}/"
    f"{os.getenv('POSTGRES_DB', 'ai_radar')}"
)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


DEFAULT_SOURCE_TARGETS = {
    "rss_feeds": [
        {"url": "https://openai.com/blog/rss.xml", "entity_id": "openai"},
        {"url": "https://www.anthropic.com/news/rss", "entity_id": "anthropic"},
        {"url": "https://deepmind.google/blog/rss.xml", "entity_id": "google-deepmind"},
        {"url": "https://huggingface.co/blog/feed.xml", "entity_id": "huggingface"},
        {"url": "https://blogs.microsoft.com/ai/feed/", "entity_id": "microsoft-ai"},
        {"url": "https://blog.google/technology/ai/rss/", "entity_id": "google-ai"},
        {"url": "https://blogs.nvidia.com/feed/", "entity_id": "nvidia"},
        {"url": "https://aws.amazon.com/blogs/machine-learning/feed/", "entity_id": "aws-ai"},
        {"url": "https://sequoiacap.com/feed/", "entity_id": "sequoia"},
    ],
    "github_repos": [
        {"owner": "openai", "repo": "openai-python"},
        {"owner": "openai", "repo": "openai-node"},
        {"owner": "openai", "repo": "whisper"},
        {"owner": "anthropics", "repo": "anthropic-sdk-python"},
        {"owner": "anthropics", "repo": "anthropic-sdk-typescript"},
        {"owner": "google-gemini", "repo": "generative-ai-python"},
        {"owner": "google-gemini", "repo": "generative-ai-js"},
        {"owner": "huggingface", "repo": "transformers"},
        {"owner": "vllm-project", "repo": "vllm"},
        {"owner": "ollama", "repo": "ollama"},
        {"owner": "langchain-ai", "repo": "langchain"},
        {"owner": "mistralai", "repo": "mistral-inference"},
    ],
    "x_accounts": [],
    "web_pages": [],
}

DEFAULT_X_TARGET_PRIORITIES = {"P0", "P1"}
DEFAULT_WEB_TARGET_PRIORITIES = {"P0", "P1", "P2"}


def _read_json_file(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _parse_priority_filter(raw: str, default: set[str]) -> set[str]:
    if not raw:
        return default
    parsed = {item.strip().upper() for item in raw.split(",") if item.strip()}
    return parsed or default


def _merge_targets(base: list[dict], extra: list[dict], key_fields: tuple[str, ...]) -> list[dict]:
    seen = set()
    merged = []
    for item in base + extra:
        if not item:
            continue
        key = tuple((item.get(field) or "").strip().lower() for field in key_fields)
        if not any(key) or key in seen:
            continue
        seen.add(key)
        merged.append(item)
    return merged


def _derive_social_targets() -> tuple[list[dict], list[dict]]:
    entities_path = Path(os.getenv("WATCH_ENTITIES_PATH", "/app/configs/watchlists/entities.json"))
    if not entities_path.exists():
        return [], []

    try:
        entities = json.loads(entities_path.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.error("加载监控对象失败，跳过X/网页派生: %s", exc)
        return [], []

    x_priorities = _parse_priority_filter(os.getenv("X_TARGET_PRIORITIES", ""), DEFAULT_X_TARGET_PRIORITIES)
    web_priorities = _parse_priority_filter(os.getenv("WEB_TARGET_PRIORITIES", ""), DEFAULT_WEB_TARGET_PRIORITIES)

    x_targets = []
    web_targets = []
    for entity in entities:
        if entity.get("is_active", "true") != "true":
            continue

        priority = (entity.get("priority") or "P2").upper()
        name_en = entity.get("name_en") or ""
        entity_type = entity.get("entity_type") or "org"
        if not name_en:
            continue

        entity_id = slugify_entity_id(name_en)
        if entity.get("x_handle") and priority in x_priorities:
            x_targets.append(
                {
                    "handle": entity["x_handle"],
                    "entity_id": entity_id,
                    "entity_type": entity_type,
                    "name_en": name_en,
                    "priority": priority,
                    "organization": entity.get("organization", ""),
                }
            )

        website_url = (entity.get("website_url") or "").strip()
        if website_url and priority in web_priorities:
            web_targets.append(
                {
                    "url": website_url,
                    "entity_id": entity_id,
                    "entity_type": entity_type,
                    "name_en": name_en,
                    "priority": priority,
                    "organization": entity.get("organization", ""),
                }
            )

    return x_targets, web_targets


def load_source_targets() -> dict:
    """
    加载采集目标配置。
    优先读取 SOURCE_TARGETS_PATH（默认 /app/configs/watchlists/source_targets.json），
    读取失败时回退到内置默认配置。
    """
    cfg_path = Path(os.getenv("SOURCE_TARGETS_PATH", "/app/configs/watchlists/source_targets.json"))
    data = DEFAULT_SOURCE_TARGETS.copy()
    if cfg_path.exists():
        try:
            file_data = json.loads(cfg_path.read_text(encoding="utf-8"))
            if isinstance(file_data, dict):
                data.update({k: v for k, v in file_data.items() if isinstance(v, list)})
        except Exception as exc:
            logger.error("加载采集目标配置失败，使用默认配置: %s", exc)

    x_targets, web_targets = _derive_social_targets()
    rss_feeds = data.get("rss_feeds", [])
    github_repos = data.get("github_repos", [])
    manual_x_targets = data.get("x_accounts", [])
    manual_web_targets = data.get("web_pages", [])

    # 简单去重，避免重复配置导致重复请求
    seen_rss = set()
    uniq_rss = []
    for item in rss_feeds:
        url = (item or {}).get("url")
        if not url or url in seen_rss:
            continue
        seen_rss.add(url)
        uniq_rss.append(item)

    seen_repo = set()
    uniq_repos = []
    for item in github_repos:
        owner = (item or {}).get("owner")
        repo = (item or {}).get("repo")
        key = f"{owner}/{repo}"
        if not owner or not repo or key in seen_repo:
            continue
        seen_repo.add(key)
        uniq_repos.append(item)

    uniq_x = _merge_targets(manual_x_targets, x_targets, ("handle", "entity_id"))
    uniq_web = _merge_targets(manual_web_targets, web_targets, ("url", "entity_id"))

    if not uniq_rss and not uniq_repos and not uniq_x and not uniq_web:
        logger.warning(f"采集目标配置为空，使用内置默认配置: {cfg_path}")
        return DEFAULT_SOURCE_TARGETS

    return {
        "rss_feeds": uniq_rss,
        "github_repos": uniq_repos,
        "x_accounts": uniq_x,
        "web_pages": uniq_web,
    }


def collect_rss():
    """RSS采集任务"""
    logger.info("开始RSS采集...")
    db = SessionLocal()

    try:
        collector = RSSCollector(db)
        targets = load_source_targets()
        feeds = targets.get("rss_feeds", [])
        max_items = int(os.getenv("RSS_MAX_ITEMS_PER_FEED", "10"))

        for feed in feeds:
            url = feed.get("url")
            entity_id = feed.get("entity_id", "unknown")
            if not url:
                continue
            events = collector.collect(url, entity_id, max_entries=max_items)
            logger.info(f"从 {feed['url']} 采集到 {len(events)} 条事件")

    except Exception as e:
        logger.error(f"RSS采集失败: {e}")
    finally:
        db.close()


def collect_github():
    """GitHub采集任务"""
    logger.info("开始GitHub采集...")
    db = SessionLocal()

    try:
        github_token = os.getenv("GITHUB_TOKEN")
        if not github_token:
            logger.warning("未配置GitHub Token，跳过GitHub采集")
            return

        collector = GitHubCollector(github_token, db)
        targets = load_source_targets()
        repos = targets.get("github_repos", [])
        max_releases = int(os.getenv("GITHUB_MAX_RELEASES_PER_REPO", "5"))

        for repo in repos:
            owner = repo.get("owner")
            repo_name = repo.get("repo")
            if not owner or not repo_name:
                continue
            events = collector.collect_releases(owner, repo_name, max_releases=max_releases)
            logger.info(f"从 {repo['owner']}/{repo['repo']} 采集到 {len(events)} 条事件")

    except Exception as e:
        logger.error(f"GitHub采集失败: {e}")
    finally:
        db.close()


def collect_x():
    """X采集任务"""
    logger.info("开始X采集...")
    db = SessionLocal()

    try:
        targets = load_source_targets()
        accounts = targets.get("x_accounts", [])
        max_items = int(os.getenv("X_MAX_ITEMS_PER_ACCOUNT", "5"))
        collector = XCollector(db)

        for account in accounts:
            handle = account.get("handle")
            entity_id = account.get("entity_id", "unknown")
            entity_type = account.get("entity_type", "person")
            if not handle:
                continue
            events = collector.collect(handle, entity_id, entity_type=entity_type, max_items=max_items)
            logger.info("从 @%s 采集到 %s 条事件", handle, len(events))
    except Exception as e:
        logger.error(f"X采集失败: {e}")
    finally:
        db.close()


def collect_web():
    """网页采集任务"""
    logger.info("开始网页采集...")
    db = SessionLocal()

    try:
        targets = load_source_targets()
        pages = targets.get("web_pages", [])
        max_items = int(os.getenv("WEB_MAX_ITEMS_PER_SITE", "3"))
        collector = WebCollector(db)

        for page in pages:
            url = page.get("url")
            entity_id = page.get("entity_id", "unknown")
            entity_type = page.get("entity_type", "org")
            if not url:
                continue
            events = collector.collect(url, entity_id, entity_type=entity_type, max_entries=max_items)
            logger.info("从网页 %s 采集到 %s 条事件", url, len(events))
    except Exception as e:
        logger.error(f"网页采集失败: {e}")
    finally:
        db.close()


def main():
    """主函数"""
    logger.info("采集Worker启动")

    # 等待数据库就绪
    time.sleep(5)

    scheduler = BackgroundScheduler()
    rss_interval_minutes = int(os.getenv("RSS_COLLECT_INTERVAL_MINUTES", "120"))
    github_interval_minutes = int(os.getenv("GITHUB_COLLECT_INTERVAL_MINUTES", "180"))
    x_interval_minutes = int(os.getenv("X_COLLECT_INTERVAL_MINUTES", "120"))
    web_interval_minutes = int(os.getenv("WEB_COLLECT_INTERVAL_MINUTES", "240"))

    # RSS定时采集
    scheduler.add_job(collect_rss, 'interval', minutes=rss_interval_minutes)

    # GitHub定时采集
    scheduler.add_job(collect_github, 'interval', minutes=github_interval_minutes)

    # X定时采集
    scheduler.add_job(collect_x, 'interval', minutes=x_interval_minutes)

    # 网页定时采集
    scheduler.add_job(collect_web, 'interval', minutes=web_interval_minutes)

    scheduler.start()

    logger.info(
        f"调度器已启动: RSS={rss_interval_minutes}min, GitHub={github_interval_minutes}min, "
        f"X={x_interval_minutes}min, Web={web_interval_minutes}min"
    )

    # 保持运行
    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        scheduler.shutdown()


if __name__ == "__main__":
    main()
