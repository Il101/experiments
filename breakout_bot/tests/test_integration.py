"""
Интеграционные тесты для всей торговой системы.

Покрывает:
- Полный цикл работы системы
- Взаимодействие между компонентами
- End-to-end сценарии
- Обработка ошибок на системном уровне
"""

import pytest
import asyncio
import numpy as np
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta

from breakout_bot.core.engine import OptimizedOrchestraEngine, TradingState
from breakout_bot.data.models import (
    Candle, L2Depth, MarketData, ScanResult, TradingLevel, Signal, Position, Order
)
from breakout_bot.config.settings import TradingPreset, SystemConfig, load_preset
from breakout_bot.risk.risk_manager import PositionSize


class TestSystemIntegration:
    """Интеграционные тесты для всей системы."""
    
    @pytest.fixture
    def mock_preset(self):
        """Возвращает реальный пресет breakout_v1."""
        preset = load_preset("breakout_v1").model_copy(deep=True)
        preset.name = "integration_test"
        return preset
    
    @pytest.fixture
    def mock_system_config(self):
        """Создает мок-системную конфигурацию."""
        return SystemConfig(
            exchange="bybit",
            trading_mode="paper",
            log_level="INFO",
            log_to_file=False,
            database_url="sqlite:///integration-test.db",
            paper_starting_balance=100000.0,
            paper_slippage_bps=5.0,
        )
    
    @pytest.fixture
    def mock_market_data(self):
        """Создает мок-рыночные данные для тестов."""
        # Создаем свечи с восходящим трендом
        candles = []
        base_time = int(datetime.now().timestamp() * 1000)
        
        for i in range(25):
            candle = Candle(
                ts=base_time - (25 - i) * 300000,  # 5-минутные свечи
                open=100.0 + i * 0.1,
                high=101.0 + i * 0.1,
                low=99.0 + i * 0.1,
                close=100.5 + i * 0.1,
                volume=1000.0 + i * 100  # Увеличивающийся объем
            )
            candles.append(candle)
        
        l2_depth = L2Depth(
            bid_usd_0_5pct=50000.0,
            ask_usd_0_5pct=50000.0,
            bid_usd_0_3pct=30000.0,
            ask_usd_0_3pct=30000.0,
            spread_bps=5.0,
            imbalance=0.2
        )
        
        return MarketData(
            symbol="BTC/USDT",
            price=102.5,
            volume_24h_usd=2000000.0,
            oi_usd=1000000.0,
            oi_change_24h=0.15,
            trades_per_minute=15.0,
            atr_5m=1.0,
            atr_15m=1.5,
            bb_width_pct=2.0,
            btc_correlation=0.6,
            l2_depth=l2_depth,
            candles_5m=candles,
            timestamp=int(datetime.now().timestamp() * 1000)
        )
    
    @pytest.fixture
    def mock_scan_result(self, mock_market_data):
        """Создает мок-результат сканирования."""
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
            market_data=mock_market_data,
            filter_results={
                "min_24h_volume": True,
                "max_spread": True,
                "min_depth_0_5pct": True,
                "min_depth_0_3pct": True,
                "min_trades_per_minute": True,
                "atr_range": True,
                "bb_width": True,
                "volume_surge_1h": True,
                "volume_surge_5m": True,
                "oi_delta": True,
                "correlation": True
            },
            score_components={
                "vol_surge": 0.5,
                "oi_delta": 0.3,
                "atr_quality": 0.4,
                "correlation": 0.2,
                "trades_per_minute": 0.1
            },
            levels=[level],
            timestamp=int(datetime.now().timestamp() * 1000)
        )
    
    @pytest.fixture
    def engine(self, mock_preset, mock_system_config):
        """Создает экземпляр движка для интеграционных тестов."""
        with patch('breakout_bot.config.settings.get_preset', return_value=mock_preset):
            with patch('breakout_bot.core.engine.ExchangeClient') as mock_exchange_client:
                with patch('breakout_bot.core.engine.MarketDataProvider') as mock_market_provider:
                    with patch('breakout_bot.core.engine.BreakoutScanner') as mock_scanner:
                        with patch('breakout_bot.core.engine.SignalGenerator') as mock_signal_generator:
                            with patch('breakout_bot.core.engine.RiskManager') as mock_risk_manager:
                                with patch('breakout_bot.core.engine.PositionManager') as mock_position_manager:
                                    with patch('breakout_bot.core.engine.ExecutionManager') as mock_execution_manager:
                                        exchange_client_mock = Mock()
                                        exchange_client_mock.fetch_markets = AsyncMock(return_value=[])
                                        exchange_client_mock.fetch_balance = AsyncMock(return_value={})
                                        mock_exchange_client.return_value = exchange_client_mock

                                        market_provider_mock = Mock()
                                        market_provider_mock.get_multiple_market_data = AsyncMock(return_value={})
                                        mock_market_provider.return_value = market_provider_mock

                                        scanner_mock = Mock()
                                        scanner_mock.scan_markets = AsyncMock(return_value=[])
                                        scanner_mock.build_levels = AsyncMock(return_value=[])
                                        mock_scanner.return_value = scanner_mock

                                        signal_generator_mock = Mock()
                                        signal_generator_mock.generate_signal = AsyncMock(return_value=None)
                                        mock_signal_generator.return_value = signal_generator_mock

                                        risk_manager_mock = Mock()
                                        risk_manager_mock.evaluate_signal_risk = Mock(return_value={"approved": False})
                                        risk_manager_mock.check_risk_limits = Mock(return_value={
                                            "kill_switch_triggered": False,
                                            "overall_status": "SAFE"
                                        })
                                        risk_manager_mock.get_risk_summary = Mock(return_value={})
                                        mock_risk_manager.return_value = risk_manager_mock

                                        position_manager_mock = Mock()
                                        position_manager_mock.process_position_updates = AsyncMock(return_value=[])
                                        position_manager_mock.add_position = Mock()
                                        position_manager_mock.cancel_all_orders = AsyncMock(return_value=None)
                                        position_manager_mock.calculate_position_metrics = Mock(return_value={})
                                        mock_position_manager.return_value = position_manager_mock

                                        filled_order = Order(
                                            id="test-order",
                                            position_id=None,
                                            symbol="BTC/USDT",
                                            side="buy",
                                            order_type="market",
                                            qty=1.0,
                                            price=100.0,
                                            status="filled",
                                            filled_qty=1.0,
                                            avg_fill_price=100.0,
                                            fees_usd=0.1,
                                            timestamps={'created_at': int(datetime.now().timestamp() * 1000)},
                                            exchange_id="test-order",
                                            metadata={}
                                        )

                                        execution_manager_mock = Mock()
                                        execution_manager_mock.execute_trade = AsyncMock(return_value=filled_order)
                                        mock_execution_manager.return_value = execution_manager_mock

                                        engine = OptimizedOrchestraEngine("integration_test", mock_system_config)
                                        engine.execution_manager = execution_manager_mock
                                        engine.exchange_client = exchange_client_mock
                                        engine.market_data_provider = market_provider_mock
                                        engine.scanner = scanner_mock
                                        engine.signal_generator = signal_generator_mock
                                        engine.risk_manager = risk_manager_mock
                                        engine.position_manager = position_manager_mock

                                        return engine
    
    @pytest.mark.asyncio
    async def test_full_trading_cycle_success(self, engine, mock_scan_result, mock_market_data):
        """Тест полного цикла торговли - успешный сценарий."""
        # Настраиваем моки для успешного цикла
        engine.exchange_client.fetch_markets = AsyncMock(return_value=["BTC/USDT"])
        engine.market_data_provider.get_multiple_market_data = AsyncMock(
            return_value={"BTC/USDT": mock_market_data}
        )
        engine.scanner.scan_markets = AsyncMock(return_value=[mock_scan_result])
        
        # Мокаем генерацию сигналов
        mock_signal = Signal(
            symbol="BTC/USDT",
            side="long",
            strategy="momentum",
            reason="Integration test signal",
            entry=100.1,
            level=100.0,
            sl=99.0,
            confidence=0.8,
            timestamp=int(datetime.now().timestamp() * 1000),
            meta={}
        )
        engine.signal_generator.generate_signal = AsyncMock(return_value=mock_signal)

        # Мокаем оценку рисков
        position_size = PositionSize(
            quantity=1.0,
            notional_usd=100.0,
            risk_usd=2.0,
            risk_r=0.02,
            stop_distance=1.1,
            is_valid=True,
            reason="Signal approved",
            precision_adjusted=False,
        )

        engine.risk_manager.evaluate_signal_risk = Mock(return_value={
            "approved": True,
            "position_size": position_size,
            "reason": "Signal approved"
        })

        # Мокаем исполнение ордеров
        engine.exchange_client.fetch_balance = AsyncMock(return_value={"USDT": 10000.0})
        
        # Мокаем управление позициями
        engine.position_manager.add_position = Mock()
        engine.position_manager.process_position_updates = AsyncMock(return_value=[])
        engine.risk_manager.check_risk_limits = Mock(return_value={
            "kill_switch_triggered": False,
            "overall_status": "SAFE"
        })
        
        # Запускаем один цикл
        engine.current_state = TradingState.SCANNING
        engine.last_scan_time = None
        
        await engine._execute_state_cycle()
        
        # Проверяем переходы состояний
        assert engine.current_state == TradingState.LEVEL_BUILDING
        assert len(engine.scan_results) == 1
        
        await engine._execute_state_cycle()
        assert engine.current_state == TradingState.SIGNAL_WAIT
        
        await engine._execute_state_cycle()
        assert engine.current_state == TradingState.SIZING
        
        await engine._execute_state_cycle()
        assert engine.current_state == TradingState.EXECUTION
        
        await engine._execute_state_cycle()
        assert engine.current_state == TradingState.MANAGING
        assert len(engine.current_positions) == 1
    
    @pytest.mark.asyncio
    async def test_full_trading_cycle_no_signals(self, engine, mock_scan_result):
        """Тест полного цикла торговли - нет сигналов."""
        # Настраиваем моки для цикла без сигналов
        engine.exchange_client.fetch_markets = AsyncMock(return_value=["BTC/USDT"])
        engine.market_data_provider.get_multiple_market_data = AsyncMock(
            return_value={"BTC/USDT": mock_scan_result.market_data}
        )
        engine.scanner.scan_markets = AsyncMock(return_value=[mock_scan_result])
        engine.signal_generator.generate_signal = AsyncMock(return_value=None)  # Нет сигналов
        
        # Запускаем цикл
        engine.current_state = TradingState.SCANNING
        engine.last_scan_time = None
        
        await engine._execute_state_cycle()
        assert engine.current_state == TradingState.LEVEL_BUILDING
        
        await engine._execute_state_cycle()
        assert engine.current_state == TradingState.SIGNAL_WAIT
        
        await engine._execute_state_cycle()
        assert engine.current_state == TradingState.SIGNAL_WAIT
    
    @pytest.mark.asyncio
    async def test_full_trading_cycle_signal_rejected(self, engine, mock_scan_result, mock_market_data):
        """Тест полного цикла торговли - сигнал отклонен."""
        # Настраиваем моки
        engine.exchange_client.fetch_markets = AsyncMock(return_value=["BTC/USDT"])
        engine.market_data_provider.get_multiple_market_data = AsyncMock(
            return_value={"BTC/USDT": mock_market_data}
        )
        engine.scanner.scan_markets = AsyncMock(return_value=[mock_scan_result])
        
        # Мокаем сигнал
        mock_signal = Signal(
            symbol="BTC/USDT",
            side="long",
            strategy="momentum",
            reason="Integration test signal",
            entry=100.1,
            level=100.0,
            sl=99.0,
            confidence=0.8,
            timestamp=int(datetime.now().timestamp() * 1000),
            meta={}
        )
        engine.signal_generator.generate_signal = AsyncMock(return_value=mock_signal)
        
        # Мокаем отклонение сигнала
        engine.risk_manager.evaluate_signal_risk = Mock(return_value={
            "approved": False,
            "reason": "Risk too high"
        })
        engine.exchange_client.fetch_balance = AsyncMock(return_value={"USDT": 10000.0})
        
        # Запускаем цикл
        engine.current_state = TradingState.SCANNING
        engine.last_scan_time = None
        
        await engine._execute_state_cycle()
        assert engine.current_state == TradingState.LEVEL_BUILDING
        
        await engine._execute_state_cycle()
        assert engine.current_state == TradingState.SIGNAL_WAIT
        
        await engine._execute_state_cycle()
        assert engine.current_state == TradingState.SIZING
        
        await engine._execute_state_cycle()
        assert engine.current_state == TradingState.SCANNING  # Возврат к сканированию
        assert len(engine.current_positions) == 0
    
    @pytest.mark.asyncio
    async def test_full_trading_cycle_kill_switch(self, engine):
        """Kill switch срабатывает при превышении лимита убытков."""

        engine.session_start_equity = engine.system_config.paper_starting_balance
        engine.preset.risk.kill_switch_loss_limit = 0.05
        engine.daily_pnl = -engine.session_start_equity * 0.06

        result = await engine._check_kill_switch()

        assert result is True
        assert engine.kill_switch_active is True
        assert "Limit" in engine.kill_switch_reason or engine.kill_switch_reason
    
    @pytest.mark.asyncio
    async def test_full_trading_cycle_position_management(self, engine, mock_market_data):
        """Тест полного цикла торговли - управление позициями."""
        # Создаем открытые позиции (3 позиции для max_concurrent_positions = 3)
        positions = []
        for i in range(3):
            position = Position(
                id=f"pos_{i+1}",
                symbol=f"BTC/USDT" if i == 0 else f"ETH/USDT" if i == 1 else "ADA/USDT",
                side="long",
                strategy="momentum",
                qty=1.0,
                entry=100.0 + i * 10,
                sl=99.0 + i * 10,
                status="open",
                timestamps={"opened_at": int(datetime.now().timestamp() * 1000)}
            )
            positions.append(position)
        engine.current_positions = positions
        
        # Настраиваем моки
        engine.market_data_provider.get_multiple_market_data = AsyncMock(
            return_value={"BTC/USDT": mock_market_data}
        )
        engine.market_data_provider.get_market_data = AsyncMock(return_value=mock_market_data)
        engine.position_manager.process_position_updates = AsyncMock(return_value=[])
        engine.exchange_client.fetch_balance = AsyncMock(return_value={"USDT": 10000.0})
        engine.risk_manager.check_risk_limits = Mock(return_value={
            "kill_switch_triggered": False,
            "overall_status": "SAFE"
        })
        
        # Запускаем цикл управления позициями
        engine.current_state = TradingState.MANAGING
        
        await engine._execute_state_cycle()
        
        # Должен остаться в состоянии управления или перейти к сканированию
        # (в зависимости от количества позиций и свободных слотов)
        assert engine.current_state in [TradingState.MANAGING, TradingState.SCANNING]
    
    @pytest.mark.asyncio
    async def test_full_trading_cycle_error_handling(self, engine):
        """Тест полного цикла торговли - обработка ошибок."""
        # Мокаем ошибку в сканировании
        engine.exchange_client.fetch_markets = AsyncMock(side_effect=Exception("Network error"))
        
        # Запускаем цикл
        engine.current_state = TradingState.SCANNING
        engine.last_scan_time = None
        
        await engine._execute_state_cycle()
        
        # Должен обработать ошибку и перейти в ERROR
        assert engine.current_state == TradingState.ERROR
        assert "Network error" in engine.last_error
    
    @pytest.mark.asyncio
    async def test_system_start_stop(self, engine):
        """Тест запуска и остановки системы."""
        # Мокаем основной цикл
        engine._execute_state_cycle = AsyncMock()
        engine.exchange_client.close = AsyncMock()
        
        # Тестируем запуск
        engine.running = True
        engine.current_state = TradingState.SCANNING
        
        # Тестируем остановку
        await engine.stop()
        
        assert engine.running is False
        engine.exchange_client.close.assert_called_once()
    
    def test_system_status_reporting(self, engine, mock_scan_result):
        """Тест отчетности о состоянии системы."""
        # Настраиваем состояние системы
        engine.current_state = TradingState.SCANNING
        engine.cycle_count = 100
        engine.last_scan_time = datetime.now()
        engine.scan_results = [mock_scan_result]
        engine.active_signals = []
        
        # Создаем позицию
        position = Position(
            id="pos_123",
            symbol="BTC/USDT",
            side="long",
            strategy="momentum",
            qty=1.0,
            entry=100.0,
            sl=99.0,
            status="open"
        )
        engine.current_positions = [position]
        
        # Мокаем компоненты
        engine.risk_manager.get_risk_summary = Mock(return_value={"total_equity": 10000.0})
        engine.position_manager.calculate_position_metrics = Mock(return_value={"win_rate": 0.6})
        
        # Получаем статус
        status = engine.get_system_status()
        
        # Проверяем основные поля
        assert status["state"] == "scanning"
        assert status["cycle_count"] == 100
        assert status["scan_results_count"] == 1
        assert status["active_signals_count"] == 0
        assert status["open_positions_count"] == 1
        assert "risk_summary" in status
        assert "position_metrics" in status
        assert status["preset_name"] == "integration_test"
        assert status["trading_mode"] == "paper"
    
    def test_performance_metrics_calculation(self, engine):
        """Тест расчета метрик производительности."""
        # Создаем позиции
        closed_position = Position(
            id="pos_1",
            symbol="BTC/USDT",
            side="long",
            strategy="momentum",
            qty=1.0,
            entry=100.0,
            sl=99.0,
            status="closed",
            pnl_r=1.5
        )
        engine.current_positions = [closed_position]
        engine.closed_positions = [closed_position]  # Добавляем в closed_positions для total_trades
        
        # Мокаем расчет метрик
        engine.position_manager.calculate_position_metrics = Mock(return_value={
            "win_rate": 0.6,
            "avg_r": 1.2,
            "sharpe_ratio": 1.5,
            "max_drawdown_r": 0.8,
            "profit_factor": 1.8,
            "consecutive_wins": 3,
            "consecutive_losses": 1
        })
        
        # Получаем метрики
        metrics = engine.get_performance_metrics()
        
        # Проверяем основные метрики
        assert metrics["total_trades"] == 1
        assert metrics["win_rate"] == 0.6
        assert metrics["avg_r"] == 1.2
        assert metrics["sharpe_ratio"] == 1.5
        assert metrics["max_drawdown_r"] == 0.8
        assert metrics["profit_factor"] == 1.8
        assert metrics["consecutive_wins"] == 3
        assert metrics["consecutive_losses"] == 1
    
    def test_position_management_integration(self, engine):
        """Тест интеграции управления позициями."""
        # Создаем позиции
        open_position = Position(
            id="pos_1",
            symbol="BTC/USDT",
            side="long",
            strategy="momentum",
            qty=1.0,
            entry=100.0,
            sl=99.0,
            status="open"
        )
        closed_position = Position(
            id="pos_2",
            symbol="ETH/USDT",
            side="short",
            strategy="retest",
            qty=2.0,
            entry=2000.0,
            sl=2100.0,
            status="closed"
        )
        engine.current_positions = [open_position, closed_position]
        
        # Тестируем получение позиций
        all_positions = engine.get_positions()
        assert len(all_positions) == 2
        
        # Фильтруем только открытые позиции
        open_positions = [pos for pos in all_positions if pos.status == "open"]
        assert len(open_positions) == 1
        assert open_positions[0].id == "pos_1"
        
        # Тестируем получение конкретной позиции
        found_position = engine.get_position("pos_1")
        assert found_position == open_position
        
        not_found = engine.get_position("pos_999")
        assert not_found is None
    
    @pytest.mark.asyncio
    async def test_market_data_flow(self, engine, mock_market_data):
        """Тест потока рыночных данных через систему."""
        # Настраиваем моки
        engine.exchange_client.fetch_markets = AsyncMock(return_value=["BTC/USDT"])
        engine.market_data_provider.get_multiple_market_data = AsyncMock(
            return_value={"BTC/USDT": mock_market_data}
        )
        engine.scanner.scan_markets = AsyncMock(return_value=[])
        
        # Запускаем сканирование
        engine.current_state = TradingState.SCANNING
        engine.last_scan_time = None
        
        await engine._execute_state_cycle()
        
        # Проверяем, что данные прошли через систему
        engine.exchange_client.fetch_markets.assert_called_once()
        engine.market_data_provider.get_multiple_market_data.assert_called_once()
        engine.scanner.scan_markets.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_signal_generation_integration(self, engine, mock_scan_result):
        """Тест интеграции генерации сигналов."""
        # Настраиваем моки
        engine.scanner.scan_markets = AsyncMock(return_value=[mock_scan_result])
        engine.signal_generator.generate_signal = AsyncMock(return_value=None)
        
        # Запускаем цикл
        engine.current_state = TradingState.SIGNAL_WAIT
        engine.scan_results = [mock_scan_result]
        
        await engine._execute_state_cycle()
        
        # Проверяем, что генератор сигналов был вызван
        engine.signal_generator.generate_signal.assert_called_once_with(mock_scan_result)
    
    @pytest.mark.asyncio
    async def test_risk_management_integration(self, engine, mock_scan_result, mock_market_data):
        """Тест интеграции управления рисками."""
        # Создаем сигнал
        mock_signal = Signal(
            symbol="BTC/USDT",
            side="long",
            strategy="momentum",
            reason="Integration test signal",
            entry=100.1,
            level=100.0,
            sl=99.0,
            confidence=0.8,
            timestamp=int(datetime.now().timestamp() * 1000),
            meta={"position_size": Mock(), "risk_evaluation": {"approved": True}}
        )
        
        # Настраиваем моки
        engine.signal_generator.generate_signal = AsyncMock(return_value=mock_signal)
        engine.market_data_cache = {"BTC/USDT": mock_market_data}
        engine.exchange_client.fetch_balance = AsyncMock(return_value={"USDT": 10000.0})
        position_size = PositionSize(
            quantity=1.0,
            notional_usd=100.0,
            risk_usd=2.0,
            risk_r=0.02,
            stop_distance=1.1,
            is_valid=True,
            reason="Signal approved",
            precision_adjusted=False,
        )

        engine.risk_manager.evaluate_signal_risk = Mock(return_value={
            "approved": True,
            "position_size": position_size,
            "reason": "Signal approved"
        })
        
        # Запускаем цикл
        engine.current_state = TradingState.SIZING
        engine.current_signals = [mock_signal]
        
        await engine._execute_state_cycle()
        
        # Проверяем, что оценка рисков была вызвана
        engine.risk_manager.evaluate_signal_risk.assert_called_once()
    
    def test_error_recovery_mechanisms(self, engine):
        """Тест механизмов восстановления после ошибок."""
        # Тестируем обработку ошибок в цикле состояний
        engine._handle_scanning_state = AsyncMock(side_effect=Exception("Test error"))
        engine.current_state = TradingState.SCANNING
        
        # Запускаем цикл с ошибкой
        asyncio.run(engine._execute_state_cycle())
        
        # Должен перейти в аварийное состояние
        assert engine.current_state == TradingState.EMERGENCY
        assert "Test error" in engine.emergency_reason
    
    def test_system_initialization(self, engine, mock_preset, mock_system_config):
        """Тест инициализации системы."""
        # Проверяем, что все компоненты инициализированы
        assert engine.preset == mock_preset
        assert engine.system_config.trading_mode == mock_system_config.trading_mode
        assert engine.system_config.exchange == mock_system_config.exchange
        assert engine.current_state == TradingState.INITIALIZING
        assert engine.running is False
        assert engine.cycle_count == 0
        assert len(engine.current_positions) == 0
        assert len(engine.scan_results) == 0
        assert len(engine.active_signals) == 0
        
        # Проверяем, что все компоненты созданы
        assert engine.exchange_client is not None
        assert engine.market_data_provider is not None
        assert engine.scanner is not None
        assert engine.signal_generator is not None
        assert engine.risk_manager is not None
        assert engine.position_manager is not None
