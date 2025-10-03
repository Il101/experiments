"""
Централизованное управление состояниями торгового движка.

Этот модуль содержит StateMachine класс, который отвечает за:
- Валидацию переходов между состояниями
- Логирование всех переходов  
- Уведомления о смене состояния
- Предотвращение недопустимых переходов
"""

import asyncio
import time
import logging
from enum import Enum
from typing import Dict, Set, Optional, Callable, Any, List
from dataclasses import dataclass
from datetime import datetime

from ..utils.enhanced_logger import LogContext

logger = logging.getLogger(__name__)


class TradingState(Enum):
    """Состояния торговой системы."""
    IDLE = "idle"
    INITIALIZING = "initializing"
    SCANNING = "scanning"
    LEVEL_BUILDING = "level_building"
    SIGNAL_WAIT = "signal_wait"
    SIZING = "sizing"
    EXECUTION = "execution"
    MANAGING = "managing"
    PAUSED = "paused"
    ERROR = "error"
    EMERGENCY = "emergency"
    STOPPED = "stopped"


@dataclass
class StateTransition:
    """Информация о переходе между состояниями."""
    from_state: TradingState
    to_state: TradingState
    reason: str
    timestamp: int
    metadata: Optional[Dict[str, Any]] = None


class StateMachine:
    """Централизованный менеджер состояний торговой системы."""
    
    # Матрица допустимых переходов между состояниями
    VALID_TRANSITIONS: Dict[TradingState, Set[TradingState]] = {
        TradingState.IDLE: {
            TradingState.INITIALIZING,
            TradingState.SCANNING,  # Allow direct scanning from idle
            TradingState.STOPPED,
            TradingState.ERROR
        },
        TradingState.INITIALIZING: {
            TradingState.SCANNING,
            TradingState.ERROR,
            TradingState.EMERGENCY,
            TradingState.STOPPED
        },
        TradingState.SCANNING: {
            TradingState.LEVEL_BUILDING,
            TradingState.MANAGING,
            TradingState.PAUSED,
            TradingState.ERROR,
            TradingState.EMERGENCY,
            TradingState.STOPPED
        },
        TradingState.LEVEL_BUILDING: {
            TradingState.SIGNAL_WAIT,
            TradingState.SCANNING,
            TradingState.ERROR,
            TradingState.EMERGENCY,
            TradingState.STOPPED
        },
        TradingState.SIGNAL_WAIT: {
            TradingState.SIZING,
            TradingState.MANAGING,
            TradingState.SCANNING,
            TradingState.PAUSED,
            TradingState.ERROR,
            TradingState.EMERGENCY,
            TradingState.STOPPED
        },
        TradingState.SIZING: {
            TradingState.EXECUTION,
            TradingState.SCANNING,
            TradingState.ERROR,
            TradingState.EMERGENCY,
            TradingState.STOPPED
        },
        TradingState.EXECUTION: {
            TradingState.MANAGING,
            TradingState.SCANNING,
            TradingState.ERROR,
            TradingState.EMERGENCY,
            TradingState.STOPPED
        },
        TradingState.MANAGING: {
            TradingState.SCANNING,
            TradingState.MANAGING,  # Self-transition для продолжения управления
            TradingState.PAUSED,
            TradingState.ERROR,
            TradingState.EMERGENCY,
            TradingState.STOPPED
        },
        TradingState.PAUSED: {
            TradingState.SCANNING,
            TradingState.MANAGING,
            TradingState.IDLE,
            TradingState.ERROR,
            TradingState.EMERGENCY,
            TradingState.STOPPED
        },
        TradingState.ERROR: {
            TradingState.SCANNING,
            TradingState.MANAGING,
            TradingState.IDLE,
            TradingState.EMERGENCY,
            TradingState.STOPPED
        },
        TradingState.EMERGENCY: {
            TradingState.STOPPED,
            TradingState.IDLE
        },
        TradingState.STOPPED: {
            TradingState.IDLE,
            TradingState.INITIALIZING
        }
    }

    def __init__(self, 
                 initial_state: TradingState = TradingState.IDLE,
                 notify_callback: Optional[Callable[[StateTransition], Any]] = None,
                 enhanced_logger=None):
        """
        Инициализация StateMachine.
        
        Args:
            initial_state: Начальное состояние
            notify_callback: Колбэк для уведомлений о переходах (может быть async)
            enhanced_logger: Логгер для расширенного логирования
        """
        self._current_state = initial_state
        self._previous_state: Optional[TradingState] = None
        self._transition_history: List[StateTransition] = []
        self._notify_callback = notify_callback
        self._enhanced_logger = enhanced_logger
        
        self._lock = asyncio.Lock()  # Для thread-safe операций
        
        logger.info(f"StateMachine initialized with state: {initial_state.value}")

    @property
    def current_state(self) -> TradingState:
        """Получить текущее состояние."""
        return self._current_state

    @property 
    def previous_state(self) -> Optional[TradingState]:
        """Получить предыдущее состояние."""
        return self._previous_state

    def can_transition(self, to_state: TradingState) -> bool:
        """
        Проверить, возможен ли переход в указанное состояние.
        
        Args:
            to_state: Целевое состояние
            
        Returns:
            True, если переход допустим
        """
        if self._current_state not in self.VALID_TRANSITIONS:
            return False
            
        return to_state in self.VALID_TRANSITIONS[self._current_state]

    async def transition_to(self, 
                          to_state: TradingState, 
                          reason: str = "", 
                          metadata: Optional[Dict[str, Any]] = None,
                          force: bool = False) -> bool:
        """
        Выполнить переход в новое состояние.
        
        Args:
            to_state: Целевое состояние
            reason: Причина перехода
            metadata: Дополнительная информация о переходе
            force: Принудительный переход (игнорировать валидацию)
            
        Returns:
            True, если переход выполнен успешно
        """
        try:
            async with asyncio.timeout(5.0):
                async with self._lock:
                    # Проверка валидности перехода
                    if not force and not self.can_transition(to_state):
                        logger.warning(
                            f"Invalid transition attempt: {self._current_state.value} -> {to_state.value}. "
                            f"Reason: {reason}"
                        )
                        return False

                    # Игнорировать переход в то же состояние
                    if self._current_state == to_state and not force:
                        logger.debug(f"Ignoring transition to same state: {to_state.value}")
                        return True

                    # Создать информацию о переходе
                    transition = StateTransition(
                        from_state=self._current_state,
                        to_state=to_state,
                        reason=reason,
                        timestamp=int(time.time() * 1000),
                        metadata=metadata
                    )

                    # Сохранить предыдущее состояние
                    self._previous_state = self._current_state
                    self._current_state = to_state

                    # Добавить в историю (лимитированная)
                    self._transition_history.append(transition)
                    if len(self._transition_history) > 100:  # Ограничить историю
                        self._transition_history = self._transition_history[-100:]

                    # Логирование
                    logger.info(
                        f"State transition: {transition.from_state.value} -> {transition.to_state.value} "
                        f"({reason})"
                    )

                    # Расширенное логирование
                    if self._enhanced_logger:
                        context = LogContext(
                            component="state_machine",
                            state=to_state.value
                        )
                        self._enhanced_logger.info(
                            f"State transition: {transition.from_state.value} -> {transition.to_state.value}",
                            context
                        )

                    # Уведомить о переходе
                    if self._notify_callback:
                        try:
                            result = self._notify_callback(transition)
                            if asyncio.iscoroutine(result):
                                await result
                        except Exception as e:
                            logger.error(f"Error in transition notification callback: {e}")

                    return True
        except asyncio.TimeoutError:
            logger.error(f"Timeout waiting for state machine lock during transition to {to_state.value}")
            return False
        except Exception as e:
            logger.error(f"Error during state transition to {to_state.value}: {e}")
            return False

    def get_transition_history(self, limit: int = 50) -> List[StateTransition]:
        """
        Получить историю переходов.
        
        Args:
            limit: Максимальное количество записей
            
        Returns:
            Список последних переходов
        """
        return self._transition_history[-limit:] if limit > 0 else self._transition_history.copy()

    def get_valid_next_states(self) -> Set[TradingState]:
        """
        Получить список допустимых состояний для перехода из текущего состояния.
        
        Returns:
            Множество допустимых состояний
        """
        return self.VALID_TRANSITIONS.get(self._current_state, set()).copy()

    def is_terminal_state(self) -> bool:
        """
        Проверить, является ли текущее состояние терминальным.
        
        Returns:
            True, если состояние терминальное
        """
        return self._current_state in {TradingState.STOPPED, TradingState.EMERGENCY}

    def is_error_state(self) -> bool:
        """
        Проверить, является ли текущее состояние ошибочным.
        
        Returns:
            True, если состояние указывает на ошибку
        """
        return self._current_state in {TradingState.ERROR, TradingState.EMERGENCY}

    def is_trading_active(self) -> bool:
        """
        Проверить, активна ли торговля в текущем состоянии.
        
        Returns:
            True, если система активно торгует
        """
        return self._current_state in {
            TradingState.SCANNING,
            TradingState.LEVEL_BUILDING, 
            TradingState.SIGNAL_WAIT,
            TradingState.SIZING,
            TradingState.EXECUTION,
            TradingState.MANAGING
        }

    def get_status(self) -> Dict[str, Any]:
        """
        Получить статус StateMachine.
        
        Returns:
            Словарь со статусной информацией
        """
        return {
            "current_state": self._current_state.value,
            "previous_state": self._previous_state.value if self._previous_state else None,
            "is_terminal": self.is_terminal_state(),
            "is_error": self.is_error_state(),
            "is_trading_active": self.is_trading_active(),
            "valid_next_states": [state.value for state in self.get_valid_next_states()],
            "transition_count": len(self._transition_history)
        }

    def reset_to_initial(self, reason: str = "System reset") -> None:
        """
        Сбросить состояние к начальному.
        
        Args:
            reason: Причина сброса
        """
        logger.info(f"Resetting StateMachine to IDLE: {reason}")
        self._previous_state = self._current_state
        self._current_state = TradingState.IDLE
