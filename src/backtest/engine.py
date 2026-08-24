"""
Бэктест-движок для прогонки стратегий по историческим данным.
"""

import logging
from typing import List, Dict
import pandas as pd
import numpy as np

from src.data.models import TradeSignal, Trade, Direction
from src.strategies.base import BaseStrategy
from src.backtest.metrics import MetricsCalculator

logger = logging.getLogger(__name__)


class BacktestEngine:
    """Движок бэктеста."""
    
    def __init__(self, config: dict):
        self.initial_capital = config.get('initial_capital', 1000000)
        self.commission_percent = config.get('commission_percent', 0.05)
        self.slippage_percent = config.get('slippage_percent', 0.02)
        
        futures_config = config.get('futures', {})
        self.contract_multiplier = futures_config.get('contract_multiplier', 1)
        
        self.capital = self.initial_capital
        self.trades: List[Trade] = []
        self.equity_curve: List[Dict] = []
        
        logger.info(f"BacktestEngine инициализирован: капитал={self.initial_capital}")
    
    def run(
        self,
        df: pd.DataFrame,
        strategy: BaseStrategy,
        signals: List[TradeSignal]
    ) -> Dict:
        logger.info(f"Запуск бэктеста стратегии: {strategy.name}")
        logger.info(f"Количество сигналов: {len(signals)}")
        
        self.capital = self.initial_capital
        self.trades = []
        self.equity_curve = []
        
        signals_sorted = sorted(signals, key=lambda s: s.timestamp)
        
        skipped_no_index = 0
        skipped_no_trade = 0
        
        for signal in signals_sorted:
            signal_idx = self._find_signal_index(df, signal.timestamp)
            
            if signal_idx is None:
                skipped_no_index += 1
                continue
                
            if signal_idx >= len(df) - 1:
                skipped_no_index += 1
                continue
            
            trade = self._open_trade(df, signal, signal_idx)
            
            if not trade:
                skipped_no_trade += 1
                continue
            
            self._close_trade(df, trade, signal_idx + 1)
            self.trades.append(trade)
        
        if skipped_no_index > 0:
            logger.warning(f"Пропущено сигналов (нет индекса): {skipped_no_index}")
        if skipped_no_trade > 0:
            logger.warning(f"Пропущено сигналов (ошибка открытия): {skipped_no_trade}")
            
        metrics = self._calculate_metrics()
        logger.info(f"Бэктест завершен. Сделок: {len(self.trades)}")
        
        return {
            'strategy_name': strategy.name,
            'trades': self.trades,
            'equity_curve': self.equity_curve,
            'metrics': metrics
        }
    
    def _find_signal_index(self, df: pd.DataFrame, timestamp) -> int:
        """Найти индекс сигнала в DataFrame (устойчиво к типам данных)."""
        try:
            ts = pd.to_datetime(timestamp)
            # get_indexer надежнее, чем get_loc, для поиска ближайшего значения
            idx = df.index.get_indexer([ts], method='nearest')[0]
            return int(idx)
        except Exception as e:
            logger.debug(f"Не удалось найти индекс для {timestamp}: {e}")
            return None
    
    def _open_trade(self, df: pd.DataFrame, signal: TradeSignal, idx: int) -> Trade:
        """Открыть сделку."""
        if signal.direction == Direction.LONG:
            entry_price = signal.entry_price * (1 + self.slippage_percent / 100)
        else:
            entry_price = signal.entry_price * (1 - self.slippage_percent / 100)
        
        # Упрощенный и надежный расчет размера позиции
        # Фиксируем риск в деньгах (например, 2000 руб. на сделку для теста)
        risk_amount = 5000.0 
        risk_per_unit = abs(entry_price - signal.stop_loss)
        
        if risk_per_unit == 0:
            logger.debug(f"risk_per_unit == 0 для сигнала в {signal.timestamp}")
            return None
        
        size = risk_amount / risk_per_unit
        
        # Если размер получился меньше 1, ставим минимум 1 контракт/акцию
        if size < 1.0:
            size = 1.0
            
        trade = Trade(
            signal=signal,
            entry_timestamp=df.index[idx],
            entry_price=entry_price,
            size=size
        )
        
        self.equity_curve.append({
            'timestamp': df.index[idx],
            'equity': self.capital,
            'trade_open': True
        })
        
        return trade
    
    def _close_trade(self, df: pd.DataFrame, trade: Trade, start_idx: int) -> None:
        """Закрыть сделку по TP, SL или концу данных."""
        
        for i in range(start_idx, len(df)):
            candle_high = df['high'].iloc[i]
            candle_low = df['low'].iloc[i]
            timestamp = df.index[i]
            
            # Проверка Stop Loss
            if trade.signal.direction == Direction.LONG:
                if candle_low <= trade.signal.stop_loss:
                    exit_price = trade.signal.stop_loss * (1 - self.slippage_percent / 100)
                    self._finalize_trade(trade, timestamp, exit_price, 'SL')
                    return
            else:
                if candle_high >= trade.signal.stop_loss:
                    exit_price = trade.signal.stop_loss * (1 + self.slippage_percent / 100)
                    self._finalize_trade(trade, timestamp, exit_price, 'SL')
                    return
            
            # Проверка Take Profit
            if trade.signal.direction == Direction.LONG:
                if candle_high >= trade.signal.take_profit:
                    exit_price = trade.signal.take_profit * (1 - self.slippage_percent / 100)
                    self._finalize_trade(trade, timestamp, exit_price, 'TP')
                    return
            else:
                if candle_low <= trade.signal.take_profit:
                    exit_price = trade.signal.take_profit * (1 + self.slippage_percent / 100)
                    self._finalize_trade(trade, timestamp, exit_price, 'TP')
                    return
        
        # Если не сработал ни TP, ни SL - закрываем по последней цене
        exit_price = df['close'].iloc[-1]
        self._finalize_trade(trade, df.index[-1], exit_price, 'END')
    
    def _finalize_trade(self, trade: Trade, exit_timestamp, exit_price: float, reason: str) -> None:
        """Завершить сделку."""
        trade.close(exit_timestamp, exit_price, reason)
        
        commission = abs(trade.pnl) * (self.commission_percent / 100)
        trade.pnl -= commission
        
        self.capital += trade.pnl
        
        self.equity_curve.append({
            'timestamp': exit_timestamp,
            'equity': self.capital,
            'trade_close': True,
            'pnl': trade.pnl
        })
    
    def _calculate_metrics(self) -> Dict:
        calculator = MetricsCalculator(self.trades, self.initial_capital)
        return calculator.calculate_all()