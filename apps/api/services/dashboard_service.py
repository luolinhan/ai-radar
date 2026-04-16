"""
Dashboard Service - 首页总览服务
"""

from datetime import datetime, timedelta
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from models import Event, Alert
from models_v2 import EventScoreDetail, ThemeCluster, EventBacktestResult
from services.signal_priority import story_signal_score


class DashboardService:
    """首页总览服务"""
    
    def __init__(self, db: Session):
        self.db = db

    def get_overview(self) -> Dict[str, Any]:
        """获取首页总览数据"""
        now = datetime.utcnow()
        today_start = now - timedelta(hours=24)
        week_start = now - timedelta(days=7)
        
        top_events = self._get_top_events(today_start, limit=5)
        alert_stats = self._get_alert_stats(today_start)
        recent_alerts = self._get_recent_alerts(limit=5)
        hot_themes = self._get_hot_themes(week_start, limit=6)
        backtest_summary = self._get_backtest_summary(week_start)
        watching_events = self._get_watching_events(today_start, limit=5)
        
        return {
            "top_events": top_events,
            "top_events_count": len(top_events),
            "alert_stats": alert_stats,
            "recent_alerts": recent_alerts,
            "hot_themes": hot_themes,
            "backtest_summary": backtest_summary,
            "watching_events": watching_events,
            "date_range": "过去24小时",
            "last_updated": now,
        }

    def _get_top_events(self, since: datetime, limit: int = 5) -> List[Dict]:
        """获取今日重点事件"""
        query = self.db.query(Event).join(
            EventScoreDetail, Event.event_id == EventScoreDetail.event_id, isouter=True
        ).filter(
            Event.published_at >= since,
            Event.content_raw.isnot(None)
        ).order_by(
            desc(EventScoreDetail.final_score),
            desc(Event.published_at)
        ).limit(max(limit * 10, 40))
        
        events = query.all()
        ranked = []
        for e in events:
            score = self._get_event_score(e.event_id)
            target_symbols = list((e.tickers or [])[:3])
            signal_score = story_signal_score(
                e,
                final_score=score,
                target_symbols=target_symbols,
            )
            ranked.append({
                "event_id": str(e.event_id),
                "title": e.title or "无标题",
                "summary": (e.content_zh or e.content_raw or "")[:150],
                "alert_level": e.alert_level,
                "source": e.source,
                "entity_id": e.entity_id,
                "published_at": e.published_at,
                "score": score,
                "signal_score": signal_score,
            })

        ranked.sort(
            key=lambda item: (
                item["signal_score"],
                item["score"],
                item["published_at"] or datetime.min,
            ),
            reverse=True,
        )

        return [
            {
                key: value
                for key, value in item.items()
                if key != "signal_score"
            }
            for item in ranked[:limit]
        ]

    def _get_event_score(self, event_id) -> float:
        """获取事件评分"""
        score = self.db.query(EventScoreDetail).filter(
            EventScoreDetail.event_id == event_id
        ).first()
        return score.final_score if score else 0

    def _get_alert_stats(self, since: datetime) -> Dict[str, int]:
        """获取告警统计"""
        stats = self.db.query(
            Event.alert_level,
            func.count(Event.event_id)
        ).filter(
            Event.published_at >= since
        ).group_by(Event.alert_level).all()
        
        return {s[0]: s[1] for s in stats}

    def _get_recent_alerts(self, limit: int = 5) -> List[Dict]:
        """获取最近告警"""
        alerts = self.db.query(Alert).filter(
            Alert.status == "sent"
        ).order_by(desc(Alert.sent_at)).limit(limit).all()
        
        result = []
        for a in alerts:
            event = self.db.query(Event).filter(
                Event.event_id == a.event_id
            ).first()
            if event:
                result.append({
                    "event_id": str(event.event_id),
                    "title": event.title or "无标题",
                    "alert_level": a.alert_level,
                    "sent_at": a.sent_at,
                    "source": event.source,
                })
        return result

    def _get_hot_themes(self, since: datetime, limit: int = 6) -> List[Dict]:
        """获取热门主题"""
        themes = self.db.query(ThemeCluster).filter(
            ThemeCluster.is_active == True,
            ThemeCluster.event_count_7d > 0
        ).order_by(
            desc(ThemeCluster.event_count_7d),
            desc(ThemeCluster.avg_score)
        ).limit(limit).all()
        
        return [
            {
                "name_en": t.name_en,
                "name_zh": t.name_zh,
                "event_count_7d": t.event_count_7d,
                "avg_score": t.avg_score,
                "heat_trend": t.heat_trend,
                "related_symbols": t.related_symbols or [],
            }
            for t in themes
        ]

    def _get_backtest_summary(self, since: datetime) -> Dict[str, Any]:
        """获取回测摘要"""
        results = self.db.query(EventBacktestResult).filter(
            EventBacktestResult.entry_time >= since
        ).all()
        
        if not results:
            return {
                "total_count": 0,
                "hit_count": 0,
                "hit_rate": 0,
                "avg_return_1d": 0,
            }
        
        hit_count = sum(1 for r in results if r.result_label == "hit")
        avg_return = sum(r.return_1d or 0 for r in results) / len(results)
        
        return {
            "total_count": len(results),
            "hit_count": hit_count,
            "hit_rate": round(hit_count / len(results) * 100, 1) if results else 0,
            "avg_return_1d": round(avg_return * 100, 2),
        }

    def _get_watching_events(self, since: datetime, limit: int = 5) -> List[Dict]:
        """获取观察中事件"""
        query = self.db.query(Event).join(
            EventScoreDetail, Event.event_id == EventScoreDetail.event_id, isouter=True
        ).filter(
            Event.published_at >= since,
            Event.alert_level == "C",
            EventScoreDetail.final_score >= 5,
            Event.content_raw.isnot(None)
        ).order_by(
            desc(EventScoreDetail.final_score),
            desc(Event.published_at)
        ).limit(max(limit * 10, 40))
        
        events = query.all()
        ranked = []
        for e in events:
            score = self._get_event_score(e.event_id)
            signal_score = story_signal_score(
                e,
                final_score=score,
                target_symbols=list((e.tickers or [])[:3]),
            )
            ranked.append({
                "event_id": str(e.event_id),
                "title": e.title or "无标题",
                "summary": (e.content_zh or e.content_raw or "")[:100],
                "source": e.source,
                "published_at": e.published_at,
                "score": score,
                "signal_score": signal_score,
            })

        ranked.sort(
            key=lambda item: (
                item["signal_score"],
                item["score"],
                item["published_at"] or datetime.min,
            ),
            reverse=True,
        )

        return [
            {
                key: value
                for key, value in item.items()
                if key != "signal_score"
            }
            for item in ranked[:limit]
        ]
