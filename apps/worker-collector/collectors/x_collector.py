"""
X/Twitter采集器 - 从公开X账户采集最近帖子。
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from .common import clean_text

logger = logging.getLogger(__name__)

try:
    import snscrape.modules.twitter as sntwitter
except Exception:  # pragma: no cover - optional dependency
    sntwitter = None


class XCollector:
    """X采集器。"""

    def __init__(self, db: Session):
        self.db = db

    def collect(self, handle: str, entity_id: str, entity_type: str = "person", max_items: int = 10) -> list:
        """
        从X账户采集帖子。
        """
        handle = (handle or "").strip().lstrip("@").lower()
        if not handle:
            return []

        if sntwitter is None:
            logger.warning("snscrape未安装，跳过X采集: %s", handle)
            return []

        events = []
        try:
            scraper = sntwitter.TwitterUserScraper(handle)
            for tweet in scraper.get_items():
                if len(events) >= max_items:
                    break

                # 过滤转推和回复，优先保留原创内容
                if getattr(tweet, "retweetedTweet", None) is not None:
                    continue
                if getattr(tweet, "inReplyToTweetId", None):
                    continue

                event = self._parse_tweet(tweet, handle, entity_id, entity_type)
                if event:
                    events.append(event)
        except Exception as exc:
            logger.error("X采集失败: @%s, 错误: %s", handle, exc)

        return events

    def _parse_tweet(self, tweet, handle: str, entity_id: str, entity_type: str) -> Optional[dict]:
        try:
            url = getattr(tweet, "url", "") or ""
            if not url:
                tweet_id = getattr(tweet, "id", None)
                if tweet_id:
                    url = f"https://x.com/{handle}/status/{tweet_id}"
            if not url:
                return None

            content = (
                getattr(tweet, "rawContent", None)
                or getattr(tweet, "content", None)
                or getattr(tweet, "renderedContent", None)
                or ""
            )
            content = clean_text(content, max_length=2500)
            if len(content) < 20:
                return None

            title = clean_text(content.split("\n", 1)[0], max_length=140)
            published_at = getattr(tweet, "date", None) or datetime.utcnow()
            user = getattr(tweet, "user", None)
            author = (
                getattr(user, "displayname", None)
                or getattr(user, "username", None)
                or handle
            )

            from models import Event

            existing = self.db.query(Event.event_id).filter(
                Event.source == "x",
                Event.url == url,
            ).first()
            if existing:
                logger.debug("X重复事件，已跳过: %s", url)
                return None

            event_id = str(uuid.uuid4())
            db_event = Event(
                event_id=event_id,
                source="x",
                source_type="social",
                entity_type=entity_type,
                entity_id=entity_id,
                author=author,
                title=title,
                content_raw=content,
                url=url,
                published_at=published_at,
                fetched_at=datetime.utcnow(),
                language="en",
            )

            self.db.add(db_event)
            self.db.commit()

            return {
                "event_id": event_id,
                "title": title,
                "url": url,
                "published_at": published_at.isoformat(),
            }
        except Exception as exc:
            self.db.rollback()
            logger.error("解析X帖失败: %s", exc)
            return None
