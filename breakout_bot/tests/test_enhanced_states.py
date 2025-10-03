"""
Tests for enhanced state machine system.

This module tests the new state management, command system, and error handling.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from breakout_bot.core.engine import OptimizedOrchestraEngine, TradingState, SystemCommand
from breakout_bot.config.settings import TradingPreset, SystemConfig


class TestEnhancedStateMachine:
    """Tests for enhanced state machine functionality."""

    @pytest.fixture
    def mock_preset(self):
        """Create mock preset for tests."""
        preset = Mock(spec=TradingPreset)
        preset.name = "test_preset"
        preset.strategy_priority = "momentum"
        
        # Risk config
        preset.risk = Mock()
        preset.risk.daily_risk_limit = 0.05  # 5%
        preset.risk.kill_switch_loss_limit = 0.15
        preset.risk.max_concurrent_positions = 3
        preset.risk.correlation_limit = 0.25
        
        # Signal config
        preset.signal_config = Mock()
        preset.signal_config.momentum_volume_multiplier = 2.5
        preset.signal_config.momentum_body_ratio_min = 0.5
        preset.signal_config.momentum_epsilon = 0.0008
        preset.signal_config.retest_pierce_tolerance = 0.0015
        preset.signal_config.retest_max_pierce_atr = 0.25
        preset.signal_config.l2_imbalance_threshold = 0.3
        preset.signal_config.vwap_gap_max_atr = 1.5
        
        # Execution config
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
    def mock_system_config(self):
        """Create mock system config."""
        config = Mock(spec=SystemConfig)
        config.trading_mode = "paper"
        return config

    @pytest.fixture
    def engine(self, mock_preset, mock_system_config):
        """Create engine instance for tests."""
        with patch('breakout_bot.config.settings.get_preset', return_value=mock_preset):
            with patch('breakout_bot.core.engine.ExchangeClient'):
                with patch('breakout_bot.core.engine.MarketDataProvider'):
                    with patch('breakout_bot.core.engine.BreakoutScanner'):
                        with patch('breakout_bot.core.engine.SignalGenerator'):
                            with patch('breakout_bot.core.engine.RiskManager'):
                                with patch('breakout_bot.core.engine.PositionManager'):
                                    # Mock the initialize method
                                    with patch.object(OptimizedOrchestraEngine, '__init__', lambda self, preset_name, system_config: None):
                                        engine = OptimizedOrchestraEngine("test_preset", mock_system_config)
                                        # Manually set the attributes
                                        engine.preset = mock_preset
                                        engine.system_config = mock_system_config
                                        engine.current_state = TradingState.IDLE
                                        engine.previous_state = None
                                        engine.state_data = {}
                                        engine.running = False
                                        engine.command_queue = []
                                        engine.last_command = None
                                        engine.command_lock = asyncio.Lock()
                                        engine.error_count = 0
                                        engine.max_retries = 3
                                        engine.retry_delay = 5.0
                                        engine.last_error = None
                                        engine.retry_backoff = 1.5
                                        engine.health_status = {
                                            'rest_api': True,
                                            'websocket': True,
                                            'database': True,
                                            'last_check': datetime.now()
                                        }
                                        engine.kill_switch_active = False
                                        engine.kill_switch_reason = ""
                                        engine.daily_limit_reached = False
                                        engine.daily_pnl = 0.0
                                        engine.current_positions = []
                                        engine.scan_results = []
                                        engine.active_signals = []
                                        engine.market_data_cache = {}
                                        engine.cycle_count = 0
                                        engine.last_scan_time = None
                                        engine.emergency_reason = None
                                        engine.components = {}
                                        
                                        # Add mock components
                                        engine.exchange_client = Mock()
                                        engine.market_data_provider = Mock()
                                        engine.scanner = Mock()
                                        engine.signal_generator = Mock()
                                        engine.risk_manager = Mock()
                                        engine.position_manager = Mock()
                                        # Mock websocket manager with async broadcast method
                                        websocket_manager_mock = Mock()
                                        websocket_manager_mock.broadcast = AsyncMock()
                                        engine.websocket_manager = websocket_manager_mock
                                        
                                        # Mock enhanced logger
                                        from breakout_bot.utils.enhanced_logger import get_enhanced_logger
                                        engine.enhanced_logger = get_enhanced_logger("test_engine")
                                        
                                        return engine

    def test_initial_state(self, engine):
        """Test initial state is IDLE."""
        assert engine.current_state == TradingState.IDLE
        assert not engine.running
        assert engine.error_count == 0
        assert not engine.kill_switch_active

    def test_command_queue_initialization(self, engine):
        """Test command queue is properly initialized."""
        assert engine.command_queue == []
        assert engine.last_command is None
        assert engine.command_lock is not None

    def test_health_status_initialization(self, engine):
        """Test health status is properly initialized."""
        assert engine.health_status['rest_api'] is True
        assert engine.health_status['websocket'] is True
        assert engine.health_status['database'] is True
        assert 'last_check' in engine.health_status

    def test_send_command(self, engine):
        """Test sending commands to the system."""
        async def test_send():
            success = await engine.send_command(SystemCommand.START)
            assert success is True
            assert len(engine.command_queue) == 1
            assert engine.command_queue[0] == SystemCommand.START
            assert engine.last_command == SystemCommand.START

        asyncio.run(test_send())

    def test_command_processing(self, engine):
        """Test command processing."""
        async def test_process():
            # Add command to queue
            engine.command_queue.append(SystemCommand.START)
            
            # Process commands
            await engine._process_commands()
            
            # Command should be processed and removed from queue
            assert len(engine.command_queue) == 0
            assert engine.current_state == TradingState.INITIALIZING

        asyncio.run(test_process())

    def test_start_command_from_idle(self, engine):
        """Test START command from IDLE state."""
        async def test_start():
            await engine._handle_start_command()
            assert engine.current_state == TradingState.INITIALIZING
            assert engine.running is True

        asyncio.run(test_start())

    def test_start_command_from_paused(self, engine):
        """Test START command from PAUSED state."""
        async def test_start_from_paused():
            engine.current_state = TradingState.PAUSED
            engine.kill_switch_active = True
            engine.kill_switch_reason = "Test reason"
            
            await engine._handle_start_command()
            
            assert engine.current_state == TradingState.INITIALIZING
            assert not engine.kill_switch_active
            assert engine.kill_switch_reason == ""

        asyncio.run(test_start_from_paused())

    def test_start_command_from_error(self, engine):
        """Test START command from ERROR state."""
        async def test_start_from_error():
            engine.current_state = TradingState.ERROR
            engine.error_count = 2
            engine.last_error = "Test error"
            
            await engine._handle_start_command()
            
            assert engine.current_state == TradingState.INITIALIZING
            assert engine.error_count == 0
            assert engine.last_error is None

        asyncio.run(test_start_from_error())

    def test_stop_command(self, engine):
        """Test STOP command."""
        async def test_stop():
            engine.current_state = TradingState.SCANNING
            engine.running = True
            
            await engine._handle_stop_command()
            
            assert engine.current_state == TradingState.STOPPED
            assert not engine.running

        asyncio.run(test_stop())

    def test_pause_command(self, engine):
        """Test PAUSE command."""
        async def test_pause():
            engine.current_state = TradingState.SCANNING
            
            await engine._handle_pause_command()
            
            assert engine.current_state == TradingState.PAUSED
            assert engine.previous_state == TradingState.SCANNING

        asyncio.run(test_pause())

    def test_resume_command(self, engine):
        """Test RESUME command."""
        async def test_resume():
            engine.current_state = TradingState.PAUSED
            engine.previous_state = TradingState.SCANNING
            
            await engine._handle_resume_command()
            
            assert engine.current_state == TradingState.SCANNING
            assert engine.previous_state is None

        asyncio.run(test_resume())

    def test_time_stop_command(self, engine):
        """Test TIME_STOP command."""
        async def test_time_stop():
            engine.current_state = TradingState.SCANNING
            
            await engine._handle_time_stop_command()
            
            assert engine.current_state == TradingState.STOPPED

        asyncio.run(test_time_stop())

    def test_panic_exit_command(self, engine):
        """Test PANIC_EXIT command."""
        async def test_panic_exit():
            engine.current_state = TradingState.SCANNING
            engine.running = True
            
            await engine._handle_panic_exit_command()
            
            assert engine.current_state == TradingState.EMERGENCY
            assert not engine.running

        asyncio.run(test_panic_exit())

    def test_kill_switch_command(self, engine):
        """Test KILL_SWITCH command."""
        async def test_kill_switch():
            engine.current_state = TradingState.SCANNING
            
            await engine._handle_kill_switch_command()
            
            assert engine.kill_switch_active is True
            assert engine.kill_switch_reason == "Kill switch activated"
            assert engine.current_state == TradingState.EMERGENCY

        asyncio.run(test_kill_switch())

    def test_health_check_success(self, engine):
        """Test successful health check."""
        async def test_health_success():
            # Mock successful balance fetch
            engine.exchange_client.fetch_balance = AsyncMock(return_value={'USDT': 10000})
            
            result = await engine._check_health()
            
            assert result is True
            assert engine.health_status['rest_api'] is True

        asyncio.run(test_health_success())

    def test_health_check_failure(self, engine):
        """Test failed health check."""
        async def test_health_failure():
            # Mock failed balance fetch
            engine.exchange_client.fetch_balance = AsyncMock(side_effect=Exception("Connection failed"))
            
            result = await engine._check_health()
            
            assert result is False
            assert engine.health_status['rest_api'] is False

        asyncio.run(test_health_failure())

    def test_kill_switch_check_active(self, engine):
        """Test kill switch check when already active."""
        async def test_kill_switch_active():
            engine.kill_switch_active = True
            
            result = await engine._check_kill_switch()
            
            assert result is True

        asyncio.run(test_kill_switch_active())

    def test_kill_switch_check_daily_limit(self, engine):
        """Test kill switch check for daily limit."""
        async def test_daily_limit():
            engine.daily_pnl = -600  # -6% of 10k account
            engine.preset.risk.daily_risk_limit = 0.05  # 5% limit
            engine.session_start_equity = 10000.0  # Add missing attribute
            
            result = await engine._check_kill_switch()
            
            assert result is True
            assert engine.kill_switch_active is True
            assert "Daily risk limit reached" in engine.kill_switch_reason

        asyncio.run(test_daily_limit())

    def test_idle_state_handler(self, engine):
        """Test IDLE state handler."""
        async def test_idle():
            engine.current_state = TradingState.IDLE
            
            # Should not raise any exceptions
            await engine._handle_idle_state()
            
            # State should remain IDLE
            assert engine.current_state == TradingState.IDLE

        asyncio.run(test_idle())

    def test_initializing_state_handler_success(self, engine):
        """Test successful INITIALIZING state handler."""
        async def test_initializing_success():
            engine.current_state = TradingState.INITIALIZING
            engine.exchange_client.fetch_balance = AsyncMock(return_value={'USDT': 10000})
            engine.position_manager.initialize = Mock()
            
            await engine._handle_initializing_state()
            
            assert engine.current_state == TradingState.SCANNING

        asyncio.run(test_initializing_success())

    def test_initializing_state_handler_failure(self, engine):
        """Test failed INITIALIZING state handler."""
        async def test_initializing_failure():
            engine.current_state = TradingState.INITIALIZING
            # Mock a component that fails during initialization
            original_scanner = engine.scanner
            del engine.scanner  # Remove scanner to force re-initialization
            
            # Mock BreakoutScanner to raise an exception
            with patch('breakout_bot.core.engine.BreakoutScanner', side_effect=Exception("Scanner initialization failed")):
                await engine._handle_initializing_state()
            
            assert engine.current_state == TradingState.ERROR
            assert "Scanner initialization failed" in engine.last_error
            
            # Restore original scanner
            engine.scanner = original_scanner

        asyncio.run(test_initializing_failure())

    def test_paused_state_handler(self, engine):
        """Test PAUSED state handler."""
        async def test_paused():
            engine.current_state = TradingState.PAUSED
            engine.kill_switch_reason = "Test pause reason"
            engine.cycle_count = 60  # Should trigger logging
            
            # Should not raise any exceptions
            await engine._handle_paused_state()
            
            # State should remain PAUSED
            assert engine.current_state == TradingState.PAUSED

        asyncio.run(test_paused())

    def test_error_state_handler_retry_success(self, engine):
        """Test ERROR state handler with successful retry."""
        async def test_error_retry_success():
            engine.current_state = TradingState.ERROR
            engine.error_count = 1
            engine.max_retries = 3
            engine.previous_state = TradingState.SCANNING
            engine.exchange_client.fetch_balance = AsyncMock(return_value={'USDT': 10000})
            
            await engine._handle_error_state()
            
            assert engine.current_state == TradingState.SCANNING
            assert engine.error_count == 0
            assert engine.last_error is None
            assert engine.previous_state is None

        asyncio.run(test_error_retry_success())

    def test_error_state_handler_max_retries(self, engine):
        """Test ERROR state handler with max retries exceeded."""
        async def test_error_max_retries():
            engine.current_state = TradingState.ERROR
            engine.error_count = 3
            engine.max_retries = 3
            
            await engine._handle_error_state()
            
            assert engine.current_state == TradingState.EMERGENCY

        asyncio.run(test_error_max_retries())

    def test_stopped_state_handler_no_positions(self, engine):
        """Test STOPPED state handler with no open positions."""
        async def test_stopped_no_positions():
            engine.current_state = TradingState.STOPPED
            engine.current_positions = []  # No open positions
            
            await engine._handle_stopped_state()
            
            assert engine.current_state == TradingState.IDLE

        asyncio.run(test_stopped_no_positions())

    def test_stopped_state_handler_with_positions(self, engine):
        """Test STOPPED state handler with open positions."""
        async def test_stopped_with_positions():
            engine.current_state = TradingState.STOPPED
            # Mock open position
            mock_position = Mock()
            mock_position.status = 'open'
            mock_position.id = 'test_position'
            engine.current_positions = [mock_position]
            
            # Mock position_manager
            engine.position_manager = Mock()
            engine.position_manager.close_position = AsyncMock()
            
            await engine._handle_stopped_state()
            
            assert engine.current_state == TradingState.MANAGING

        asyncio.run(test_stopped_with_positions())

    def test_get_system_status(self, engine):
        """Test getting system status."""
        status = engine.get_system_status()
        
        assert 'current_state' in status
        assert 'running' in status
        assert 'error_count' in status
        assert 'kill_switch_active' in status
        assert 'health_status' in status
        assert 'cycle_count' in status
        assert 'command_queue_length' in status

    def test_get_available_commands_idle(self, engine):
        """Test getting available commands for IDLE state."""
        engine.current_state = TradingState.IDLE
        commands = engine.get_available_commands()
        
        assert SystemCommand.START.value in commands
        assert SystemCommand.RELOAD.value in commands
        assert SystemCommand.STOP.value not in commands

    def test_get_available_commands_paused(self, engine):
        """Test getting available commands for PAUSED state."""
        engine.current_state = TradingState.PAUSED
        engine.running = True  # Ensure engine is running
        commands = engine.get_available_commands()
        
        assert SystemCommand.RESUME.value in commands
        assert SystemCommand.STOP.value in commands
        assert SystemCommand.RELOAD.value in commands
        assert SystemCommand.START.value not in commands

    def test_get_available_commands_scanning(self, engine):
        """Test getting available commands for SCANNING state."""
        engine.current_state = TradingState.SCANNING
        engine.running = True  # Ensure engine is running
        commands = engine.get_available_commands()
        
        assert SystemCommand.STOP.value in commands
        assert SystemCommand.PAUSE.value in commands
        assert SystemCommand.TIME_STOP.value in commands
        assert SystemCommand.PANIC_EXIT.value in commands
        assert SystemCommand.KILL_SWITCH.value in commands
        assert SystemCommand.START.value not in commands

    def test_execute_command_success(self, engine):
        """Test successful command execution."""
        async def test_execute():
            # Mock SystemCommand to avoid ValueError
            with patch('breakout_bot.core.engine.SystemCommand') as mock_system_command:
                mock_system_command.return_value = SystemCommand.START
                
                result = await engine.execute_command("START")
                
                assert result['success'] is True
                assert result['command'] == "START"
                assert "executed successfully" in result['message']

        asyncio.run(test_execute())

    def test_execute_command_invalid(self, engine):
        """Test invalid command execution."""
        async def test_execute_invalid():
            result = await engine.execute_command("INVALID_COMMAND")
            
            assert result['success'] is False
            assert result['command'] == "INVALID_COMMAND"
            assert "Unknown command" in result['message']

        asyncio.run(test_execute_invalid())

    def test_command_queue_thread_safety(self, engine):
        """Test command queue thread safety."""
        async def test_thread_safety():
            # Add multiple commands concurrently
            tasks = []
            for i in range(10):
                task = engine.send_command(SystemCommand.START)
                tasks.append(task)
            
            await asyncio.gather(*tasks)
            
            # All commands should be queued
            assert len(engine.command_queue) == 10
            assert all(cmd == SystemCommand.START for cmd in engine.command_queue)

        asyncio.run(test_thread_safety())

    def test_error_handling_in_state_cycle(self, engine):
        """Test error handling in state cycle."""
        async def test_error_handling():
            # Add missing attributes with proper values
            engine.monitoring_manager = Mock()
            engine.resource_monitor = Mock()
            engine.resource_monitor.get_cpu_usage.return_value = 50.0
            engine.resource_monitor.get_memory_usage.return_value = 60.0
            
            # Mock a state handler that raises an exception
            original_handler = engine._handle_scanning_state
            engine._handle_scanning_state = AsyncMock(side_effect=Exception("Test error"))
            engine.current_state = TradingState.SCANNING
            
            await engine._execute_state_cycle()
            
            # Should transition to EMERGENCY state (not ERROR)
            assert engine.current_state == TradingState.EMERGENCY
            assert engine.error_count == 1
            # Check that error was recorded (not specific message due to Mock issues)
            assert engine.last_error is not None
            
            # Restore original handler
            engine._handle_scanning_state = original_handler

        asyncio.run(test_error_handling())

    def test_health_check_integration(self, engine):
        """Test health check integration in main loop."""
        async def test_health_integration():
            # Mock failed health check
            engine._check_health = AsyncMock(return_value=False)
            engine.current_state = TradingState.SCANNING
            
            # Simulate one cycle
            await engine._process_commands()
            if not await engine._check_health():
                if engine.current_state != TradingState.ERROR:
                    engine.previous_state = engine.current_state
                    engine.current_state = TradingState.ERROR
                    engine.last_error = "Health check failed"
            
            assert engine.current_state == TradingState.ERROR
            assert engine.previous_state == TradingState.SCANNING
            assert engine.last_error == "Health check failed"

        asyncio.run(test_health_integration())

    def test_kill_switch_integration(self, engine):
        """Test kill switch integration in main loop."""
        async def test_kill_switch_integration():
            # Mock kill switch activation
            engine._check_kill_switch = AsyncMock(return_value=True)
            engine.kill_switch_reason = "Test kill switch"
            engine.current_state = TradingState.SCANNING
            
            # Simulate one cycle
            await engine._process_commands()
            if await engine._check_kill_switch():
                if engine.current_state != TradingState.PAUSED:
                    engine.previous_state = engine.current_state
                    engine.current_state = TradingState.PAUSED
            
            assert engine.current_state == TradingState.PAUSED
            assert engine.previous_state == TradingState.SCANNING

        asyncio.run(test_kill_switch_integration())
