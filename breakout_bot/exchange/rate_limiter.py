"""
Bybit API Rate Limiter

Реализует правильные ограничения скорости запросов для Bybit API
на основе официальной документации, включая:
- Мониторинг заголовков X-Bapi-Limit-*
- Exponential backoff при превышении лимитов
- Разные лимиты для разных типов endpoints
- Интеграция с CCXT
"""

import asyncio
import time
import logging
import random
from typing import Dict, Optional, Any, Callable, Union
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class EndpointCategory(Enum):
    """Категории endpoints с разными rate limits."""
    MARKET_DATA = "market_data"  # 50-100 req/s
    TRADING = "trading"         # 10-20 req/s
    ACCOUNT = "account"         # 20-50 req/s
    PUBLIC = "public"           # Высокие лимиты


@dataclass
class RateLimitInfo:
    """Информация о текущих rate limits из ответов API."""
    limit: int = 0                    # X-Bapi-Limit
    remaining: int = 0                # X-Bapi-Limit-Status
    reset_timestamp: int = 0          # X-Bapi-Limit-Reset-Timestamp
    last_updated: float = 0.0


@dataclass
class EndpointLimits:
    """Предустановленные лимиты для разных типов endpoints."""
    requests_per_second: int
    burst_limit: int
    cooldown_seconds: float = 1.0


class BybitRateLimiter:
    """
    Умный rate limiter для Bybit API.
    
    Особенности:
    - Отслеживает заголовки X-Bapi-Limit-* из ответов
    - Разные лимиты для разных категорий endpoints
    - Exponential backoff с jitter
    - Адаптивные задержки на основе реальных данных API
    """

    # Конфигурация лимитов на основе документации Bybit (оптимизировано для сканирования)
    DEFAULT_LIMITS = {
        EndpointCategory.MARKET_DATA: EndpointLimits(15, 30),   # Оптимально для сканирования с concurrency=10
        EndpointCategory.TRADING: EndpointLimits(5, 10),        # Консервативно для торговли
        EndpointCategory.ACCOUNT: EndpointLimits(10, 20),       # Умеренно для аккаунта
        EndpointCategory.PUBLIC: EndpointLimits(20, 40),        # Мягко для публичных данных
    }

    # IP level лимит: безопасный подход (Bybit ~6 req/s per IP)
    IP_LEVEL_LIMIT = 25  # Оптимизировано для 10 параллельных потоков
    IP_WINDOW_SECONDS = 5

    def __init__(self):
        """Инициализация rate limiter."""
        # Лимиты для каждой категории endpoints
        self.category_limits = self.DEFAULT_LIMITS.copy()
        
        # Информация о текущих лимитах из API
        self.current_limits: Dict[str, RateLimitInfo] = {}
        
        # Счетчики запросов по категориям
        self.request_counts: Dict[EndpointCategory, list] = {
            category: [] for category in EndpointCategory
        }
        
        # IP level счетчик
        self.ip_requests: list = []
        
        # Exponential backoff состояние
        self.backoff_state: Dict[EndpointCategory, dict] = {}
        
        # Блокировка для безопасности потоков
        self._lock = asyncio.Lock()

    async def acquire(self, 
                     endpoint: str, 
                     category: EndpointCategory = EndpointCategory.PUBLIC,
                     method: str = "GET") -> bool:
        """
        Получить разрешение на выполнение запроса.
        
        Args:
            endpoint: URL endpoint
            category: Категория endpoint для определения лимитов  
            method: HTTP метод
            
        Returns:
            True если запрос можно выполнить
        """
        async with self._lock:
            await self._cleanup_old_requests()
            
            # Проверить IP level лимит
            if not self._check_ip_limit():
                await self._wait_for_ip_reset()
                return False
            
            # Проверить category level лимит
            if not self._check_category_limit(category):
                delay = self._calculate_backoff_delay(category)
                logger.debug(f"Rate limit для {category.value}, ждем {delay:.2f}s")
                await asyncio.sleep(delay)
                return False
            
            # Записать запрос
            current_time = time.time()
            self.request_counts[category].append(current_time)
            self.ip_requests.append(current_time)
            
            return True

    def update_from_response_headers(self, headers: Dict[str, Any], endpoint: str = ""):
        """
        Обновить информацию о лимитах из заголовков ответа API.
        
        Args:
            headers: HTTP заголовки ответа
            endpoint: Endpoint для которого получены заголовки
        """
        try:
            limit_info = RateLimitInfo()
            
            # Извлечь заголовки Bybit
            if 'X-Bapi-Limit' in headers:
                limit_info.limit = int(headers['X-Bapi-Limit'])
            if 'X-Bapi-Limit-Status' in headers:
                limit_info.remaining = int(headers['X-Bapi-Limit-Status'])
            if 'X-Bapi-Limit-Reset-Timestamp' in headers:
                limit_info.reset_timestamp = int(headers['X-Bapi-Limit-Reset-Timestamp'])
            
            limit_info.last_updated = time.time()
            self.current_limits[endpoint] = limit_info
            
            logger.debug(f"Обновлены лимиты для {endpoint}: {limit_info.remaining}/{limit_info.limit}")
            
            # Сбросить backoff если есть доступные запросы
            if limit_info.remaining > 0:
                self._reset_backoff(endpoint)
                
        except (ValueError, KeyError) as e:
            logger.warning(f"Ошибка парсинга rate limit заголовков: {e}")

    def handle_rate_limit_error(self, 
                               error: Exception, 
                               endpoint: str = "",
                               category: EndpointCategory = EndpointCategory.PUBLIC):
        """
        Обработать ошибку превышения rate limit.
        
        Args:
            error: Исключение
            endpoint: Endpoint где произошла ошибка
            category: Категория endpoint
        """
        error_msg = str(error).lower()
        
        # Определить тип ошибки
        if "too many visits" in error_msg or "10006" in error_msg:
            # Account level rate limit
            self._trigger_backoff(category, account_level=True)
            logger.warning(f"Account rate limit превышен для {category.value}")
        elif "access too frequent" in error_msg or "403" in error_msg:
            # IP level rate limit
            self._trigger_backoff(category, ip_level=True)  
            logger.warning("IP rate limit превышен")
        elif "rate limit" in error_msg or "429" in error_msg:
            # Generic rate limit
            self._trigger_backoff(category, account_level=True)
            logger.warning(f"Rate limit для {category.value}")
        else:
            # Не rate limit ошибка - не применяем backoff
            logger.debug(f"Не-rate-limit ошибка: {error_msg}")

    async def wait_for_reset(self, endpoint: str = "") -> float:
        """
        Дождаться сброса rate limit для endpoint.
        
        Args:
            endpoint: Endpoint для ожидания
            
        Returns:
            Время ожидания в секундах
        """
        if endpoint in self.current_limits:
            limit_info = self.current_limits[endpoint]
            if limit_info.reset_timestamp > 0:
                current_time = int(time.time() * 1000)
                if limit_info.reset_timestamp > current_time:
                    wait_seconds = (limit_info.reset_timestamp - current_time) / 1000
                    logger.info(f"Ожидание сброса rate limit: {wait_seconds:.1f}s")
                    await asyncio.sleep(wait_seconds)
                    return wait_seconds
        
        return 0.0

    def get_status(self) -> Dict[str, Any]:
        """Получить текущий статус rate limiter."""
        current_time = time.time()
        
        # Подсчет запросов за последнюю секунду для каждой категории
        category_rates = {}
        for category, requests in self.request_counts.items():
            recent_requests = [r for r in requests if current_time - r <= 1.0]
            category_rates[category.value] = len(recent_requests)
        
        # IP level requests за последние 5 секунд
        recent_ip_requests = [r for r in self.ip_requests if current_time - r <= self.IP_WINDOW_SECONDS]
        
        return {
            "category_rates": category_rates,
            "ip_requests_5s": len(recent_ip_requests),
            "ip_limit": self.IP_LEVEL_LIMIT,
            "active_limits": {
                endpoint: {
                    "remaining": info.remaining,
                    "limit": info.limit,
                    "reset_in_seconds": max(0, (info.reset_timestamp - int(time.time() * 1000)) / 1000) 
                    if info.reset_timestamp > 0 else 0
                }
                for endpoint, info in self.current_limits.items()
                if time.time() - info.last_updated < 60  # Показать только свежие данные
            },
            "backoff_active": {
                category.value: bool(self.backoff_state.get(category))
                for category in EndpointCategory
            }
        }
    
    def reset_limits(self):
        """Сбросить все лимиты и backoff состояния."""
        self.ip_requests.clear()
        self.request_counts.clear()
        self.backoff_state.clear()
        self.current_limits.clear()
        logger.info("Rate limiter limits reset")

    # === ВНУТРЕННИЕ МЕТОДЫ ===

    async def _cleanup_old_requests(self):
        """Очистить старые записи запросов."""
        current_time = time.time()
        
        # Очистить запросы старше 1 секунды для категорий
        for category in self.request_counts:
            self.request_counts[category] = [
                r for r in self.request_counts[category] 
                if current_time - r <= 1.0
            ]
        
        # Очистить IP запросы старше 5 секунд
        self.ip_requests = [
            r for r in self.ip_requests 
            if current_time - r <= self.IP_WINDOW_SECONDS
        ]

    def _check_ip_limit(self) -> bool:
        """Проверить IP level лимит."""
        current_requests = len(self.ip_requests)
        return current_requests < self.IP_LEVEL_LIMIT

    def _check_category_limit(self, category: EndpointCategory) -> bool:
        """Проверить лимит для категории endpoint."""
        limits = self.category_limits[category]
        current_requests = len(self.request_counts[category])
        return current_requests < limits.requests_per_second

    async def _wait_for_ip_reset(self):
        """Дождаться сброса IP лимита."""
        if self.ip_requests:
            oldest_request = min(self.ip_requests)
            wait_time = self.IP_WINDOW_SECONDS - (time.time() - oldest_request)
            if wait_time > 0:
                logger.warning(f"IP rate limit, ждем {wait_time:.1f}s")
                await asyncio.sleep(wait_time)

    def _calculate_backoff_delay(self, category: EndpointCategory) -> float:
        """Рассчитать задержку для exponential backoff."""
        backoff_info = self.backoff_state.get(category, {})
        
        if not backoff_info:
            return self.category_limits[category].cooldown_seconds
        
        retry_count = backoff_info.get('retry_count', 0)
        base_delay = backoff_info.get('base_delay', 1.0)
        
        # Exponential backoff с jitter (как в документации)
        delay = min(300, (2 ** retry_count) * base_delay + random.uniform(0, 0.1))
        
        return delay

    def _trigger_backoff(self, 
                        category: EndpointCategory, 
                        account_level: bool = False,
                        ip_level: bool = False):
        """Запустить exponential backoff для категории."""
        current_backoff = self.backoff_state.get(category, {})
        
        retry_count = current_backoff.get('retry_count', 0) + 1
        # Более мягкие задержки
        base_delay = 0.5 if account_level else (2.0 if ip_level else 0.2)
        
        self.backoff_state[category] = {
            'retry_count': retry_count,
            'base_delay': base_delay,
            'triggered_at': time.time(),
            'account_level': account_level,
            'ip_level': ip_level
        }

    def _reset_backoff(self, endpoint: str = "", category: EndpointCategory = None):
        """Сбросить backoff состояние."""
        if category and category in self.backoff_state:
            del self.backoff_state[category]
        
        # Также можем сбросить все backoff если получили успешный ответ
        if endpoint in self.current_limits:
            limit_info = self.current_limits[endpoint]
            if limit_info.remaining > 5:  # Есть достаточно запросов
                self.backoff_state.clear()


# === ДЕКОРАТОРЫ И УТИЛИТЫ ===

def classify_endpoint(endpoint: str, method: str = "GET") -> EndpointCategory:
    """
    Классифицировать endpoint по категории для определения лимитов.
    
    Args:
        endpoint: URL endpoint
        method: HTTP метод
        
    Returns:
        Категория endpoint
    """
    endpoint_lower = endpoint.lower()
    
    # Trading endpoints
    if any(path in endpoint_lower for path in ['/order/', '/position/', '/execution/']):
        return EndpointCategory.TRADING
    
    # Account endpoints  
    if any(path in endpoint_lower for path in ['/account/', '/wallet/', '/asset/']):
        return EndpointCategory.ACCOUNT
    
    # Market data endpoints
    if any(path in endpoint_lower for path in ['/market/', '/kline', '/ticker', '/orderbook']):
        return EndpointCategory.MARKET_DATA
    
    # По умолчанию публичные
    return EndpointCategory.PUBLIC


def rate_limited(rate_limiter: BybitRateLimiter, 
                endpoint: str = "",
                category: EndpointCategory = None,
                max_retries: int = 3):
    """
    Декоратор для автоматического применения rate limiting к функциям.
    
    Args:
        rate_limiter: Экземпляр BybitRateLimiter
        endpoint: Endpoint для классификации
        category: Принудительная категория
        max_retries: Максимум попыток при rate limiting
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Определить категорию
            used_category = category or classify_endpoint(endpoint)
            
            for attempt in range(max_retries + 1):
                try:
                    # Получить разрешение на запрос
                    if await rate_limiter.acquire(endpoint, used_category):
                        result = await func(*args, **kwargs) if asyncio.iscoroutinefunction(func) else func(*args, **kwargs)
                        
                        # Обновить лимиты из заголовков если доступны
                        if hasattr(result, 'headers'):
                            rate_limiter.update_from_response_headers(result.headers, endpoint)
                        
                        return result
                    else:
                        if attempt == max_retries:
                            raise Exception(f"Rate limit exceeded for {endpoint} after {max_retries} retries")
                        continue
                        
                except Exception as e:
                    error_msg = str(e).lower()
                    if any(keyword in error_msg for keyword in ['rate limit', 'too many', 'frequent']):
                        rate_limiter.handle_rate_limit_error(e, endpoint, used_category)
                        if attempt == max_retries:
                            raise
                        
                        # Подождать перед следующей попыткой
                        delay = rate_limiter._calculate_backoff_delay(used_category)
                        await asyncio.sleep(delay)
                        continue
                    else:
                        raise
            
            raise Exception(f"Max retries exceeded for {endpoint}")
        
        return wrapper
    return decorator
