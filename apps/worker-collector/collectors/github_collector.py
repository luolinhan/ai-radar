"""
GitHub采集器 - 从GitHub采集repo/release更新
"""

import logging
import uuid
from datetime import datetime

from github import Github
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class GitHubCollector:
    """GitHub采集器"""

    def __init__(self, token: str, db: Session):
        self.github = Github(token)
        self.db = db

    def collect_releases(self, owner: str, repo: str) -> list:
        """
        采集仓库的release

        Args:
            owner: 仓库owner
            repo: 仓库名

        Returns:
            采集到的事件列表
        """
        events = []

        try:
            logger.info(f"获取GitHub release: {owner}/{repo}")
            repository = self.github.get_repo(f"{owner}/{repo}")

            releases = repository.get_releases()

            for release in releases[:10]:  # 只取最近10个release
                event = self._parse_release(release, owner, repo)
                if event:
                    events.append(event)

        except Exception as e:
            logger.error(f"GitHub采集失败: {owner}/{repo}, 错误: {e}")

        return events

    def _parse_release(self, release, owner: str, repo: str) -> dict:
        """解析单个release"""
        try:
            event_id = str(uuid.uuid4())

            title = f"{owner}/{repo}: Release {release.tag_name}"
            content = release.body or f"新版本发布: {release.tag_name}"

            # 保存到数据库
            from models import Event
            db_event = Event(
                event_id=event_id,
                source="github",
                source_type="official_api",
                entity_type="org",
                entity_id=owner,
                author=release.author.login if release.author else owner,
                title=title,
                content_raw=content,
                url=release.html_url,
                published_at=release.published_at or datetime.utcnow(),
                fetched_at=datetime.utcnow(),
                language="en",
            )

            self.db.add(db_event)
            self.db.commit()

            return {
                "event_id": event_id,
                "title": title,
                "url": release.html_url,
                "tag_name": release.tag_name,
            }

        except Exception as e:
            logger.error(f"解析GitHub release失败: {e}")
            return None