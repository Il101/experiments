"""
Тесты для технических индикаторов.

Покрывает:
- SMA, EMA
- ATR, True Range
- Bollinger Bands
- VWAP
- RSI
- OBV
- Chandelier Exit
- Donchian Channels
- Корреляция
- Swing Highs/Lows
"""

import pytest
import numpy as np
from unittest.mock import patch
from datetime import datetime, timedelta

from breakout_bot.indicators.technical import (
    sma, ema, true_range, atr, bollinger_bands, bollinger_band_width,
    donchian_channels, vwap, rsi, obv, chandelier_exit, calculate_correlation,
    volume_surge_ratio, swing_highs_lows
)
from breakout_bot.data.models import Candle


class TestSMA:
    """Тесты для Simple Moving Average."""
    
    def test_sma_basic(self):
        """Тест базового расчета SMA."""
        values = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        period = 3
        
        result = sma(values, period)
        
        # Первые period-1 значения должны быть NaN
        assert np.isnan(result[0])
        assert np.isnan(result[1])
        
        # Остальные значения должны быть рассчитаны
        assert result[2] == 2.0  # (1+2+3)/3
        assert result[3] == 3.0  # (2+3+4)/3
        assert result[9] == 9.0  # (8+9+10)/3
    
    def test_sma_insufficient_data(self):
        """Тест SMA с недостаточными данными."""
        values = [1, 2]
        period = 5
        
        result = sma(values, period)
        
        # Все значения должны быть NaN
        assert all(np.isnan(result))
    
    def test_sma_single_value(self):
        """Тест SMA с одним значением."""
        values = [5]
        period = 1
        
        result = sma(values, period)
        
        assert result[0] == 5.0
    
    def test_sma_numpy_array(self):
        """Тест SMA с numpy массивом."""
        values = np.array([1, 2, 3, 4, 5])
        period = 2
        
        result = sma(values, period)
        
        assert np.isnan(result[0])
        assert result[1] == 1.5
        assert result[2] == 2.5
        assert result[3] == 3.5
        assert result[4] == 4.5


class TestEMA:
    """Тесты для Exponential Moving Average."""
    
    def test_ema_basic(self):
        """Тест базового расчета EMA."""
        values = [1, 2, 3, 4, 5]
        period = 3
        
        result = ema(values, period)
        
        # Первое значение должно быть равно первому входному значению
        assert result[0] == 1.0
        
        # Остальные значения должны быть рассчитаны
        assert not np.isnan(result[1])
        assert not np.isnan(result[2])
        assert not np.isnan(result[3])
        assert not np.isnan(result[4])
    
    def test_ema_empty_array(self):
        """Тест EMA с пустым массивом."""
        values = []
        period = 3
        
        result = ema(values, period)
        
        assert len(result) == 0
    
    def test_ema_single_value(self):
        """Тест EMA с одним значением."""
        values = [5]
        period = 3
        
        result = ema(values, period)
        
        assert result[0] == 5.0
    
    def test_ema_with_nan_values(self):
        """Тест EMA с NaN значениями."""
        values = [1, np.nan, 3, 4, 5]
        period = 3
        
        result = ema(values, period)
        
        # Первое значение должно быть 1
        assert result[0] == 1.0
        
        # Второе значение должно быть равно предыдущему (NaN заменено)
        assert result[1] == result[0]
        
        # Третье значение должно быть рассчитано
        assert not np.isnan(result[2])


class TestTrueRange:
    """Тесты для True Range."""
    
    def test_true_range_basic(self):
        """Тест базового расчета True Range."""
        high = np.array([10, 12, 11, 13, 14])
        low = np.array([8, 9, 10, 11, 12])
        close = np.array([9, 11, 10, 12, 13])
        
        result = true_range(high, low, close)
        
        # Первое значение должно быть high[0] - low[0]
        assert result[0] == 2.0
        
        # Остальные значения должны быть рассчитаны
        assert result[1] == 3.0  # max(12-9, |12-9|, |9-11|) = max(3, 3, 2) = 3
        assert result[2] == 1.0  # max(11-10, |11-11|, |10-10|) = max(1, 0, 0) = 1
        assert result[3] == 3.0  # max(13-11, |13-10|, |11-12|) = max(2, 3, 1) = 3
        assert result[4] == 2.0  # max(14-12, |14-12|, |12-13|) = max(2, 2, 1) = 2
    
    def test_true_range_single_value(self):
        """Тест True Range с одним значением."""
        high = np.array([10])
        low = np.array([8])
        close = np.array([9])
        
        result = true_range(high, low, close)
        
        assert result[0] == 2.0


class TestATR:
    """Тесты для Average True Range."""
    
    @pytest.fixture
    def mock_candles(self):
        """Создает мок-свечи для тестов."""
        return [
            Candle(
                ts=int((datetime.now() - timedelta(minutes=i*5)).timestamp() * 1000),
                open=100.0 + i * 0.1,
                high=101.0 + i * 0.1,
                low=99.0 + i * 0.1,
                close=100.5 + i * 0.1,
                volume=1000.0 + i * 50
            )
            for i in range(20, 0, -1)
        ]
    
    def test_atr_basic(self, mock_candles):
        """Тест базового расчета ATR."""
        result = atr(mock_candles, period=14)
        
        assert len(result) == len(mock_candles)
        
        # Первые значения могут быть NaN или рассчитаны (зависит от реализации)
        # Проверяем, что есть хотя бы одно рассчитанное значение
        has_calculated_values = any(not np.isnan(val) and val > 0 for val in result)
        assert has_calculated_values
    
    def test_atr_insufficient_data(self, mock_candles):
        """Тест ATR с недостаточными данными."""
        short_candles = mock_candles[:5]  # Только 5 свечей
        
        result = atr(short_candles, period=14)
        
        # Все значения должны быть NaN
        assert all(np.isnan(result))
    
    def test_atr_single_candle(self):
        """Тест ATR с одной свечой."""
        candles = [
            Candle(
                ts=int(datetime.now().timestamp() * 1000),
                open=100.0,
                high=101.0,
                low=99.0,
                close=100.5,
                volume=1000.0
            )
        ]
        
        result = atr(candles, period=14)
        
        assert len(result) == 1
        assert np.isnan(result[0])


class TestBollingerBands:
    """Тесты для Bollinger Bands."""
    
    def test_bollinger_bands_basic(self):
        """Тест базового расчета Bollinger Bands."""
        values = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20]
        period = 10
        std_dev = 2.0
        
        upper, middle, lower = bollinger_bands(values, period, std_dev)
        
        assert len(upper) == len(values)
        assert len(middle) == len(values)
        assert len(lower) == len(values)
        
        # Первые period-1 значения должны быть NaN
        for i in range(period - 1):
            assert np.isnan(upper[i])
            assert np.isnan(middle[i])
            assert np.isnan(lower[i])
        
        # Остальные значения должны быть рассчитаны
        for i in range(period - 1, len(values)):
            assert not np.isnan(upper[i])
            assert not np.isnan(middle[i])
            assert not np.isnan(lower[i])
            assert upper[i] > middle[i] > lower[i]
    
    def test_bollinger_bands_insufficient_data(self):
        """Тест Bollinger Bands с недостаточными данными."""
        values = [1, 2, 3]
        period = 10
        
        upper, middle, lower = bollinger_bands(values, period, std_dev=2.0)
        
        # Все значения должны быть NaN
        assert all(np.isnan(upper))
        assert all(np.isnan(middle))
        assert all(np.isnan(lower))
    
    def test_bollinger_band_width(self):
        """Тест расчета ширины Bollinger Bands."""
        upper = np.array([np.nan, np.nan, 12.0, 13.0, 14.0])
        lower = np.array([np.nan, np.nan, 8.0, 7.0, 6.0])
        middle = np.array([np.nan, np.nan, 10.0, 10.0, 10.0])
        
        width = bollinger_band_width(upper, lower, middle)
        
        # Первые два значения должны быть NaN
        assert np.isnan(width[0])
        assert np.isnan(width[1])
        
        # Остальные значения должны быть рассчитаны
        assert width[2] == 40.0  # (12-8)/10 * 100
        assert width[3] == 60.0  # (13-7)/10 * 100
        assert width[4] == 80.0  # (14-6)/10 * 100


class TestDonchianChannels:
    """Тесты для Donchian Channels."""
    
    @pytest.fixture
    def mock_candles(self):
        """Создает мок-свечи для тестов."""
        return [
            Candle(
                ts=int((datetime.now() - timedelta(minutes=i*5)).timestamp() * 1000),
                open=100.0 + i * 0.1,
                high=101.0 + i * 0.1,
                low=99.0 + i * 0.1,
                close=100.5 + i * 0.1,
                volume=1000.0 + i * 50
            )
            for i in range(25, 0, -1)
        ]
    
    def test_donchian_channels_basic(self, mock_candles):
        """Тест базового расчета Donchian Channels."""
        period = 10
        
        upper, lower = donchian_channels(mock_candles, period)
        
        assert len(upper) == len(mock_candles)
        assert len(lower) == len(mock_candles)
        
        # Первые period-1 значения должны быть NaN
        for i in range(period - 1):
            assert np.isnan(upper[i])
            assert np.isnan(lower[i])
        
        # Остальные значения должны быть рассчитаны
        for i in range(period - 1, len(mock_candles)):
            assert not np.isnan(upper[i])
            assert not np.isnan(lower[i])
            assert upper[i] >= lower[i]
    
    def test_donchian_channels_insufficient_data(self, mock_candles):
        """Тест Donchian Channels с недостаточными данными."""
        short_candles = mock_candles[:5]  # Только 5 свечей
        period = 10
        
        upper, lower = donchian_channels(short_candles, period)
        
        # Все значения должны быть NaN
        assert all(np.isnan(upper))
        assert all(np.isnan(lower))


class TestVWAP:
    """Тесты для Volume Weighted Average Price."""
    
    @pytest.fixture
    def mock_candles(self):
        """Создает мок-свечи для тестов."""
        return [
            Candle(
                ts=int((datetime.now() - timedelta(minutes=i*5)).timestamp() * 1000),
                open=100.0 + i * 0.1,
                high=101.0 + i * 0.1,
                low=99.0 + i * 0.1,
                close=100.5 + i * 0.1,
                volume=1000.0 + i * 100
            )
            for i in range(10, 0, -1)
        ]
    
    def test_vwap_basic(self, mock_candles):
        """Тест базового расчета VWAP."""
        result = vwap(mock_candles)
        
        assert len(result) == len(mock_candles)
        
        # Все значения должны быть рассчитаны
        for i in range(len(result)):
            assert not np.isnan(result[i])
            assert result[i] > 0
    
    def test_vwap_empty_candles(self):
        """Тест VWAP с пустым списком свечей."""
        result = vwap([])
        
        assert len(result) == 0
    
    def test_vwap_single_candle(self, mock_candles):
        """Тест VWAP с одной свечой."""
        single_candle = [mock_candles[0]]
        
        result = vwap(single_candle)
        
        assert len(result) == 1
        assert result[0] == single_candle[0].typical_price


class TestRSI:
    """Тесты для Relative Strength Index."""
    
    def test_rsi_basic(self):
        """Тест базового расчета RSI."""
        values = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20]
        period = 14
        
        result = rsi(values, period)
        
        assert len(result) == len(values)
        
        # Проверяем, что есть рассчитанные значения
        has_calculated_values = any(not np.isnan(val) and 0 <= val <= 100 for val in result)
        assert has_calculated_values
    
    def test_rsi_insufficient_data(self):
        """Тест RSI с недостаточными данными."""
        values = [1, 2, 3]
        period = 14
        
        result = rsi(values, period)
        
        # Все значения должны быть NaN
        assert all(np.isnan(result))
    
    def test_rsi_constant_values(self):
        """Тест RSI с постоянными значениями."""
        values = [100] * 20
        period = 14
        
        result = rsi(values, period)
        
        # При постоянных значениях RSI может быть NaN или 50
        # Проверяем, что нет некорректных значений
        for val in result:
            if not np.isnan(val):
                assert 0 <= val <= 100


class TestOBV:
    """Тесты для On-Balance Volume."""
    
    @pytest.fixture
    def mock_candles(self):
        """Создает мок-свечи для тестов."""
        return [
            Candle(
                ts=int((datetime.now() - timedelta(minutes=i*5)).timestamp() * 1000),
                open=100.0 + i * 0.1,
                high=101.0 + i * 0.1,
                low=99.0 + i * 0.1,
                close=100.0 + i * 0.1,  # Восходящий тренд
                volume=1000.0 + i * 100
            )
            for i in range(10, 0, -1)
        ]
    
    def test_obv_basic(self, mock_candles):
        """Тест базового расчета OBV."""
        result = obv(mock_candles)
        
        assert len(result) == len(mock_candles)
        
        # Первое значение должно быть 0
        assert result[0] == 0
        
        # Остальные значения должны быть рассчитаны
        for i in range(1, len(result)):
            assert not np.isnan(result[i])
    
    def test_obv_single_candle(self):
        """Тест OBV с одной свечой."""
        candles = [
            Candle(
                ts=int(datetime.now().timestamp() * 1000),
                open=100.0,
                high=101.0,
                low=99.0,
                close=100.5,
                volume=1000.0
            )
        ]
        
        result = obv(candles)
        
        assert len(result) == 1
        assert result[0] == 0
    
    def test_obv_mixed_trend(self):
        """Тест OBV со смешанным трендом."""
        candles = [
            Candle(ts=1, open=100, high=101, low=99, close=100, volume=1000),
            Candle(ts=2, open=100, high=101, low=99, close=101, volume=2000),  # Восходящий
            Candle(ts=3, open=101, high=102, low=100, close=100, volume=1500),  # Нисходящий
            Candle(ts=4, open=100, high=101, low=99, close=101, volume=3000),  # Восходящий
        ]
        
        result = obv(candles)
        
        assert result[0] == 0
        assert result[1] == 2000  # +2000
        assert result[2] == 500   # +2000 - 1500
        assert result[3] == 3500  # +500 + 3000


class TestChandelierExit:
    """Тесты для Chandelier Exit."""
    
    @pytest.fixture
    def mock_candles(self):
        """Создает мок-свечи для тестов."""
        return [
            Candle(
                ts=int((datetime.now() - timedelta(minutes=i*5)).timestamp() * 1000),
                open=100.0 + i * 0.1,
                high=101.0 + i * 0.1,
                low=99.0 + i * 0.1,
                close=100.5 + i * 0.1,
                volume=1000.0 + i * 50
            )
            for i in range(25, 0, -1)
        ]
    
    def test_chandelier_exit_long(self, mock_candles):
        """Тест Chandelier Exit для лонга."""
        period = 22
        atr_multiplier = 3.0
        
        result = chandelier_exit(mock_candles, period, atr_multiplier, long=True)
        
        assert len(result) == len(mock_candles)
        
        # Первые period-1 значения должны быть NaN
        for i in range(period - 1):
            assert np.isnan(result[i])
        
        # Остальные значения должны быть рассчитаны
        for i in range(period - 1, len(result)):
            assert not np.isnan(result[i])
            assert result[i] > 0
    
    def test_chandelier_exit_short(self, mock_candles):
        """Тест Chandelier Exit для шорта."""
        period = 22
        atr_multiplier = 3.0
        
        result = chandelier_exit(mock_candles, period, atr_multiplier, long=False)
        
        assert len(result) == len(mock_candles)
        
        # Первые period-1 значения должны быть NaN
        for i in range(period - 1):
            assert np.isnan(result[i])
        
        # Остальные значения должны быть рассчитаны
        for i in range(period - 1, len(result)):
            assert not np.isnan(result[i])
            assert result[i] > 0
    
    def test_chandelier_exit_insufficient_data(self, mock_candles):
        """Тест Chandelier Exit с недостаточными данными."""
        short_candles = mock_candles[:10]  # Только 10 свечей
        period = 22
        
        result = chandelier_exit(short_candles, period, 3.0, long=True)
        
        # Все значения должны быть NaN
        assert all(np.isnan(result))


class TestCorrelation:
    """Тесты для корреляции."""
    
    def test_calculate_correlation_basic(self):
        """Тест базового расчета корреляции."""
        values1 = np.array([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
        values2 = np.array([2, 4, 6, 8, 10, 12, 14, 16, 18, 20])
        period = 5
        
        result = calculate_correlation(values1, values2, period)
        
        assert len(result) == len(values1)
        
        # Первые period-1 значения должны быть NaN
        for i in range(period - 1):
            assert np.isnan(result[i])
        
        # Остальные значения должны быть рассчитаны
        for i in range(period - 1, len(result)):
            assert not np.isnan(result[i])
            assert -1 <= result[i] <= 1
    
    def test_calculate_correlation_different_lengths(self):
        """Тест корреляции с разными длинами массивов."""
        values1 = np.array([1, 2, 3])
        values2 = np.array([1, 2, 3, 4])
        
        with pytest.raises(ValueError):
            calculate_correlation(values1, values2, 3)
    
    def test_calculate_correlation_insufficient_data(self):
        """Тест корреляции с недостаточными данными."""
        values1 = np.array([1, 2, 3])
        values2 = np.array([1, 2, 3])
        period = 5
        
        result = calculate_correlation(values1, values2, period)
        
        # Все значения должны быть NaN
        assert all(np.isnan(result))
    
    def test_calculate_correlation_with_nan(self):
        """Тест корреляции с NaN значениями."""
        values1 = np.array([1, 2, np.nan, 4, 5, 6, 7, 8, 9, 10])
        values2 = np.array([2, 4, 6, 8, 10, 12, 14, 16, 18, 20])
        period = 5
        
        result = calculate_correlation(values1, values2, period)
        
        # Должен обработать NaN значения
        for i in range(period - 1, len(result)):
            if not np.isnan(result[i]):
                assert -1 <= result[i] <= 1


class TestVolumeSurgeRatio:
    """Тесты для Volume Surge Ratio."""
    
    @pytest.fixture
    def mock_candles(self):
        """Создает мок-свечи для тестов."""
        return [
            Candle(
                ts=int((datetime.now() - timedelta(minutes=i*5)).timestamp() * 1000),
                open=100.0 + i * 0.1,
                high=101.0 + i * 0.1,
                low=99.0 + i * 0.1,
                close=100.5 + i * 0.1,
                volume=1000.0 + i * 100
            )
            for i in range(25, 0, -1)
        ]
    
    def test_volume_surge_ratio_basic(self, mock_candles):
        """Тест базового расчета Volume Surge Ratio."""
        lookback_periods = 20
        
        result = volume_surge_ratio(mock_candles, lookback_periods)
        
        assert len(result) == len(mock_candles)
        
        # Первые lookback_periods-1 значения должны быть NaN
        for i in range(lookback_periods - 1):
            assert np.isnan(result[i])
        
        # Остальные значения должны быть рассчитаны
        for i in range(lookback_periods - 1, len(result)):
            assert not np.isnan(result[i])
            assert result[i] > 0
    
    def test_volume_surge_ratio_insufficient_data(self, mock_candles):
        """Тест Volume Surge Ratio с недостаточными данными."""
        short_candles = mock_candles[:10]  # Только 10 свечей
        lookback_periods = 20
        
        result = volume_surge_ratio(short_candles, lookback_periods)
        
        # Все значения должны быть NaN
        assert all(np.isnan(result))


class TestSwingHighsLows:
    """Тесты для Swing Highs/Lows."""
    
    @pytest.fixture
    def mock_candles(self):
        """Создает мок-свечи для тестов."""
        return [
            Candle(
                ts=int((datetime.now() - timedelta(minutes=i*5)).timestamp() * 1000),
                open=100.0 + i * 0.1,
                high=101.0 + i * 0.1,
                low=99.0 + i * 0.1,
                close=100.5 + i * 0.1,
                volume=1000.0 + i * 50
            )
            for i in range(10, 0, -1)
        ]
    
    def test_swing_highs_lows_basic(self, mock_candles):
        """Тест базового расчета Swing Highs/Lows."""
        left_bars = 2
        right_bars = 2
        
        swing_highs, swing_lows = swing_highs_lows(mock_candles, left_bars, right_bars)
        
        assert len(swing_highs) == len(mock_candles)
        assert len(swing_lows) == len(mock_candles)
        
        # Первые left_bars и последние right_bars значения должны быть NaN
        for i in range(left_bars):
            assert np.isnan(swing_highs[i])
            assert np.isnan(swing_lows[i])
        
        for i in range(len(mock_candles) - right_bars, len(mock_candles)):
            assert np.isnan(swing_highs[i])
            assert np.isnan(swing_lows[i])
    
    def test_swing_highs_lows_insufficient_data(self, mock_candles):
        """Тест Swing Highs/Lows с недостаточными данными."""
        short_candles = mock_candles[:3]  # Только 3 свечи
        left_bars = 2
        right_bars = 2
        
        swing_highs, swing_lows = swing_highs_lows(short_candles, left_bars, right_bars)
        
        # Все значения должны быть NaN
        assert all(np.isnan(swing_highs))
        assert all(np.isnan(swing_lows))
    
    def test_swing_highs_lows_swing_high_detection(self):
        """Тест обнаружения swing high."""
        # Создаем свечи с явным swing high в середине
        candles = [
            Candle(ts=1, open=100, high=101, low=99, close=100, volume=1000),
            Candle(ts=2, open=100, high=102, low=99, close=101, volume=1000),
            Candle(ts=3, open=101, high=105, low=100, close=104, volume=1000),  # Swing high
            Candle(ts=4, open=104, high=103, low=102, close=103, volume=1000),
            Candle(ts=5, open=103, high=102, low=101, close=102, volume=1000),
        ]
        
        swing_highs, swing_lows = swing_highs_lows(candles, 1, 1)
        
        # В позиции 2 должен быть swing high
        assert not np.isnan(swing_highs[2])
        assert swing_highs[2] == 105.0
    
    def test_swing_highs_lows_swing_low_detection(self):
        """Тест обнаружения swing low."""
        # Создаем свечи с явным swing low в середине
        candles = [
            Candle(ts=1, open=100, high=101, low=99, close=100, volume=1000),
            Candle(ts=2, open=100, high=101, low=98, close=99, volume=1000),
            Candle(ts=3, open=99, high=100, low=95, close=96, volume=1000),  # Swing low
            Candle(ts=4, open=96, high=97, low=96, close=97, volume=1000),
            Candle(ts=5, open=97, high=98, low=97, close=98, volume=1000),
        ]
        
        swing_highs, swing_lows = swing_highs_lows(candles, 1, 1)
        
        # В позиции 2 должен быть swing low
        assert not np.isnan(swing_lows[2])
        assert swing_lows[2] == 95.0
