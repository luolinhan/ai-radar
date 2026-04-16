"""
Event Service - 事件服务
"""

import os
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import desc, or_

from models import Event
from models_v2 import (
    EventScoreDetail, 
    EventImpactHypothesis, 
    MarketContextSnapshot, 
    RiskAlert,
    EventBacktestResult,
    EntityMarketMap
)
from services.signal_priority import methodology_signal_score, story_signal_score


class EventService:
    """事件服务"""
    
    def __init__(self, db: Session):
        self.db = db

    def get_full_detail(self, event_id: UUID) -> Optional[Dict[str, Any]]:
        """获取事件完整详情"""
        event = self.db.query(Event).filter(Event.event_id == event_id).first()
        if not event:
            return None
        
        score_detail = self.db.query(EventScoreDetail).filter(
            EventScoreDetail.event_id == event_id
        ).first()
        
        impacts = self.db.query(EventImpactHypothesis).filter(
            EventImpactHypothesis.event_id == event_id
        ).all()
        
        market_context = self.db.query(MarketContextSnapshot).filter(
            MarketContextSnapshot.event_id == event_id
        ).first()
        
        risks = self.db.query(RiskAlert).filter(
            RiskAlert.event_id == event_id
        ).all()
        
        backtests = self.db.query(EventBacktestResult).filter(
            EventBacktestResult.event_id == event_id
        ).all()
        
        targets = self._get_target_mappings(event)
        
        return {
            "event_id": str(event.event_id),
            "source": event.source,
            "source_type": event.source_type,
            "entity_id": event.entity_id,
            "entity_type": event.entity_type,
            "author": event.author,
            "title": event.title,
            "content_raw": event.content_raw,
            "content_zh": event.content_zh,
            "url": event.url,
            "published_at": event.published_at,
            "fetched_at": event.fetched_at,
            "language": event.language,
            "topics": event.topics or [],
            "companies": event.companies or [],
            "products": event.products or [],
            "tickers": event.tickers or [],
            "signals": event.signals or {},
            "alert_level": event.alert_level,
            "alert_reason": event.alert_reason,
            "research_impact": event.research_impact,
            "product_impact": event.product_impact,
            "market_impact": event.market_impact,
            "why_it_matters_zh": event.why_it_matters_zh,
            "targets": targets,
            "impacts": [
                {
                    "symbol": i.symbol,
                    "direction": i.direction,
                    "impact_type": i.impact_type,
                    "hypothesis_text_zh": i.hypothesis_text_zh,
                    "confidence": i.confidence,
                    "time_horizon": i.time_horizon,
                }
                for i in impacts
            ],
            "market_context": self._format_market_context(market_context),
            "score_detail": self._format_score_detail(score_detail),
            "risks": [
                {
                    "risk_type": r.risk_type,
                    "risk_level": r.risk_level,
                    "risk_text_zh": r.risk_text_zh,
                    "action_suggestion": r.action_suggestion,
                }
                for r in risks
            ],
            "backtest_results": [
                {
                    "symbol": b.symbol,
                    "entry_time": b.entry_time,
                    "price_at_entry": b.price_at_entry,
                    "return_1h": b.return_1h,
                    "return_1d": b.return_1d,
                    "max_upside": b.max_upside,
                    "max_drawdown": b.max_drawdown,
                    "result_label": b.result_label,
                }
                for b in backtests
            ],
        }

    def _get_target_mappings(self, event: Event) -> List[Dict]:
        """获取事件的标的映射"""
        targets = []
        entity_maps = self.db.query(EntityMarketMap).filter(
            EntityMarketMap.entity_id == event.entity_id,
            EntityMarketMap.is_active == True
        ).all()
        
        for m in entity_maps:
            targets.append({
                "symbol": m.mapped_symbol,
                "name": m.mapped_name,
                "market": m.market,
                "relation_type": m.relation_type,
                "confidence": m.confidence,
                "notes": m.notes,
            })
        
        if event.companies:
            for company in event.companies:
                company_maps = self.db.query(EntityMarketMap).filter(
                    EntityMarketMap.entity_id == company.lower().replace(" ", "-"),
                    EntityMarketMap.entity_type == "org",
                    EntityMarketMap.is_active == True
                ).all()
                for m in company_maps:
                    if m.mapped_symbol not in [t["symbol"] for t in targets]:
                        targets.append({
                            "symbol": m.mapped_symbol,
                            "name": m.mapped_name,
                            "market": m.market,
                            "relation_type": m.relation_type,
                            "confidence": m.confidence,
                        })
        
        return targets

    def _format_market_context(self, ctx: Optional[MarketContextSnapshot]) -> Optional[Dict]:
        if not ctx:
            return None
        return {
            "market_session": ctx.market_session,
            "us_market_open": ctx.us_market_open,
            "days_to_earnings": ctx.days_to_earnings,
            "has_macro_event_nearby": ctx.has_macro_event_nearby,
            "macro_event_type": ctx.macro_event_type,
            "tradability_hint": ctx.tradability_hint,
            "context_summary_zh": ctx.context_summary_zh,
        }

    def _format_score_detail(self, score: Optional[EventScoreDetail]) -> Optional[Dict]:
        if not score:
            return None
        return {
            "source_score": score.source_score,
            "novelty_score": score.novelty_score,
            "surprise_score": score.surprise_score,
            "tradability_score": score.tradability_score,
            "confidence_score": score.confidence_score,
            "final_score": score.final_score,
            "scoring_reason_zh": score.scoring_reason_zh,
            "is_high_priority": score.is_high_priority,
            "is_actionable": score.is_actionable,
        }

    def get_recommendations(self, limit: int = 10) -> List[Dict]:
        """获取推荐关注的事件"""
        now = datetime.utcnow()
        lookback_hours = max(24, int(os.getenv("RECOMMENDATION_LOOKBACK_HOURS", "144")))
        lookback = now - timedelta(hours=lookback_hours)
        min_score = float(os.getenv("RECOMMENDATION_MIN_SCORE", "6"))
        min_signal = float(os.getenv("RECOMMENDATION_MIN_SIGNAL", "8"))
        
        query = self.db.query(Event).join(
            EventScoreDetail, Event.event_id == EventScoreDetail.event_id
        ).filter(
            Event.published_at >= lookback,
            EventScoreDetail.final_score >= min_score,
            or_(
                EventScoreDetail.is_actionable == True,
                EventScoreDetail.final_score >= 7.0,
            ),
            or_(Event.title.is_(None), ~Event.title.ilike("RT %")),
            ~Event.content_raw.ilike("RT @%"),
            ~Event.content_raw.ilike("Repost:%"),
        ).order_by(
            desc(Event.published_at),
            desc(EventScoreDetail.final_score)
        ).limit(max(limit * 8, 40))
        
        events = query.all()
        
        enriched = []
        for e in events:
            score = self.db.query(EventScoreDetail).filter(
                EventScoreDetail.event_id == e.event_id
            ).first()

            targets = self._get_target_mappings(e)
            
            impacts = self.db.query(EventImpactHypothesis).filter(
                EventImpactHypothesis.event_id == e.event_id
            ).all()
            
            risks = self.db.query(RiskAlert).filter(
                RiskAlert.event_id == e.event_id
            ).first()

            target_symbols = [item["symbol"] for item in targets[:3]]
            signal_score = story_signal_score(
                e,
                final_score=score.final_score if score else 0,
                target_symbols=target_symbols,
            )
            if signal_score < min_signal and (score.final_score if score else 0) < 7.4:
                continue

            enriched.append({
                "event_id": str(e.event_id),
                "title": e.title,
                "summary_zh": (e.why_it_matters_zh or e.content_zh or e.content_raw or "")[:120],
                "final_score": score.final_score if score else 0,
                "signal_score": signal_score,
                "alert_level": e.alert_level,
                "direction": impacts[0].direction if impacts else None,
                "target_symbols": [i.symbol for i in impacts[:3]] or target_symbols,
                "action_suggestion": risks.action_suggestion if risks else "watch",
                "risk_level": risks.risk_level if risks else "medium",
                "published_at": e.published_at,
            })

        enriched.sort(
            key=lambda item: (
                item["signal_score"],
                item["final_score"],
                item["published_at"] or datetime.min,
            ),
            reverse=True,
        )

        recommendations = []
        for item in enriched[:limit]:
            item.pop("signal_score", None)
            recommendations.append(item)
        return recommendations

    def get_methodology_stream(self, limit: int = 20) -> List[Dict]:
        """获取方法论流：偏实战工作流、技巧、提示词和前沿使用方式。"""
        now = datetime.utcnow()
        lookback_hours = max(24, int(os.getenv("METHODOLOGY_LOOKBACK_HOURS", "168")))
        min_signal = float(os.getenv("METHODOLOGY_MIN_SIGNAL", "6.5"))
        lookback = now - timedelta(hours=lookback_hours)

        rows = (
            self.db.query(Event, EventScoreDetail)
            .outerjoin(EventScoreDetail, Event.event_id == EventScoreDetail.event_id)
            .filter(
                Event.published_at >= lookback,
                Event.content_raw.isnot(None),
                or_(Event.title.is_(None), ~Event.title.ilike("RT %")),
                ~Event.content_raw.ilike("RT @%"),
                ~Event.content_raw.ilike("Repost:%"),
            )
            .order_by(desc(Event.published_at))
            .limit(max(limit * 12, 120))
            .all()
        )

        items = []
        for event, score_row in rows:
            final_score = score_row.final_score if score_row else 0
            methodology_score = methodology_signal_score(
                event,
                final_score=final_score,
            )
            if methodology_score < min_signal:
                continue

            impacts = self.db.query(EventImpactHypothesis).filter(
                EventImpactHypothesis.event_id == event.event_id
            ).all()
            mapped_targets = self._get_target_mappings(event)
            target_symbols = [impact.symbol for impact in impacts[:3]] or [
                item["symbol"] for item in mapped_targets[:3]
            ]

            items.append({
                "event_id": str(event.event_id),
                "title": event.title,
                "summary_zh": (event.why_it_matters_zh or event.content_zh or event.content_raw or "")[:180],
                "source": event.source,
                "entity_id": event.entity_id,
                "topics": event.topics or [],
                "target_symbols": target_symbols,
                "published_at": event.published_at,
                "methodology_score": methodology_score,
                "final_score": final_score,
            })

        items.sort(
            key=lambda item: (
                item["methodology_score"],
                item["final_score"],
                item["published_at"] or datetime.min,
            ),
            reverse=True,
        )

        return [
            {
                key: value
                for key, value in item.items()
                if key != "final_score"
            }
            for item in items[:limit]
        ]
