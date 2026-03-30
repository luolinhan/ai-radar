"""
翻译器 - 使用AI API进行翻译
"""

import logging
import httpx

logger = logging.getLogger(__name__)


class Translator:
    """AI翻译器"""

    def __init__(self, api_base_url: str, api_key: str, model: str = "qwen3.5-plus"):
        self.api_base_url = api_base_url
        self.api_key = api_key
        self.model = model

    def translate(self, content: str) -> str:
        """
        翻译内容到中文

        Args:
            content: 原始内容（通常英文）

        Returns:
            中文翻译结果
        """
        if not content:
            return ""

        # 构建翻译prompt
        prompt = f"""请将以下内容翻译成中文。

要求：
1. 保持专业术语的准确性（如GPT、LLM、Transformer等不需要翻译）
2. 保留原文中的链接、@handle、股票代码等
3. 翻译要流畅自然，适合中文读者阅读

原文：
{content}

请直接输出翻译结果，不要添加任何解释或说明。"""

        try:
            with httpx.Client(timeout=60) as client:
                # API URL已经包含/v1，直接拼接
                url = f"{self.api_base_url}/chat/completions"
                response = client.post(
                    url,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": self.model,
                        "messages": [
                            {"role": "user", "content": prompt}
                        ],
                        "temperature": 0.3,
                        "max_tokens": 2000,
                    },
                )

                if response.status_code == 200:
                    data = response.json()
                    translated = data["choices"][0]["message"]["content"]
                    return translated.strip()
                else:
                    logger.error(f"翻译API错误: {response.status_code}")
                    return content  # 返回原文作为fallback

        except Exception as e:
            logger.error(f"翻译失败: {e}")
            return content  # 返回原文作为fallback