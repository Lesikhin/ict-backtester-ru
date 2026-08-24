"""
Детекторы ICT-паттернов для анализа рыночной структуры.

Каждый детектор реализует поиск конкретного паттерна:
- SwingDetector: локальные экстремумы (Swing High/Low)
- FVGDetector: ценовые дисбалансы (Fair Value Gap)
- StructureDetector: слом структуры (MSS/BOS)
- SweepDetector: снятие ликвидности
"""

import logging
from typing import List, Tuple, Optional
import pandas as pd
import numpy as np

from src.data.models import (
    SwingPoint, FairValueGap, StructureBreak, 
    LiquiditySweep, Direction
)

logger = logging.getLogger(__name__)


class SwingDetector:
    """
    Детектор свинговых точек (локальных экстремумов).
    
    Свинг подтверждается, если цена слева и справа от него
    находится ниже (для Swing High) или выше (для Swing Low).
    
    Attributes:
        left_bars: Количество свечей слева для подтверждения
        right_bars: Количество свечей справа для подтверждения
    """
    
    def __init__(self, left_bars: int = 5, right_bars: int = 5):
        """
        Инициализация детектора.
        
        Args:
            left_bars: Количество свечей слева
            right_bars: Количество свечей справа
        """
        self.left_bars = left_bars
        self.right_bars = right_bars
        logger.debug(f"SwingDetector инициализирован: left={left_bars}, right={right_bars}")
    
    def detect(self, df: pd.DataFrame) -> List[SwingPoint]:
        """
        Найти все свинговые точки в данных.
        
        Args:
            df: DataFrame с колонками open, high, low, close
                Индекс - datetime
            
        Returns:
            Список найденных SwingPoint, отсортированный по времени
        """
        swings = []
        
        # Проходим по всем свечам, начиная с left_bars
        # и заканчивая за right_bars до конца
        for i in range(self.left_bars, len(df) - self.right_bars):
            
            # Проверяем Swing High
            if self._is_swing_high(df, i):
                swing = SwingPoint(
                    index=i,
                    timestamp=df.index[i],
                    price=df['high'].iloc[i],
                    direction=Direction.LONG,  # Swing High = бычий экстремум
                    strength=1
                )
                swings.append(swing)
            
            # Проверяем Swing Low
            elif self._is_swing_low(df, i):
                swing = SwingPoint(
                    index=i,
                    timestamp=df.index[i],
                    price=df['low'].iloc[i],
                    direction=Direction.SHORT,  # Swing Low = медвежий экстремум
                    strength=1
                )
                swings.append(swing)
        
        # Сортируем по индексу (времени)
        swings.sort(key=lambda s: s.index)
        
        logger.info(f"Найдено {len(swings)} свинговых точек")
        return swings
    
    def _is_swing_high(self, df: pd.DataFrame, index: int) -> bool:
        """
        Проверить, является ли свеча по индексу Swing High.
        
        Swing High: high[i] > high[i-1], high[i-2], ..., high[i-left]
                    high[i] > high[i+1], high[i+2], ..., high[i+right]
        
        Args:
            df: DataFrame с данными
            index: Индекс проверяемой свечи
            
        Returns:
            True если это Swing High
        """
        current_high = df['high'].iloc[index]
        
        # Проверяем свечи слева
        left_slice = df['high'].iloc[index - self.left_bars:index]
        if not all(current_high > left_slice):
            return False
        
        # Проверяем свечи справа
        right_slice = df['high'].iloc[index + 1:index + self.right_bars + 1]
        if not all(current_high > right_slice):
            return False
        
        return True
    
    def _is_swing_low(self, df: pd.DataFrame, index: int) -> bool:
        """
        Проверить, является ли свеча по индексу Swing Low.
        
        Swing Low: low[i] < low[i-1], low[i-2], ..., low[i-left]
                   low[i] < low[i+1], low[i+2], ..., low[i+right]
        
        Args:
            df: DataFrame с данными
            index: Индекс проверяемой свечи
            
        Returns:
            True если это Swing Low
        """
        current_low = df['low'].iloc[index]
        
        # Проверяем свечи слева
        left_slice = df['low'].iloc[index - self.left_bars:index]
        if not all(current_low < left_slice):
            return False
        
        # Проверяем свечи справа
        right_slice = df['low'].iloc[index + 1:index + self.right_bars + 1]
        if not all(current_low < right_slice):
            return False
        
        return True


class FVGDetector:
    """
    Детектор Fair Value Gap (ценовых дисбалансов).
    
    FVG образуется, когда между тенью первой и третьей свечи есть разрыв.
    
    Бычий FVG (Bullish):
        low[2] > high[0]  (разрыв вверх)
        
    Медвежий FVG (Bearish):
        high[2] < low[0]  (разрыв вниз)
    
    Attributes:
        min_size_percent: Минимальный размер FVG в % от цены
        max_age_bars: Максимальный возраст FVG в свечах
    """
    
    def __init__(self, min_size_percent: float = 0.1, max_age_bars: int = 50):
        """
        Инициализация детектора.
        
        Args:
            min_size_percent: Минимальный размер FVG (%)
            max_age_bars: Максимальный возраст FVG (свечей)
        """
        self.min_size_percent = min_size_percent
        self.max_age_bars = max_age_bars
        logger.debug(f"FVGDetector инициализирован: min_size={min_size_percent}%, max_age={max_age_bars}")
    
    def detect(self, df: pd.DataFrame) -> List[FairValueGap]:
        """
        Найти все Fair Value Gap в данных.
        
        Args:
            df: DataFrame с колонками open, high, low, close
            
        Returns:
            Список найденных FairValueGap
        """
        fvgs = []
        
        # Проходим по всем свечам, начиная с третьей (индекс 2)
        for i in range(2, len(df)):
            
            # Получаем цены трех свечей
            candle_0 = i - 2  # Первая свеча
            candle_1 = i - 1  # Центральная свеча (FVG формируется здесь)
            candle_2 = i      # Третья свеча
            
            high_0 = df['high'].iloc[candle_0]
            low_0 = df['low'].iloc[candle_0]
            high_2 = df['high'].iloc[candle_2]
            low_2 = df['low'].iloc[candle_2]
            
            # Проверяем бычий FVG
            if low_2 > high_0:
                fvg_top = low_2
                fvg_bottom = high_0
                fvg_size = fvg_top - fvg_bottom
                mid_price = (high_0 + low_2) / 2
                fvg_size_percent = (fvg_size / mid_price) * 100
                
                if fvg_size_percent >= self.min_size_percent:
                    fvg = FairValueGap(
                        index=candle_1,
                        timestamp=df.index[candle_1],
                        top=fvg_top,
                        bottom=fvg_bottom,
                        direction=Direction.LONG
                    )
                    fvgs.append(fvg)
            
            # Проверяем медвежий FVG
            elif high_2 < low_0:
                fvg_top = low_0
                fvg_bottom = high_2
                fvg_size = fvg_top - fvg_bottom
                mid_price = (low_0 + high_2) / 2
                fvg_size_percent = (fvg_size / mid_price) * 100
                
                if fvg_size_percent >= self.min_size_percent:
                    fvg = FairValueGap(
                        index=candle_1,
                        timestamp=df.index[candle_1],
                        top=fvg_top,
                        bottom=fvg_bottom,
                        direction=Direction.SHORT
                    )
                    fvgs.append(fvg)
        
        # Помечаем митигированные FVG
        self._mark_mitigated(fvgs, df)
        
        logger.info(f"Найдено {len(fvgs)} Fair Value Gap")
        return fvgs
    
    def _mark_mitigated(self, fvgs: List[FairValueGap], df: pd.DataFrame) -> None:
        """
        Пометить FVG, которые были закрыты (митигированы).
        
        FVG считается митигированным, если цена вернулась в его зону.
        
        Args:
            fvgs: Список FVG для проверки
            df: DataFrame с данными
        """
        for fvg in fvgs:
            # Проверяем свечи после формирования FVG
            for i in range(fvg.index + 1, min(fvg.index + self.max_age_bars + 1, len(df))):
                
                candle_low = df['low'].iloc[i]
                candle_high = df['high'].iloc[i]
                
                # Для бычьего FVG: цена должна опуститься в зону FVG
                if fvg.direction == Direction.LONG:
                    if candle_low <= fvg.top:
                        fvg.mitigated = True
                        fvg.mitigated_index = i
                        break
                
                # Для медвежьего FVG: цена должна подняться в зону FVG
                elif fvg.direction == Direction.SHORT:
                    if candle_high >= fvg.bottom:
                        fvg.mitigated = True
                        fvg.mitigated_index = i
                        break


class StructureDetector:
    """
    Детектор слома рыночной структуры (MSS/BOS).
    
    Market Structure Shift (MSS) или Break of Structure (BOS) происходит,
    когда цена пробивает последний значимый свинг в противоположном направлении.
    
    Бычий MSS: цена пробивает вверх последний Swing High
    Медвежий MSS: цена пробивает вниз последний Swing Low
    """
    
    def __init__(self):
        """Инициализация детектора."""
        logger.debug("StructureDetector инициализирован")
    
    def detect(self, df: pd.DataFrame, swings: List[SwingPoint]) -> List[StructureBreak]:
        """
        Найти все сломы структуры.
        
        Args:
            df: DataFrame с данными
            swings: Список свинговых точек
            
        Returns:
            Список найденных StructureBreak
        """
        breaks = []
        
        if len(swings) < 2:
            logger.warning("Недостаточно свингов для определения структуры")
            return breaks
        
        # Группируем свинги по типу
        swing_highs = [s for s in swings if s.direction == Direction.LONG]
        swing_lows = [s for s in swings if s.direction == Direction.SHORT]
        
        # Ищем пробои Swing High (бычий MSS)
        for i, swing_high in enumerate(swing_highs[:-1]):
            next_high = swing_highs[i + 1]
            
            # Проверяем, был ли пробой между двумя свингами
            for j in range(swing_high.index + 1, next_high.index):
                if df['high'].iloc[j] > swing_high.price:
                    # Найден пробой
                    breakout = StructureBreak(
                        index=j,
                        timestamp=df.index[j],
                        price=df['high'].iloc[j],
                        direction=Direction.LONG,
                        broken_swing=swing_high
                    )
                    breaks.append(breakout)
                    break
        
        # Ищем пробои Swing Low (медвежий MSS)
        for i, swing_low in enumerate(swing_lows[:-1]):
            next_low = swing_lows[i + 1]
            
            # Проверяем, был ли пробой между двумя свингами
            for j in range(swing_low.index + 1, next_low.index):
                if df['low'].iloc[j] < swing_low.price:
                    # Найден пробой
                    breakout = StructureBreak(
                        index=j,
                        timestamp=df.index[j],
                        price=df['low'].iloc[j],
                        direction=Direction.SHORT,
                        broken_swing=swing_low
                    )
                    breaks.append(breakout)
                    break
        
        # Сортируем по индексу
        breaks.sort(key=lambda b: b.index)
        
        logger.info(f"Найдено {len(breaks)} сломов структуры")
        return breaks


class SweepDetector:
    """
    Детектор снятия ликвидности (Liquidity Sweep).
    
    Снятие ликвидности происходит, когда цена пробивает уровень тенью,
    но закрывается внутри диапазона (тело свечи не закрепляется за уровнем).
    
    Это классическая манипуляция Smart Money для сбора стоп-лоссов.
    """
    
    def __init__(self):
        """Инициализация детектора."""
        logger.debug("SweepDetector инициализирован")
    
    def detect(self, df: pd.DataFrame, swings: List[SwingPoint]) -> List[LiquiditySweep]:
        """
        Найти все случаи снятия ликвидности.
        
        Args:
            df: DataFrame с данными
            swings: Список свинговых точек (уровней ликвидности)
            
        Returns:
            Список найденных LiquiditySweep
        """
        sweeps = []
        
        for swing in swings:
            # Проверяем свечи после формирования свинга
            for i in range(swing.index + 1, len(df)):
                
                candle_open = df['open'].iloc[i]
                candle_high = df['high'].iloc[i]
                candle_low = df['low'].iloc[i]
                candle_close = df['close'].iloc[i]
                
                # Проверяем снятие Swing High (медвежий sweep)
                if swing.direction == Direction.LONG:  # Swing High
                    # Тень пробила уровень вверх
                    if candle_high > swing.price:
                        # Но тело закрылось ниже уровня
                        if candle_close < swing.price:
                            sweep = LiquiditySweep(
                                index=i,
                                timestamp=df.index[i],
                                swept_level=swing,
                                sweep_price=candle_high,
                                close_price=candle_close,
                                direction=Direction.SHORT  # Медвежий сигнал
                            )
                            sweeps.append(sweep)
                            break  # Переходим к следующему свингу
                
                # Проверяем снятие Swing Low (бычий sweep)
                elif swing.direction == Direction.SHORT:  # Swing Low
                    # Тень пробила уровень вниз
                    if candle_low < swing.price:
                        # Но тело закрылось выше уровня
                        if candle_close > swing.price:
                            sweep = LiquiditySweep(
                                index=i,
                                timestamp=df.index[i],
                                swept_level=swing,
                                sweep_price=candle_low,
                                close_price=candle_close,
                                direction=Direction.LONG  # Бычий сигнал
                            )
                            sweeps.append(sweep)
                            break  # Переходим к следующему свингу
        
        # Сортируем по индексу
        sweeps.sort(key=lambda s: s.index)
        
        logger.info(f"Найдено {len(sweeps)} случаев снятия ликвидности")
        return sweeps