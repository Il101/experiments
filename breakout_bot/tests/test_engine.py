"""
Тесты для OrchestraEngine - основного движка торговой системы.

Покрывает:
- Инициализацию движка
- Переходы между состояниями
- Обработку каждого состояния
- Обработку ошибок
- Метрики и статус системы
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta

from breakout_bot.core.engine import OptimizedOrchestraEngine, TradingState
from breakout_bot.data.models import Position, Signal, ScanResult, MarketData, Candle, L2Depth
from breakout_bot.config.settings import TradingPreset, SystemConfig, load_preset


class TestOrchestraEngine:
    """Тесты для OrchestraEngine."""
    
    @pytest.fixture
    def mock_preset(self):
        """Возвращает реальный пресет breakout_v1 для тестов."""
        return load_preset("breakout_v1").model_copy(deep=True)

    @pytest.fixture
    def mock_system_config(self):
        """Создает мок-системную конфигурацию."""
        return SystemConfig(
            exchange="bybit",
            trading_mode="paper",
            log_level="INFO",
            log_to_file=False,
            database_url="sqlite:///test.db",
            paper_starting_balance=100000.0,
            paper_slippage_bps=5.0,
        )
    
    @pytest.fixture
    def mock_market_data(self):
        """Создает мок-рыночные данные."""
        return MarketData(
            symbol="BTC/USDT",
            price=50000.0,
            volume_24h_usd=1000000.0,
            oi_usd=500000.0,
            oi_change_24h=0.05,
            trades_per_minute=100.0,
            atr_5m=500.0,
            atr_15m=750.0,
            bb_width_pct=2.5,
            btc_correlation=0.7,
            l2_depth=L2Depth(
                bid_usd_0_5pct=10000.0,
                ask_usd_0_5pct=10000.0,
                bid_usd_0_3pct=5000.0,
                ask_usd_0_3pct=5000.0,
                spread_bps=2.0,
                imbalance=0.1
            ),
            candles_5m=[],
            timestamp=int(datetime.now().timestamp() * 1000)
        )
    
    @pytest.fixture
    def mock_scan_result(self):
        """Создает мок-результат сканирования."""
        return ScanResult(
            symbol="BTC/USDT",
            score=0.85,
            rank=1,
            market_data=self.mock_market_data,
            filter_results={
                'min_24h_volume': True,
                'min_oi': True,
                'max_spread': True,
                'min_depth_0_5pct': True,
                'min_depth_0_3pct': True,
                'min_trades_per_minute': True,
                'atr_range': True,
                'bb_width': True,
                'volume_surge_1h': True,
                'volume_surge_5m': True,
                'oi_delta': True,
                'correlation': True
            },
            score_components={
                'vol_surge': 0.3,
                'oi_delta': 0.2,
                'atr_quality': 0.15,
                'correlation': 0.2,
                'trades_per_minute': 0.1
            },
            levels=[],
            timestamp=int(datetime.now().timestamp() * 1000)
        )
    
    @pytest.fixture
    def mock_signal(self):
        """Создает мок-сигнал."""
        return Signal(
            symbol="BTC/USDT",
            side="long",
            strategy="momentum",
            reason="Price breakout with volume surge",
            entry=51000.0,
            level=50000.0,
            sl=49000.0,
            confidence=0.8,
            timestamp=int(datetime.now().timestamp() * 1000),
            meta={
                'scan_score': 0.85,
                'btc_correlation': 0.7,
                'volume_surge': 2.5,
                'atr_quality': 0.8
            }
        )
    
    @pytest.fixture
    def mock_position(self):
        """Создает мок-позицию."""
        return Position(
            id="pos_123",
            symbol="BTC/USDT",
            side="long",
            strategy="momentum",
            qty=0.1,
            entry=51000.0,
            sl=49000.0,
            tp=53000.0,
            status="open",
            timestamps={'opened_at': int(datetime.now().timestamp() * 1000)},
            meta={
                'signal_id': 'signal_123',
                'btc_correlation': 0.7,
                'scan_score': 0.85,
                'position_size_usd': 5100.0,
                'risk_usd': 100.0
            }
        )
    
    @pytest.fixture
    def engine(self, mock_preset, mock_system_config):
        """Создает экземпляр OrchestraEngine для тестирования."""
        with patch('breakout_bot.config.settings.get_preset', return_value=mock_preset):
            with patch('breakout_bot.config.settings.SystemConfig.from_env', return_value=mock_system_config):
                with patch('breakout_bot.core.engine.ExchangeClient') as mock_exchange:
                    with patch('breakout_bot.core.engine.MarketDataProvider') as mock_market_data:
                        with patch('breakout_bot.core.engine.BreakoutScanner') as mock_scanner:
                            with patch('breakout_bot.core.engine.SignalGenerator') as mock_signal_gen:
                                with patch('breakout_bot.core.engine.RiskManager') as mock_risk:
                                    with patch('breakout_bot.core.engine.PositionManager') as mock_position:
                                        # Настройка моков
                                        mock_exchange.return_value = Mock()
                                        mock_market_data.return_value = Mock()
                                        mock_scanner.return_value = Mock()
                                        mock_signal_gen.return_value = Mock()
                                        mock_risk.return_value = Mock()
                                        mock_position.return_value = Mock()
                                        
                                        return OptimizedOrchestraEngine("breakout_v1_working")
    
    def test_initialization(self, engine):
        """Тест инициализации движка."""
        assert engine.preset.name == "breakout_v1_working"
        assert engine.current_state == TradingState.INITIALIZING
        assert engine.running is False
        assert engine.cycle_count == 0
        assert engine.emergency_reason is None
        assert len(engine.current_positions) == 0
        assert len(engine.scan_results) == 0
        assert len(engine.active_signals) == 0
    
    def test_start_stop(self, engine):
        """Тест запуска и остановки движка."""
        # Мок для основного цикла и health check
        with patch.object(engine, '_execute_state_cycle', new_callable=AsyncMock) as mock_cycle, \
             patch.object(engine, '_check_health', new_callable=AsyncMock) as mock_health, \
             patch.object(engine, '_check_kill_switch', new_callable=AsyncMock) as mock_kill_switch:
            
            mock_cycle.side_effect = [None, KeyboardInterrupt()]
            mock_health.return_value = True
            mock_kill_switch.return_value = False
            
            # Тест запуска
            asyncio.run(engine.start())
            
            assert engine.running is False
            assert engine.current_state == TradingState.STOPPED
    
    def test_scanning_state_no_scan_time(self, engine):
        """Тест состояния сканирования - не время сканировать."""
        # Инициализируем компоненты
        asyncio.run(engine.initialize())
        
        engine.current_state = TradingState.SCANNING
        engine.last_scan_time = datetime.now()
        
        with patch.object(engine, 'trading_orchestrator') as mock_orchestrator:
            mock_orchestrator.start_trading_cycle = AsyncMock()
            asyncio.run(engine._execute_state_cycle())
            mock_orchestrator.start_trading_cycle.assert_called_once()
    
    def test_scanning_state_with_scan(self, engine):
        """Тест состояния сканирования - время сканировать."""
        # Инициализируем компоненты
        asyncio.run(engine.initialize())
        
        engine.current_state = TradingState.SCANNING
        engine.last_scan_time = None
        
        with patch.object(engine, 'trading_orchestrator') as mock_orchestrator:
            mock_orchestrator.start_trading_cycle = AsyncMock()
            asyncio.run(engine._execute_state_cycle())
            mock_orchestrator.start_trading_cycle.assert_called_once()
    
    def test_scanning_state_no_candidates(self, engine):
        """Тест состояния сканирования - нет кандидатов."""
        # Инициализируем компоненты
        asyncio.run(engine.initialize())
        
        engine.current_state = TradingState.SCANNING
        engine.scan_results = []
        
        with patch.object(engine, 'trading_orchestrator') as mock_orchestrator:
            mock_orchestrator.start_trading_cycle = AsyncMock()
            asyncio.run(engine._execute_state_cycle())
            mock_orchestrator.start_trading_cycle.assert_called_once()
    
    def test_level_building_state_with_valid_levels(self, engine):
        """Тест состояния построения уровней - есть валидные уровни."""
        # Инициализируем компоненты
        asyncio.run(engine.initialize())
        
        engine.current_state = TradingState.LEVEL_BUILDING
        engine.scan_results = [self.mock_scan_result]
        
        with patch.object(engine, 'trading_orchestrator') as mock_orchestrator:
            mock_orchestrator.start_trading_cycle = AsyncMock()
            asyncio.run(engine._execute_state_cycle())
            mock_orchestrator.start_trading_cycle.assert_called_once()
    
    def test_level_building_state_no_valid_levels(self, engine):
        """Тест состояния построения уровней - нет валидных уровней."""
        # Инициализируем компоненты
        asyncio.run(engine.initialize())
        
        engine.current_state = TradingState.LEVEL_BUILDING
        engine.scan_results = []
        
        with patch.object(engine.trading_orchestrator, '_execute_level_building_cycle', new_callable=AsyncMock) as mock_level:
            asyncio.run(engine._execute_state_cycle())
            mock_level.assert_called_once()
    
    def test_signal_wait_state_with_signals(self, engine):
        """Тест состояния ожидания сигналов - есть сигналы."""
        # Инициализируем компоненты
        asyncio.run(engine.initialize())
        
        engine.current_state = TradingState.SIGNAL_WAIT
        engine.scan_results = [self.mock_scan_result]
        engine.signal_generator.generate_signals.return_value = [self.mock_signal]
        
        with patch.object(engine, '_handle_signal_wait_state', new_callable=AsyncMock) as mock_signal:
            asyncio.run(engine._execute_state_cycle())
            mock_signal.assert_called_once()
    
    def test_signal_wait_state_no_signals(self, engine):
        """Тест состояния ожидания сигналов - нет сигналов."""
        # Инициализируем компоненты
        asyncio.run(engine.initialize())
        
        engine.current_state = TradingState.SIGNAL_WAIT
        engine.scan_results = [self.mock_scan_result]
        engine.signal_generator.generate_signals.return_value = []
        
        with patch.object(engine, '_handle_signal_wait_state', new_callable=AsyncMock) as mock_signal:
            asyncio.run(engine._execute_state_cycle())
            mock_signal.assert_called_once()
    
    def test_sizing_state_approved_signals(self, engine):
        """Тест состояния расчета размера - одобренные сигналы."""
        # Инициализируем компоненты
        asyncio.run(engine.initialize())
        
        engine.current_state = TradingState.SIZING
        engine.active_signals = [self.mock_signal]
        engine.risk_manager.evaluate_signal_risk.return_value = {
            'approved': True,
            'position_size': Mock(quantity=0.1, notional_usd=5100.0, risk_usd=100.0),
            'reason': 'Approved'
        }
        
        with patch.object(engine, '_handle_sizing_state', new_callable=AsyncMock) as mock_sizing:
            asyncio.run(engine._execute_state_cycle())
            mock_sizing.assert_called_once()
    
    def test_sizing_state_rejected_signals(self, engine):
        """Тест состояния расчета размера - отклоненные сигналы."""
        # Инициализируем компоненты
        asyncio.run(engine.initialize())
        
        engine.current_state = TradingState.SIZING
        engine.active_signals = [self.mock_signal]
        engine.risk_manager.evaluate_signal_risk.return_value = {
            'approved': False,
            'reason': 'Risk too high'
        }
        
        with patch.object(engine, '_handle_sizing_state', new_callable=AsyncMock) as mock_sizing:
            asyncio.run(engine._execute_state_cycle())
            mock_sizing.assert_called_once()
    
    def test_execution_state_success(self, engine):
        """Тест состояния исполнения - успех."""
        # Инициализируем компоненты
        asyncio.run(engine.initialize())
        
        engine.current_state = TradingState.EXECUTION
        engine.active_signals = [self.mock_signal]
        engine.exchange_client.create_order.return_value = Mock(id="order_123")
        
        with patch.object(engine, '_handle_execution_state', new_callable=AsyncMock) as mock_exec:
            asyncio.run(engine._execute_state_cycle())
            mock_exec.assert_called_once()
    
    def test_execution_state_failure(self, engine):
        """Тест состояния исполнения - ошибка."""
        # Инициализируем компоненты
        asyncio.run(engine.initialize())
        
        engine.current_state = TradingState.EXECUTION
        engine.active_signals = [self.mock_signal]
        engine.exchange_client.create_order.side_effect = Exception("Order failed")
        
        with patch.object(engine, '_handle_execution_state', new_callable=AsyncMock) as mock_exec:
            asyncio.run(engine._execute_state_cycle())
            mock_exec.assert_called_once()
    
    def test_managing_state_with_positions(self, engine):
        """Тест состояния управления - есть позиции."""
        # Инициализируем компоненты
        asyncio.run(engine.initialize())
        
        engine.current_state = TradingState.MANAGING
        engine.current_positions = [self.mock_position]
        engine.risk_manager.check_risk_limits.return_value = {
            'kill_switch_triggered': False
        }
        
        with patch.object(engine, '_handle_managing_state', new_callable=AsyncMock) as mock_manage:
            asyncio.run(engine._execute_state_cycle())
            mock_manage.assert_called_once()
    
    def test_managing_state_kill_switch(self, engine):
        """Тест состояния управления - сработал kill switch."""
        # Инициализируем компоненты
        asyncio.run(engine.initialize())
        
        engine.current_state = TradingState.MANAGING
        engine.current_positions = [self.mock_position]
        engine.risk_manager.check_risk_limits.return_value = {
            'kill_switch_triggered': True
        }
        
        with patch.object(engine, '_handle_managing_state', new_callable=AsyncMock) as mock_manage:
            asyncio.run(engine._execute_state_cycle())
            mock_manage.assert_called_once()
    
    def test_managing_state_no_positions(self, engine):
        """Тест состояния управления - нет позиций."""
        # Инициализируем компоненты
        asyncio.run(engine.initialize())
        
        engine.current_state = TradingState.MANAGING
        engine.current_positions = []
        
        with patch.object(engine, '_handle_managing_state', new_callable=AsyncMock) as mock_manage:
            asyncio.run(engine._execute_state_cycle())
            mock_manage.assert_called_once()
    
    def test_emergency_state(self, engine):
        """Тест аварийного состояния."""
        # Инициализируем компоненты
        asyncio.run(engine.initialize())
        
        engine.current_state = TradingState.EMERGENCY
        engine.emergency_reason = "Test emergency"
        engine.current_positions = [self.mock_position]
        
        with patch.object(engine, '_handle_emergency_state', new_callable=AsyncMock) as mock_emergency:
            asyncio.run(engine._execute_state_cycle())
            mock_emergency.assert_called_once()
    
    def test_get_system_status(self, engine):
        """Тест получения статуса системы."""
        engine.current_positions = [self.mock_position]
        engine.scan_results = [self.mock_scan_result]
        engine.active_signals = [self.mock_signal]
        engine.cycle_count = 10
        engine.last_scan_time = datetime.now()
        
        status = engine.get_system_status()
        
        assert status['state'] == TradingState.INITIALIZING.value
        assert status['cycle_count'] == 10
        assert status['open_positions_count'] == 1
        assert status['scan_results_count'] == 1
        assert status['active_signals_count'] == 1
        assert status['preset_name'] == "breakout_v1"
        assert status['trading_mode'] == "paper"
    
    def test_get_positions(self, engine):
        """Тест получения позиций."""
        engine.current_positions = [self.mock_position]
        
        positions = engine.get_positions()
        assert len(positions) == 1
        assert positions[0].id == "pos_123"
    
    def test_get_position_by_id(self, engine):
        """Тест получения позиции по ID."""
        engine.current_positions = [self.mock_position]
        
        position = engine.get_position("pos_123")
        assert position is not None
        assert position.id == "pos_123"
        
        position = engine.get_position("nonexistent")
        assert position is None
    
    def test_get_performance_metrics(self, engine):
        """Тест получения метрик производительности."""
        engine.current_positions = [self.mock_position]
        engine.position_manager.calculate_position_metrics.return_value = {
            'win_rate': 0.6,
            'avg_r': 1.2,
            'sharpe_ratio': 1.5,
            'max_drawdown_r': 0.8,
            'profit_factor': 1.8,
            'consecutive_wins': 3,
            'consecutive_losses': 1
        }
        
        metrics = engine.get_performance_metrics()
        
        assert metrics['total_trades'] == 0  # Нет закрытых позиций
        assert metrics['win_rate'] == 0.6
        assert metrics['avg_r'] == 1.2
        assert metrics['sharpe_ratio'] == 1.5
    
    def test_state_cycle_error_handling(self, engine):
        """Тест обработки ошибок в цикле состояний."""
        # Инициализируем компоненты
        asyncio.run(engine.initialize())
        
        engine.current_state = TradingState.SCANNING
        
        with patch.object(engine, '_handle_scanning_state', new_callable=AsyncMock) as mock_scan:
            mock_scan.side_effect = Exception("Scan error")
            
            asyncio.run(engine._execute_state_cycle())
            
            assert engine.current_state == TradingState.EMERGENCY
            assert "Scan error" in engine.emergency_reason
    
    def test_emergency_reason_setting(self, engine):
        """Тест установки причины аварии."""
        engine.emergency_reason = "Test emergency"
        assert engine.emergency_reason == "Test emergency"
    
    def test_cycle_count_increment(self, engine):
        """Тест увеличения счетчика циклов."""
        initial_count = engine.cycle_count
        
        with patch.object(engine, '_handle_scanning_state', new_callable=AsyncMock):
            asyncio.run(engine._execute_state_cycle())
        
        assert engine.cycle_count == initial_count + 1
    
    def test_running_flag(self, engine):
        """Тест флага запуска."""
        assert engine.running is False
        
        engine.running = True
        assert engine.running is True
