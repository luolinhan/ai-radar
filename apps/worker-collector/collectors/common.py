"""
采集器公共工具。
"""

from __future__ import annotations

import re
import unicodedata
from html import unescape


def slugify_entity_id(value: str) -> str:
    """把名称转换成稳定的事件实体ID。"""
    if not value:
        return "unknown"

    normalized = unicodedata.normalize("NFKD", value)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    candidate = ascii_text or value
    candidate = re.sub(r"[^0-9a-zA-Z]+", "-", candidate.lower()).strip("-")
    return candidate or "unknown"


def clean_text(value: str, max_length: int | None = None) -> str:
    """压缩空白并截断文本。"""
    text = unescape(value or "")
    text = re.sub(r"\s+", " ", text).strip()
    if max_length and len(text) > max_length:
        return text[: max_length - 3].rstrip() + "..."
    return text

