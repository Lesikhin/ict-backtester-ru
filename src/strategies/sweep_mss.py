"""
Стратегия: Sweep + FVG (без проверки митигации)
"""

import logging
from typing import List
import pandas as pd

from src.strategies.base import BaseStrategy
from src.data.models import (
    TradeSignal, SwingPoint, FairValueGap, StructureBreak,
    LiquiditySweep, LiquidityLevel, Direction, PatternType
)

logger = logging.getLogger(__name__)


class SweepMSSStrategy(BaseStrategy):
    """Стратегия: Снятие ликвидности -> Вход на FVG."""
    
    def __init__(self, config: dict):
        super().__init__("Sweep_MSS_FVG", config)
        self.risk_percent = config.get('risk_per_trade_percent', 1.0)
        self.rr_ratio = config.get('reward_risk_ratio', 2.0)
        self.use_fvg_entry = config.get('use_fvg_entry', True)
    
    def generate_signals(
        self,
        df: pd.DataFrame,
        swings: List[SwingPoint],
        fvgs: List[FairValueGap],
        breaks: List[StructureBreak],
        sweeps: List[LiquiditySweep],
        levels: List[LiquidityLevel]
    ) -> List[TradeSignal]:
        
        signals = []
        
        logger.info(f"Анализ {len(sweeps)} снятий ликвидности...")
        
        for sweep in sweeps:
            # Ищем ближайший FVG после sweep (в пределах 20 свечей)
            # БЕЗ проверки митигации
            valid_fvg = None
            
            for fvg in fvgs:
                if fvg.index > sweep.index and fvg.index < sweep.index + 20:
                    # Проверяем только направление
                    if sweep.direction == Direction.LONG and fvg.direction == Direction.LONG:
                        valid_fvg = fvg
                        break
                    elif sweep.direction == Direction.SHORT and fvg.direction == Direction.SHORT:
                        valid_fvg = fvg
                        break
            
            if not valid_fvg:
                continue
            
            # Создаем сигнал
            if sweep.direction == Direction.LONG:
                entry_price = valid_fvg.top if self.use_fvg_entry else valid_fvg.midpoint
                stop_loss = sweep.sweep_price * 0.995
                direction = Direction.LONG
                pattern = PatternType.SWEEP_BULLISH
            else:
                entry_price = valid_fvg.bottom if self.use_fvg_entry else valid_fvg.midpoint
                stop_loss = sweep.sweep_price * 1.005
                direction = Direction.SHORT
                pattern = PatternType.SWEEP_BEARISH
            
            risk_points = abs(entry_price - stop_loss)
            if risk_points == 0:
                continue
            
            if direction == Direction.LONG:
                take_profit = entry_price + (risk_points * self.rr_ratio)
            else:
                take_profit = entry_price - (risk_points * self.rr_ratio)
            
            signal = TradeSignal(
                timestamp=sweep.timestamp,
                direction=direction,
                entry_price=entry_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                risk_reward=self.rr_ratio,
                pattern_type=pattern,
                confidence=0.70,
                metadata={
                    "sweep_index": sweep.index,
                    "fvg_index": valid_fvg.index
                }
            )
            signals.append(signal)
        
        logger.info(f"Создано сигналов: {len(signals)}")
        return signals