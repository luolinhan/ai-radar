"""
RSS采集器 - 从RSS/Atom feeds采集内容
"""

import logging
import uuid
from datetime import datetime

import feedparser
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class RSSCollector:
    """RSS采集器"""

    def __init__(self, db: Session):
        self.db = db

    def collect(self, feed_url: str, entity_id: str, max_entries: int = 20) -> list:
        """
        从RSS feed采集内容

        Args:
            feed_url: RSS feed URL
            entity_id: 关联的实体ID

        Returns:
            采集到的事件列表
        """
        events = []

        try:
            logger.info(f"解析RSS: {feed_url}")
            feed = feedparser.parse(feed_url)

            if feed.bozo:
                logger.warning(f"RSS解析警告: {feed.bozo_exception}")

            for entry in feed.entries[:max_entries]:
                event = self._parse_entry(entry, entity_id, feed_url)
                if event:
                    events.append(event)

        except Exception as e:
            logger.error(f"RSS采集失败: {feed_url}, 错误: {e}")

        return events

    def _parse_entry(self, entry: dict, entity_id: str, feed_url: str) -> dict:
        """解析单个RSS entry"""
        try:
            # 提取内容
            title = entry.get("title", "")
            content = entry.get("summary", entry.get("content", entry.get("description", "")))

            if isinstance(content, list):
                content = content[0].get("value", "") if content else ""

            # 提取链接
            url = entry.get("link", "")
            if not url:
                logger.warning("RSS entry缺少link，跳过")
                return None

            # 提取发布时间
            published_at = datetime.utcnow()
            published_at_inferred = True
            if hasattr(entry, "published_parsed") and entry.published_parsed:
                published_at = datetime(*entry.published_parsed[:6])
                published_at_inferred = False
            elif hasattr(entry, "updated_parsed") and entry.updated_parsed:
                published_at = datetime(*entry.updated_parsed[:6])
                published_at_inferred = False

            # 提取作者
            author = entry.get("author", "")

            # 创建事件数据
            event_id = str(uuid.uuid4())

            # 保存到数据库
            from models import Event

            # 按来源+URL做幂等，避免同一RSS反复入库
            existing = self.db.query(Event.event_id).filter(
                Event.source == "rss",
                Event.url == url,
            ).first()
            if existing:
                logger.debug(f"RSS重复事件，已跳过: {url}")
                return None

            db_event = Event(
                event_id=event_id,
                source="rss",
                source_type="rss",
                entity_type="org",
                entity_id=entity_id,
                author=author,
                title=title,
                content_raw=content,
                url=url,
                published_at=published_at,
                fetched_at=datetime.utcnow(),
                language="en",
                signals={"published_at_inferred": published_at_inferred},
            )

            self.db.add(db_event)
            self.db.commit()

            return {
                "event_id": event_id,
                "title": title,
                "url": url,
                "published_at": published_at.isoformat(),
            }

        except Exception as e:
            self.db.rollback()
            logger.error(f"解析RSS entry失败: {e}")
            return None
