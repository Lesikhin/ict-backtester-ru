"""
Базовый класс для всех торговых стратегий.
"""

import logging
from abc import ABC, abstractmethod
from typing import List
import pandas as pd

from src.data.models import (
    TradeSignal, SwingPoint, FairValueGap, StructureBreak,
    LiquiditySweep, LiquidityLevel
)

logger = logging.getLogger(__name__)


class BaseStrategy(ABC):
    """Абстрактный базовый класс для ICT-стратегий."""
    
    def __init__(self, name: str, config: dict):
        self.name = name
        self.config = config
        logger.info(f"Инициализирована стратегия: {self.name}")
    
    @abstractmethod
    def generate_signals(
        self,
        df: pd.DataFrame,
        swings: List[SwingPoint],
        fvgs: List[FairValueGap],
        breaks: List[StructureBreak],
        sweeps: List[LiquiditySweep],
        levels: List[LiquidityLevel]
    ) -> List[TradeSignal]:
        """Генерация торговых сигналов."""
        pass
    
    def _calculate_position_size(
        self,
        capital: float,
        risk_percent: float,
        entry_price: float,
        stop_loss: float
    ) -> float:
        """Рассчитать размер позиции на основе риска."""
        risk_amount = capital * (risk_percent / 100.0)
        risk_per_unit = abs(entry_price - stop_loss)
        
        if risk_per_unit == 0:
            return 0.0
        
        return risk_amount / risk_per_unit