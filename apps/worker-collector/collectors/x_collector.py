"""
X/Twitter采集器 - 从公开X账户采集最近帖子。
"""

from __future__ import annotations

import os
import logging
import uuid
from datetime import datetime
from typing import Optional

import feedparser
import httpx
from sqlalchemy.orm import Session

from .common import clean_text

logger = logging.getLogger(__name__)

try:
    import snscrape.modules.twitter as sntwitter
except Exception:  # pragma: no cover - optional dependency
    sntwitter = None


PRIMARY_RSSHUB = os.getenv("RSSHUB_URL", "https://rsshub.rssforever.com")
BACKUP_RSSHUB_INSTANCES = [
    item.strip()
    for item in os.getenv(
        "RSSHUB_BACKUP_URLS",
        "https://rsshub.pseudoyu.com,https://rsshub.app,https://rsshub.litecy.com",
    ).split(",")
    if item.strip()
]


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

        events = self._collect_from_rsshub(handle, entity_id, entity_type, max_items)
        if events:
            return events

        if sntwitter is None:
            logger.warning("snscrape未安装，且RSSHub不可用，跳过X采集: %s", handle)
            return []

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

    def _collect_from_rsshub(self, handle: str, entity_id: str, entity_type: str, max_items: int) -> list:
        events = []
        instances = [PRIMARY_RSSHUB, *BACKUP_RSSHUB_INSTANCES]

        for rsshub_url in instances:
            feed_url = f"{rsshub_url.rstrip('/')}/twitter/user/{handle}"
            try:
                xml = self._fetch_rsshub_feed(feed_url)
                if not xml:
                    continue

                feed = feedparser.parse(xml)
                if feed.bozo:
                    logger.warning("RSSHub解析警告: %s", getattr(feed, "bozo_exception", "unknown"))

                for entry in feed.entries[:max_items]:
                    event = self._parse_rsshub_entry(entry, handle, entity_id, entity_type)
                    if event:
                        events.append(event)

                if events:
                    logger.info("RSSHub采集成功: @%s, %s 条, 来源=%s", handle, len(events), rsshub_url)
                    return events
            except Exception as exc:
                logger.warning("RSSHub采集失败: @%s, 来源=%s, 错误=%s", handle, rsshub_url, exc)
                continue

        return events

    def _fetch_rsshub_feed(self, feed_url: str) -> str:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0 Safari/537.36"
            ),
            "Accept": "application/rss+xml, application/xml;q=0.9, */*;q=0.8",
        }
        with httpx.Client(timeout=20, follow_redirects=True, headers=headers) as client:
            response = client.get(feed_url)
            response.raise_for_status()
            return response.text

    def _parse_rsshub_entry(self, entry, handle: str, entity_id: str, entity_type: str) -> Optional[dict]:
        try:
            url = entry.get("link", "") or entry.get("id", "") or ""
            if not url:
                return None

            title = clean_text(entry.get("title", "") or entry.get("summary", ""), max_length=140)
            content = entry.get("summary", "") or entry.get("description", "") or entry.get("title", "")
            content = clean_text(content, max_length=2500)
            if len(content) < 20:
                return None

            published = getattr(entry, "published_parsed", None) or getattr(entry, "updated_parsed", None)
            if published:
                published_at = datetime(*published[:6])
                published_at_inferred = False
            else:
                published_at = datetime.utcnow()
                published_at_inferred = True

            author = clean_text(entry.get("author", "") or handle, max_length=80)

            from models import Event

            existing = self.db.query(Event.event_id).filter(
                Event.source == "x",
                Event.url == url,
            ).first()
            if existing:
                logger.debug("X/RSSHub重复事件，已跳过: %s", url)
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
        except Exception as exc:
            self.db.rollback()
            logger.error("解析X/RSSHub条目失败: %s", exc)
            return None

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
            tweet_date = getattr(tweet, "date", None)
            published_at = tweet_date or datetime.utcnow()
            published_at_inferred = tweet_date is None
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
        except Exception as exc:
            self.db.rollback()
            logger.error("解析X帖失败: %s", exc)
            return None
