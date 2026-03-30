"""
AI Worker - 负责翻译、分析、通知
"""

import os
import time
import logging
from datetime import datetime

from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from processors.translator import Translator
from processors.feishu_notifier import FeishuNotifier

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


def process_untranslated():
    """处理未翻译的事件"""
    logger.info("开始处理未翻译事件...")
    db = SessionLocal()

    try:
        translator = Translator(
            api_base_url=os.getenv("AI_API_BASE_URL"),
            api_key=os.getenv("AI_API_KEY"),
            model=os.getenv("AI_MODEL", "qwen3.5-plus"),
        )

        from models import Event
        # 获取未翻译的事件
        untranslated = db.query(Event).filter(Event.content_zh == None).limit(10).all()

        for event in untranslated:
            try:
                logger.info(f"翻译事件: {event.event_id}")
                translated = translator.translate(event.content_raw)

                event.content_zh = translated
                db.commit()

                logger.info(f"翻译完成: {event.event_id}")

            except Exception as e:
                logger.error(f"翻译失败: {event.event_id}, 错误: {e}")

        logger.info(f"处理了 {len(untranslated)} 条未翻译事件")

    except Exception as e:
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

        notifier = FeishuNotifier(webhook_url)

        from models import Event, Alert
        # 获取需要告警且未发送的事件
        alert_events = db.query(Event).filter(
            Event.alert_level.in_(["S", "A"]),
            Event.content_zh != None,
        ).limit(5).all()

        for event in alert_events:
            try:
                logger.info(f"发送告警: {event.event_id}")

                success = notifier.send_event_alert(
                    title=event.title or "新事件",
                    content_zh=event.content_zh,
                    url=event.url,
                    source=event.source,
                    alert_level=event.alert_level,
                )

                if success:
                    # 记录告警状态
                    alert = Alert(
                        id=os.urandom(16).hex(),
                        event_id=event.event_id,
                        alert_level=event.alert_level,
                        sent_at=datetime.utcnow(),
                        channel="feishu",
                        status="sent",
                    )
                    db.add(alert)
                    db.commit()

                    logger.info(f"告警发送成功: {event.event_id}")

            except Exception as e:
                logger.error(f"告警发送失败: {event.event_id}, 错误: {e}")

        logger.info(f"处理了 {len(alert_events)} 条告警")

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

    # 翻译每5分钟处理一次
    scheduler.add_job(process_untranslated, 'interval', minutes=5)

    # 告警每1分钟检查一次
    scheduler.add_job(send_alerts, 'interval', minutes=1)

    scheduler.start()

    logger.info("调度器已启动")

    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        scheduler.shutdown()


if __name__ == "__main__":
    main()