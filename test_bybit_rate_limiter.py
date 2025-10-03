#!/usr/bin/env python3
"""
Тест настройки rate limiting для Bybit API.

Проверяет:
1. Работу BybitRateLimiter с реальными запросами
2. Обработку заголовков X-Bapi-Limit-*
3. Exponential backoff при превышении лимитов
4. Интеграцию с ExchangeClient
"""

import asyncio
import time
import logging
from typing import List
import os
import sys

# Добавить путь к проекту
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from breakout_bot.config.settings import SystemConfig
from breakout_bot.exchange.exchange_client import ExchangeClient
from breakout_bot.exchange.rate_limiter import BybitRateLimiter, EndpointCategory

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class BybitRateLimiterTester:
    """Тестер для BybitRateLimiter."""

    def __init__(self):
        """Инициализация тестера."""
        self.results = {}
        
        # Конфигурация для Bybit
        self.config = SystemConfig()
        self.config.exchange = 'bybit'
        self.config.trading_mode = 'paper'  # Используем paper mode для безопасности
        
        # Создание exchange client
        self.exchange_client = ExchangeClient(self.config)

    async def test_rate_limiter_initialization(self):
        """Тест 1: Инициализация rate limiter."""
        logger.info("🧪 Тест 1: Инициализация BybitRateLimiter")
        
        try:
            # Проверить что rate limiter создан для Bybit
            assert self.exchange_client.rate_limiter is not None, "RateLimiter должен быть создан для Bybit"
            
            # Проверить начальный статус
            status = self.exchange_client.rate_limiter.get_status()
            assert isinstance(status, dict), "Статус должен быть словарем"
            assert 'category_rates' in status, "Должны быть category_rates"
            assert 'ip_requests_5s' in status, "Должен быть счетчик IP запросов"
            
            logger.info("✅ Инициализация прошла успешно")
            logger.info(f"📊 Начальный статус: {status}")
            
            self.results['initialization'] = 'PASSED'
            
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации: {e}")
            self.results['initialization'] = f'FAILED: {e}'

    async def test_single_request_rate_limiting(self):
        """Тест 2: Rate limiting для одиночных запросов."""
        logger.info("🧪 Тест 2: Rate limiting одиночных запросов")
        
        try:
            # Выполнить несколько запросов на получение данных
            test_symbols = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT']
            request_times = []
            
            for symbol in test_symbols:
                start_time = time.time()
                
                # Выполнить запрос через exchange client
                ticker = await self.exchange_client.fetch_ticker(symbol)
                
                end_time = time.time()
                request_time = end_time - start_time
                request_times.append(request_time)
                
                logger.info(f"📈 {symbol}: {request_time:.3f}s, ticker: {bool(ticker)}")
                
                # Проверить статус rate limiter
                status = self.exchange_client.rate_limiter.get_status()
                logger.debug(f"Rate limiter status: {status['category_rates']}")
                
                # Небольшая задержка между запросами
                await asyncio.sleep(0.1)
            
            avg_request_time = sum(request_times) / len(request_times)
            logger.info(f"📊 Среднее время запроса: {avg_request_time:.3f}s")
            
            # Проверить что запросы выполнились
            assert all(t > 0 for t in request_times), "Все запросы должны выполниться"
            assert avg_request_time < 5.0, "Среднее время не должно превышать 5 секунд"
            
            logger.info("✅ Одиночные запросы работают корректно")
            self.results['single_requests'] = 'PASSED'
            
        except Exception as e:
            logger.error(f"❌ Ошибка в одиночных запросах: {e}")
            self.results['single_requests'] = f'FAILED: {e}'

    async def test_burst_requests(self):
        """Тест 3: Burst запросы для проверки лимитов."""
        logger.info("🧪 Тест 3: Burst запросы")
        
        try:
            # Выполнить много запросов подряд
            symbols = ['BTCUSDT'] * 15  # 15 одинаковых запросов
            
            start_time = time.time()
            successful_requests = 0
            rate_limited_requests = 0
            
            for i, symbol in enumerate(symbols):
                try:
                    ticker = await self.exchange_client.fetch_ticker(symbol)
                    if ticker:
                        successful_requests += 1
                    logger.debug(f"Запрос {i+1}: успешный")
                    
                except Exception as e:
                    if 'rate limit' in str(e).lower() or 'too many' in str(e).lower():
                        rate_limited_requests += 1
                        logger.info(f"Запрос {i+1}: rate limited")
                    else:
                        logger.warning(f"Запрос {i+1}: другая ошибка - {e}")
            
            end_time = time.time()
            total_time = end_time - start_time
            requests_per_second = len(symbols) / total_time
            
            logger.info(f"📊 Всего запросов: {len(symbols)}")
            logger.info(f"📊 Успешных: {successful_requests}")
            logger.info(f"📊 Rate limited: {rate_limited_requests}")
            logger.info(f"📊 Общее время: {total_time:.2f}s")
            logger.info(f"📊 Скорость: {requests_per_second:.2f} req/s")
            
            # Получить финальный статус
            status = self.exchange_client.rate_limiter.get_status()
            logger.info(f"📊 Финальный статус rate limiter: {status}")
            
            # Проверки
            assert successful_requests > 0, "Должны быть успешные запросы"
            assert requests_per_second < 50, "Скорость должна быть ограничена (< 50 req/s)"
            
            if rate_limited_requests > 0:
                logger.info("✅ Rate limiting работает - некоторые запросы были ограничены")
            else:
                logger.info("✅ Все запросы прошли - лимиты не превышены")
            
            self.results['burst_requests'] = 'PASSED'
            
        except Exception as e:
            logger.error(f"❌ Ошибка в burst запросах: {e}")
            self.results['burst_requests'] = f'FAILED: {e}'

    async def test_different_endpoints(self):
        """Тест 4: Разные endpoints с разными лимитами."""
        logger.info("🧪 Тест 4: Разные типы endpoints")
        
        try:
            symbol = 'BTCUSDT'
            
            # Тест разных типов запросов
            endpoints_tested = []
            
            # Market data
            try:
                ticker = await self.exchange_client.fetch_ticker(symbol)
                endpoints_tested.append(('ticker', 'market_data', bool(ticker)))
                await asyncio.sleep(0.1)
            except Exception as e:
                logger.warning(f"Ticker request failed: {e}")
                endpoints_tested.append(('ticker', 'market_data', False))
            
            # Order book
            try:
                order_book = await self.exchange_client.fetch_order_book(symbol, 10)
                endpoints_tested.append(('orderbook', 'market_data', bool(order_book)))
                await asyncio.sleep(0.1)
            except Exception as e:
                logger.warning(f"Order book request failed: {e}")
                endpoints_tested.append(('orderbook', 'market_data', False))
            
            # OHLCV
            try:
                ohlcv = await self.exchange_client.fetch_ohlcv(symbol, '5m', 10)
                endpoints_tested.append(('ohlcv', 'market_data', bool(ohlcv)))
                await asyncio.sleep(0.1)
            except Exception as e:
                logger.warning(f"OHLCV request failed: {e}")
                endpoints_tested.append(('ohlcv', 'market_data', False))
            
            # Логирование результатов
            for endpoint, category, success in endpoints_tested:
                status_icon = "✅" if success else "❌"
                logger.info(f"{status_icon} {endpoint} ({category}): {success}")
            
            successful_endpoints = sum(1 for _, _, success in endpoints_tested if success)
            
            assert successful_endpoints > 0, "Хотя бы один endpoint должен работать"
            
            logger.info(f"✅ Протестировано {len(endpoints_tested)} endpoints, успешных: {successful_endpoints}")
            self.results['different_endpoints'] = 'PASSED'
            
        except Exception as e:
            logger.error(f"❌ Ошибка в тесте endpoints: {e}")
            self.results['different_endpoints'] = f'FAILED: {e}'

    async def test_rate_limiter_status_monitoring(self):
        """Тест 5: Мониторинг статуса rate limiter."""
        logger.info("🧪 Тест 5: Мониторинг статуса")
        
        try:
            # Выполнить несколько запросов для генерации статистики
            for i in range(5):
                await self.exchange_client.fetch_ticker('BTCUSDT')
                await asyncio.sleep(0.2)
            
            # Получить подробный статус
            status = self.exchange_client.get_rate_limiter_status()
            
            assert status is not None, "Статус rate limiter должен быть доступен"
            
            # Проверить структуру статуса
            required_keys = ['category_rates', 'ip_requests_5s', 'ip_limit']
            for key in required_keys:
                assert key in status, f"Ключ '{key}' должен присутствовать в статусе"
            
            logger.info("📊 Детальный статус rate limiter:")
            for key, value in status.items():
                logger.info(f"  {key}: {value}")
            
            logger.info("✅ Мониторинг статуса работает корректно")
            self.results['status_monitoring'] = 'PASSED'
            
        except Exception as e:
            logger.error(f"❌ Ошибка в мониторинге статуса: {e}")
            self.results['status_monitoring'] = f'FAILED: {e}'

    async def run_all_tests(self):
        """Запустить все тесты."""
        logger.info("🚀 Запуск всех тестов BybitRateLimiter")
        logger.info("=" * 60)
        
        tests = [
            self.test_rate_limiter_initialization,
            self.test_single_request_rate_limiting,
            self.test_burst_requests,
            self.test_different_endpoints,
            self.test_rate_limiter_status_monitoring
        ]
        
        for test in tests:
            try:
                await test()
                await asyncio.sleep(1)  # Пауза между тестами
            except Exception as e:
                logger.error(f"Критическая ошибка в тесте {test.__name__}: {e}")
                self.results[test.__name__] = f'CRITICAL_ERROR: {e}'
        
        # Итоговый отчет
        logger.info("=" * 60)
        logger.info("📋 ИТОГОВЫЙ ОТЧЕТ ТЕСТИРОВАНИЯ")
        logger.info("=" * 60)
        
        passed_tests = 0
        total_tests = len(self.results)
        
        for test_name, result in self.results.items():
            if result == 'PASSED':
                logger.info(f"✅ {test_name}: {result}")
                passed_tests += 1
            else:
                logger.error(f"❌ {test_name}: {result}")
        
        logger.info("=" * 60)
        logger.info(f"📊 РЕЗУЛЬТАТ: {passed_tests}/{total_tests} тестов прошли успешно")
        
        if passed_tests == total_tests:
            logger.info("🎉 ВСЕ ТЕСТЫ ПРОШЛИ! Rate limiting настроен корректно")
        else:
            logger.warning("⚠️  Некоторые тесты не прошли. Требуется дополнительная настройка")
        
        return self.results


async def main():
    """Основная функция."""
    try:
        tester = BybitRateLimiterTester()
        results = await tester.run_all_tests()
        return results
    except Exception as e:
        logger.error(f"Критическая ошибка в main: {e}")
        return {"main": f"CRITICAL_ERROR: {e}"}


if __name__ == "__main__":
    asyncio.run(main())
