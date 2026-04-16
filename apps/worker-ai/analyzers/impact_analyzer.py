"""
影响分析引擎 - 分析事件对标的的影响方向
"""

import logging
from typing import Dict, Any, List, Optional
from uuid import UUID

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class ImpactAnalyzer:
    """影响分析引擎"""

    def __init__(self, db: Session, translator: Optional[Any] = None):
        self.db = db
        self.translator = translator
    
    def analyze_impact(self, event: Any, targets: List[Dict]) -> List[Dict]:
        """
        分析事件对标的的影响
        
        Args:
            event: Event对象
            targets: 标的列表
            
        Returns:
            影响分析结果列表
        """
        results = []
        
        # 获取事件内容
        content = (event.content_zh or event.content_raw or "").lower()
        title = (event.title or "").lower()
        combined_text = f"{title} {content}"
        
        # 关键词规则
        bullish_keywords = [
            "发布", "launch", "release", "突破", "breakthrough", "超预期", "beat",
            "增长", "growth", "合作", "partnership", "投资", "investment", "融资",
            "funding", "收购", "acquisition", "获得", "win", "contract", "订单",
            "升级", "upgrade", "创新", "innovation", "领先", "leading",
        ]
        
        bearish_keywords = [
            "下调", "downgrade", "低于预期", "miss", "亏损", "loss", "裁员",
            "layoff", "诉讼", "lawsuit", "调查", "investigation", "罚款", "fine",
            "风险", "risk", "担忧", "concern", "下跌", "decline", "关闭", "shutdown",
            "暂停", "suspend", "延迟", "delay", "竞争", "competition threat",
        ]
        
        neutral_keywords = [
            "更新", "update", "宣布", "announce", "报告", "report", "研究", "research",
            "测试", "test", "预览", "preview", "计划", "plan",
        ]
        
        for target in targets:
            symbol = target["symbol"]
            relation_type = target.get("relation_type", "direct")
            
            # 计算情绪分数
            bullish_score = sum(1 for kw in bullish_keywords if kw in combined_text)
            bearish_score = sum(1 for kw in bearish_keywords if kw in combined_text)
            neutral_score = sum(1 for kw in neutral_keywords if kw in combined_text)
            
            # 根据关系类型调整
            if relation_type == "competitor":
                # 竞品利好 = 自身利空
                bullish_score, bearish_score = bearish_score, bullish_score
            
            # 确定方向
            if bullish_score > bearish_score and bullish_score > neutral_score:
                direction = "bullish"
                confidence = min(0.9, 0.5 + bullish_score * 0.1)
            elif bearish_score > bullish_score and bearish_score > neutral_score:
                direction = "bearish"
                confidence = min(0.9, 0.5 + bearish_score * 0.1)
            else:
                direction = "neutral"
                confidence = 0.5
            
            # 确定影响类型
            impact_type = self._determine_impact_type(combined_text)
            
            # 确定时间维度
            time_horizon = self._determine_time_horizon(combined_text)
            
            # 生成假设文本
            hypothesis_text = self._generate_hypothesis(
                symbol, direction, impact_type, event.title, combined_text
            )
            
            results.append({
                "symbol": symbol,
                "direction": direction,
                "impact_type": impact_type,
                "hypothesis_text_zh": hypothesis_text,
                "confidence": confidence,
                "time_horizon": time_horizon,
                "reasoning": f"bullish={bullish_score}, bearish={bearish_score}",
            })
        
        return results
    
    def _determine_impact_type(self, text: str) -> str:
        """确定影响类型"""
        if any(kw in text for kw in ["earnings", "revenue", "profit", "收入", "利润", "财报"]):
            return "fundamental"
        elif any(kw in text for kw in ["sentiment", "market", "情绪", "市场"]):
            return "sentiment"
        elif any(kw in text for kw in ["valuation", "估值", "pe ", "price target"]):
            return "valuation"
        elif any(kw in text for kw in ["policy", "regulation", "政策", "监管", "法律"]):
            return "policy"
        elif any(kw in text for kw in ["supply", "chain", "供应链", "产能", "芯片"]):
            return "supply_chain"
        else:
            return "sentiment"
    
    def _determine_time_horizon(self, text: str) -> str:
        """确定时间维度"""
        if any(kw in text for kw in ["今天", "today", "intraday", "日内"]):
            return "intraday"
        elif any(kw in text for kw in ["本周", "this week", "短期"]):
            return "1d"
        elif any(kw in text for kw in ["本月", "this month", "中期"]):
            return "1w"
        else:
            return "3d"
    
    def _generate_hypothesis(self, symbol: str, direction: str,
                              impact_type: str, title: str, content: str) -> str:
        """生成中文假设说明。优先用 LLM 生成具体分析，失败时用模板回退。"""
        template_result = self._generate_hypothesis_template(
            symbol, direction, impact_type, title, content
        )

        if not self.translator:
            return template_result

        try:
            direction_text = {
                "bullish": "利好",
                "bearish": "利空",
                "neutral": "中性",
            }
            impact_type_text = {
                "fundamental": "基本面",
                "sentiment": "情绪面",
                "valuation": "估值",
                "policy": "政策",
                "supply_chain": "供应链",
            }

            prompt = f"""你是一个股票市场分析助手。请基于以下信息，用1-2句简体中文分析 {symbol} 受到的影响。

当前初步判断：{direction_text.get(direction, '中性')}影响（{impact_type_text.get(impact_type, '情绪面')}）
事件标题：{title}
事件内容：{content[:500]}

请具体说明：
1. 为什么是{direction_text.get(direction, '中性')}影响（具体原因，不是套话）
2. 影响的传导路径是什么
3. 短期还是长期

直接输出分析，50字以内。"""

            llm_result = self.translator.analyze(
                system_prompt="你是专业的A股和美股分析助手，给出具体、可操作的分析。",
                user_prompt=prompt,
                max_tokens=200,
            )
            if llm_result and len(llm_result.strip()) > 10:
                return f"{symbol} - {llm_result.strip()}"
        except Exception as e:
            logger.warning("LLM 生成 hypothesis 失败 (%s): %s", symbol, e)

        return template_result

    def _generate_hypothesis_template(self, symbol: str, direction: str,
                                       impact_type: str, title: str, content: str) -> str:
        """模板方式生成假设说明（LLM 失败时的回退）。"""
        direction_text = {
            "bullish": "利好",
            "bearish": "利空",
            "neutral": "中性",
        }
        
        impact_text = {
            "fundamental": "基本面",
            "sentiment": "情绪面",
            "valuation": "估值",
            "policy": "政策",
            "supply_chain": "供应链",
        }
        
        hypothesis = (
            f"{symbol} - "
            f"{direction_text.get(direction, '中性')}影响"
            f"（{impact_text.get(impact_type, '情绪面')}）"
        )
        if title:
            hypothesis += f"：{title[:50]}"
        
        return hypothesis
    
    def save_impact_hypotheses(self, event_id: UUID, impacts: List[Dict]) -> int:
        """保存影响假设到数据库"""
        from models_v2 import EventImpactHypothesis
        from uuid import uuid4
        
        count = 0
        for impact in impacts:
            hypothesis = EventImpactHypothesis(
                id=uuid4(),
                event_id=event_id,
                symbol=impact["symbol"],
                direction=impact["direction"],
                impact_type=impact["impact_type"],
                hypothesis_text_zh=impact["hypothesis_text_zh"],
                confidence=impact["confidence"],
                time_horizon=impact["time_horizon"],
                reasoning=impact.get("reasoning"),
            )
            self.db.add(hypothesis)
            count += 1
        
        self.db.commit()
        return count
