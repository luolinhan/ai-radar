"""
AI Worker v2 - 负责翻译、分析、主题聚类和飞书推送。
"""

from __future__ import annotations

import logging
import os
import time
from datetime import datetime, timedelta
from uuid import uuid4

from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy import and_, create_engine
from sqlalchemy.orm import sessionmaker

from analyzers import (
    ImpactAnalyzer,
    MarketContextAnalyzer,
    RiskAnalyzer,
    ScoringEngine,
    TargetMapper,
    ThemeClassifier,
)
from analyzers.theme_classifier import THEME_RULES
from processors.feishu_notifier import FeishuNotifier
from processors.translator import Translator, contains_chinese

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://ai_radar:ai_radar_password@postgres:5432/ai_radar",
)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

DEFAULT_SIGNAL_KEYWORDS = [
    "release",
    "launch",
    "model",
    "gpt",
    "claude",
    "gemini",
    "open source",
    "paper",
    "benchmark",
    "safety",
    "policy",
    "funding",
    "acquire",
    "partnership",
    "chip",
    "gpu",
    "发布",
    "开源",
    "模型",
    "安全",
    "融资",
    "收购",
    "合作",
]

HIGH_PRIORITY_ENTITY_IDS = {
    "openai",
    "anthropic",
    "google-deepmind",
    "nvidia",
    "microsoft-ai",
    "google-ai",
    "xai",
    "sequoia",
}

EDITORIAL_PRIORITY_TOPICS = {
    "frontier-models",
    "open-source-models",
    "ai-infra",
    "gpu-compute",
    "ai-applications",
    "chip-supply-chain",
}

EDITORIAL_PRIORITY_KEYWORDS = {
    "launch",
    "launched",
    "release",
    "released",
    "reasoning",
    "agent",
    "agentic",
    "workflow",
    "benchmark",
    "open model",
    "open-source",
    "open source",
    "weights",
    "byte for byte",
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
    "multimodal",
    "推理",
    "智能体",
    "工作流",
    "开源",
    "发布",
    "模型",
    "提示词",
    "教程",
    "案例",
    "技巧",
}

LOW_SIGNAL_PATTERNS = {
    "text from @",
    "<img",
    "just now",
    "rsshub-quote",
    "repost:",
}


def parse_bool_env(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "y", "on"}


def get_recent_window_days() -> int:
    return max(3, int(os.getenv("COLLECT_MAX_EVENT_AGE_DAYS", "6")))


def get_analysis_window_days() -> int:
    return max(1, int(os.getenv("ANALYSIS_LOOKBACK_DAYS", str(get_recent_window_days()))))


def get_theme_window_days() -> int:
    return max(3, int(os.getenv("THEME_LOOKBACK_DAYS", str(get_recent_window_days()))))


def build_translator() -> Translator:
    return Translator(
        api_base_url=os.getenv("AI_API_BASE_URL"),
        api_key=os.getenv("AI_API_KEY"),
        model=os.getenv("AI_MODEL", "qwen3.5-plus"),
        timeout_seconds=int(os.getenv("TRANSLATE_TIMEOUT_SECONDS", "120")),
        max_retries=int(os.getenv("TRANSLATE_MAX_RETRIES", "1")),
    )


def translate_enabled() -> bool:
    return parse_bool_env("TRANSLATE_ENABLED", True)


def translation_batch_settings() -> tuple[int, int]:
    max_items = int(os.getenv("TRANSLATE_BATCH_ITEM_LIMIT", "10"))
    max_chars = int(os.getenv("TRANSLATE_BATCH_CHAR_LIMIT", "8000"))
    return max(1, max_items), max(1000, max_chars)


def translation_item_text_limit() -> int:
    return max(200, int(os.getenv("TRANSLATE_ITEM_TEXT_LIMIT", "1000")))


def prepare_translation_text(text: str) -> str:
    raw = (text or "").strip()
    if not raw:
        return ""

    limit = translation_item_text_limit()
    if len(raw) <= limit:
        return raw

    return raw[:limit].rstrip() + "\n\n[内容较长，已截断，仅翻译前半部分以控制成本和时延]"


def build_translation_source_text(event) -> str:
    title = (event.title or "").strip()
    content = (event.content_raw or "").strip()

    if title and content:
        normalized_title = " ".join(title.lower().split())
        normalized_content = " ".join(content.lower().split())
        if normalized_title and normalized_title not in normalized_content:
            return prepare_translation_text(f"{title}\n\n{content}")

    if content:
        return prepare_translation_text(content)

    if title:
        return prepare_translation_text(title)

    return ""


def split_translation_items(items: list[dict], max_items: int, max_chars: int) -> list[list[dict]]:
    batches: list[list[dict]] = []
    current_batch: list[dict] = []
    current_chars = 0

    for item in items:
        text = prepare_translation_text(str(item.get("text", "")))
        if not text:
            continue

        text_len = len(text)
        should_split = (
            current_batch
            and (
                len(current_batch) >= max_items
                or current_chars + text_len > max_chars
            )
        )
        if should_split:
            batches.append(current_batch)
            current_batch = []
            current_chars = 0

        current_batch.append({"id": item.get("id"), "text": text})
        current_chars += text_len

    if current_batch:
        batches.append(current_batch)

    return batches


def translate_items_with_fallback(translator: Translator, items: list[dict]) -> dict[str, str]:
    if not items:
        return {}

    if len(items) == 1:
        single = items[0]
        result = translator.translate_batch(items)
        if result:
            return result

        text = prepare_translation_text(str(single.get("text", "")))
        translated = translator.translate(text)
        if translated:
            return {str(single.get("id", "")).strip(): translated}
        return {}

    batch_result = translator.translate_batch(items)
    if batch_result:
        return batch_result

    mid = len(items) // 2
    left = translate_items_with_fallback(translator, items[:mid])
    right = translate_items_with_fallback(translator, items[mid:])
    left.update(right)
    return left


def translate_items_in_batches(translator: Translator, items: list[dict]) -> dict[str, str]:
    if not items:
        return {}

    max_items, max_chars = translation_batch_settings()
    batches = split_translation_items(items, max_items=max_items, max_chars=max_chars)
    translated_map: dict[str, str] = {}

    for batch in batches:
        translated_map.update(translate_items_with_fallback(translator, batch))

    return translated_map


def compute_signal_score(event, signal_keywords: list[str]) -> int:
    text_body = event.content_zh or event.content_raw or ""
    text = f"{event.title or ''}\n{text_body}".lower()
    score = 0
    topics = set(normalize_topics(getattr(event, "topics", []) or []))

    if event.alert_level == "S":
        score += 4
    elif event.alert_level == "A":
        score += 2

    if event.entity_id in HIGH_PRIORITY_ENTITY_IDS:
        score += 2

    if event.source == "github":
        score += 2
    elif event.source == "x":
        score += 2
    elif event.source == "rss":
        score += 1
    elif event.source == "web":
        score += 1

    content_len = len((text_body or "").strip())
    if content_len >= 120:
        score += 1
    if content_len >= 300:
        score += 1

    keyword_hits = sum(1 for keyword in signal_keywords if keyword and keyword in text)
    score += min(keyword_hits, 4)

    editorial_topic_hits = topics.intersection(EDITORIAL_PRIORITY_TOPICS)
    if editorial_topic_hits:
        score += 2 + min(2, len(editorial_topic_hits) - 1)

    editorial_keyword_hits = sum(
        1 for keyword in EDITORIAL_PRIORITY_KEYWORDS if keyword in text
    )
    score += min(editorial_keyword_hits, 4)

    if getattr(event, "tickers", None):
        score += 1
    if getattr(event, "why_it_matters_zh", None):
        score += 1

    if any(pattern in text for pattern in LOW_SIGNAL_PATTERNS) and not editorial_topic_hits:
        score -= 3

    if (
        bool((getattr(event, "signals", {}) or {}).get("published_at_inferred"))
        and not editorial_topic_hits
        and not getattr(event, "tickers", None)
    ):
        score -= 2

    return score


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
        topics.append(text)
    return topics


def merge_topics(existing_topics, classified_topics) -> list[str]:
    merged = normalize_topics(existing_topics)
    seen = {topic.lower() for topic in merged}

    for topic in classified_topics or []:
        text = str(topic or "").strip()
        if not text:
            continue
        key = text.lower()
        if key in seen:
            continue
        seen.add(key)
        merged.append(text)

    return merged[:5]


def process_untranslated():
    if not translate_enabled():
        logger.info("翻译已禁用，跳过未翻译处理")
        return

    logger.info("开始处理未翻译事件...")
    db = SessionLocal()

    try:
        from models import Event

        translator = build_translator()
        batch_size = int(os.getenv("TRANSLATE_BATCH_SIZE", "10"))
        recent_window_start = datetime.utcnow() - timedelta(days=get_recent_window_days())

        untranslated = (
            db.query(Event)
            .filter(
                Event.content_zh.is_(None),
                Event.published_at >= recent_window_start,
            )
            .order_by(Event.published_at.desc())
            .limit(batch_size)
            .all()
        )

        if not untranslated:
            logger.info("没有待翻译事件")
            return

        translated_count = 0
        copied_count = 0
        failed_count = 0
        pending_items = []
        event_lookup = {}

        for event in untranslated:
            source_text = build_translation_source_text(event)
            if not source_text:
                failed_count += 1
                logger.info("跳过无可翻译文本事件: %s", event.event_id)
                continue

            if contains_chinese(source_text):
                event.content_zh = source_text
                copied_count += 1
                continue

            event_id = str(event.event_id)
            pending_items.append({"id": event_id, "text": source_text})
            event_lookup[event_id] = event

        if pending_items:
            translated_map = translate_items_in_batches(translator, pending_items)
            for item in pending_items:
                event_id = str(item["id"])
                original_text = str(item["text"]).strip()
                translated = (translated_map.get(event_id) or "").strip()
                event = event_lookup[event_id]

                if not translated:
                    failed_count += 1
                    logger.warning("翻译为空，跳过: %s", event_id)
                    continue

                if translated == original_text and not contains_chinese(translated):
                    failed_count += 1
                    # If the original text is a URL, mark it as failed but don't log warning
                    if not original_text.startswith("http://") and not original_text.startswith("https://"):
                        logger.warning("翻译结果疑似无效，跳过: %s", event_id)
                    continue

                event.content_zh = translated
                translated_count += 1

        db.commit()
        logger.info(
            "翻译处理完成: total=%s, translated=%s, copied=%s, failed=%s",
            len(untranslated),
            translated_count,
            copied_count,
            failed_count,
        )
    except Exception as exc:
        db.rollback()
        logger.error("翻译处理失败: %s", exc)
    finally:
        db.close()


def analyze_unanalyzed_events():
    logger.info("开始分析未处理事件...")
    db = SessionLocal()

    try:
        from models import Event
        from models_v2 import EventScoreDetail

        analysis_window_start = datetime.utcnow() - timedelta(days=get_analysis_window_days())
        unanalyzed = (
            db.query(Event)
            .filter(
                Event.content_zh.isnot(None),
                Event.published_at >= analysis_window_start,
            )
            .outerjoin(EventScoreDetail, Event.event_id == EventScoreDetail.event_id)
            .filter(EventScoreDetail.id.is_(None))
            .order_by(Event.published_at.desc())
            .limit(int(os.getenv("ANALYSIS_BATCH_SIZE", "30")))
            .all()
        )

        if not unanalyzed:
            logger.info("没有待分析事件")
            return

        logger.info("发现 %d 条待分析事件", len(unanalyzed))

        target_mapper = TargetMapper(db)
        market_analyzer = MarketContextAnalyzer(db)
        impact_analyzer = ImpactAnalyzer(db, translator=translator)
        scoring_engine = ScoringEngine(db)
        risk_analyzer = RiskAnalyzer(db)
        theme_classifier = ThemeClassifier()
        translator = build_translator()

        for event in unanalyzed:
            try:
                logger.info("分析事件: %s", event.event_id)

                targets = target_mapper.map_event_targets(event)
                market_context = market_analyzer.analyze_context(
                    event.published_at or datetime.utcnow()
                )
                impacts = impact_analyzer.analyze_impact(event, targets)
                score = scoring_engine.score_event(event, targets)
                risks = risk_analyzer.analyze_risks(
                    event, score, market_context, targets
                )
                action = risk_analyzer.determine_action(risks, score)

                merged_topics = merge_topics(
                    event.topics,
                    theme_classifier.classify_event(event, targets),
                )
                if merged_topics != normalize_topics(event.topics):
                    event.topics = merged_topics

                if not (event.why_it_matters_zh or "").strip():
                    why_it_matters = theme_classifier.summarize_why_it_matters(
                        event,
                        merged_topics,
                        targets,
                        score,
                        translator=translator,
                    )
                    if why_it_matters:
                        event.why_it_matters_zh = why_it_matters

                if targets:
                    impact_analyzer.save_impact_hypotheses(event.event_id, impacts)
                market_analyzer.save_context(event.event_id, market_context)
                scoring_engine.save_score(event.event_id, score)
                risk_analyzer.save_risks(event.event_id, risks, action)
                logger.info(
                    "事件分析完成: %s, score=%.1f, topics=%s",
                    event.event_id,
                    score.get("final_score", 0),
                    merged_topics,
                )
            except Exception as exc:
                logger.error("分析事件失败: %s, 错误: %s", event.event_id, exc)
                db.rollback()

        logger.info("分析完成: %d 条事件", len(unanalyzed))
    except Exception as exc:
        logger.error("分析任务失败: %s", exc)
    finally:
        db.close()


def refresh_recent_themes():
    logger.info("开始刷新主题聚类...")
    db = SessionLocal()

    try:
        from models import Event
        from models_v2 import EventScoreDetail, ThemeCluster

        now = datetime.utcnow()
        short_window_days = get_theme_window_days()
        short_window_start = now - timedelta(days=short_window_days)
        long_window_start = now - timedelta(days=30)
        trend_window_days = max(1, short_window_days // 2)
        trend_split = now - timedelta(days=trend_window_days)
        previous_trend_start = trend_split - timedelta(days=trend_window_days)

        recent_events = (
            db.query(Event)
            .filter(Event.published_at >= long_window_start)
            .order_by(Event.published_at.desc())
            .all()
        )

        if not recent_events:
            logger.info("最近 30 天没有事件，跳过主题刷新")
            return

        event_ids = [event.event_id for event in recent_events]
        score_rows = (
            db.query(EventScoreDetail)
            .filter(EventScoreDetail.event_id.in_(event_ids))
            .all()
        )
        score_map = {row.event_id: row for row in score_rows}

        target_mapper = TargetMapper(db)
        classifier = ThemeClassifier()
        translator = build_translator()

        topics_updated = 0
        summary_updated = 0
        for event in recent_events:
            current_topics = normalize_topics(event.topics)
            need_targets = not current_topics or not (event.why_it_matters_zh or "").strip()
            targets = target_mapper.map_event_targets(event) if need_targets else []
            merged_topics = merge_topics(
                current_topics,
                classifier.classify_event(event, targets),
            )

            if merged_topics != current_topics:
                event.topics = merged_topics
                topics_updated += 1

            if not (event.why_it_matters_zh or "").strip():
                score_row = score_map.get(event.event_id)
                score_summary = {"final_score": score_row.final_score} if score_row else None
                summary = classifier.summarize_why_it_matters(
                    event,
                    merged_topics,
                    targets,
                    score_summary,
                    translator=translator,
                )
                if summary:
                    event.why_it_matters_zh = summary
                    summary_updated += 1

        if topics_updated or summary_updated:
            db.commit()

        themes = (
            db.query(ThemeCluster)
            .filter(ThemeCluster.is_active.is_(True))
            .all()
        )
        if not themes:
            logger.info("没有主题簇配置，跳过聚类统计")
            return

        for theme in themes:
            matched_recent = []
            matched_30d = []
            recent_half = 0
            previous_half = 0
            score_values = []
            actionable_count = 0

            for event in recent_events:
                event_topics = normalize_topics(event.topics)
                if theme.name_en not in event_topics:
                    continue

                published_at = event.published_at or datetime.min
                if published_at >= long_window_start:
                    matched_30d.append(event)

                if published_at >= short_window_start:
                    matched_recent.append(event)
                    score_row = score_map.get(event.event_id)
                    if score_row:
                        score_values.append(score_row.final_score or 0)
                        if score_row.is_actionable:
                            actionable_count += 1

                if published_at >= trend_split:
                    recent_half += 1
                elif previous_trend_start <= published_at < trend_split:
                    previous_half += 1

            if recent_half > previous_half:
                heat_trend = "up"
            elif recent_half < previous_half:
                heat_trend = "down"
            else:
                heat_trend = "flat"

            default_symbols = list(THEME_RULES.get(theme.name_en, {}).get("symbols", []))

            theme.event_count_7d = len(matched_recent)
            theme.event_count_30d = len(matched_30d)
            theme.avg_score = round(sum(score_values) / len(score_values), 2) if score_values else 0
            theme.hit_rate = round(actionable_count / len(matched_recent) * 100, 1) if matched_recent else 0
            theme.heat_trend = heat_trend
            if default_symbols:
                theme.related_symbols = default_symbols[:5]

        db.commit()
        logger.info(
            "主题刷新完成: themes=%s, topics_updated=%s, summary_updated=%s",
            len(themes),
            topics_updated,
            summary_updated,
        )
    except Exception as exc:
        db.rollback()
        logger.error("主题刷新失败: %s", exc)
    finally:
        db.close()


def send_alerts():
    logger.info("开始发送告警...")
    db = SessionLocal()

    try:
        webhook_url = os.getenv("FEISHU_WEBHOOK_URL")
        if not webhook_url:
            logger.warning("未配置飞书Webhook，跳过告警发送")
            return

        from models import Alert, Event
        from models_v2 import EventScoreDetail

        notifier = FeishuNotifier(
            webhook_url,
            dashboard_url=os.getenv("DASHBOARD_PUBLIC_URL", ""),
        )
        require_translation = parse_bool_env("ALERT_REQUIRE_TRANSLATION", True)
        allow_on_demand_translation = translate_enabled()
        max_per_run = int(os.getenv("ALERT_MAX_PER_RUN", "5"))
        dedup_hours = int(os.getenv("ALERT_DEDUP_HOURS", "24"))
        lookback_hours = int(os.getenv("ALERT_LOOKBACK_HOURS", "144"))
        min_event_score = float(os.getenv("ALERT_MIN_EVENT_SCORE", "6"))
        min_quality_score = int(os.getenv("ALERT_MIN_QUALITY_SCORE", "4"))
        signal_keywords_env = (os.getenv("ALERT_SIGNAL_KEYWORDS") or "").strip()
        if signal_keywords_env:
            signal_keywords = [
                keyword.strip().lower()
                for keyword in signal_keywords_env.split(",")
                if keyword.strip()
            ]
        else:
            signal_keywords = [keyword.lower() for keyword in DEFAULT_SIGNAL_KEYWORDS]

        now = datetime.utcnow()
        dedup_window_start = now - timedelta(hours=dedup_hours)
        lookback_window_start = now - timedelta(hours=lookback_hours)

        recent_sent_alerts = (
            db.query(Alert)
            .filter(
                Alert.channel == "feishu",
                Alert.status == "sent",
                Alert.sent_at >= dedup_window_start,
            )
            .all()
        )
        recent_sent_event_ids = {alert.event_id for alert in recent_sent_alerts}

        candidates = (
            db.query(Event, EventScoreDetail)
            .join(EventScoreDetail, Event.event_id == EventScoreDetail.event_id)
            .filter(
                Event.published_at >= lookback_window_start,
                EventScoreDetail.final_score >= min_event_score,
            )
            .order_by(Event.published_at.desc())
            .limit(max_per_run * 12)
            .all()
        )

        ranked_candidates = []
        for event, score_row in candidates:
            if event.event_id in recent_sent_event_ids:
                continue

            signal_score = compute_signal_score(event, signal_keywords)
            if signal_score < min_quality_score:
                continue

            ranked_candidates.append((event, score_row, signal_score))

        ranked_candidates.sort(
            key=lambda item: (
                bool(item[1].is_actionable),
                item[1].final_score or 0,
                item[2],
                item[0].published_at or datetime.min,
            ),
            reverse=True,
        )

        if allow_on_demand_translation and ranked_candidates:
            translator = build_translator()
            translation_items = []
            for event, _score_row, _signal_score in ranked_candidates:
                if (event.content_zh or "").strip():
                    continue
                source_text = build_translation_source_text(event)
                if not source_text:
                    continue
                if contains_chinese(source_text):
                    event.content_zh = source_text
                    continue
                translation_items.append({"id": str(event.event_id), "text": source_text})

            if translation_items:
                translated_map = translate_items_in_batches(translator, translation_items)
                for event, _score_row, _signal_score in ranked_candidates:
                    translated = (translated_map.get(str(event.event_id)) or "").strip()
                    if translated:
                        event.content_zh = translated
                db.commit()

        sent_count = 0

        for event, score_row, signal_score in ranked_candidates:
            if sent_count >= max_per_run:
                break

            content_zh = (event.content_zh or "").strip()
            source_text = build_translation_source_text(event)
            detail_url = ""
            dashboard_url = (os.getenv("DASHBOARD_PUBLIC_URL", "") or "").rstrip("/")
            if dashboard_url:
                detail_url = f"{dashboard_url}/dashboard/events/{event.event_id}"

            if not content_zh and source_text:
                if contains_chinese(source_text):
                    content_zh = source_text
                elif require_translation:
                    logger.info("跳过未翻译告警: %s", event.event_id)
                    continue
                else:
                    content_zh = source_text

            content_for_card = content_zh or (event.title or "").strip()
            if len(content_for_card) < 12:
                logger.info("跳过低质量告警: %s", event.event_id)
                continue

            recent_sent_same_url = (
                db.query(Alert.id)
                .join(Event, Alert.event_id == Event.event_id)
                .filter(
                    and_(
                        Alert.channel == "feishu",
                        Alert.status == "sent",
                        Event.url == event.url,
                        Alert.sent_at >= dedup_window_start,
                    )
                )
                .first()
            )
            if recent_sent_same_url:
                logger.info("跳过重复URL告警: %s", event.event_id)
                continue

            success = notifier.send_event_alert(
                title=event.title or "新事件",
                content_zh=content_for_card,
                url=event.url,
                source=event.source,
                alert_level=event.alert_level,
                entity_id=event.entity_id,
                published_at=event.published_at,
                fetched_at=event.fetched_at,
                published_time_inferred=bool((event.signals or {}).get("published_at_inferred", False)),
                quality_score=round(score_row.final_score or 0, 1),
                why_it_matters_zh=event.why_it_matters_zh,
                research_impact=event.research_impact,
                product_impact=event.product_impact,
                market_impact=event.market_impact,
                topics=normalize_topics(event.topics),
                detail_url=detail_url or None,
            )

            if success:
                db.add(
                    Alert(
                        id=uuid4(),
                        event_id=event.event_id,
                        alert_level=event.alert_level,
                        sent_at=now,
                        channel="feishu",
                        status="sent",
                    )
                )
                db.commit()
                sent_count += 1
                logger.info(
                    "告警发送成功: %s, final_score=%.1f, signal_score=%s",
                    event.event_id,
                    score_row.final_score or 0,
                    signal_score,
                )
            else:
                db.add(
                    Alert(
                        id=uuid4(),
                        event_id=event.event_id,
                        alert_level=event.alert_level,
                        sent_at=now,
                        channel="feishu",
                        status="failed",
                        error_message="send_failed",
                    )
                )
                db.commit()

        logger.info("告警处理完成: sent=%d, candidates=%d", sent_count, len(ranked_candidates))
    except Exception as exc:
        db.rollback()
        logger.error("告警处理失败: %s", exc)
    finally:
        db.close()


def main():
    logger.info("AI Worker v2 启动")

    time.sleep(5)

    scheduler = BackgroundScheduler()

    scheduler.add_job(
        process_untranslated,
        "interval",
        minutes=int(os.getenv("TRANSLATE_SCAN_INTERVAL_MINUTES", "1")),
    )

    scheduler.add_job(
        analyze_unanalyzed_events,
        "interval",
        minutes=int(os.getenv("ANALYSIS_SCAN_INTERVAL_MINUTES", "30")),
    )

    scheduler.add_job(
        refresh_recent_themes,
        "interval",
        minutes=int(os.getenv("THEME_REFRESH_INTERVAL_MINUTES", "30")),
    )

    scheduler.add_job(
        send_alerts,
        "interval",
        minutes=int(os.getenv("ALERT_SCAN_INTERVAL_MINUTES", "2")),
    )

    scheduler.start()
    logger.info("调度器已启动")

    logger.info("执行初始任务...")
    process_untranslated()
    analyze_unanalyzed_events()
    refresh_recent_themes()
    send_alerts()

    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        scheduler.shutdown()


if __name__ == "__main__":
    main()
