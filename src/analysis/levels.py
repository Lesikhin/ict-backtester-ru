"""
Детектор уровней ликвидности (поддержки/сопротивления).

Использует кластеризацию свинговых точек для нахождения зон,
где цена формировала базы и где происходит наибольшая активность.
"""

import logging
from typing import List
import pandas as pd
import numpy as np
from sklearn.cluster import DBSCAN

from src.data.models import SwingPoint, LiquidityLevel, Direction

logger = logging.getLogger(__name__)


class LiquidityLevelDetector:
    """
    Детектор уровней ликвидности через кластеризацию.
    
    Использует алгоритм DBSCAN для группировки свинговых точек
    в кластеры, которые представляют собой уровни поддержки/сопротивления.
    """
    
    def __init__(self, cluster_distance_percent: float = 0.5, min_touches: int = 3):
        """
        Инициализация детектора.
        
        Args:
            cluster_distance_percent: Максимальное расстояние между точками в кластере (%)
            min_touches: Минимальное количество точек для формирования уровня
        """
        self.cluster_distance_percent = cluster_distance_percent
        self.min_touches = min_touches
        logger.debug(
            f"LiquidityLevelDetector инициализирован: "
            f"distance={cluster_distance_percent}%, min_touches={min_touches}"
        )
    
    def detect(self, df: pd.DataFrame, swings: List[SwingPoint]) -> List[LiquidityLevel]:
        """
        Найти все уровни ликвидности.
        
        Args:
            df: DataFrame с данными
            swings: Список свинговых точек
            
        Returns:
            Список найденных LiquidityLevel
        """
        if len(swings) < self.min_touches:
            logger.warning("Недостаточно свингов для кластеризации")
            return []
        
        # Разделяем свинги по типу
        swing_highs = [s for s in swings if s.direction == Direction.LONG]
        swing_lows = [s for s in swings if s.direction == Direction.SHORT]
        
        levels = []
        
        # Кластеризуем Swing Highs (зоны сопротивления)
        if len(swing_highs) >= self.min_touches:
            high_levels = self._cluster_swings(swing_highs, df)
            levels.extend(high_levels)
        
        # Кластеризуем Swing Lows (зоны поддержки)
        if len(swing_lows) >= self.min_touches:
            low_levels = self._cluster_swings(swing_lows, df)
            levels.extend(low_levels)
        
        # Сортируем по количеству касаний
        levels.sort(key=lambda l: l.touches, reverse=True)
        
        logger.info(f"Найдено {len(levels)} уровней ликвидности")
        return levels
    
    def _cluster_swings(
        self, 
        swings: List[SwingPoint], 
        df: pd.DataFrame
    ) -> List[LiquidityLevel]:
        """Кластеризовать свинговые точки в уровни."""
        
        # Извлекаем цены для кластеризации
        prices = np.array([[s.price] for s in swings])
        
        # Рассчитываем eps для DBSCAN в абсолютных значениях
        mean_price = np.mean(prices)
        eps_absolute = mean_price * (self.cluster_distance_percent / 100)
        
        # Кластеризация
        clustering = DBSCAN(eps=eps_absolute, min_samples=self.min_touches).fit(prices)
        
        levels = []
        labels = clustering.labels_
        
        # Группируем свинги по кластерам
        unique_labels = set(labels)
        unique_labels.discard(-1)  # -1 означает шум
        
        for label in unique_labels:
            cluster_mask = labels == label
            cluster_swings = [swings[i] for i in range(len(swings)) if cluster_mask[i]]
            
            if len(cluster_swings) >= self.min_touches:
                level = self._create_level_from_cluster(cluster_swings, df)
                levels.append(level)
        
        return levels
    
    def _create_level_from_cluster(
        self, 
        cluster_swings: List[SwingPoint], 
        df: pd.DataFrame
    ) -> LiquidityLevel:
        """Создать уровень ликвидности из кластера свингов."""
        
        prices = [s.price for s in cluster_swings]
        
        price_mean = float(np.mean(prices))
        price_std = float(np.std(prices))
        
        # Границы уровня
        top = price_mean + price_std
        bottom = price_mean - price_std
        
        # Временные границы
        timestamps = [s.timestamp for s in cluster_swings]
        first_touch = min(timestamps)
        last_touch = max(timestamps)
        
        level = LiquidityLevel(
            price=price_mean,
            top=top,
            bottom=bottom,
            touches=len(cluster_swings),
            swing_points=cluster_swings,
            first_touch=first_touch,
            last_touch=last_touch
        )
        
        logger.debug(f"Создан уровень: {level}")
        return level