"""
Реестр и фабрика стратегий.
"""

from src.strategies.base import BaseStrategy
from src.strategies.sweep_mss import SweepMSSStrategy
from src.strategies.power_of_3 import PowerOf3Strategy
from src.strategies.mmxm import MMXMStrategy

STRATEGY_REGISTRY = {
    "sweep_mss": SweepMSSStrategy,
    "power_of_3": PowerOf3Strategy,
    "mmxm": MMXMStrategy,
}


def get_strategy(name: str, config: dict) -> BaseStrategy:
    """Фабричный метод для создания экземпляра стратегии."""
    if name not in STRATEGY_REGISTRY:
        raise ValueError(f"Неизвестная стратегия: {name}. Доступные: {list(STRATEGY_REGISTRY.keys())}")
    
    strategy_class = STRATEGY_REGISTRY[name]
    return strategy_class(config)