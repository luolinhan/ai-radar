"""
数据库模型定义
"""

from datetime import datetime
from uuid import UUID

from sqlalchemy import Column, String, DateTime, Float, Text, JSON, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID as PGUUID

from database import Base


class WatchEntity(Base):
    """监控对象表"""
    __tablename__ = "watch_entities"

    id = Column(PGUUID(as_uuid=True), primary_key=True)
    entity_type = Column(String, nullable=False)  # person, org, topic
    name_en = Column(String, nullable=False)
    name_zh = Column(String)
    aliases = Column(JSON)  # 别名列表
    x_handle = Column(String)  # Twitter账号
    github_handle = Column(String)
    website_url = Column(String)
    organization = Column(String)
    priority = Column(String, default="P2")  # P0, P1, P2
    keywords = Column(JSON)  # 补充关键词
    is_active = Column(String, default="true")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class SourceRule(Base):
    """采集规则表"""
    __tablename__ = "source_rules"

    id = Column(PGUUID(as_uuid=True), primary_key=True)
    source = Column(String, nullable=False)  # x, github, rss, arxiv等
    entity_id = Column(PGUUID(as_uuid=True))
    query = Column(String)  # 查询条件
    schedule = Column(String, default="*/30 * * * *")  # cron表达式
    is_active = Column(String, default="true")
    last_run = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)


class Event(Base):
    """事件表 - 存储CanonicalEvent"""
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

    # 结构化信息
    topics = Column(JSON)
    claims = Column(JSON)
    companies = Column(JSON)
    products = Column(JSON)
    tickers = Column(JSON)
    signals = Column(JSON)

    # 评分
    novelty_score = Column(Float, default=0)
    impact_score = Column(Float, default=0)
    confidence_score = Column(Float, default=0)

    # 告警
    alert_level = Column(String, default="C")
    alert_reason = Column(String)

    # 聚类
    cluster_id = Column(PGUUID(as_uuid=True))

    # 影响分析
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
    channel = Column(String)  # feishu, email
    status = Column(String, default="pending")  # pending, sent, failed, skipped
    error_message = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
