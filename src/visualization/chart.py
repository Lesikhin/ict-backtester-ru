"""
Визуализация результатов бэктеста через Plotly.
"""

import logging
from typing import List, Dict
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from src.data.models import Trade, FairValueGap, LiquidityLevel, Direction

logger = logging.getLogger(__name__)


class ChartRenderer:
    """Рендерер интерактивных графиков."""
    
    def __init__(self, config: dict):
        self.output_format = config.get('output_format', 'html')
        self.show_fvg = config.get('show_fvg', True)
        self.show_levels = config.get('show_levels', True)
        self.show_entries = config.get('show_entries', True)
        self.max_candles = config.get('max_candles_display', 500)
    
    def render_backtest_results(
        self,
        df: pd.DataFrame,
        trades: List[Trade],
        fvgs: List[FairValueGap],
        levels: List[LiquidityLevel],
        metrics: Dict,
        output_path: str = "backtest_results.html"
    ) -> None:
        """
        Отрисовать результаты бэктеста.
        
        Args:
            df: DataFrame с данными
            trades: Список сделок
            fvgs: Список FVG
            levels: Список уровней
            metrics: Метрики бэктеста
            output_path: Путь для сохранения графика
        """
        logger.info("Создание интерактивного графика...")
        
        # Ограничиваем количество свечей
        if len(df) > self.max_candles:
            df = df.tail(self.max_candles)
        
        # Создаем subplot с 2 графиками: свечи + equity curve
        fig = make_subplots(
            rows=2, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.03,
            row_heights=[0.7, 0.3],
            subplot_titles=('Price Action', 'Equity Curve')
        )
        
        # 1. Свечи
        self._add_candlesticks(fig, df, row=1)
        
        # 2. FVG
        if self.show_fvg:
            self._add_fvgs(fig, fvgs, df.index, row=1)
        
        # 3. Уровни
        if self.show_levels:
            self._add_levels(fig, levels, df.index, row=1)
        
        # 4. Точки входа/выхода
        if self.show_entries:
            self._add_trades(fig, trades, row=1)
        
        # 5. Equity curve
        self._add_equity_curve(fig, trades, row=2)
        
        # Добавляем метрики в заголовок
        title = self._create_title(metrics)
        fig.update_layout(title=title, height=800, showlegend=True)
        
        # Сохраняем
        if self.output_format == 'html':
            fig.write_html(output_path)
            logger.info(f"График сохранен: {output_path}")
        else:
            fig.write_image(output_path)
            logger.info(f"График сохранен: {output_path}")
    
    def _add_candlesticks(self, fig, df: pd.DataFrame, row: int) -> None:
        """Добавить свечи."""
        fig.add_trace(
            go.Candlestick(
                x=df.index,
                open=df['open'],
                high=df['high'],
                low=df['low'],
                close=df['close'],
                name='OHLC'
            ),
            row=row, col=1
        )
    
    def _add_fvgs(self, fig, fvgs: List[FairValueGap], timestamps, row: int) -> None:
        """Добавить FVG."""
        for fvg in fvgs[-50:]:  # Последние 50 FVG
            if fvg.index < len(timestamps) - 10:
                color = 'rgba(0, 255, 0, 0.1)' if fvg.direction == Direction.LONG else 'rgba(255, 0, 0, 0.1)'
                
                fig.add_shape(
                    type="rect",
                    x0=timestamps[fvg.index],
                    x1=timestamps[-1],
                    y0=fvg.bottom,
                    y1=fvg.top,
                    fillcolor=color,
                    line=dict(width=0),
                    row=row, col=1
                )
    
    def _add_levels(self, fig, levels: List[LiquidityLevel], timestamps, row: int) -> None:
        """Добавить уровни."""
        for level in levels[-10:]:  # Последние 10 уровней
            fig.add_hline(
                y=level.price,
                line_dash="dash",
                line_color="blue",
                annotation_text=f"L{level.touches}",
                row=row, col=1
            )
    
    def _add_trades(self, fig, trades: List[Trade], row: int) -> None:
        """Добавить точки входа/выхода."""
        entries_x = []
        entries_y = []
        entries_colors = []
        
        exits_x = []
        exits_y = []
        exits_colors = []
        
        for trade in trades:
            # Вход
            entries_x.append(trade.entry_timestamp)
            entries_y.append(trade.entry_price)
            entries_colors.append('green' if trade.signal.direction == Direction.LONG else 'red')
            
            # Выход
            if trade.exit_timestamp:
                exits_x.append(trade.exit_timestamp)
                exits_y.append(trade.exit_price)
                exits_colors.append('lime' if trade.pnl > 0 else 'orange')
        
        # Точки входа
        fig.add_trace(
            go.Scatter(
                x=entries_x,
                y=entries_y,
                mode='markers',
                marker=dict(size=10, color=entries_colors, symbol='triangle-up'),
                name='Entry',
                showlegend=False
            ),
            row=row, col=1
        )
        
        # Точки выхода
        fig.add_trace(
            go.Scatter(
                x=exits_x,
                y=exits_y,
                mode='markers',
                marker=dict(size=10, color=exits_colors, symbol='x'),
                name='Exit',
                showlegend=False
            ),
            row=row, col=1
        )
    
    def _add_equity_curve(self, fig, trades: List[Trade], row: int) -> None:
        """Добавить equity curve."""
        equity = [1000000]  # Начальный капитал
        timestamps = [trades[0].entry_timestamp] if trades else []
        
        for trade in trades:
            equity.append(equity[-1] + trade.pnl)
            timestamps.append(trade.exit_timestamp)
        
        fig.add_trace(
            go.Scatter(
                x=timestamps,
                y=equity,
                mode='lines',
                line=dict(color='blue', width=2),
                name='Equity'
            ),
            row=row, col=1
        )
    
    def _create_title(self, metrics: Dict) -> str:
        """Создать заголовок с метриками."""
        return (
            f"ICT Backtest Results | "
            f"Trades: {metrics['total_trades']} | "
            f"Win Rate: {metrics['win_rate']:.1f}% | "
            f"Return: {metrics['total_return_percent']:.2f}% | "
            f"Profit Factor: {metrics['profit_factor']:.2f} | "
            f"Max DD: {metrics['max_drawdown']:.2f}%"
        )