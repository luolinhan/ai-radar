"""
评分引擎 - 对事件进行多维度评分
"""

import logging
from collections.abc import Iterable
from typing import Dict, Any, List, Optional
from uuid import UUID, uuid4
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class ScoringEngine:
    """评分引擎"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def score_event(self, event: Any, targets: List[Dict] = None) -> Dict:
        """
        对事件进行评分
        
        Args:
            event: Event对象
            targets: 标的列表（可选）
            
        Returns:
            评分结果字典
        """
        content = event.content_raw or ""
        content_zh = event.content_zh or ""
        title = event.title or ""
        
        # 1. 来源可靠性评分 (0-10)
        source_score = self._score_source(event.source, event.entity_id)
        
        # 2. 新意度评分 (0-10)
        novelty_score = self._score_novelty(event, content, content_zh)
        
        # 3. 意外度评分 (0-10)
        surprise_score = self._score_surprise(content, content_zh, title)
        
        # 4. 可交易性评分 (0-10)
        tradability_score = self._score_tradability(event, targets)
        
        # 5. 信息置信度评分 (0-10)
        confidence_score = self._score_confidence(event, content)
        
        # 计算综合评分
        final_score = self._calculate_final_score(
            source_score, novelty_score, surprise_score,
            tradability_score, confidence_score
        )
        
        # 生成评分原因
        scoring_reason = self._generate_scoring_reason(
            source_score, novelty_score, surprise_score,
            tradability_score, confidence_score, final_score
        )
        
        # 判断是否高优先级
        is_high_priority = final_score >= 7.0
        
        # 判断是否可操作
        has_targets = bool(targets and len(targets) > 0)
        is_actionable = (
            final_score >= 6.0 and
            tradability_score >= 5.0 and
            has_targets
        )
        
        return {
            "source_score": source_score,
            "novelty_score": novelty_score,
            "surprise_score": surprise_score,
            "tradability_score": tradability_score,
            "confidence_score": confidence_score,
            "final_score": final_score,
            "scoring_reason_zh": scoring_reason,
            "is_high_priority": is_high_priority,
            "is_actionable": is_actionable,
            "key_factors": self._extract_key_factors(event, content),
        }
    
    def _score_source(self, source: str, entity_id: str) -> float:
        """来源可靠性评分"""
        # 高可靠性来源
        high_reliability = ["github", "rss"]
        medium_reliability = ["x", "twitter"]
        low_reliability = ["web", "unknown"]
        
        # 高优先级实体加分
        high_priority_entities = [
            "openai", "anthropic", "google-deepmind", "nvidia", 
            "microsoft-ai", "meta-ai", "xai", "google-ai"
        ]
        
        base_score = 5.0
        
        if source in high_reliability:
            base_score = 8.0
        elif source in medium_reliability:
            base_score = 6.0
        elif source in low_reliability:
            base_score = 5.0
        
        if entity_id and entity_id.lower() in high_priority_entities:
            base_score = min(10.0, base_score + 1.5)
        
        return base_score
    
    def _score_novelty(self, event: Any, content: str, content_zh: str) -> float:
        """新意度评分"""
        # 检查是否重复叙事
        novelty_keywords = [
            "首次", "first", "新", "new", "突破", "breakthrough",
            "发布", "launch", "推出", "release", "创新", "innovation",
            "独家", "exclusive", "原创", "original",
        ]
        
        repeat_keywords = [
            "重新", "re-", "更新", "update", "修正", "fix",
            "再次", "again", "续", "continued",
        ]
        
        combined = f"{content} {content_zh}".lower()
        
        novelty_count = sum(1 for kw in novelty_keywords if kw in combined)
        repeat_count = sum(1 for kw in repeat_keywords if kw in combined)
        
        score = 5.0 + novelty_count * 0.8 - repeat_count * 1.0
        
        # 检查时间是否近期首次出现
        if event.published_at:
            recent_events = self._check_recent_similar_events(
                event.entity_id, event.published_at
            )
            if recent_events > 3:
                score -= 1.5
            elif recent_events > 1:
                score -= 0.5
        
        return max(0, min(10, score))
    
    def _score_surprise(self, content: str, content_zh: str, title: str) -> float:
        """意外度评分"""
        surprise_keywords = [
            "意外", "unexpected", "surprise", "超预期", "beat",
            "震惊", "shock", "突然", "sudden", "暴跌", "plunge",
            "暴涨", "surge", "紧急", "urgent", "突发", "breaking",
        ]
        
        expected_keywords = [
            "预期", "expected", "计划", "planned", "如期", "as expected",
            "符合", "in line", "常规", "routine",
        ]
        
        combined = f"{content} {content_zh} {title}".lower()
        
        surprise_count = sum(1 for kw in surprise_keywords if kw in combined)
        expected_count = sum(1 for kw in expected_keywords if kw in combined)
        
        score = 5.0 + surprise_count * 1.2 - expected_count * 0.8
        
        return max(0, min(10, score))
    
    def _score_tradability(self, event: Any, targets: List[Dict]) -> float:
        """可交易性评分"""
        score = 5.0
        
        # 有明确标的加分
        if targets and len(targets) > 0:
            score += min(3.0, len(targets) * 0.5)
            
            # 有直接关系标的额外加分
            direct_targets = [t for t in targets if t.get("relation_type") == "direct"]
            if direct_targets:
                score += 1.0
        
        # 有tickers字段加分
        if event.tickers and len(event.tickers) > 0:
            score += 1.0
        
        # 有明确影响说明加分
        if event.market_impact or event.why_it_matters_zh:
            score += 1.0
        
        # 内容长度适中加分
        content_len = len(event.content_raw or "")
        if content_len >= 200:
            score += 0.5
        
        return min(10, score)
    
    def _score_confidence(self, event: Any, content: str) -> float:
        """信息置信度评分"""
        score = 5.0
        
        # 有URL来源加分
        if event.url:
            score += 1.0
            
            # 官方来源额外加分
            official_domains = [
                "openai.com", "anthropic.com", "google.com", "nvidia.com",
                "microsoft.com", "meta.com", "github.com", "arxiv.org"
            ]
            if any(domain in event.url.lower() for domain in official_domains):
                score += 1.5
        
        # 内容完整性加分
        if event.title:
            score += 0.5
        if event.content_zh:
            score += 0.5
        if event.companies or event.products:
            score += 0.5
        
        return min(10, score)
    
    def _calculate_final_score(self, source: float, novelty: float, 
                                surprise: float, tradability: float,
                                confidence: float) -> float:
        """计算综合评分"""
        # 加权平均
        weights = {
            "source": 0.15,
            "novelty": 0.25,
            "surprise": 0.25,
            "tradability": 0.20,
            "confidence": 0.15,
        }
        
        final = (
            source * weights["source"] +
            novelty * weights["novelty"] +
            surprise * weights["surprise"] +
            tradability * weights["tradability"] +
            confidence * weights["confidence"]
        )
        
        return round(final, 1)
    
    def _generate_scoring_reason(self, source: float, novelty: float,
                                   surprise: float, tradability: float,
                                   confidence: float, final: float) -> str:
        """生成评分原因"""
        reasons = []
        
        if source >= 8:
            reasons.append("来源可靠")
        elif source >= 6:
            reasons.append("来源较可靠")
        
        if novelty >= 7:
            reasons.append("内容新颖")
        elif novelty < 4:
            reasons.append("内容重复")
        
        if surprise >= 7:
            reasons.append("超出预期")
        
        if tradability >= 7:
            reasons.append("具备交易价值")
        elif tradability < 4:
            reasons.append("缺乏明确标的")
        
        if confidence >= 8:
            reasons.append("信息完整")
        
        level = "高" if final >= 7 else "中" if final >= 5 else "低"
        
        return f"综合评分{level}（{final}分）：{'，'.join(reasons)}"
    
    def _extract_key_factors(self, event: Any, content: str) -> List[str]:
        """提取关键因素"""
        raw_groups = [
            (event.companies or [])[:3],
            (event.products or [])[:2],
            (event.tickers or [])[:2],
            (event.topics or [])[:2],
        ]

        factors: List[str] = []
        seen = set()
        for group in raw_groups:
            for value in self._flatten_factor_values(group):
                text = value.strip()
                if not text:
                    continue
                key = text.lower()
                if key in seen:
                    continue
                seen.add(key)
                factors.append(text)
                if len(factors) >= 5:
                    return factors

        return factors

    def _flatten_factor_values(self, value: Any) -> List[str]:
        """将 JSON 字段中的嵌套值规整为字符串列表。"""
        if value is None:
            return []

        if isinstance(value, str):
            return [value]

        if isinstance(value, dict):
            items: List[str] = []
            for item in value.values():
                items.extend(self._flatten_factor_values(item))
            return items

        if isinstance(value, Iterable):
            items: List[str] = []
            for item in value:
                items.extend(self._flatten_factor_values(item))
            return items

        return [str(value)]
    
    def _check_recent_similar_events(self, entity_id: str, published_at: datetime) -> int:
        """检查近期相似事件数量"""
        from models import Event
        
        lookback = published_at - timedelta(days=7)
        
        count = self.db.query(Event).filter(
            Event.entity_id == entity_id,
            Event.published_at >= lookback,
            Event.published_at < published_at
        ).count()
        
        return count
    
    def save_score(self, event_id: UUID, score: Dict) -> None:
        """保存评分到数据库"""
        from models_v2 import EventScoreDetail

        key_factors = score.get("key_factors") or None
        
        detail = EventScoreDetail(
            id=uuid4(),
            event_id=event_id,
            source_score=score["source_score"],
            novelty_score=score["novelty_score"],
            surprise_score=score["surprise_score"],
            tradability_score=score["tradability_score"],
            confidence_score=score["confidence_score"],
            final_score=score["final_score"],
            scoring_reason_zh=score["scoring_reason_zh"],
            key_factors=key_factors,
            is_high_priority=score["is_high_priority"],
            is_actionable=score["is_actionable"],
        )
        self.db.add(detail)
        try:
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise
