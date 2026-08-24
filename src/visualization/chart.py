"""
Визуализация результатов бэктеста через Plotly.
Масштабируемый график с range slider для навигации по всему периоду.
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
        self.max_levels_display = 5  # Максимум уровней для отображения
    
    def render_backtest_results(
        self,
        df: pd.DataFrame,
        trades: List[Trade],
        fvgs: List[FairValueGap],
        levels: List[LiquidityLevel],
        metrics: Dict,
        output_path: str = "backtest_results.html"
    ) -> None:
        """Отрисовать результаты бэктеста."""
        
        logger.info("Создание интерактивного графика...")
        
        # Показываем ВСЕ данные (без ограничения)
        df_display = df
        
        # Создаем subplot: свечи (75%) + equity curve (25%)
        fig = make_subplots(
            rows=2, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.03,
            row_heights=[0.75, 0.25],
            subplot_titles=('Price Action with Trades', 'Equity Curve')
        )
        
        # 1. Свечи OHLC
        self._add_candlesticks(fig, df_display, row=1)
        
        # 2. Уровни ликвидности (только релевантные)
        if self.show_levels and levels:
            self._add_levels(fig, levels, df_display, row=1)
        
        # 3. FVG (последние 20, полупрозрачные зоны)
        if self.show_fvg and fvgs:
            self._add_fvgs(fig, fvgs, df_display, row=1)
        
        # 4. Все точки входа/выхода
        if self.show_entries and trades:
            self._add_trades(fig, trades, row=1)
        
        # 5. Equity curve
        self._add_equity_curve(fig, trades, row=2)
        
        # Заголовок с метриками
        title = self._create_title(metrics)
        
        # Настройки layout с range slider
        fig.update_layout(
            title=dict(
                text=title,
                x=0.5,
                xanchor='center',
                font=dict(size=16)
            ),
            height=1000,
            showlegend=True,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1,
                font=dict(size=10)
            ),
            xaxis_rangeslider_visible=True,  # Включаем range slider
            xaxis_rangeslider_thickness=0.05,
            template="plotly_white",
            hovermode='x unified'
        )
        
        # Сохраняем
        if self.output_format == 'html':
            fig.write_html(output_path, include_plotlyjs='cdn')
            logger.info(f"График сохранен: {output_path}")
        else:
            fig.write_image(output_path, width=1920, height=1080)
            logger.info(f"График сохранен: {output_path}")
    
    def _add_candlesticks(self, fig, df: pd.DataFrame, row: int) -> None:
        """Добавить свечи OHLC."""
        fig.add_trace(
            go.Candlestick(
                x=df.index,
                open=df['open'],
                high=df['high'],
                low=df['low'],
                close=df['close'],
                name='OHLC',
                increasing_line_color='#26a69a',
                decreasing_line_color='#ef5350',
                increasing_fillcolor='#26a69a',
                decreasing_fillcolor='#ef5350',
                opacity=0.7
            ),
            row=row, col=1
        )
    
    def _add_levels(self, fig, levels: List[LiquidityLevel], df: pd.DataFrame, row: int) -> None:
        """Добавить только релевантные уровни (в диапазоне цены ±15%)."""
        
        # Получаем диапазон цен на графике
        price_min = df['low'].min()
        price_max = df['high'].max()
        price_range = price_max - price_min
        price_center = (price_max + price_min) / 2
        
        # Фильтруем уровни: только те, что находятся в диапазоне ±15% от центра
        relevant_levels = []
        for level in levels:
            if abs(level.price - price_center) <= (price_range * 0.15):
                relevant_levels.append(level)
        
        # Сортируем по количеству касаний и берем топ-5
        relevant_levels.sort(key=lambda l: l.touches, reverse=True)
        top_levels = relevant_levels[:self.max_levels_display]
        
        colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA07A', '#98D8C8']
        
        for i, level in enumerate(top_levels):
            color = colors[i % len(colors)]
            
            # Горизонтальная линия
            fig.add_hline(
                y=level.price,
                line_dash="dash",
                line_color=color,
                line_width=2,
                annotation_text=f"L{i+1} ({level.touches})",
                annotation_position="right",
                annotation_font_size=10,
                row=row, col=1
            )
    
    def _add_fvgs(self, fig, fvgs: List[FairValueGap], df: pd.DataFrame, row: int) -> None:
        """Добавить FVG как полупрозрачные зоны (последние 20)."""
        
        # Берем последние 20 FVG
        recent_fvgs = fvgs[-20:] if len(fvgs) > 20 else fvgs
        
        for fvg in recent_fvgs:
            if fvg.index < len(df.index):
                # Определяем цвет
                if fvg.direction == Direction.LONG:
                    color = 'rgba(38, 166, 154, 0.1)'  # Зеленый полупрозрачный
                else:
                    color = 'rgba(239, 83, 80, 0.1)'   # Красный полупрозрачный
                
                # Добавляем прямоугольник (только на 50 свечей вперед, не до конца)
                end_idx = min(fvg.index + 50, len(df.index) - 1)
                
                fig.add_shape(
                    type="rect",
                    x0=df.index[fvg.index],
                    x1=df.index[end_idx],
                    y0=fvg.bottom,
                    y1=fvg.top,
                    fillcolor=color,
                    line=dict(width=0),
                    row=row, col=1
                )
    
    def _add_trades(self, fig, trades: List[Trade], row: int) -> None:
        """Добавить все точки входа/выхода с маленькими маркерами."""
        
        entries_x = []
        entries_y = []
        entries_colors = []
        entries_text = []
        
        exits_x = []
        exits_y = []
        exits_colors = []
        exits_text = []
        
        for trade in trades:
            # Вход
            entries_x.append(trade.entry_timestamp)
            entries_y.append(trade.entry_price)
            entries_colors.append('#26a69a' if trade.signal.direction == Direction.LONG else '#ef5350')
            entries_text.append(f"Entry: {trade.entry_price:.2f}<br>Time: {trade.entry_timestamp}")
            
            # Выход
            if trade.exit_timestamp and trade.exit_price:
                exits_x.append(trade.exit_timestamp)
                exits_y.append(trade.exit_price)
                exits_colors.append('#00ff00' if trade.pnl > 0 else '#ff6600')
                exits_text.append(f"Exit: {trade.exit_price:.2f}<br>PnL: {trade.pnl:.0f} руб.")
        
        # Точки входа (маленькие треугольники)
        if entries_x:
            fig.add_trace(
                go.Scatter(
                    x=entries_x,
                    y=entries_y,
                    mode='markers',
                    marker=dict(
                        size=6,
                        color=entries_colors,
                        symbol='triangle-up',
                        line=dict(width=0.5, color='black')
                    ),
                    name='Entry',
                    text=entries_text,
                    hoverinfo='text',
                    showlegend=True
                ),
                row=row, col=1
            )
        
        # Точки выхода (маленькие крестики)
        if exits_x:
            fig.add_trace(
                go.Scatter(
                    x=exits_x,
                    y=exits_y,
                    mode='markers',
                    marker=dict(
                        size=6,
                        color=exits_colors,
                        symbol='x',
                        line=dict(width=1, color='black')
                    ),
                    name='Exit',
                    text=exits_text,
                    hoverinfo='text',
                    showlegend=True
                ),
                row=row, col=1
            )
    
    def _add_equity_curve(self, fig, trades: List[Trade], row: int) -> None:
        """Добавить equity curve."""
        
        if not trades:
            return
        
        # Строим equity curve
        equity = [1000000]  # Начальный капитал
        timestamps = [trades[0].entry_timestamp]
        
        for trade in trades:
            equity.append(equity[-1] + trade.pnl)
            timestamps.append(trade.exit_timestamp)
        
        fig.add_trace(
            go.Scatter(
                x=timestamps,
                y=equity,
                mode='lines',
                line=dict(color='#1f77b4', width=2),
                name='Equity Curve',
                fill='tozeroy',
                fillcolor='rgba(31, 119, 180, 0.1)'
            ),
            row=row, col=1
        )
        
        # Добавляем горизонтальную линию начального капитала
        fig.add_hline(
            y=1000000,
            line_dash="dot",
            line_color="gray",
            line_width=1,
            annotation_text="Initial",
            annotation_position="left",
            row=row, col=1
        )
    
    def _create_title(self, metrics: Dict) -> str:
        """Создать заголовок с метриками."""
        return (
            f"<b>ICT Backtest Results</b><br>"
            f"Trades: {metrics['total_trades']} | "
            f"Win Rate: {metrics['win_rate']:.1f}% | "
            f"Return: {metrics['total_return_percent']:.2f}% | "
            f"Profit Factor: {metrics['profit_factor']:.2f} | "
            f"Max DD: {metrics['max_drawdown']:.2f}%"
        )