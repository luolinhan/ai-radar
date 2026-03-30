"""
采集Worker - 负责从各种数据源采集信息
"""

import os
import time
import logging
from datetime import datetime

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


def collect_rss():
    """RSS采集任务"""
    logger.info("开始RSS采集...")
    db = SessionLocal()

    try:
        collector = RSSCollector(db)
        # 读取配置的RSS源
        feeds = [
            {"url": "https://openai.com/blog/rss.xml", "entity_id": "openai"},
            {"url": "https://www.anthropic.com/news/rss", "entity_id": "anthropic"},
            {"url": "https://deepmind.google/blog/rss.xml", "entity_id": "google-deepmind"},
        ]

        for feed in feeds:
            events = collector.collect(feed["url"], feed["entity_id"])
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

        # 监控的组织和仓库
        repos = [
            {"owner": "openai", "repo": "whisper"},
            {"owner": "anthropics", "repo": "anthropic-sdk-python"},
            {"owner": "google-deepmind", "repo": "alphafold"},
        ]

        for repo in repos:
            events = collector.collect_releases(repo["owner"], repo["repo"])
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

    # RSS每30分钟采集一次
    scheduler.add_job(collect_rss, 'interval', minutes=30)

    # GitHub每1小时采集一次
    scheduler.add_job(collect_github, 'interval', hours=1)

    scheduler.start()

    logger.info("调度器已启动")

    # 保持运行
    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        scheduler.shutdown()


if __name__ == "__main__":
    main()