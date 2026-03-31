"""
飞书通知器 - 发送事件告警到飞书
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

    # 如果是naive datetime，假设为UTC
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    # 转为北京时间
    beijing_time = dt.astimezone(BEIJING_TZ)
    return beijing_time.strftime("%Y/%m/%d %H:%M")


class FeishuNotifier:
    """飞书机器人通知"""

    # 来源图标映射
    SOURCE_ICONS = {
        "rss": "📰",
        "github": "💻",
        "twitter": "🐦",
        "x": "🐦",
        "arxiv": "📄",
        "blog": "📝",
        "hacker_news": "🔥",
    }

    # 告警等级样式
    ALERT_STYLES = {
        "S": {"emoji": "🚨", "color": "red", "label": "S级·紧急"},
        "A": {"emoji": "⚡", "color": "orange", "label": "A级·重要"},
        "B": {"emoji": "📌", "color": "blue", "label": "B级·关注"},
        "C": {"emoji": "📋", "color": "grey", "label": "C级·普通"},
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
        quality_score: Optional[int] = None,
        why_it_matters_zh: Optional[str] = None,
        research_impact: Optional[str] = None,
        product_impact: Optional[str] = None,
        market_impact: Optional[str] = None,
        topics: Optional[list[str]] = None,
    ) -> bool:
        """
        发送事件告警 - 科技感卡片风格
        """
        style = self.ALERT_STYLES.get(alert_level, self.ALERT_STYLES["C"])
        source_icon = self.SOURCE_ICONS.get(source.lower(), "📡")

        # 时间转为北京时间
        time_str = format_beijing_time(published_at)

        # 构建卡片元素
        elements = []

        # 1. 元信息栏（来源、实体、时间）
        meta_parts = [
            f"{source_icon} **{source.upper()}**",
            f"🏢 {entity_id or '-'}",
            f"🕐 {time_str}",
        ]
        if quality_score is not None:
            meta_parts.append(f"⭐ {quality_score}分")

        elements.append({
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": "  |  ".join(meta_parts),
            },
        })

        # 2. 分割线
        elements.append({"tag": "hr"})

        # 3. 内容摘要
        content_preview = content_zh[:500] + "..." if len(content_zh) > 500 else content_zh
        elements.append({
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": content_preview,
            },
        })

        # 4. 为什么值得关注
        if why_it_matters_zh:
            elements.append({"tag": "hr"})
            elements.append({
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": f"💡 **为什么值得关注**\n{why_it_matters_zh[:300]}",
                },
            })

        # 5. 影响分析（如果有）
        impact_items = []
        if research_impact:
            impact_items.append(f"🔬 研究: {research_impact[:100]}")
        if product_impact:
            impact_items.append(f"🛠️ 产品: {product_impact[:100]}")
        if market_impact:
            impact_items.append(f"📊 市场: {market_impact[:100]}")

        if impact_items:
            elements.append({
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": "\n".join(impact_items),
                },
            })

        # 6. 主题标签
        if topics:
            tag_text = " ".join([f"`{t}`" for t in topics[:6]])
            elements.append({
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": f"🏷️ {tag_text}",
                },
            })

        # 7. 操作按钮
        elements.append({"tag": "hr"})

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
                "text": {"tag": "plain_text", "content": "🖥️ 控制台"},
                "url": f"{self.dashboard_url}/events",
                "type": "default",
            })

        elements.append({"tag": "action", "actions": actions})

        # 8. 底部时间戳
        now_beijing = datetime.now(BEIJING_TZ).strftime("%Y/%m/%d %H:%M")
        elements.append({
            "tag": "note",
            "elements": [
                {
                    "tag": "plain_text",
                    "content": f"AI Radar · {now_beijing}",
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
                        "tag": "lark_md",
                        "content": f"{style['emoji']} **{title[:80]}{'...' if len(title) > 80 else ''}**",
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