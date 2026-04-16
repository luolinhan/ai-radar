"""
v2 数据模型扩展 - 交易辅助系统
"""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Column, String, DateTime, Float, Text, JSON, Integer, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PGUUID

from database import Base


class EntityMarketMap(Base):
    """实体到交易标的映射表"""
    __tablename__ = "entity_market_map"
    
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    entity_id = Column(String, nullable=False, index=True)
    entity_type = Column(String, nullable=False)
    entity_name = Column(String)
    mapped_symbol = Column(String, nullable=False, index=True)
    mapped_name = Column(String)
    market = Column(String, default="US")
    relation_type = Column(String, nullable=False)
    confidence = Column(Float, default=0.8)
    notes = Column(Text)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class EventImpactHypothesis(Base):
    """事件影响假设表"""
    __tablename__ = "event_impact_hypothesis"
    
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    event_id = Column(PGUUID(as_uuid=True), ForeignKey("events.event_id"), nullable=False, index=True)
    symbol = Column(String, nullable=False, index=True)
    direction = Column(String, nullable=False)
    impact_type = Column(String, nullable=False)
    hypothesis_text_zh = Column(Text)
    confidence = Column(Float, default=0.7)
    time_horizon = Column(String, default="1d")
    reasoning = Column(Text)
    is_validated = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class MarketContextSnapshot(Base):
    """市场上下文快照表"""
    __tablename__ = "market_context_snapshot"
    
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    event_id = Column(PGUUID(as_uuid=True), ForeignKey("events.event_id"), nullable=False, index=True)
    event_time = Column(DateTime, nullable=False)
    market_session = Column(String)
    us_market_open = Column(Boolean, default=False)
    next_earnings_date = Column(DateTime)
    days_to_earnings = Column(Integer)
    earnings_season = Column(Boolean, default=False)
    has_macro_event_nearby = Column(Boolean, default=False)
    macro_event_type = Column(String)
    macro_event_date = Column(DateTime)
    days_to_macro = Column(Integer)
    symbol_price_change_1d = Column(Float)
    sector_price_change_1d = Column(Float)
    index_price_change_1d = Column(Float)
    priced_in_hint = Column(Boolean, default=False)
    priced_in_reason = Column(Text)
    tradability_hint = Column(String)
    context_summary_zh = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)


class EventScoreDetail(Base):
    """事件评分拆解表"""
    __tablename__ = "event_score_detail"
    
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    event_id = Column(PGUUID(as_uuid=True), ForeignKey("events.event_id"), nullable=False, index=True)
    source_score = Column(Float, default=0)
    novelty_score = Column(Float, default=0)
    surprise_score = Column(Float, default=0)
    tradability_score = Column(Float, default=0)
    confidence_score = Column(Float, default=0)
    final_score = Column(Float, default=0)
    scoring_model = Column(String, default="v1")
    scoring_reason_zh = Column(Text)
    key_factors = Column(JSON)
    is_high_priority = Column(Boolean, default=False)
    is_actionable = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class EventBacktestResult(Base):
    """事件回测结果表"""
    __tablename__ = "event_backtest_result"
    
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    event_id = Column(PGUUID(as_uuid=True), ForeignKey("events.event_id"), nullable=False, index=True)
    symbol = Column(String, nullable=False, index=True)
    entry_time = Column(DateTime, nullable=False)
    price_at_entry = Column(Float)
    return_15m = Column(Float)
    return_1h = Column(Float)
    return_1d = Column(Float)
    return_3d = Column(Float)
    return_1w = Column(Float)
    max_upside = Column(Float)
    max_drawdown = Column(Float)
    result_label = Column(String)
    hit_threshold = Column(Float, default=0.02)
    analysis_notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)


class ThemeCluster(Base):
    """主题簇表"""
    __tablename__ = "theme_clusters"
    
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    name_en = Column(String, nullable=False, unique=True)
    name_zh = Column(String)
    description = Column(Text)
    related_entities = Column(JSON)
    related_symbols = Column(JSON)
    event_count_7d = Column(Integer, default=0)
    event_count_30d = Column(Integer, default=0)
    heat_trend = Column(String)
    avg_score = Column(Float, default=0)
    hit_rate = Column(Float)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class RiskAlert(Base):
    """风险提示表"""
    __tablename__ = "risk_alerts"
    
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    event_id = Column(PGUUID(as_uuid=True), ForeignKey("events.event_id"), nullable=False, index=True)
    risk_type = Column(String, nullable=False)
    risk_level = Column(String, default="medium")
    risk_text_zh = Column(Text)
    action_suggestion = Column(String)
    action_reason = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
