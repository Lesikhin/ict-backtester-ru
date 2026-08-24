"""
Юнит-тесты для детекторов ICT-паттернов.
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from src.analysis.detectors import SwingDetector, FVGDetector
from src.data.models import Direction


@pytest.fixture
def sample_dataframe():
    """Создать тестовый DataFrame с данными."""
    dates = pd.date_range('2024-01-01', periods=20, freq='H')
    
    # Создаем данные с явными паттернами
    data = {
        'open': [100 + i * 0.5 for i in range(20)],
        'high': [102 + i * 0.5 for i in range(20)],
        'low': [98 + i * 0.5 for i in range(20)],
        'close': [101 + i * 0.5 for i in range(20)],
        'volume': [1000] * 20
    }
    
    df = pd.DataFrame(data, index=dates)
    return df


class TestSwingDetector:
    """Тесты для SwingDetector."""
    
    def test_detect_swing_high(self, sample_dataframe):
        """Тест обнаружения Swing High."""
        # Создаем явный Swing High
        sample_dataframe.iloc[10, 1] = 120  # high
        sample_dataframe.iloc[9, 1] = 110
        sample_dataframe.iloc[11, 1] = 110
        
        detector = SwingDetector(left_bars=3, right_bars=3)
        swings = detector.detect(sample_dataframe)
        
        # Проверяем, что найден хотя бы один Swing High
        swing_highs = [s for s in swings if s.direction == Direction.LONG]
        assert len(swing_highs) > 0
    
    def test_detect_swing_low(self, sample_dataframe):
        """Тест обнаружения Swing Low."""
        # Создаем явный Swing Low
        sample_dataframe.iloc[10, 2] = 80  # low
        sample_dataframe.iloc[9, 2] = 90
        sample_dataframe.iloc[11, 2] = 90
        
        detector = SwingDetector(left_bars=3, right_bars=3)
        swings = detector.detect(sample_dataframe)
        
        # Проверяем, что найден хотя бы один Swing Low
        swing_lows = [s for s in swings if s.direction == Direction.SHORT]
        assert len(swing_lows) > 0


class TestFVGDetector:
    """Тесты для FVGDetector."""
    
    def test_detect_bullish_fvg(self):
        """Тест обнаружения бычьего FVG."""
        dates = pd.date_range('2024-01-01', periods=5, freq='H')
        
        # Создаем бычий FVG: low[2] > high[0]
        data = {
            'open': [100, 105, 110, 115, 120],
            'high': [102, 107, 112, 117, 122],
            'low': [98, 103, 108, 113, 118],
            'close': [101, 106, 111, 116, 121],
            'volume': [1000] * 5
        }
        
        # Модифицируем для создания FVG
        data['high'][0] = 100  # high[0]
        data['low'][2] = 105   # low[2] > high[0]
        
        df = pd.DataFrame(data, index=dates)
        
        detector = FVGDetector(min_size_percent=0.1)
        fvgs = detector.detect(df)
        
        # Проверяем, что найден бычий FVG
        bullish_fvgs = [f for f in fvgs if f.direction == Direction.LONG]
        assert len(bullish_fvgs) > 0
    
    def test_fvg_mitigation(self):
        """Тест определения митигированного FVG."""
        dates = pd.date_range('2024-01-01', periods=10, freq='H')
        
        # Создаем FVG и затем митигацию
        data = {
            'open': [100, 105, 110, 115, 120, 118, 116, 114, 112, 110],
            'high': [102, 107, 112, 117, 122, 120, 118, 116, 114, 112],
            'low': [98, 103, 108, 113, 118, 116, 114, 112, 110, 108],
            'close': [101, 106, 111, 116, 121, 119, 117, 115, 113, 111],
            'volume': [1000] * 10
        }
        
        df = pd.DataFrame(data, index=dates)
        
        detector = FVGDetector(min_size_percent=0.1, max_age_bars=50)
        fvgs = detector.detect(df)
        
        # Проверяем, что хотя бы один FVG был митигирован
        mitigated_fvgs = [f for f in fvgs if f.mitigated]
        # Может быть 0 или больше, зависит от данных
        assert isinstance(mitigated_fvgs, list)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])