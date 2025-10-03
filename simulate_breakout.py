#!/usr/bin/env python3
"""
Симуляция пробоя для генерации сигнала.

Этот скрипт симулирует движение цены, которое может вызвать генерацию сигнала.
"""

import asyncio
import aiohttp
import json
import time
from datetime import datetime

class BreakoutSimulator:
    """Симулятор пробоя для генерации сигналов."""
    
    def __init__(self):
        self.base_url = "http://localhost:8000/api"
        self.symbol = None
        self.levels = []
        self.current_price = None
    
    async def get_best_candidate(self):
        """Получает лучшего кандидата."""
        async with aiohttp.ClientSession() as session:
            async with session.get(f'{self.base_url}/scanner/last') as response:
                data = await response.json()
                candidates = data.get('candidates', [])
                
                if not candidates:
                    print("❌ Нет кандидатов")
                    return None
                
                # Ищем кандидата с хорошими уровнями
                for candidate in candidates:
                    if candidate.get('levels') and len(candidate['levels']) > 0:
                        self.symbol = candidate['symbol']
                        self.levels = candidate['levels']
                        self.current_price = candidate.get('current_price', 100.0)
                        print(f"🎯 Выбран кандидат: {self.symbol}")
                        print(f"📊 Уровней: {len(self.levels)}")
                        print(f"💰 Текущая цена: {self.current_price}")
                        return candidate
                
                print("❌ Нет кандидатов с уровнями")
                return None
    
    async def simulate_breakout(self):
        """Симулирует пробой уровня."""
        if not self.levels:
            print("❌ Нет уровней для симуляции")
            return
        
        # Берем первый уровень (самый сильный)
        level = self.levels[0]
        level_price = level['price']
        level_type = level['level_type']
        
        print(f"🎯 Симулируем пробой уровня:")
        print(f"  Тип: {level_type}")
        print(f"  Цена: {level_price:.6f}")
        print(f"  Сила: {level['strength']:.3f}")
        
        # Симулируем движение цены к уровню и пробой
        if level_type == 'resistance':
            # Для сопротивления - движение вверх с пробоем
            target_price = level_price * 1.005  # 0.5% выше уровня
            print(f"📈 Целевая цена (пробой сопротивления): {target_price:.6f}")
        else:
            # Для поддержки - движение вниз с пробоем
            target_price = level_price * 0.995  # 0.5% ниже уровня
            print(f"📉 Целевая цена (пробой поддержки): {target_price:.6f}")
        
        # Симулируем постепенное движение к цели
        steps = 10
        price_step = (target_price - self.current_price) / steps
        
        print(f"🔄 Симулируем движение цены...")
        for i in range(steps):
            self.current_price += price_step
            print(f"  Шаг {i+1}/{steps}: {self.current_price:.6f}")
            await asyncio.sleep(1)
        
        print(f"✅ Симуляция завершена. Финальная цена: {self.current_price:.6f}")
    
    async def check_for_signals(self):
        """Проверяет, появились ли сигналы."""
        print("🔍 Проверяем генерацию сигналов...")
        
        async with aiohttp.ClientSession() as session:
            # Проверяем статус движка
            async with session.get(f'{self.base_url}/engine/status') as response:
                status = await response.json()
                print(f"🎯 Состояние движка: {status.get('state')}")
                
                if status.get('state') == 'sizing':
                    print("✅ Движок перешел в состояние SIZING - сигналы найдены!")
                    return True
                elif status.get('state') == 'execution':
                    print("✅ Движок перешел в состояние EXECUTION - позиции открываются!")
                    return True
                elif status.get('state') == 'managing':
                    print("✅ Движок перешел в состояние MANAGING - позиции открыты!")
                    return True
                else:
                    print("⏳ Движок все еще в состоянии ожидания сигналов")
                    return False
    
    async def run_simulation(self):
        """Запускает полную симуляцию."""
        print("🚀 Запуск симуляции пробоя")
        print("=" * 50)
        
        # 1. Получаем кандидата
        candidate = await self.get_best_candidate()
        if not candidate:
            return
        
        # 2. Симулируем пробой
        await self.simulate_breakout()
        
        # 3. Ждем и проверяем генерацию сигналов
        print("\n⏳ Ждем генерации сигналов...")
        for i in range(10):  # Проверяем 10 раз
            print(f"  Проверка {i+1}/10...")
            if await self.check_for_signals():
                break
            await asyncio.sleep(5)
        
        print("\n🏁 Симуляция завершена")

async def main():
    """Главная функция."""
    simulator = BreakoutSimulator()
    await simulator.run_simulation()

if __name__ == "__main__":
    asyncio.run(main())
