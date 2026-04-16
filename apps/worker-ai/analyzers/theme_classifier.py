"""
主题分类器 - 将事件归入稳定主题簇，供 dashboard 和推送使用。
"""

from __future__ import annotations

import logging
from collections import defaultdict
from collections.abc import Iterable
from typing import Any, Optional

logger = logging.getLogger(__name__)


THEME_RULES = {
    "frontier-models": {
        "keywords": [
            "gpt", "claude", "gemini", "llama", "qwen", "kimi", "doubao",
            "deepseek", "mistral", "grok", "foundation model", "frontier model",
            "reasoning model", "multimodal model", "moe",
        ],
        "entities": [
            "openai", "anthropic", "google-deepmind", "google-ai", "meta-ai",
            "xai", "qwen", "moonshot-ai", "zhipu-ai", "deepseek", "mistral",
        ],
        "symbols": ["MSFT", "GOOGL", "META", "NVDA", "BABA"],
    },
    "ai-infra": {
        "keywords": [
            "inference", "training", "runtime", "cuda", "cluster", "compute",
            "infrastructure", "serving", "throughput", "latency", "data pipeline",
            "agentic ai", "server", "cloud ai",
        ],
        "entities": ["nvidia", "aws-ai", "microsoft-ai", "databricks-ai", "huggingface"],
        "symbols": ["NVDA", "AMD", "AVGO", "SMCI", "ARM"],
    },
    "gpu-compute": {
        "keywords": [
            "gpu", "tensor core", "h100", "h200", "b200", "blackwell",
            "accelerator", "compute card", "nvlink", "grace blackwell",
        ],
        "entities": ["nvidia", "amd", "arm", "intel"],
        "symbols": ["NVDA", "AMD", "INTC", "SMCI", "MU"],
    },
    "data-center": {
        "keywords": [
            "data center", "datacenter", "rack", "power", "cooling", "server room",
            "colocation", "energy", "factory", "ai factory",
        ],
        "entities": ["aws-ai", "microsoft-ai", "google-ai", "nvidia"],
        "symbols": ["EQIX", "DLR", "AMZN", "MSFT", "GOOGL"],
    },
    "ai-applications": {
        "keywords": [
            "copilot", "assistant", "agent", "workflow", "workspace", "search",
            "app", "video generation", "creative tool", "office", "browser", "consumer ai",
            "prompt", "prompting", "use case", "tutorial", "guide", "playbook",
            "claude code", "vibe coding", "automation",
        ],
        "entities": ["openai", "google-ai", "microsoft-ai", "moonshot-ai", "xai", "perplexity"],
        "symbols": ["MSFT", "GOOGL", "AAPL", "CRM", "NOW"],
    },
    "open-source-models": {
        "keywords": [
            "open source", "gguf", "hugging face", "huggingface", "weights",
            "community", "apache 2.0", "model card", "checkpoint", "oss model",
        ],
        "entities": ["huggingface", "meta-llama", "ollama", "mistral"],
        "symbols": ["META", "NVDA", "MSFT"],
    },
    "policy-regulation": {
        "keywords": [
            "policy", "regulation", "compliance", "government", "executive order",
            "white house", "eu ai act", "监管", "法规", "政策",
        ],
        "entities": [],
        "symbols": ["MSFT", "GOOGL", "META", "NVDA"],
    },
    "ai-safety": {
        "keywords": [
            "safety", "alignment", "risk", "eval", "red team", "guardrail",
            "harmlessness", "security", "misuse",
        ],
        "entities": ["anthropic", "openai", "google-deepmind"],
        "symbols": ["MSFT", "GOOGL"],
    },
    "funding-ma": {
        "keywords": [
            "funding", "valuation", "acquisition", "acquire", "merger", "m&a",
            "investment", "investor", "raise", "round", "seed", "series a",
            "series b", "ipo",
        ],
        "entities": ["sequoia", "a16z", "benchmark"],
        "symbols": ["NVDA", "MSFT", "GOOGL", "AMZN"],
    },
    "chip-supply-chain": {
        "keywords": [
            "semiconductor", "foundry", "asml", "tsmc", "wafer", "lithography",
            "chip supply", "packaging", "fab", "hbm", "memory",
        ],
        "entities": ["nvidia", "amd", "intel", "tsmc"],
        "symbols": ["NVDA", "TSM", "ASML", "AMAT", "LRCX"],
    },
}


class ThemeClassifier:
    """基于规则的主题分类器。"""

    def classify_event(self, event: Any, targets: list[dict] | None = None) -> list[str]:
        text = self._build_search_text(event, targets)
        entity_id = str(getattr(event, "entity_id", "") or "").lower()
        tickers = {
            str(item).upper()
            for item in self._flatten_values(getattr(event, "tickers", []) or [])
            if str(item).strip()
        }
        if targets:
            tickers.update(
                str(target.get("symbol", "")).upper()
                for target in targets
                if str(target.get("symbol", "")).strip()
            )

        scores: dict[str, int] = defaultdict(int)
        for theme_name, rule in THEME_RULES.items():
            if entity_id and entity_id in rule["entities"]:
                scores[theme_name] += 4

            symbol_hits = tickers.intersection(set(rule["symbols"]))
            if symbol_hits:
                scores[theme_name] += len(symbol_hits) * 2

            for keyword in rule["keywords"]:
                if keyword in text:
                    scores[theme_name] += 2 if " " in keyword else 1

        ranked = [
            name
            for name, score in sorted(scores.items(), key=lambda item: (-item[1], item[0]))
            if score >= 2
        ]
        return ranked[:3]

    def summarize_why_it_matters(
        self,
        event: Any,
        topics: list[str],
        targets: list[dict] | None = None,
        score: dict[str, Any] | None = None,
        translator: Optional[Any] = None,
    ) -> str | None:
        """生成"为什么值得关注"摘要。优先用 LLM 生成具体可操作内容，失败时回退到模板。"""
        if getattr(event, "why_it_matters_zh", None):
            return event.why_it_matters_zh

        target_symbols = [
            str(target.get("symbol", "")).upper()
            for target in (targets or [])
            if str(target.get("symbol", "")).strip()
        ]
        final_score = score.get("final_score") if score else None
        topic_text = "、".join(topics[:2]) if topics else "AI 主线"
        symbol_text = "、".join(target_symbols[:3]) if target_symbols else "相关标的"

        # 尝试 LLM 生成
        if translator:
            llm_result = self._generate_why_it_matters_llm(
                translator, event, topics, target_symbols, score
            )
            if llm_result:
                return llm_result

        # 模板回退
        if final_score and final_score >= 7:
            return f"该事件同时落在 {topic_text} 主题，且对 {symbol_text} 有较明确映射，具备较高跟踪优先级。"
        if target_symbols:
            return f"该事件落在 {topic_text} 主题，并能映射到 {symbol_text}，适合继续观察后续兑现情况。"
        if topics:
            return f"该事件可归入 {topic_text} 主题，适合用于观察近期叙事热度是否继续累积。"
        return None

    def _generate_why_it_matters_llm(
        self,
        translator: Any,
        event: Any,
        topics: list[str],
        target_symbols: list[str],
        score: dict[str, Any] | None = None,
    ) -> str | None:
        """用 LLM 生成具体的、可操作的事件摘要。"""
        logger.info("LLM 生成 why_it_matters 开始: event=%s", str(getattr(event, "event_id", "?"))[:8])
        try:
            title = (event.title or "").strip()
            content = (event.content_zh or event.content_raw or "").strip()
            if len(content) > 1500:
                content = content[:1500] + "..."

            entity_id = getattr(event, "entity_id", "") or ""
            source = getattr(event, "source", "") or ""

            symbols_hint = f"、".join(target_symbols[:3]) if target_symbols else "无明确标的"
            topics_hint = "、".join(topics[:3]) if topics else "未分类"
            score_hint = f"综合评分 {score.get('final_score', 0) if score else 0}/10" if score else ""

            prompt = f"""你是一个AI投资分析助手。请基于以下事件信息，用2-3句简体中文说明"这个事件为什么值得关注，对什么标的或方向有什么影响"。

要求：
1. 不要说"该事件可归入XX主题"之类的模板话
2. 给出具体、可操作的分析：涉及哪些公司/产品、对哪些标的有什么方向的影响、短期还是长期
3. 如果事件有明确标的，说明方向（利好/利空/中性）和理由
4. 控制在80字以内，中文
5. 直接输出分析，不要加"分析："前缀

事件标题：{title}
事件来源：{source} / {entity_id}
涉及主题：{topics_hint}
关联标的：{symbols_hint}
{score_hint}

事件内容（中文翻译）：
{content}

请直接输出你的分析："""

            result = translator.analyze(
                system_prompt="你是AI投资分析助手，用简体中文分析事件的投资价值。",
                user_prompt=prompt,
                max_tokens=300,
                temperature=0.3,
            )
            if result and len(result.strip()) > 10:
                logger.info("LLM 生成 why_it_matters 成功: event=%s, len=%d", str(getattr(event, "event_id", "?"))[:8], len(result.strip()))
                return result.strip()
            logger.warning("LLM 生成 why_it_matters 返回空或太短: event=%s, result=%s", str(getattr(event, "event_id", "?"))[:8], repr(result)[:100] if result else "None")
            return None
        except Exception as e:
            logger.warning("LLM 生成 why_it_matters 失败: %s", e)
            return None

    def _build_search_text(self, event: Any, targets: list[dict] | None = None) -> str:
        parts = [
            getattr(event, "entity_id", "") or "",
            getattr(event, "title", "") or "",
            getattr(event, "content_zh", "") or "",
            getattr(event, "content_raw", "") or "",
            getattr(event, "why_it_matters_zh", "") or "",
        ]
        parts.extend(self._flatten_values(getattr(event, "companies", []) or []))
        parts.extend(self._flatten_values(getattr(event, "products", []) or []))
        parts.extend(self._flatten_values(getattr(event, "topics", []) or []))
        parts.extend(self._flatten_values(getattr(event, "tickers", []) or []))

        if targets:
            for target in targets:
                parts.extend(
                    [
                        str(target.get("symbol", "") or ""),
                        str(target.get("name", "") or ""),
                        str(target.get("relation_type", "") or ""),
                    ]
                )

        return " ".join(str(part).lower() for part in parts if str(part).strip())

    def _flatten_values(self, value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            return [value]
        if isinstance(value, dict):
            result: list[str] = []
            for nested in value.values():
                result.extend(self._flatten_values(nested))
            return result
        if isinstance(value, Iterable):
            result: list[str] = []
            for nested in value:
                result.extend(self._flatten_values(nested))
            return result
        return [str(value)]
