"""
网页采集器 - 从网页/主页/博客页抓取内容，并自动发现RSS。
"""

from __future__ import annotations

import hashlib
import logging
import re
import uuid
from datetime import datetime
from html import unescape
from typing import Optional
from urllib.parse import urljoin

import httpx
from sqlalchemy.orm import Session

from .common import clean_text
from .rss_collector import RSSCollector

logger = logging.getLogger(__name__)


class WebCollector:
    """网页采集器。"""

    FEED_RE = re.compile(
        r'<link[^>]+rel=["\'](?:alternate|feed|rss)["\'][^>]+type=["\']application/(?:rss\+xml|atom\+xml)["\'][^>]+href=["\']([^"\']+)["\']',
        re.IGNORECASE,
    )

    META_TITLE_RE = re.compile(
        r'<meta[^>]+property=["\']og:title["\'][^>]+content=["\']([^"\']+)["\']',
        re.IGNORECASE,
    )
    META_DESC_RE = re.compile(
        r'<meta[^>]+(?:property|name)=["\'](?:og:description|twitter:description|description)["\'][^>]+content=["\']([^"\']+)["\']',
        re.IGNORECASE,
    )
    META_AUTHOR_RE = re.compile(
        r'<meta[^>]+(?:name|property)=["\']author["\'][^>]+content=["\']([^"\']+)["\']',
        re.IGNORECASE,
    )
    META_PUBLISHED_RE = re.compile(
        r'<meta[^>]+(?:property|name)=["\'](?:article:published_time|pubdate|date|publish_date)["\'][^>]+content=["\']([^"\']+)["\']',
        re.IGNORECASE,
    )
    HTML_LANG_RE = re.compile(r'<html[^>]+lang=["\']([^"\']+)["\']', re.IGNORECASE)
    TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)
    TAG_BLOCK_RE = re.compile(
        r"</?(?:script|style|noscript|svg|header|footer|nav|aside|iframe)[^>]*>",
        re.IGNORECASE,
    )
    PARAGRAPH_RE = re.compile(r"<p[^>]*>(.*?)</p>", re.IGNORECASE | re.DOTALL)

    def __init__(self, db: Session):
        self.db = db
        self.rss_collector = RSSCollector(db)

    def collect(
        self,
        page_url: str,
        entity_id: str,
        entity_type: str = "org",
        max_entries: int = 3,
    ) -> list:
        """
        采集网页内容；如果发现RSS/Atom feed，优先走feed。
        """
        if not page_url:
            return []

        try:
            html = self._fetch(page_url)
            if not html:
                return []

            feed_url = self._discover_feed_url(page_url, html)
            if feed_url:
                logger.info("网页发现RSS: %s -> %s", page_url, feed_url)
                events = self.rss_collector.collect(feed_url, entity_id, max_entries=max_entries)
                if events:
                    return events

            return [event for event in [self._parse_page(page_url, entity_id, entity_type, html)] if event]
        except Exception as exc:
            logger.error("网页采集失败: %s, 错误: %s", page_url, exc)
            return []

    def _fetch(self, page_url: str) -> str:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0 Safari/537.36"
            )
        }
        with httpx.Client(timeout=20, follow_redirects=True, headers=headers) as client:
            response = client.get(page_url)
            response.raise_for_status()
            return response.text

    def _discover_feed_url(self, page_url: str, html: str) -> Optional[str]:
        match = self.FEED_RE.search(html)
        if not match:
            return None
        href = match.group(1).strip()
        return urljoin(page_url, href)

    def _parse_page(self, page_url: str, entity_id: str, entity_type: str, html: str) -> Optional[dict]:
        from models import Event

        title = self._extract_title(html, page_url)
        description = self._extract_description(html)
        author = self._extract_author(html)
        published_at = self._extract_published_at(html)
        lang = self._extract_lang(html)

        body_text = self._extract_body_text(html)
        content_parts = [part for part in [title, description, body_text] if part]
        content_raw = clean_text("\n\n".join(content_parts), max_length=4000)
        if len(content_raw) < 40:
            return None

        content_hash = hashlib.sha1(content_raw.encode("utf-8")).hexdigest()
        existing = (
            self.db.query(Event.content_raw, Event.signals)
            .filter(Event.source == "web", Event.url == page_url)
            .order_by(Event.fetched_at.desc())
            .first()
        )
        if existing and existing[1] and existing[1].get("content_hash") == content_hash:
            logger.debug("网页重复内容，已跳过: %s", page_url)
            return None

        event_id = str(uuid.uuid4())
        db_event = Event(
            event_id=event_id,
            source="web",
            source_type="webpage",
            entity_type=entity_type,
            entity_id=entity_id,
            author=author,
            title=title,
            content_raw=content_raw,
            url=page_url,
            published_at=published_at,
            fetched_at=datetime.utcnow(),
            language=lang,
            signals={"content_hash": content_hash},
        )

        self.db.add(db_event)
        self.db.commit()

        return {
            "event_id": event_id,
            "title": title,
            "url": page_url,
            "published_at": published_at.isoformat(),
        }

    def _extract_title(self, html: str, fallback_url: str) -> str:
        for pattern in [self.META_TITLE_RE, self.TITLE_RE]:
            match = pattern.search(html)
            if match:
                return clean_text(match.group(1), max_length=180)
        return clean_text(fallback_url, max_length=180)

    def _extract_description(self, html: str) -> str:
        match = self.META_DESC_RE.search(html)
        if match:
            return clean_text(match.group(1), max_length=500)
        return ""

    def _extract_author(self, html: str) -> str:
        match = self.META_AUTHOR_RE.search(html)
        return clean_text(match.group(1), max_length=80) if match else ""

    def _extract_published_at(self, html: str) -> datetime:
        match = self.META_PUBLISHED_RE.search(html)
        if match:
            value = clean_text(match.group(1))
            try:
                return datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=None)
            except Exception:
                pass
        return datetime.utcnow()

    def _extract_lang(self, html: str) -> str:
        match = self.HTML_LANG_RE.search(html)
        if match:
            return clean_text(match.group(1), max_length=16) or "en"
        return "en"

    def _extract_body_text(self, html: str) -> str:
        body = re.sub(r"<(?:script|style|noscript|svg|header|footer|nav|aside|iframe)[^>]*>.*?</(?:script|style|noscript|svg|header|footer|nav|aside|iframe)>", " ", html, flags=re.IGNORECASE | re.DOTALL)
        paragraphs = self.PARAGRAPH_RE.findall(body)
        if paragraphs:
            text = "\n".join(clean_text(re.sub(r"<[^>]+>", " ", p)) for p in paragraphs[:8])
            text = clean_text(text, max_length=2500)
            if text:
                return text

        stripped = re.sub(r"<[^>]+>", " ", body)
        stripped = clean_text(stripped, max_length=2500)
        return stripped

