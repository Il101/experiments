#!/usr/bin/env python3
"""
Быстрый тест торгового цикла.

Этот скрипт:
1. Проверяет статус движка
2. Показывает результаты сканирования
3. Отслеживает генерацию сигналов
4. Мониторит открытие и закрытие позиций
"""

import asyncio
import aiohttp
import json
import time
from datetime import datetime

async def check_engine_status():
    """Проверяет статус движка."""
    async with aiohttp.ClientSession() as session:
        async with session.get('http://localhost:8000/api/engine/status') as response:
            return await response.json()

async def get_scan_results():
    """Получает результаты сканирования."""
    async with aiohttp.ClientSession() as session:
        async with session.get('http://localhost:8000/api/scanner/last') as response:
            return await response.json()

async def get_positions():
    """Получает позиции."""
    async with aiohttp.ClientSession() as session:
        async with session.get('http://localhost:8000/api/trading/positions') as response:
            return await response.json()

async def get_engine_metrics():
    """Получает метрики движка."""
    async with aiohttp.ClientSession() as session:
        async with session.get('http://localhost:8000/api/engine/metrics') as response:
            return await response.json()

async def monitor_trading_cycle():
    """Мониторит торговый цикл."""
    print("🔍 Мониторинг торгового цикла...")
    print("=" * 50)
    
    cycle_count = 0
    max_cycles = 20  # Максимум 20 циклов мониторинга
    
    while cycle_count < max_cycles:
        cycle_count += 1
        print(f"\n📊 Цикл {cycle_count} - {datetime.now().strftime('%H:%M:%S')}")
        
        try:
            # 1. Статус движка
            status = await check_engine_status()
            print(f"🎯 Состояние: {status.get('state', 'unknown')}")
            print(f"📈 Позиций: {status.get('openPositions', 0)}")
            print(f"💰 PnL: {status.get('dailyR', 0):.4f}")
            
            # 2. Результаты сканирования
            scan_data = await get_scan_results()
            candidates = scan_data.get('candidates', [])
            print(f"🔍 Кандидатов: {len(candidates)}")
            
            if candidates:
                best_candidate = candidates[0]
                print(f"🏆 Лучший: {best_candidate['symbol']} (score: {best_candidate['score']:.3f})")
                
                # Показываем фильтры
                filters = best_candidate.get('filters', {})
                passed_filters = [k for k, v in filters.items() if v]
                failed_filters = [k for k, v in filters.items() if not v]
                print(f"✅ Пройдено: {len(passed_filters)} фильтров")
                print(f"❌ Не пройдено: {len(failed_filters)} фильтров")
            
            # 3. Позиции
            positions_data = await get_positions()
            if isinstance(positions_data, list):
                positions = positions_data
            else:
                positions = positions_data.get('positions', [])
            print(f"💼 Позиций: {len(positions)}")
            
            if positions:
                for pos in positions:
                    print(f"  📊 {pos['symbol']}: {pos['side']} {pos['qty']} @ {pos['entry']}")
                    print(f"     SL: {pos['sl']}, TP: {pos.get('tp', 'N/A')}")
                    print(f"     Статус: {pos['status']}")
            
            # 4. Метрики
            metrics = await get_engine_metrics()
            print(f"📈 Всего сигналов: {metrics.get('totalSignals', 0)}")
            print(f"💼 Всего сделок: {metrics.get('totalTrades', 0)}")
            print(f"💰 PnL: {metrics.get('dailyPnlR', 0):.4f}")
            
            # Проверяем, есть ли активные позиции
            if positions:
                print("🎯 Есть активные позиции - отслеживаем их закрытие...")
                # Ждем дольше, чтобы отследить закрытие
                await asyncio.sleep(30)
            else:
                # Нет позиций - ждем меньше
                await asyncio.sleep(10)
                
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            await asyncio.sleep(5)
    
    print("\n🏁 Мониторинг завершен")

async def main():
    """Главная функция."""
    print("🚀 Быстрый тест торгового цикла")
    print("Убедитесь, что движок запущен: ./start.sh")
    print()
    
    # Проверяем, что движок запущен
    try:
        status = await check_engine_status()
        if status.get('state') == 'idle':
            print("⚠️ Движок не запущен. Запустите его командой:")
            print("curl -X POST -H 'Content-Type: application/json' -d '{\"preset\": \"breakout_v1\", \"mode\": \"paper\"}' http://localhost:8000/api/engine/start")
            return
    except Exception as e:
        print(f"❌ Не удалось подключиться к движку: {e}")
        print("Убедитесь, что API сервер запущен: ./start.sh")
        return
    
    await monitor_trading_cycle()

if __name__ == "__main__":
    asyncio.run(main())
