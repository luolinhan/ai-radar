"""
Theme Service - 主题服务
"""

from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import desc

from models import Event
from models_v2 import ThemeCluster, EventScoreDetail


class ThemeService:
    """主题服务"""
    
    def __init__(self, db: Session):
        self.db = db

    def get_list(self) -> List[Dict[str, Any]]:
        """获取主题列表"""
        themes = self.db.query(ThemeCluster).filter(
            ThemeCluster.is_active == True
        ).order_by(
            desc(ThemeCluster.event_count_7d),
            desc(ThemeCluster.avg_score)
        ).all()
        
        return [
            {
                "id": str(t.id),
                "name_en": t.name_en,
                "name_zh": t.name_zh,
                "description": t.description,
                "related_symbols": t.related_symbols or [],
                "event_count_7d": t.event_count_7d,
                "event_count_30d": t.event_count_30d,
                "heat_trend": t.heat_trend,
                "avg_score": t.avg_score,
                "hit_rate": t.hit_rate,
            }
            for t in themes
        ]

    def get_detail(self, theme_id: UUID) -> Optional[Dict[str, Any]]:
        """获取主题详情"""
        theme = self.db.query(ThemeCluster).filter(
            ThemeCluster.id == theme_id,
            ThemeCluster.is_active == True
        ).first()
        
        if not theme:
            return None
        
        recent_events = self._get_theme_events(theme.name_en, limit=10)
        
        return {
            "id": str(theme.id),
            "name_en": theme.name_en,
            "name_zh": theme.name_zh,
            "description": theme.description,
            "related_symbols": theme.related_symbols or [],
            "event_count_7d": theme.event_count_7d,
            "event_count_30d": theme.event_count_30d,
            "heat_trend": theme.heat_trend,
            "avg_score": theme.avg_score,
            "hit_rate": theme.hit_rate,
            "recent_events": recent_events,
        }

    def _get_theme_events(self, theme_name: str, limit: int = 10) -> List[Dict]:
        """获取主题相关事件"""
        week_ago = datetime.utcnow() - timedelta(days=7)
        
        query = self.db.query(Event).join(
            EventScoreDetail, Event.event_id == EventScoreDetail.event_id, isouter=True
        ).filter(
            Event.published_at >= week_ago,
            Event.topics != None
        ).order_by(
            desc(EventScoreDetail.final_score),
            desc(Event.published_at)
        ).limit(50)
        
        events = query.all()
        
        matched_events = []
        for e in events:
            topics = e.topics or []
            if any(self._topic_matches_theme(t, theme_name) for t in topics):
                matched_events.append({
                    "event_id": str(e.event_id),
                    "title": e.title,
                    "published_at": e.published_at,
                    "alert_level": e.alert_level,
                    "source": e.source,
                    "score": self._get_event_score(e.event_id),
                })
        
        return matched_events[:limit]

    def _topic_matches_theme(self, topic: str, theme_name: str) -> bool:
        """判断topic是否匹配theme"""
        theme_lower = theme_name.lower()
        topic_lower = topic.lower() if topic else ""
        if not topic_lower:
            return False

        if (
            topic_lower == theme_lower
            or theme_lower in topic_lower
            or topic_lower in theme_lower
        ):
            return True

        mapping = {
            "frontier-models": ["gpt", "claude", "gemini", "llama", "llm", "model", "openai", "anthropic"],
            "ai-infra": ["gpu", "chip", "nvidia", "infrastructure", "training", "inference"],
            "gpu-compute": ["gpu", "nvidia", "compute", "chip", "h100", "a100"],
            "data-center": ["data center", "server", "cloud"],
            "ai-applications": ["application", "copilot", "chatgpt", "product"],
            "open-source-models": ["open source", "llama", "huggingface", "mistral"],
            "policy-regulation": ["policy", "regulation", "safety", "law"],
            "ai-safety": ["safety", "alignment", "risk"],
            "funding-ma": ["funding", "acquisition", "merger", "investment"],
            "chip-supply-chain": ["tsmc", "asml", "semiconductor", "supply chain"],
        }
        
        keywords = mapping.get(theme_lower, [])
        return any(kw in topic_lower for kw in keywords)

    def _get_event_score(self, event_id) -> float:
        """获取事件评分"""
        score = self.db.query(EventScoreDetail).filter(
            EventScoreDetail.event_id == event_id
        ).first()
        return score.final_score if score else 0
