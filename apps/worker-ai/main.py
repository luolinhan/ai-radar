"""
AI Worker - 负责翻译、分析、通知
"""

import os
import time
import logging
from datetime import datetime, timedelta
from uuid import uuid4

from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy import and_
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from processors.translator import Translator
from processors.feishu_notifier import FeishuNotifier
from processors.translator import contains_chinese

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


def parse_bool_env(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "y", "on"}


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
    max_items = int(os.getenv("TRANSLATE_BATCH_ITEM_LIMIT", "40"))
    max_chars = int(os.getenv("TRANSLATE_BATCH_CHAR_LIMIT", "16000"))
    return max(1, max_items), max(1000, max_chars)


def split_translation_items(items: list[dict], max_items: int, max_chars: int) -> list[list[dict]]:
    batches: list[list[dict]] = []
    current_batch: list[dict] = []
    current_chars = 0

    for item in items:
        text = str(item.get("text", "")).strip()
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

        current_batch.append(item)
        current_chars += text_len

    if current_batch:
        batches.append(current_batch)

    return batches


def translate_items_in_batches(translator: Translator, items: list[dict]) -> dict[str, str]:
    if not items:
        return {}

    max_items, max_chars = translation_batch_settings()
    batches = split_translation_items(items, max_items=max_items, max_chars=max_chars)
    translated_map: dict[str, str] = {}

    for batch in batches:
        batch_result = translator.translate_batch(batch)
        if not batch_result:
            continue
        translated_map.update(batch_result)

    return translated_map


def compute_signal_score(event, signal_keywords: list[str]) -> int:
    """简单信号评分：用于控制告警质量和排序"""
    text_body = event.content_zh or event.content_raw or ""
    text = f"{event.title or ''}\n{text_body}".lower()
    score = 0

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

    keyword_hits = sum(1 for kw in signal_keywords if kw and kw in text)
    score += min(keyword_hits, 4)
    return score


def process_untranslated():
    """处理未翻译的事件"""
    if not translate_enabled():
        logger.info("翻译已禁用，跳过未翻译处理")
        return

    logger.info("开始处理未翻译事件...")
    db = SessionLocal()

    try:
        translator = build_translator()
        batch_size = int(os.getenv("TRANSLATE_BATCH_SIZE", "40"))
        from models import Event

        # 获取未翻译的事件
        untranslated = (
            db.query(Event)
            .filter(Event.content_zh.is_(None), Event.content_raw.isnot(None))
            .order_by(Event.published_at.desc())
            .limit(batch_size)
            .all()
        )

        if not untranslated:
            logger.info("没有待翻译事件")
            return

        translated_count = 0
        copied_chinese_count = 0
        failed_count = 0

        pending_jobs = []
        event_map = {}

        for event in untranslated:
            raw_text = (event.content_raw or "").strip()
            if not raw_text:
                failed_count += 1
                continue

            if contains_chinese(raw_text):
                event.content_zh = raw_text
                copied_chinese_count += 1
                continue

            pending_jobs.append((event.event_id, raw_text))
            event_map[event.event_id] = event

        if pending_jobs:
            logger.info("并发改为批量翻译: pending=%s", len(pending_jobs))
            translated_map = translate_items_in_batches(
                translator,
                [{"id": str(event_id), "text": text} for event_id, text in pending_jobs],
            )

            for event_id, raw_text in pending_jobs:
                event = event_map.get(event_id)
                if not event:
                    failed_count += 1
                    continue

                translated = (translated_map.get(str(event_id)) or "").strip()
                if not translated:
                    failed_count += 1
                    logger.warning("翻译为空，跳过: %s", event_id)
                    continue

                if translated == raw_text and not contains_chinese(translated):
                    failed_count += 1
                    logger.warning("翻译结果疑似无效（与原文一致），跳过: %s", event_id)
                    continue

                event.content_zh = translated
                translated_count += 1

        db.commit()
        logger.info(
            "翻译处理完成: total=%s, translated=%s, copied=%s, failed=%s",
            len(untranslated),
            translated_count,
            copied_chinese_count,
            failed_count,
        )

    except Exception as e:
        db.rollback()
        logger.error(f"翻译处理失败: {e}")
    finally:
        db.close()


def send_alerts():
    """发送告警通知"""
    logger.info("开始发送告警...")
    db = SessionLocal()

    try:
        webhook_url = os.getenv("FEISHU_WEBHOOK_URL")
        if not webhook_url:
            logger.warning("未配置飞书Webhook，跳过告警发送")
            return

        notifier = FeishuNotifier(
            webhook_url,
            dashboard_url=os.getenv("DASHBOARD_PUBLIC_URL", ""),
        )
        require_translation = parse_bool_env("ALERT_REQUIRE_TRANSLATION", True)
        allow_on_demand_translation = translate_enabled()
        max_per_run = int(os.getenv("ALERT_MAX_PER_RUN", "3"))
        dedup_hours = int(os.getenv("ALERT_DEDUP_HOURS", "24"))
        lookback_hours = int(os.getenv("ALERT_LOOKBACK_HOURS", "72"))
        min_quality_score = int(os.getenv("ALERT_MIN_QUALITY_SCORE", "4"))
        signal_keywords_env = (os.getenv("ALERT_SIGNAL_KEYWORDS") or "").strip()
        if signal_keywords_env:
            signal_keywords = [kw.strip().lower() for kw in signal_keywords_env.split(",") if kw.strip()]
        else:
            signal_keywords = [kw.lower() for kw in DEFAULT_SIGNAL_KEYWORDS]
        now = datetime.utcnow()
        dedup_window_start = now - timedelta(hours=dedup_hours)
        lookback_window_start = now - timedelta(hours=lookback_hours)

        from models import Event, Alert
        # 已发送/已跳过的事件不再重复处理
        processed_event_exists = db.query(Alert.id).filter(
            Alert.event_id == Event.event_id,
            Alert.channel == "feishu",
            Alert.status.in_(["sent", "skipped"]),
        ).exists()

        # 先取候选，再做质量和近窗去重
        alert_events = db.query(Event).filter(
            Event.content_raw.isnot(None),
            Event.published_at >= lookback_window_start,
            ~processed_event_exists,
        ).order_by(Event.published_at.desc()).limit(max_per_run * 5).all()

        ranked_events = sorted(
            ((compute_signal_score(event, signal_keywords), event) for event in alert_events),
            key=lambda x: (x[0], x[1].published_at or datetime.min),
            reverse=True,
        )

        if allow_on_demand_translation:
            need_translation_items = []
            event_lookup = {}
            for _, event in ranked_events:
                content_zh = (event.content_zh or "").strip()
                content_raw = (event.content_raw or "").strip()
                if content_zh or not content_raw:
                    continue
                if contains_chinese(content_raw):
                    event.content_zh = content_raw
                    continue

                if len(content_raw) < 30:
                    continue

                event_id = str(event.event_id)
                event_lookup[event_id] = event
                need_translation_items.append({"id": event_id, "text": content_raw[:4000]})

            if need_translation_items:
                translated_map = translate_items_in_batches(
                    build_translator(),
                    need_translation_items,
                )
                for event_id, event in event_lookup.items():
                    translated = (translated_map.get(event_id) or "").strip()
                    if translated:
                        event.content_zh = translated
                db.commit()

        sent_count = 0

        for quality_score, event in ranked_events:
            if sent_count >= max_per_run:
                break

            try:
                content_zh = (event.content_zh or "").strip()
                content_raw = (event.content_raw or "").strip()

                if not content_zh and content_raw:
                    if contains_chinese(content_raw):
                        content_zh = content_raw
                    elif require_translation:
                        db.add(Alert(
                            id=uuid4(),
                            event_id=event.event_id,
                            alert_level=event.alert_level,
                            sent_at=now,
                            channel="feishu",
                            status="skipped",
                            error_message="translation_required_but_unavailable",
                        ))
                        db.commit()
                        logger.info(f"跳过未翻译告警: {event.event_id}")
                        continue

                content_for_card = (content_zh or "").strip()
                if not content_for_card and not require_translation:
                    content_for_card = content_raw

                if not content_for_card:
                    content_for_card = event.title or "新事件"

                if len(content_for_card) < 30:
                    db.add(Alert(
                        id=uuid4(),
                        event_id=event.event_id,
                        alert_level=event.alert_level,
                        sent_at=now,
                        channel="feishu",
                        status="skipped",
                        error_message="low_quality_content",
                    ))
                    db.commit()
                    logger.info(f"跳过低质量告警: {event.event_id}")
                    continue

                if quality_score < min_quality_score:
                    db.add(Alert(
                        id=uuid4(),
                        event_id=event.event_id,
                        alert_level=event.alert_level,
                        sent_at=now,
                        channel="feishu",
                        status="skipped",
                        error_message=f"low_signal_score_{quality_score}",
                    ))
                    db.commit()
                    logger.info(f"跳过低信号告警: {event.event_id}, score={quality_score}")
                    continue

                # 近窗内同URL已推送过，则跳过，避免同一资讯多次刷屏
                recent_sent_same_url = db.query(Alert.id).join(
                    Event, Alert.event_id == Event.event_id
                ).filter(
                    and_(
                        Alert.channel == "feishu",
                        Alert.status == "sent",
                        Event.url == event.url,
                        Alert.sent_at >= dedup_window_start,
                    )
                ).first()
                if recent_sent_same_url:
                    db.add(Alert(
                        id=uuid4(),
                        event_id=event.event_id,
                        alert_level=event.alert_level,
                        sent_at=now,
                        channel="feishu",
                        status="skipped",
                        error_message=f"duplicate_url_within_{dedup_hours}h",
                    ))
                    db.commit()
                    logger.info(f"跳过重复URL告警: {event.event_id}")
                    continue

                logger.info(f"发送告警: {event.event_id}")
                published_time_inferred = bool((event.signals or {}).get("published_at_inferred", False))

                success = notifier.send_event_alert(
                    title=event.title or "新事件",
                    content_zh=content_for_card,
                    url=event.url,
                    source=event.source,
                    alert_level=event.alert_level,
                    entity_id=event.entity_id,
                    published_at=event.published_at,
                    fetched_at=event.fetched_at,
                    published_time_inferred=published_time_inferred,
                    quality_score=quality_score,
                    why_it_matters_zh=event.why_it_matters_zh,
                    research_impact=event.research_impact,
                    product_impact=event.product_impact,
                    market_impact=event.market_impact,
                    topics=event.topics or [],
                )

                if success:
                    alert = Alert(
                        id=uuid4(),
                        event_id=event.event_id,
                        alert_level=event.alert_level,
                        sent_at=now,
                        channel="feishu",
                        status="sent",
                    )
                    db.add(alert)
                    db.commit()
                    sent_count += 1

                    logger.info(f"告警发送成功: {event.event_id}")
                else:
                    db.add(Alert(
                        id=uuid4(),
                        event_id=event.event_id,
                        alert_level=event.alert_level,
                        sent_at=now,
                        channel="feishu",
                        status="failed",
                        error_message="feishu_send_failed",
                    ))
                    db.commit()
                    logger.warning(f"告警发送失败: {event.event_id}")

            except Exception as e:
                db.rollback()
                logger.error(f"告警发送失败: {event.event_id}, 错误: {e}")

        logger.info(f"告警处理完成: candidates={len(alert_events)}, sent={sent_count}")

    except Exception as e:
        logger.error(f"告警处理失败: {e}")
    finally:
        db.close()


def main():
    """主函数"""
    logger.info("AI Worker启动")

    # 等待数据库就绪
    time.sleep(5)

    scheduler = BackgroundScheduler()

    # 翻译任务：默认每2分钟执行一次，并发批处理
    scheduler.add_job(
        process_untranslated,
        'interval',
        minutes=int(os.getenv("TRANSLATE_SCAN_INTERVAL_MINUTES", "2")),
    )

    # 告警定时检查（默认每10分钟，可通过环境变量覆盖）
    scheduler.add_job(
        send_alerts,
        'interval',
        minutes=int(os.getenv("ALERT_SCAN_INTERVAL_MINUTES", "10")),
    )

    scheduler.start()

    logger.info("调度器已启动")

    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        scheduler.shutdown()


if __name__ == "__main__":
    main()
