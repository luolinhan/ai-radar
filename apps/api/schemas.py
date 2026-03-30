"""
API响应模型
"""

from datetime import datetime
from uuid import UUID
from typing import Optional, List, Any

from pydantic import BaseModel, field_validator


class EventResponse(BaseModel):
    """事件响应模型"""
    event_id: UUID
    source: str
    source_type: str
    entity_type: str
    entity_id: str
    author: Optional[str] = None
    title: Optional[str] = None
    content_raw: str
    content_zh: Optional[str] = None
    url: str
    published_at: datetime
    fetched_at: datetime
    language: str = "en"
    topics: List[str] = []
    claims: List[str] = []
    companies: List[str] = []
    products: List[str] = []
    tickers: List[str] = []
    signals: List[str] = []
    novelty_score: float = 0
    impact_score: float = 0
    confidence_score: float = 0
    alert_level: str = "C"
    alert_reason: Optional[str] = None
    cluster_id: Optional[UUID] = None
    research_impact: Optional[str] = None
    product_impact: Optional[str] = None
    market_impact: Optional[str] = None
    policy_impact: Optional[str] = None
    why_it_matters_zh: Optional[str] = None
    what_to_watch_next: Optional[str] = None

    @field_validator('topics', 'claims', 'companies', 'products', 'tickers', 'signals', mode='before')
    @classmethod
    def none_to_list(cls, v: Any) -> List[str]:
        if v is None:
            return []
        return v

    class Config:
        from_attributes = True


class EventListResponse(BaseModel):
    """事件列表响应"""
    total: int
    items: List[EventResponse]