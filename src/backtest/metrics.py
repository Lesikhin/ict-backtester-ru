"""
Расчет метрик бэктеста.
"""

import logging
from typing import List, Dict
import numpy as np
import pandas as pd

from src.data.models import Trade, Direction

logger = logging.getLogger(__name__)


class MetricsCalculator:
    """Калькулятор метрик бэктеста."""
    
    def __init__(self, trades: List[Trade], initial_capital: float):
        self.trades = trades
        self.initial_capital = initial_capital
    
    def calculate_all(self) -> Dict:
        """Рассчитать все метрики."""
        if not self.trades:
            return self._empty_metrics()
        
        return {
            'total_trades': len(self.trades),
            'winning_trades': self._count_winning_trades(),
            'losing_trades': self._count_losing_trades(),
            'win_rate': self._calculate_win_rate(),
            'total_pnl': self._calculate_total_pnl(),
            'total_return_percent': self._calculate_total_return(),
            'profit_factor': self._calculate_profit_factor(),
            'average_win': self._calculate_average_win(),
            'average_loss': self._calculate_average_loss(),
            'max_drawdown': self._calculate_max_drawdown(),
            'sharpe_ratio': self._calculate_sharpe_ratio(),
            'expectancy': self._calculate_expectancy(),
        }
    
    def _empty_metrics(self) -> Dict:
        return {
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'win_rate': 0.0,
            'total_pnl': 0.0,
            'total_return_percent': 0.0,
            'profit_factor': 0.0,
            'average_win': 0.0,
            'average_loss': 0.0,
            'max_drawdown': 0.0,
            'sharpe_ratio': 0.0,
            'expectancy': 0.0,
        }
    
    def _count_winning_trades(self) -> int:
        return sum(1 for t in self.trades if t.pnl > 0)
    
    def _count_losing_trades(self) -> int:
        return sum(1 for t in self.trades if t.pnl < 0)
    
    def _calculate_win_rate(self) -> float:
        if not self.trades:
            return 0.0
        winning = self._count_winning_trades()
        return (winning / len(self.trades)) * 100
    
    def _calculate_total_pnl(self) -> float:
        return sum(t.pnl for t in self.trades)
    
    def _calculate_total_return(self) -> float:
        total_pnl = self._calculate_total_pnl()
        return (total_pnl / self.initial_capital) * 100
    
    def _calculate_profit_factor(self) -> float:
        gross_profit = sum(t.pnl for t in self.trades if t.pnl > 0)
        gross_loss = abs(sum(t.pnl for t in self.trades if t.pnl < 0))
        
        if gross_loss == 0:
            return float('inf') if gross_profit > 0 else 0.0
        
        return gross_profit / gross_loss
    
    def _calculate_average_win(self) -> float:
        wins = [t.pnl for t in self.trades if t.pnl > 0]
        return np.mean(wins) if wins else 0.0
    
    def _calculate_average_loss(self) -> float:
        losses = [t.pnl for t in self.trades if t.pnl < 0]
        return np.mean(losses) if losses else 0.0
    
    def _calculate_max_drawdown(self) -> float:
        """Рассчитать максимальную просадку."""
        equity = self.initial_capital
        peak = equity
        max_dd = 0.0
        
        for trade in self.trades:
            equity += trade.pnl
            if equity > peak:
                peak = equity
            
            drawdown = ((peak - equity) / peak) * 100
            if drawdown > max_dd:
                max_dd = drawdown
        
        return max_dd
    
    def _calculate_sharpe_ratio(self) -> float:
        """Рассчитать коэффициент Шарпа (упрощенно)."""
        if not self.trades:
            return 0.0
        
        returns = [t.pnl_percent for t in self.trades]
        mean_return = np.mean(returns)
        std_return = np.std(returns)
        
        if std_return == 0:
            return 0.0
        
        # Упрощенная формула Шарпа (без безрисковой ставки)
        return mean_return / std_return
    
    def _calculate_expectancy(self) -> float:
        """Рассчитать математическое ожидание."""
        if not self.trades:
            return 0.0
        
        win_rate = self._calculate_win_rate() / 100
        avg_win = self._calculate_average_win()
        avg_loss = abs(self._calculate_average_loss())
        
        return (win_rate * avg_win) - ((1 - win_rate) * avg_loss)