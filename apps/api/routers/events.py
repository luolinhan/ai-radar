"""
事件路由 - CRUD操作
"""

from datetime import datetime
from uuid import UUID
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from database import get_db
from models import Event
from schemas import EventResponse, EventListResponse

router = APIRouter()


@router.get("", response_model=EventListResponse)
async def list_events(
    source: Optional[str] = Query(None),
    entity_id: Optional[str] = Query(None),
    alert_level: Optional[str] = Query(None),
    limit: int = Query(50, le=200),
    offset: int = Query(0),
    db: Session = Depends(get_db),
):
    """获取事件列表"""
    query = db.query(Event)

    if source:
        query = query.filter(Event.source == source)
    if entity_id:
        query = query.filter(Event.entity_id == entity_id)
    if alert_level:
        query = query.filter(Event.alert_level == alert_level)

    query = query.order_by(Event.published_at.desc())

    total = query.count()
    events = query.offset(offset).limit(limit).all()

    return EventListResponse(
        total=total,
        items=[EventResponse.from_orm(e) for e in events],
    )


@router.get("/{event_id}", response_model=EventResponse)
async def get_event(event_id: UUID, db: Session = Depends(get_db)):
    """获取单个事件详情"""
    event = db.query(Event).filter(Event.event_id == event_id).first()
    if not event:
        return {"error": "Event not found"}
    return EventResponse.from_orm(event)