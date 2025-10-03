#!/usr/bin/env python3
"""
Простой тест для проверки базовой функциональности BybitRateLimiter.
"""

import asyncio
import time
import logging
import os
import sys

# Добавить путь к проекту
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from breakout_bot.exchange.rate_limiter import BybitRateLimiter, EndpointCategory

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def test_rate_limiter_basic():
    """Базовый тест rate limiter."""
    logger.info("🧪 Тестирование базовой функциональности BybitRateLimiter")
    
    # Создать rate limiter
    limiter = BybitRateLimiter()
    
    # Тест 1: Инициализация
    logger.info("✅ Rate limiter создан")
    
    # Тест 2: Статус
    status = limiter.get_status()
    logger.info(f"📊 Статус: {status}")
    assert 'category_rates' in status
    assert 'ip_requests_5s' in status
    logger.info("✅ Статус работает")
    
    # Тест 3: Получение разрешений
    success_count = 0
    for i in range(10):
        can_request = await limiter.acquire("/v5/market/tickers", EndpointCategory.MARKET_DATA)
        if can_request:
            success_count += 1
        await asyncio.sleep(0.01)  # 10ms между запросами
    
    logger.info(f"📊 Успешных acquire: {success_count}/10")
    assert success_count > 0, "Должно быть хотя бы несколько успешных acquire"
    logger.info("✅ Acquire работает")
    
    # Тест 4: Финальный статус
    final_status = limiter.get_status()
    logger.info(f"📊 Финальный статус: {final_status}")
    
    # Проверить что есть активность
    assert final_status['ip_requests_5s'] > 0, "Должны быть записаны IP запросы"
    logger.info("✅ Все тесты прошли успешно!")
    
    return True


async def main():
    """Главная функция."""
    try:
        result = await test_rate_limiter_basic()
        if result:
            logger.info("🎉 ТЕСТ ЗАВЕРШЕН УСПЕШНО!")
        return result
    except Exception as e:
        logger.error(f"❌ ТЕСТ ПРОВАЛЕН: {e}")
        return False


if __name__ == "__main__":
    asyncio.run(main())
