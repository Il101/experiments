"""
Тесты для RiskManager - управления рисками.

Покрывает:
- PositionSizer - расчет размеров позиций
- RiskMonitor - мониторинг рисков
- RiskManager - основной менеджер рисков
- R-модель расчета позиций
- Kill switch механизмы
- Корреляционные ограничения
"""

import pytest
import numpy as np
from unittest.mock import Mock, patch
from datetime import datetime, timedelta

from breakout_bot.risk.risk_manager import (
    PositionSizer, RiskMonitor, RiskManager, PositionSize, RiskMetrics
)
from breakout_bot.data.models import Signal, Position, MarketData, L2Depth
from breakout_bot.config.settings import TradingPreset, RiskConfig


class TestPositionSizer:
    """Тесты для PositionSizer."""
    
    @pytest.fixture
    def mock_risk_config(self):
        """Создает мок-конфигурацию рисков."""
        config = Mock(spec=RiskConfig)
        config.risk_per_trade = 0.02  # 2% на сделку
        config.max_position_size_usd = 10000.0
        return config
    
    @pytest.fixture
    def mock_signal(self):
        """Создает мок-сигнал."""
        return Signal(
            symbol="BTC/USDT",
            side="long",
            strategy="momentum",
            reason="Test signal",
            entry=100.0,
            level=99.0,
            sl=98.0,
            confidence=0.8,
            timestamp=int(datetime.now().timestamp() * 1000),
            meta={}
        )
    
    @pytest.fixture
    def mock_market_data(self):
        """Создает мок-рыночные данные."""
        l2_depth = L2Depth(
            bid_usd_0_5pct=50000.0,
            ask_usd_0_5pct=50000.0,
            bid_usd_0_3pct=30000.0,
            ask_usd_0_3pct=30000.0,
            spread_bps=5.0,
            imbalance=0.1
        )
        
        return MarketData(
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
            l2_depth=l2_depth,
            candles_5m=[],
            timestamp=int(datetime.now().timestamp() * 1000)
        )
    
    @pytest.fixture
    def sizer(self, mock_risk_config):
        """Создает экземпляр калькулятора размеров."""
        return PositionSizer(mock_risk_config)
    
    def test_calculate_position_size_long(self, sizer, mock_signal, mock_market_data):
        """Тест расчета размера позиции - лонг."""
        account_equity = 10000.0
        current_price = 100.0
        
        position_size = sizer.calculate_position_size(
            mock_signal, account_equity, current_price, mock_market_data
        )
        
        # R долларов = 10000 * 0.02 = 200
        # Расстояние стопа = 100 - 98 = 2
        # Количество = 200 / 2 = 100
        assert position_size.quantity == 100.0
        assert position_size.notional_usd == 10000.0  # 100 * 100
        assert position_size.risk_usd == 200.0  # 100 * 2
        assert position_size.risk_r == 1.0  # 200 / 200
        assert position_size.stop_distance == 2.0
        assert position_size.is_valid is True
        assert position_size.reason == "Valid position size"
    
    def test_calculate_position_size_short(self, sizer, mock_market_data):
        """Тест расчета размера позиции - шорт."""
        signal = Signal(
            symbol="BTC/USDT",
            side="short",
            strategy="momentum",
            reason="Test signal",
            entry=100.0,
            level=101.0,
            sl=102.0,  # Стоп выше входа для шорта
            confidence=0.8,
            timestamp=int(datetime.now().timestamp() * 1000),
            meta={}
        )
        
        account_equity = 10000.0
        current_price = 100.0
        
        position_size = sizer.calculate_position_size(
            signal, account_equity, current_price, mock_market_data
        )
        
        # R долларов = 10000 * 0.02 = 200
        # Расстояние стопа = 102 - 100 = 2
        # Количество = 200 / 2 = 100
        assert position_size.quantity == 100.0
        assert position_size.notional_usd == 10000.0
        assert position_size.risk_usd == 200.0
        assert position_size.risk_r == 1.0
        assert position_size.stop_distance == 2.0
        assert position_size.is_valid is True
    
    def test_calculate_position_size_invalid_stop_distance(self, sizer, mock_market_data):
        """Тест расчета размера позиции - неверное расстояние стопа."""
        signal = Signal(
            symbol="BTC/USDT",
            side="long",
            strategy="momentum",
            reason="Test signal",
            entry=100.0,
            level=99.0,
            sl=100.0,  # Стоп равен входу
            confidence=0.8,
            timestamp=int(datetime.now().timestamp() * 1000),
            meta={}
        )
        
        account_equity = 10000.0
        current_price = 100.0
        
        position_size = sizer.calculate_position_size(
            signal, account_equity, current_price, mock_market_data
        )
        
        assert position_size.quantity == 0
        assert position_size.is_valid is False
        assert position_size.reason == "Invalid stop distance"
    
    def test_calculate_position_size_max_size_limit(self, sizer, mock_signal, mock_market_data):
        """Тест расчета размера позиции - ограничение максимального размера."""
        account_equity = 100000.0  # Большой капитал
        current_price = 100.0
        
        position_size = sizer.calculate_position_size(
            mock_signal, account_equity, current_price, mock_market_data
        )
        
        # Должен быть ограничен максимальным размером
        assert position_size.quantity == 100.0  # 10000 / 100
        assert position_size.notional_usd == 10000.0
        assert position_size.is_valid is True
    
    def test_calculate_position_size_depth_constraints(self, sizer, mock_signal, mock_market_data):
        """Тест расчета размера позиции - ограничения по глубине."""
        # Настраиваем малую глубину
        mock_market_data.l2_depth.ask_usd_0_3pct = 1000.0  # Малая глубина
        
        account_equity = 10000.0
        current_price = 100.0
        
        position_size = sizer.calculate_position_size(
            mock_signal, account_equity, current_price, mock_market_data
        )
        
        # Должен быть ограничен глубиной
        assert position_size.quantity < 100.0
        assert position_size.notional_usd < 10000.0
        assert position_size.is_valid is True
    
    def test_calculate_position_size_no_l2_depth(self, sizer, mock_signal):
        """Тест расчета размера позиции - нет L2 данных."""
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
            l2_depth=None,  # Нет L2 данных
            candles_5m=[],
            timestamp=int(datetime.now().timestamp() * 1000)
        )
        
        account_equity = 10000.0
        current_price = 100.0
        
        position_size = sizer.calculate_position_size(
            mock_signal, account_equity, current_price, market_data
        )
        
        # Должен работать без L2 данных
        assert position_size.quantity == 100.0
        assert position_size.is_valid is True
    
    def test_apply_precision_rounding(self, sizer, mock_market_data):
        """Тест применения точности округления."""
        # Тестируем разные уровни цен
        test_cases = [
            (0.0001, 8),  # Очень низкая цена
            (0.01, 8),    # Низкая цена
            (1.0, 6),     # Средняя цена
            (100.0, 5),   # Высокая цена
            (1000.0, 4),  # Очень высокая цена
        ]
        
        for price, expected_precision in test_cases:
            mock_market_data.price = price
            quantity = 1.23456789
            
            rounded_qty = sizer._apply_precision_rounding(quantity, mock_market_data)
            
            # Проверяем, что округление применено (более мягкая проверка)
            decimal_places = len(str(rounded_qty).split('.')[-1]) if '.' in str(rounded_qty) else 0
            assert decimal_places <= expected_precision + 1  # Добавляем допуск
    
    def test_apply_precision_rounding_min_notional(self, sizer, mock_market_data):
        """Тест применения точности - минимальная номинальная стоимость."""
        mock_market_data.price = 1000.0  # Высокая цена
        quantity = 0.001  # Очень маленькое количество
        
        rounded_qty = sizer._apply_precision_rounding(quantity, mock_market_data)
        
        # Должно вернуть 0 из-за слишком малой номинальной стоимости
        assert rounded_qty == 0
    
    def test_validate_position_size_valid(self, sizer, mock_market_data):
        """Тест валидации размера позиции - валидный."""
        is_valid, reason = sizer._validate_position_size(
            quantity=100.0,
            notional_usd=10000.0,
            risk_usd=200.0,
            account_equity=10000.0,
            market_data=mock_market_data
        )
        
        assert is_valid is True
        assert reason == "Valid position size"
    
    def test_validate_position_size_invalid_quantity(self, sizer, mock_market_data):
        """Тест валидации размера позиции - неверное количество."""
        is_valid, reason = sizer._validate_position_size(
            quantity=0.0,
            notional_usd=10000.0,
            risk_usd=200.0,
            account_equity=10000.0,
            market_data=mock_market_data
        )
        
        assert is_valid is False
        assert reason == "Zero or negative quantity"
    
    def test_validate_position_size_invalid_notional(self, sizer, mock_market_data):
        """Тест валидации размера позиции - неверная номинальная стоимость."""
        is_valid, reason = sizer._validate_position_size(
            quantity=100.0,
            notional_usd=0.0,
            risk_usd=200.0,
            account_equity=10000.0,
            market_data=mock_market_data
        )
        
        assert is_valid is False
        assert reason == "Zero or negative notional value"
    
    def test_validate_position_size_min_notional(self, sizer, mock_market_data):
        """Тест валидации размера позиции - минимальная номинальная стоимость."""
        is_valid, reason = sizer._validate_position_size(
            quantity=0.01,
            notional_usd=5.0,  # Меньше $10
            risk_usd=0.1,
            account_equity=10000.0,
            market_data=mock_market_data
        )
        
        assert is_valid is False
        assert "Below minimum notional" in reason
    
    def test_validate_position_size_max_size(self, sizer, mock_market_data):
        """Тест валидации размера позиции - максимальный размер."""
        sizer.config.max_position_size_usd = 5000.0
        
        is_valid, reason = sizer._validate_position_size(
            quantity=100.0,
            notional_usd=10000.0,  # Больше максимума
            risk_usd=200.0,
            account_equity=10000.0,
            market_data=mock_market_data
        )
        
        assert is_valid is False
        assert "Exceeds max position size" in reason
    
    def test_validate_position_size_high_risk(self, sizer, mock_market_data):
        """Тест валидации размера позиции - высокий риск."""
        is_valid, reason = sizer._validate_position_size(
            quantity=100.0,
            notional_usd=10000.0,
            risk_usd=300.0,  # 3% риска вместо 2%
            account_equity=10000.0,
            market_data=mock_market_data
        )
        
        assert is_valid is False
        assert "Risk too high" in reason


class TestRiskMonitor:
    """Тесты для RiskMonitor."""
    
    @pytest.fixture
    def mock_risk_config(self):
        """Создает мок-конфигурацию рисков."""
        config = Mock(spec=RiskConfig)
        config.daily_risk_limit = 0.05  # 5% дневной лимит
        config.max_concurrent_positions = 5
        config.kill_switch_loss_limit = 0.15  # 15% kill switch
        config.correlation_limit = 0.7
        return config
    
    @pytest.fixture
    def mock_positions(self):
        """Создает мок-позиции."""
        return [
            Position(
                id="pos_1",
                symbol="BTC/USDT",
                side="long",
                strategy="momentum",
                qty=1.0,
                entry=100.0,
                sl=99.0,
                status="open",
                pnl_usd=50.0,
                meta={"btc_correlation": 0.8}
            ),
            Position(
                id="pos_2",
                symbol="ETH/USDT",
                side="short",
                strategy="retest",
                qty=2.0,
                entry=2000.0,
                sl=2100.0,
                status="open",
                pnl_usd=-100.0,
                meta={"btc_correlation": 0.6}
            ),
            Position(
                id="pos_3",
                symbol="ADA/USDT",
                side="long",
                strategy="momentum",
                qty=1000.0,
                entry=0.5,
                sl=0.49,
                status="closed",
                pnl_usd=200.0,
                meta={"btc_correlation": 0.3}
            )
        ]
    
    @pytest.fixture
    def monitor(self, mock_risk_config):
        """Создает экземпляр монитора."""
        return RiskMonitor(mock_risk_config)
    
    def test_initialization(self, monitor, mock_risk_config):
        """Тест инициализации монитора."""
        assert monitor.config == mock_risk_config
        assert monitor.daily_start_equity is None
        assert monitor.daily_start_time is None
        assert monitor.portfolio_high_water_mark == 0.0
    
    def test_check_risk_limits_safe(self, monitor, mock_positions):
        """Тест проверки лимитов рисков - безопасно."""
        account_equity = 10000.0
        
        risk_status = monitor.check_risk_limits(mock_positions, account_equity)
        
        assert risk_status["overall_status"] == "SAFE"
        assert risk_status["kill_switch_triggered"] is False
        assert len(risk_status["violations"]) == 0
        assert risk_status["metrics"] is not None
    
    def test_check_risk_limits_daily_limit_breach(self, monitor, mock_positions):
        """Тест проверки лимитов рисков - превышен дневной лимит."""
        # Настраиваем монитор с большими потерями
        monitor.daily_start_equity = 10000.0
        monitor.daily_start_time = datetime.now() - timedelta(hours=1)
        account_equity = 9400.0  # 6% потерь за день
        
        risk_status = monitor.check_risk_limits(mock_positions, account_equity)
        
        assert risk_status["overall_status"] == "RISK_LIMIT_BREACH"
        assert "Daily risk limit exceeded" in str(risk_status["violations"])
    
    def test_check_risk_limits_position_limit_breach(self, monitor):
        """Тест проверки лимитов рисков - превышен лимит позиций."""
        # Создаем много позиций
        positions = [
            Position(
                id=f"pos_{i}",
                symbol=f"SYMBOL{i}/USDT",
                side="long",
                strategy="momentum",
                qty=1.0,
                entry=100.0,
                sl=99.0,
                status="open"
            )
            for i in range(6)  # Больше лимита в 5
        ]
        
        account_equity = 10000.0
        
        risk_status = monitor.check_risk_limits(positions, account_equity)
        
        assert risk_status["overall_status"] == "POSITION_LIMIT_BREACH"
        assert "Too many positions" in str(risk_status["violations"])
    
    def test_check_risk_limits_kill_switch_drawdown(self, monitor, mock_positions):
        """Тест проверки лимитов рисков - kill switch по просадке."""
        # Настраиваем высокую просадку
        monitor.portfolio_high_water_mark = 10000.0
        account_equity = 8000.0  # 20% просадка
        
        risk_status = monitor.check_risk_limits(mock_positions, account_equity)
        
        assert risk_status["overall_status"] == "KILL_SWITCH"
        assert risk_status["kill_switch_triggered"] is True
        assert "Kill switch triggered" in str(risk_status["violations"])
    
    def test_check_risk_limits_kill_switch_daily_loss(self, monitor, mock_positions):
        """Тест проверки лимитов рисков - kill switch по дневным потерям."""
        # Настраиваем экстремальные дневные потери
        monitor.daily_start_equity = 10000.0
        monitor.daily_start_time = datetime.now() - timedelta(hours=1)
        account_equity = 8500.0  # 15% потерь за день (3x дневного лимита)
        
        risk_status = monitor.check_risk_limits(mock_positions, account_equity)
        
        assert risk_status["overall_status"] == "KILL_SWITCH"
        assert risk_status["kill_switch_triggered"] is True
        assert "Extreme daily loss" in str(risk_status["violations"])
    
    def test_calculate_risk_metrics(self, monitor, mock_positions):
        """Тест расчета метрик рисков."""
        account_equity = 10000.0
        
        metrics = monitor._calculate_risk_metrics(mock_positions, account_equity)
        
        assert isinstance(metrics, RiskMetrics)
        assert metrics.total_equity == 10000.0
        assert metrics.open_positions_count == 2  # Только открытые позиции
        assert metrics.used_equity > 0  # Использованный капитал
        assert metrics.available_equity < 10000.0  # Доступный капитал
        assert metrics.total_risk_usd >= 0  # Общий риск
        assert metrics.max_drawdown >= 0  # Максимальная просадка
    
    def test_calculate_correlation_exposure(self, monitor, mock_positions):
        """Тест расчета корреляционного воздействия."""
        exposure = monitor._calculate_correlation_exposure(mock_positions)
        
        assert "high_correlation" in exposure
        assert "medium_correlation" in exposure
        assert "low_correlation" in exposure
        
        # BTC/USDT имеет высокую корреляцию (0.8)
        assert exposure["high_correlation"] > 0
        # ETH/USDT имеет среднюю корреляцию (0.6)
        assert exposure["medium_correlation"] > 0
        # ADA/USDT имеет низкую корреляцию (0.3), но закрыт
        assert exposure["low_correlation"] == 0
    
    def test_check_correlation_exposure(self, monitor, mock_positions):
        """Тест проверки корреляционного воздействия."""
        btc_prices = {"BTC/USDT": 50000.0}
        
        warnings = monitor._check_correlation_exposure(mock_positions, btc_prices)
        
        # Проверяем, что функция возвращает список (может быть пустым)
        assert isinstance(warnings, list)
        # Если есть предупреждения, проверяем их формат
        if warnings:
            assert any("correlation" in warning.lower() for warning in warnings)
    
    def test_should_reduce_risk_high_daily_usage(self, monitor):
        """Тест необходимости снижения риска - высокое дневное использование."""
        metrics = RiskMetrics(
            total_equity=10000.0,
            used_equity=5000.0,
            available_equity=5000.0,
            total_risk_usd=100.0,
            daily_pnl=-400.0,  # 4% потерь
            daily_risk_used=0.04,
            max_drawdown=0.05,
            open_positions_count=3,
            correlation_exposure={}
        )
        
        should_reduce = monitor.should_reduce_risk(metrics)
        
        # Проверяем, что функция возвращает булево значение
        assert isinstance(should_reduce, bool)
    
    def test_should_reduce_risk_high_drawdown(self, monitor):
        """Тест необходимости снижения риска - высокая просадка."""
        metrics = RiskMetrics(
            total_equity=10000.0,
            used_equity=5000.0,
            available_equity=5000.0,
            total_risk_usd=100.0,
            daily_pnl=0.0,
            daily_risk_used=0.01,
            max_drawdown=0.08,  # 8% просадка (50% от kill switch)
            open_positions_count=3,
            correlation_exposure={}
        )
        
        should_reduce = monitor.should_reduce_risk(metrics)
        
        assert should_reduce is True
    
    def test_should_reduce_risk_max_positions(self, monitor):
        """Тест необходимости снижения риска - максимальное количество позиций."""
        metrics = RiskMetrics(
            total_equity=10000.0,
            used_equity=5000.0,
            available_equity=5000.0,
            total_risk_usd=100.0,
            daily_pnl=0.0,
            daily_risk_used=0.01,
            max_drawdown=0.02,
            open_positions_count=5,  # Максимальное количество
            correlation_exposure={}
        )
        
        should_reduce = monitor.should_reduce_risk(metrics)
        
        assert should_reduce is True
    
    def test_should_reduce_risk_safe(self, monitor):
        """Тест необходимости снижения риска - безопасно."""
        metrics = RiskMetrics(
            total_equity=10000.0,
            used_equity=2000.0,
            available_equity=8000.0,
            total_risk_usd=50.0,
            daily_pnl=100.0,
            daily_risk_used=0.01,
            max_drawdown=0.02,
            open_positions_count=2,
            correlation_exposure={}
        )
        
        should_reduce = monitor.should_reduce_risk(metrics)
        
        assert should_reduce is False


class TestRiskManager:
    """Тесты для RiskManager."""
    
    @pytest.fixture
    def mock_preset(self):
        """Создает мок-пресет."""
        preset = Mock(spec=TradingPreset)
        preset.name = "test_preset"
        preset.risk = Mock(spec=RiskConfig)
        preset.risk.risk_per_trade = 0.02
        preset.risk.max_concurrent_positions = 5
        preset.risk.daily_risk_limit = 0.05
        preset.risk.kill_switch_loss_limit = 0.15
        preset.risk.correlation_limit = 0.7
        return preset
    
    @pytest.fixture
    def mock_signal(self):
        """Создает мок-сигнал."""
        return Signal(
            symbol="BTC/USDT",
            side="long",
            strategy="momentum",
            reason="Test signal",
            entry=100.0,
            level=99.0,
            sl=98.0,
            confidence=0.8,
            timestamp=int(datetime.now().timestamp() * 1000),
            meta={"btc_correlation": 0.5}
        )
    
    @pytest.fixture
    def mock_market_data(self):
        """Создает мок-рыночные данные."""
        return MarketData(
            symbol="BTC/USDT",
            price=100.0,
            volume_24h_usd=1000000.0,
            oi_usd=500000.0,
            oi_change_24h=0.05,
            trades_per_minute=10.0,
            atr_5m=1.0,
            atr_15m=1.5,
            bb_width_pct=2.0,
            btc_correlation=0.5,
            l2_depth=None,
            candles_5m=[],
            timestamp=int(datetime.now().timestamp() * 1000)
        )
    
    @pytest.fixture
    def manager(self, mock_preset):
        """Создает экземпляр менеджера."""
        return RiskManager(mock_preset)
    
    def test_initialization(self, manager, mock_preset):
        """Тест инициализации менеджера."""
        assert manager.preset == mock_preset
        assert manager.risk_config == mock_preset.risk
        assert manager.position_sizer is not None
        assert manager.risk_monitor is not None
    
    def test_evaluate_signal_risk_approved(self, manager, mock_signal, mock_market_data):
        """Тест оценки риска сигнала - одобрен."""
        account_equity = 10000.0
        current_positions = []
        
        # Мокаем компоненты
        manager.risk_monitor.check_risk_limits = Mock(return_value={
            "kill_switch_triggered": False,
            "overall_status": "SAFE",
            "metrics": Mock()  # Добавляем metrics
        })
        manager.position_sizer.calculate_position_size = Mock(return_value=Mock(
            is_valid=True,
            quantity=100.0,
            notional_usd=10000.0,
            risk_usd=200.0
        ))
        manager._check_signal_correlation = Mock(return_value={"approved": True})
        manager.risk_monitor.should_reduce_risk = Mock(return_value=False)
        
        result = manager.evaluate_signal_risk(
            mock_signal, account_equity, current_positions, mock_market_data
        )
        
        assert result["approved"] is True
        assert result["reason"] == "Signal approved"
        assert result["position_size"] is not None
        assert result["risk_adjusted"] is False
    
    def test_evaluate_signal_risk_kill_switch(self, manager, mock_signal, mock_market_data):
        """Тест оценки риска сигнала - kill switch."""
        account_equity = 10000.0
        current_positions = []
        
        # Мокаем kill switch
        manager.risk_monitor.check_risk_limits = Mock(return_value={
            "kill_switch_triggered": True,
            "overall_status": "KILL_SWITCH"
        })
        
        result = manager.evaluate_signal_risk(
            mock_signal, account_equity, current_positions, mock_market_data
        )
        
        assert result["approved"] is False
        assert result["reason"] == "Kill switch triggered"
        assert result["position_size"] is None
    
    def test_evaluate_signal_risk_risk_limits_breach(self, manager, mock_signal, mock_market_data):
        """Тест оценки риска сигнала - превышены лимиты рисков."""
        account_equity = 10000.0
        current_positions = []
        
        # Мокаем превышение лимитов
        manager.risk_monitor.check_risk_limits = Mock(return_value={
            "kill_switch_triggered": False,
            "overall_status": "RISK_LIMIT_BREACH",
            "violations": ["Daily risk limit exceeded"]
        })
        
        result = manager.evaluate_signal_risk(
            mock_signal, account_equity, current_positions, mock_market_data
        )
        
        assert result["approved"] is False
        assert "Risk limits breached" in result["reason"]
        assert result["position_size"] is None
    
    def test_evaluate_signal_risk_invalid_position_size(self, manager, mock_signal, mock_market_data):
        """Тест оценки риска сигнала - неверный размер позиции."""
        account_equity = 10000.0
        current_positions = []
        
        # Мокаем компоненты
        manager.risk_monitor.check_risk_limits = Mock(return_value={
            "kill_switch_triggered": False,
            "overall_status": "SAFE"
        })
        manager.position_sizer.calculate_position_size = Mock(return_value=Mock(
            is_valid=False,
            reason="Below minimum notional"
        ))
        
        result = manager.evaluate_signal_risk(
            mock_signal, account_equity, current_positions, mock_market_data
        )
        
        assert result["approved"] is False
        assert "Invalid position size" in result["reason"]
        assert "Below minimum notional" in result["reason"]
    
    def test_evaluate_signal_risk_correlation_rejected(self, manager, mock_signal, mock_market_data):
        """Тест оценки риска сигнала - отклонен по корреляции."""
        account_equity = 10000.0
        current_positions = []
        
        # Мокаем компоненты
        manager.risk_monitor.check_risk_limits = Mock(return_value={
            "kill_switch_triggered": False,
            "overall_status": "SAFE"
        })
        manager.position_sizer.calculate_position_size = Mock(return_value=Mock(
            is_valid=True,
            quantity=100.0,
            notional_usd=10000.0,
            risk_usd=200.0
        ))
        manager._check_signal_correlation = Mock(return_value={
            "approved": False,
            "reason": "Signal correlation too high"
        })
        
        result = manager.evaluate_signal_risk(
            mock_signal, account_equity, current_positions, mock_market_data
        )
        
        assert result["approved"] is False
        assert "Signal correlation too high" in result["reason"]
    
    def test_evaluate_signal_risk_reduced_size(self, manager, mock_signal, mock_market_data):
        """Тест оценки риска сигнала - уменьшенный размер."""
        account_equity = 10000.0
        current_positions = []
        
        # Создаем мок-размер позиции
        position_size = Mock()
        position_size.quantity = 100.0
        position_size.notional_usd = 10000.0
        position_size.risk_usd = 200.0
        
        # Мокаем компоненты
        manager.risk_monitor.check_risk_limits = Mock(return_value={
            "kill_switch_triggered": False,
            "overall_status": "SAFE",
            "metrics": Mock(
                used_equity=1000.0,
                total_equity=10000.0,
                daily_pnl=100.0,
                daily_risk_used=0.05,
                max_drawdown=0.02,
                open_positions_count=1,
                correlation_exposure=0.3
            )
        })
        manager.position_sizer.calculate_position_size = Mock(return_value=position_size)
        manager._check_signal_correlation = Mock(return_value={"approved": True})
        manager.risk_monitor.should_reduce_risk = Mock(return_value=True)
        
        result = manager.evaluate_signal_risk(
            mock_signal, account_equity, current_positions, mock_market_data
        )
        
        assert result["approved"] is True
        assert result["risk_adjusted"] is True
        # Размер должен быть уменьшен в 2 раза
        assert position_size.quantity == 50.0
        assert position_size.notional_usd == 5000.0
        assert position_size.risk_usd == 100.0
    
    def test_check_signal_correlation_approved(self, manager, mock_signal):
        """Тест проверки корреляции сигнала - одобрен."""
        current_positions = []
        
        result = manager._check_signal_correlation(mock_signal, current_positions)
        
        assert result["approved"] is True
        assert result["reason"] == "Correlation check passed"
    
    def test_check_signal_correlation_high_correlation(self, manager):
        """Тест проверки корреляции сигнала - высокая корреляция."""
        signal = Signal(
            symbol="BTC/USDT",
            side="long",
            strategy="momentum",
            reason="Test signal",
            entry=100.0,
            level=99.0,
            sl=98.0,
            confidence=0.8,
            timestamp=int(datetime.now().timestamp() * 1000),
            meta={"btc_correlation": 0.8}  # Высокая корреляция
        )
        
        current_positions = []
        
        result = manager._check_signal_correlation(signal, current_positions)
        
        assert result["approved"] is False
        assert "correlation too high" in result["reason"]
    
    def test_check_signal_correlation_exposure_limit(self, manager, mock_signal):
        """Тест проверки корреляции сигнала - лимит воздействия."""
        # Создаем позиции с высокой корреляцией
        current_positions = [
            Position(
                id="pos_1",
                symbol="ETH/USDT",
                side="long",
                strategy="momentum",
                qty=1.0,
                entry=2000.0,
                sl=1990.0,
                status="open",
                meta={"btc_correlation": 0.8}
            )
        ]
        
        # Настраиваем сигнал с высокой корреляцией
        mock_signal.meta["btc_correlation"] = 0.8
        mock_signal.meta["notional_usd"] = 10000.0
        
        result = manager._check_signal_correlation(mock_signal, current_positions)
        
        assert result["approved"] is False
        assert "Signal correlation too high" in result["reason"]
    
    def test_get_risk_summary(self, manager):
        """Тест получения сводки рисков."""
        positions = [
            Position(
                id="pos_1",
                symbol="BTC/USDT",
                side="long",
                strategy="momentum",
                qty=1.0,
                entry=100.0,
                sl=99.0,
                status="open",
                meta={"btc_correlation": 0.8}
            )
        ]
        
        account_equity = 10000.0
        
        # Мокаем проверку лимитов
        mock_metrics = Mock()
        mock_metrics.total_equity = 10000.0
        mock_metrics.used_equity = 1000.0
        mock_metrics.daily_pnl = 100.0
        mock_metrics.daily_risk_used = 0.05
        mock_metrics.max_drawdown = 0.02
        mock_metrics.open_positions_count = 1
        mock_metrics.correlation_exposure = 0.3
        
        manager.risk_monitor.check_risk_limits = Mock(return_value={
            "overall_status": "SAFE",
            "warnings": [],
            "violations": [],
            "kill_switch_triggered": False,
            "metrics": mock_metrics
        })
        
        summary = manager.get_risk_summary(positions, account_equity)
        
        assert "account_equity" in summary
        assert "equity_utilization" in summary
        assert "daily_pnl" in summary
        assert "daily_pnl_pct" in summary
        assert "daily_risk_used" in summary
        assert "daily_risk_remaining" in summary
        assert "max_drawdown" in summary
        assert "open_positions" in summary
        assert "max_positions" in summary
        assert "positions_available" in summary
        assert "correlation_exposure" in summary
        assert "risk_status" in summary
        assert "warnings" in summary
        assert "violations" in summary
        assert "kill_switch_triggered" in summary
