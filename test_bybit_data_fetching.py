#!/usr/bin/env python3
"""
Тест получения данных от Bybit API.

Проверяет:
1. Актуальность получаемых данных
2. Полноту данных для каждого символа
3. Rate limits и оптимальную скорость запросов
4. Обработку ошибок 429 (Too Many Requests)
"""

import asyncio
import time
import os
import sys
from typing import Dict, List, Any, Optional
from datetime import datetime
from collections import defaultdict
import ccxt.async_support as ccxt_async

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from breakout_bot.config.settings import SystemConfig
from breakout_bot.exchange import ExchangeClient, MarketDataProvider
from breakout_bot.data.models import MarketData


class BybitDataTester:
    """Тестер получения данных от Bybit."""
    
    def __init__(self):
        self.config = SystemConfig()
        self.exchange_client = None
        self.market_data_provider = None
        self.results = {
            'successful_requests': 0,
            'failed_requests': 0,
            'rate_limit_errors': 0,
            'timeout_errors': 0,
            'other_errors': 0,
            'total_time': 0,
            'avg_response_time': 0,
            'symbols_tested': 0,
            'complete_data_count': 0,
            'incomplete_data_count': 0,
            'errors_by_type': defaultdict(int),
            'response_times': []
        }
        
    async def initialize(self):
        """Инициализация клиентов."""
        print("🚀 Инициализация клиентов Bybit...")
        self.exchange_client = ExchangeClient(self.config)
        self.market_data_provider = MarketDataProvider(
            self.exchange_client,
            enable_websocket=False  # Только REST API
        )
        print("✅ Клиенты инициализированы\n")
        
    async def test_single_symbol_data(self, symbol: str) -> Dict[str, Any]:
        """Тест получения данных для одного символа."""
        start_time = time.time()
        result = {
            'symbol': symbol,
            'success': False,
            'data_completeness': {},
            'response_time': 0,
            'error': None,
            'timestamp': datetime.now().isoformat()
        }
        
        try:
            # Получить рыночные данные
            market_data = await self.market_data_provider.get_market_data(symbol)
            
            response_time = time.time() - start_time
            result['response_time'] = response_time
            self.results['response_times'].append(response_time)
            
            if market_data:
                result['success'] = True
                self.results['successful_requests'] += 1
                
                # Проверка полноты данных
                completeness = {
                    'has_price': market_data.price is not None and market_data.price > 0,
                    'has_volume': market_data.volume_24h_usd is not None and market_data.volume_24h_usd > 0,
                    'has_oi': market_data.oi_usd is not None and market_data.oi_usd > 0,
                    'has_trades_per_min': market_data.trades_per_minute is not None and market_data.trades_per_minute > 0,
                    'has_atr_5m': market_data.atr_5m is not None and market_data.atr_5m > 0,
                    'has_atr_15m': market_data.atr_15m is not None and market_data.atr_15m > 0,
                    'has_bb_width': market_data.bb_width_pct is not None and market_data.bb_width_pct > 0,
                    'has_depth': market_data.l2_depth is not None,
                    'has_candles': market_data.candles_5m is not None and len(market_data.candles_5m) > 0,
                }
                
                result['data_completeness'] = completeness
                result['data'] = {
                    'price': market_data.price,
                    'volume_24h': market_data.volume_24h_usd,
                    'oi_usd': market_data.oi_usd,
                    'trades_per_min': market_data.trades_per_minute,
                    'atr_5m': market_data.atr_5m,
                    'atr_15m': market_data.atr_15m,
                    'bb_width_pct': market_data.bb_width_pct,
                    'btc_correlation': market_data.btc_correlation,
                    'candles_count': len(market_data.candles_5m) if market_data.candles_5m else 0,
                    'depth_bid_0.5': market_data.l2_depth.bid_usd_0_5pct if market_data.l2_depth else 0,
                    'depth_ask_0.5': market_data.l2_depth.ask_usd_0_5pct if market_data.l2_depth else 0,
                    'spread_bps': market_data.l2_depth.spread_bps if market_data.l2_depth else 0,
                }
                
                # Подсчет полноты
                complete_fields = sum(1 for v in completeness.values() if v)
                total_fields = len(completeness)
                
                if complete_fields == total_fields:
                    self.results['complete_data_count'] += 1
                else:
                    self.results['incomplete_data_count'] += 1
                    
            else:
                result['error'] = "No data returned"
                self.results['failed_requests'] += 1
                
        except asyncio.TimeoutError:
            result['error'] = "Timeout"
            self.results['timeout_errors'] += 1
            self.results['failed_requests'] += 1
            
        except Exception as e:
            error_str = str(e)
            result['error'] = error_str
            self.results['failed_requests'] += 1
            
            # Классификация ошибок
            if '429' in error_str or 'rate limit' in error_str.lower():
                self.results['rate_limit_errors'] += 1
                self.results['errors_by_type']['rate_limit'] += 1
            elif 'timeout' in error_str.lower():
                self.results['timeout_errors'] += 1
                self.results['errors_by_type']['timeout'] += 1
            else:
                self.results['other_errors'] += 1
                self.results['errors_by_type']['other'] += 1
                
        return result
        
    async def test_concurrent_requests(self, symbols: List[str], concurrency: int) -> List[Dict[str, Any]]:
        """Тест параллельных запросов с заданной concurrency."""
        print(f"📊 Тест параллельных запросов: {len(symbols)} символов, concurrency={concurrency}")
        
        semaphore = asyncio.Semaphore(concurrency)
        
        async def bounded_fetch(symbol: str):
            async with semaphore:
                return await self.test_single_symbol_data(symbol)
                
        start_time = time.time()
        results = await asyncio.gather(*[bounded_fetch(s) for s in symbols], return_exceptions=True)
        total_time = time.time() - start_time
        
        print(f"⏱️  Время выполнения: {total_time:.2f}s")
        print(f"   Среднее время на символ: {total_time/len(symbols):.2f}s")
        print(f"   Успешных запросов: {self.results['successful_requests']}")
        print(f"   Неудачных запросов: {self.results['failed_requests']}")
        
        return [r for r in results if not isinstance(r, Exception)]
        
    async def test_rate_limits(self):
        """Тест rate limits - постепенное увеличение нагрузки."""
        print("\n" + "="*80)
        print("🔍 ТЕСТ RATE LIMITS")
        print("="*80 + "\n")
        
        # Получить список символов
        symbols = await self.exchange_client.fetch_markets()
        test_symbols = symbols[:20]  # Тестируем на 20 символах
        
        print(f"Тестируем на {len(test_symbols)} символах: {', '.join(test_symbols[:5])}...\n")
        
        concurrency_levels = [1, 5, 10, 15, 20, 25, 30]
        
        for concurrency in concurrency_levels:
            print(f"\n{'─'*80}")
            print(f"Тест с concurrency = {concurrency}")
            print('─'*80)
            
            # Сброс статистики для этого теста
            test_start = time.time()
            prev_successful = self.results['successful_requests']
            prev_rate_limit = self.results['rate_limit_errors']
            
            await self.test_concurrent_requests(test_symbols[:10], concurrency)
            
            test_duration = time.time() - test_start
            new_successful = self.results['successful_requests'] - prev_successful
            new_rate_limit = self.results['rate_limit_errors'] - prev_rate_limit
            
            requests_per_second = new_successful / test_duration if test_duration > 0 else 0
            
            print(f"\n📈 Результаты:")
            print(f"   Успешных запросов: {new_successful}/10")
            print(f"   Rate limit ошибок: {new_rate_limit}")
            print(f"   Скорость: {requests_per_second:.2f} req/s")
            
            if new_rate_limit > 0:
                print(f"\n⚠️  ВНИМАНИЕ: Обнаружены rate limit ошибки!")
                print(f"   Рекомендуемая concurrency: {concurrency - 5}")
                break
                
            # Пауза между тестами
            await asyncio.sleep(2)
            
    async def test_data_freshness(self, symbol: str = 'BTC/USDT:USDT'):
        """Тест актуальности данных - повторные запросы."""
        print("\n" + "="*80)
        print("🕐 ТЕСТ АКТУАЛЬНОСТИ ДАННЫХ")
        print("="*80 + "\n")
        
        print(f"Символ: {symbol}")
        print("Выполняем 5 запросов с интервалом 2 секунды...\n")
        
        prices = []
        timestamps = []
        
        for i in range(5):
            result = await self.test_single_symbol_data(symbol)
            
            if result['success']:
                price = result['data']['price']
                prices.append(price)
                timestamps.append(datetime.now())
                
                print(f"Запрос {i+1}: Price = ${price:,.2f}, Response time = {result['response_time']:.2f}s")
            else:
                print(f"Запрос {i+1}: FAILED - {result['error']}")
                
            if i < 4:  # Не ждем после последнего запроса
                await asyncio.sleep(2)
                
        if len(prices) > 1:
            print(f"\n📊 Анализ:")
            print(f"   Цены: {', '.join([f'${p:,.2f}' for p in prices])}")
            print(f"   Разброс: ${max(prices) - min(prices):,.2f}")
            print(f"   Изменение: {((prices[-1] - prices[0]) / prices[0] * 100):.3f}%")
            print(f"   ✅ Данные обновляются в реальном времени" if prices[-1] != prices[0] else 
                  "⚠️  Данные могут быть кэшированы")
                  
    async def test_complete_data_structure(self, symbol: str = 'BTC/USDT:USDT'):
        """Детальная проверка структуры данных для одного символа."""
        print("\n" + "="*80)
        print("🔬 ДЕТАЛЬНАЯ ПРОВЕРКА ДАННЫХ")
        print("="*80 + "\n")
        
        print(f"Символ: {symbol}\n")
        
        result = await self.test_single_symbol_data(symbol)
        
        if result['success']:
            print("✅ Данные успешно получены\n")
            
            print("📋 Полнота данных:")
            for field, has_data in result['data_completeness'].items():
                status = "✅" if has_data else "❌"
                print(f"   {status} {field}")
                
            print("\n📊 Значения:")
            for field, value in result['data'].items():
                if isinstance(value, float):
                    print(f"   {field}: {value:.6f}")
                else:
                    print(f"   {field}: {value}")
                    
            print(f"\n⏱️  Время ответа: {result['response_time']:.2f}s")
        else:
            print(f"❌ Ошибка получения данных: {result['error']}")
            
    async def test_multiple_symbols_detailed(self, symbols: List[str]):
        """Детальный тест нескольких символов."""
        print("\n" + "="*80)
        print("📚 ДЕТАЛЬНЫЙ ТЕСТ НЕСКОЛЬКИХ СИМВОЛОВ")
        print("="*80 + "\n")
        
        print(f"Тестируем {len(symbols)} символов: {', '.join(symbols)}\n")
        
        results = await self.test_concurrent_requests(symbols, concurrency=10)
        
        print("\n📊 СВОДКА ПО СИМВОЛАМ:")
        print("─"*80)
        
        for result in results:
            if result['success']:
                completeness = sum(1 for v in result['data_completeness'].values() if v)
                total = len(result['data_completeness'])
                status = "✅" if completeness == total else "⚠️ "
                print(f"{status} {result['symbol']:20s} | Полнота: {completeness}/{total} | "
                      f"Время: {result['response_time']:.2f}s | "
                      f"Цена: ${result['data']['price']:,.2f}")
            else:
                print(f"❌ {result['symbol']:20s} | FAILED: {result['error']}")
                
    def print_final_summary(self):
        """Печать финальной сводки."""
        print("\n" + "="*80)
        print("📈 ФИНАЛЬНАЯ СВОДКА")
        print("="*80 + "\n")
        
        total_requests = self.results['successful_requests'] + self.results['failed_requests']
        success_rate = (self.results['successful_requests'] / total_requests * 100) if total_requests > 0 else 0
        
        print(f"Всего запросов: {total_requests}")
        print(f"✅ Успешных: {self.results['successful_requests']} ({success_rate:.1f}%)")
        print(f"❌ Неудачных: {self.results['failed_requests']}")
        print(f"\nОшибки:")
        print(f"   Rate limit (429): {self.results['rate_limit_errors']}")
        print(f"   Timeout: {self.results['timeout_errors']}")
        print(f"   Другие: {self.results['other_errors']}")
        
        if self.results['response_times']:
            avg_time = sum(self.results['response_times']) / len(self.results['response_times'])
            min_time = min(self.results['response_times'])
            max_time = max(self.results['response_times'])
            
            print(f"\nВремя ответа:")
            print(f"   Среднее: {avg_time:.2f}s")
            print(f"   Минимум: {min_time:.2f}s")
            print(f"   Максимум: {max_time:.2f}s")
            
        print(f"\nПолнота данных:")
        print(f"   Полные: {self.results['complete_data_count']}")
        print(f"   Неполные: {self.results['incomplete_data_count']}")
        
        # Рекомендации
        print("\n" + "="*80)
        print("💡 РЕКОМЕНДАЦИИ")
        print("="*80 + "\n")
        
        if self.results['rate_limit_errors'] > 0:
            print("⚠️  Обнаружены rate limit ошибки!")
            print("   Рекомендации:")
            print("   - Уменьшите LIVE_SCAN_CONCURRENCY в .env")
            print("   - Увеличьте задержки между запросами")
            print("   - Проверьте, что используется rate limiter")
        else:
            print("✅ Rate limit ошибок не обнаружено")
            
        if avg_time > 2.0:
            print("\n⚠️  Среднее время ответа > 2 секунд")
            print("   Рекомендации:")
            print("   - Проверьте сетевое подключение")
            print("   - Рассмотрите использование WebSocket для real-time данных")
        else:
            print("\n✅ Время ответа в норме")
            
        if self.results['incomplete_data_count'] > self.results['complete_data_count']:
            print("\n⚠️  Много неполных данных")
            print("   Рекомендации:")
            print("   - Проверьте логи на предмет ошибок")
            print("   - Убедитесь, что API keys корректны (если требуются)")
        else:
            print("\n✅ Большинство данных полные")
            
        # Оптимальные настройки
        if self.results['successful_requests'] > 0 and self.results['rate_limit_errors'] == 0:
            print("\n🎯 ОПТИМАЛЬНЫЕ НАСТРОЙКИ ДЛЯ .env:")
            print("─"*80)
            
            if avg_time < 1.0:
                recommended_concurrency = 20
            elif avg_time < 2.0:
                recommended_concurrency = 15
            else:
                recommended_concurrency = 10
                
            print(f"ENGINE_MARKET_FETCH_LIMIT=50")
            print(f"LIVE_SCAN_CONCURRENCY={recommended_concurrency}")
            print(f"MARKET_DATA_TIMEOUT=120")
            print("─"*80)
            
    async def run_full_test_suite(self):
        """Запуск полного набора тестов."""
        print("="*80)
        print("🧪 BYBIT DATA FETCHING TEST SUITE")
        print("="*80)
        
        await self.initialize()
        
        # Тест 1: Детальная проверка одного символа
        await self.test_complete_data_structure('BTC/USDT:USDT')
        
        # Тест 2: Проверка актуальности данных
        await self.test_data_freshness('BTC/USDT:USDT')
        
        # Тест 3: Детальный тест нескольких популярных символов
        popular_symbols = [
            'BTC/USDT:USDT',
            'ETH/USDT:USDT',
            'SOL/USDT:USDT',
            'BNB/USDT:USDT',
            'XRP/USDT:USDT'
        ]
        await self.test_multiple_symbols_detailed(popular_symbols)
        
        # Тест 4: Rate limits
        await self.test_rate_limits()
        
        # Финальная сводка
        self.print_final_summary()
        
        # Закрыть соединения
        if self.exchange_client:
            await self.exchange_client.close()
            
        print("\n✅ Все тесты завершены!\n")


async def main():
    """Главная функция."""
    tester = BybitDataTester()
    
    try:
        await tester.run_full_test_suite()
    except KeyboardInterrupt:
        print("\n\n⚠️  Тесты прерваны пользователем")
    except Exception as e:
        print(f"\n\n❌ Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if tester.exchange_client:
            try:
                await tester.exchange_client.close()
            except:
                pass


if __name__ == '__main__':
    asyncio.run(main())
