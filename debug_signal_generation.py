#!/usr/bin/env python3
"""
Отладочный скрипт для проверки генерации сигналов.
"""

import asyncio
import logging
import sys
from pathlib import Path

# Добавить путь к модулям
sys.path.append('.')

from breakout_bot.config.settings import load_preset, SystemConfig
from breakout_bot.exchange.exchange_client import ExchangeClient, MarketDataProvider
from breakout_bot.scanner.market_scanner import BreakoutScanner
from breakout_bot.signals.signal_generator import SignalGenerator
from breakout_bot.data.models import MarketData

# Настроить логирование
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

async def debug_signal_generation():
    """Отладка генерации сигналов."""
    try:
        # Загрузить пресет
        preset = load_preset("breakout_v1_ultra_relaxed")
        
        # Создать системы
        config = SystemConfig(
            exchange="bybit",
            paper_mode=True,
            paper_starting_balance=10000,
            paper_slippage_bps=5
        )
        exchange_client = ExchangeClient(config)
        market_data_provider = MarketDataProvider(exchange_client, enable_websocket=False)
        scanner = BreakoutScanner(preset)
        signal_generator = SignalGenerator(preset)
        
        # Получить топ символы
        test_symbols = ['BTC/USDT:USDT', 'ETH/USDT:USDT', 'SOL/USDT:USDT']
        
        print(f"\n🔍 Тестируем генерацию сигналов:")
        
        for symbol in test_symbols:
            print(f"\n📊 Анализируем {symbol}:")
            
            try:
                # Получить market data
                market_data = await market_data_provider.get_market_data(symbol)
                if not market_data:
                    print(f"❌ Не удалось получить market data для {symbol}")
                    continue
                
                print(f"  📈 Market Data получен:")
                print(f"    - Цена: ${market_data.price:,.2f}")
                print(f"    - Объем 24h: ${market_data.volume_24h_usd:,.0f}")
                print(f"    - OI: ${market_data.oi_usd:,.0f}")
                print(f"    - Trades/min: {market_data.trades_per_minute:.1f}")
                print(f"    - ATR 15m: {market_data.atr_15m:.6f}")
                print(f"    - Свечи 5m: {len(market_data.candles_5m) if market_data.candles_5m else 0}")
                print(f"    - L2 Depth: {'✅' if market_data.l2_depth else '❌'}")
                
                # Сканировать рынок
                scan_result = await scanner._scan_single_market(market_data)
                if not scan_result:
                    print(f"  ❌ Сканирование не вернуло результат")
                    continue
                
                print(f"  🔍 Результат сканирования:")
                print(f"    - Прошел все фильтры: {'✅' if scan_result.passed_all_filters else '❌'}")
                print(f"    - Счет: {scan_result.score:.3f}")
                print(f"    - Уровни: {len(scan_result.levels) if scan_result.levels else 0}")
                
                if scan_result.levels:
                    for i, level in enumerate(scan_result.levels):
                        print(f"      Level {i+1}: {level.level_type} @ ${level.price:.2f} (strength: {level.strength:.3f})")
                
                # Попытаться сгенерировать сигнал
                signal = await signal_generator.generate_signal(scan_result)
                
                if signal:
                    print(f"  ✅ Сигнал сгенерирован:")
                    print(f"    - Тип: {signal.strategy}")
                    print(f"    - Сторона: {signal.side}")
                    print(f"    - Цена входа: ${signal.entry:.2f}")
                    print(f"    - Стоп лосс: ${signal.sl:.2f}")
                    print(f"    - Уверенность: {signal.confidence:.2f}")
                else:
                    print(f"  ❌ Сигнал не сгенерирован")
                    
                    # Детальная диагностика
                    if not scan_result.passed_all_filters:
                        failed_filters = [name for name, passed in scan_result.filter_results.items() if not passed]
                        print(f"    💥 Не прошли фильтры: {failed_filters}")
                    
                    if not scan_result.levels:
                        print(f"    💥 Нет торговых уровней")
                    
                    if not market_data.candles_5m or len(market_data.candles_5m) < 20:
                        print(f"    💥 Недостаточно свечей: {len(market_data.candles_5m) if market_data.candles_5m else 0} < 20")
                
            except Exception as e:
                print(f"❌ Ошибка при анализе {symbol}: {e}")
                import traceback
                traceback.print_exc()
        
        await exchange_client.close()
        
    except Exception as e:
        logger.error(f"Ошибка в отладке: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug_signal_generation())
