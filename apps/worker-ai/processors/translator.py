"""
翻译器 - 使用AI API进行翻译
"""

import json
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
                            "enable_thinking": False,
                            "temperature": 0.1,
                            "max_tokens": 1800,
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

    def translate_batch(self, items: list[dict]) -> Optional[dict[str, str]]:
        """
        批量翻译内容到中文。

        Args:
            items: [{"id": "...", "text": "..."}]

        Returns:
            id -> translation 映射；失败时返回None
        """
        normalized_items = []
        for item in items:
            item_id = str(item.get("id", "")).strip()
            text = str(item.get("text", "")).strip()
            if not item_id or not text:
                continue
            normalized_items.append({"id": item_id, "text": text})

        if not normalized_items:
            return {}

        payload = json.dumps(normalized_items, ensure_ascii=False)
        prompt = f"""请将下面这些内容批量翻译成简体中文。

要求：
1. 每条内容独立翻译，不要合并、不要总结、不要遗漏
2. 保留链接、@handle、股票代码、代码片段
3. 输出必须是严格 JSON 数组，不要 Markdown，不要代码块，不要额外解释
4. JSON 每个元素格式必须是 {{\"id\": \"原始id\", \"translation\": \"中文译文\"}}
5. 原始 id 必须原样返回，顺序可以不同，但不要丢项
6. translation 请尽量保持单行，换行改为空格，不要保留 HTML 标签

输入：
{payload}

只输出 JSON 数组。"""

        for attempt in range(self.max_retries + 1):
            try:
                with httpx.Client(timeout=self.timeout_seconds) as client:
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
                                {"role": "system", "content": "你是专业中英科技翻译，输出严格 JSON。"},
                                {"role": "user", "content": prompt},
                            ],
                            "enable_thinking": False,
                            "temperature": 0.1,
                            "max_tokens": 4096,
                        },
                    )

                    if response.status_code != 200:
                        logger.error(
                            "批量翻译API错误: status=%s, attempt=%s/%s, body=%s",
                            response.status_code,
                            attempt + 1,
                            self.max_retries + 1,
                            response.text[:300],
                        )
                    else:
                        data = response.json()
                        raw_text = data["choices"][0]["message"]["content"].strip()
                        parsed = self._parse_batch_translation_response(raw_text)
                        if parsed:
                            return parsed
                        logger.error(
                            "批量翻译响应解析失败: attempt=%s/%s, body=%s",
                            attempt + 1,
                            self.max_retries + 1,
                            raw_text[:500],
                        )
            except Exception as e:
                logger.error(
                    "批量翻译失败: attempt=%s/%s, error=%s",
                    attempt + 1,
                    self.max_retries + 1,
                    e,
                )

            if attempt < self.max_retries:
                time.sleep(min(2 ** attempt, 5))

        return None

    def _sanitize_json_string_controls(self, content: str) -> str:
        """
        将 JSON 文本中字符串内部的真实控制字符转义。

        这可以处理模型把多行 markdown 直接塞进 JSON 字符串的情况。
        """
        result = []
        in_string = False
        escaped = False

        for ch in content:
            if not in_string:
                result.append(ch)
                if ch == '"':
                    in_string = True
                continue

            if escaped:
                result.append(ch)
                escaped = False
                continue

            if ch == "\\":
                result.append(ch)
                escaped = True
                continue

            if ch == '"':
                result.append(ch)
                in_string = False
                continue

            if ch == "\r" or ch == "\n":
                result.append("\\n")
                continue

            if ord(ch) < 0x20:
                result.append(f"\\u{ord(ch):04x}")
                continue

            result.append(ch)

        return "".join(result)

    def _parse_batch_translation_response(self, content: str) -> Optional[dict[str, str]]:
        raw = (content or "").strip()
        if not raw:
            return None

        if raw.startswith("```"):
            lines = raw.splitlines()
            if len(lines) >= 3:
                raw = "\n".join(lines[1:-1]).strip()

        try:
            data = json.loads(raw)
        except Exception:
            try:
                data = json.loads(self._sanitize_json_string_controls(raw))
            except Exception:
                start = raw.find("[")
                end = raw.rfind("]")
                if start == -1 or end == -1 or end <= start:
                    return None
                try:
                    data = json.loads(self._sanitize_json_string_controls(raw[start : end + 1]))
                except Exception:
                    return None

        result: dict[str, str] = {}
        if isinstance(data, dict):
            data = data.get("items") or data.get("translations") or []

        if not isinstance(data, list):
            return None

        for item in data:
            if not isinstance(item, dict):
                continue
            item_id = str(item.get("id", "")).strip()
            translation = str(item.get("translation", "")).strip()
            translation = translation.replace("\r\n", "\n").replace("\r", "\n")
            if item_id and translation:
                result[item_id] = translation

        return result or None


def contains_chinese(text: str) -> bool:
    """判断文本是否包含中文字符"""
    return bool(re.search(r"[\u4e00-\u9fff]", text or ""))
