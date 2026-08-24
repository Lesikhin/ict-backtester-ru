"""
Стратегия: Power of 3 (Accumulation, Manipulation, Distribution)
"""

import logging
from typing import List, Optional
import pandas as pd

from src.strategies.base import BaseStrategy
from src.data.models import (
    TradeSignal, SwingPoint, FairValueGap, StructureBreak,
    LiquiditySweep, LiquidityLevel, Direction, PatternType
)

logger = logging.getLogger(__name__)


class PowerOf3Strategy(BaseStrategy):
    """Стратегия Power of 3 (AMD)."""
    
    def __init__(self, config: dict):
        super().__init__("Power_of_3_AMD", config)
        self.consolidation_hours = config.get('consolidation_hours', 4)
        self.manipulation_lookback = config.get('manipulation_lookback', 10)
        self.risk_percent = config.get('risk_per_trade_percent', 1.0)
        self.rr_ratio = config.get('reward_risk_ratio', 2.0)
    
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
        
        for sweep in sweeps:
            if self._is_consolidation_before(df, sweep.index):
                target_direction = Direction.LONG if sweep.direction == Direction.LONG else Direction.SHORT
                mss = self._find_subsequent_mss(breaks, sweep.index, target_direction)
                
                if mss:
                    signal = self._create_amd_signal(df, sweep, mss, levels)
                    if signal:
                        signals.append(signal)
        
        return signals
    
    def _is_consolidation_before(self, df: pd.DataFrame, current_index: int) -> bool:
        lookback = self.consolidation_hours * 4
        start_idx = max(0, current_index - lookback)
        
        if start_idx >= current_index:
            return False
        
        slice_df = df.iloc[start_idx:current_index]
        highest_high = slice_df['high'].max()
        lowest_low = slice_df['low'].min()
        avg_close = slice_df['close'].mean()
        
        range_percent = ((highest_high - lowest_low) / avg_close) * 100
        return range_percent < 0.5
    
    def _find_subsequent_mss(
        self,
        breaks: List[StructureBreak],
        after_index: int,
        direction: Direction
    ) -> Optional[StructureBreak]:
        for mss in breaks:
            if mss.index > after_index and mss.direction == direction:
                return mss
        return None
    
    def _create_amd_signal(
        self,
        df: pd.DataFrame,
        sweep: LiquiditySweep,
        mss: StructureBreak,
        levels: List[LiquidityLevel]
    ) -> TradeSignal:
        
        if sweep.direction == Direction.LONG:
            entry_price = df['close'].iloc[mss.index]
            stop_loss = sweep.sweep_price * 0.998
            direction = Direction.LONG
            pattern = PatternType.SWEEP_BULLISH
        else:
            entry_price = df['close'].iloc[mss.index]
            stop_loss = sweep.sweep_price * 1.002
            direction = Direction.SHORT
            pattern = PatternType.SWEEP_BEARISH
        
        risk_points = abs(entry_price - stop_loss)
        if direction == Direction.LONG:
            take_profit = entry_price + (risk_points * self.rr_ratio)
        else:
            take_profit = entry_price - (risk_points * self.rr_ratio)
        
        return TradeSignal(
            timestamp=mss.timestamp,
            direction=direction,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            risk_reward=self.rr_ratio,
            pattern_type=pattern,
            confidence=0.75,
            metadata={
                "strategy": "AMD",
                "sweep_index": sweep.index,
                "mss_index": mss.index
            }
        )