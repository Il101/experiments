#!/usr/bin/env python3
"""
Enhanced Error Handler
Централизованная обработка ошибок с типизацией, retry логикой и recovery стратегиями
"""

import asyncio
import logging
import time
from typing import Optional, Dict, Any, Callable, Type, Union
from enum import Enum
from dataclasses import dataclass
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)

class ErrorCategory(Enum):
    """Категории ошибок для специализированной обработки"""
    NETWORK = "network"
    EXCHANGE_API = "exchange_api" 
    DATA_VALIDATION = "data_validation"
    TRADING_LOGIC = "trading_logic"
    RESOURCE = "resource"
    CONFIGURATION = "configuration"
    UNKNOWN = "unknown"

class ErrorSeverity(Enum):
    """Уровни критичности ошибок"""
    LOW = "low"           # Можно проигнорировать
    MEDIUM = "medium"     # Требует внимания но не критично
    HIGH = "high"         # Критично, требует retry
    CRITICAL = "critical" # Система должна остановиться

@dataclass
class ErrorContext:
    """Контекст ошибки для обработки"""
    category: ErrorCategory
    severity: ErrorSeverity
    operation: str
    component: str
    retry_count: int = 0
    max_retries: int = 3
    retry_delay: float = 1.0
    backoff_multiplier: float = 2.0
    metadata: Optional[Dict[str, Any]] = None

class EnhancedErrorHandler:
    """Улучшенный обработчик ошибок с retry логикой"""
    
    def __init__(self):
        self.error_counts: Dict[ErrorCategory, int] = {}
        self.last_errors: Dict[str, float] = {}
        self.circuit_breakers: Dict[str, bool] = {}
        
        # Карта типов ошибок к категориям
        self.error_mapping = {
            # Сетевые ошибки
            ConnectionError: ErrorCategory.NETWORK,
            TimeoutError: ErrorCategory.NETWORK,
            OSError: ErrorCategory.NETWORK,
            
            # Ошибки валидации
            ValueError: ErrorCategory.DATA_VALIDATION,
            TypeError: ErrorCategory.DATA_VALIDATION,
            KeyError: ErrorCategory.DATA_VALIDATION,
            
            # Ошибки ресурсов
            MemoryError: ErrorCategory.RESOURCE,
            
            # По умолчанию
            Exception: ErrorCategory.UNKNOWN
        }
    
    def classify_error(self, error: Exception) -> ErrorCategory:
        """Классифицируем ошибку по типу"""
        error_type = type(error)
        
        # Ищем точное совпадение
        if error_type in self.error_mapping:
            return self.error_mapping[error_type]
        
        # Ищем по наследованию
        for exc_type, category in self.error_mapping.items():
            if isinstance(error, exc_type):
                return category
        
        # Специальные случаи по сообщению
        error_msg = str(error).lower()
        
        if any(keyword in error_msg for keyword in ['timeout', 'connection', 'network', 'dns']):
            return ErrorCategory.NETWORK
        
        if any(keyword in error_msg for keyword in ['api', 'rate limit', 'forbidden', 'unauthorized']):
            return ErrorCategory.EXCHANGE_API
        
        if any(keyword in error_msg for keyword in ['validation', 'invalid', 'missing required']):
            return ErrorCategory.DATA_VALIDATION
        
        return ErrorCategory.UNKNOWN
    
    def get_severity(self, error: Exception, context: ErrorContext) -> ErrorSeverity:
        """Определяем критичность ошибки"""
        category = context.category
        operation = context.operation.lower()
        
        # Критичные операции
        if any(critical_op in operation for critical_op in ['execute', 'close_position', 'emergency']):
            return ErrorSeverity.CRITICAL
        
        # Высокая критичность для торговой логики
        if category in [ErrorCategory.TRADING_LOGIC, ErrorCategory.EXCHANGE_API]:
            return ErrorSeverity.HIGH
        
        # Средняя для сети и ресурсов
        if category in [ErrorCategory.NETWORK, ErrorCategory.RESOURCE]:
            return ErrorSeverity.MEDIUM
        
        # Низкая для валидации и конфигурации
        return ErrorSeverity.LOW
    
    async def handle_with_retry(self, 
                               operation: Callable,
                               context: ErrorContext,
                               *args, **kwargs) -> Any:
        """Выполняет операцию с retry логикой"""
        
        for attempt in range(context.max_retries + 1):
            try:
                if asyncio.iscoroutinefunction(operation):
                    return await operation(*args, **kwargs)
                else:
                    return operation(*args, **kwargs)
                    
            except Exception as e:
                context.category = self.classify_error(e)
                context.severity = self.get_severity(e, context)
                context.retry_count = attempt
                
                # Логируем ошибку
                self._log_error(e, context)
                
                # Обновляем статистику
                self._update_error_stats(context.category)
                
                # Проверяем circuit breaker
                if self._is_circuit_open(context.component):
                    logger.error(f"Circuit breaker OPEN for {context.component}")
                    raise e
                
                # Если это последняя попытка или критичная ошибка
                if attempt == context.max_retries or context.severity == ErrorSeverity.CRITICAL:
                    logger.error(f"Operation {context.operation} failed permanently after {attempt + 1} attempts")
                    raise e
                
                # Рассчитываем delay для retry
                delay = context.retry_delay * (context.backoff_multiplier ** attempt)
                
                logger.info(f"Retrying {context.operation} in {delay:.1f}s (attempt {attempt + 1}/{context.max_retries})")
                await asyncio.sleep(delay)
        
        raise Exception(f"Operation {context.operation} exhausted all retries")
    
    @asynccontextmanager
    async def error_context(self, context: ErrorContext):
        """Контекстный менеджер для обработки ошибок"""
        try:
            yield context
        except Exception as e:
            context.category = self.classify_error(e)
            context.severity = self.get_severity(e, context)
            
            self._log_error(e, context)
            self._update_error_stats(context.category)
            
            # Определяем стратегию recovery
            if context.severity == ErrorSeverity.CRITICAL:
                logger.critical(f"CRITICAL error in {context.component}.{context.operation}: {e}")
                raise e
            elif context.severity == ErrorSeverity.HIGH:
                logger.error(f"HIGH severity error in {context.component}.{context.operation}: {e}")
                raise e
            else:
                logger.warning(f"Handled error in {context.component}.{context.operation}: {e}")
                # Можем не перебрасывать ошибку для LOW/MEDIUM severity
    
    def _log_error(self, error: Exception, context: ErrorContext):
        """Логирует ошибку с контекстом"""
        log_data = {
            'category': context.category.value,
            'severity': context.severity.value,
            'operation': context.operation,
            'component': context.component,
            'retry_count': context.retry_count,
            'error_type': type(error).__name__,
            'error_msg': str(error)
        }
        
        if context.metadata:
            log_data['metadata'] = context.metadata
        
        if context.severity in [ErrorSeverity.CRITICAL, ErrorSeverity.HIGH]:
            logger.error(f"Error handled: {log_data}")
        else:
            logger.warning(f"Error handled: {log_data}")
    
    def _update_error_stats(self, category: ErrorCategory):
        """Обновляем статистику ошибок"""
        self.error_counts[category] = self.error_counts.get(category, 0) + 1
        
        # Проверяем на превышение лимитов
        if self.error_counts[category] > 10:  # Порог для circuit breaker
            component_key = f"{category.value}_high_error_rate"
            self.circuit_breakers[component_key] = True
            logger.warning(f"Circuit breaker TRIGGERED for {category.value} (>{self.error_counts[category]} errors)")
    
    def _is_circuit_open(self, component: str) -> bool:
        """Проверяет состояние circuit breaker"""
        return self.circuit_breakers.get(component, False)
    
    def reset_circuit_breaker(self, component: str):
        """Сбрасывает circuit breaker"""
        if component in self.circuit_breakers:
            del self.circuit_breakers[component]
            logger.info(f"Circuit breaker RESET for {component}")
    
    def get_error_stats(self) -> Dict[str, Any]:
        """Возвращает статистику ошибок"""
        return {
            'error_counts': {k.value: v for k, v in self.error_counts.items()},
            'circuit_breakers': dict(self.circuit_breakers),
            'total_errors': sum(self.error_counts.values())
        }

# Глобальный instance для использования в системе
enhanced_error_handler = EnhancedErrorHandler()

# Удобные декораторы для различных типов операций
def handle_network_errors(operation: str, component: str = "network", max_retries: int = 3):
    """Декоратор для обработки сетевых ошибок"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            context = ErrorContext(
                category=ErrorCategory.NETWORK,
                severity=ErrorSeverity.MEDIUM,
                operation=operation,
                component=component,
                max_retries=max_retries,
                retry_delay=2.0
            )
            return await enhanced_error_handler.handle_with_retry(func, context, *args, **kwargs)
        return wrapper
    return decorator

def handle_exchange_errors(operation: str, component: str = "exchange", max_retries: int = 2):
    """Декоратор для обработки ошибок биржи"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            context = ErrorContext(
                category=ErrorCategory.EXCHANGE_API,
                severity=ErrorSeverity.HIGH,
                operation=operation,
                component=component,
                max_retries=max_retries,
                retry_delay=5.0
            )
            return await enhanced_error_handler.handle_with_retry(func, context, *args, **kwargs)
        return wrapper
    return decorator

def handle_critical_errors(operation: str, component: str = "trading"):
    """Декоратор для критичных торговых операций (без retry)"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            context = ErrorContext(
                category=ErrorCategory.TRADING_LOGIC,
                severity=ErrorSeverity.CRITICAL,
                operation=operation,
                component=component,
                max_retries=0  # Критичные операции не повторяем
            )
            async with enhanced_error_handler.error_context(context):
                if asyncio.iscoroutinefunction(func):
                    return await func(*args, **kwargs)
                else:
                    return func(*args, **kwargs)
        return wrapper
    return decorator
