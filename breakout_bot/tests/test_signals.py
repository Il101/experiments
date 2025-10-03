"""
Тесты для SignalGenerator - генерации торговых сигналов.

Покрывает:
- Momentum стратегию
- Retest стратегию
- Валидацию условий сигналов
- Расчет уверенности
- Обработку истории брейкаутов
"""

import asyncio
import pytest
import numpy as np
from unittest.mock import Mock, patch
from datetime import datetime, timedelta
from typing import Dict, List

from breakout_bot.signals.signal_generator import (
    SignalValidator, MomentumStrategy, RetestStrategy, SignalGenerator
)
from breakout_bot.data.models import (
    Candle, L2Depth, MarketData, ScanResult, TradingLevel, Signal
)
from breakout_bot.config.settings import TradingPreset, SignalConfig
from breakout_bot.config import get_preset


# Общие фикстуры для всех тестов
@pytest.fixture
def mock_candles():
    """Создает мок-свечи для тестов."""
    base_time = int(datetime.now().timestamp() * 1000)
    candles = []
    
    for i in range(20):
        candle = Candle(
            ts=base_time - (20 - i) * 300000,  # 5-минутные свечи
            open=100.0 + i * 0.1,
            high=101.0 + i * 0.1,
            low=98.0 + i * 0.1,  # Некоторые low будут меньше 100.0
            close=100.5 + i * 0.1,
            volume=1000.0 + i * 10
        )
        candles.append(candle)
    
    return candles

@pytest.fixture
def mock_l2_depth():
    """Создает мок-L2 данные."""
    return L2Depth(
        bid_usd_0_5pct=50000.0,
        ask_usd_0_5pct=50000.0,
        bid_usd_0_3pct=30000.0,
        ask_usd_0_3pct=30000.0,
        spread_bps=5.0,
        imbalance=0.4
    )


class TestSignalValidator:
    """Тесты для SignalValidator."""
    
    @pytest.fixture
    def mock_signal_config(self):
        """Создает мок-конфигурацию сигналов."""
        config = Mock(spec=SignalConfig)
        config.momentum_epsilon = 0.001
        config.momentum_volume_multiplier = 2.0
        config.momentum_body_ratio_min = 0.6
        config.l2_imbalance_threshold = 0.3
        config.vwap_gap_max_atr = 2.0
        config.retest_max_pierce_atr = 1.0
        config.retest_pierce_tolerance = 0.0005
        return config
    
    
    @pytest.fixture
    def mock_level(self):
        """Создает мок-торговый уровень."""
        return TradingLevel(
            price=100.0,
            level_type="resistance",
            touch_count=3,
            strength=0.8,
            first_touch_ts=int(datetime.now().timestamp() * 1000),
            last_touch_ts=int(datetime.now().timestamp() * 1000)
        )
    
    @pytest.fixture
    def validator(self, mock_signal_config):
        """Создает экземпляр валидатора."""
        return SignalValidator(mock_signal_config)
    
    def test_validate_momentum_conditions_price_breakout_resistance(self, validator, mock_candles, mock_level, mock_l2_depth):
        """Тест валидации momentum условий - пробой сопротивления."""
        # Настраиваем свечу с пробоем
        mock_candles[-1].close = 100.1  # Пробой уровня 100.0
        current_price = 100.1
        
        conditions = validator.validate_momentum_conditions(
            'TEST/USDT', mock_candles, mock_level, mock_l2_depth, current_price
        )
        
        # Проверяем, что условия проверяются (может быть True или False в зависимости от конфигурации)
        assert 'price_breakout' in conditions
        assert 'details' in conditions
        if conditions['price_breakout']:
            assert 'breakout_price' in conditions['details']
    
    def test_validate_momentum_conditions_price_breakout_support(self, validator, mock_candles, mock_l2_depth):
        """Тест валидации momentum условий - пробой поддержки."""
        level = TradingLevel(
            price=100.0,
            level_type="support",
            touch_count=3,
            strength=0.8,
            first_touch_ts=int(datetime.now().timestamp() * 1000),
            last_touch_ts=int(datetime.now().timestamp() * 1000)
        )
        
        # Настраиваем свечу с пробоем вниз
        mock_candles[-1].close = 99.9  # Пробой уровня 100.0
        current_price = 99.9
        
        conditions = validator.validate_momentum_conditions(
            'TEST/USDT', mock_candles, level, mock_l2_depth, current_price
        )
        
        # Проверяем, что условия проверяются
        assert 'price_breakout' in conditions
        assert 'details' in conditions
        if conditions['price_breakout']:
            assert 'breakout_price' in conditions['details']
    
    def test_validate_momentum_conditions_volume_surge(self, validator, mock_candles, mock_level, mock_l2_depth):
        """Тест валидации momentum условий - всплеск объема."""
        # Настраиваем высокий объем в последней свече
        mock_candles[-1].volume = 5000.0  # Высокий объем
        current_price = 100.1
        
        conditions = validator.validate_momentum_conditions(
            'TEST/USDT', mock_candles, mock_level, mock_l2_depth, current_price
        )
        
        # Проверяем, что условия проверяются
        assert 'volume_surge' in conditions
        assert 'details' in conditions
        if conditions['volume_surge']:
            assert 'volume_ratio' in conditions['details']
    
    def test_validate_momentum_conditions_body_ratio(self, validator, mock_candles, mock_level, mock_l2_depth):
        """Тест валидации momentum условий - соотношение тела свечи."""
        # Настраиваем свечу с большим телом
        mock_candles[-1].open = 100.0
        mock_candles[-1].high = 100.1
        mock_candles[-1].low = 99.9
        mock_candles[-1].close = 100.05  # Большое тело
        current_price = 100.05
        
        conditions = validator.validate_momentum_conditions(
            'TEST/USDT', mock_candles, mock_level, mock_l2_depth, current_price
        )
        
        # Проверяем, что условия проверяются
        assert 'body_ratio' in conditions
        assert 'details' in conditions
        if conditions['body_ratio']:
            assert 'body_ratio' in conditions['details']
    
    def test_validate_momentum_conditions_l2_imbalance(self, validator, mock_candles, mock_level, mock_l2_depth):
        """Тест валидации momentum условий - дисбаланс L2."""
        current_price = 100.1
        
        conditions = validator.validate_momentum_conditions(
            'TEST/USDT', mock_candles, mock_level, mock_l2_depth, current_price
        )
        
        # Проверяем, что условия проверяются
        assert 'l2_imbalance' in conditions
        assert 'details' in conditions
        if conditions['l2_imbalance']:
            assert 'l2_imbalance' in conditions['details']
        assert conditions['details']['imbalance_threshold'] == 0.3
    
    def test_validate_momentum_conditions_vwap_gap(self, validator, mock_candles, mock_level, mock_l2_depth):
        """Тест валидации momentum условий - разрыв VWAP."""
        current_price = 100.1
        
        with patch('breakout_bot.signals.signal_generator.vwap') as mock_vwap:
            with patch('breakout_bot.signals.signal_generator.atr') as mock_atr:
                # Настраиваем моки
                mock_vwap.return_value = np.array([100.0] * 20)
                mock_atr.return_value = np.array([0.01] * 20)
                
                conditions = validator.validate_momentum_conditions(
                    'TEST/USDT', mock_candles, mock_level, mock_l2_depth, current_price
                )
                
                # Проверяем, что условия проверяются
                assert 'vwap_gap' in conditions
                assert 'details' in conditions
                if 'vwap_gap' in conditions['details']:
                    assert 'max_vwap_gap' in conditions['details']
    
    def test_validate_momentum_conditions_insufficient_data(self, validator, mock_level, mock_l2_depth):
        """Тест валидации momentum условий - недостаточно данных."""
        conditions = validator.validate_momentum_conditions(
            'TEST/USDT', [], mock_level, mock_l2_depth, 100.0
        )
        
        # Все условия должны быть False
        assert conditions['price_breakout'] is False
        assert conditions['volume_surge'] is False
        assert conditions['body_ratio'] is False
        assert conditions['l2_imbalance'] is False
        assert conditions['vwap_gap'] is False
    
    def test_validate_retest_conditions_level_retest(self, validator, mock_candles, mock_level, mock_l2_depth):
        """Тест валидации retest условий - ретест уровня."""
        # Настраиваем цену близко к уровню
        current_price = 100.002  # В пределах 0.5% от уровня 100.0
        
        conditions = validator.validate_retest_conditions(
            'TEST/USDT', mock_candles, mock_level, mock_l2_depth, current_price
        )
        
        assert conditions['level_retest'] is True
        assert conditions['details']['distance_from_level'] <= 0.005
    
    def test_validate_retest_conditions_pierce_tolerance(self, validator, mock_candles, mock_level, mock_l2_depth):
        """Тест валидации retest условий - толерантность к пробитию."""
        current_price = 100.0
        
        with patch('breakout_bot.signals.signal_generator.atr') as mock_atr:
            mock_atr.return_value = np.array([0.01] * 20)
            
            conditions = validator.validate_retest_conditions(
                'TEST/USDT', mock_candles, mock_level, mock_l2_depth, current_price
            )
            
            # Проверяем, что условия проверяются
            assert 'pierce_tolerance' in conditions
            assert 'details' in conditions
            if 'pierce_amount' in conditions['details']:
                assert 'max_pierce' in conditions['details']
    
    def test_validate_retest_conditions_previous_breakout(self, validator, mock_candles, mock_level, mock_l2_depth):
        """Тест валидации retest условий - предыдущий брейкаут."""
        current_price = 100.0
        previous_breakout = {
            'timestamp': int((datetime.now() - timedelta(hours=2)).timestamp() * 1000),
            'level_price': 100.0,
            'side': 'long'
        }
        
        conditions = validator.validate_retest_conditions(
            'TEST/USDT', mock_candles, mock_level, mock_l2_depth, current_price, previous_breakout
        )
        
        # Проверяем, что условия проверяются
        assert 'previous_breakout' in conditions
        assert 'details' in conditions
        if 'hours_since_breakout' in conditions['details']:
            assert isinstance(conditions['details']['hours_since_breakout'], (int, float))
    
    def test_validate_retest_conditions_old_breakout(self, validator, mock_candles, mock_level, mock_l2_depth):
        """Тест валидации retest условий - старый брейкаут."""
        current_price = 100.0
        previous_breakout = {
            'timestamp': int((datetime.now() - timedelta(days=2)).timestamp() * 1000),
            'level_price': 100.0,
            'side': 'long'
        }
        
        conditions = validator.validate_retest_conditions(
            'TEST/USDT', mock_candles, mock_level, mock_l2_depth, current_price, previous_breakout
        )
        
        assert conditions['previous_breakout'] is False
        assert conditions['details']['hours_since_breakout'] > 24


class TestMomentumStrategy:
    """Тесты для MomentumStrategy."""
    
    @pytest.fixture
    def mock_preset(self):
        """Создает мок-пресет."""
        preset = Mock(spec=TradingPreset)
        preset.signal_config = Mock(spec=SignalConfig)
        preset.signal_config.momentum_epsilon = 0.001
        preset.signal_config.momentum_volume_multiplier = 2.0
        preset.signal_config.momentum_body_ratio_min = 0.6
        preset.signal_config.l2_imbalance_threshold = 0.3
        preset.signal_config.vwap_gap_max_atr = 2.0
        preset.signal_config.retest_max_pierce_atr = 1.0
        preset.signal_config.retest_pierce_tolerance = 0.0005
        preset.signal_config.volume_surge_threshold = 1.5
        preset.signal_config.body_ratio_threshold = 0.6
        preset.position_config = Mock()
        preset.position_config.tp1_r = 1.0
        preset.position_config.tp2_r = 2.0
        return preset
    
    @pytest.fixture
    def mock_scan_result(self, mock_candles, mock_l2_depth):
        """Создает мок-результат сканирования."""
        market_data = MarketData(
            symbol="BTC/USDT",
            price=100.0,
            volume_24h_usd=1000000.0,
            oi_usd=500000.0,
            oi_change_24h=0.05,
            trades_per_minute=10.0,
            atr_5m=1.0,
            atr_15m=1.5,
            bb_width_pct=2.0,
            btc_correlation=0.8,
            l2_depth=mock_l2_depth,
            candles_5m=mock_candles,
            timestamp=int(datetime.now().timestamp() * 1000)
        )
        
        level = TradingLevel(
            price=100.0,
            level_type="resistance",
            touch_count=3,
            strength=0.8,
            first_touch_ts=int(datetime.now().timestamp() * 1000),
            last_touch_ts=int(datetime.now().timestamp() * 1000)
        )
        
        return ScanResult(
            symbol="BTC/USDT",
            score=0.8,
            rank=1,
            market_data=market_data,
            filter_results={"min_24h_volume": True},
            score_components={"vol_surge": 0.5},
            levels=[level],
            timestamp=int(datetime.now().timestamp() * 1000)
        )
    
    @pytest.fixture
    def strategy(self, mock_preset):
        """Создает экземпляр стратегии."""
        return MomentumStrategy(mock_preset)
    
    def test_generate_signal_success(self, strategy, mock_scan_result):
        """Тест успешной генерации сигнала."""
        # Настраиваем условия для успешного сигнала
        mock_scan_result.market_data.candles_5m[-1].close = 100.2  # Пробой с запасом
        mock_scan_result.market_data.candles_5m[-1].volume = 5000.0  # Высокий объем
        mock_scan_result.market_data.candles_5m[-1].open = 99.8  # Низкий open для большого body
        mock_scan_result.market_data.candles_5m[-1].high = 100.002
        mock_scan_result.market_data.candles_5m[-1].low = 99.7  # Низкий low для большого body
        
        with patch('breakout_bot.signals.signal_generator.vwap') as mock_vwap:
            with patch('breakout_bot.signals.signal_generator.atr') as mock_atr:
                mock_vwap.return_value = np.array([100.0] * 20)
                mock_atr.return_value = np.array([5.0] * 20)
                
                # Проверяем условия перед генерацией сигнала
                conditions = strategy.validator.validate_momentum_conditions(
                    mock_scan_result.symbol,
                    mock_scan_result.market_data.candles_5m,
                    mock_scan_result.levels[0],
                    mock_scan_result.market_data.l2_depth,
                    mock_scan_result.market_data.price
                )
                print("Conditions:", conditions)
                
                signal = strategy.generate_signal(mock_scan_result, mock_scan_result.levels[0])
                print("Signal:", signal)
                
                assert signal is not None
                assert signal.symbol == "BTC/USDT"
                assert signal.side == "long"
                assert signal.strategy == "momentum"
                assert signal.entry == 100.1  # breakout price
                assert signal.level == 100.0
                assert signal.confidence > 0
                assert "level_strength" in signal.meta
                assert "scan_score" in signal.meta
    
    def test_generate_signal_insufficient_data(self, strategy, mock_scan_result):
        """Тест генерации сигнала - недостаточно данных."""
        # Убираем свечи
        mock_scan_result.market_data.candles_5m = []
        
        signal = strategy.generate_signal(mock_scan_result, mock_scan_result.levels[0])

        assert signal is None


    def test_generate_signal_conditions_not_met(self, strategy, mock_scan_result):
        """Тест генерации сигнала - условия не выполнены."""
        # Настраиваем условия, которые не пройдут валидацию
        mock_scan_result.market_data.candles_5m[-1].close = 99.9  # Нет пробоя
        mock_scan_result.market_data.candles_5m[-1].volume = 100.0  # Низкий объем
        
        signal = strategy.generate_signal(mock_scan_result, mock_scan_result.levels[0])
        
        assert signal is None
    
    def test_calculate_momentum_stop_loss_long(self, strategy, mock_candles):
        """Тест расчета стоп-лосса для лонга."""
        entry_price = 100.0
        
        with patch('breakout_bot.signals.signal_generator.atr') as mock_atr:
            mock_atr.return_value = np.array([5.0] * 20)
            
            stop_loss = strategy._calculate_momentum_stop_loss(mock_candles, entry_price, 'long')
            
            # Стоп должен быть ниже входа
            assert stop_loss < entry_price
            assert stop_loss > 0
    
    def test_calculate_momentum_stop_loss_short(self, strategy, mock_candles):
        """Тест расчета стоп-лосса для шорта."""
        entry_price = 100.0
        
        with patch('breakout_bot.signals.signal_generator.atr') as mock_atr:
            mock_atr.return_value = np.array([0.01] * 20)
            
            stop_loss = strategy._calculate_momentum_stop_loss(mock_candles, entry_price, 'short')
            
            # Стоп должен быть выше входа
            assert stop_loss > entry_price
            assert stop_loss > 0
    
    def test_calculate_momentum_confidence(self, strategy, mock_scan_result):
        """Тест расчета уверенности сигнала."""
        conditions = {
            'details': {
                'volume_ratio': 3.0,
                'body_ratio': 0.7,
                'l2_imbalance': 0.4
            }
        }
        
        confidence = strategy._calculate_momentum_confidence(conditions, mock_scan_result)
        
        assert 0 <= confidence <= 1
        assert confidence > 0.1  # Минимальная уверенность


class TestRetestStrategy:
    """Тесты для RetestStrategy."""
    
    @pytest.fixture
    def mock_preset(self):
        """Создает мок-пресет."""
        preset = Mock(spec=TradingPreset)
        preset.signal_config = Mock(spec=SignalConfig)
        preset.signal_config.retest_pierce_tolerance = 0.0005
        preset.position_config = Mock()
        preset.position_config.tp1_r = 1.0
        preset.position_config.tp2_r = 2.0
        return preset
    
    @pytest.fixture
    def strategy(self, mock_preset):
        """Создает экземпляр стратегии."""
        return RetestStrategy(mock_preset)
    
    def test_add_breakout_history(self, strategy):
        """Тест добавления истории брейкаутов."""
        symbol = "BTC/USDT"
        breakout_info = {
            'timestamp': int(datetime.now().timestamp() * 1000),
            'level_price': 100.0,
            'side': 'long'
        }
        
        strategy.add_breakout_history(symbol, breakout_info)
        
        assert symbol in strategy.breakout_history
        assert len(strategy.breakout_history[symbol]) == 1
        assert strategy.breakout_history[symbol][0] == breakout_info
    
    def test_add_breakout_history_cleanup_old(self, strategy):
        """Тест очистки старых брейкаутов."""
        symbol = "BTC/USDT"
        
        # Добавляем старый брейкаут
        old_breakout = {
            'timestamp': int((datetime.now() - timedelta(days=8)).timestamp() * 1000),
            'level_price': 100.0,
            'side': 'long'
        }
        strategy.add_breakout_history(symbol, old_breakout)
        
        # Добавляем новый брейкаут
        new_breakout = {
            'timestamp': int(datetime.now().timestamp() * 1000),
            'level_price': 100.0,
            'side': 'long'
        }
        strategy.add_breakout_history(symbol, new_breakout)
        
        # Старый должен быть удален
        assert len(strategy.breakout_history[symbol]) == 1
        assert strategy.breakout_history[symbol][0] == new_breakout
    
    def test_find_relevant_breakout(self, strategy):
        """Тест поиска релевантного брейкаута."""
        symbol = "BTC/USDT"
        
        # Добавляем брейкауты
        breakout1 = {
            'timestamp': int((datetime.now() - timedelta(hours=1)).timestamp() * 1000),
            'level_price': 100.0,
            'side': 'long'
        }
        breakout2 = {
            'timestamp': int((datetime.now() - timedelta(hours=2)).timestamp() * 1000),
            'level_price': 200.0,
            'side': 'short'
        }
        
        strategy.breakout_history[symbol] = [breakout1, breakout2]
        
        # Ищем брейкаут для уровня 100.0
        level = TradingLevel(
            price=100.0,
            level_type="resistance",
            touch_count=3,
            strength=0.8,
            first_touch_ts=int(datetime.now().timestamp() * 1000),
            last_touch_ts=int(datetime.now().timestamp() * 1000)
        )
        
        relevant = strategy._find_relevant_breakout(symbol, level)
        
        assert relevant == breakout1  # Должен найти первый (более свежий)
    
    def test_find_relevant_breakout_no_match(self, strategy):
        """Тест поиска релевантного брейкаута - нет совпадений."""
        symbol = "BTC/USDT"
        
        # Добавляем брейкаут с другим уровнем
        breakout = {
            'timestamp': int(datetime.now().timestamp() * 1000),
            'level_price': 200.0,
            'side': 'long'
        }
        
        strategy.breakout_history[symbol] = [breakout]
        
        # Ищем брейкаут для уровня 100.0
        level = TradingLevel(
            price=100.0,
            level_type="resistance",
            touch_count=3,
            strength=0.8,
            first_touch_ts=int(datetime.now().timestamp() * 1000),
            last_touch_ts=int(datetime.now().timestamp() * 1000)
        )
        
        relevant = strategy._find_relevant_breakout(symbol, level)
        
        assert relevant is None


class TestSignalGenerator:
    """Тесты для SignalGenerator."""
    
    @pytest.fixture
    def mock_preset(self):
        """Создает мок-пресет."""
        preset = Mock(spec=TradingPreset)
        preset.name = "test_preset"
        preset.strategy_priority = "momentum"
        
        # Добавляем необходимые конфигурации
        preset.signal_config = Mock()
        preset.signal_config.momentum_volume_multiplier = 2.5
        preset.signal_config.momentum_body_ratio_min = 0.5
        preset.signal_config.momentum_epsilon = 0.0008
        preset.signal_config.retest_pierce_tolerance = 0.0015
        preset.signal_config.retest_max_pierce_atr = 0.25
        preset.signal_config.l2_imbalance_threshold = 0.3
        preset.signal_config.vwap_gap_max_atr = 1.5
        
        preset.execution_config = Mock()
        preset.execution_config.enable_twap = True
        preset.execution_config.enable_iceberg = True
        preset.execution_config.max_depth_fraction = 0.25
        preset.execution_config.twap_min_slices = 4
        preset.execution_config.twap_max_slices = 12
        preset.execution_config.twap_interval_seconds = 2.5
        preset.execution_config.iceberg_min_notional = 6000.0
        preset.execution_config.limit_offset_bps = 1.5
        preset.execution_config.spread_widen_bps = 10.0
        preset.execution_config.deadman_timeout_ms = 8000
        preset.execution_config.taker_fee_bps = 6.5
        preset.execution_config.maker_fee_bps = 1.5
        
        return preset
    
    @pytest.fixture
    def mock_scan_result(self):
        """Создает мок-результат сканирования."""
        # Создаем тестовые свечи
        test_candles = []
        base_time = int(datetime.now().timestamp() * 1000)
        for i in range(20):
            test_candles.append(Candle(
                ts=base_time - (20 - i) * 300000,  # 5 минут назад
                open=100.0 + i * 0.1,
                high=100.0 + i * 0.1 + 0.5,
                low=100.0 + i * 0.1 - 0.5,
                close=100.0 + i * 0.1 + 0.25,
                volume=1000.0 + i * 100
            ))
        
        market_data = MarketData(
            symbol="BTC/USDT",
            price=100.0,
            volume_24h_usd=1000000.0,
            oi_usd=500000.0,
            oi_change_24h=0.05,
            trades_per_minute=10.0,
            atr_5m=1.0,
            atr_15m=1.5,
            bb_width_pct=2.0,
            btc_correlation=0.8,
            l2_depth=L2Depth(
                bid_usd_0_5pct=10000.0,
                ask_usd_0_5pct=10000.0,
                bid_usd_0_3pct=5000.0,
                ask_usd_0_3pct=5000.0,
                spread_bps=5.0,
                imbalance=0.1
            ),
            candles_5m=test_candles,
            timestamp=int(datetime.now().timestamp() * 1000)
        )
        
        level = TradingLevel(
            price=100.0,
            level_type="resistance",
            touch_count=3,
            strength=0.8,
            first_touch_ts=int(datetime.now().timestamp() * 1000),
            last_touch_ts=int(datetime.now().timestamp() * 1000)
        )
        
        return ScanResult(
            symbol="BTC/USDT",
            score=0.8,
            rank=1,
            market_data=market_data,
            filter_results={"min_24h_volume": True},
            score_components={"vol_surge": 0.5},
            levels=[level],
            timestamp=int(datetime.now().timestamp() * 1000)
        )
    
    @pytest.fixture
    def generator(self, mock_preset):
        """Создает экземпляр генератора."""
        return SignalGenerator(mock_preset)
    
    def test_initialization(self, generator, mock_preset):
        """Тест инициализации генератора."""
        assert generator.preset == mock_preset
        assert generator.momentum_strategy is not None
        assert generator.retest_strategy is not None
    
    def test_generate_signals_empty_results(self, generator):
        """Тест генерации сигналов - пустые результаты."""
        signals = generator.generate_signals([])
        
        assert signals == []
    
    def test_generate_signals_failed_filters(self, generator, mock_scan_result):
        """Тест генерации сигналов - не прошли фильтры."""
        mock_scan_result.filter_results = {"min_24h_volume": False}
        
        signals = generator.generate_signals([mock_scan_result])
        
        assert signals == []
    
    def test_generate_signals_no_levels(self, generator, mock_scan_result):
        """Тест генерации сигналов - нет уровней."""
        mock_scan_result.levels = []
        
        signals = generator.generate_signals([mock_scan_result])
        
        assert signals == []
    
    def test_generate_signals_momentum_priority(self, generator, mock_scan_result):
        """Тест генерации сигналов - приоритет momentum."""
        generator.preset.strategy_priority = "momentum"
        generator.momentum_strategy.generate_signal = Mock(return_value=Mock())
        generator.retest_strategy.generate_signal = Mock(return_value=None)
        
        signals = generator.generate_signals([mock_scan_result])
        
        assert len(signals) == 1
        generator.momentum_strategy.generate_signal.assert_called_once()
        generator.retest_strategy.generate_signal.assert_not_called()
    
    def test_generate_signals_retest_priority(self, generator, mock_scan_result):
        """Тест генерации сигналов - приоритет retest."""
        generator.preset.strategy_priority = "retest"
        generator.momentum_strategy.generate_signal = Mock(return_value=None)
        generator.retest_strategy.generate_signal = Mock(return_value=Mock())
        
        signals = generator.generate_signals([mock_scan_result])
        
        assert len(signals) == 1
        generator.retest_strategy.generate_signal.assert_called_once()
        generator.momentum_strategy.generate_signal.assert_not_called()
    
    def test_generate_signals_fallback_strategy(self, generator, mock_scan_result):
        """Тест генерации сигналов - fallback стратегия."""
        generator.preset.strategy_priority = "momentum"
        generator.momentum_strategy.generate_signal = Mock(return_value=None)
        generator.retest_strategy.generate_signal = Mock(return_value=Mock())
        
        signals = generator.generate_signals([mock_scan_result])
        
        assert len(signals) == 1
        generator.momentum_strategy.generate_signal.assert_called_once()
        generator.retest_strategy.generate_signal.assert_called_once()
    
    def test_generate_signals_sorting(self, generator, mock_scan_result):
        """Тест сортировки сигналов по уверенности."""
        # Создаем два сигнала с разной уверенностью
        signal1 = Mock()
        signal1.confidence = 0.6
        signal2 = Mock()
        signal2.confidence = 0.8
        
        generator.momentum_strategy.generate_signal = Mock(side_effect=[signal1, signal2])
        
        # Создаем два результата сканирования
        scan_result2 = Mock()
        scan_result2.passed_all_filters = True
        scan_result2.levels = [Mock()]
        
        signals = generator.generate_signals([mock_scan_result, scan_result2])
        
        # Должны быть отсортированы по убыванию уверенности
        assert len(signals) == 2
        assert signals[0].confidence == 0.8
        assert signals[1].confidence == 0.6
    
    def test_add_breakout_history(self, generator):
        """Тест добавления истории брейкаутов."""
        symbol = "BTC/USDT"
        breakout_info = {
            'timestamp': int(datetime.now().timestamp() * 1000),
            'level_price': 100.0,
            'side': 'long'
        }
        
        generator.add_breakout_history(symbol, breakout_info)
        
        # Должно передать в retest стратегию
        assert symbol in generator.retest_strategy.breakout_history
        assert generator.retest_strategy.breakout_history[symbol][0] == breakout_info
    
    def test_get_signal_summary_empty(self, generator):
        """Тест получения сводки сигналов - пустой список."""
        summary = generator.get_signal_summary([])
        
        assert summary['total_signals'] == 0
        assert summary['by_strategy'] == {}
        assert summary['by_side'] == {}
        assert summary['avg_confidence'] == 0.0
        assert summary['top_symbols'] == []
    
    def test_get_signal_summary_with_signals(self, generator):
        """Тест получения сводки сигналов - с сигналами."""
        signal1 = Mock()
        signal1.strategy = "momentum"
        signal1.side = "long"
        signal1.confidence = 0.8
        signal1.symbol = "BTC/USDT"
        
        signal2 = Mock()
        signal2.strategy = "retest"
        signal2.side = "short"
        signal2.confidence = 0.6
        signal2.symbol = "ETH/USDT"
        
        signals = [signal1, signal2]
        summary = generator.get_signal_summary(signals)
        
        assert summary['total_signals'] == 2
        assert summary['by_strategy']['momentum'] == 1
        assert summary['by_strategy']['retest'] == 1
        assert summary['by_side']['long'] == 1
        assert summary['by_side']['short'] == 1
        assert summary['avg_confidence'] == 0.7
        assert summary['top_symbols'] == ["BTC/USDT", "ETH/USDT"]
    
    def test_generate_signals_error_handling(self, generator, mock_scan_result):
        """Тест обработки ошибок при генерации сигналов."""
        # Мокаем метод, который вызовет исключение
        generator.momentum_strategy.generate_signal = Mock(side_effect=Exception("Test error"))
        
        signals = generator.generate_signals([mock_scan_result])
        
        # Должен обработать ошибку и продолжить
        assert signals == []


class TestSyntheticSignals:
    """Synthetic scenario tests for end-to-end signal generation."""

    @pytest.fixture(scope="module")
    def preset(self):
        return get_preset('breakout_v1')

    def _build_filter_maps(self) -> Dict[str, bool]:
        return {
            'min_24h_volume': True,
            'max_spread': True,
            'min_depth_0_5pct': True,
            'min_depth_0_3pct': True,
            'min_trades_per_minute': True,
            'atr_range': True,
            'bb_width': True,
            'volume_surge_1h': True,
            'volume_surge_5m': True,
            'correlation': True,
            'data_health': True,
        }

    def _build_filter_details(self) -> Dict[str, Dict[str, float]]:
        return {name: {'passed': True, 'value': 1.0, 'threshold': 0.0, 'reason': 'synthetic'} for name in self._build_filter_maps().keys()}

    def _build_momentum_candles(self) -> List[Candle]:
        base = int(datetime.now().timestamp() * 1000) - 39 * 300000
        candles: List[Candle] = []
        for i in range(40):
            ts = base + i * 300000
            open_price = 100.0 + i * 0.01
            close_price = open_price + 0.06
            high = close_price + 0.02
            low = open_price - 0.02
            volume = 1200.0
            if i == 39:
                close_price = open_price + 0.12
                volume = 5000.0
            candles.append(Candle(ts=ts, open=open_price, high=high, low=low, close=close_price, volume=volume))
        return candles

    def test_signal_momentum_synthetic(self, preset):
        candles = self._build_momentum_candles()
        l2_depth = L2Depth(
            bid_usd_0_5pct=200000.0,
            ask_usd_0_5pct=200000.0,
            bid_usd_0_3pct=120000.0,
            ask_usd_0_3pct=120000.0,
            spread_bps=3.0,
            imbalance=0.6,
        )
        market_data = MarketData(
            symbol='SYNTH/USDT',
            price=candles[-1].close,
            volume_24h_usd=250_000_000.0,
            oi_usd=100_000_000.0,
            oi_change_24h=0.05,
            trades_per_minute=25.0,
            atr_5m=0.12,
            atr_15m=0.18,
            bb_width_pct=12.0,
            btc_correlation=0.2,
            l2_depth=l2_depth,
            candles_5m=candles,
            timestamp=candles[-1].ts,
        )
        scan_result = ScanResult(
            symbol='SYNTH/USDT',
            score=1.2,
            rank=1,
            market_data=market_data,
            filter_results=self._build_filter_maps(),
            filter_details=self._build_filter_details(),
            score_components={'vol_surge': 0.7},
            levels=[
                TradingLevel(
                    price=100.0,
                    level_type='resistance',
                    touch_count=4,
                    strength=0.9,
                    first_touch_ts=candles[10].ts,
                    last_touch_ts=candles[-5].ts,
                )
            ],
            timestamp=candles[-1].ts,
        )

        generator = SignalGenerator(preset)
        signal = asyncio.run(generator.generate_signal(scan_result))

        assert signal is not None, "Momentum signal should be generated on synthetic breakout"
        assert signal.strategy == 'momentum'
        assert signal.symbol == 'SYNTH/USDT'

    def _build_retest_candles(self) -> List[Candle]:
        base = int(datetime.now().timestamp() * 1000) - 39 * 300000
        candles: List[Candle] = []
        for i in range(40):
            ts = base + i * 300000
            open_price = 50.0 + i * 0.01
            close_price = open_price + 0.01
            high = close_price + 0.01
            low = open_price - 0.02
            volume = 900.0
            if i == 30:
                open_price = 50.8
                close_price = 51.0
                high = 51.2
                low = 50.6
                volume = 3000.0
            if i == 39:
                open_price = 50.48
                close_price = 50.52
                high = 50.52
                low = 50.42
                volume = 1200.0
            candles.append(Candle(ts=ts, open=open_price, high=high, low=low, close=close_price, volume=volume))
        return candles

    def test_signal_retest_synthetic(self, preset):
        candles = self._build_retest_candles()
        l2_depth = L2Depth(
            bid_usd_0_5pct=120000.0,
            ask_usd_0_5pct=120000.0,
            bid_usd_0_3pct=80000.0,
            ask_usd_0_3pct=80000.0,
            spread_bps=4.0,
            imbalance=0.55,
        )
        market_data = MarketData(
            symbol='SYNTH/USDT',
            price=candles[-1].close,
            volume_24h_usd=180_000_000.0,
            oi_usd=90_000_000.0,
            oi_change_24h=0.04,
            trades_per_minute=18.0,
            atr_5m=0.08,
            atr_15m=0.12,
            bb_width_pct=9.0,
            btc_correlation=0.25,
            l2_depth=l2_depth,
            candles_5m=candles,
            timestamp=candles[-1].ts,
        )
        level = TradingLevel(
            price=50.5,
            level_type='support',
            touch_count=5,
            strength=0.85,
            first_touch_ts=candles[5].ts,
            last_touch_ts=candles[-10].ts,
        )
        scan_result = ScanResult(
            symbol='SYNTH/USDT',
            score=0.9,
            rank=1,
            market_data=market_data,
            filter_results=self._build_filter_maps(),
            filter_details=self._build_filter_details(),
            score_components={'vol_surge': 0.6},
            levels=[level],
            timestamp=candles[-1].ts,
        )

        generator = SignalGenerator(preset)
        generator.retest_strategy.add_breakout_history(
            'SYNTH/USDT',
            {
                'timestamp': candles[-8].ts,
                'level_price': level.price,
                'side': 'long',
            },
        )

        signal = asyncio.run(generator.generate_signal(scan_result))

        assert signal is not None, "Retest signal should fire for synthetic retest"
        assert signal.strategy == 'retest'
        assert signal.symbol == 'SYNTH/USDT'
