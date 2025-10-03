#!/usr/bin/env python3
"""
Проверка доступности API эндпоинтов для тестирования торгового цикла.
"""

import asyncio
import aiohttp
import json

async def check_endpoint(session, url, name):
    """Проверяет доступность эндпоинта."""
    try:
        async with session.get(url) as response:
            data = await response.json()
            print(f"✅ {name}: {response.status}")
            return True, data
    except Exception as e:
        print(f"❌ {name}: {e}")
        return False, None

async def main():
    """Проверяет все необходимые эндпоинты."""
    print("🔍 Проверка API эндпоинтов...")
    print("=" * 40)
    
    base_url = "http://localhost:8000/api"
    endpoints = [
        (f"{base_url}/engine/status", "Статус движка"),
        (f"{base_url}/engine/metrics", "Метрики движка"),
        (f"{base_url}/scanner/last", "Результаты сканирования"),
        (f"{base_url}/trading/positions", "Позиции"),
        (f"{base_url}/monitoring/current-session", "Текущая сессия"),
    ]
    
    async with aiohttp.ClientSession() as session:
        results = {}
        
        for url, name in endpoints:
            success, data = await check_endpoint(session, url, name)
            results[name] = {"success": success, "data": data}
        
        print("\n📊 Сводка:")
        for name, result in results.items():
            status = "✅" if result["success"] else "❌"
            print(f"  {status} {name}")
        
        # Показываем детали для успешных эндпоинтов
        print("\n📈 Детали:")
        
        if results["Статус движка"]["success"]:
            status_data = results["Статус движка"]["data"]
            print(f"  🎯 Состояние: {status_data.get('state', 'unknown')}")
            print(f"  📈 Позиций: {status_data.get('openPositions', 0)}")
            print(f"  💰 PnL: {status_data.get('dailyR', 0):.4f}")
        
        if results["Результаты сканирования"]["success"]:
            scan_data = results["Результаты сканирования"]["data"]
            candidates = scan_data.get('candidates', [])
            print(f"  🔍 Кандидатов: {len(candidates)}")
            if candidates:
                best = candidates[0]
                print(f"  🏆 Лучший: {best['symbol']} (score: {best['score']:.3f})")
        
        if results["Позиции"]["success"]:
            positions_data = results["Позиции"]["data"]
            if isinstance(positions_data, list):
                positions = positions_data
            else:
                positions = positions_data.get('positions', [])
            print(f"  💼 Позиций: {len(positions)}")
            for pos in positions:
                print(f"    📊 {pos['symbol']}: {pos['side']} {pos['qty']} @ {pos['entry']}")

if __name__ == "__main__":
    asyncio.run(main())
