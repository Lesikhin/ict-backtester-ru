"""
Базовые модели данных для ICT-Backtester-RU.
Используются dataclasses для строгой типизации и читаемости.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import Optional, List
import pandas as pd


class Direction(Enum):
    """Направление рынка или сделки."""
    LONG = auto()
    SHORT = auto()
    NEUTRAL = auto()


class PatternType(Enum):
    """Типы ICT-паттернов."""
    SWING_HIGH = auto()
    SWING_LOW = auto()
    FVG_BULLISH = auto()
    FVG_BEARISH = auto()
    MSS_BULLISH = auto()
    MSS_BEARISH = auto()
    SWEEP_BULLISH = auto()
    SWEEP_BEARISH = auto()
    LIQUIDITY_LEVEL = auto()


@dataclass
class OHLCV:
    """
    Модель свечи OHLCV.
    
    Attributes:
        timestamp: Время свечи
        open: Цена открытия
        high: Максимальная цена
        low: Минимальная цена
        close: Цена закрытия
        volume: Объем торгов
    """
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    
    @classmethod
    def from_series(cls, series: pd.Series) -> 'OHLCV':
        """Создать OHLCV из pandas Series."""
        return cls(
            timestamp=series.name if isinstance(series.name, datetime) else pd.to_datetime(series.name),
            open=float(series['open']),
            high=float(series['high']),
            low=float(series['low']),
            close=float(series['close']),
            volume=float(series.get('volume', 0))
        )


@dataclass
class SwingPoint:
    """
    Модель свинговой точки (локального экстремума).
    
    Attributes:
        index: Индекс свечи в DataFrame
        timestamp: Время свечи
        price: Цена экстремума
        direction: Тип свинга (HIGH/LOW)
        strength: "Сила" свинга (количество подтверждений)
    """
    index: int
    timestamp: datetime
    price: float
    direction: Direction
    strength: int = 1
    
    def __repr__(self) -> str:
        dir_str = "HIGH" if self.direction == Direction.LONG else "LOW"
        return f"SwingPoint({dir_str}, price={self.price:.2f}, time={self.timestamp})"


@dataclass
class FairValueGap:
    """
    Модель Fair Value Gap (ценового дисбаланса).
    
    FVG образуется, когда между тенью первой и третьей свечи есть разрыв.
    
    Attributes:
        index: Индекс центральной свечи FVG
        timestamp: Время формирования
        top: Верхняя граница FVG
        bottom: Нижняя граница FVG
        direction: Тип FVG (бычий/медвежий)
        mitigated: Был ли FVG закрыт (цена вернулась в него)
        mitigated_index: Индекс свечи, закрывшей FVG
    """
    index: int
    timestamp: datetime
    top: float
    bottom: float
    direction: Direction
    mitigated: bool = False
    mitigated_index: Optional[int] = None
    
    @property
    def size(self) -> float:
        """Размер FVG в пунктах."""
        return abs(self.top - self.bottom)
    
    @property
    def midpoint(self) -> float:
        """Середина FVG."""
        return (self.top + self.bottom) / 2
    
    def __repr__(self) -> str:
        dir_str = "BULL" if self.direction == Direction.LONG else "BEAR"
        return f"FVG({dir_str}, [{self.bottom:.2f}-{self.top:.2f}], mitigated={self.mitigated})"


@dataclass
class StructureBreak:
    """
    Модель слома рыночной структуры (MSS/BOS).
    
    Attributes:
        index: Индекс свечи пробоя
        timestamp: Время пробоя
        price: Цена пробоя
        direction: Направление пробоя (бычий/медвежий)
        broken_swing: Какой свинг был пробит
    """
    index: int
    timestamp: datetime
    price: float
    direction: Direction
    broken_swing: SwingPoint
    
    def __repr__(self) -> str:
        dir_str = "BULLISH" if self.direction == Direction.LONG else "BEARISH"
        return f"StructureBreak({dir_str}, price={self.price:.2f})"


@dataclass
class LiquiditySweep:
    """
    Модель снятия ликвидности.
    
    Происходит, когда цена пробивает уровень тенью, но закрывается внутри диапазона.
    
    Attributes:
        index: Индекс свечи снятия
        timestamp: Время снятия
        swept_level: Какой уровень был снят
        sweep_price: Цена, до которой дошла тень
        close_price: Цена закрытия свечи
        direction: Направление снятия (бычий/медвежий)
    """
    index: int
    timestamp: datetime
    swept_level: SwingPoint
    sweep_price: float
    close_price: float
    direction: Direction
    
    def __repr__(self) -> str:
        dir_str = "BULL" if self.direction == Direction.LONG else "BEAR"
        return f"LiquiditySweep({dir_str}, level={self.swept_level.price:.2f})"


@dataclass
class LiquidityLevel:
    """
    Модель уровня ликвидности (поддержки/сопротивления).
    
    Формируется из кластера свинговых точек.
    
    Attributes:
        price: Цена уровня (среднее значение кластера)
        top: Верхняя граница зоны
        bottom: Нижняя граница зоны
        touches: Количество касаний уровня
        swing_points: Список свингов, формирующих уровень
        first_touch: Время первого касания
        last_touch: Время последнего касания
    """
    price: float
    top: float
    bottom: float
    touches: int
    swing_points: List[SwingPoint] = field(default_factory=list)
    first_touch: Optional[datetime] = None
    last_touch: Optional[datetime] = None
    
    def __repr__(self) -> str:
        return f"LiquidityLevel(price={self.price:.2f}, touches={self.touches})"


@dataclass
class TradeSignal:
    """
    Модель торгового сигнала.
    
    Attributes:
        timestamp: Время генерации сигнала
        direction: Направление сделки (LONG/SHORT)
        entry_price: Цена входа
        stop_loss: Цена стоп-лосса
        take_profit: Цена тейк-профита
        risk_reward: Соотношение риск/прибыль
        pattern_type: Тип паттерна, сгенерировавшего сигнал
        confidence: Уверенность в сигнале (0-1)
        metadata: Дополнительные данные (комментарии, ID паттерна)
    """
    timestamp: datetime
    direction: Direction
    entry_price: float
    stop_loss: float
    take_profit: float
    risk_reward: float
    pattern_type: PatternType
    confidence: float = 1.0
    metadata: dict = field(default_factory=dict)
    
    @property
    def risk_points(self) -> float:
        """Размер риска в пунктах."""
        return abs(self.entry_price - self.stop_loss)
    
    @property
    def reward_points(self) -> float:
        """Размер потенциальной прибыли в пунктах."""
        return abs(self.take_profit - self.entry_price)
    
    def __repr__(self) -> str:
        dir_str = "LONG" if self.direction == Direction.LONG else "SHORT"
        return (f"TradeSignal({dir_str}, entry={self.entry_price:.2f}, "
                f"SL={self.stop_loss:.2f}, TP={self.take_profit:.2f}, "
                f"RR={self.risk_reward:.2f})")


@dataclass
class Trade:
    """
    Модель совершенной сделки.
    
    Attributes:
        signal: Сигнал, породивший сделку
        entry_timestamp: Время входа
        entry_price: Фактическая цена входа (с учетом проскальзывания)
        exit_timestamp: Время выхода
        exit_price: Фактическая цена выхода
        size: Размер позиции (контракты)
        pnl: Прибыль/убыток в рублях
        pnl_percent: Прибыль/убыток в процентах
        exit_reason: Причина выхода (TP, SL, Time)
    """
    signal: TradeSignal
    entry_timestamp: datetime
    entry_price: float
    exit_timestamp: Optional[datetime] = None
    exit_price: Optional[float] = None
    size: float = 1.0
    pnl: float = 0.0
    pnl_percent: float = 0.0
    exit_reason: Optional[str] = None
    
    @property
    def is_open(self) -> bool:
        """Открыта ли сделка."""
        return self.exit_timestamp is None
    
    def close(self, exit_timestamp: datetime, exit_price: float, reason: str) -> None:
        """Закрыть сделку."""
        self.exit_timestamp = exit_timestamp
        self.exit_price = exit_price
        self.exit_reason = reason
        
        # Расчет PnL
        if self.signal.direction == Direction.LONG:
            self.pnl = (exit_price - self.entry_price) * self.size
        else:
            self.pnl = (self.entry_price - exit_price) * self.size
        
        self.pnl_percent = (self.pnl / (self.entry_price * self.size)) * 100