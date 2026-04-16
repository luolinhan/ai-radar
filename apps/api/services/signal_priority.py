"""
高信号事件优先级规则。
"""

from __future__ import annotations

from datetime import datetime
from typing import Iterable


HIGH_SIGNAL_TOPICS = {
    "frontier-models",
    "open-source-models",
    "ai-infra",
    "gpu-compute",
    "ai-applications",
    "chip-supply-chain",
}

METHODOLOGY_TOPICS = {
    "ai-applications",
    "frontier-models",
    "ai-infra",
    "open-source-models",
}

HIGH_SIGNAL_ENTITIES = {
    "openai",
    "anthropic",
    "google-deepmind",
    "google-ai",
    "meta-ai",
    "meta-llama",
    "nvidia",
    "xai",
    "moonshot-ai",
    "deepseek",
    "zhipu-ai",
    "qwen",
    "mistral",
    "huggingface",
}

METHODOLOGY_ENTITIES = {
    "andrej-karpathy",
    "dan-koe",
    "simon-willison",
    "shawn-wang",
    "latent-space",
    "andrew-ng",
}

HIGH_SIGNAL_KEYWORDS = {
    "launch",
    "launched",
    "release",
    "released",
    "introduces",
    "introduced",
    "announce",
    "announced",
    "reasoning",
    "agent",
    "agentic",
    "workflow",
    "benchmark",
    "sota",
    "open model",
    "open-source",
    "open source",
    "weights",
    "multimodal",
    "byte for byte",
    "inference",
    "coding",
    "prompt",
    "prompting",
    "playbook",
    "guide",
    "tutorial",
    "use case",
    "vibe coding",
    "claude code",
    "system prompt",
    "eval",
    "模型",
    "发布",
    "开源",
    "推理",
    "智能体",
    "工作流",
    "基准",
    "提示词",
    "教程",
    "案例",
    "技巧",
}

METHODOLOGY_KEYWORDS = {
    "prompt",
    "prompting",
    "guide",
    "tutorial",
    "playbook",
    "workflow",
    "agent workflow",
    "use case",
    "use cases",
    "system prompt",
    "eval",
    "benchmark",
    "coding",
    "claude code",
    "vibe coding",
    "automation",
    "llm",
    "how to",
    "技巧",
    "提示词",
    "教程",
    "工作流",
    "案例",
    "自动化",
}

METHODOLOGY_STRONG_KEYWORDS = {
    "system prompt",
    "claude code",
    "vibe coding",
    "playbook",
    "tutorial",
    "guide",
    "how to",
    "eval",
    "提示词",
    "教程",
    "工作流",
}

LOW_SIGNAL_PATTERNS = {
    "text from @",
    "<img",
    "just now",
    "rsshub-quote",
    "repost:",
}


def normalize_topics(value) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        items = value
    else:
        items = [value]

    topics: list[str] = []
    seen = set()
    for item in items:
        text = str(item or "").strip()
        if not text:
            continue
        key = text.lower()
        if key in seen:
            continue
        seen.add(key)
        topics.append(key)
    return topics


def story_signal_score(
    event,
    *,
    final_score: float = 0,
    target_symbols: Iterable[str] | None = None,
) -> float:
    title = str(getattr(event, "title", "") or "")
    content = str(getattr(event, "content_zh", "") or getattr(event, "content_raw", "") or "")
    entity_id = str(getattr(event, "entity_id", "") or "").lower()
    topics = set(normalize_topics(getattr(event, "topics", []) or []))
    text = f"{title}\n{content}".lower()
    signals = getattr(event, "signals", {}) or {}
    signal = float(final_score or 0)

    topic_hits = topics.intersection(HIGH_SIGNAL_TOPICS)
    if topic_hits:
        signal += 2.5 + min(1.5, 0.5 * max(0, len(topic_hits) - 1))

    if entity_id in HIGH_SIGNAL_ENTITIES:
        signal += 2

    keyword_hits = sum(1 for keyword in HIGH_SIGNAL_KEYWORDS if keyword in text)
    signal += min(keyword_hits * 0.6, 3.0)

    target_count = len([symbol for symbol in (target_symbols or []) if str(symbol).strip()])
    if target_count:
        signal += min(2.0, 0.7 + 0.4 * target_count)

    source = str(getattr(event, "source", "") or "").lower()
    if source in {"github", "rss"}:
        signal += 0.8
    elif source == "web":
        signal += 0.4

    published_at = getattr(event, "published_at", None)
    if isinstance(published_at, datetime):
        age_hours = max(0.0, (datetime.utcnow() - published_at).total_seconds() / 3600)
        if age_hours <= 24:
            signal += 1.2
        elif age_hours <= 72:
            signal += 0.6

    if any(pattern in text for pattern in LOW_SIGNAL_PATTERNS) and not topic_hits and not target_count:
        signal -= 2.5

    if bool(signals.get("published_at_inferred")) and not topic_hits and not target_count:
        signal -= 1.5

    if not topic_hits and not target_count and float(final_score or 0) < 7:
        signal -= 1.2

    return round(signal, 2)


def methodology_signal_score(
    event,
    *,
    final_score: float = 0,
) -> float:
    title = str(getattr(event, "title", "") or "")
    content = str(getattr(event, "content_zh", "") or getattr(event, "content_raw", "") or "")
    entity_id = str(getattr(event, "entity_id", "") or "").lower()
    topics = set(normalize_topics(getattr(event, "topics", []) or []))
    text = f"{title}\n{content}".lower()
    score = 0.0

    if entity_id in METHODOLOGY_ENTITIES:
        score += 3.5

    topic_hits = topics.intersection(METHODOLOGY_TOPICS)
    if topic_hits:
        score += min(2.0, 1.0 + 0.5 * len(topic_hits))

    keyword_hits = sum(1 for keyword in METHODOLOGY_KEYWORDS if keyword in text)
    strong_hits = sum(1 for keyword in METHODOLOGY_STRONG_KEYWORDS if keyword in text)
    score += min(keyword_hits * 0.8, 4.0)
    score += min(strong_hits * 1.2, 3.6)

    source = str(getattr(event, "source", "") or "").lower()
    if source in {"rss", "github", "web"}:
        score += 1.0
    elif source in {"x", "twitter"}:
        score += 0.4

    if final_score:
        score += min(float(final_score) * 0.35, 3.0)

    if any(pattern in text for pattern in LOW_SIGNAL_PATTERNS):
        score -= 2.5

    if entity_id == "dan-koe" and keyword_hits == 0 and strong_hits == 0:
        score -= 3.0

    if len(title.strip()) < 10 and keyword_hits == 0 and strong_hits == 0:
        score -= 1.5

    return round(score, 2)
