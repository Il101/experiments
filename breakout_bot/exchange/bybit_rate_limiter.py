"""
Bybit API Rate Limiter - Правильная реализация согласно официальной документации.

Основано на официальной документации Bybit:
- X-RateLimit-* заголовки
- Простые лимиты: 50 req/sec для market data
- Простая обработка "too many visits" с sleep(1)
"""

import asyncio
import time
import logging
import random
from typing import Dict, Optional, Any, Callable
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class EndpointCategory(Enum):
    """Категории endpoints с разными rate limits."""
    MARKET_DATA = "market_data"
    TRADING = "trading"
    ACCOUNT = "account"
    PUBLIC = "public"


@dataclass
class RateLimitInfo:
    """Информация о rate limit из заголовков Bybit."""
    limit: int
    remaining: int
    reset_timestamp: int
    last_updated: float


class BybitRateLimiter:
    """
    Правильный rate limiter для Bybit API согласно документации.
    
    Особенности:
    - Использует X-RateLimit-* заголовки (не X-Bapi-Limit-*)
    - Простые лимиты: 50 req/sec для market data
    - Простая обработка "too many visits" с sleep(1)
    - Минимальная задержка между запросами
    """

    # Оптимизированные лимиты согласно официальной документации Bybit
    DEFAULT_LIMITS = {
        EndpointCategory.MARKET_DATA: 50,   # Public market data per docs
        EndpointCategory.TRADING: 20,
        EndpointCategory.ACCOUNT: 30,
        EndpointCategory.PUBLIC: 50,
    }

    def __init__(self):
        """Инициализация rate limiter."""
        self.request_times = {}  # {category: [timestamps]}
        self.rate_limit_info = {}  # {endpoint: RateLimitInfo}
        self.min_delay = 0.02  # 20ms между запросами (~50 req/sec)
        
    async def wait_if_needed(self, category: EndpointCategory, endpoint: str = ""):
        """
        Подождать если необходимо согласно rate limits.
        
        Args:
            category: Категория endpoint
            endpoint: Конкретный endpoint (опционально)
        """
        current_time = time.time()
        
        # Очистить старые записи (старше 1 секунды)
        if category in self.request_times:
            self.request_times[category] = [
                t for t in self.request_times[category] 
                if current_time - t < 1.0
            ]
        else:
            self.request_times[category] = []
        
        # Проверить лимит
        limit = self.DEFAULT_LIMITS[category]
        current_requests = len(self.request_times[category])
        
        logger.debug(f"Rate limiter check: {category.value} - {current_requests}/{limit} requests")
        
        if current_requests >= limit:
            # Превышен лимит, ждем до следующей секунды
            sleep_time = 1.0 - (current_time - self.request_times[category][0])
            if sleep_time > 0:
                logger.warning(f"Rate limit exceeded for {category.value}, waiting {sleep_time:.2f}s")
                await asyncio.sleep(sleep_time)
                # Очистить старые записи после ожидания
                current_time = time.time()
                self.request_times[category] = [
                    t for t in self.request_times[category] 
                    if current_time - t < 1.0
                ]
        
        # Добавить минимальную задержку между запросами
        if self.request_times[category]:
            time_since_last = current_time - self.request_times[category][-1]
            if time_since_last < self.min_delay:
                logger.debug(f"Adding min delay: {self.min_delay - time_since_last:.3f}s")
                await asyncio.sleep(self.min_delay - time_since_last)
        
        # Записать время запроса
        self.request_times[category].append(time.time())
        logger.debug(f"Request recorded for {category.value}, total: {len(self.request_times[category])}")

    def update_from_headers(self, headers: Dict[str, str], endpoint: str = ""):
        """
        Обновить информацию о rate limits из заголовков ответа.
        
        Args:
            headers: HTTP заголовки ответа
            endpoint: Endpoint для которого получены заголовки
        """
        # Bybit использует X-RateLimit-* заголовки
        limit = headers.get('X-RateLimit-Limit')
        remaining = headers.get('X-RateLimit-Remaining')
        reset = headers.get('X-RateLimit-Reset')
        
        if limit and remaining and reset:
            try:
                self.rate_limit_info[endpoint] = RateLimitInfo(
                    limit=int(limit),
                    remaining=int(remaining),
                    reset_timestamp=int(reset),
                    last_updated=time.time()
                )
                logger.debug(f"Updated rate limit for {endpoint}: {remaining}/{limit}")
            except (ValueError, TypeError) as e:
                logger.warning(f"Failed to parse rate limit headers: {e}")

    async def execute_with_retry(self, 
                                func: Callable,
                                category: EndpointCategory,
                                endpoint: str = "",
                                max_retries: int = 3,
                                *args, **kwargs):
        """
        Выполнить функцию с учетом rate limits и retry при "too many visits".
        
        Args:
            func: Функция для выполнения
            category: Категория endpoint
            endpoint: Endpoint для логирования
            max_retries: Максимум попыток
            *args, **kwargs: Аргументы для функции
        """
        for attempt in range(max_retries + 1):
            try:
                logger.debug(f"Executing {endpoint} (attempt {attempt + 1}/{max_retries + 1})")
                
                # Подождать если необходимо
                await self.wait_if_needed(category, endpoint)
                
                # Выполнить функцию
                result = await func(*args, **kwargs)
                
                # Обновить информацию о rate limits из заголовков
                if hasattr(result, 'headers'):
                    self.update_from_headers(result.headers, endpoint)
                
                logger.debug(f"Successfully executed {endpoint}")
                return result
                
            except Exception as e:
                error_msg = str(e).lower()
                
                # Проверить на "too many visits" согласно документации
                if "too many visits" in error_msg or "rate limit" in error_msg or "access too frequent" in error_msg:
                    if attempt < max_retries:
                        # Увеличенная задержка для Bybit блокировки
                        wait_time = 2.0 + random.uniform(0, 1.0)  # 2-3 секунды
                        logger.warning(f"Rate limit hit on {endpoint}, retry {attempt + 1}/{max_retries} after {wait_time:.1f}s")
                        await asyncio.sleep(wait_time)
                        continue
                    else:
                        logger.error(f"Rate limit exceeded after {max_retries} retries for {endpoint}")
                        raise
                else:
                    # Другие ошибки не связанные с rate limit
                    raise
        
        raise Exception(f"Failed after {max_retries} retries")

    def get_status(self) -> Dict[str, Any]:
        """Получить статус rate limiter."""
        current_time = time.time()
        
        # Подсчитать запросы за последнюю секунду
        category_rates = {}
        for category, requests in self.request_times.items():
            recent_requests = [r for r in requests if current_time - r < 1.0]
            category_rates[category.value] = {
                "current": len(recent_requests),
                "limit": self.DEFAULT_LIMITS[category]
            }
        
        return {
            "category_rates": category_rates,
            "rate_limit_info": {
                endpoint: {
                    "limit": info.limit,
                    "remaining": info.remaining,
                    "reset_in_seconds": max(0, info.reset_timestamp - int(current_time))
                }
                for endpoint, info in self.rate_limit_info.items()
                if current_time - info.last_updated < 60  # Показать только свежие данные
            },
            "min_delay_ms": self.min_delay * 1000
        }
    
    def reset_limits(self):
        """Сбросить все лимиты."""
        self.request_times.clear()
        self.rate_limit_info.clear()
        logger.info("Rate limiter limits reset")


def classify_endpoint(endpoint: str) -> EndpointCategory:
    """
    Классифицировать endpoint по категории.
    
    Args:
        endpoint: Путь к endpoint
        
    Returns:
        Категория endpoint
    """
    endpoint_lower = endpoint.lower()
    
    if '/market/' in endpoint_lower:
        return EndpointCategory.MARKET_DATA
    elif '/order/' in endpoint_lower or '/trade/' in endpoint_lower:
        return EndpointCategory.TRADING
    elif '/account/' in endpoint_lower or '/position/' in endpoint_lower:
        return EndpointCategory.ACCOUNT
    else:
        return EndpointCategory.PUBLIC
