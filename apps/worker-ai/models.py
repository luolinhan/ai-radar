"""
数据库模型 - 与API共享
"""

from datetime import datetime
from uuid import UUID

from sqlalchemy import Column, String, DateTime, Float, Text, JSON
from sqlalchemy.dialects.postgresql import UUID as PGUUID

from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class Event(Base):
    """事件表"""
    __tablename__ = "events"

    event_id = Column(PGUUID(as_uuid=True), primary_key=True)
    source = Column(String, nullable=False)
    source_type = Column(String, nullable=False)
    entity_type = Column(String, nullable=False)
    entity_id = Column(String, nullable=False)
    author = Column(String)
    title = Column(String)
    content_raw = Column(Text, nullable=False)
    content_zh = Column(Text)
    url = Column(String, nullable=False)
    published_at = Column(DateTime, nullable=False)
    fetched_at = Column(DateTime, default=datetime.utcnow)
    language = Column(String, default="en")

    topics = Column(JSON)
    claims = Column(JSON)
    companies = Column(JSON)
    products = Column(JSON)
    tickers = Column(JSON)
    signals = Column(JSON)

    novelty_score = Column(Float, default=0)
    impact_score = Column(Float, default=0)
    confidence_score = Column(Float, default=0)

    alert_level = Column(String, default="C")
    alert_reason = Column(String)

    cluster_id = Column(PGUUID(as_uuid=True))

    research_impact = Column(Text)
    product_impact = Column(Text)
    market_impact = Column(Text)
    policy_impact = Column(Text)
    why_it_matters_zh = Column(Text)
    what_to_watch_next = Column(Text)

    created_at = Column(DateTime, default=datetime.utcnow)


class Alert(Base):
    """告警记录表"""
    __tablename__ = "alerts"

    id = Column(PGUUID(as_uuid=True), primary_key=True)
    event_id = Column(PGUUID(as_uuid=True))
    alert_level = Column(String)
    sent_at = Column(DateTime)
    channel = Column(String)
    status = Column(String, default="pending")
    error_message = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)