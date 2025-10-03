#!/usr/bin/env python3
"""
Симулятор движения цены для тестирования управления позициями.

Этот скрипт симулирует различные сценарии движения цены:
1. Успешный TP1
2. Успешный TP2  
3. Стоп-лосс
4. Трейлинг-стоп
5. Add-on позиции
"""

import asyncio
import aiohttp
import json
import time
import random
from datetime import datetime

class PriceSimulator:
    """Симулятор движения цены."""
    
    def __init__(self):
        self.base_price = 100.0
        self.current_price = 100.0
        self.positions = []
        self.scenarios = [
            {"name": "Успешный TP1", "target_change": 0.02, "duration": 60},
            {"name": "Успешный TP2", "target_change": 0.04, "duration": 120},
            {"name": "Стоп-лосс", "target_change": -0.02, "duration": 30},
            {"name": "Трейлинг", "target_change": 0.03, "duration": 90},
            {"name": "Add-on", "target_change": 0.01, "duration": 45},
        ]
    
    async def get_positions(self):
        """Получает текущие позиции."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get('http://localhost:8000/api/trading/positions') as response:
                    data = await response.json()
                    return data.get('positions', [])
        except Exception as e:
            print(f"❌ Ошибка получения позиций: {e}")
            return []
    
    async def simulate_scenario(self, scenario):
        """Симулирует конкретный сценарий."""
        print(f"\n🎭 Симулируем сценарий: {scenario['name']}")
        print(f"🎯 Целевое изменение: {scenario['target_change']*100:.1f}%")
        print(f"⏱️ Длительность: {scenario['duration']} секунд")
        
        start_time = time.time()
        target_price = self.current_price * (1 + scenario['target_change'])
        
        # Симулируем плавное движение к целевой цене
        steps = scenario['duration'] // 5  # Обновляем каждые 5 секунд
        price_step = (target_price - self.current_price) / steps
        
        for step in range(steps):
            # Добавляем небольшую случайность
            noise = random.uniform(-0.001, 0.001)  # ±0.1% шум
            self.current_price += price_step + (self.current_price * noise)
            
            print(f"📈 Цена: {self.current_price:.4f} (изменение: {(self.current_price/self.base_price - 1)*100:.2f}%)")
            
            # Проверяем позиции
            positions = await self.get_positions()
            if positions:
                print(f"💼 Активных позиций: {len(positions)}")
                for pos in positions:
                    pnl = self.calculate_pnl(pos)
                    print(f"  📊 {pos['symbol']}: PnL = {pnl:.2f}%")
            
            await asyncio.sleep(5)
        
        print(f"✅ Сценарий '{scenario['name']}' завершен")
        print(f"📈 Финальная цена: {self.current_price:.4f}")
    
    def calculate_pnl(self, position):
        """Рассчитывает PnL позиции."""
        if position['side'] == 'long':
            return ((self.current_price - position['entry']) / position['entry']) * 100
        else:
            return ((position['entry'] - self.current_price) / position['entry']) * 100
    
    async def run_simulation(self):
        """Запускает полную симуляцию."""
        print("🚀 Запускаем симуляцию движения цены")
        print("=" * 50)
        
        # Получаем начальные позиции
        initial_positions = await self.get_positions()
        if not initial_positions:
            print("⚠️ Нет активных позиций для симуляции")
            print("Запустите движок и дождитесь открытия позиций")
            return
        
        print(f"📊 Начальные позиции: {len(initial_positions)}")
        for pos in initial_positions:
            print(f"  📈 {pos['symbol']}: {pos['side']} {pos['qty']} @ {pos['entry']}")
            print(f"     SL: {pos['sl']}, TP: {pos.get('tp', 'N/A')}")
        
        # Симулируем каждый сценарий
        for scenario in self.scenarios:
            await self.simulate_scenario(scenario)
            
            # Проверяем, есть ли еще позиции
            positions = await self.get_positions()
            if not positions:
                print("✅ Все позиции закрыты - симуляция завершена")
                break
            
            print(f"💼 Осталось позиций: {len(positions)}")
            
            # Небольшая пауза между сценариями
            await asyncio.sleep(10)
        
        # Финальная проверка
        final_positions = await self.get_positions()
        print(f"\n🏁 Симуляция завершена")
        print(f"📊 Финальных позиций: {len(final_positions)}")
        print(f"📈 Финальная цена: {self.current_price:.4f}")
        print(f"📊 Общее изменение: {(self.current_price/self.base_price - 1)*100:.2f}%")

async def main():
    """Главная функция."""
    simulator = PriceSimulator()
    await simulator.run_simulation()

if __name__ == "__main__":
    asyncio.run(main())
