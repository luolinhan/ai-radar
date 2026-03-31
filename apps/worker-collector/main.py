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
}


def load_source_targets() -> dict:
    """
    加载采集目标配置。
    优先读取 SOURCE_TARGETS_PATH（默认 /app/configs/watchlists/source_targets.json），
    读取失败时回退到内置默认配置。
    """
    cfg_path = Path(os.getenv("SOURCE_TARGETS_PATH", "/app/configs/watchlists/source_targets.json"))
    if not cfg_path.exists():
        return DEFAULT_SOURCE_TARGETS

    try:
        data = json.loads(cfg_path.read_text(encoding="utf-8"))
        rss_feeds = data.get("rss_feeds", [])
        github_repos = data.get("github_repos", [])

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

        if not uniq_rss and not uniq_repos:
            logger.warning(f"采集目标配置为空，使用内置默认配置: {cfg_path}")
            return DEFAULT_SOURCE_TARGETS

        return {"rss_feeds": uniq_rss, "github_repos": uniq_repos}
    except Exception as e:
        logger.error(f"加载采集目标配置失败，使用默认配置: {e}")
        return DEFAULT_SOURCE_TARGETS


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


def main():
    """主函数"""
    logger.info("采集Worker启动")

    # 等待数据库就绪
    time.sleep(5)

    scheduler = BackgroundScheduler()
    rss_interval_minutes = int(os.getenv("RSS_COLLECT_INTERVAL_MINUTES", "120"))
    github_interval_minutes = int(os.getenv("GITHUB_COLLECT_INTERVAL_MINUTES", "180"))

    # RSS定时采集
    scheduler.add_job(collect_rss, 'interval', minutes=rss_interval_minutes)

    # GitHub定时采集
    scheduler.add_job(collect_github, 'interval', minutes=github_interval_minutes)

    scheduler.start()

    logger.info(
        f"调度器已启动: RSS={rss_interval_minutes}min, GitHub={github_interval_minutes}min"
    )

    # 保持运行
    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        scheduler.shutdown()


if __name__ == "__main__":
    main()
