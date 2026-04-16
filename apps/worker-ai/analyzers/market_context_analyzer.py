"""
市场上下文分析引擎 - 分析事件发生时的市场环境
"""

import logging
from typing import Dict, Any, Optional
from uuid import UUID, uuid4
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class MarketContextAnalyzer:
    """市场上下文分析引擎"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def analyze_context(self, event_time: datetime, symbol: Optional[str] = None) -> Dict:
        """
        分析市场上下文
        
        Args:
            event_time: 事件时间
            symbol: 相关标的（可选）
            
        Returns:
            市场上下文字典
        """
        context = {
            "event_time": event_time,
            "market_session": self._get_market_session(event_time),
            "us_market_open": self._is_us_market_open(event_time),
            "days_to_earnings": None,
            "earnings_season": self._is_earnings_season(event_time),
            "has_macro_event_nearby": False,
            "macro_event_type": None,
            "days_to_macro": None,
            "tradability_hint": "medium",
            "context_summary_zh": None,
        }
        
        # 检查宏观事件
        macro_info = self._check_macro_events(event_time)
        context.update(macro_info)
        
        # 生成可交易性提示
        context["tradability_hint"] = self._calculate_tradability(context)
        
        # 生成中文摘要
        context["context_summary_zh"] = self._generate_summary(context)
        
        return context
    
    def _get_market_session(self, dt: datetime) -> str:
        """判断市场交易时段"""
        # 美股交易时间 (UTC)
        # 盘前: 09:00-13:30 UTC (4:00-9:30 ET)
        # 盘中: 13:30-20:00 UTC (9:30-16:00 ET)
        # 盘后: 20:00-24:00 UTC (16:00-20:00 ET)
        
        if dt.weekday() >= 5:  # 周末
            return "weekend"
        
        hour = dt.hour
        minute = dt.minute
        time_val = hour * 60 + minute
        
        # UTC时间
        pre_start = 9 * 60      # 09:00 UTC
        market_open = 13 * 60 + 30  # 13:30 UTC
        market_close = 20 * 60  # 20:00 UTC
        post_end = 24 * 60      # 24:00 UTC
        
        if time_val < pre_start:
            return "pre"
        elif time_val < market_open:
            return "pre"
        elif time_val < market_close:
            return "regular"
        elif time_val < post_end:
            return "post"
        else:
            return "after_hours"
    
    def _is_us_market_open(self, dt: datetime) -> bool:
        """判断美股是否开盘"""
        if dt.weekday() >= 5:
            return False
        
        hour = dt.hour
        minute = dt.minute
        time_val = hour * 60 + minute
        
        market_open = 13 * 60 + 30  # 13:30 UTC
        market_close = 20 * 60      # 20:00 UTC
        
        return market_open <= time_val < market_close
    
    def _is_earnings_season(self, dt: datetime) -> bool:
        """判断是否财报季"""
        month = dt.month
        # 财报季通常在1、4、7、10月的中下旬到次月上旬
        earnings_months = [1, 2, 4, 5, 7, 8, 10, 11]
        return month in earnings_months
    
    def _check_macro_events(self, dt: datetime) -> Dict:
        """检查附近的宏观事件"""
        # 2026年主要宏观事件日期（示例）
        macro_events = [
            # FOMC会议
            {"date": datetime(2026, 1, 29), "type": "FOMC", "name": "FOMC利率决议"},
            {"date": datetime(2026, 3, 19), "type": "FOMC", "name": "FOMC利率决议"},
            {"date": datetime(2026, 5, 7), "type": "FOMC", "name": "FOMC利率决议"},
            {"date": datetime(2026, 6, 18), "type": "FOMC", "name": "FOMC利率决议"},
            {"date": datetime(2026, 7, 30), "type": "FOMC", "name": "FOMC利率决议"},
            {"date": datetime(2026, 9, 17), "type": "FOMC", "name": "FOMC利率决议"},
            {"date": datetime(2026, 11, 5), "type": "FOMC", "name": "FOMC利率决议"},
            {"date": datetime(2026, 12, 17), "type": "FOMC", "name": "FOMC利率决议"},
            # CPI数据（通常每月中旬）
            {"date": datetime(2026, 4, 10), "type": "CPI", "name": "CPI数据"},
            {"date": datetime(2026, 5, 14), "type": "CPI", "name": "CPI数据"},
            # 非农数据（通常每月第一个周五）
            {"date": datetime(2026, 4, 3), "type": "NFP", "name": "非农就业数据"},
            {"date": datetime(2026, 5, 1), "type": "NFP", "name": "非农就业数据"},
        ]
        
        nearest_event = None
        min_days = 999
        
        for event in macro_events:
            days_diff = abs((event["date"] - dt).days)
            if days_diff < min_days and days_diff <= 7:
                min_days = days_diff
                nearest_event = event
        
        if nearest_event:
            return {
                "has_macro_event_nearby": True,
                "macro_event_type": nearest_event["type"],
                "days_to_macro": min_days,
            }
        
        return {
            "has_macro_event_nearby": False,
            "macro_event_type": None,
            "days_to_macro": None,
        }
    
    def _calculate_tradability(self, context: Dict) -> str:
        """计算可交易性提示"""
        score = 0
        
        # 市场开盘加分
        if context["us_market_open"]:
            score += 2
        
        # 盘前盘后减分
        if context["market_session"] in ["pre", "post"]:
            score += 1
        elif context["market_session"] == "weekend":
            score -= 2
        
        # 宏观事件附近减分
        if context["has_macro_event_nearby"]:
            days = context["days_to_macro"] or 7
            if days <= 1:
                score -= 2
            elif days <= 3:
                score -= 1
        
        # 财报季减分
        if context["earnings_season"]:
            score -= 0.5
        
        if score >= 2:
            return "high"
        elif score >= 1:
            return "medium"
        elif score >= 0:
            return "low"
        else:
            return "avoid"
    
    def _generate_summary(self, context: Dict) -> str:
        """生成中文摘要"""
        parts = []
        
        # 市场状态
        session_map = {
            "pre": "盘前",
            "regular": "盘中",
            "post": "盘后",
            "weekend": "休市",
            "after_hours": "盘后",
        }
        parts.append(session_map.get(context["market_session"], "未知"))
        
        # 宏观事件
        if context["has_macro_event_nearby"]:
            days = context["days_to_macro"]
            event_type = context["macro_event_type"]
            parts.append(f"{days}天后{event_type}")
        
        # 可交易性
        tradability_map = {
            "high": "适合交易",
            "medium": "可谨慎交易",
            "low": "不建议交易",
            "avoid": "避免交易",
        }
        parts.append(tradability_map.get(context["tradability_hint"], ""))
        
        return " | ".join(parts)
    
    def save_context(self, event_id: UUID, context: Dict) -> None:
        """保存市场上下文到数据库"""
        from models_v2 import MarketContextSnapshot
        
        snapshot = MarketContextSnapshot(
            id=uuid4(),
            event_id=event_id,
            event_time=context["event_time"],
            market_session=context["market_session"],
            us_market_open=context["us_market_open"],
            earnings_season=context["earnings_season"],
            has_macro_event_nearby=context["has_macro_event_nearby"],
            macro_event_type=context["macro_event_type"],
            days_to_macro=context["days_to_macro"],
            tradability_hint=context["tradability_hint"],
            context_summary_zh=context["context_summary_zh"],
        )
        self.db.add(snapshot)
        self.db.commit()
