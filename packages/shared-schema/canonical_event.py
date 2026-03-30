"""
CanonicalEvent - 统一事件结构
所有采集器输出必须符合该schema
"""

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class SourceType(str, Enum):
    """数据来源类型"""
    OFFICIAL_API = "official_api"
    RSS = "rss"
    WEBHOOK = "webhook"
    OPENCLI = "opencli"


class Source(str, Enum):
    """数据源"""
    X = "x"
    GITHUB = "github"
    RSS = "rss"
    ARXIV = "arxiv"
    YOUTUBE = "youtube"
    REDDIT = "reddit"
    HACKER_NEWS = "hn"
    SEC = "sec"
    OPENCLI = "opencli"
    BLOG = "blog"
    SUBSTACK = "substack"


class EntityType(str, Enum):
    """实体类型"""
    PERSON = "person"
    ORG = "org"
    TOPIC = "topic"


class AlertLevel(str, Enum):
    """告警等级"""
    S = "S"  # 立即飞书 + 邮件
    A = "A"  # 飞书提醒
    B = "B"  # 控制台 + 日报
    C = "C"  # 仅入库


class CanonicalEvent(BaseModel):
    """
    标准事件对象 - 系统核心数据模型
    所有采集器输出都必须转换到该结构
    """

    event_id: UUID = Field(default_factory=uuid4, description="事件唯一ID")
    source: Source = Field(..., description="数据来源")
    source_type: SourceType = Field(..., description="来源类型")
    entity_type: EntityType = Field(..., description="实体类型")
    entity_id: str = Field(..., description="实体标识，如sam-altman")
    author: Optional[str] = Field(None, description="作者账号")
    title: Optional[str] = Field(None, description="标题")
    content_raw: str = Field(..., description="原始内容")
    content_zh: Optional[str] = Field(None, description="中文翻译")
    url: str = Field(..., description="原文链接")
    published_at: datetime = Field(..., description="发布时间")
    fetched_at: datetime = Field(default_factory=datetime.utcnow, description="采集时间")
    language: str = Field(default="en", description="原文语言")

    # 结构化信息
    topics: list[str] = Field(default_factory=list, description="主题标签")
    claims: list[str] = Field(default_factory=list, description="核心观点/事实")
    companies: list[str] = Field(default_factory=list, description="提及公司")
    products: list[str] = Field(default_factory=list, description="提及产品")
    tickers: list[str] = Field(default_factory=list, description="股票代码")
    signals: list[str] = Field(default_factory=list, description="关键信号")

    # 评分
    novelty_score: float = Field(default=0, ge=0, le=1, description="新颖度评分")
    impact_score: float = Field(default=0, ge=0, le=1, description="影响度评分")
    confidence_score: float = Field(default=0, ge=0, le=1, description="置信度评分")

    # 告警
    alert_level: AlertLevel = Field(default=AlertLevel.C, description="告警等级")
    alert_reason: Optional[str] = Field(None, description="告警原因")

    # 聚类
    cluster_id: Optional[UUID] = Field(None, description="事件聚类ID")

    # 影响分析
    research_impact: Optional[str] = Field(None, description="对研究路线的影响")
    product_impact: Optional[str] = Field(None, description="对产品竞争格局的影响")
    market_impact: Optional[str] = Field(None, description="对资本/市场叙事的影响")
    policy_impact: Optional[str] = Field(None, description="对监管/政策的影响")
    why_it_matters_zh: Optional[str] = Field(None, description="为什么值得关注")
    what_to_watch_next: Optional[str] = Field(None, description="接下来要盯什么")

    class Config:
        use_enum_values = True


class EventCreate(BaseModel):
    """创建事件的输入模型"""
    source: Source
    source_type: SourceType
    entity_type: EntityType
    entity_id: str
    author: Optional[str] = None
    title: Optional[str] = None
    content_raw: str
    url: str
    published_at: datetime
    language: str = "en"


class EventUpdate(BaseModel):
    """更新事件的模型"""
    content_zh: Optional[str] = None
    topics: Optional[list[str]] = None
    claims: Optional[list[str]] = None
    companies: Optional[list[str]] = None
    products: Optional[list[str]] = None
    tickers: Optional[list[str]] = None
    signals: Optional[list[str]] = None
    novelty_score: Optional[float] = None
    impact_score: Optional[float] = None
    confidence_score: Optional[float] = None
    alert_level: Optional[AlertLevel] = None
    alert_reason: Optional[str] = None
    cluster_id: Optional[UUID] = None
    research_impact: Optional[str] = None
    product_impact: Optional[str] = None
    market_impact: Optional[str] = None
    policy_impact: Optional[str] = None
    why_it_matters_zh: Optional[str] = None
    what_to_watch_next: Optional[str] = None