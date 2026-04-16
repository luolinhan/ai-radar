"""
风险分析引擎 - 分析交易风险和操作建议
"""

import logging
from typing import Dict, Any, List, Optional
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class RiskAnalyzer:
    """风险分析引擎"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def analyze_risks(self, event: Any, score: Dict, 
                      market_context: Dict, targets: List[Dict]) -> List[Dict]:
        """
        分析风险
        
        Args:
            event: Event对象
            score: 评分结果
            market_context: 市场上下文
            targets: 标的列表
            
        Returns:
            风险列表
        """
        risks = []
        
        # 1. 财报窗口风险
        earnings_risk = self._check_earnings_risk(market_context)
        if earnings_risk:
            risks.append(earnings_risk)
        
        # 2. 宏观事件风险
        macro_risk = self._check_macro_risk(market_context)
        if macro_risk:
            risks.append(macro_risk)
        
        # 3. 市场已反映风险
        priced_in_risk = self._check_priced_in_risk(event, score)
        if priced_in_risk:
            risks.append(priced_in_risk)
        
        # 4. 来源不可靠风险
        source_risk = self._check_source_risk(event, score)
        if source_risk:
            risks.append(source_risk)
        
        # 5. 缺乏标的风险
        target_risk = self._check_target_risk(targets)
        if target_risk:
            risks.append(target_risk)
        
        # 6. 市场状态风险
        session_risk = self._check_session_risk(market_context)
        if session_risk:
            risks.append(session_risk)
        
        # 如果没有风险，添加一般提示
        if not risks:
            risks.append({
                "risk_type": "general",
                "risk_level": "low",
                "risk_text_zh": "暂无明显风险因素",
                "action_suggestion": "watch",
            })
        
        return risks
    
    def _check_earnings_risk(self, context: Dict) -> Optional[Dict]:
        """检查财报窗口风险"""
        if not context.get("earnings_season"):
            return None
        
        return {
            "risk_type": "earnings_season",
            "risk_level": "medium",
            "risk_text_zh": "当前处于财报季，业绩因素可能主导股价，事件影响可能被稀释",
            "action_suggestion": "wait",
        }
    
    def _check_macro_risk(self, context: Dict) -> Optional[Dict]:
        """检查宏观事件风险"""
        if not context.get("has_macro_event_nearby"):
            return None
        
        days = context.get("days_to_macro", 7)
        event_type = context.get("macro_event_type", "宏观事件")
        
        if days <= 1:
            level = "high"
            text = f"明天有{event_type}发布，市场波动性可能显著增加，建议观望"
            action = "skip"
        elif days <= 3:
            level = "medium"
            text = f"{days}天后有{event_type}发布，事件影响可能被宏观因素覆盖"
            action = "wait"
        else:
            level = "low"
            text = f"近期有{event_type}发布（{days}天后），需关注宏观影响"
            action = "watch"
        
        return {
            "risk_type": "macro_event",
            "risk_level": level,
            "risk_text_zh": text,
            "action_suggestion": action,
        }
    
    def _check_priced_in_risk(self, event: Any, score: Dict) -> Optional[Dict]:
        """检查市场已反映风险"""
        # 如果事件是预期内的，可能已被市场定价
        content = (event.content_raw or "").lower()
        
        expected_keywords = ["预期", "expected", "计划", "planned", "rumored", "传闻"]
        
        if any(kw in content for kw in expected_keywords):
            return {
                "risk_type": "priced_in",
                "risk_level": "medium",
                "risk_text_zh": "事件可能已在预期中，市场可能已经提前反映",
                "action_suggestion": "watch",
            }
        
        return None
    
    def _check_source_risk(self, event: Any, score: Dict) -> Optional[Dict]:
        """检查来源可靠性风险"""
        if score.get("source_score", 0) < 5:
            return {
                "risk_type": "source_unreliable",
                "risk_level": "medium",
                "risk_text_zh": "信息来源可靠性较低，建议交叉验证",
                "action_suggestion": "wait",
            }
        
        return None
    
    def _check_target_risk(self, targets: List[Dict]) -> Optional[Dict]:
        """检查缺乏标的风险"""
        if not targets or len(targets) == 0:
            return {
                "risk_type": "no_target",
                "risk_level": "high",
                "risk_text_zh": "无法映射到明确交易标的，不适合直接交易",
                "action_suggestion": "skip",
            }
        
        return None
    
    def _check_session_risk(self, context: Dict) -> Optional[Dict]:
        """检查市场状态风险"""
        session = context.get("market_session", "unknown")
        
        if session == "weekend":
            return {
                "risk_type": "market_closed",
                "risk_level": "low",
                "risk_text_zh": "市场休市，事件影响可能在开盘后被消化",
                "action_suggestion": "wait",
            }
        elif session in ["pre", "post"]:
            return {
                "risk_type": "after_hours",
                "risk_level": "low",
                "risk_text_zh": "盘前/盘后时段，流动性较低，波动可能被放大",
                "action_suggestion": "wait",
            }
        
        return None
    
    def determine_action(self, risks: List[Dict], score: Dict) -> str:
        """
        确定最终操作建议
        
        Returns:
            trade / wait / watch / skip
        """
        final_score = score.get("final_score", 0)
        
        # 如果有任何高风险，建议跳过
        high_risks = [r for r in risks if r.get("risk_level") == "high"]
        if high_risks:
            return "skip"
        
        # 如果有多个中等风险，建议等待
        medium_risks = [r for r in risks if r.get("risk_level") == "medium"]
        if len(medium_risks) >= 2:
            return "wait"
        
        # 根据评分决定
        if final_score >= 8:
            return "trade"
        elif final_score >= 6:
            return "watch"
        else:
            return "skip"
    
    def save_risks(self, event_id: UUID, risks: List[Dict], action: str) -> int:
        """保存风险提示到数据库"""
        from models_v2 import RiskAlert
        
        count = 0
        for risk in risks:
            alert = RiskAlert(
                id=uuid4(),
                event_id=event_id,
                risk_type=risk["risk_type"],
                risk_level=risk["risk_level"],
                risk_text_zh=risk["risk_text_zh"],
                action_suggestion=risk.get("action_suggestion", action),
            )
            self.db.add(alert)
            count += 1
        
        self.db.commit()
        return count
