"""
翻译器 - 使用AI API进行翻译
"""

import logging
import re
import time
from typing import Optional

import httpx

logger = logging.getLogger(__name__)


class Translator:
    """AI翻译器"""

    def __init__(
        self,
        api_base_url: str,
        api_key: str,
        model: str = "qwen3.5-plus",
        timeout_seconds: int = 60,
        max_retries: int = 2,
    ):
        self.api_base_url = api_base_url
        self.api_key = api_key
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.max_retries = max(0, max_retries)

    def translate(self, content: str) -> Optional[str]:
        """
        翻译内容到中文

        Args:
            content: 原始内容（通常英文）

        Returns:
            中文翻译结果；失败时返回None
        """
        if not content:
            return ""

        # 构建翻译prompt
        prompt = f"""请将以下内容翻译成简体中文。

要求：
1. 保持专业术语的准确性（如GPT、LLM、Transformer等不需要翻译）
2. 保留原文中的链接、@handle、股票代码等
3. 翻译要流畅自然，适合中文读者阅读
4. 不要省略关键信息，不要总结，完整翻译

原文：
{content}

请直接输出翻译结果，不要添加任何解释或说明。"""

        for attempt in range(self.max_retries + 1):
            try:
                with httpx.Client(timeout=self.timeout_seconds) as client:
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
                                {"role": "system", "content": "你是专业中英科技翻译，输出简体中文译文。"},
                                {"role": "user", "content": prompt},
                            ],
                            "temperature": 0.1,
                            "max_tokens": 2600,
                        },
                    )

                    if response.status_code == 200:
                        data = response.json()
                        translated = data["choices"][0]["message"]["content"]
                        translated = translated.strip()
                        if not translated:
                            logger.warning("翻译结果为空")
                            return None
                        return translated

                    logger.error(
                        "翻译API错误: status=%s, attempt=%s/%s, body=%s",
                        response.status_code,
                        attempt + 1,
                        self.max_retries + 1,
                        response.text[:300],
                    )
            except Exception as e:
                logger.error(
                    "翻译失败: attempt=%s/%s, error=%s",
                    attempt + 1,
                    self.max_retries + 1,
                    e,
                )

            if attempt < self.max_retries:
                time.sleep(min(2 ** attempt, 5))

        return None


def contains_chinese(text: str) -> bool:
    """判断文本是否包含中文字符"""
    return bool(re.search(r"[\u4e00-\u9fff]", text or ""))
