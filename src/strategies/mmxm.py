"""
Стратегия: Market Maker Model (MMXM)
Глобальная модель разворота Smart Money.
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


class MMXMStrategy(BaseStrategy):
    """
    Стратегия Market Maker Model (MMXM).
    
    MM Buy Model:
    1. Smart Money Reverse - разворот тренда (MSS)
    2. Original Consolidation - формирование базы
    3. Manipulation (Spring) - ложный пробой вниз
    4. Distribution - рост к ликвидности выше
    
    MM Sell Model - зеркальная ситуация.
    """
    
    def __init__(self, config: dict):
        super().__init__("MMXM", config)
        self.risk_percent = config.get('risk_per_trade_percent', 1.0)
        self.rr_ratio = config.get('reward_risk_ratio', 3.0)
        self.consolidation_bars = config.get('consolidation_bars', 20)
    
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
        
        # Ищем паттерн: MSS -> Consolidation -> Sweep (Spring) -> Signal
        for i, mss in enumerate(breaks):
            
            # Проверяем, была ли консолидация после MSS
            consolidation_range = self._find_consolidation(df, mss.index)
            
            if not consolidation_range:
                continue
            
            start_idx, end_idx = consolidation_range
            
            # Ищем sweep (Spring) после консолидации
            spring = self._find_spring_after_consolidation(sweeps, end_idx, mss.direction)
            
            if not spring:
                continue
            
            # Формируем сигнал
            signal = self._create_mmxm_signal(df, mss, spring, levels)
            if signal:
                signals.append(signal)
                logger.debug(f"Сгенерирован MMXM сигнал: {signal}")
        
        return signals
    
    def _find_consolidation(self, df: pd.DataFrame, after_index: int) -> Optional[tuple]:
        """
        Найти период консолидации после MSS.
        Консолидация = узкий диапазон цены за N свечей.
        """
        lookback = self.consolidation_bars
        end_idx = min(after_index + lookback, len(df) - 1)
        
        if after_index >= end_idx:
            return None
        
        slice_df = df.iloc[after_index:end_idx]
        highest = slice_df['high'].max()
        lowest = slice_df['low'].min()
        avg_price = slice_df['close'].mean()
        
        range_percent = ((highest - lowest) / avg_price) * 100
        
        # Если диапазон меньше 1%, считаем это консолидацией
        if range_percent < 1.0:
            return (after_index, end_idx)
        
        return None
    
    def _find_spring_after_consolidation(
        self,
        sweeps: List[LiquiditySweep],
        after_index: int,
        mss_direction: Direction
    ) -> Optional[LiquiditySweep]:
        """
        Найти Spring (ложный пробой) после консолидации.
        Для бычьего MSS ищем медвежий sweep (Spring вниз).
        """
        # Для бычьего MSS нужен медвежий sweep (направление SHORT)
        target_direction = Direction.SHORT if mss_direction == Direction.LONG else Direction.LONG
        
        for sweep in sweeps:
            if sweep.index > after_index and sweep.direction == target_direction:
                return sweep
        
        return None
    
    def _create_mmxm_signal(
        self,
        df: pd.DataFrame,
        mss: StructureBreak,
        spring: LiquiditySweep,
        levels: List[LiquidityLevel]
    ) -> TradeSignal:
        """Создать сигнал на основе MMXM модели."""
        
        # После Spring (ложного пробоя) входим в направлении MSS
        if mss.direction == Direction.LONG:
            # Бычий MMXM
            entry_price = df['close'].iloc[spring.index + 1] if spring.index + 1 < len(df) else spring.close_price
            stop_loss = spring.sweep_price * 0.995  # Чуть ниже Spring
            direction = Direction.LONG
            pattern = PatternType.SWEEP_BULLISH
        else:
            # Медвежий MMXM
            entry_price = df['close'].iloc[spring.index + 1] if spring.index + 1 < len(df) else spring.close_price
            stop_loss = spring.sweep_price * 1.005
            direction = Direction.SHORT
            pattern = PatternType.SWEEP_BEARISH
        
        risk_points = abs(entry_price - stop_loss)
        if direction == Direction.LONG:
            take_profit = entry_price + (risk_points * self.rr_ratio)
        else:
            take_profit = entry_price - (risk_points * self.rr_ratio)
        
        return TradeSignal(
            timestamp=spring.timestamp,
            direction=direction,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            risk_reward=self.rr_ratio,
            pattern_type=pattern,
            confidence=0.80,
            metadata={
                "strategy": "MMXM",
                "mss_index": mss.index,
                "spring_index": spring.index
            }
        )