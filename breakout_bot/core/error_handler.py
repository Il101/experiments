"""
Централизованная обработка ошибок для торгового движка.

Этот модуль содержит ErrorHandler класс, который отвечает за:
- Классификацию ошибок по типам
- Стратегии восстановления для различных ошибок
- Circuit breaker pattern для внешних зависимостей
- Логирование и уведомления об ош        # Уведомить о новой ошибке
        if self.notify_callback:
            try:
                result = self.notify_callback(error_info)
                if asyncio.iscoroutine(result):
                    await result
            except Exception as e:
                logger.error(f"Error in error notification callback: {e}")- Предотвращение каскадных сбоев
"""

import asyncio
import time
import logging
from enum import Enum
from typing import Dict, Optional, Callable, Any, Type, List
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import traceback

from .state_machine import TradingState

logger = logging.getLogger(__name__)


class ErrorSeverity(Enum):
    """Уровни критичности ошибок."""
    LOW = "low"           # Предупреждения, не влияют на работу
    MEDIUM = "medium"     # Требуют внимания, могут повторяться  
    HIGH = "high"         # Критические ошибки, нужен переход в ERROR состояние
    CRITICAL = "critical" # Катастрофические ошибки, нужен EMERGENCY режим


class ErrorCategory(Enum):
    """Категории ошибок для группировки."""
    NETWORK = "network"           # Сетевые ошибки, API
    DATA = "data"                # Проблемы с данными, валидация
    TRADING = "trading"          # Ошибки торговой логики
    SYSTEM = "system"            # Системные ошибки, ресурсы  
    EXTERNAL = "external"        # Внешние зависимости
    LOGIC = "logic"              # Логические ошибки в коде
    CONFIGURATION = "config"     # Ошибки конфигурации


class RecoveryStrategy(Enum):
    """Стратегии восстановления после ошибок."""
    RETRY = "retry"              # Повторить операцию с задержкой
    SKIP = "skip"                # Пропустить и продолжить
    RESET = "reset"              # Сбросить состояние компонента
    EMERGENCY = "emergency"      # Переход в аварийный режим
    IGNORE = "ignore"            # Игнорировать (только для LOW severity)


@dataclass
class ErrorInfo:
    """Информация об ошибке."""
    exception: Exception
    severity: ErrorSeverity
    category: ErrorCategory  
    recovery_strategy: RecoveryStrategy
    component: str
    operation: str
    timestamp: datetime = field(default_factory=datetime.now)
    context: Dict[str, Any] = field(default_factory=dict)
    stack_trace: str = field(default="")
    retry_count: int = 0


class CircuitBreaker:
    """Circuit breaker для защиты от каскадных сбоев."""
    
    def __init__(self, 
                 failure_threshold: int = 5,
                 recovery_timeout: int = 60,
                 success_threshold: int = 3):
        """
        Инициализация Circuit Breaker.
        
        Args:
            failure_threshold: Количество ошибок для открытия
            recovery_timeout: Время до попытки восстановления (сек)
            success_threshold: Количество успехов для закрытия
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.success_threshold = success_threshold
        
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: Optional[datetime] = None
        self._state = "closed"  # closed, open, half_open
        
    @property
    def state(self) -> str:
        """Получить текущее состояние Circuit Breaker."""
        if self._state == "open":
            # Проверить, не пора ли перейти в half_open
            if (self._last_failure_time and 
                datetime.now() - self._last_failure_time > timedelta(seconds=self.recovery_timeout)):
                self._state = "half_open"
                self._success_count = 0
                
        return self._state
    
    def record_success(self):
        """Записать успешную операцию."""
        if self._state == "half_open":
            self._success_count += 1
            if self._success_count >= self.success_threshold:
                self._state = "closed"
                self._failure_count = 0
        elif self._state == "closed":
            self._failure_count = max(0, self._failure_count - 1)
    
    def record_failure(self):
        """Записать неуспешную операцию."""
        self._failure_count += 1
        self._last_failure_time = datetime.now()
        
        if self._failure_count >= self.failure_threshold:
            self._state = "open"
    
    def can_execute(self) -> bool:
        """Проверить, можно ли выполнить операцию."""
        return self.state in ["closed", "half_open"]


class ErrorHandler:
    """Централизованная система обработки ошибок."""
    
    # Правила классификации ошибок
    ERROR_CLASSIFICATION: Dict[Type[Exception], Dict[str, Any]] = {
        ConnectionError: {
            "severity": ErrorSeverity.HIGH,
            "category": ErrorCategory.NETWORK,
            "recovery": RecoveryStrategy.RETRY
        },
        TimeoutError: {
            "severity": ErrorSeverity.MEDIUM,
            "category": ErrorCategory.NETWORK, 
            "recovery": RecoveryStrategy.RETRY
        },
        ValueError: {
            "severity": ErrorSeverity.MEDIUM,
            "category": ErrorCategory.DATA,
            "recovery": RecoveryStrategy.SKIP
        },
        KeyError: {
            "severity": ErrorSeverity.MEDIUM,
            "category": ErrorCategory.DATA,
            "recovery": RecoveryStrategy.SKIP
        },
        MemoryError: {
            "severity": ErrorSeverity.CRITICAL,
            "category": ErrorCategory.SYSTEM,
            "recovery": RecoveryStrategy.EMERGENCY
        },
        PermissionError: {
            "severity": ErrorSeverity.CRITICAL,
            "category": ErrorCategory.SYSTEM,
            "recovery": RecoveryStrategy.EMERGENCY
        }
    }
    
    def __init__(self, 
                 max_retries: int = 3,
                 retry_backoff: float = 2.0,
                 max_error_history: int = 1000,
                 notify_callback: Optional[Callable[[ErrorInfo], Any]] = None):
        """
        Инициализация ErrorHandler.
        
        Args:
            max_retries: Максимальное количество повторов
            retry_backoff: Коэффициент увеличения задержки
            max_error_history: Максимальный размер истории ошибок
            notify_callback: Колбэк для уведомлений об ошибках (может быть async)
        """
        self.max_retries = max_retries
        self.retry_backoff = retry_backoff
        self.max_error_history = max_error_history
        self.notify_callback = notify_callback
        
        self._error_history: List[ErrorInfo] = []
        self._circuit_breakers: Dict[str, CircuitBreaker] = {}
        self._retry_delays: Dict[str, float] = {}
        
        # Счетчики для мониторинга
        self._error_counts: Dict[ErrorCategory, int] = {cat: 0 for cat in ErrorCategory}
        self._total_errors = 0
        
        logger.info("ErrorHandler initialized")
        
    def classify_error(self, 
                      exception: Exception,
                      component: str,
                      operation: str,
                      context: Optional[Dict[str, Any]] = None) -> ErrorInfo:
        """
        Классифицировать ошибку и определить стратегию восстановления.
        
        Args:
            exception: Исключение для классификации
            component: Компонент где произошла ошибка
            operation: Операция при которой произошла ошибка
            context: Дополнительный контекст
            
        Returns:
            Классифицированная информация об ошибке
        """
        exception_type = type(exception)
        classification = self.ERROR_CLASSIFICATION.get(exception_type)
        
        if not classification:
            # Классификация по строке исключения
            error_msg = str(exception).lower()
            if any(word in error_msg for word in ["timeout", "connection", "network"]):
                classification = {
                    "severity": ErrorSeverity.MEDIUM,
                    "category": ErrorCategory.NETWORK,
                    "recovery": RecoveryStrategy.RETRY
                }
            elif any(word in error_msg for word in ["permission", "access", "forbidden"]):
                classification = {
                    "severity": ErrorSeverity.HIGH,
                    "category": ErrorCategory.SYSTEM,
                    "recovery": RecoveryStrategy.EMERGENCY
                }
            else:
                # Базовая классификация для неизвестных ошибок
                classification = {
                    "severity": ErrorSeverity.MEDIUM,
                    "category": ErrorCategory.LOGIC,
                    "recovery": RecoveryStrategy.RESET
                }
        
        error_info = ErrorInfo(
            exception=exception,
            severity=classification["severity"],
            category=classification["category"],
            recovery_strategy=classification["recovery"],
            component=component,
            operation=operation,
            context=context or {},
            stack_trace=traceback.format_exc()
        )
        
        return error_info
        
    async def handle_error(self, 
                          exception: Exception,
                          component: str,
                          operation: str,
                          context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Обработать ошибку и определить дальнейшие действия.
        
        Args:
            exception: Исключение для обработки
            component: Компонент где произошла ошибка  
            operation: Операция при которой произошла ошибка
            context: Дополнительный контекст
            
        Returns:
            Результат обработки с рекомендациями
        """
        # Классифицировать ошибку
        error_info = self.classify_error(exception, component, operation, context)
        
        # Записать в историю
        self._add_to_history(error_info)
        
        # Обновить статистику
        self._error_counts[error_info.category] += 1
        self._total_errors += 1
        
        # Получить или создать Circuit Breaker для компонента
        circuit_key = f"{component}:{operation}"
        if circuit_key not in self._circuit_breakers:
            self._circuit_breakers[circuit_key] = CircuitBreaker()
            
        circuit_breaker = self._circuit_breakers[circuit_key]
        circuit_breaker.record_failure()
        
        # Определить действия на основе стратегии восстановления
        recovery_action = await self._determine_recovery_action(error_info, circuit_breaker)
        
        # Уведомить о ошибке
        if self.notify_callback:
            try:
                result = self.notify_callback(error_info)
                if asyncio.iscoroutine(result):
                    await result
            except Exception as e:
                logger.error(f"Error in notification callback: {e}")
        
        # Логирование
        self._log_error(error_info, recovery_action)
        
        return recovery_action
        
    async def _determine_recovery_action(self, 
                                       error_info: ErrorInfo,
                                       circuit_breaker: CircuitBreaker) -> Dict[str, Any]:
        """Определить действия для восстановления после ошибки."""
        action = {
            "strategy": error_info.recovery_strategy.value,
            "should_retry": False,
            "delay": 0.0,
            "next_state": None,
            "emergency": False
        }
        
        # Если Circuit Breaker открыт - не повторяем
        if not circuit_breaker.can_execute():
            action["strategy"] = "circuit_open"
            action["next_state"] = TradingState.ERROR
            return action
            
        if error_info.recovery_strategy == RecoveryStrategy.RETRY:
            if error_info.retry_count < self.max_retries:
                action["should_retry"] = True
                action["delay"] = min(
                    self.retry_backoff ** error_info.retry_count,
                    60.0  # Максимальная задержка 60 сек
                )
            else:
                # Превышено количество повторов
                action["strategy"] = "max_retries_exceeded"
                action["next_state"] = TradingState.ERROR
                
        elif error_info.recovery_strategy == RecoveryStrategy.EMERGENCY:
            action["emergency"] = True
            action["next_state"] = TradingState.EMERGENCY
            
        elif error_info.recovery_strategy == RecoveryStrategy.RESET:
            action["next_state"] = TradingState.IDLE
            
        elif error_info.recovery_strategy == RecoveryStrategy.SKIP:
            # Просто продолжаем работу
            pass
            
        return action
        
    def record_success(self, component: str, operation: str):
        """Записать успешную операцию для Circuit Breaker."""
        circuit_key = f"{component}:{operation}"
        if circuit_key in self._circuit_breakers:
            self._circuit_breakers[circuit_key].record_success()
            
    def get_circuit_breaker_status(self, component: str, operation: str) -> str:
        """Получить статус Circuit Breaker для компонента."""
        circuit_key = f"{component}:{operation}"
        if circuit_key in self._circuit_breakers:
            return self._circuit_breakers[circuit_key].state
        return "closed"
        
    def _add_to_history(self, error_info: ErrorInfo):
        """Добавить ошибку в историю с ограничением размера."""
        self._error_history.append(error_info)
        
        # Ограничить размер истории
        if len(self._error_history) > self.max_error_history:
            self._error_history = self._error_history[-self.max_error_history:]
            
    def _log_error(self, error_info: ErrorInfo, recovery_action: Dict[str, Any]):
        """Залогировать ошибку с подходящим уровнем."""
        log_data = {
            "component": error_info.component,
            "operation": error_info.operation, 
            "exception_type": type(error_info.exception).__name__,
            "exception_msg": str(error_info.exception),
            "severity": error_info.severity.value,
            "category": error_info.category.value,
            "recovery_strategy": recovery_action["strategy"]
        }
        
        if error_info.severity == ErrorSeverity.CRITICAL:
            logger.critical(f"Critical error in {error_info.component}: {error_info.exception}", 
                          extra=log_data)
        elif error_info.severity == ErrorSeverity.HIGH:
            logger.error(f"High severity error in {error_info.component}: {error_info.exception}",
                        extra=log_data)
        elif error_info.severity == ErrorSeverity.MEDIUM:
            logger.warning(f"Medium severity error in {error_info.component}: {error_info.exception}",
                         extra=log_data)
        else:
            logger.info(f"Low severity error in {error_info.component}: {error_info.exception}",
                       extra=log_data)
                       
    def get_error_statistics(self) -> Dict[str, Any]:
        """Получить статистику ошибок."""
        return {
            "total_errors": self._total_errors,
            "errors_by_category": dict(self._error_counts),
            "circuit_breakers": {
                key: breaker.state 
                for key, breaker in self._circuit_breakers.items()
            },
            "recent_errors_count": len(self._error_history),
        }
        
    def get_recent_errors(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Получить список недавних ошибок."""
        recent = self._error_history[-limit:] if limit > 0 else self._error_history
        
        return [
            {
                "timestamp": error.timestamp.isoformat(),
                "component": error.component,
                "operation": error.operation,
                "exception_type": type(error.exception).__name__,
                "exception_msg": str(error.exception),
                "severity": error.severity.value,
                "category": error.category.value,
                "retry_count": error.retry_count
            }
            for error in recent
        ]
        
    def clear_history(self):
        """Очистить историю ошибок (для тестирования)."""
        self._error_history.clear()
        self._error_counts = {cat: 0 for cat in ErrorCategory}
        self._total_errors = 0
        self._circuit_breakers.clear()
        
        logger.info("Error history cleared")



