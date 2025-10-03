"""
TradingOrchestrator - главный координатор торговых операций.

Отвечает исключительно за:
- Координацию всех торговых компонентов
- Управление торговым циклом
- Принятие решений о переходах между состояниями
- Мониторинг общего состояния торговой системы
"""

import asyncio
import logging
import time
import uuid
from typing import Dict, List, Optional, Any
from datetime import datetime

from .state_machine import StateMachine, TradingState
from .error_handler import ErrorHandler
from .scanning_manager import ScanningManager
from .signal_manager import SignalManager
from .resource_manager import ResourceManager
from ..data.models import Signal, Position, MarketData
from ..position import PositionManager
from ..position.position_manager import PositionUpdate
from ..execution.manager import ExecutionManager
from ..risk import RiskManager
from ..utils.enhanced_logger import LogContext
from ..utils.enhanced_error_handler import enhanced_error_handler, ErrorContext, ErrorCategory, ErrorSeverity, handle_critical_errors

logger = logging.getLogger(__name__)


class TradingOrchestrator:
    """Главный координатор торговой системы."""

    def __init__(self,
                 state_machine: StateMachine,
                 error_handler: ErrorHandler,
                 scanning_manager: ScanningManager,
                 signal_manager: SignalManager,
                 resource_manager: ResourceManager,
                 position_manager: PositionManager,
                 execution_manager: ExecutionManager,
                 risk_manager: RiskManager,
                 enhanced_logger,
                 monitoring_manager,
                 preset):
        """
        Инициализация TradingOrchestrator.
        
        Args:
            state_machine: Машина состояний
            error_handler: Обработчик ошибок
            scanning_manager: Менеджер сканирования
            signal_manager: Менеджер сигналов
            resource_manager: Менеджер ресурсов
            position_manager: Менеджер позиций
            execution_manager: Менеджер исполнения
            risk_manager: Менеджер рисков
            enhanced_logger: Расширенный логгер
            monitoring_manager: Менеджер мониторинга
            preset: Торговый пресет
        """
        # Core components
        self.state_machine = state_machine
        self.error_handler = error_handler
        self.scanning_manager = scanning_manager
        self.signal_manager = signal_manager
        self.resource_manager = resource_manager
        
        # Trading components  
        self.position_manager = position_manager
        self.execution_manager = execution_manager
        self.risk_manager = risk_manager
        
        # Infrastructure
        self.enhanced_logger = enhanced_logger
        self.monitoring_manager = monitoring_manager
        self.preset = preset
        
        # State
        self.current_session_id = str(uuid.uuid4())
        self.current_positions: List[Position] = []
        self.trading_cycle_count = 0
        self.last_cycle_time = 0
        
        # Configuration
        self.max_concurrent_positions = preset.risk.max_concurrent_positions
        
        logger.info("TradingOrchestrator initialized")

    async def start_trading_cycle(self, exchange_client) -> None:
        """Запустить главный торговый цикл."""
        logger.info("Starting trading orchestrator cycle...")
        
        cycle_start_time = time.time()
        self.current_session_id = str(uuid.uuid4())
        
        try:
            # Выполнить цикл в зависимости от состояния
            current_state = self.state_machine.current_state
            
            if current_state == TradingState.SCANNING:
                await self._execute_scanning_cycle(exchange_client)
                
            elif current_state == TradingState.LEVEL_BUILDING:
                await self._execute_level_building_cycle()
                
            elif current_state == TradingState.SIGNAL_WAIT:
                await self._execute_signal_wait_cycle()
                
            elif current_state == TradingState.SIZING:
                await self._execute_sizing_cycle()
                
            elif current_state == TradingState.EXECUTION:
                await self._execute_execution_cycle()
                
            elif current_state == TradingState.MANAGING:
                await self._execute_managing_cycle()
                
            self.trading_cycle_count += 1
            self.last_cycle_time = time.time() - cycle_start_time
            
            # Записать успешное выполнение для Circuit Breaker
            self.error_handler.record_success("orchestrator", "trading_cycle")
            
        except Exception as e:
            # ✅ IMPROVED: Enhanced error handling for trading cycle
            context = ErrorContext(
                category=enhanced_error_handler.classify_error(e),
                severity=ErrorSeverity.HIGH,
                operation="trading_cycle",
                component="orchestrator",
                max_retries=2,
                metadata={
                    "state": current_state.value,
                    "session_id": self.current_session_id,
                    "cycle_count": self.trading_cycle_count
                }
            )
            enhanced_error_handler._log_error(e, context)
            
            # Обработать ошибку централизованно (fallback)
            recovery_action = await self.error_handler.handle_error(
                exception=e,
                component="orchestrator", 
                operation="trading_cycle",
                context={
                    "state": current_state.value,
                    "session_id": self.current_session_id,
                    "cycle_count": self.trading_cycle_count
                }
            )
            
            # Выполнить восстановление
            await self._execute_recovery_action(recovery_action)

    async def _execute_scanning_cycle(self, exchange_client) -> None:
        """Выполнить цикл сканирования рынков."""
        context = LogContext(
            component="orchestrator",
            state="SCANNING",
            session_id=self.current_session_id
        )
        
        self.enhanced_logger.info("Executing scanning cycle...", context)
        
        try:
            # Сканировать рынки
            scan_results = await self.scanning_manager.scan_markets(
                exchange_client, 
                self.current_session_id
            )
            
            # Переход к следующему состоянию
            if scan_results:
                self.enhanced_logger.info(
                    f"Scan complete: {len(scan_results)} candidates found, transitioning to LEVEL_BUILDING",
                    context
                )
                await self.state_machine.transition_to(
                    TradingState.LEVEL_BUILDING,
                    f"Found {len(scan_results)} candidates"
                )
            else:
                self.enhanced_logger.warning("No candidates found, staying in SCANNING", context)
                # Остаемся в сканировании, но делаем паузу
                await asyncio.sleep(5.0)
                
        except Exception as e:
            raise Exception(f"Scanning cycle failed: {e}")

    async def _execute_level_building_cycle(self) -> None:
        """Выполнить цикл построения уровней."""
        context = LogContext(
            component="orchestrator", 
            state="LEVEL_BUILDING",
            session_id=self.current_session_id
        )
        
        self.enhanced_logger.info("Executing level building cycle...", context)
        
        # В текущей архитектуре уровни строятся внутри сканера
        # Здесь просто переходим к ожиданию сигналов
        self.enhanced_logger.info("Level building complete, transitioning to SIGNAL_WAIT", context)
        await self.state_machine.transition_to(
            TradingState.SIGNAL_WAIT,
            "Level building complete"
        )
        
        # Небольшая задержка для предотвращения зависания
        await asyncio.sleep(0.1)

    async def _execute_signal_wait_cycle(self) -> None:
        """Выполнить цикл ожидания сигналов."""
        context = LogContext(
            component="orchestrator",
            state="SIGNAL_WAIT", 
            session_id=self.current_session_id
        )
        
        self.enhanced_logger.debug("Executing signal wait cycle...", context)
        
        # Проверить открытые позиции - если есть, перейти к управлению
        open_positions = [p for p in self.current_positions if p.status == 'open']
        if open_positions:
            self.enhanced_logger.info(
                f"Found {len(open_positions)} open positions, transitioning to MANAGING",
                context
            )
            await self.state_machine.transition_to(
                TradingState.MANAGING,
                f"Managing {len(open_positions)} open positions"
            )
            return
        
        # Попытаться сгенерировать сигналы из последнего сканирования
        scan_results = getattr(self.scanning_manager, 'last_scan_results', [])
        
        if scan_results:
            self.enhanced_logger.info(
                f"Generating signals from {len(scan_results)} scan results...",
                context
            )
            signals = await self.signal_manager.generate_signals_from_scan(
                scan_results, 
                self.current_session_id
            )
            
            if signals:
                self.enhanced_logger.info(
                    f"Found {len(signals)} signals, transitioning to SIZING",
                    context
                )
                await self.state_machine.transition_to(
                    TradingState.SIZING,
                    f"Found {len(signals)} signals"
                )
            else:
                self.enhanced_logger.debug("No signals generated, waiting...", context)
                await asyncio.sleep(2.0)  # Ожидание перед следующей проверкой
        else:
            # Нет данных для сигналов, вернуться к сканированию
            self.enhanced_logger.warning("No scan data for signals, returning to SCANNING", context)
            await self.state_machine.transition_to(
                TradingState.SCANNING,
                "No scan data for signals"
            )

    async def _execute_sizing_cycle(self) -> None:
        """Выполнить цикл размерения позиций."""
        context = LogContext(
            component="orchestrator",
            state="SIZING",
            session_id=self.current_session_id
        )
        
        self.enhanced_logger.info("Executing sizing cycle...", context)
        
        active_signals = self.signal_manager.get_active_signals()
        if not active_signals:
            await self.state_machine.transition_to(
                TradingState.SCANNING,
                "No signals to size"
            )
            return
        
        try:
            # Оценить риски и размеры позиций
            sized_signals = []
            
            for signal in active_signals:
                # Получить рыночные данные для сигнала
                market_data = self.signal_manager.signal_market_data.get(signal.symbol)
                if not market_data:
                    continue
                    
                # Оценить риск
                equity = await self._get_current_equity()
                risk_evaluation = self.risk_manager.evaluate_signal_risk(
                    signal,
                    equity,
                    self.current_positions,
                    market_data
                )
                
                # Log risk evaluation details
                logger.info(f"Risk evaluation for {signal.symbol}: approved={risk_evaluation.get('approved')}, reason={risk_evaluation.get('reason')}, position_size={risk_evaluation.get('position_size')}")
                
                if risk_evaluation.get('approved'):
                    sized_signals.append(signal)
                    
            if sized_signals:
                await self.state_machine.transition_to(
                    TradingState.EXECUTION,
                    f"Position sizing complete: {len(sized_signals)} signals"
                )
            else:
                await self.state_machine.transition_to(
                    TradingState.SCANNING,
                    "No signals passed risk evaluation"
                )
                
        except Exception as e:
            raise Exception(f"Sizing cycle failed: {e}")
        
        # Небольшая задержка для предотвращения зависания
        await asyncio.sleep(0.1)

    async def _execute_execution_cycle(self) -> None:
        """Выполнить цикл исполнения сделок."""
        context = LogContext(
            component="orchestrator",
            state="EXECUTION",
            session_id=self.current_session_id
        )
        
        self.enhanced_logger.info("Executing execution cycle...", context)
        
        active_signals = self.signal_manager.get_active_signals()
        if not active_signals:
            await self.state_machine.transition_to(
                TradingState.SCANNING,
                "Nothing to execute"
            )
            return
        
        try:
            opened_positions = []
            
            for signal in active_signals:
                position = await self._open_position_from_signal(signal)
                if position:
                    opened_positions.append(position)
                    await self.signal_manager.mark_signal_executed(signal, success=True)
                else:
                    await self.signal_manager.mark_signal_executed(signal, success=False)
                    
            if opened_positions:
                self.current_positions.extend(opened_positions)
                await self.state_machine.transition_to(
                    TradingState.MANAGING,
                    f"Opened {len(opened_positions)} positions"
                )
            else:
                await self.state_machine.transition_to(
                    TradingState.SCANNING,
                    "No positions opened"
                )
                
        except Exception as e:
            raise Exception(f"Execution cycle failed: {e}")
        
        # Небольшая задержка для предотвращения зависания
        await asyncio.sleep(0.1)

    async def _execute_managing_cycle(self) -> None:
        """Выполнить цикл управления позициями."""
        context = LogContext(
            component="orchestrator",
            state="MANAGING",
            session_id=self.current_session_id
        )
        
        self.enhanced_logger.debug("Executing managing cycle...", context)
        
        try:
            # Обновить позиции
            await self._update_open_positions()
            
            # Фильтровать только открытые позиции
            open_positions = [p for p in self.current_positions if p.status == 'open']
            self.current_positions = open_positions
            
            if not open_positions:
                await self.state_machine.transition_to(
                    TradingState.SCANNING,
                    "No open positions"
                )
                return
            
            # Проверить, есть ли свободные слоты для новых позиций
            if len(open_positions) < self.max_concurrent_positions:
                await self.state_machine.transition_to(
                    TradingState.SCANNING,
                    "Available position slots"
                )
            else:
                # Все слоты заняты, продолжаем управление
                await asyncio.sleep(5.0)
                # Остаемся в состоянии MANAGING
                
        except Exception as e:
            raise Exception(f"Managing cycle failed: {e}")

    async def _open_position_from_signal(self, signal: Signal) -> Optional[Position]:
        """Открыть позицию по сигналу."""
        try:
            # Получить рыночные данные
            market_data = self.signal_manager.signal_market_data.get(signal.symbol)
            if not market_data:
                logger.warning(f"No market data for signal {signal.symbol}")
                return None
                
            # Проверить готовый размер позиции в meta сигнала
            position_size = None
            if hasattr(signal, 'meta') and signal.meta and 'position_size' in signal.meta:
                meta_ps = signal.meta['position_size']
                if isinstance(meta_ps, dict) and 'quantity' in meta_ps:
                    # Используем готовые данные из meta
                    from ..risk.risk_manager import PositionSize
                    position_size = PositionSize(
                        quantity=meta_ps['quantity'],
                        notional_usd=meta_ps.get('notional_usd', 0),
                        risk_usd=meta_ps.get('risk_usd', 0),
                        risk_r=meta_ps.get('risk_r', 0.01),
                        stop_distance=meta_ps.get('stop_distance', 0),
                        is_valid=True,
                        reason="Pre-calculated from signal meta"
                    )
                    logger.info(f"Using pre-calculated position size for {signal.symbol}: {position_size.quantity}")
            
            if not position_size:
                # Рассчитать размер позиции через risk manager
                equity = await self._get_current_equity()
                risk_evaluation = self.risk_manager.evaluate_signal_risk(
                    signal, equity, self.current_positions, market_data
                )
                
                if not risk_evaluation.get('approved'):
                    logger.info(f"Signal {signal.symbol} rejected by risk manager")
                    return None
                    
                position_size = risk_evaluation.get('position_size')
                if not position_size:
                    logger.warning(f"No position_size returned by risk evaluation for {signal.symbol}")
                    return None
            
            # Исполнить сделку
            entry_side = 'buy' if signal.side == 'long' else 'sell'
            order = await self.execution_manager.execute_trade(
                symbol=signal.symbol,
                side=entry_side,
                total_quantity=position_size.quantity,
                market_data=market_data,
                position_size=position_size,
                intent="entry"
            )
            
            if not order or not order.filled_qty:
                logger.warning(f"Failed to execute order for {signal.symbol}")
                return None
                
            # Создать позицию
            position = Position(
                id=str(uuid.uuid4()),
                symbol=signal.symbol,
                side=signal.side,
                strategy=signal.strategy,
                qty=order.filled_qty,
                entry=order.avg_fill_price or signal.entry,
                sl=signal.sl,
                tp=None,
                status='open',
                pnl_usd=0.0,
                pnl_r=0.0,
                fees_usd=order.fees_usd,
                timestamps={'opened_at': int(time.time() * 1000)},
                meta={
                    'signal_confidence': signal.confidence,
                    'entry_order': order.model_dump() if hasattr(order, 'model_dump') else (order.__dict__ if hasattr(order, '__dict__') else str(order)),
                    'stop_distance': position_size.stop_distance,
                    'initial_qty': order.filled_qty,
                    'btc_correlation': getattr(market_data, 'btc_correlation', 0.0),
                    'notional_usd': position_size.notional_usd
                }
            )
            
            logger.info(f"Opened position {position.symbol}: {position.qty} @ {position.entry}")
            return position
            
        except Exception as e:
            logger.error(f"Error opening position from signal {signal.symbol}: {e}")
            return None

    async def _update_open_positions(self) -> None:
        """Обновить открытые позиции."""
        if not self.current_positions:
            return
            
        # Получить только открытые позиции
        open_positions = [p for p in self.current_positions if p.status == 'open']
        if not open_positions:
            return
            
        # Получить рыночные данные для всех открытых позиций
        symbols = [p.symbol for p in open_positions]
        
        try:
            # Получить актуальные рыночные данные через ScanningManager
            market_data_dict = await self.scanning_manager.market_data_provider.get_multiple_market_data(symbols)
            
            if not market_data_dict:
                logger.warning("No market data received for position updates")
                return
                
            # Обновить PnL для всех позиций
            for position in open_positions:
                if position.symbol in market_data_dict:
                    market_data = market_data_dict[position.symbol]
                    await self._calculate_position_pnl(position, market_data.price)
            
            # Обработать обновления позиций через PositionManager
            updates = await self.position_manager.process_position_updates(
                open_positions, market_data_dict
            )
            
            # Применить обновления позиций
            if updates:
                logger.info(f"Processing {len(updates)} position updates")
                await self._apply_position_updates(updates, market_data_dict)
                
        except Exception as e:
            logger.error(f"Error updating open positions: {e}")

    async def _calculate_position_pnl(self, position: Position, current_price: float) -> None:
        """Рассчитать PnL для позиции."""
        try:
            if position.side == 'long':
                # Для лонга: (текущая цена - цена входа) * количество
                price_diff = current_price - position.entry
            else:
                # Для шорта: (цена входа - текущая цена) * количество 
                price_diff = position.entry - current_price
                
            # PnL в USD
            position.pnl_usd = price_diff * position.qty
            
            # PnL в R-мультипликах
            if position.side == 'long':
                risk = position.entry - position.sl
            else:
                risk = position.sl - position.entry
                
            if risk > 0:
                position.pnl_r = (current_price - position.entry) / risk if position.side == 'long' else (position.entry - current_price) / risk
            else:
                position.pnl_r = 0.0
                
        except Exception as e:
            logger.error(f"Error calculating PnL for {position.symbol}: {e}")

    async def _apply_position_updates(self, updates: List[PositionUpdate], market_data_dict: Dict[str, MarketData]) -> None:
        """Применить обновления к позициям."""
        for update in updates:
            try:
                position = next((p for p in self.current_positions if p.id == update.position_id), None)
                if not position:
                    logger.warning(f"Position {update.position_id} not found for update")
                    continue
                    
                if update.action == 'update_stop':
                    # Обновить стоп-лосс
                    old_sl = position.sl
                    position.sl = update.price
                    logger.info(f"Updated stop loss for {position.symbol}: {old_sl} -> {position.sl}")
                    
                elif update.action == 'take_profit':
                    # Частичное закрытие на тейк-профит
                    if update.quantity and update.quantity > 0:
                        position.qty -= update.quantity
                        logger.info(f"Partial take profit for {position.symbol}: closed {update.quantity}, remaining {position.qty}")
                        
                        # Если вся позиция закрыта
                        if position.qty <= 0:
                            position.status = 'closed'
                            position.timestamps['closed_at'] = int(time.time() * 1000)
                            
                elif update.action == 'close':
                    # Полное закрытие позиции
                    position.status = 'closed'
                    position.timestamps['closed_at'] = int(time.time() * 1000)
                    logger.info(f"Closed position {position.symbol}: {update.reason}")
                    
                elif update.action == 'add_on':
                    # Добавление к позиции
                    if update.quantity and update.quantity > 0:
                        # В реальной ситуации здесь был бы ордер на увеличение позиции
                        logger.info(f"Add-on signal for {position.symbol}: {update.quantity} @ {update.price}")
                        
            except Exception as e:
                logger.error(f"Error applying position update {update.action}: {e}")

    async def _get_current_equity(self) -> float:
        """Получить текущий эквити счета.""" 
        try:
            # Получить доступ к exchange client через scanning manager
            exchange_client = getattr(self.scanning_manager, 'market_data_provider', None)
            if exchange_client and hasattr(exchange_client, 'exchange_client'):
                balance = await exchange_client.exchange_client.fetch_balance()
                
                # Получить баланс USDT (основная валюта для расчета эквити)
                usdt_balance = balance.get('USDT', 0.0)
                
                # Добавить текущую PnL от открытых позиций
                total_position_pnl = sum(p.pnl_usd for p in self.current_positions if p.status == 'open')
                
                equity = usdt_balance + total_position_pnl
                
                # Логирование для отладки
                if len([p for p in self.current_positions if p.status == 'open']) > 0:
                    logger.debug(f"Current equity: USDT balance {usdt_balance}, positions PnL {total_position_pnl}, total {equity}")
                
                return equity
                
        except Exception as e:
            logger.error(f"Error getting current equity: {e}")
            
        # Fallback - возвращаем значение по умолчанию для paper trading
        logger.warning("Using default equity value - real balance unavailable")
        return 100000.0

    async def _execute_recovery_action(self, recovery_action: Dict[str, Any]) -> None:
        """Выполнить действие восстановления после ошибки."""
        if recovery_action.get("emergency"):
            await self.state_machine.transition_to(
                TradingState.EMERGENCY,
                "Emergency recovery"
            )
        elif recovery_action.get("next_state"):
            await self.state_machine.transition_to(
                recovery_action["next_state"],
                "Error recovery"
            )
        elif recovery_action.get("should_retry") and recovery_action.get("delay", 0) > 0:
            await asyncio.sleep(recovery_action["delay"])
            # Остаемся в текущем состоянии для повтора

    def get_status(self) -> Dict[str, Any]:
        """Получить статус TradingOrchestrator."""
        return {
            "current_state": self.state_machine.current_state.value,
            "session_id": self.current_session_id,
            "cycle_count": self.trading_cycle_count,
            "last_cycle_time_ms": int(self.last_cycle_time * 1000),
            "positions_count": len(self.current_positions),
            "max_concurrent_positions": self.max_concurrent_positions,
            
            # Статус компонентов
            "state_machine": self.state_machine.get_status(),
            "scanning_manager": self.scanning_manager.get_status(),
            "signal_manager": self.signal_manager.get_status(),
            "resource_manager": self.resource_manager.get_status(),
            "error_handler": self.error_handler.get_error_statistics()
        }

    def get_positions(self) -> List[Position]:
        """Получить текущие позиции."""
        return self.current_positions.copy()
