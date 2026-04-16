"""
标的映射引擎 - 将事件实体映射到交易标的
"""

import logging
from typing import List, Dict, Any, Optional
from uuid import UUID, uuid4
from datetime import datetime

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class TargetMapper:
    """标的映射引擎"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def map_event_targets(self, event: Any) -> List[Dict]:
        """
        为事件映射交易标的
        
        Args:
            event: Event对象
            
        Returns:
            映射结果列表
        """
        targets = []
        seen_symbols = set()
        
        # 1. 从entity_id映射
        entity_targets = self._map_from_entity_id(event.entity_id)
        for t in entity_targets:
            if t["symbol"] not in seen_symbols:
                targets.append(t)
                seen_symbols.add(t["symbol"])
        
        # 2. 从companies字段映射
        if event.companies:
            for company in event.companies:
                company_targets = self._map_from_company(company)
                for t in company_targets:
                    if t["symbol"] not in seen_symbols:
                        targets.append(t)
                        seen_symbols.add(t["symbol"])
        
        # 3. 从products字段映射
        if event.products:
            for product in event.products:
                product_targets = self._map_from_product(product)
                for t in product_targets:
                    if t["symbol"] not in seen_symbols:
                        targets.append(t)
                        seen_symbols.add(t["symbol"])
        
        # 4. 从topics字段映射
        if event.topics:
            for topic in event.topics:
                topic_targets = self._map_from_topic(topic)
                for t in topic_targets:
                    if t["symbol"] not in seen_symbols:
                        targets.append(t)
                        seen_symbols.add(t["symbol"])
        
        # 5. 从tickers字段直接提取
        if event.tickers:
            for ticker in event.tickers:
                if ticker not in seen_symbols:
                    targets.append({
                        "symbol": ticker,
                        "name": ticker,
                        "relation_type": "mentioned",
                        "confidence": 0.9,
                        "source": "ticker_field",
                    })
                    seen_symbols.add(ticker)
        
        return targets
    
    def _map_from_entity_id(self, entity_id: str) -> List[Dict]:
        """从entity_id查询映射"""
        from models_v2 import EntityMarketMap
        
        maps = self.db.query(EntityMarketMap).filter(
            EntityMarketMap.entity_id == entity_id.lower(),
            EntityMarketMap.is_active == True
        ).all()
        
        return [
            {
                "symbol": m.mapped_symbol,
                "name": m.mapped_name,
                "market": m.market,
                "relation_type": m.relation_type,
                "confidence": m.confidence,
                "source": "entity_map",
            }
            for m in maps
        ]
    
    def _map_from_company(self, company: str) -> List[Dict]:
        """从公司名查询映射"""
        from models_v2 import EntityMarketMap
        
        # 尝试多种形式的匹配
        slug = company.lower().replace(" ", "-").replace(".", "")
        aliases = [
            slug,
            company.lower(),
            company.lower().replace(" ", ""),
        ]
        
        maps = self.db.query(EntityMarketMap).filter(
            EntityMarketMap.entity_id.in_(aliases),
            EntityMarketMap.entity_type == "org",
            EntityMarketMap.is_active == True
        ).all()
        
        return [
            {
                "symbol": m.mapped_symbol,
                "name": m.mapped_name,
                "market": m.market,
                "relation_type": m.relation_type,
                "confidence": m.confidence,
                "source": "company_map",
            }
            for m in maps
        ]
    
    def _map_from_product(self, product: str) -> List[Dict]:
        """从产品名查询映射"""
        from models_v2 import EntityMarketMap
        
        slug = product.lower().replace(" ", "-")
        
        maps = self.db.query(EntityMarketMap).filter(
            EntityMarketMap.entity_id == slug,
            EntityMarketMap.entity_type == "product",
            EntityMarketMap.is_active == True
        ).all()
        
        # 产品相关的主题映射
        product_topic_map = {
            "gpt": ["NVDA", "MSFT"],
            "chatgpt": ["MSFT", "NVDA"],
            "claude": ["AMZN", "NVDA"],
            "gemini": ["GOOGL"],
            "llama": ["META"],
            "copilot": ["MSFT"],
            "midjourney": ["NVDA"],
            "sora": ["MSFT", "NVDA"],
        }
        
        product_lower = product.lower()
        if product_lower in product_topic_map:
            for symbol in product_topic_map[product_lower]:
                if not any(m.mapped_symbol == symbol for m in maps):
                    maps.append(type("obj", (object,), {
                        "mapped_symbol": symbol,
                        "mapped_name": symbol,
                        "market": "US",
                        "relation_type": "beneficiary",
                        "confidence": 0.7,
                    })())
        
        return [
            {
                "symbol": m.mapped_symbol,
                "name": getattr(m, "mapped_name", m.mapped_symbol),
                "market": getattr(m, "market", "US"),
                "relation_type": m.relation_type,
                "confidence": m.confidence,
                "source": "product_map",
            }
            for m in maps
        ]
    
    def _map_from_topic(self, topic: str) -> List[Dict]:
        """从主题查询映射"""
        from models_v2 import EntityMarketMap
        
        slug = topic.lower().replace(" ", "-")
        
        maps = self.db.query(EntityMarketMap).filter(
            EntityMarketMap.entity_id == slug,
            EntityMarketMap.entity_type == "topic",
            EntityMarketMap.is_active == True
        ).all()
        
        # 主题关键词映射
        topic_symbol_map = {
            "llm": ["NVDA", "MSFT", "GOOGL"],
            "large language model": ["NVDA", "MSFT", "GOOGL"],
            "generative ai": ["NVDA", "MSFT"],
            "ai chips": ["NVDA", "AMD"],
            "gpu": ["NVDA", "AMD"],
            "ai infrastructure": ["NVDA", "SMCI"],
            "data center": ["NVDA", "EQIX", "SMCI"],
            "inference": ["NVDA", "AMD"],
            "training": ["NVDA"],
            "open source": ["META", "MSFT"],
        }
        
        topic_lower = topic.lower()
        additional_symbols = []
        for key, symbols in topic_symbol_map.items():
            if key in topic_lower:
                additional_symbols.extend(symbols)
        
        for symbol in additional_symbols:
            if not any(m.mapped_symbol == symbol for m in maps):
                maps.append(type("obj", (object,), {
                    "mapped_symbol": symbol,
                    "mapped_name": symbol,
                    "market": "US",
                    "relation_type": "thematic",
                    "confidence": 0.6,
                })())
        
        return [
            {
                "symbol": m.mapped_symbol,
                "name": getattr(m, "mapped_name", m.mapped_symbol),
                "market": getattr(m, "market", "US"),
                "relation_type": m.relation_type,
                "confidence": m.confidence,
                "source": "topic_map",
            }
            for m in maps
        ]
    
    def save_impact_hypotheses(self, event_id: UUID, targets: List[Dict], 
                                 direction: str = "neutral", 
                                 impact_type: str = "sentiment") -> int:
        """保存影响假设到数据库"""
        from models_v2 import EventImpactHypothesis
        
        count = 0
        for t in targets:
            hypothesis = EventImpactHypothesis(
                id=uuid4(),
                event_id=event_id,
                symbol=t["symbol"],
                direction=t.get("direction", direction),
                impact_type=t.get("impact_type", impact_type),
                hypothesis_text_zh=t.get("hypothesis_text_zh"),
                confidence=t.get("confidence", 0.7),
                time_horizon=t.get("time_horizon", "1d"),
            )
            self.db.add(hypothesis)
            count += 1
        
        self.db.commit()
        return count
