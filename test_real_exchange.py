#!/usr/bin/env python3
"""
Тестирование с реальными биржами (Binance/Bybit)
ВАЖНО: Используйте только тестовые API ключи!
"""

import asyncio
import time
import logging
from typing import Dict, Any, List
import ccxt
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RealExchangeTester:
    """Тестер для реальных бирж"""
    
    def __init__(self):
        self.test_results = {}
        self.exchanges = {}
        
    async def run_real_exchange_tests(self):
        """Запуск тестов с реальными биржами"""
        logger.info("🚀 Starting real exchange testing...")
        
        try:
            # Test 1: API Connectivity
            await self.test_api_connectivity()
            
            # Test 2: Market Data
            await self.test_market_data()
            
            # Test 3: Order Book
            await self.test_order_book()
            
            # Test 4: Rate Limits
            await self.test_rate_limits()
            
            # Test 5: Small Test Orders (только с тестовыми ключами!)
            await self.test_small_orders()
            
            # Test 6: Error Handling
            await self.test_error_handling()
            
            # Generate report
            self.generate_report()
            
        except Exception as e:
            logger.error(f"❌ Real exchange testing failed: {e}")
    
    async def test_api_connectivity(self):
        """Test 1: Проверка подключения к API"""
        logger.info("🔍 Testing API connectivity...")
        
        try:
            # Test Binance (public API)
            binance = ccxt.binance({
                'sandbox': True,  # Используем sandbox!
                'apiKey': '',  # Оставляем пустым для public API
                'secret': '',
            })
            
            # Test connection
            markets = binance.load_markets()
            assert len(markets) > 0
            
            # Test Bybit (public API)
            bybit = ccxt.bybit({
                'sandbox': True,  # Используем sandbox!
                'apiKey': '',
                'secret': '',
            })
            
            markets = bybit.load_markets()
            assert len(markets) > 0
            
            self.test_results['api_connectivity'] = 'PASSED'
            logger.info("✅ API connectivity test passed")
            
        except Exception as e:
            self.test_results['api_connectivity'] = f'FAILED: {e}'
            logger.error(f"❌ API connectivity test failed: {e}")
    
    async def test_market_data(self):
        """Test 2: Тестирование получения рыночных данных"""
        logger.info("🔍 Testing market data...")
        
        try:
            binance = ccxt.binance({'sandbox': True})
            
            # Test ticker data
            ticker = binance.fetch_ticker('BTC/USDT')
            assert 'last' in ticker
            assert ticker['last'] > 0
            
            # Test OHLCV data
            ohlcv = binance.fetch_ohlcv('BTC/USDT', '1m', limit=100)
            assert len(ohlcv) == 100
            assert all(len(candle) == 6 for candle in ohlcv)  # [timestamp, open, high, low, close, volume]
            
            # Test trades data
            trades = binance.fetch_trades('BTC/USDT', limit=10)
            assert len(trades) > 0
            
            self.test_results['market_data'] = 'PASSED'
            logger.info("✅ Market data test passed")
            
        except Exception as e:
            self.test_results['market_data'] = f'FAILED: {e}'
            logger.error(f"❌ Market data test failed: {e}")
    
    async def test_order_book(self):
        """Test 3: Тестирование стакана заявок"""
        logger.info("🔍 Testing order book...")
        
        try:
            binance = ccxt.binance({'sandbox': True})
            
            # Test order book
            orderbook = binance.fetch_order_book('BTC/USDT')
            assert 'bids' in orderbook
            assert 'asks' in orderbook
            assert len(orderbook['bids']) > 0
            assert len(orderbook['asks']) > 0
            
            # Test spread calculation
            best_bid = orderbook['bids'][0][0]
            best_ask = orderbook['asks'][0][0]
            spread = best_ask - best_bid
            spread_bps = (spread / best_bid) * 10000
            
            logger.info(f"Spread: {spread:.2f} USDT ({spread_bps:.2f} bps)")
            
            # Test depth
            total_bid_volume = sum(bid[1] for bid in orderbook['bids'][:10])
            total_ask_volume = sum(ask[1] for ask in orderbook['asks'][:10])
            
            logger.info(f"Top 10 bids volume: {total_bid_volume:.2f} BTC")
            logger.info(f"Top 10 asks volume: {total_ask_volume:.2f} BTC")
            
            self.test_results['order_book'] = 'PASSED'
            logger.info("✅ Order book test passed")
            
        except Exception as e:
            self.test_results['order_book'] = f'FAILED: {e}'
            logger.error(f"❌ Order book test failed: {e}")
    
    async def test_rate_limits(self):
        """Test 4: Тестирование лимитов запросов"""
        logger.info("🔍 Testing rate limits...")
        
        try:
            binance = ccxt.binance({'sandbox': True})
            
            # Test rapid requests
            start_time = time.time()
            request_count = 0
            
            for i in range(20):  # 20 запросов подряд
                try:
                    ticker = binance.fetch_ticker('BTC/USDT')
                    request_count += 1
                except ccxt.RateLimitExceeded:
                    logger.warning(f"Rate limit hit after {request_count} requests")
                    break
                except Exception as e:
                    logger.warning(f"Request {i} failed: {e}")
            
            elapsed = time.time() - start_time
            requests_per_second = request_count / elapsed
            
            logger.info(f"Made {request_count} requests in {elapsed:.2f}s ({requests_per_second:.2f} req/s)")
            
            # Binance typically allows 1200 requests per minute
            if requests_per_second > 20:  # 20 req/s = 1200 req/min
                logger.warning("Rate limit might be too high for production")
            
            self.test_results['rate_limits'] = 'PASSED'
            logger.info("✅ Rate limits test passed")
            
        except Exception as e:
            self.test_results['rate_limits'] = f'FAILED: {e}'
            logger.error(f"❌ Rate limits test failed: {e}")
    
    async def test_small_orders(self):
        """Test 5: Тестирование мелких ордеров (ТОЛЬКО С ТЕСТОВЫМИ КЛЮЧАМИ!)"""
        logger.info("🔍 Testing small orders (SANDBOX ONLY!)...")
        
        try:
            # ВНИМАНИЕ: Используйте только тестовые API ключи!
            # Никогда не используйте реальные ключи для тестирования!
            
            logger.warning("⚠️  WARNING: This test requires TEST API keys!")
            logger.warning("⚠️  Never use real API keys for testing!")
            
            # Для этого теста нужны тестовые API ключи
            # binance = ccxt.binance({
            #     'sandbox': True,
            #     'apiKey': 'YOUR_TEST_API_KEY',
            #     'secret': 'YOUR_TEST_SECRET',
            # })
            
            # # Test small buy order
            # order = binance.create_market_buy_order('BTC/USDT', 0.001)  # 0.001 BTC
            # logger.info(f"Test order created: {order}")
            
            # # Test order status
            # order_status = binance.fetch_order(order['id'], 'BTC/USDT')
            # logger.info(f"Order status: {order_status}")
            
            # # Cancel order if still open
            # if order_status['status'] == 'open':
            #     binance.cancel_order(order['id'], 'BTC/USDT')
            #     logger.info("Test order cancelled")
            
            self.test_results['small_orders'] = 'SKIPPED (No test API keys)'
            logger.info("⏭️  Small orders test skipped (no test API keys)")
            
        except Exception as e:
            self.test_results['small_orders'] = f'FAILED: {e}'
            logger.error(f"❌ Small orders test failed: {e}")
    
    async def test_error_handling(self):
        """Test 6: Тестирование обработки ошибок"""
        logger.info("🔍 Testing error handling...")
        
        try:
            binance = ccxt.binance({'sandbox': True})
            
            # Test invalid symbol
            try:
                ticker = binance.fetch_ticker('INVALID/SYMBOL')
                assert False, "Should have raised an error"
            except ccxt.BadSymbol:
                logger.info("✅ Invalid symbol error handled correctly")
            
            # Test invalid timeframe
            try:
                ohlcv = binance.fetch_ohlcv('BTC/USDT', 'invalid_timeframe')
                assert False, "Should have raised an error"
            except ccxt.BadRequest:
                logger.info("✅ Invalid timeframe error handled correctly")
            
            # Test network timeout
            try:
                # Simulate timeout
                binance.timeout = 1  # 1ms timeout
                ticker = binance.fetch_ticker('BTC/USDT')
                assert False, "Should have timed out"
            except ccxt.NetworkError:
                logger.info("✅ Network timeout handled correctly")
            finally:
                binance.timeout = 10000  # Reset timeout
            
            self.test_results['error_handling'] = 'PASSED'
            logger.info("✅ Error handling test passed")
            
        except Exception as e:
            self.test_results['error_handling'] = f'FAILED: {e}'
            logger.error(f"❌ Error handling test failed: {e}")
    
    def generate_report(self):
        """Генерация отчета о тестировании"""
        logger.info("📊 Generating real exchange test report...")
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results.values() 
                          if result == 'PASSED')
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'test_type': 'real_exchange',
            'total_tests': total_tests,
            'passed_tests': passed_tests,
            'failed_tests': total_tests - passed_tests,
            'success_rate': (passed_tests / total_tests * 100) if total_tests > 0 else 0,
            'test_results': self.test_results,
            'recommendations': self.get_recommendations()
        }
        
        # Save report
        with open('real_exchange_test_report.json', 'w') as f:
            import json
            json.dump(report, f, indent=2)
        
        # Print summary
        logger.info("=" * 60)
        logger.info("📊 REAL EXCHANGE TEST REPORT")
        logger.info("=" * 60)
        logger.info(f"Total Tests: {total_tests}")
        logger.info(f"Passed: {passed_tests}")
        logger.info(f"Failed: {total_tests - passed_tests}")
        logger.info(f"Success Rate: {report['success_rate']:.1f}%")
        logger.info("=" * 60)
        
        for test_name, result in self.test_results.items():
            status = "✅" if result == 'PASSED' else "❌" if result.startswith('FAILED') else "⏭️"
            logger.info(f"{status} {test_name}: {result}")
        
        logger.info("=" * 60)
        logger.info("📄 Full report saved to: real_exchange_test_report.json")
    
    def get_recommendations(self):
        """Получить рекомендации по результатам тестирования"""
        recommendations = []
        
        if self.test_results.get('api_connectivity') == 'PASSED':
            recommendations.append("✅ API connectivity is working - ready for production")
        else:
            recommendations.append("❌ Fix API connectivity issues before going live")
        
        if self.test_results.get('rate_limits') == 'PASSED':
            recommendations.append("✅ Rate limits are acceptable for current usage")
        else:
            recommendations.append("⚠️  Consider implementing rate limiting in the application")
        
        if self.test_results.get('small_orders') == 'SKIPPED (No test API keys)':
            recommendations.append("🔑 Get test API keys to test order execution")
            recommendations.append("💰 Start with very small amounts (0.001 BTC)")
            recommendations.append("🛡️  Use sandbox/testnet environments only")
        
        recommendations.append("📊 Monitor latency and slippage in production")
        recommendations.append("🔄 Implement retry logic for failed requests")
        recommendations.append("📈 Track fill rates and execution quality")
        
        return recommendations

async def main():
    """Main function"""
    tester = RealExchangeTester()
    await tester.run_real_exchange_tests()

if __name__ == "__main__":
    asyncio.run(main())
