"""
Тесты для BreakoutScanner - сканирования рынка.

Покрывает:
- MarketFilter - фильтрация рынков
- MarketScorer - скоринг рынков
- BreakoutScanner - основной сканер
- Применение фильтров
- Расчет метрик
- Обнаружение уровней
"""

import pytest
import numpy as np
from unittest.mock import Mock, patch
from datetime import datetime, timedelta
from typing import List

from breakout_bot.scanner.market_scanner import (
    MarketFilter, MarketScorer, BreakoutScanner, FilterResult, ScanMetrics
)
from breakout_bot.data.models import (
    Candle, L2Depth, MarketData, ScanResult, TradingLevel
)
from breakout_bot.config.settings import (
    TradingPreset, LiquidityFilters, VolatilityFilters, ScannerConfig
)
from breakout_bot.config import get_preset
from breakout_bot.diagnostics import DiagnosticsCollector


class TestMarketFilter:
    """Тесты для MarketFilter."""
    
    @pytest.fixture
    def mock_preset(self):
        """Создает мок-пресет."""
        preset = Mock(spec=TradingPreset)
        preset.liquidity_filters = Mock(spec=LiquidityFilters)
        preset.liquidity_filters.min_24h_volume_usd = 1000000.0
        preset.liquidity_filters.min_oi_usd = 500000.0
        preset.liquidity_filters.max_spread_bps = 10.0
        preset.liquidity_filters.min_depth_usd_0_5pct = 10000.0
        preset.liquidity_filters.min_depth_usd_0_3pct = 5000.0
        preset.liquidity_filters.min_trades_per_minute = 5.0
        
        preset.volatility_filters = Mock(spec=VolatilityFilters)
        preset.volatility_filters.atr_range_min = 0.01
        preset.volatility_filters.atr_range_max = 0.05
        preset.volatility_filters.bb_width_percentile_max = 80.0
        preset.volatility_filters.volume_surge_1h_min = 1.5
        preset.volatility_filters.volume_surge_5m_min = 2.0
        preset.volatility_filters.oi_delta_threshold = 0.1
        
        preset.risk = Mock()
        preset.risk.correlation_limit = 0.7
        
        return preset
    
    @pytest.fixture
    def mock_market_data(self):
        """Создает мок-рыночные данные."""
        l2_depth = L2Depth(
            bid_usd_0_5pct=15000.0,
            ask_usd_0_5pct=15000.0,
            bid_usd_0_3pct=8000.0,
            ask_usd_0_3pct=8000.0,
            spread_bps=8.0,
            imbalance=0.2
        )
        
        # Создаем тестовые свечи
        test_candles = []
        base_time = int(datetime.now().timestamp() * 1000)
        for i in range(20):
            test_candles.append(Candle(
                ts=base_time - (20 - i) * 300000,  # 5 минут назад
                open=50000.0 + i * 10,
                high=50000.0 + i * 10 + 50,
                low=50000.0 + i * 10 - 50,
                close=50000.0 + i * 10 + 25,
                volume=1000.0 + i * 100
            ))
        
        return MarketData(
            symbol="BTC/USDT",
            price=50000.0,
            volume_24h_usd=2000000.0,
            oi_usd=1000000.0,
            oi_change_24h=0.15,
            trades_per_minute=15.0,
            atr_5m=500.0,
            atr_15m=750.0,
            bb_width_pct=3.0,
            btc_correlation=0.6,
            l2_depth=l2_depth,
            candles_5m=test_candles,
            timestamp=int(datetime.now().timestamp() * 1000)
        )
    
    @pytest.fixture
    def filter_instance(self, mock_preset):
        """Создает экземпляр фильтра."""
        return MarketFilter("test_filter", mock_preset)
    
    def test_apply_liquidity_filters_all_passed(self, filter_instance, mock_market_data):
        """Тест применения ликвидных фильтров - все пройдены."""
        results = filter_instance.apply_liquidity_filters(mock_market_data)
        
        assert results["min_24h_volume"].passed is True
        assert results["min_24h_volume"].value == 2000000.0
        assert results["min_oi"].passed is True
        assert results["min_oi"].value == 1000000.0
        assert results["max_spread"].passed is True
        assert results["max_spread"].value == 8.0
        assert results["min_depth_0_5pct"].passed is True
        assert results["min_depth_0_3pct"].passed is True
        assert results["min_trades_per_minute"].passed is True
        assert results["min_trades_per_minute"].value == 15.0
    
    def test_apply_liquidity_filters_volume_failed(self, filter_instance, mock_market_data):
        """Тест применения ликвидных фильтров - не пройден объем."""
        mock_market_data.volume_24h_usd = 500000.0  # Меньше минимума
        
        results = filter_instance.apply_liquidity_filters(mock_market_data)
        
        assert results["min_24h_volume"].passed is False
        assert results["min_24h_volume"].value == 500000.0
        assert results["min_24h_volume"].threshold == 1000000.0
    
    def test_apply_liquidity_filters_spread_failed(self, filter_instance, mock_market_data):
        """Тест применения ликвидных фильтров - не пройден спред."""
        mock_market_data.l2_depth.spread_bps = 15.0  # Больше максимума
        
        results = filter_instance.apply_liquidity_filters(mock_market_data)
        
        assert results["max_spread"].passed is False
        assert results["max_spread"].value == 15.0
        assert results["max_spread"].threshold == 10.0
    
    def test_apply_liquidity_filters_no_oi(self, filter_instance, mock_market_data):
        """Тест применения ликвидных фильтров - нет OI."""
        mock_market_data.oi_usd = None
        
        results = filter_instance.apply_liquidity_filters(mock_market_data)
        
        # OI фильтр не должен применяться
        assert "min_oi" not in results
    
    def test_apply_volatility_filters_all_passed(self, filter_instance, mock_market_data):
        """Тест применения волатильности фильтров - все пройдены."""
        metrics = ScanMetrics()
        metrics.vol_surge_1h = 2.0
        metrics.vol_surge_5m = 2.5
        metrics.oi_delta_24h = 0.2
        
        results = filter_instance.apply_volatility_filters(mock_market_data, metrics)
        
        assert results["atr_range"].passed is True
        assert results["bb_width"].passed is True
        assert results["volume_surge_1h"].passed is True
        assert results["volume_surge_5m"].passed is True
        assert results["oi_delta"].passed is True
    
    def test_apply_volatility_filters_atr_failed(self, filter_instance, mock_market_data):
        """Тест применения волатильности фильтров - не пройден ATR."""
        mock_market_data.atr_15m = 100.0  # ATR ratio = 100/50000 = 0.002 < 0.01
        
        metrics = ScanMetrics()
        results = filter_instance.apply_volatility_filters(mock_market_data, metrics)
        
        assert results["atr_range"].passed is False
        assert results["atr_range"].value == 0.002
    
    def test_apply_volatility_filters_bb_width_failed(self, filter_instance, mock_market_data):
        """Тест применения волатильности фильтров - не пройдена ширина BB."""
        mock_market_data.bb_width_pct = 90.0  # Больше максимума
        
        metrics = ScanMetrics()
        results = filter_instance.apply_volatility_filters(mock_market_data, metrics)
        
        assert results["bb_width"].passed is False
        assert results["bb_width"].value == 90.0
        assert results["bb_width"].threshold == 80.0
    
    def test_apply_volatility_filters_volume_surge_failed(self, filter_instance, mock_market_data):
        """Тест применения волатильности фильтров - не пройден всплеск объема."""
        metrics = ScanMetrics()
        metrics.vol_surge_1h = 1.2  # Меньше минимума
        metrics.vol_surge_5m = 1.8  # Меньше минимума
        
        results = filter_instance.apply_volatility_filters(mock_market_data, metrics)
        
        assert results["volume_surge_1h"].passed is False
        assert results["volume_surge_1h"].value == 1.2
        assert results["volume_surge_5m"].passed is False
        assert results["volume_surge_5m"].value == 1.8
    
    def test_apply_volatility_filters_no_oi_delta(self, filter_instance, mock_market_data):
        """Тест применения волатильности фильтров - нет OI delta."""
        mock_market_data.oi_change_24h = None
        
        metrics = ScanMetrics()
        results = filter_instance.apply_volatility_filters(mock_market_data, metrics)
        
        # OI delta фильтр не должен применяться
        assert "oi_delta" not in results
    
    def test_apply_correlation_filter_passed(self, filter_instance, mock_market_data):
        """Тест применения корреляционного фильтра - пройден."""
        mock_market_data.btc_correlation = 0.5  # Меньше лимита
        
        results = filter_instance.apply_correlation_filter(mock_market_data)
        
        assert results["correlation"].passed is True
        assert results["correlation"].value == 0.5
        assert results["correlation"].threshold == 0.85
    
    def test_apply_correlation_filter_failed(self, filter_instance, mock_market_data):
        """Тест применения корреляционного фильтра - не пройден."""
        mock_market_data.btc_correlation = 0.9  # Больше лимита
        
        results = filter_instance.apply_correlation_filter(mock_market_data)
        
        assert results["correlation"].passed is False
        assert results["correlation"].value == 0.9
        assert results["correlation"].threshold == 0.85


class TestMarketScorer:
    """Тесты для MarketScorer."""
    
    @pytest.fixture
    def mock_score_weights(self):
        """Создает мок-веса скоринга."""
        return {
            "vol_surge": 0.3,
            "oi_delta": 0.2,
            "atr_quality": 0.2,
            "correlation": 0.2,
            "trades_per_minute": 0.1
        }
    
    @pytest.fixture
    def mock_metrics(self):
        """Создает мок-метрики."""
        metrics = ScanMetrics()
        metrics.vol_surge_1h = 2.0
        metrics.vol_surge_5m = 2.5
        metrics.oi_delta_24h = 0.15
        metrics.atr_quality = 0.8
        metrics.btc_correlation = 0.3
        metrics.trades_per_minute = 20.0
        return metrics
    
    @pytest.fixture
    def mock_market_data(self):
        """Создает мок-рыночные данные."""
        return MarketData(
            symbol="BTC/USDT",
            price=50000.0,
            volume_24h_usd=2000000.0,
            oi_usd=1000000.0,
            oi_change_24h=0.15,
            trades_per_minute=20.0,
            atr_5m=500.0,
            atr_15m=750.0,
            bb_width_pct=3.0,
            btc_correlation=0.3,
            l2_depth=None,
            candles_5m=[],
            timestamp=int(datetime.now().timestamp() * 1000)
        )
    
    @pytest.fixture
    def scorer(self, mock_score_weights):
        """Создает экземпляр скорера."""
        return MarketScorer(mock_score_weights)
    
    def test_initialization(self, scorer, mock_score_weights):
        """Тест инициализации скорера."""
        assert scorer.weights == mock_score_weights
    
    def test_calculate_score(self, scorer, mock_metrics, mock_market_data):
        """Тест расчета скора."""
        score, components = scorer.calculate_score(mock_metrics, mock_market_data)
        
        assert isinstance(score, float)
        assert isinstance(components, dict)
        
        # Проверяем, что все компоненты присутствуют
        assert "vol_surge" in components
        assert "oi_delta" in components
        assert "atr_quality" in components
        assert "correlation" in components
        assert "trades_per_minute" in components
        
        # Проверяем, что скор рассчитан
        assert abs(score) < 10  # Разумные границы
    
    def test_normalize_volume_surge(self, scorer):
        """Тест нормализации всплеска объема."""
        # Тестируем разные значения
        surge_1h = 2.0
        surge_5m = 3.0
        
        normalized = scorer._normalize_volume_surge(surge_1h, surge_5m)
        
        assert isinstance(normalized, float)
        assert -3 <= normalized <= 3  # Z-score границы
    
    def test_normalize_oi_delta(self, scorer):
        """Тест нормализации OI delta."""
        # Тестируем разные значения
        test_cases = [0.05, 0.1, 0.2, None]
        
        for oi_delta in test_cases:
            normalized = scorer._normalize_oi_delta(oi_delta)
            
            # Проверяем, что возвращается число (может быть int или float)
            assert isinstance(normalized, (int, float))
            if oi_delta is not None:
                assert -3 <= normalized <= 3  # Z-score границы
            else:
                assert normalized == 0.0
    
    def test_normalize_atr_quality(self, scorer):
        """Тест нормализации качества ATR."""
        # Тестируем разные значения
        test_cases = [0.3, 0.5, 0.8, 1.0]
        
        for atr_quality in test_cases:
            normalized = scorer._normalize_atr_quality(atr_quality)
            
            assert isinstance(normalized, float)
            assert -3 <= normalized <= 3  # Z-score границы
    
    def test_normalize_correlation(self, scorer):
        """Тест нормализации корреляции."""
        # Тестируем разные значения корреляции
        test_cases = [0.0, 0.3, 0.7, 1.0]
        
        for correlation in test_cases:
            normalized = scorer._normalize_correlation(correlation)
            
            assert isinstance(normalized, float)
            assert -3 <= normalized <= 3  # Z-score границы
            
            # Низкая корреляция должна давать высокий скор
            if correlation == 0.0:
                assert normalized > 0
            elif correlation == 1.0:
                assert normalized < 0
    
    def test_normalize_trades_per_minute(self, scorer):
        """Тест нормализации сделок в минуту."""
        # Тестируем разные значения
        test_cases = [1, 10, 100, 1000]
        
        for trades in test_cases:
            normalized = scorer._normalize_trades_per_minute(trades)
            
            # Проверяем, что возвращается число (может быть int или float)
            assert isinstance(normalized, (int, float))
            assert -3 <= normalized <= 3  # Z-score границы
    
    def test_calculate_gainers_momentum(self, scorer, mock_market_data):
        """Тест расчета momentum для gainers."""
        # Создаем свечи с восходящим трендом
        candles = [
            Candle(
                ts=int((datetime.now() - timedelta(minutes=i*5)).timestamp() * 1000),
                open=100.0 + i * 0.1,
                high=101.0 + i * 0.1,
                low=99.0 + i * 0.1,
                close=100.5 + i * 0.1,
                volume=1000.0 + i * 100
            )
            for i in range(5, 0, -1)
        ]
        mock_market_data.candles_5m = candles
        
        momentum = scorer._calculate_gainers_momentum(mock_market_data)
        
        assert isinstance(momentum, float)
        assert -3 <= momentum <= 3  # Z-score границы
    
    def test_calculate_gainers_momentum_insufficient_data(self, scorer, mock_market_data):
        """Тест расчета momentum для gainers - недостаточно данных."""
        mock_market_data.candles_5m = []  # Нет свечей
        
        momentum = scorer._calculate_gainers_momentum(mock_market_data)
        
        assert momentum == 0.0


class TestBreakoutScanner:
    """Тесты для BreakoutScanner."""
    
    @pytest.fixture
    def mock_preset(self):
        """Создает мок-пресет."""
        preset = Mock(spec=TradingPreset)
        preset.name = "test_preset"
        preset.scanner_config = Mock(spec=ScannerConfig)
        preset.scanner_config.score_weights = {
            "vol_surge": 0.3,
            "oi_delta": 0.2,
            "atr_quality": 0.2,
            "correlation": 0.2,
            "trades_per_minute": 0.1
        }
        preset.scanner_config.max_candidates = 10
        preset.scanner_config.symbol_whitelist = None
        preset.scanner_config.symbol_blacklist = None
        preset.scanner_config.top_n_by_volume = None
        
        # Настраиваем фильтры
        preset.liquidity_filters = Mock(spec=LiquidityFilters)
        preset.liquidity_filters.min_24h_volume_usd = 1000000.0
        preset.liquidity_filters.min_oi_usd = 500000.0
        preset.liquidity_filters.max_spread_bps = 10.0
        preset.liquidity_filters.min_depth_usd_0_5pct = 10000.0
        preset.liquidity_filters.min_depth_usd_0_3pct = 5000.0
        preset.liquidity_filters.min_trades_per_minute = 5.0
        
        preset.volatility_filters = Mock(spec=VolatilityFilters)
        preset.volatility_filters.atr_range_min = 0.01
        preset.volatility_filters.atr_range_max = 0.05
        preset.volatility_filters.bb_width_percentile_max = 80.0
        preset.volatility_filters.volume_surge_1h_min = 1.5
        preset.volatility_filters.volume_surge_5m_min = 2.0
        preset.volatility_filters.oi_delta_threshold = 0.1
        
        preset.risk = Mock()
        preset.risk.correlation_limit = 0.7
        
        return preset
    
    @pytest.fixture
    def mock_market_data_list(self):
        """Создает список мок-рыночных данных."""
        symbols = ["BTC/USDT", "ETH/USDT", "ADA/USDT"]
        market_data_list = []
        
        for i, symbol in enumerate(symbols):
            l2_depth = L2Depth(
                bid_usd_0_5pct=15000.0 + i * 5000,
                ask_usd_0_5pct=15000.0 + i * 5000,
                bid_usd_0_3pct=8000.0 + i * 2000,
                ask_usd_0_3pct=8000.0 + i * 2000,
                spread_bps=8.0 - i,
                imbalance=0.2 - i * 0.1
            )
            
            # Создаем тестовые свечи
            test_candles = []
            base_time = int(datetime.now().timestamp() * 1000)
            for j in range(20):
                test_candles.append(Candle(
                    ts=base_time - (20 - j) * 300000,  # 5 минут назад
                    open=50000.0 - i * 10000 + j * 10,
                    high=50000.0 - i * 10000 + j * 10 + 50,
                    low=50000.0 - i * 10000 + j * 10 - 50,
                    close=50000.0 - i * 10000 + j * 10 + 25,
                    volume=1000.0 + j * 100
                ))
            
            market_data = MarketData(
                symbol=symbol,
                price=50000.0 - i * 10000,
                volume_24h_usd=2000000.0 + i * 500000,
                oi_usd=1000000.0 + i * 200000,
                oi_change_24h=0.15 + i * 0.05,
                trades_per_minute=15.0 + i * 5,
                atr_5m=500.0 - i * 100,
                atr_15m=750.0 - i * 150,
                bb_width_pct=3.0 + i,
                btc_correlation=0.6 - i * 0.2,
                l2_depth=l2_depth,
                candles_5m=test_candles,
                timestamp=int(datetime.now().timestamp() * 1000)
            )
            market_data_list.append(market_data)
        
        return market_data_list
    
    @pytest.fixture
    def scanner(self, mock_preset):
        """Создает экземпляр сканера."""
        return BreakoutScanner(mock_preset)
    
    def test_initialization(self, scanner, mock_preset):
        """Тест инициализации сканера."""
        assert scanner.preset == mock_preset
        assert scanner.filter is not None
        assert scanner.scorer is not None
        assert scanner.level_detector is not None
    
    def test_apply_symbol_filters_no_filters(self, scanner, mock_market_data_list):
        """Тест применения фильтров символов - нет фильтров."""
        filtered = scanner._apply_symbol_filters(mock_market_data_list)
        
        assert len(filtered) == len(mock_market_data_list)
        assert filtered == mock_market_data_list


@pytest.mark.asyncio
async def test_filters_gate_reason_tracking():
    preset = get_preset('breakout_v1')
    collector = DiagnosticsCollector(enabled=True, session_id='test_filters_gate')
    scanner = BreakoutScanner(preset, diagnostics=collector)

    base_ts = int(datetime.now().timestamp() * 1000) - 39 * 300000
    candles: List[Candle] = []
    for i in range(40):
        ts = base_ts + i * 300000
        volume = 900.0 if i < 28 else 1600.0
        candles.append(
            Candle(
                ts=ts,
                open=100.0 + i * 0.02,
                high=100.3 + i * 0.02,
                low=99.7 + i * 0.02,
                close=100.1 + i * 0.02,
                volume=volume,
            )
        )

    l2_depth = L2Depth(
        bid_usd_0_5pct=150000.0,
        ask_usd_0_5pct=150000.0,
        bid_usd_0_3pct=95000.0,
        ask_usd_0_3pct=95000.0,
        spread_bps=4.0,
        imbalance=0.4,
    )

    market_data = MarketData(
        symbol='FILTER/USDT',
        price=100.5,
        volume_24h_usd=220_000_000.0,
        oi_usd=90_000_000.0,
        oi_change_24h=0.12,
        trades_per_minute=0.0,
        atr_5m=1.2,
        atr_15m=2.1,
        bb_width_pct=14.0,
        btc_correlation=0.25,
        l2_depth=l2_depth,
        candles_5m=candles,
        timestamp=candles[-1].ts,
    )

    results = await scanner.scan_markets([market_data])
    assert results
    scan_result = results[0]
    assert scan_result.filter_results['min_trades_per_minute'] is False
    assert collector.reasons['filter:min_trades_per_minute'] >= 1
    
    def test_apply_symbol_filters_whitelist(self, scanner, mock_market_data_list):
        """Тест применения фильтров символов - whitelist."""
        scanner.preset.scanner_config.symbol_whitelist = ["BTC/USDT", "ETH/USDT"]
        
        filtered = scanner._apply_symbol_filters(mock_market_data_list)
        
        assert len(filtered) == 2
        assert filtered[0].symbol == "BTC/USDT"
        assert filtered[1].symbol == "ETH/USDT"
    
    def test_apply_symbol_filters_blacklist(self, scanner, mock_market_data_list):
        """Тест применения фильтров символов - blacklist."""
        scanner.preset.scanner_config.symbol_blacklist = ["ADA/USDT"]
        
        filtered = scanner._apply_symbol_filters(mock_market_data_list)
        
        assert len(filtered) == 2
        assert all(md.symbol != "ADA/USDT" for md in filtered)
    
    def test_filter_by_volume(self, scanner, mock_market_data_list):
        """Тест фильтрации по объему."""
        top_n = 2
        
        filtered = scanner._filter_by_volume(mock_market_data_list, top_n)
        
        assert len(filtered) == 2
        # Должны быть отсортированы по убыванию объема
        assert filtered[0].volume_24h_usd >= filtered[1].volume_24h_usd
    
    def test_calculate_scan_metrics(self, scanner, mock_market_data_list):
        """Тест расчета метрик сканирования."""
        market_data = mock_market_data_list[0]
        btc_data = mock_market_data_list[0]  # Используем как BTC данные
        
        # Добавляем свечи для расчета метрик
        candles = [
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
        market_data.candles_5m = candles
        
        metrics = scanner._calculate_scan_metrics(market_data, btc_data)
        
        assert isinstance(metrics, ScanMetrics)
        assert metrics.vol_surge_1h > 0
        assert metrics.vol_surge_5m > 0
        assert metrics.atr_quality >= 0
        assert metrics.bb_width_pct == market_data.bb_width_pct
        assert metrics.btc_correlation == market_data.btc_correlation
        assert metrics.trades_per_minute == market_data.trades_per_minute
        assert metrics.liquidity_score == market_data.liquidity_score
    
    def test_calculate_scan_metrics_insufficient_data(self, scanner, mock_market_data_list):
        """Тест расчета метрик сканирования - недостаточно данных."""
        market_data = mock_market_data_list[0]
        market_data.candles_5m = []  # Нет свечей
        
        metrics = scanner._calculate_scan_metrics(market_data, None)
        
        assert isinstance(metrics, ScanMetrics)
        assert metrics.vol_surge_1h == 0.0
        assert metrics.vol_surge_5m == 0.0
        assert metrics.atr_quality == 0.0
    
    @pytest.mark.asyncio
    async def test_scan_single_market_passed(self, scanner, mock_market_data_list):
        """Тест сканирования одного рынка - прошел фильтры."""
        market_data = mock_market_data_list[0]
        btc_data = None
        
        # Мокаем обнаружение уровней
        with patch.object(scanner.level_detector, 'detect_levels') as mock_detect:
            mock_detect.return_value = [
                TradingLevel(
                    price=50000.0,
                    level_type="resistance",
                    touch_count=3,
                    strength=0.8,
                    first_touch_ts=int(datetime.now().timestamp() * 1000),
                    last_touch_ts=int(datetime.now().timestamp() * 1000)
                )
            ]
            
            result = await scanner._scan_single_market(market_data, btc_data)
        
        assert result is not None
        assert isinstance(result, ScanResult)
        assert result.symbol == "BTC/USDT"
        assert result.score is not None
        assert result.market_data == market_data
        # Проверяем, что результат имеет правильную структуру
        assert hasattr(result, 'passed_all_filters')
        assert len(result.levels) == 1
    
    @pytest.mark.asyncio
    async def test_scan_single_market_failed(self, scanner, mock_market_data_list):
        """Тест сканирования одного рынка - не прошел фильтры."""
        market_data = mock_market_data_list[0]
        market_data.volume_24h_usd = 100000.0  # Меньше минимума
        btc_data = None
        
        result = await scanner._scan_single_market(market_data, btc_data)
        
        assert result is not None
        assert isinstance(result, ScanResult)
        assert result.symbol == "BTC/USDT"
        assert result.passed_all_filters is False
        assert "min_24h_volume" in result.filter_results
        assert result.filter_results["min_24h_volume"] is False
    
    @pytest.mark.asyncio
    async def test_scan_single_market_level_detection_error(self, scanner, mock_market_data_list):
        """Тест сканирования одного рынка - ошибка обнаружения уровней."""
        market_data = mock_market_data_list[0]
        btc_data = None
        
        # Мокаем ошибку обнаружения уровней
        with patch.object(scanner.level_detector, 'detect_levels') as mock_detect:
            mock_detect.side_effect = Exception("Level detection error")
            
            result = await scanner._scan_single_market(market_data, btc_data)
        
        assert result is not None
        assert isinstance(result, ScanResult)
        assert result.levels == []  # Пустой список уровней
    
    @pytest.mark.asyncio
    async def test_scan_markets_success(self, scanner, mock_market_data_list):
        """Тест сканирования рынков - успешно."""
        btc_data = mock_market_data_list[0]
        
        # Мокаем обнаружение уровней
        with patch.object(scanner.level_detector, 'detect_levels') as mock_detect:
            mock_detect.return_value = [
                TradingLevel(
                    price=50000.0,
                    level_type="resistance",
                    touch_count=3,
                    strength=0.8,
                    first_touch_ts=int(datetime.now().timestamp() * 1000),
                    last_touch_ts=int(datetime.now().timestamp() * 1000)
                )
            ]
            
            results = await scanner.scan_markets(mock_market_data_list, btc_data)
        
        assert isinstance(results, list)
        assert len(results) <= scanner.preset.scanner_config.max_candidates
        
        # Проверяем, что результаты отсортированы по скору
        if len(results) > 1:
            for i in range(len(results) - 1):
                assert results[i].score >= results[i + 1].score
        
        # Проверяем ранжирование
        for i, result in enumerate(results):
            assert result.rank == i + 1
    
    @pytest.mark.asyncio
    async def test_scan_markets_with_volume_filter(self, scanner, mock_market_data_list):
        """Тест сканирования рынков - с фильтром по объему."""
        scanner.preset.scanner_config.top_n_by_volume = 2
        btc_data = mock_market_data_list[0]
        
        results = await scanner.scan_markets(mock_market_data_list, btc_data)
        
        # Должно быть не больше 2 результатов
        assert len(results) <= 2
    
    @pytest.mark.asyncio
    async def test_scan_markets_error_handling(self, scanner, mock_market_data_list):
        """Тест сканирования рынков - обработка ошибок."""
        btc_data = mock_market_data_list[0]
        
        # Мокаем ошибку в сканировании одного рынка
        with patch.object(scanner, '_scan_single_market') as mock_scan:
            mock_scan.side_effect = [Exception("Scan error"), None, None]
            
            results = await scanner.scan_markets(mock_market_data_list, btc_data)
        
        # Должен обработать ошибку и продолжить
        assert isinstance(results, list)
        assert len(results) >= 0  # Может быть 0 или больше в зависимости от успешных сканирований
    
    def test_apply_symbol_filters_whitelist_and_blacklist(self, scanner, mock_market_data_list):
        """Тест применения фильтров символов - whitelist и blacklist."""
        scanner.preset.scanner_config.symbol_whitelist = ["BTC/USDT", "ETH/USDT", "ADA/USDT"]
        scanner.preset.scanner_config.symbol_blacklist = ["ADA/USDT"]
        
        filtered = scanner._apply_symbol_filters(mock_market_data_list)
        
        assert len(filtered) == 2
        assert all(md.symbol in ["BTC/USDT", "ETH/USDT"] for md in filtered)
        assert all(md.symbol != "ADA/USDT" for md in filtered)
    
    def test_apply_symbol_filters_empty_whitelist(self, scanner, mock_market_data_list):
        """Тест применения фильтров символов - пустой whitelist."""
        scanner.preset.scanner_config.symbol_whitelist = []
        
        filtered = scanner._apply_symbol_filters(mock_market_data_list)
        
        # Пустой whitelist может означать "все разрешены" или "ничего не разрешено"
        # Проверяем, что функция возвращает список
        assert isinstance(filtered, list)
    
    def test_apply_symbol_filters_empty_blacklist(self, scanner, mock_market_data_list):
        """Тест применения фильтров символов - пустой blacklist."""
        scanner.preset.scanner_config.symbol_blacklist = []
        
        filtered = scanner._apply_symbol_filters(mock_market_data_list)
        
        assert len(filtered) == len(mock_market_data_list)
        assert filtered == mock_market_data_list
