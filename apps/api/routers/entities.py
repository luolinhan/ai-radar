"""
监控对象路由
"""

from uuid import UUID
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from database import get_db
from models import WatchEntity

router = APIRouter()


@router.get("")
async def list_entities(
    entity_type: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    is_active: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """获取监控对象列表"""
    query = db.query(WatchEntity)

    if entity_type:
        query = query.filter(WatchEntity.entity_type == entity_type)
    if priority:
        query = query.filter(WatchEntity.priority == priority)
    if is_active:
        query = query.filter(WatchEntity.is_active == is_active)

    entities = query.all()

    return {
        "total": len(entities),
        "items": [
            {
                "id": str(e.id),
                "entity_type": e.entity_type,
                "name_en": e.name_en,
                "name_zh": e.name_zh,
                "x_handle": e.x_handle,
                "github_handle": e.github_handle,
                "organization": e.organization,
                "priority": e.priority,
            }
            for e in entities
        ],
    }


@router.post("")
async def create_entity(entity: dict, db: Session = Depends(get_db)):
    """创建监控对象"""
    from uuid import uuid4

    new_entity = WatchEntity(
        id=uuid4(),
        entity_type=entity.get("entity_type"),
        name_en=entity.get("name_en"),
        name_zh=entity.get("name_zh"),
        aliases=entity.get("aliases", []),
        x_handle=entity.get("x_handle"),
        github_handle=entity.get("github_handle"),
        website_url=entity.get("website_url"),
        organization=entity.get("organization"),
        priority=entity.get("priority", "P2"),
        keywords=entity.get("keywords", []),
    )

    db.add(new_entity)
    db.commit()

    return {"id": str(new_entity.id), "status": "created"}