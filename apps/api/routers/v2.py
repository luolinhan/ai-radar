"""
v2 API路由 - 交易辅助系统
"""

from datetime import datetime, timedelta
from uuid import UUID
from typing import Optional, List

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc

from database import get_db
from services.dashboard_service import DashboardService
from services.event_service import EventService
from services.theme_service import ThemeService
from schemas_v2 import (
    DashboardOverview,
    EventFullDetail,
    ThemeDetail,
    ThemeList,
    RecommendationList,
    MethodologyInsightList,
)
from models import Event
from models_v2 import EventBacktestResult, EntityMarketMap

router = APIRouter(prefix="/v1", tags=["v2 - 交易辅助"])


@router.get("/dashboard/overview", response_model=DashboardOverview)
async def get_dashboard_overview(db: Session = Depends(get_db)):
    """获取首页总览数据"""
    service = DashboardService(db)
    return service.get_overview()


@router.get("/events/{event_id}/full", response_model=EventFullDetail)
async def get_event_full_detail(event_id: UUID, db: Session = Depends(get_db)):
    """获取事件完整详情"""
    service = EventService(db)
    result = service.get_full_detail(event_id)
    if not result:
        raise HTTPException(status_code=404, detail="Event not found")
    return result


@router.get("/themes", response_model=ThemeList)
async def get_themes(db: Session = Depends(get_db)):
    """获取主题列表"""
    service = ThemeService(db)
    themes = service.get_list()
    return ThemeList(total=len(themes), items=themes)


@router.get("/themes/{theme_id}", response_model=ThemeDetail)
async def get_theme_detail(theme_id: UUID, db: Session = Depends(get_db)):
    """获取主题详情"""
    service = ThemeService(db)
    result = service.get_detail(theme_id)
    if not result:
        raise HTTPException(status_code=404, detail="Theme not found")
    return result


@router.get("/alerts/recommendations", response_model=RecommendationList)
async def get_recommendations(
    limit: int = Query(10, le=50),
    db: Session = Depends(get_db)
):
    """获取推荐关注的事件"""
    service = EventService(db)
    items = service.get_recommendations(limit=limit)
    return RecommendationList(total=len(items), items=items)


@router.get("/methodology", response_model=MethodologyInsightList)
async def get_methodology_stream(
    limit: int = Query(20, le=50),
    db: Session = Depends(get_db)
):
    """获取方法论流"""
    service = EventService(db)
    items = service.get_methodology_stream(limit=limit)
    return MethodologyInsightList(total=len(items), items=items)


@router.get("/backtests/events")
async def get_event_backtests(
    days: int = Query(7, le=30),
    symbol: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """获取事件回测数据"""
    now = datetime.utcnow()
    since = now - timedelta(days=days)
    query = db.query(EventBacktestResult).filter(EventBacktestResult.entry_time >= since)
    if symbol:
        query = query.filter(EventBacktestResult.symbol == symbol.upper())
    results = query.order_by(desc(EventBacktestResult.entry_time)).limit(100).all()
    return {
        "total": len(results),
        "items": [
            {
                "id": str(r.id),
                "event_id": str(r.event_id),
                "symbol": r.symbol,
                "entry_time": r.entry_time,
                "return_1d": r.return_1d,
                "result_label": r.result_label,
            }
            for r in results
        ],
    }


@router.get("/entities/{entity_id}/full")
async def get_entity_full_detail(
    entity_id: str,
    db: Session = Depends(get_db)
):
    """获取实体完整详情"""
    from models import WatchEntity
    
    entity = db.query(WatchEntity).filter(
        WatchEntity.name_en.ilike(f"%{entity_id}%")
    ).first()
    
    entity_name = None
    if entity:
        entity_name = entity.name_en
    else:
        maps = db.query(EntityMarketMap).filter(
            EntityMarketMap.entity_id == entity_id.lower()
        ).first()
        if maps:
            entity_name = maps.entity_name
        else:
            raise HTTPException(status_code=404, detail="Entity not found")
    
    targets = db.query(EntityMarketMap).filter(
        EntityMarketMap.entity_id == entity_id.lower(),
        EntityMarketMap.is_active == True
    ).all()
    
    week_ago = datetime.utcnow() - timedelta(days=30)
    events = db.query(Event).filter(
        Event.entity_id == entity_id.lower(),
        Event.published_at >= week_ago
    ).order_by(desc(Event.published_at)).limit(10).all()
    
    return {
        "entity_id": entity_id,
        "entity_name": entity_name,
        "mapped_targets": [
            {
                "symbol": t.mapped_symbol,
                "name": t.mapped_name,
                "relation_type": t.relation_type,
                "confidence": t.confidence,
            }
            for t in targets
        ],
        "recent_events": [
            {
                "event_id": str(e.event_id),
                "title": e.title,
                "published_at": e.published_at,
                "alert_level": e.alert_level,
            }
            for e in events
        ],
        "event_count_30d": len(events),
    }
