"""
飞书通知器 - 发送事件告警到飞书
方案D: 新闻快讯风格，鲜艳醒目
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

# 北京时区
BEIJING_TZ = timezone(timedelta(hours=8))


def format_beijing_time(dt: Optional[datetime]) -> str:
    """将UTC时间转为北京时间格式化显示"""
    if dt is None:
        return "-"

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    beijing_time = dt.astimezone(BEIJING_TZ)
    return beijing_time.strftime("%m/%d %H:%M")


def format_time_short(dt: Optional[datetime]) -> str:
    """简短时间格式：显示延迟时间"""
    if dt is None:
        return "-"

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    now = datetime.now(timezone.utc)
    delta = now - dt

    total_minutes = int(delta.total_seconds() // 60)
    if total_minutes < 1:
        return "刚刚"
    if total_minutes < 60:
        return f"{total_minutes}分钟前"
    if total_minutes < 1440:
        return f"{total_minutes // 60}小时前"
    return f"{total_minutes // 1440}天前"


class FeishuNotifier:
    """飞书机器人通知 - 新闻快讯风格"""

    # 来源图标映射
    SOURCE_ICONS = {
        "rss": "📰",
        "github": "💻",
        "x": "𝕏",
        "twitter": "🐦",
        "web": "🌐",
        "arxiv": "📄",
        "blog": "📝",
        "hacker_news": "🔥",
    }

    # 告警等级样式 - 鲜艳醒目
    ALERT_STYLES = {
        "S": {
            "emoji": "🚨",
            "color": "red",
            "label": "BREAKING",
            "subtitle": "S级紧急"
        },
        "A": {
            "emoji": "⚡",
            "color": "orange",
            "label": "BREAKING",
            "subtitle": "A级重要"
        },
        "B": {
            "emoji": "📌",
            "color": "blue",
            "label": "INFO",
            "subtitle": "B级关注"
        },
        "C": {
            "emoji": "📋",
            "color": "grey",
            "label": "NOTE",
            "subtitle": "C级普通"
        },
    }

    def __init__(self, webhook_url: str, dashboard_url: Optional[str] = None):
        self.webhook_url = webhook_url
        self.dashboard_url = (dashboard_url or "").rstrip("/")

    def send_event_alert(
        self,
        title: str,
        content_zh: str,
        url: str,
        source: str,
        alert_level: str,
        entity_id: Optional[str] = None,
        published_at: Optional[datetime] = None,
        fetched_at: Optional[datetime] = None,
        published_time_inferred: bool = False,
        quality_score: Optional[int] = None,
        why_it_matters_zh: Optional[str] = None,
        research_impact: Optional[str] = None,
        product_impact: Optional[str] = None,
        market_impact: Optional[str] = None,
        topics: Optional[list[str]] = None,
    ) -> bool:
        """
        发送事件告警 - 新闻快讯风格
        """
        style = self.ALERT_STYLES.get(alert_level, self.ALERT_STYLES["C"])
        source_icon = self.SOURCE_ICONS.get(source.lower(), "📡")

        # 时间格式化
        time_str = format_time_short(published_at)

        # 构建卡片元素
        elements = []

        # 1. 标题区 - 大字体单独一行
        title_display = title[:60] + "..." if len(title) > 60 else title
        elements.append({
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": f"**{title_display}**",
            },
        })

        # 2. 分割线
        elements.append({"tag": "hr"})

        # 3. 正文内容
        content_preview = content_zh[:300] + "..." if len(content_zh) > 300 else content_zh
        elements.append({
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": content_preview,
            },
        })

        # 4. 核心影响（高亮显示）- 提取最重要的影响
        impact_text = None
        if why_it_matters_zh:
            impact_text = why_it_matters_zh[:100]
        elif research_impact:
            impact_text = f"🔬 {research_impact[:80]}"
        elif product_impact:
            impact_text = f"🛠️ {product_impact[:80]}"
        elif market_impact:
            impact_text = f"📊 {market_impact[:80]}"

        if impact_text:
            elements.append({
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": f"💡 **{impact_text}**",
                },
            })

        # 5. 分割线
        elements.append({"tag": "hr"})

        # 6. 三栏信息 - 使用column_set布局
        # 第一行：来源、实体、评分
        col1_text = f"{source_icon} {source.upper()}"
        col2_text = f"🏢 {entity_id or '-'}"
        col3_text = f"⭐ {quality_score or '-'}/10"

        elements.append({
            "tag": "column_set",
            "flex_mode": "none",
            "background_style": "grey",
            "columns": [
                {
                    "tag": "column",
                    "width": "weighted",
                    "weight": 1,
                    "elements": [{
                        "tag": "div",
                        "text": {"tag": "plain_text", "content": col1_text},
                        "text_align": "center",
                    }],
                },
                {
                    "tag": "column",
                    "width": "weighted",
                    "weight": 1,
                    "elements": [{
                        "tag": "div",
                        "text": {"tag": "plain_text", "content": col2_text},
                        "text_align": "center",
                    }],
                },
                {
                    "tag": "column",
                    "width": "weighted",
                    "weight": 1,
                    "elements": [{
                        "tag": "div",
                        "text": {"tag": "plain_text", "content": col3_text},
                        "text_align": "center",
                    }],
                },
            ],
        })

        # 第二行：时间信息
        time_col1 = f"🕐 {time_str}"
        time_col2 = f"📅 {format_beijing_time(published_at)}"
        time_col3 = f"🏷️ {alert_level}级"

        elements.append({
            "tag": "column_set",
            "flex_mode": "none",
            "background_style": "grey",
            "columns": [
                {
                    "tag": "column",
                    "width": "weighted",
                    "weight": 1,
                    "elements": [{
                        "tag": "div",
                        "text": {"tag": "plain_text", "content": time_col1},
                        "text_align": "center",
                    }],
                },
                {
                    "tag": "column",
                    "width": "weighted",
                    "weight": 1,
                    "elements": [{
                        "tag": "div",
                        "text": {"tag": "plain_text", "content": time_col2},
                        "text_align": "center",
                    }],
                },
                {
                    "tag": "column",
                    "width": "weighted",
                    "weight": 1,
                    "elements": [{
                        "tag": "div",
                        "text": {"tag": "plain_text", "content": time_col3},
                        "text_align": "center",
                    }],
                },
            ],
        })

        # 7. 主题标签（如果有）
        if topics and len(topics) > 0:
            tag_text = " ".join([f"`{t}`" for t in topics[:4]])
            elements.append({
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": f"🏷️ {tag_text}",
                },
            })

        # 8. 分割线
        elements.append({"tag": "hr"})

        # 9. 操作按钮
        actions = [
            {
                "tag": "button",
                "text": {"tag": "plain_text", "content": "🔗 查看原文"},
                "url": url,
                "type": "primary",
            }
        ]

        if self.dashboard_url:
            actions.append({
                "tag": "button",
                "text": {"tag": "plain_text", "content": "📊 详情"},
                "url": f"{self.dashboard_url}/events",
                "type": "default",
            })

        elements.append({"tag": "action", "actions": actions})

        # 10. 底部时间戳
        now_str = datetime.now(BEIJING_TZ).strftime("%Y/%m/%d %H:%M")
        elements.append({
            "tag": "note",
            "elements": [
                {
                    "tag": "plain_text",
                    "content": f"AI Radar · 推送于 {now_str}",
                }
            ],
        })

        # 构建完整消息
        message = {
            "msg_type": "interactive",
            "card": {
                "config": {
                    "wide_screen_mode": True,
                    "enable_forward": True,
                },
                "header": {
                    "title": {
                        "tag": "plain_text",
                        "content": f"{style['emoji']} {style['label']} · {style['subtitle']}",
                    },
                    "template": style["color"],
                },
                "elements": elements,
            },
        }

        try:
            with httpx.Client(timeout=15) as client:
                response = client.post(self.webhook_url, json=message)

                if response.status_code == 200:
                    data = response.json()
                    if data.get("StatusCode") == 0:
                        logger.info(f"飞书通知发送成功")
                        return True
                    else:
                        logger.error(f"飞书通知失败: {data}")
                        return False
                else:
                    logger.error(f"飞书请求错误: {response.status_code}")
                    return False

        except Exception as e:
            logger.error(f"飞书通知发送异常: {e}")
            return False

    def send_text(self, text: str) -> bool:
        """发送简单文本消息"""
        message = {
            "msg_type": "text",
            "content": {
                "text": text,
            },
        }

        try:
            with httpx.Client(timeout=10) as client:
                response = client.post(self.webhook_url, json=message)
                return response.status_code == 200
        except Exception as e:
            logger.error(f"飞书文本发送异常: {e}")
            return False