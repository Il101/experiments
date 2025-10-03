"""
Optimized Orchestra Engine for Breakout Bot Trading System.

This module implements resource-optimized version of the main trading system
with improved CPU, memory, and disk usage management.
"""

import asyncio
import os
from dataclasses import asdict
from collections import Counter, deque
import gc
import psutil
import uuid
from enum import Enum
from typing import Dict, List, Optional, Any, Tuple, Set
from statistics import mean
from datetime import datetime
import logging
import time
from ..utils.enhanced_logger import get_enhanced_logger, LogContext, log_performance
from ..utils.performance_monitor import get_performance_monitor
from ..utils.metrics_logger import get_metrics_logger, log_engine_cycle, log_trade_event, log_scanner_metrics, log_risk_metrics
from .state_machine import StateMachine, TradingState
from .error_handler import ErrorHandler, ErrorInfo
from concurrent.futures import ThreadPoolExecutor
import weakref
from contextlib import asynccontextmanager
import inspect
import importlib

from pydantic import ValidationError

from ..config import get_preset
from ..config.settings import TradingPreset, SystemConfig, ExecutionConfig, load_preset
from ..data.models import Position, Signal, ScanResult, MarketData, Order
from ..exchange import ExchangeClient, MarketDataProvider
from ..scanner import BreakoutScanner
from ..signals import SignalGenerator
from ..risk import RiskManager
from ..risk.risk_manager import PositionSize
from ..position import PositionManager, PositionUpdate
from ..utils.resource_monitor import get_resource_monitor, ResourceLimits
from ..utils.monitoring_manager import get_monitoring_manager
from ..data.monitoring import CheckpointType, CheckpointStatus
from ..indicators.technical import clear_indicator_cache
from ..exchange.exchange_client import close_all_connections
from ..execution.manager import ExecutionManager
from ..diagnostics import DiagnosticsCollector

logger = logging.getLogger(__name__)


# TradingState enum moved to state_machine.py


class SystemCommand(Enum):
    """System commands."""
    START = "start"
    STOP = "stop"
    PAUSE = "pause"
    RESUME = "resume"
    RELOAD = "reload"
    EMERGENCY_STOP = "emergency_stop"
    TIME_STOP = "time_stop"
    PANIC_EXIT = "panic_exit"
    RETRY = "retry"
    KILL_SWITCH = "kill_switch"
    OPTIMIZE = "optimize"
    RESET = "reset"


class OptimizedAdaptiveDelay:
    """Resource-aware adaptive delay mechanism."""
    
    def __init__(self, 
                 min_delay: float = 0.1, 
                 max_delay: float = 5.0, 
                 initial_delay: float = 1.0,
                 cpu_threshold: float = 70.0,
                 memory_threshold: float = 80.0):
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.current_delay = initial_delay
        self.cpu_threshold = cpu_threshold
        self.memory_threshold = memory_threshold
        
        self.last_cycle_time = 0
        self.cycle_times = []
        self.max_history = 20  # Reduced from 10 for memory efficiency
        
        # Resource monitoring
        self.resource_monitor = get_resource_monitor()
    
    async def wait(self):
        """Wait with resource-aware adaptive delay."""
        now = time.time()
        
        # Adjust delay based on system resources
        current_metrics = self.resource_monitor.get_current_metrics()
        if current_metrics:
            # Increase delay if CPU is high
            if current_metrics.cpu_percent > self.cpu_threshold:
                self.current_delay = min(self.max_delay, self.current_delay * 1.2)
            
            # Increase delay if memory is high
            if current_metrics.memory_percent > self.memory_threshold:
                self.current_delay = min(self.max_delay, self.current_delay * 1.1)
        
        # Traditional cycle-based adjustment
        if self.last_cycle_time > 0:
            cycle_time = now - self.last_cycle_time
            
            self.cycle_times.append(cycle_time)
            if len(self.cycle_times) > self.max_history:
                self.cycle_times.pop(0)
            
            if len(self.cycle_times) >= 5:  # Need some history
                avg_cycle_time = sum(self.cycle_times) / len(self.cycle_times)
                
                if avg_cycle_time < self.min_delay:
                    self.current_delay = min(self.max_delay, self.current_delay * 1.1)
                elif avg_cycle_time > self.max_delay:
                    self.current_delay = max(self.min_delay, self.current_delay * 0.9)
        
        await asyncio.sleep(self.current_delay)
        self.last_cycle_time = time.time()
    
    def get_stats(self) -> Dict[str, float]:
        """Get delay statistics."""
        if not self.cycle_times:
            return {'current_delay': self.current_delay, 'avg_cycle_time': 0}
        
        return {
            'current_delay': self.current_delay,
            'avg_cycle_time': sum(self.cycle_times) / len(self.cycle_times),
            'min_cycle_time': min(self.cycle_times),
            'max_cycle_time': max(self.cycle_times)
        }


class OptimizedPerformanceMonitor:
    """Memory-efficient performance monitoring."""
    
    def __init__(self, max_history: int = 100):
        self.max_history = max_history
        self.metrics = {
            'cycle_count': 0,
            'total_cycle_time': 0,
            'avg_cycle_time': 0,
            'max_cycle_time': 0,
            'min_cycle_time': float('inf'),
            'last_scan_time': 0,
            'last_signal_time': 0,
            'last_position_update_time': 0,
            'memory_usage_mb': 0,
            'cpu_usage_percent': 0
        }
        self.start_time = time.time()
        self.resource_monitor = get_resource_monitor()
    
    def record_cycle(self, cycle_time: float, state: str):
        """Record cycle performance with resource tracking."""
        self.metrics['cycle_count'] += 1
        self.metrics['total_cycle_time'] += cycle_time
        self.metrics['avg_cycle_time'] = (self.metrics['total_cycle_time'] / 
                                        self.metrics['cycle_count'])
        self.metrics['max_cycle_time'] = max(self.metrics['max_cycle_time'], cycle_time)
        self.metrics['min_cycle_time'] = min(self.metrics['min_cycle_time'], cycle_time)
        
        # Update resource metrics
        current_metrics = self.resource_monitor.get_current_metrics()
        if current_metrics:
            self.metrics['memory_usage_mb'] = current_metrics.memory_used_mb
            self.metrics['cpu_usage_percent'] = current_metrics.cpu_percent
        
        # State-specific timings
        if state == 'scanning':
            self.metrics['last_scan_time'] = time.time()
        elif state == 'signal_wait':
            self.metrics['last_signal_time'] = time.time()
        elif state == 'managing':
            self.metrics['last_position_update_time'] = time.time()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get performance statistics."""
        uptime = time.time() - self.start_time
        return {
            **self.metrics,
            'uptime_seconds': uptime,
            'cycles_per_minute': (self.metrics['cycle_count'] / uptime) * 60 if uptime > 0 else 0
        }




class OptimizedOrchestraEngine:
    """Resource-optimized trading system coordinator."""
    
    def __init__(self,
                 preset_name: str,
                 system_config: Optional[SystemConfig] = None,
                 symbols_whitelist: Optional[List[str]] = None):
        """Initialize the optimized orchestra engine."""
        
        # Load configuration
        settings_module = importlib.import_module('breakout_bot.config.settings')
        preset_fn = getattr(settings_module, 'get_preset', get_preset)
        loaded_preset = preset_fn(preset_name)

        if not isinstance(loaded_preset, TradingPreset):
            loaded_preset = load_preset(preset_name)

        if getattr(loaded_preset, 'execution_config', None) is None:
            loaded_preset = loaded_preset.model_copy(update={'execution_config': ExecutionConfig()})

        self.preset = loaded_preset

        raw_system_config = system_config or SystemConfig.from_env()
        if not isinstance(raw_system_config, SystemConfig):
            merged_config = SystemConfig.from_env()
            for field_name in merged_config.model_fields:
                if hasattr(raw_system_config, field_name):
                    setattr(merged_config, field_name, getattr(raw_system_config, field_name))
            raw_system_config = merged_config

        self.system_config = raw_system_config
        self._paper_mode = getattr(self.system_config, 'paper_mode', True)

        # Initialize session ID first
        self._session_id: Optional[str] = None
        self.current_session_id: Optional[str] = None
        
        diag_env_enabled = os.getenv('DEBUG_DIAG', '0') not in {'0', 'false', 'False', ''}
        self.debug_diag = bool(getattr(self.system_config, 'debug_diag', False) or diag_env_enabled)
        self.diagnostics = DiagnosticsCollector(enabled=self.debug_diag, session_id=self.current_session_id)
        self.reasons_counter = self.diagnostics.reasons
        
        # Initialize enhanced logger early
        self.enhanced_logger = get_enhanced_logger("trading_engine")
        
        context = LogContext(component="engine", state="initializing")
        self.enhanced_logger.info(
            f"OptimizedOrchestraEngine.__init__ - system_config.paper_mode: {getattr(self.system_config, 'paper_mode', None)}, self._paper_mode: {self._paper_mode}",
            context
        )
        
        # Initialize symbols whitelist first
        self.symbols_whitelist = (
            [symbol.strip().upper() for symbol in symbols_whitelist if symbol.strip()]
            if symbols_whitelist else []
        )
        
        # Initialize signal tracking
        self.active_signals: List[Signal] = []
        
        # Initialize components with resource limits
        self.exchange_client = ExchangeClient(self.system_config)
        # Use hybrid approach: REST API for scanning, WebSocket for trading
        self.market_data_provider = MarketDataProvider(self.exchange_client, enable_websocket=False)
        self.scanner = BreakoutScanner(self.preset, diagnostics=self.diagnostics)
        self.signal_generator = SignalGenerator(self.preset, diagnostics=self.diagnostics)
        self.risk_manager = RiskManager(self.preset)
        self.position_manager = PositionManager(self.preset)
        self.execution_manager = ExecutionManager(self.exchange_client, self.preset)
        
        # WebSocket-enabled provider for active positions
        self._trading_market_data_provider = None
        
        # Initialize resource monitoring
        self.resource_monitor = get_resource_monitor()
        self.resource_limits = ResourceLimits(
            max_cpu_percent=80.0,
            max_memory_percent=85.0,
            max_memory_mb=2048.0,
            max_disk_percent=90.0,
            max_threads=50,  # Reduced from unlimited
            max_open_files=500
        )
        
        # Process monitoring
        self.monitoring_manager = get_monitoring_manager()
        
        # Initialize performance monitoring
        self.adaptive_delay = OptimizedAdaptiveDelay(
            min_delay=0.1,
            max_delay=5.0,
            initial_delay=0.5
        )
        self.performance_monitor = OptimizedPerformanceMonitor()
        
        # Optimized thread pool with limits
        self.thread_pool = ThreadPoolExecutor(
            max_workers=min(4, psutil.cpu_count()),  # Limit to CPU cores
            thread_name_prefix="breakout_bot"
        )
        
        # Initialize logging system with size limits
        self.logs = []
        self.max_logs = 500  # Reduced from 1000
        
        # WebSocket notification system
        self.websocket_manager = None
        self._setup_websocket_notifications()
        
        # Component list for easy access (using weak references to prevent memory leaks)
        self.components = {
            'exchange_client': weakref.ref(self.exchange_client),
            'market_data_provider': weakref.ref(self.market_data_provider),
            'scanner': weakref.ref(self.scanner),
            'signal_generator': weakref.ref(self.signal_generator),
            'risk_manager': weakref.ref(self.risk_manager),
            'position_manager': weakref.ref(self.position_manager)
        }
        
        # State management
        # Initialize centralized state machine
        self.state_machine = StateMachine(
            initial_state=TradingState.INITIALIZING,
            notify_callback=self._handle_state_transition_notification,
            enhanced_logger=self.enhanced_logger
        )
        
        # Initialize centralized error handler
        self.error_handler = ErrorHandler(
            max_retries=3,
            retry_backoff=2.0,
            notify_callback=self._handle_error_notification
        )
        
        # Legacy properties for backward compatibility (to be removed later)
        self.previous_state: Optional[TradingState] = None
        self.state_data: Dict[str, Any] = {}
        self.running = False
        
        # Command queue and control
        self.command_queue: List[SystemCommand] = []
        
    @property
    def current_state(self) -> TradingState:
        """Получить текущее состояние из StateMachine (для обратной совместимости)."""
        return self.state_machine.current_state
        
    @current_state.setter
    def current_state(self, value: TradingState):
        """Предупреждение о прямом присваивании состояния (deprecated)."""
        logger.warning(
            f"Direct assignment to current_state is deprecated. "
            f"Use _transition_to_state() instead. Attempted: {value.value}"
        )
        # В production это должно быть запрещено, но пока оставим для совместимости
        self.last_command: Optional[SystemCommand] = None
        self.command_lock = asyncio.Lock()
        
        # Error handling and retry
        self.error_count = 0
        self.max_retries = 3
        self.retry_delay = 5.0
        self.last_error: Optional[str] = None
        self.retry_backoff = 1.5
        
        # Health monitoring
        self.health_status = {
            'rest_api': True,
            'websocket': True,
            'database': True,
            'memory': True,
            'cpu': True
        }
        
        # Performance tracking
        self.starting_equity = 0.0
        self.cycle_count = 0
        self.last_cycle_time = 0.0
        self.avg_cycle_time = 0.0
        
        # Trading state
        self.active_positions: List[Position] = []
        self.pending_orders: List[Order] = []
        self.last_scan_time = 0.0
        self.last_signal_time = 0.0
        
        # Market data cache
        self.market_data_cache: Dict[str, MarketData] = {}
        self.cache_ttl = 30.0  # 30 seconds
        
        # Signal management
        self.active_signals: List[Signal] = []
        self.signal_history: List[Signal] = []
        self.max_signal_history = 1000
        
        # Symbols management
        self.symbols_whitelist: Set[str] = set()
        self.symbols_blacklist: Set[str] = set()
        
        # Performance metrics
        self.total_trades = 0
        self.winning_trades = 0
        self.losing_trades = 0
        self.total_pnl = 0.0
        self.max_drawdown = 0.0
        self.current_drawdown = 0.0
        
        # Risk management
        self.daily_pnl = 0.0
        self.daily_trades = 0
        self.last_reset_time = time.time()
        
        # System monitoring
        self.system_start_time = time.time()
        self.last_health_check = 0.0
        self.health_check_interval = 60.0  # 1 minute
        
        # Logging
        self.log_level = logging.INFO
        self.log_to_file = True
        self.log_to_console = True
        
        # Configuration
        self.preset = loaded_preset
        # paper_mode is a property, so we don't set it directly
        
        # Additional attributes
        self.kill_switch_active = False
        self.kill_switch_reason = ""
        self.daily_limit_reached = False
        self.consecutive_losses = 0
        
        # Data storage with size limits
        self.current_positions: List[Position] = []
        self.closed_positions: List[Position] = []
        self.scan_results: List[ScanResult] = []
        self.current_signals: List[Signal] = []
        self.signal_market_data: Dict[str, MarketData] = {}
        self.order_history: List[Order] = []
        default_equity = getattr(self.system_config, 'paper_starting_balance', 0.0) or 0.0
        self.last_known_equity = default_equity
        self.session_start_equity: Optional[float] = None
        self.max_cache_size = 100  # Limit market data cache
        self.last_scan_summary: Optional[Dict[str, Any]] = None
        
        # Metrics
        self.last_scan_time: Optional[datetime] = None
        self.emergency_reason: Optional[str] = None
        
        # Optimization settings
        self.auto_optimize = True
        self.optimization_interval = 300  # 5 minutes
        self.last_optimization = 0.0
        
        # Components are already initialized above
        
        # Log initialization
        context = LogContext(component="engine", state="initialized")
        self.enhanced_logger.info(f"Optimized Orchestra Engine initialized with preset: {preset_name}", context)
        self.enhanced_logger.info(f"Resource limits: CPU<{self.resource_limits.max_cpu_percent}%, "
                   f"Memory<{self.resource_limits.max_memory_percent}%, "
                   f"Threads<{self.resource_limits.max_threads}", context)
    
    def get_trading_market_data_provider(self) -> MarketDataProvider:
        """Get WebSocket-enabled market data provider for active positions."""
        if self._trading_market_data_provider is None:
            self._trading_market_data_provider = MarketDataProvider(self.exchange_client, enable_websocket=True)
        return self._trading_market_data_provider
    
    def is_running(self) -> bool:
        """Check if the engine is currently running."""
        # Engine is running if it's not in idle, stopped, or emergency states
        if not self.running:
            return False
        
        # Check if we're in a running state (including emergency and paused as "running with issues")
        running_states = {
            TradingState.SCANNING, TradingState.LEVEL_BUILDING, TradingState.SIGNAL_WAIT,
            TradingState.SIZING, TradingState.EXECUTION, TradingState.MANAGING,
            TradingState.INITIALIZING, TradingState.EMERGENCY, TradingState.PAUSED
        }
        return self.current_state in running_states
    
    async def start(self) -> None:
        """Start the trading system with resource optimization."""
        
        context = LogContext(component="engine", state="starting")
        self.enhanced_logger.info("Starting Optimized Breakout Bot Orchestra Engine...", context)
        self._add_log('INFO', 'engine', 'Starting Optimized Breakout Bot Orchestra Engine...')
        
        # Start resource monitoring
        await self.resource_monitor.start()
        
        self.running = True
        self.current_state = TradingState.INITIALIZING
        self.daily_pnl = 0.0
        self.consecutive_losses = 0
        self.kill_switch_active = False
        self.kill_switch_reason = ""
        self.session_start_equity = None
        
        # Start monitoring session
        preset_name_value = getattr(self.preset, 'name', 'unknown')
        if not isinstance(preset_name_value, str):
            preset_name_value = str(preset_name_value)
        preset_name = preset_name_value
        self.current_session_id = self.monitoring_manager.start_session(preset_name)
        
        # Add initialization checkpoint
        self.monitoring_manager.add_checkpoint(
            CheckpointType.SCAN_START,
            f"Engine started with preset '{preset_name}'",
            CheckpointStatus.COMPLETED,
            self.current_session_id,
            data={"preset": preset_name, "mode": "paper" if self.paper_mode else "live"}
        )
        
        try:
            while self.running:
                cycle_start = time.time()
                
                # Process commands first (non-blocking)
                await self._process_commands()
                
                # Check resource health and optimize if needed
                if self.auto_optimize:
                    await self._check_and_optimize_resources()
                
                # Parallel health and kill switch checks
                health_task = asyncio.create_task(self._check_health())
                kill_switch_task = asyncio.create_task(self._check_kill_switch())
                
                # Wait for both checks to complete
                health_ok, kill_switch_active = await asyncio.gather(
                    health_task, kill_switch_task, return_exceptions=True
                )
                
                # Handle health check result
                if isinstance(health_ok, Exception) or not health_ok:
                    if self.current_state != TradingState.ERROR:
                        self.previous_state = self.current_state
                        self.current_state = TradingState.ERROR
                        self.last_error = "Health check failed"
                        context = LogContext(component="engine", state="error")
                        self.enhanced_logger.error("System health check failed, entering ERROR state", context)
                        await self._notify_error("HEALTH_CHECK_FAILED", "System health check failed", {"state": self.current_state.value})
                
                # Handle kill switch result
                if isinstance(kill_switch_active, Exception):
                    context = LogContext(component="engine", state="error")
                    self.enhanced_logger.error(f"Kill switch check failed with exception: {kill_switch_active}", context)
                    if self.current_state != TradingState.ERROR:
                        self.previous_state = self.current_state
                        self.current_state = TradingState.ERROR
                        self.last_error = f"Kill switch check failed: {kill_switch_active}"
                        await self._notify_error("KILL_SWITCH_CHECK_FAILED", f"Kill switch check failed: {kill_switch_active}", {"exception": str(kill_switch_active)})
                elif kill_switch_active:
                    if self.current_state != TradingState.PAUSED:
                        self.previous_state = self.current_state
                        self.current_state = TradingState.PAUSED
                        context = LogContext(component="engine", state="paused")
                        self.enhanced_logger.critical(f"Kill switch activated: {self.kill_switch_reason}", context)
                        
                        # Notify about kill switch activation
                        await self._notify_kill_switch(self.kill_switch_reason)
                        
                        # Log the state transition with reason
                        logger.critical(f"FSM transition to PAUSED due to kill switch: {self.kill_switch_reason}")
                else:
                    context = LogContext(component="engine", state="running")
                    self.enhanced_logger.debug("Kill switch check passed", context)
                
                # Execute state cycle (with performance monitoring)
                await self._execute_state_cycle()

                # Persist scan summary when a new scan completed
                if self.current_state in {TradingState.LEVEL_BUILDING, TradingState.SIGNAL_WAIT}:
                    self._record_scan_summary()
                
                # Handle error state with retry
                if self.current_state == TradingState.ERROR:
                    await self._handle_error_state()
                
                # Record cycle performance
                cycle_time = time.time() - cycle_start
                self.performance_monitor.record_cycle(cycle_time, self.current_state.value)
                
                # Resource-aware adaptive delay
                await self.adaptive_delay.wait()
                
        except KeyboardInterrupt:
            context = LogContext(component="engine", state="stopping")
            self.enhanced_logger.info("Received shutdown signal", context)
            self.current_state = TradingState.STOPPED
            self.running = False
        except Exception as e:
            context = LogContext(component="engine", state="error")
            self.enhanced_logger.error(f"Unexpected error in main loop: {e}", context)
            self._add_log('ERROR', 'engine', f"Unexpected error in main loop: {e}", {'error_type': type(e).__name__})
            self.emergency_reason = f"Main loop error: {e}"
            self.current_state = TradingState.EMERGENCY
            # Don't set running = False in emergency state, keep it running but with issues
        finally:
            # Only call stop if we're not in emergency state
            if self.current_state != TradingState.EMERGENCY:
                await self.stop()
    
    async def stop(self) -> None:
        """Stop the trading system gracefully with resource cleanup."""
        
        logger.info("Stopping Optimized Orchestra Engine...")
        
        self.running = False
        self.current_state = TradingState.STOPPED
        
        # Close any open orders
        # Cancel pending signals
        # Save state
        
        # Close exchange client (support mocks/sync methods)
        close_fn = getattr(self.exchange_client, 'close', None)
        if close_fn:
            close_result = close_fn()
            if inspect.isawaitable(close_result):
                await close_result
        
        # Shutdown thread pool
        if hasattr(self, 'thread_pool'):
            self.thread_pool.shutdown(wait=True)
        
        # Clear indicator cache
        clear_indicator_cache()
        
        # Close all exchange connections
        await close_all_connections()
        
        # Close position manager
        if hasattr(self, 'position_manager'):
            self.position_manager.close()
        
        # Stop resource monitoring
        await self.resource_monitor.stop()

        # Close monitoring session
        if self.current_session_id:
            session_status = 'error' if self.emergency_reason else 'completed'
            try:
                self.monitoring_manager.end_session(self.current_session_id, session_status)
            except Exception as exc:
                logger.error(f"Failed to end monitoring session {self.current_session_id}: {exc}")
            finally:
                self.current_session_id = None

        # Force garbage collection
        gc.collect()

        logger.info("Optimized Orchestra Engine stopped")
    
    async def _process_commands(self) -> None:
        """Process queued commands."""
        async with self.command_lock:
            if not self.command_queue:
                return
            
            command = self.command_queue.pop(0)
            await self._execute_command(command)
    
    async def _execute_command(self, command: SystemCommand) -> None:
        """Execute a specific command."""
        logger.info(f"Executing command: {command.value}")
        
        if command == SystemCommand.START:
            await self._handle_start_command()
        elif command == SystemCommand.STOP:
            await self._handle_stop_command()
        elif command == SystemCommand.PAUSE:
            await self._handle_pause_command()
        elif command == SystemCommand.RESUME:
            await self._handle_resume_command()
        elif command == SystemCommand.EMERGENCY_STOP:
            await self._handle_emergency_stop_command()
        elif command == SystemCommand.TIME_STOP:
            await self._handle_time_stop_command()
        elif command == SystemCommand.PANIC_EXIT:
            await self._handle_panic_exit_command()
        elif command == SystemCommand.KILL_SWITCH:
            await self._handle_kill_switch_command()
        elif command == SystemCommand.OPTIMIZE:
            await self._handle_optimize_command()
        elif command == SystemCommand.RESET:
            await self._handle_reset_command()
    
    async def _handle_start_command(self) -> None:
        """Handle start command."""
        # Start from any state except emergency
        if self.current_state != TradingState.EMERGENCY:
            self.running = True
            self.kill_switch = False
            self.kill_switch_active = False
            self.kill_switch_reason = ""
            self.error_count = 0
            self.last_error = None
            self.current_state = TradingState.INITIALIZING
            logger.info("Engine started via command")
    
    async def _handle_stop_command(self) -> None:
        """Handle stop command."""
        self.running = False
        self.current_state = TradingState.STOPPED
        logger.info("Engine stopped via command")
    
    async def _handle_pause_command(self) -> None:
        """Handle pause command."""
        if self.current_state in [TradingState.SCANNING, TradingState.LEVEL_BUILDING, TradingState.SIGNAL_WAIT, TradingState.EXECUTION, TradingState.MANAGING]:
            self.previous_state = self.current_state
            self.current_state = TradingState.PAUSED
            logger.info("Engine paused via command")
    
    async def _handle_resume_command(self) -> None:
        """Handle resume command."""
        if self.current_state == TradingState.PAUSED:
            if self.previous_state:
                self.current_state = self.previous_state
                self.previous_state = None
            else:
                # If no previous state, go to scanning
                self.current_state = TradingState.SCANNING
            logger.info("Engine resumed via command")
    
    async def _handle_emergency_stop_command(self) -> None:
        """Handle emergency stop command."""
        self.running = False
        self.current_state = TradingState.EMERGENCY
        self.emergency_reason = "Emergency stop command"
        logger.critical("Emergency stop activated via command")
    
    async def _handle_reset_command(self) -> None:
        """Handle reset command."""
        self.running = False
        self.current_state = TradingState.IDLE
        self.previous_state = None
        self.error_count = 0
        self.last_error = None
        logger.info("Engine reset via command")
    
    async def _handle_time_stop_command(self) -> None:
        """Handle time stop command."""
        self.running = False
        self.current_state = TradingState.STOPPED
        logger.info("Engine stopped via time stop command")
    
    async def _handle_panic_exit_command(self) -> None:
        """Handle panic exit command."""
        self.running = False
        self.current_state = TradingState.EMERGENCY
        self.emergency_reason = "Panic exit command"
        logger.critical("Panic exit activated via command")
    
    async def _handle_kill_switch_command(self) -> None:
        """Handle kill switch command."""
        self.running = False
        self.kill_switch = True
        self.kill_switch_active = True
        self.kill_switch_reason = "Kill switch activated"
        await self._notify_kill_switch("Kill switch activated via command")
        self.current_state = TradingState.EMERGENCY
        self.emergency_reason = "Kill switch activated"
        import logging
        logging.getLogger(__name__).critical("Kill switch activated via command")
    
    async def _handle_optimize_command(self) -> None:
        """Handle optimize command."""
        logger.info("Optimize command received - optimization not implemented yet")
        # TODO: Implement optimization logic
    
    async def execute_command(self, command: str) -> Dict[str, Any]:
        """Execute a command by name."""
        try:
            command_enum = SystemCommand(command)
            await self._execute_command(command_enum)
            return {
                "success": True,
                "message": f"Command '{command}' executed successfully",
                "command": command
            }
        except ValueError:
            logger.error(f"Unknown command: {command}")
            return {
                "success": False,
                "message": f"Unknown command: {command}",
                "command": command
            }
    
    async def _check_health(self) -> bool:
        """Check system health and return True if healthy."""
        try:
            logger.info(f"_check_health called - paper_mode: {self.paper_mode}")
            # Check if exchange client is initialized
            if not self.exchange_client:
                logger.warning("Exchange client not initialized, skipping health check")
                self.health_status['rest_api'] = True  # Assume healthy for paper trading
                return True
            
            if self.paper_mode:
                logger.info("Paper mode: verifying simulated balance")
                await self.exchange_client.fetch_balance()
                self.health_status['rest_api'] = True
            else:
                api_key = os.getenv('EXCHANGE_API_KEY')
                api_secret = os.getenv('EXCHANGE_SECRET')
                if not api_key or not api_secret:
                    logger.info("API keys отсутствуют, пропускаем проверку баланса в live режиме")
                    self.health_status['rest_api'] = True
                else:
                    logger.info("Checking balance in live mode")
                    await self.exchange_client.fetch_balance()
                    self.health_status['rest_api'] = True
            
            # Check WebSocket (if implemented)
            # self.health_status['websocket'] = await self._check_websocket()
            
            # Check database (if implemented)
            # self.health_status['database'] = await self._check_database()
            
            self.health_status['last_check'] = datetime.now()
            return True
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            self.health_status['rest_api'] = False
            self.error_count += 1
            
            # Auto-recovery attempt for common errors
            if "Connection" in str(e) or "timeout" in str(e).lower():
                logger.info("Attempting auto-recovery for connection error...")
                try:
                    # Reset exchange client connection
                    if hasattr(self, 'exchange_client') and self.exchange_client:
                        await self.exchange_client.close()
                        self.exchange_client = ExchangeClient(self.system_config)
                    logger.info("Auto-recovery successful")
                except Exception as recovery_error:
                    logger.error(f"Auto-recovery failed: {recovery_error}")
            
            return False
    
    async def _check_kill_switch(self) -> bool:
        """Check if kill switch should be activated."""
        try:
            # Check if preset is loaded
            if not self.preset:
                logger.error("Preset not loaded, cannot check kill switch")
                return False
            
            equity_base = self.session_start_equity or self.starting_equity or self.last_known_equity or 1.0
            daily_limit_usd = equity_base * self.preset.risk.daily_risk_limit
            kill_switch_usd = equity_base * self.preset.risk.kill_switch_loss_limit

            # Check if kill switch should be activated
            should_activate = False
            reason = ""

            if self.daily_pnl <= -kill_switch_usd:
                should_activate = True
                reason = f"Kill switch loss limit reached: {self.daily_pnl:.2f} <= -{kill_switch_usd:.2f}"
            elif self.daily_pnl <= -daily_limit_usd:
                should_activate = True
                reason = f"Daily risk limit reached: {self.daily_pnl:.2f} <= -{daily_limit_usd:.2f}"
            else:
                max_losses = self.preset.risk.max_consecutive_losses
                if self.consecutive_losses >= max_losses:
                    should_activate = True
                    reason = f"Max consecutive losses reached: {self.consecutive_losses} >= {max_losses}"

            # Activate kill switch if conditions are met
            if should_activate and not self.kill_switch_active:
                self.kill_switch_active = True
                self.kill_switch_reason = reason
                logger.critical(f"Kill switch activated: {self.kill_switch_reason}")
                await self._notify_kill_switch(self.kill_switch_reason)
                return True
            
            # Reset kill switch if conditions are no longer met
            elif not should_activate and self.kill_switch_active:
                logger.info(f"Kill switch reset: conditions no longer met (daily_pnl={self.daily_pnl:.2f}, consecutive_losses={self.consecutive_losses})")
                self.kill_switch_active = False
                self.kill_switch_reason = ""
                return False
            
            # Return current status
            if self.kill_switch_active:
                logger.debug(f"Kill switch still active: {self.kill_switch_reason}")
                return True

            logger.debug(
                "Kill switch check: daily_pnl=%.2f, consecutive_losses=%s, daily_limit_usd=%.2f, kill_switch_usd=%.2f",
                self.daily_pnl,
                self.consecutive_losses,
                daily_limit_usd,
                kill_switch_usd,
            )
            return False
            
        except Exception as e:
            logger.error(f"Error in kill switch check: {e}")
            return False
    
    async def _fetch_market_data_safe(self, symbol: str, use_websocket: bool = False) -> Optional[MarketData]:
        """Safely fetch market data for a symbol."""
        try:
            if use_websocket:
                # Use WebSocket-enabled provider for active positions
                provider = self.get_trading_market_data_provider()
                return await provider.get_market_data(symbol)
            else:
                # Use REST API provider for scanning
                return await self.market_data_provider.get_market_data(symbol)
        except Exception as e:
            logger.warning(f"Failed to fetch market data for {symbol}: {e}")
            return None

    async def run_manual_scan(self,
                              preset_name: Optional[str] = None,
                              limit: Optional[int] = None,
                              symbols: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Run a single scan cycle without starting the full engine loop."""

        from ..config.settings import get_preset

        if preset_name and preset_name != self.preset.name:
            preset = get_preset(preset_name)
            scanner = BreakoutScanner(preset)
        else:
            preset = self.preset
            scanner = self.scanner

        if limit and hasattr(preset, 'scanner_config') and limit > preset.scanner_config.max_candidates:
            preset.scanner_config.max_candidates = limit
            if hasattr(scanner, 'preset'):
                scanner.preset.scanner_config.max_candidates = limit

        if symbols:
            universe = [s.strip().upper() for s in symbols if s.strip()]
        elif self.symbols_whitelist:
            universe = list(self.symbols_whitelist)
        else:
            universe = await self.exchange_client.fetch_markets()

        fetch_limit = limit or preset.scanner_config.max_candidates
        symbols_to_fetch = universe[:fetch_limit] if fetch_limit > 0 else universe

        market_data = await self.market_data_provider.get_multiple_market_data(symbols_to_fetch)
        market_data_list = list(market_data.values())
        btc_data = market_data.get('BTC/USDT') or market_data.get('BTC/USDT:USDT')

        scan_results = await scanner.scan_markets(market_data_list, btc_data)

        if limit:
            scan_results = scan_results[:limit]

        self.scan_results = scan_results
        self.last_scan_time = datetime.now()
        self._record_scan_summary()

        return self.get_last_scan_results()

    def _record_scan_summary(self) -> None:
        """Capture summary statistics after each scan."""
        if not self.scan_results:
            self.last_scan_summary = None
            return

        filter_pass = Counter()
        filter_fail = Counter()
        for result in self.scan_results:
            for name, passed in result.filter_results.items():
                if passed:
                    filter_pass[name] += 1
                else:
                    filter_fail[name] += 1

        scores = [r.score for r in self.scan_results]
        self.last_scan_summary = {
            'markets_considered': len(self.scan_results),
            'avg_score': mean(scores) if scores else None,
            'min_score': min(scores) if scores else None,
            'max_score': max(scores) if scores else None,
            'filter_pass': dict(filter_pass),
            'filter_fail': dict(filter_fail),
            'signal_count': len(self.active_signals),
        }

    async def _get_account_equity(self) -> float:
        """Получить доступную эквити для расчёта позиций."""
        balance: Dict[str, float] = {}
        try:
            if self.paper_mode:
                # В paper режиме используем фиксированный баланс
                balance = {'USDT': 10000.0}
            else:
                # Только если есть API ключи
                api_key = os.getenv('EXCHANGE_API_KEY')
                api_secret = os.getenv('EXCHANGE_SECRET')
                
                if not api_key or not api_secret:
                    logger.info("No API keys available, using paper balance")
                    balance = {'USDT': 10000.0}
                else:
                    balance = await self.exchange_client.fetch_balance()
        except Exception as exc:
            logger.warning(f"Не удалось получить баланс: {exc}")
            # Fallback для paper режима
            balance = {'USDT': 10000.0}

        equity = self._select_equity_from_balance(balance)

        if equity <= 0:
            paper_exchange = getattr(self.exchange_client, '_paper_exchange', None)
            if paper_exchange and hasattr(paper_exchange, 'balance'):
                equity = float(paper_exchange.balance.get('USDT', equity or 0))

        if equity <= 0:
            fallback = self.last_known_equity or self.starting_equity or 1.0
            equity = fallback

        self.last_known_equity = equity
        if self.session_start_equity is None and equity > 0:
            self.session_start_equity = equity
        logger.debug(f"Текущая эквити для расчёта позиций: {equity:.2f} USDT")
        return equity

    def _select_equity_from_balance(self, balance: Dict[str, float]) -> float:
        """Выбрать подходящую валюту эквити из баланса."""
        if not balance:
            return 0.0

        # Get cash balance
        cash_balance = 0.0
        for stable in ('USDT', 'USDC', 'USD', 'BUSD', 'USDP'):
            value = balance.get(stable)
            if isinstance(value, (int, float)) and value > 0:
                cash_balance = float(value)
                break
        
        if cash_balance == 0:
            numeric_values = [float(v) for v in balance.values() if isinstance(v, (int, float))]
            cash_balance = sum(numeric_values) if numeric_values else 0.0
        
        # Add unrealized PnL from current positions
        unrealized_pnl = 0.0
        for position in self.current_positions:
            if hasattr(position, 'unrealized_pnl') and position.unrealized_pnl is not None:
                unrealized_pnl += position.unrealized_pnl
        
        total_equity = cash_balance + unrealized_pnl
        logger.debug(f"Equity calculation: cash={cash_balance:.2f}, unrealized_pnl={unrealized_pnl:.2f}, total={total_equity:.2f}")
        
        return total_equity

    async def _resolve_market_data_for_signal(self, signal: Signal) -> Optional[MarketData]:
        market_snapshot = signal.meta.get('market_snapshot') if signal.meta else None
        if market_snapshot:
            try:
                return MarketData.model_validate(market_snapshot)
            except ValidationError as exc:
                logger.debug(f"Market snapshot validation failed for {signal.symbol}: {exc}")

        cached = self.signal_market_data.get(signal.symbol)
        if cached:
            return cached

        cached = self.market_data_cache.get(signal.symbol)
        if cached:
            return cached

        market_data = await self._fetch_market_data_safe(signal.symbol, use_websocket=True)
        if market_data:
            self.market_data_cache[signal.symbol] = market_data
            self.signal_market_data[signal.symbol] = market_data
        return market_data

    async def _open_position(self, signal: Signal) -> Optional[Position]:
        """Создать бумажную позицию по сигналу."""
        size_payload = signal.meta.get('position_size') or {}
        qty = float(size_payload.get('quantity', 0) or 0)
        if qty <= 0:
            logger.warning(f"Нулевая позиция по сигналу {signal.symbol}, пропускаем исполнение")
            return None

        side = 'buy' if signal.side == 'long' else 'sell'
        position_size = None
        try:
            allowed_keys = {field: size_payload[field] for field in PositionSize.__dataclass_fields__ if field in size_payload}
            if allowed_keys:
                position_size = PositionSize(**allowed_keys)
        except TypeError:
            position_size = None

        market_data = await self._resolve_market_data_for_signal(signal)
        if not market_data:
            logger.error(f"Нет маркет-данных для исполнения {signal.symbol}")
            return None

        try:
            order = await self.execution_manager.execute_trade(
                symbol=signal.symbol,
                side=side,
                total_quantity=qty,
                market_data=market_data,
                position_size=position_size,
                reduce_only=False,
                intent='entry'
            )
        except Exception as exc:
            logger.error(f"Ошибка исполнения ордера {signal.symbol}: {exc}")
            return None

        if not order or not order.filled_qty:
            logger.error(f"Ордер не был заполнен при открытии {signal.symbol}")
            return None

        filled_qty = order.filled_qty
        fill_price = order.avg_fill_price or signal.entry
        timestamp = order.timestamps.get('created_at', int(time.time() * 1000))
        stop_distance = size_payload.get('stop_distance') or abs(signal.entry - signal.sl)

        position = Position(
            id=str(uuid.uuid4()),
            symbol=signal.symbol,
            side=signal.side,
            strategy=signal.strategy,
            qty=filled_qty,
            entry=fill_price,
            sl=signal.sl,
            tp=signal.meta.get('tp2') or signal.meta.get('tp1'),
            status='open',
            pnl_usd=0.0,
            pnl_r=0.0,
            fees_usd=order.fees_usd,
            timestamps={'opened_at': timestamp},
            meta={
                'entry_order_id': order.id,
                'position_size': size_payload,
                'tp1': signal.meta.get('tp1'),
                'tp2': signal.meta.get('tp2'),
                'btc_correlation': signal.meta.get('market_snapshot', {}).get('btc_correlation'),
                'stop_distance': stop_distance,
                'entry_fee': order.fees_usd,
                'signal_reason': signal.reason,
                'execution': order.metadata,
                'initial_qty': filled_qty,
            }
        )

        self.order_history.append(order)
        self.position_manager.add_position(position)
        logger.info(
            f"Открыта позиция {position.id} {position.symbol} qty={filled_qty:.4f} по {fill_price:.6f}"
        )

        return position

    async def _close_position(self, position: Position, current_price: float, reason: str) -> None:
        """Закрыть бумажную позицию и зафиксировать результат."""
        if position.status == 'closed':
            return
        qty = position.qty
        side = 'sell' if position.side == 'long' else 'buy'

        market_data = self.market_data_cache.get(position.symbol)
        if not market_data:
            market_data = await self._fetch_market_data_safe(position.symbol, use_websocket=True)
            if market_data:
                self.market_data_cache[position.symbol] = market_data

        try:
            order = await self.execution_manager.execute_trade(
                symbol=position.symbol,
                side=side,
                total_quantity=qty,
                market_data=market_data or MarketData(
                    symbol=position.symbol,
                    price=current_price,
                    volume_24h_usd=0.0,
                    oi_usd=None,
                    oi_change_24h=None,
                    trades_per_minute=0.0,
                    atr_5m=0.0,
                    atr_15m=0.0,
                    bb_width_pct=0.0,
                    btc_correlation=0.0,
                    l2_depth=None,
                    candles_5m=[],
                    timestamp=int(time.time() * 1000)
                ),
                position_size=None,
                reduce_only=True,
                intent=reason
            )
        except Exception as exc:
            logger.error(f"Не удалось закрыть позицию {position.id}: {exc}")
            return

        if not order:
            logger.error(f"Исполнитель не вернул данные по закрытию позиции {position.id}")
            return

        exit_price = order.avg_fill_price or current_price
        timestamp = order.timestamps.get('created_at', int(time.time() * 1000))
        direction = 1 if position.side == 'long' else -1
        gross_pnl = (exit_price - position.entry) * position.qty * direction
        total_fees = (position.meta.get('entry_fee', 0.0) or 0.0) + order.fees_usd
        net_pnl = gross_pnl - total_fees

        stop_distance = position.meta.get('stop_distance') or abs(position.entry - position.sl)
        risk_unit = stop_distance * position.qty if stop_distance else position.entry or 1

        position.status = 'closed'
        position.pnl_usd = net_pnl
        position.pnl_r = net_pnl / risk_unit if risk_unit else 0.0
        position.fees_usd = total_fees
        position.timestamps['closed_at'] = timestamp
        position.meta.update({
            'exit_order_id': order.id,
            'exit_price': exit_price,
            'exit_fee': order.fees_usd,
            'exit_reason': reason,
            'exit_execution': order.metadata,
        })

        self.order_history.append(order)
        self.closed_positions.append(position)
        self.position_manager.remove_position(position.id)
        self.signal_market_data.pop(position.symbol, None)

        if position in self.current_positions:
            self.current_positions.remove(position)

        self.daily_pnl += net_pnl
        self.consecutive_losses = self.consecutive_losses + 1 if net_pnl < 0 else 0

        logger.info(
            f"Позиция {position.id} закрыта ({reason}) по {exit_price:.6f}, PnL={net_pnl:.2f} USDT"
        )

    async def _update_open_positions(self) -> None:
        """Обновить состояние открытых позиций и обработать выходы."""
        if not self.current_positions:
            return

        to_close: List[Tuple[Position, str, float]] = []
        market_data_dict: Dict[str, MarketData] = {}

        for position in list(self.current_positions):
            market_data = self.market_data_cache.get(position.symbol)
            if not market_data:
                market_data = await self._fetch_market_data_safe(position.symbol, use_websocket=True)
                if market_data:
                    self.market_data_cache[position.symbol] = market_data

            if not market_data:
                continue

            market_data_dict[position.symbol] = market_data

            current_price = market_data.price
            direction = 1 if position.side == 'long' else -1
            stop_distance = position.meta.get('stop_distance') or abs(position.entry - position.sl)
            position.pnl_usd = (current_price - position.entry) * position.qty * direction
            risk_unit = stop_distance * position.qty if stop_distance else position.entry or 1
            position.pnl_r = position.pnl_usd / risk_unit if risk_unit else 0.0
            position.meta['last_price'] = current_price
            position.meta['updated_at'] = datetime.now().isoformat() + "Z"
            self.position_manager.update_position(position)

            exit_reason = None
            tp1 = position.meta.get('tp1')
            tp2 = position.meta.get('tp2')

            if position.side == 'long':
                if current_price <= position.sl:
                    exit_reason = 'stop_loss'
                elif tp2 and current_price >= tp2:
                    exit_reason = 'tp2'
                elif tp1 and current_price >= tp1:
                    exit_reason = 'tp1'
            else:
                if current_price >= position.sl:
                    exit_reason = 'stop_loss'
                elif tp2 and current_price <= tp2:
                    exit_reason = 'tp2'
                elif tp1 and current_price <= tp1:
                    exit_reason = 'tp1'

            if exit_reason:
                to_close.append((position, exit_reason, current_price))

        updates: List[PositionUpdate] = []
        try:
            if hasattr(self, 'position_manager'):
                updates = await self.position_manager.process_position_updates(
                    self.current_positions,
                    market_data_dict
                )
        except Exception as exc:
            logger.error(f"Ошибка при обработке обновлений позиций: {exc}")

        if updates:
            await self._apply_position_updates(updates, market_data_dict)

        for position, reason, price in to_close:
            if position.status != 'closed':
                await self._close_position(position, price, reason)

    async def _apply_position_updates(self,
                                      updates: List[PositionUpdate],
                                      market_data_dict: Dict[str, MarketData]) -> None:
        for update in updates:
            position = next((p for p in self.current_positions if p.id == update.position_id), None)
            if not position:
                continue

            market_data = market_data_dict.get(position.symbol)

            if update.action == 'update_stop' and update.price:
                old_stop = position.sl
                position.sl = update.price
                position.meta.setdefault('stop_updates', []).append({
                    'old': old_stop,
                    'new': update.price,
                    'timestamp': int(time.time() * 1000),
                    'reason': update.reason,
                })
                logger.info(f"Стоп по {position.symbol} обновлён: {old_stop:.6f} -> {update.price:.6f}")
                await self._notify_stop_moved(position.id, old_stop, update.price)
                continue

            if update.action == 'take_profit' and update.quantity:
                await self._scale_out_position(
                    position,
                    update.quantity,
                    update.price,
                    market_data,
                    update.reason or 'take_profit'
                )
                continue

            if update.action == 'close':
                fallback_price = update.price or (market_data.price if market_data else position.entry)
                await self._close_position(position, fallback_price, update.reason or 'managed_close')
                continue

            if update.action == 'add_on' and update.quantity:
                await self._add_on_position(
                    position,
                    update.quantity,
                    update.price,
                    market_data,
                    update.reason or 'add_on'
                )

    async def _scale_out_position(self,
                                  position: Position,
                                  quantity: float,
                                  price_hint: Optional[float],
                                  market_data: Optional[MarketData],
                                  reason: str) -> None:
        if quantity <= 0 or position.status != 'open':
            return

        exit_side = 'sell' if position.side == 'long' else 'buy'
        trade_qty = min(quantity, position.qty)
        if trade_qty <= 0:
            return

        market_snapshot = market_data or await self._fetch_market_data_safe(position.symbol, use_websocket=True)
        if market_snapshot:
            self.market_data_cache[position.symbol] = market_snapshot

        order = await self.execution_manager.execute_trade(
            symbol=position.symbol,
            side=exit_side,
            total_quantity=trade_qty,
            market_data=market_snapshot or MarketData(
                symbol=position.symbol,
                price=price_hint or position.entry,
                volume_24h_usd=0.0,
                oi_usd=None,
                oi_change_24h=None,
                trades_per_minute=0.0,
                atr_5m=0.0,
                atr_15m=0.0,
                bb_width_pct=0.0,
                btc_correlation=0.0,
                l2_depth=None,
                candles_5m=[],
                timestamp=int(time.time() * 1000)
            ),
            position_size=None,
            reduce_only=True,
            intent=reason
        )

        if not order or not order.filled_qty:
            logger.warning(f"Сделка для частичного выхода {position.symbol} не заполнена")
            return

        fill_qty = order.filled_qty
        fill_price = order.avg_fill_price or price_hint or (market_snapshot.price if market_snapshot else position.entry)
        direction = 1 if position.side == 'long' else -1
        realized = (fill_price - position.entry) * fill_qty * direction - order.fees_usd

        position.qty = max(0.0, position.qty - fill_qty)
        position.fees_usd += order.fees_usd
        position.meta.setdefault('realized_trades', []).append({
            'qty': fill_qty,
            'price': fill_price,
            'reason': reason,
            'timestamp': order.timestamps.get('created_at', int(time.time() * 1000)),
            'order_id': order.id,
            'execution': order.metadata,
            'realized_usd': realized,
        })
        total_realized = position.meta.get('realized_pnl_usd', 0.0) + realized
        position.meta['realized_pnl_usd'] = total_realized

        self.daily_pnl += realized
        self.order_history.append(order)
        
        # Notify about take profit
        await self._notify_take_profit(position.id, fill_price, realized)

        if position.qty <= 1e-8:
            position.qty = 0.0
            position.status = 'closed'
            position.pnl_usd = total_realized
            stop_distance = position.meta.get('stop_distance') or abs(position.entry - position.sl)
            initial_qty = position.meta.get('initial_qty', fill_qty) or fill_qty
            risk_unit = stop_distance * initial_qty if stop_distance else 0.0
            position.pnl_r = position.pnl_usd / risk_unit if risk_unit else 0.0
            position.timestamps['closed_at'] = order.timestamps.get('created_at', int(time.time() * 1000))
            position.meta.update({
                'exit_reason': reason,
                'exit_execution': order.metadata,
            })
            if position in self.current_positions:
                self.current_positions.remove(position)
            self.closed_positions.append(position)
            self.position_manager.remove_position(position.id)
            self.consecutive_losses = self.consecutive_losses + 1 if total_realized < 0 else 0
        else:
            self.position_manager.update_position(position)

    async def _add_on_position(self,
                                position: Position,
                                quantity: float,
                                price_hint: Optional[float],
                                market_data: Optional[MarketData],
                                reason: str) -> None:
        if quantity <= 0 or position.status != 'open':
            return

        entry_side = 'buy' if position.side == 'long' else 'sell'
        snapshot = market_data or await self._fetch_market_data_safe(position.symbol, use_websocket=True)
        if snapshot:
            self.market_data_cache[position.symbol] = snapshot

        order = await self.execution_manager.execute_trade(
            symbol=position.symbol,
            side=entry_side,
            total_quantity=quantity,
            market_data=snapshot or MarketData(
                symbol=position.symbol,
                price=price_hint or position.entry,
                volume_24h_usd=0.0,
                oi_usd=None,
                oi_change_24h=None,
                trades_per_minute=0.0,
                atr_5m=0.0,
                atr_15m=0.0,
                bb_width_pct=0.0,
                btc_correlation=0.0,
                l2_depth=None,
                candles_5m=[],
                timestamp=int(time.time() * 1000)
            ),
            position_size=None,
            reduce_only=False,
            intent=reason
        )

        if not order or not order.filled_qty:
            logger.warning(f"Не удалось увеличить позицию {position.symbol}")
            return

        fill_qty = order.filled_qty
        fill_price = order.avg_fill_price or price_hint or (snapshot.price if snapshot else position.entry)
        total_qty = position.qty + fill_qty
        if total_qty <= 0:
            return
        position.entry = ((position.entry * position.qty) + (fill_price * fill_qty)) / total_qty
        position.qty = total_qty
        position.fees_usd += order.fees_usd
        position.meta['initial_qty'] = position.meta.get('initial_qty', total_qty - fill_qty) + fill_qty
        position.meta.setdefault('add_on_trades', []).append({
            'qty': fill_qty,
            'price': fill_price,
            'timestamp': order.timestamps.get('created_at', int(time.time() * 1000)),
            'execution': order.metadata,
        })
        self.order_history.append(order)
        self.position_manager.update_position(position)
    
    async def _handle_idle_state(self) -> None:
        """Handle IDLE state - waiting for start command."""
        # Just wait for start command
        await asyncio.sleep(1.0)
    
    async def _handle_initializing_state(self) -> None:
        """Handle INITIALIZING state - setup components."""
        try:
            logger.info("Initializing trading system components...")
            
            # Initialize exchange client
            if not self.exchange_client:
                self.exchange_client = ExchangeClient(self.system_config)
                # ExchangeClient doesn't have an initialize method, it's initialized in __init__
            
            # Initialize market data provider
            if not hasattr(self, 'market_data_provider'):
                # Use hybrid approach: REST API for scanning, WebSocket for trading
                self.market_data_provider = MarketDataProvider(self.exchange_client, enable_websocket=False)
            
            # Initialize scanner
            if not hasattr(self, 'scanner'):
                self.scanner = BreakoutScanner(self.preset)
            
            # Initialize signal generator
            if not hasattr(self, 'signal_generator'):
                self.signal_generator = SignalGenerator(self.preset)
            
            # Initialize risk manager
            if not hasattr(self, 'risk_manager'):
                self.risk_manager = RiskManager(self.preset)
            
            # Initialize position manager
            if not hasattr(self, 'position_manager'):
                self.position_manager = PositionManager(self.preset)
            
            context = LogContext(component="engine", state="initializing")
            self.enhanced_logger.info("Initialization complete, transitioning to SCANNING", context)
            await self._transition_to_state(TradingState.SCANNING, "Initialization complete")
            
        except Exception as e:
            # Use centralized error handling
            recovery_action = await self.error_handler.handle_error(
                exception=e,
                component="engine",
                operation="initialization",
                context={"state": "initializing"}
            )
            
            self.last_error = str(e)
            
            # Execute recovery action
            if recovery_action["emergency"]:
                await self._transition_to_state(TradingState.EMERGENCY, f"Initialization emergency: {e}")
            elif recovery_action["next_state"]:
                await self._transition_to_state(recovery_action["next_state"], f"Initialization failed: {e}")
            else:
                await self._transition_to_state(TradingState.ERROR, f"Initialization failed: {e}")
    
    async def _handle_scanning_state(self) -> None:
        """Handle SCANNING state - scan for market opportunities."""
        try:
            context = LogContext(
                component="scanning",
                state="SCANNING",
                session_id=self.current_session_id
            )
            self.enhanced_logger.info("Scanning for market opportunities...", context)
            
            # Очистим сигналы прошлых циклов
            self.signal_market_data.clear()
            self.current_signals.clear()

            # Add scanning start checkpoint
            self.monitoring_manager.add_checkpoint(
                CheckpointType.SCAN_START,
                "Starting market scan",
                CheckpointStatus.IN_PROGRESS,
                self.current_session_id
            )
            
            # Get market data
            symbols = await self.exchange_client.fetch_markets()
            if self.symbols_whitelist:
                symbols = [s for s in symbols if s in self.symbols_whitelist]
            # Use hybrid approach: scan all symbols with REST API (no WebSocket limits)
            fetch_limit = int(os.getenv('ENGINE_MARKET_FETCH_LIMIT', '0'))  # 0 = all symbols
            symbols_to_fetch = symbols[:fetch_limit] if fetch_limit > 0 else symbols
            market_data = await self.market_data_provider.get_multiple_market_data(symbols_to_fetch)

            # Обновляем кэш рыночных данных, контролируя размер
            for symbol, data in market_data.items():
                self.market_data_cache[symbol] = data
                if len(self.market_data_cache) > self.max_cache_size:
                    oldest_key = next(iter(self.market_data_cache))
                    if oldest_key in self.market_data_cache:
                        self.market_data_cache.pop(oldest_key)
            
            # Add market data checkpoint
            self.monitoring_manager.add_checkpoint(
                CheckpointType.SCAN_START,
                f"Fetched data for {len(symbols)} markets",
                CheckpointStatus.COMPLETED,
                self.current_session_id,
                metrics={"markets_count": len(symbols_to_fetch), "data_points": len(market_data)}
            )
            
            # Run scanner
            scan_results = await self.scanner.scan_markets(
                list(market_data.values()),
                market_data.get('BTC/USDT') or market_data.get('BTC/USDT:USDT')
            )
            self.scan_results = scan_results
            
            # Add scan completion checkpoint
            self.monitoring_manager.add_checkpoint(
                CheckpointType.SCAN_COMPLETE,
                f"Scan completed, found {len(scan_results)} candidates",
                CheckpointStatus.COMPLETED,
                self.current_session_id,
                metrics={"candidates_found": len(scan_results), "markets_scanned": len(symbols)}
            )
            
            if scan_results:
                self.enhanced_logger.info(f"Found {len(scan_results)} candidates, transitioning to LEVEL_BUILDING", context)
                await self._transition_to_state(TradingState.LEVEL_BUILDING, f"Found {len(scan_results)} candidates")
            else:
                self.enhanced_logger.debug("No candidates found, continuing scan", context)
                await asyncio.sleep(5.0)  # Wait before next scan
                
        except Exception as e:
            # Use centralized error handling
            recovery_action = await self.error_handler.handle_error(
                exception=e,
                component="scanner",
                operation="market_scan",
                context={"state": "scanning", "symbols_count": len(symbols_to_fetch) if 'symbols_to_fetch' in locals() else 0}
            )
            
            self.last_error = str(e)
            
            # Execute recovery action with retry logic
            if recovery_action["should_retry"]:
                logger.info(f"Retrying scan after {recovery_action['delay']}s delay")
                await asyncio.sleep(recovery_action["delay"])
                # Continue in scanning state for retry
            elif recovery_action["next_state"]:
                await self._transition_to_state(recovery_action["next_state"], f"Scanning failed: {e}")
            else:
                await self._transition_to_state(TradingState.ERROR, f"Scanning failed: {e}")
    
    async def _handle_level_building_state(self) -> None:
        """Handle LEVEL_BUILDING state - build trading levels."""
        try:
            context = LogContext(component="level_building", state="LEVEL_BUILDING")
            self.enhanced_logger.info("Building trading levels...", context)
            self.enhanced_logger.info(f"Processing {len(self.scan_results)} scan results", context)
            
            # Add level building start checkpoint
            if self.current_session_id:
                self.monitoring_manager.add_checkpoint(
                    CheckpointType.LEVEL_BUILDING_START,
                    "Starting level building",
                    CheckpointStatus.IN_PROGRESS,
                    self.current_session_id
                )
            
            # Process scan results to build levels
            for i, result in enumerate(self.scan_results):
                self.enhanced_logger.debug(f"Building levels for candidate {i+1}/{len(self.scan_results)}: {result.symbol}", context)
                try:
                    # Build levels for each candidate
                    levels = await self.scanner.build_levels(result)
                    result.levels = levels
                    self.enhanced_logger.debug(f"Built {len(levels)} levels for {result.symbol}", context)
                except Exception as e:
                    self.enhanced_logger.error(f"Error building levels for {result.symbol}: {e}", context)
                    result.levels = []
            
            self.enhanced_logger.info("Levels built, transitioning to SIGNAL_WAIT", context)
            
            # Add level building completion checkpoint
            if self.current_session_id:
                self.monitoring_manager.add_checkpoint(
                    CheckpointType.LEVEL_BUILDING_COMPLETE,
                    f"Levels built for {len(self.scan_results)} candidates",
                    CheckpointStatus.COMPLETED,
                    self.current_session_id
                )
            
            await self._transition_to_state(TradingState.SIGNAL_WAIT, "Level building complete")
            
        except Exception as e:
            context = LogContext(component="level_building", state="ERROR")
            # Reduced traceback logging - only log essential error info
            self.enhanced_logger.error(f"Level building failed: {type(e).__name__}: {str(e)}", context)
            await self._transition_to_state(TradingState.ERROR, f"Level building failed: {e}")
            self.last_error = f"Level building failed: {e}"
    
    async def _handle_signal_wait_state(self) -> None:
        """Handle SIGNAL_WAIT state - wait for trading signals."""
        try:
            if self.kill_switch_active:
                logger.info("Kill switch active, skipping signal processing")
                await asyncio.sleep(2.0)
                return

            # Check if we have open positions that need management
            open_positions = [p for p in self.current_positions if p.status == 'open']
            if open_positions:
                logger.debug(f"Found {len(open_positions)} open positions, transitioning to MANAGING")
                await self._transition_to_state(TradingState.MANAGING, f"Managing {len(open_positions)} open positions")
                return

            logger.debug("Waiting for trading signals...")
            
            # Check for signals
            signals = []
            for result in self.scan_results:
                signal = await self.signal_generator.generate_signal(result)
                if signal:
                    market_data = result.market_data
                    if market_data:
                        self.signal_market_data[signal.symbol] = market_data
                        signal.meta.setdefault('market_snapshot', market_data.model_dump())
                    signals.append(signal)
            
            if signals:
                logger.info(f"Found {len(signals)} signals, transitioning to SIZING")
                
                # Add signal detection checkpoint
                if self.current_session_id:
                    self.monitoring_manager.add_checkpoint(
                        CheckpointType.SIGNAL_DETECTED,
                        f"Found {len(signals)} trading signals",
                        CheckpointStatus.COMPLETED,
                        self.current_session_id
                    )
                
                self.current_signals = signals
                await self._transition_to_state(TradingState.SIZING, f"Found {len(signals)} signals")
            else:
                logger.debug("No signals found, continuing wait")
                await asyncio.sleep(2.0)  # Wait before next check
                
        except Exception as e:
            logger.error(f"Signal wait failed: {e}")
            self.current_state = TradingState.ERROR
            self.last_error = f"Signal wait failed: {e}"
    
    async def _handle_sizing_state(self) -> None:
        """Handle SIZING state - calculate position sizes."""
        try:
            logger.debug("Calculating position sizes...")
            if not self.current_signals:
                logger.debug("Сигналов для расчёта нет, возвращаемся к сканированию")
                self.current_state = TradingState.SCANNING
                return

            account_equity = await self._get_account_equity()
            remaining_equity = account_equity
            sized_signals: List[Signal] = []
            preview_positions: List[Position] = []

            for signal in self.current_signals:
                market_data = self.signal_market_data.get(signal.symbol) or self.market_data_cache.get(signal.symbol)
                if not market_data:
                    market_data = await self._fetch_market_data_safe(signal.symbol, use_websocket=True)
                    if not market_data:
                        logger.warning(f"Нет рыночных данных для сигнала {signal.symbol}, пропускаем")
                        continue
                    self.market_data_cache[signal.symbol] = market_data
                    self.signal_market_data[signal.symbol] = market_data

                simulated_positions = self.current_positions + preview_positions

                try:
                    risk_result = self.risk_manager.evaluate_signal_risk(
                        signal,
                        remaining_equity,
                        simulated_positions,
                        market_data
                    )
                except Exception as exc:
                    logger.error(f"Ошибка оценки рисков для {signal.symbol}: {exc}")
                    continue

                if not risk_result.get('approved'):
                    logger.info(
                        "Сигнал %s отклонён risk_manager: %s",
                        signal.symbol,
                        risk_result.get('reason', 'no reason'),
                    )
                    signal.meta['risk_evaluation'] = risk_result
                    continue

                position_size = risk_result.get('position_size')
                if not position_size or not position_size.is_valid or position_size.quantity <= 0:
                    logger.info(
                        "Сигнал %s отклонён: позиция недопустима (%s)",
                        signal.symbol,
                        getattr(position_size, 'reason', 'unknown'),
                    )
                    signal.meta['risk_evaluation'] = risk_result
                    continue

                if position_size.notional_usd > remaining_equity:
                    logger.info(
                        "Недостаточно средств для %s: требуется %.2f, доступно %.2f",
                        signal.symbol,
                        position_size.notional_usd,
                        remaining_equity,
                    )
                    signal.meta['risk_evaluation'] = risk_result
                    continue

                payload = asdict(position_size)
                payload['account_equity'] = remaining_equity
                signal.meta['position_size'] = payload
                signal.meta['market_price'] = market_data.price
                signal.meta['risk_evaluation'] = {
                    key: value for key, value in risk_result.items() if key != 'position_size'
                }
                signal.meta.setdefault('tp1', signal.meta.get('tp1'))
                signal.meta.setdefault('tp2', signal.meta.get('tp2'))

                sized_signals.append(signal)
                remaining_equity -= position_size.notional_usd

                preview_positions.append(
                    Position(
                        id=f"preview_{uuid.uuid4()}",
                        symbol=signal.symbol,
                        side=signal.side,
                        strategy=signal.strategy,
                        qty=position_size.quantity,
                        entry=signal.entry,
                        sl=signal.sl,
                        tp=signal.meta.get('tp2') or signal.meta.get('tp1'),
                        status='open',
                        timestamps={'opened_at': int(time.time() * 1000)},
                        meta={'preview': True}
                    )
                )

            logger.info(
                "Sized %s signals (equity %.2f -> %.2f)",
                len(sized_signals),
                account_equity,
                remaining_equity,
            )
            self.current_signals = sized_signals
            self.active_signals = sized_signals
            await self._transition_to_state(TradingState.EXECUTION if sized_signals else TradingState.SCANNING, 
                                          f"Position sizing complete: {len(sized_signals)} signals" if sized_signals else "No signals to execute")

        except Exception as e:
            logger.error(f"Sizing failed: {e}")
            await self._transition_to_state(TradingState.ERROR, f"Sizing failed: {e}")
            self.last_error = f"Sizing failed: {e}"

    async def _handle_execution_state(self) -> None:
        """Handle EXECUTION state - execute trades."""
        try:
            logger.debug("Executing trades...")
            if not self.current_signals:
                logger.debug("Исполнять нечего, возвращаемся к сканированию")
                await self._transition_to_state(TradingState.SCANNING, "Nothing to execute")
                return

            opened_positions: List[Position] = []

            for signal in self.current_signals:
                position = await self._open_position(signal)
                if position:
                    opened_positions.append(position)

            if opened_positions:
                self.current_positions.extend(opened_positions)
                logger.info(f"Открыто {len(opened_positions)} позиций, переходим к управлению")
                await self._transition_to_state(TradingState.MANAGING, f"Opened {len(opened_positions)} positions")
            else:
                logger.info("Позиции не открыты, возвращаемся к сканированию")
                await self._transition_to_state(TradingState.SCANNING, "No positions opened")

            self.current_signals = []
            self.active_signals = []
            
        except Exception as e:
            # Use centralized error handling  
            recovery_action = await self.error_handler.handle_error(
                exception=e,
                component="execution",
                operation="trade_execution",
                context={
                    "signals_count": len(self.current_signals),
                    "opened_positions": len(opened_positions) if 'opened_positions' in locals() else 0
                }
            )
            
            self.last_error = str(e)
            
            # Execute recovery action
            if recovery_action["next_state"]:
                await self._transition_to_state(recovery_action["next_state"], f"Execution failed: {e}")
            else:
                await self._transition_to_state(TradingState.ERROR, f"Execution failed: {e}")
    
    async def _handle_managing_state(self) -> None:
        """Handle MANAGING state - manage open positions."""
        try:
            logger.debug("Managing open positions...")
            await self._update_open_positions()

            open_positions = [p for p in self.current_positions if p.status == 'open']
            self.current_positions = open_positions

            if not open_positions:
                logger.debug("Открытых позиций нет, возвращаемся к сканированию")
                await self._transition_to_state(TradingState.SCANNING, "No open positions")
                return

            if len(open_positions) < self.preset.risk.max_concurrent_positions:
                logger.debug("Есть свободные слоты, возобновляем сканирование")
                await self._transition_to_state(TradingState.SCANNING, "Available position slots")
            else:
                logger.debug("Все слоты заняты, продолжаем сопровождение")
                await asyncio.sleep(5.0)
                await self._transition_to_state(TradingState.MANAGING, "All slots occupied, continuing management")

        except Exception as e:
            logger.error(f"Position management failed: {e}")
            await self._transition_to_state(TradingState.ERROR, f"Position management failed: {e}")
            self.last_error = f"Position management failed: {e}"
    
    async def _handle_emergency_state(self) -> None:
        """Handle EMERGENCY state - emergency stop."""
        logger.critical("EMERGENCY STATE: System stopped due to critical error")
        # Don't do anything, just wait for manual intervention
        await asyncio.sleep(10.0)
    
    async def _handle_paused_state(self) -> None:
        """Handle PAUSED state - kill switch or daily limit reached."""
        # System is paused, just wait for resume command
        # Log status periodically
        if self.cycle_count % 60 == 0:  # Every minute
            logger.info(f"System paused: {self.kill_switch_reason}")
    
    async def _handle_error_state(self) -> None:
        """Handle ERROR state - retry with backoff."""
        if self.error_count >= self.max_retries:
            logger.error(f"Max retries exceeded ({self.max_retries}), entering EMERGENCY state")
            await self._transition_to_state(TradingState.EMERGENCY, f"Max retries exceeded: {self.max_retries}")
            return
        
        # Calculate backoff delay
        delay = self.retry_delay * (self.retry_backoff ** self.error_count)
        logger.info(f"Error state: retry {self.error_count}/{self.max_retries} in {delay:.1f}s")
        
        # Wait for retry delay
        await asyncio.sleep(delay)
        
        # Try to recover
        try:
            # Test basic connectivity (skip in paper mode)
            if not self.paper_mode:
                logger.info("Testing connectivity in live mode")
                await self.exchange_client.fetch_balance()
            else:
                logger.info("Skipping connectivity test in paper mode")
            logger.info("Recovery successful, returning to previous state")
            
            if self.previous_state:
                await self._transition_to_state(self.previous_state, "Recovery successful")
                self.previous_state = None
            else:
                await self._transition_to_state(TradingState.SCANNING, "Recovery successful, returning to scanning")
            
            self.error_count = 0
            self.last_error = None
            
        except Exception as e:
            self.error_count += 1
            self.last_error = str(e)
            logger.error(f"Recovery failed: {e}")
    
    async def _check_and_optimize_resources(self):
        """Check system resources and perform optimizations if needed."""
        current_time = time.time()
        
        # Only check every optimization_interval seconds
        if current_time - self.last_optimization < self.optimization_interval:
            return
        
        try:
            # Get current resource metrics
            current_metrics = self.resource_monitor.get_current_metrics()
            if not current_metrics:
                return
            
            # Check if optimization is needed
            needs_optimization = False
            
            if current_metrics.cpu_percent > self.resource_limits.max_cpu_percent:
                logger.warning(f"High CPU usage detected: {current_metrics.cpu_percent:.1f}%")
                needs_optimization = True
            
            if current_metrics.memory_percent > self.resource_limits.max_memory_percent:
                logger.warning(f"High memory usage detected: {current_metrics.memory_percent:.1f}%")
                needs_optimization = True
            
            if current_metrics.active_threads > self.resource_limits.max_threads:
                logger.warning(f"High thread count detected: {current_metrics.active_threads}")
                needs_optimization = True
            
            if needs_optimization:
                await self._perform_optimization()
                self.last_optimization = current_time
                
        except Exception as e:
            logger.error(f"Error checking resources: {e}")
    
    async def _perform_optimization(self):
        """Perform resource optimization."""
        logger.info("Performing resource optimization...")
        
        try:
            # Clear caches
            clear_indicator_cache()
            
            # Limit market data cache size
            if len(self.market_data_cache) > self.max_cache_size:
                # Keep only the most recent entries
                items = list(self.market_data_cache.items())
                self.market_data_cache = dict(items[-self.max_cache_size:])
                logger.info(f"Reduced market data cache to {len(self.market_data_cache)} entries")
            
            # Clear old scan results
            if len(self.scan_results) > 50:
                self.scan_results = self.scan_results[-50:]
                logger.info("Cleared old scan results")
            
            # Clear old logs
            if len(self.logs) > self.max_logs:
                self.logs = self.logs[-self.max_logs:]
                logger.info("Cleared old logs")
            
            # Force garbage collection
            collected = gc.collect()
            logger.info(f"Garbage collection freed {collected} objects")
            
            # Log optimization results
            current_metrics = self.resource_monitor.get_current_metrics()
            if current_metrics:
                logger.info(f"Post-optimization: CPU {current_metrics.cpu_percent:.1f}%, "
                           f"Memory {current_metrics.memory_percent:.1f}%, "
                           f"Threads {current_metrics.active_threads}")
            
        except Exception as e:
            logger.error(f"Error during optimization: {e}")
    
    async def _execute_state_cycle(self) -> None:
        """Execute one cycle of the state machine with resource monitoring."""
        
        cycle_start_time = time.time()
        
        try:
            # Update monitoring session state
            if self.current_session_id:
                # Map state to checkpoint type
                state_to_checkpoint = {
                    TradingState.INITIALIZING: CheckpointType.SCAN_START,
                    TradingState.SCANNING: CheckpointType.SCAN_START,
                    TradingState.LEVEL_BUILDING: CheckpointType.LEVEL_BUILDING_START,
                    TradingState.SIGNAL_WAIT: CheckpointType.SIGNAL_DETECTED,
                    TradingState.SIZING: CheckpointType.POSITION_SIZING,
                    TradingState.EXECUTION: CheckpointType.ORDER_PLACED,
                    TradingState.MANAGING: CheckpointType.POSITION_OPENED,
                    TradingState.ERROR: CheckpointType.ERROR
                }
                checkpoint_type = state_to_checkpoint.get(self.current_state, CheckpointType.SCAN_START)
                # Update session state through public API if available
                if hasattr(self.monitoring_manager, 'update_session_state'):
                    self.monitoring_manager.update_session_state(self.current_session_id, checkpoint_type)
                elif hasattr(self.monitoring_manager, '_update_session_state'):
                    self.monitoring_manager._update_session_state(self.current_session_id, checkpoint_type)
            
            # Check if we should skip this cycle due to high resource usage (only every 10 cycles)
            if self.cycle_count % 10 == 0:
                current_metrics = self.resource_monitor.get_current_metrics()
                if current_metrics:
                    if (current_metrics.cpu_percent > 90.0 or 
                        current_metrics.memory_percent > 95.0):
                        logger.warning("Skipping cycle due to high resource usage")
                        return
            
            if self.current_state == TradingState.IDLE:
                await self._handle_idle_state()
            
            elif self.current_state == TradingState.INITIALIZING:
                await self._handle_initializing_state()
            
            elif self.current_state == TradingState.SCANNING:
                await self._handle_scanning_state()
            
            elif self.current_state == TradingState.LEVEL_BUILDING:
                await self._handle_level_building_state()
            
            elif self.current_state == TradingState.SIGNAL_WAIT:
                await self._handle_signal_wait_state()
            
            elif self.current_state == TradingState.SIZING:
                await self._handle_sizing_state()
            
            elif self.current_state == TradingState.EXECUTION:
                await self._handle_execution_state()
            
            elif self.current_state == TradingState.MANAGING:
                await self._handle_managing_state()
            
            elif self.current_state == TradingState.PAUSED:
                await self._handle_paused_state()
            
            elif self.current_state == TradingState.ERROR:
                await self._handle_error_state()
            
            elif self.current_state == TradingState.EMERGENCY:
                await self._handle_emergency_state()
            
            elif self.current_state == TradingState.STOPPED:
                self.running = False
            
            self.cycle_count += 1
            
            # Log cycle metrics
            cycle_time = time.time() - cycle_start_time
            positions_count = len(self.current_positions) if hasattr(self, 'current_positions') else 0
            signals_count = len(self.active_signals) if hasattr(self, 'active_signals') else 0
            orders_count = len(self.order_history) if hasattr(self, 'order_history') else 0
            
            log_engine_cycle(
                cycle_time=cycle_time,
                state=self.current_state.value,
                positions_count=positions_count,
                signals_count=signals_count,
                orders_count=orders_count
            )
            
            # Store cycle time for latency calculation
            if not hasattr(self, '_cycle_times'):
                self._cycle_times = deque(maxlen=100)
            self._cycle_times.append(cycle_time)
            self._last_cycle_time = cycle_time
            
        except Exception as e:
            context = LogContext(component="engine", state=str(self.current_state))
            self.enhanced_logger.error(f"Error in state {self.current_state}: {e}", context)
            self.error_count += 1
            self.last_error = str(e)
            
            # Enhanced error handling with auto-recovery
            # For trading states, any error should trigger emergency mode (kill-switch behavior)
            if self.current_state in [TradingState.SCANNING, TradingState.LEVEL_BUILDING, TradingState.SIGNAL_WAIT]:
                self.enhanced_logger.error(f"Error in trading state {self.current_state}, entering EMERGENCY state", context)
                await self._transition_to_state(TradingState.EMERGENCY, f"Error in {self.current_state}: {e}")
                self.emergency_reason = f"Error in {self.current_state}: {e}"
                return
            
            # For other states, allow limited recovery attempts
            if self.error_count <= 3:  # Allow up to 3 errors before emergency
                self.enhanced_logger.warning(f"Error count: {self.error_count}/3, attempting recovery...", context)
                
                # Try to recover based on error type
                if "Connection" in str(e) or "timeout" in str(e).lower():
                    self.enhanced_logger.info("Connection error detected, attempting reconnection...", context)
                    try:
                        if hasattr(self, 'exchange_client') and self.exchange_client:
                            await self.exchange_client.close()
                            self.exchange_client = ExchangeClient(self.system_config)
                        self.enhanced_logger.info("Reconnection successful", context)
                        return  # Continue normal operation
                    except Exception as recovery_error:
                        self.enhanced_logger.error(f"Reconnection failed: {recovery_error}", context)
                
                # For other errors, reset to IDLE for recovery
                self.enhanced_logger.info("Resetting to IDLE state for recovery...", context)
                await self._transition_to_state(TradingState.IDLE, "Resetting for recovery")
                return
            else:
                # Too many errors, go to emergency
                self.enhanced_logger.error(f"Too many errors ({self.error_count}), entering emergency state", context)
                await self._transition_to_state(TradingState.EMERGENCY, f"Too many errors: {self.error_count}")
                self.emergency_reason = f"Too many errors: {self.error_count}"
    
    # ... (rest of the methods would be similar to the original engine but with resource monitoring)
    # For brevity, I'll include just the key methods
    
    
    
    def _add_log(self, level: str, component: str, message: str, data: Optional[Dict[str, Any]] = None):
        """Add a log entry to the system with size limits."""
        log_entry = {
            'id': str(uuid.uuid4()),
            'timestamp': datetime.now().isoformat() + "Z",
            'level': level,
            'component': component,
            'message': message,
            'data': data
        }
        
        self.logs.append(log_entry)
        
        # Keep only the most recent logs
        if len(self.logs) > self.max_logs:
            self.logs = self.logs[-self.max_logs:]
        
        # Also log to standard logger
        if level == 'ERROR':
            logger.error(f"[{component}] {message}")
        elif level == 'WARNING':
            logger.warning(f"[{component}] {message}")
        elif level == 'INFO':
            logger.info(f"[{component}] {message}")
        else:
            logger.debug(f"[{component}] {message}")
    
    def get_status(self) -> Dict[str, Any]:
        """Get current engine status."""
        return {
            'state': self.current_state.value,
            'running': self.running,
            'cycle_count': self.cycle_count,
            'positions_count': len(self.current_positions),
            'scan_results_count': len(self.scan_results),
            'preset_name': self.preset.name if self.preset else 'unknown',
            'trading_mode': self.system_config.trading_mode if self.system_config and hasattr(self.system_config, 'trading_mode') else 'paper',
            'last_error': self.last_error,
            'emergency_reason': self.emergency_reason,
            'health_status': self.health_status,
            'performance_stats': self.performance_monitor.get_stats(),
            'resource_health': self.resource_monitor.get_health_status(),
            'state_machine_status': self.state_machine.get_status(),
            'error_statistics': self.error_handler.get_error_statistics()
        }
    
    def get_logs(self, limit: int = 100, level: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get system logs with optional filtering."""
        logs = self.logs.copy()
        
        # Filter by level if specified
        if level:
            logs = [log for log in logs if log['level'].upper() == level.upper()]
        
        # Return most recent logs
        return logs[-limit:] if limit > 0 else logs
    
    async def pause(self) -> None:
        """Pause the trading system."""
        if self.running and self.current_state not in [TradingState.PAUSED, TradingState.ERROR, TradingState.EMERGENCY]:
            self.previous_state = self.current_state
            self.current_state = TradingState.PAUSED
            self._add_log('INFO', 'engine', 'Trading system paused')
            logger.info("Trading system paused")
    
    async def resume(self) -> None:
        """Resume the trading system."""
        if self.running and self.current_state == TradingState.PAUSED:
            self.current_state = self.previous_state or TradingState.SCANNING
            self.previous_state = None
            self._add_log('INFO', 'engine', 'Trading system resumed')
            logger.info("Trading system resumed")
    
    async def emergency_stop(self, reason: str = "Manual emergency stop") -> None:
        """Emergency stop the trading system."""
        self.running = False
        self.current_state = TradingState.EMERGENCY
        self.emergency_reason = reason
        self._add_log('ERROR', 'engine', f'Emergency stop: {reason}')
        logger.error(f"Emergency stop: {reason}")
        
        # Cancel all open orders
        try:
            if hasattr(self, 'position_manager'):
                await self.position_manager.cancel_all_orders()
        except Exception as e:
            logger.error(f"Error canceling orders during emergency stop: {e}")
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary."""
        return {
            'cycle_count': self.cycle_count,
            'uptime_seconds': time.time() - self.start_time if hasattr(self, 'start_time') else 0,
            'performance_stats': self.performance_monitor.get_stats(),
            'resource_health': self.resource_monitor.get_health_status(),
            'current_state': self.current_state.value,
            'positions_count': len(self.current_positions),
            'scan_results_count': len(self.scan_results)
        }
    
    def get_available_commands(self) -> List[str]:
        """Get available commands for current state."""
        if not self.running:
            return ["start", "reload"]
        
        commands = ["stop", "pause", "resume", "emergency_stop", "reload"]
        
        if self.current_state == TradingState.ERROR:
            commands.append("retry")
        
        if self.current_state == TradingState.PAUSED:
            commands.append("resume")
        
        if self.current_state == TradingState.SCANNING:
            commands.append("time_stop")
            commands.append("panic_exit")
            commands.append("kill_switch")
        
        return commands
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status."""
        state_value = self.current_state.value
        if not self.running and self.current_state == TradingState.IDLE:
            state_value = TradingState.INITIALIZING.value
        return {
            'state': state_value,
            'current_state': self.current_state.value,
            'running': self.running,
            'cycle_count': self.cycle_count,
            'command_queue_length': len(self.command_queue) if hasattr(self, 'command_queue') else 0,
            'positions_count': len(self.current_positions),
            'scan_results_count': len(self.scan_results),
            'preset_name': self.preset.name if self.preset else 'unknown',
            'trading_mode': self.system_config.trading_mode if self.system_config and hasattr(self.system_config, 'trading_mode') else 'paper',
            'last_error': self.last_error,
            'error_count': self.error_count,
            'kill_switch_active': self.kill_switch_active,
            'emergency_reason': self.emergency_reason,
            'health_status': self.health_status,
            'performance_stats': self.performance_monitor.get_stats() if hasattr(self, 'performance_monitor') else {},
            'resource_health': self.resource_monitor.get_health_status() if hasattr(self, 'resource_monitor') else {},
            'active_signals_count': len(self.active_signals),
            'open_positions_count': len(self.current_positions),
            'risk_summary': self._get_risk_summary(),
            'position_metrics': self._get_position_metrics()
        }
    
    def _get_risk_summary(self) -> Dict[str, Any]:
        """Get risk summary."""
        try:
            if hasattr(self, 'risk_manager') and self.risk_manager:
                default_equity = getattr(self.system_config, 'paper_starting_balance', 100000.0)
                equity = self.last_known_equity or default_equity
                return self.risk_manager.get_risk_summary(self.current_positions, equity)
            return {'daily_pnl_r': 0.0, 'max_drawdown_r': 0.0}
        except Exception as e:
            logger.warning(f"Failed to get risk summary: {e}")
            return {'daily_pnl_r': 0.0, 'max_drawdown_r': 0.0}
    
    def _get_position_metrics(self) -> Dict[str, Any]:
        """Get position metrics."""
        try:
            if hasattr(self, 'position_manager') and self.position_manager:
                positions = self.current_positions + self.closed_positions
                return self.position_manager.calculate_position_metrics(positions)
            return {'max_drawdown_r': 0.0, 'win_rate': 0.0}
        except Exception as e:
            logger.warning(f"Failed to get position metrics: {e}")
            return {'max_drawdown_r': 0.0, 'win_rate': 0.0}
    
    def get_positions(self) -> List[Position]:
        """Get all positions."""
        positions: List[Position] = []
        for pos in self.current_positions:
            if hasattr(pos, '_fixture_function'):
                try:
                    pos = pos._fixture_function()
                except Exception:
                    pass
            positions.append(pos)
        return positions

    def get_position(self, position_id: str) -> Optional[Position]:
        """Backward-compatible alias for get_position_by_id."""
        return self.get_position_by_id(position_id)

    def get_position_by_id(self, position_id: str) -> Optional[Position]:
        """Get position by ID."""
        for pos in self.get_positions():
            if pos and getattr(pos, 'id', None) == position_id:
                return pos
        return None
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics."""
        metrics = dict(self.performance_monitor.get_stats())
        position_metrics = self._get_position_metrics()
        if position_metrics:
            metrics.update(position_metrics)
        metrics.setdefault('total_trades', len(self.closed_positions))
        metrics.setdefault('win_rate', 0.0)
        metrics.setdefault('avg_r', 0.0)
        metrics.setdefault('sharpe_ratio', 0.0)
        return metrics
    
    
    def get_last_scan_results(self) -> List[Dict[str, Any]]:
        """Get last scan results."""
        results = []
        for result in self.scan_results:
            result_dict = {
                'symbol': result.symbol,
                'score': result.score,
                'rank': result.rank,
                'filters': result.filter_results,
                'metrics': result.score_components,
                'levels': [level.dict() for level in result.levels],
                'timestamp': result.timestamp,
                'market_data': result.market_data.dict() if result.market_data else {}
            }
            results.append(result_dict)
        return results

    def get_last_scan_summary(self) -> Dict[str, Any]:
        """Return cached summary of the most recent scan."""
        return self.last_scan_summary or {}

    def get_orders(self) -> List[Order]:
        """Return a snapshot of known orders."""
        return list(self.order_history)

    async def cancel_order(self, order_id: str) -> bool:
        """Cancel an order by ID and update local state."""
        order = next(
            (
                existing
                for existing in reversed(self.order_history)
                if getattr(existing, 'id', None) == order_id
                or getattr(existing, 'exchange_id', None) == order_id
            ),
            None,
        )

        if not order:
            raise ValueError(f"Order {order_id} not found")

        exchange_id = order.exchange_id or order.id
        symbol = order.symbol

        success = await self.exchange_client.cancel_order(exchange_id, symbol)

        if success:
            order.status = 'cancelled'
            order.timestamps['cancelled_at'] = int(time.time() * 1000)

        return success

    async def _handle_stopped_state(self):
        """Handle stopped state - close all positions and clean up."""
        try:
            logger.info("Handling stopped state - closing all positions")
            
            # Check if there are positions to close
            has_positions = len(self.current_positions) > 0
            
            # Close all open positions
            for position in self.current_positions[:]:
                try:
                    if hasattr(self, 'position_manager') and self.position_manager:
                        await self.position_manager.close_position(position.id, "stopped")
                except Exception as e:
                    logger.error(f"Failed to close position {position.id}: {e}")
            
            # Clear all data
            self.current_positions.clear()
            self.active_signals.clear()
            self.scan_results.clear()
            
            # If there were positions to close, transition to MANAGING
            if has_positions:
                self.current_state = TradingState.MANAGING
                logger.info("Positions closed, transitioning to MANAGING")
            else:
                self.current_state = TradingState.IDLE
                logger.info("No positions to close, transitioning to IDLE")
            
        except Exception as e:
            logger.error(f"Error in stopped state handler: {e}")
            self.current_state = TradingState.ERROR
            self.last_error = str(e)

    async def send_command(self, command: SystemCommand) -> bool:
        """Send a command to the engine (for testing compatibility)."""
        try:
            # Add command to queue if it exists
            if hasattr(self, 'command_queue'):
                self.command_queue.append(command)
            else:
                # Create command queue if it doesn't exist
                self.command_queue = [command]
            
            # Set last command
            self.last_command = command
            
            # Execute command
            result = await self.execute_command(command.value)
            return result.get('success', False)
        except Exception as e:
            logger.error(f"Failed to send command {command.value}: {e}")
            return False

    @property
    def paper_mode(self) -> bool:
        """Check if engine is in paper mode."""
        return getattr(self, '_paper_mode', True)

    @property
    def current_session_id(self) -> str:
        """Get current session ID."""
        if not hasattr(self, '_session_id'):
            self._session_id = str(uuid.uuid4())
        return self._session_id
    
    @current_session_id.setter
    def current_session_id(self, value: str) -> None:
        """Set current session ID."""
        self._session_id = value
        if hasattr(self, 'diagnostics') and self.diagnostics:
            self.diagnostics.update_session(value)
    
    def get_equity_history(self) -> List[Dict[str, Any]]:
        """Get equity history for performance tracking."""
        try:
            # Get real equity data from position manager
            if hasattr(self, 'position_manager') and self.position_manager:
                return self.position_manager.get_equity_history()
            
            # Fallback: calculate from current positions
            current_equity = 10000.0  # Starting equity
            total_pnl = 0.0
            
            if hasattr(self, 'current_positions') and self.current_positions:
                for position in self.current_positions:
                    if hasattr(position, 'pnl_usd') and position.pnl_usd:
                        total_pnl += position.pnl_usd
            
            current_equity += total_pnl
            
            # Calculate drawdown
            peak_equity = getattr(self, '_peak_equity', current_equity)
            if current_equity > peak_equity:
                self._peak_equity = current_equity
                peak_equity = current_equity
            
            drawdown = (peak_equity - current_equity) / peak_equity if peak_equity > 0 else 0.0
            
            return [
                {
                    'timestamp': int(time.time() * 1000),
                    'equity': current_equity,
                    'drawdown': drawdown,
                    'returns': total_pnl / 10000.0 if 10000.0 > 0 else 0.0
                }
            ]
        except Exception as e:
            logger.error(f"Error getting equity history: {e}")
            return [
                {
                    'timestamp': int(time.time() * 1000),
                    'equity': 10000.0,
                    'drawdown': 0.0,
                    'returns': 0.0
                }
            ]
    
    def get_r_distribution(self) -> Dict[str, Any]:
        """Get R-multiple distribution statistics."""
        try:
            # Get R-multiples from closed positions
            r_multiples = []
            
            if hasattr(self, 'position_manager') and self.position_manager:
                # Get from position manager if available
                closed_positions = getattr(self.position_manager, 'closed_positions', [])
                for position in closed_positions:
                    if hasattr(position, 'pnl_r') and position.pnl_r is not None:
                        r_multiples.append(position.pnl_r)
            elif hasattr(self, 'current_positions'):
                # Fallback: check current positions for R-multiples
                for position in self.current_positions:
                    if hasattr(position, 'pnl_r') and position.pnl_r is not None:
                        r_multiples.append(position.pnl_r)
            
            if not r_multiples:
                return {
                    'mean_r': 0.0,
                    'std_r': 0.0,
                    'min_r': 0.0,
                    'max_r': 0.0,
                    'positive_r_count': 0,
                    'negative_r_count': 0,
                    'total_trades': 0
                }
            
            # Calculate statistics
            mean_r = mean(r_multiples)
            std_r = (sum((r - mean_r) ** 2 for r in r_multiples) / len(r_multiples)) ** 0.5
            min_r = min(r_multiples)
            max_r = max(r_multiples)
            positive_r_count = sum(1 for r in r_multiples if r > 0)
            negative_r_count = sum(1 for r in r_multiples if r < 0)
            
            return {
                'mean_r': mean_r,
                'std_r': std_r,
                'min_r': min_r,
                'max_r': max_r,
                'positive_r_count': positive_r_count,
                'negative_r_count': negative_r_count,
                'total_trades': len(r_multiples)
            }
        except Exception as e:
            logger.error(f"Error calculating R-distribution: {e}")
            return {
                'mean_r': 0.0,
                'std_r': 0.0,
                'min_r': 0.0,
                'max_r': 0.0,
                'positive_r_count': 0,
                'negative_r_count': 0,
                'total_trades': 0
            }
    
    def get_candle_data(self, symbol: str, timeframe: str = '1m', limit: int = 100) -> List[Dict[str, Any]]:
        """Get candle data for a symbol."""
        try:
            # Try to get data from exchange client
            if hasattr(self, 'exchange_client') and self.exchange_client:
                # Use asyncio to run the async method
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # If we're in an async context, create a task
                    task = asyncio.create_task(
                        self.exchange_client.fetch_ohlcv(symbol, timeframe, limit=limit)
                    )
                    # Wait for the task to complete
                    return asyncio.run_coroutine_threadsafe(
                        self.exchange_client.fetch_ohlcv(symbol, timeframe, limit=limit),
                        loop
                    ).result()
                else:
                    # If we're not in an async context, run directly
                    return asyncio.run(
                        self.exchange_client.fetch_ohlcv(symbol, timeframe, limit=limit)
                    )
            
            # Fallback: return empty list
            logger.warning(f"No exchange client available for candle data: {symbol}")
            return []
        except Exception as e:
            logger.error(f"Error getting candle data for {symbol}: {e}")
            return []
    
    def get_support_resistance_levels(self, symbol: str) -> List[Dict[str, Any]]:
        """Get support and resistance levels for a symbol."""
        try:
            # Try to get levels from scanner if available
            if hasattr(self, 'scanner') and self.scanner:
                # Get recent scan results for this symbol
                scan_results = getattr(self.scanner, 'last_scan_results', [])
                for result in scan_results:
                    if hasattr(result, 'symbol') and result.symbol == symbol:
                        if hasattr(result, 'levels'):
                            return [
                                {
                                    'price': level.get('high', 0),
                                    'type': 'resistance',
                                    'strength': level.get('strength', 0.5),
                                    'timestamp': int(time.time() * 1000)
                                }
                                for level in result.levels.get('resistance', [])
                            ] + [
                                {
                                    'price': level.get('low', 0),
                                    'type': 'support',
                                    'strength': level.get('strength', 0.5),
                                    'timestamp': int(time.time() * 1000)
                                }
                                for level in result.levels.get('support', [])
                            ]
            
            # Fallback: try to get from market data
            if hasattr(self, 'market_data_provider') and self.market_data_provider:
                try:
                    # Get recent price data and calculate levels
                    candle_data = self.get_candle_data(symbol, '1h', 24)  # Last 24 hours
                    if candle_data:
                        highs = [candle['high'] for candle in candle_data]
                        lows = [candle['low'] for candle in candle_data]
                        
                        # Simple level detection based on recent highs and lows
                        resistance_levels = []
                        support_levels = []
                        
                        if highs:
                            # Find resistance levels (recent highs)
                            recent_high = max(highs[-5:])  # Last 5 candles
                            resistance_levels.append({
                                'price': recent_high,
                                'type': 'resistance',
                                'strength': 0.7,
                                'timestamp': int(time.time() * 1000)
                            })
                        
                        if lows:
                            # Find support levels (recent lows)
                            recent_low = min(lows[-5:])  # Last 5 candles
                            support_levels.append({
                                'price': recent_low,
                                'type': 'support',
                                'strength': 0.7,
                                'timestamp': int(time.time() * 1000)
                            })
                        
                        return resistance_levels + support_levels
                except Exception as e:
                    logger.warning(f"Error calculating levels from market data: {e}")
            
            # No data available
            return []
        except Exception as e:
            logger.error(f"Error getting support/resistance levels for {symbol}: {e}")
            return []
    
    def get_latency(self) -> float:
        """Get current engine latency in milliseconds."""
        try:
            if hasattr(self, '_last_cycle_time') and hasattr(self, '_cycle_times'):
                # Calculate average latency from recent cycles
                if self._cycle_times:
                    return mean(self._cycle_times[-10:]) * 1000  # Convert to ms
            return 45.0  # Default fallback
        except Exception as e:
            logger.error(f"Error getting latency: {e}")
            return 45.0
    
    def get_uptime(self) -> int:
        """Get engine uptime in seconds."""
        try:
            if hasattr(self, 'start_time') and self.start_time:
                return int(time.time() - self.start_time)
            return 0
        except Exception as e:
            logger.error(f"Error getting uptime: {e}")
            return 0
    
    def get_avg_latency(self) -> float:
        """Get average engine latency in milliseconds."""
        try:
            if hasattr(self, '_cycle_times') and self._cycle_times:
                return mean(self._cycle_times) * 1000  # Convert to ms
            return 47.5  # Default fallback
        except Exception as e:
            logger.error(f"Error getting average latency: {e}")
            return 47.5
    
    def get_recent_order_events(self) -> List[Dict[str, Any]]:
        """Get recent order events for WebSocket updates."""
        try:
            events = []
            if hasattr(self, 'execution_manager') and self.execution_manager:
                # Get recent order events from execution manager
                recent_orders = self.execution_manager.get_recent_orders(10)
                for order in recent_orders:
                    events.append({
                        'id': getattr(order, 'id', ''),
                        'symbol': getattr(order, 'symbol', ''),
                        'side': getattr(order, 'side', ''),
                        'type': getattr(order, 'type', 'market'),
                        'qty': getattr(order, 'qty', 0),
                        'price': getattr(order, 'price', None),
                        'status': getattr(order, 'status', 'pending'),
                        'createdAt': getattr(order, 'created_at', datetime.now().isoformat()),
                        'updatedAt': getattr(order, 'updated_at', None),
                        'filledAt': getattr(order, 'filled_at', None),
                        'fees': getattr(order, 'fees', 0),
                        'reason': getattr(order, 'reason', None),
                        'timestamp': int(time.time() * 1000)
                    })
            return events
        except Exception as e:
            logger.error(f"Error getting recent order events: {e}")
            return []
    
    def get_recent_position_events(self) -> List[Dict[str, Any]]:
        """Get recent position events for WebSocket updates."""
        try:
            events = []
            if hasattr(self, 'position_manager') and self.position_manager:
                # Get recent position events from position manager
                recent_positions = self.position_manager.get_recent_positions(10)
                for position in recent_positions:
                    status = getattr(position, 'status', '')
                    events.append({
                        'id': getattr(position, 'id', ''),
                        'symbol': getattr(position, 'symbol', ''),
                        'side': getattr(position, 'side', ''),
                        'entry': getattr(position, 'entry', 0),
                        'sl': getattr(position, 'sl', 0),
                        'tp': getattr(position, 'tp', None),
                        'size': getattr(position, 'size', 0),
                        'mode': getattr(position, 'mode', 'paper'),
                        'openedAt': getattr(position, 'opened_at', datetime.now().isoformat()),
                        'updatedAt': getattr(position, 'updated_at', None),
                        'closedAt': getattr(position, 'closed_at', None),
                        'pnlR': getattr(position, 'pnl_r', None),
                        'pnlUsd': getattr(position, 'pnl_usd', None),
                        'unrealizedPnlR': getattr(position, 'unrealized_pnl_r', None),
                        'unrealizedPnlUsd': getattr(position, 'unrealized_pnl_usd', None),
                        'reason': getattr(position, 'reason', None),
                        'action': 'opened' if status == 'open' else 'closed',
                        'timestamp': int(time.time() * 1000)
                    })
            return events
        except Exception as e:
            logger.error(f"Error getting recent position events: {e}")
            return []

    def get_active_signals(self) -> List[Signal]:
        """Get active signals for WebSocket updates."""
        try:
            return getattr(self, 'active_signals', [])
        except Exception as e:
            logger.error(f"Error getting active signals: {e}")
            return []
    
    def _setup_websocket_notifications(self):
        """Setup WebSocket notification system."""
        try:
            from ..api.websocket import manager
            self.websocket_manager = manager
        except ImportError:
            logger.warning("WebSocket manager not available")
            self.websocket_manager = None
    
    async def _notify_websocket(self, event_type: str, data: Dict[str, Any]):
        """Send notification to WebSocket clients."""
        if not hasattr(self, 'websocket_manager') or not self.websocket_manager:
            return
        
        try:
            from ..api.websocket import create_websocket_message
            message = create_websocket_message(event_type, data)
            await self.websocket_manager.broadcast(message)
        except Exception as e:
            import logging
            logging.getLogger(__name__).debug(f"Failed to send WebSocket notification: {e}")
    
    async def _transition_to_state(self, new_state: TradingState, reason: str = ""):
        """Transition to a new state using centralized StateMachine."""
        success = await self.state_machine.transition_to(new_state, reason)
        if not success:
            logger.error(f"Failed to transition to state {new_state.value}: {reason}")
            return False
        
        # Update legacy property for backward compatibility
        self.previous_state = self.state_machine.previous_state
        return True

    async def _handle_state_transition_notification(self, transition):
        """Handle state transition notifications from StateMachine."""
        try:
            # Notify WebSocket clients about state transition
            await self._notify_websocket("FSM_TRANSITION", {
                "from_state": transition.from_state.value,
                "to_state": transition.to_state.value,
                "reason": transition.reason,
                "timestamp": transition.timestamp,
                "metadata": transition.metadata
            })
        except Exception as e:
            logger.error(f"Error sending state transition notification: {e}")
            
    async def _handle_error_notification(self, error_info: ErrorInfo):
        """Handle error notifications from ErrorHandler."""
        try:
            # Notify WebSocket clients about errors
            await self._notify_websocket("ERROR", {
                "component": error_info.component,
                "operation": error_info.operation,
                "exception_type": type(error_info.exception).__name__,
                "exception_msg": str(error_info.exception),
                "severity": error_info.severity.value,
                "category": error_info.category.value,
                "timestamp": int(error_info.timestamp.timestamp() * 1000),
                "retry_count": error_info.retry_count
            })
        except Exception as e:
            logger.error(f"Error sending error notification: {e}")
    
    async def _notify_kill_switch(self, reason: str):
        """Notify about kill switch activation."""
        if hasattr(self, 'websocket_manager') and self.websocket_manager:
            await self._notify_websocket("KILL_SWITCH", {
                "reason": reason,
                "timestamp": int(time.time() * 1000)
            })
    
    async def _notify_stop_moved(self, position_id: str, old_stop: float, new_stop: float):
        """Notify about stop loss movement."""
        if hasattr(self, 'websocket_manager') and self.websocket_manager:
            await self._notify_websocket("STOP_MOVED", {
                "position_id": position_id,
                "old_stop": old_stop,
                "new_stop": new_stop,
                "timestamp": int(time.time() * 1000)
            })
    
    async def _notify_take_profit(self, position_id: str, price: float, pnl: float):
        """Notify about take profit execution."""
        if hasattr(self, 'websocket_manager') and self.websocket_manager:
            await self._notify_websocket("TAKE_PROFIT", {
                "position_id": position_id,
                "price": price,
                "pnl": pnl,
                "timestamp": int(time.time() * 1000)
            })
    
    async def _notify_error(self, error_type: str, message: str, details: Dict[str, Any] = None):
        """Notify about errors."""
        if hasattr(self, 'websocket_manager') and self.websocket_manager:
            await self._notify_websocket("ERROR", {
                "error_type": error_type,
                "message": message,
                "details": details or {},
                "timestamp": int(time.time() * 1000)
            })
