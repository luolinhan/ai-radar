"""
飞书通知器 - 发送事件告警到飞书
"""

import logging
import httpx

logger = logging.getLogger(__name__)


class FeishuNotifier:
    """飞书机器人通知"""

    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url

    def send_event_alert(
        self,
        title: str,
        content_zh: str,
        url: str,
        source: str,
        alert_level: str,
    ) -> bool:
        """
        发送事件告警

        Args:
            title: 标题
            content_zh: 中文内容
            url: 原文链接
            source: 来源
            alert_level: 告警等级

        Returns:
            是否发送成功
        """
        # 构建飞书消息卡片
        level_color = {
            "S": "red",
            "A": "orange",
            "B": "blue",
            "C": "grey",
        }

        message = {
            "msg_type": "interactive",
            "card": {
                "config": {
                    "wide_screen_mode": True,
                },
                "header": {
                    "title": {
                        "tag": "plain_text",
                        "content": f"【{alert_level}级告警】{title}",
                    },
                    "template": level_color.get(alert_level, "blue"),
                },
                "elements": [
                    {
                        "tag": "div",
                        "text": {
                            "tag": "lark_md",
                            "content": content_zh[:500] if len(content_zh) > 500 else content_zh,
                        },
                    },
                    {
                        "tag": "div",
                        "fields": [
                            {
                                "is_short": True,
                                "text": {
                                    "tag": "lark_md",
                                    "content": f"**来源**: {source}",
                                },
                            },
                            {
                                "is_short": True,
                                "text": {
                                    "tag": "lark_md",
                                    "content": f"**等级**: {alert_level}",
                                },
                            },
                        ],
                    },
                    {
                        "tag": "action",
                        "actions": [
                            {
                                "tag": "button",
                                "text": {
                                    "tag": "plain_text",
                                    "content": "查看原文",
                                },
                                "url": url,
                                "type": "primary",
                            },
                        ],
                    },
                ],
            },
        }

        try:
            with httpx.Client(timeout=10) as client:
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