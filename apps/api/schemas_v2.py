"""
v2 API响应模型 - 交易辅助系统
"""

from datetime import datetime
from uuid import UUID
from typing import Optional, List, Dict, Any

from pydantic import BaseModel, Field


class TargetMapping(BaseModel):
    """标的映射"""
    symbol: str
    name: Optional[str] = None
    market: Optional[str] = None
    relation_type: str
    confidence: float
    direction: Optional[str] = None
    notes: Optional[str] = None


class ImpactHypothesis(BaseModel):
    """影响假设"""
    symbol: str
    direction: str
    impact_type: str
    hypothesis_text_zh: Optional[str] = None
    confidence: float
    time_horizon: str


class MarketContext(BaseModel):
    """市场上下文"""
    market_session: Optional[str] = None
    us_market_open: bool = False
    days_to_earnings: Optional[int] = None
    has_macro_event_nearby: bool = False
    macro_event_type: Optional[str] = None
    tradability_hint: Optional[str] = None
    context_summary_zh: Optional[str] = None


class ScoreDetail(BaseModel):
    """评分明细"""
    source_score: float = 0
    novelty_score: float = 0
    surprise_score: float = 0
    tradability_score: float = 0
    confidence_score: float = 0
    final_score: float = 0
    scoring_reason_zh: Optional[str] = None
    is_high_priority: bool = False
    is_actionable: bool = False


class RiskAlertItem(BaseModel):
    """风险提示项"""
    risk_type: str
    risk_level: str
    risk_text_zh: Optional[str] = None
    action_suggestion: Optional[str] = None


class BacktestResult(BaseModel):
    """回测结果"""
    symbol: str
    entry_time: datetime
    price_at_entry: Optional[float] = None
    return_1h: Optional[float] = None
    return_1d: Optional[float] = None
    return_3d: Optional[float] = None
    max_upside: Optional[float] = None
    max_drawdown: Optional[float] = None
    result_label: Optional[str] = None


class EventFullDetail(BaseModel):
    """事件完整详情"""
    event_id: UUID
    source: str
    entity_id: str
    title: Optional[str] = None
    content_raw: str
    content_zh: Optional[str] = None
    url: str
    published_at: datetime
    alert_level: str = "C"
    topics: List[str] = []
    companies: List[str] = []
    products: List[str] = []
    tickers: List[str] = []
    research_impact: Optional[str] = None
    product_impact: Optional[str] = None
    market_impact: Optional[str] = None
    why_it_matters_zh: Optional[str] = None
    targets: List[TargetMapping] = []
    impacts: List[ImpactHypothesis] = []
    market_context: Optional[MarketContext] = None
    score_detail: Optional[ScoreDetail] = None
    risks: List[RiskAlertItem] = []
    backtest_results: List[BacktestResult] = []


class DashboardOverview(BaseModel):
    """首页总览"""
    top_events: List[Dict[str, Any]] = []
    top_events_count: int = 0
    alert_stats: Dict[str, int] = {}
    recent_alerts: List[Dict[str, Any]] = []
    hot_themes: List[Dict[str, Any]] = []
    backtest_summary: Dict[str, Any] = {}
    watching_events: List[Dict[str, Any]] = []
    date_range: str = "过去24小时"
    last_updated: Optional[datetime] = None


class ThemeDetail(BaseModel):
    """主题详情"""
    id: UUID
    name_en: str
    name_zh: Optional[str] = None
    description: Optional[str] = None
    related_symbols: List[str] = []
    event_count_7d: int = 0
    event_count_30d: int = 0
    heat_trend: Optional[str] = None
    avg_score: float = 0
    hit_rate: Optional[float] = None
    recent_events: List[Dict[str, Any]] = []


class ThemeList(BaseModel):
    """主题列表"""
    total: int
    items: List[ThemeDetail]


class EntityFullDetail(BaseModel):
    """实体完整详情"""
    entity_id: str
    entity_name: Optional[str] = None
    mapped_targets: List[TargetMapping] = []
    recent_events: List[Dict[str, Any]] = []
    event_count_30d: int = 0


class Recommendation(BaseModel):
    """推荐事件"""
    event_id: UUID
    title: Optional[str] = None
    summary_zh: Optional[str] = None
    final_score: float = 0
    alert_level: str = "C"
    direction: Optional[str] = None
    target_symbols: List[str] = []
    action_suggestion: str = "watch"
    risk_level: str = "medium"
    published_at: Optional[datetime] = None


class RecommendationList(BaseModel):
    """推荐事件列表"""
    total: int
    items: List[Recommendation]


class MethodologyInsight(BaseModel):
    """方法论事件"""
    event_id: UUID
    title: Optional[str] = None
    summary_zh: Optional[str] = None
    source: str
    entity_id: str
    topics: List[str] = []
    target_symbols: List[str] = []
    published_at: Optional[datetime] = None
    methodology_score: float = 0


class MethodologyInsightList(BaseModel):
    """方法论事件列表"""
    total: int
    items: List[MethodologyInsight]
