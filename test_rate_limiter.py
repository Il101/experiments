#!/usr/bin/env python3
"""
Тест rate limiter для проверки работы.
"""

import asyncio
import sys
import os

# Добавить путь к проекту
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from breakout_bot.exchange.bybit_rate_limiter import BybitRateLimiter, EndpointCategory

async def test_rate_limiter():
    """Тест rate limiter."""
    print("🧪 Тестирую BybitRateLimiter...")
    
    # Создать rate limiter
    limiter = BybitRateLimiter()
    print(f"✅ Rate limiter создан: {type(limiter)}")
    
    # Тест 1: Проверить лимиты
    print(f"📊 Лимиты: {limiter.DEFAULT_LIMITS}")
    
    # Тест 2: Проверить wait_if_needed
    print("⏳ Тестирую wait_if_needed...")
    await limiter.wait_if_needed(EndpointCategory.MARKET_DATA, "/v5/market/tickers")
    print("✅ wait_if_needed работает")
    
    # Тест 3: Проверить статус
    status = limiter.get_status()
    print(f"📈 Статус: {status}")
    
    # Тест 4: Проверить execute_with_retry
    print("🔄 Тестирую execute_with_retry...")
    
    async def dummy_func():
        return {"test": "success"}
    
    result = await limiter.execute_with_retry(
        dummy_func,
        EndpointCategory.MARKET_DATA,
        "/v5/market/tickers"
    )
    print(f"✅ execute_with_retry работает: {result}")
    
    print("🎉 Все тесты прошли успешно!")

if __name__ == "__main__":
    asyncio.run(test_rate_limiter())
