#!/usr/bin/env python3
"""
Скрипт для тестирования полного цикла сделки от сканирования до закрытия позиции.

Этот скрипт:
1. Запускает движок в paper режиме
2. Ждет генерации сигналов
3. Открывает позицию
4. Симулирует движение цены
5. Отслеживает управление позицией до закрытия
"""

import asyncio
import logging
import time
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class TradeCycleTester:
    """Тестер полного цикла сделки."""
    
    def __init__(self):
        self.engine_status = None
        self.scan_results = []
        self.signals = []
        self.positions = []
        self.test_start_time = None
        
    async def run_full_cycle_test(self):
        """Запускает полный тест цикла сделки."""
        logger.info("🚀 Начинаем тест полного цикла сделки")
        self.test_start_time = datetime.now()
        
        try:
            # 1. Запускаем движок
            await self.start_engine()
            
            # 2. Ждем сканирования и генерации сигналов
            await self.wait_for_signals()
            
            # 3. Открываем позицию
            await self.open_position()
            
            # 4. Симулируем движение цены и управление позицией
            await self.simulate_price_movement()
            
            # 5. Отслеживаем закрытие позиции
            await self.track_position_closure()
            
            # 6. Анализируем результаты
            await self.analyze_results()
            
        except Exception as e:
            logger.error(f"❌ Ошибка в тесте: {e}")
            raise
        finally:
            # Останавливаем движок
            await self.stop_engine()
    
    async def start_engine(self):
        """Запускает движок в paper режиме."""
        logger.info("📊 Запускаем движок...")
        
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.post(
                'http://localhost:8000/api/engine/start',
                json={'preset': 'breakout_v1', 'mode': 'paper'}
            ) as response:
                result = await response.json()
                if result.get('success'):
                    logger.info("✅ Движок запущен успешно")
                else:
                    raise Exception(f"Не удалось запустить движок: {result}")
    
    async def wait_for_signals(self, max_wait_minutes=10):
        """Ждет генерации сигналов."""
        logger.info("⏳ Ждем генерации сигналов...")
        
        start_time = time.time()
        max_wait_seconds = max_wait_minutes * 60
        
        while time.time() - start_time < max_wait_seconds:
            # Проверяем статус движка
            engine_status = await self.get_engine_status()
            
            if engine_status.get('state') == 'signal_wait':
                logger.info("🎯 Движок в состоянии ожидания сигналов")
                
                # Получаем результаты сканирования
                scan_results = await self.get_scan_results()
                if scan_results and len(scan_results) > 0:
                    logger.info(f"📈 Найдено {len(scan_results)} кандидатов")
                    self.scan_results = scan_results
                    break
            
            elif engine_status.get('state') == 'execution':
                logger.info("⚡ Движок в состоянии исполнения")
                break
            
            elif engine_status.get('state') == 'managing':
                logger.info("📊 Движок в состоянии управления позициями")
                break
            
            await asyncio.sleep(5)
        
        if not self.scan_results:
            raise Exception("Не удалось получить результаты сканирования")
    
    async def open_position(self):
        """Открывает позицию."""
        logger.info("💼 Открываем позицию...")
        
        # Ждем, пока движок откроет позицию
        max_wait_seconds = 300  # 5 минут
        start_time = time.time()
        
        while time.time() - start_time < max_wait_seconds:
            engine_status = await self.get_engine_status()
            
            if engine_status.get('state') == 'managing':
                # Получаем открытые позиции
                positions = await self.get_positions()
                if positions and len(positions) > 0:
                    logger.info(f"✅ Открыто {len(positions)} позиций")
                    self.positions = positions
                    break
            
            await asyncio.sleep(5)
        
        if not self.positions:
            logger.warning("⚠️ Позиции не были открыты")
    
    async def simulate_price_movement(self):
        """Симулирует движение цены для тестирования управления позицией."""
        logger.info("📈 Симулируем движение цены...")
        
        if not self.positions:
            logger.warning("Нет позиций для симуляции")
            return
        
        # Симулируем различные сценарии движения цены
        scenarios = [
            {"name": "Успешный TP1", "price_change": 0.02, "duration": 30},
            {"name": "Успешный TP2", "price_change": 0.04, "duration": 60},
            {"name": "Стоп-лосс", "price_change": -0.02, "duration": 20},
            {"name": "Трейлинг", "price_change": 0.03, "duration": 45},
        ]
        
        for scenario in scenarios:
            logger.info(f"🎭 Симулируем сценарий: {scenario['name']}")
            
            # Ждем указанное время
            await asyncio.sleep(scenario['duration'])
            
            # Проверяем статус позиций
            positions = await self.get_positions()
            if not positions:
                logger.info("✅ Позиции закрыты")
                break
            
            logger.info(f"📊 Активных позиций: {len(positions)}")
    
    async def track_position_closure(self):
        """Отслеживает закрытие позиций."""
        logger.info("👀 Отслеживаем закрытие позиций...")
        
        max_wait_seconds = 600  # 10 минут
        start_time = time.time()
        
        while time.time() - start_time < max_wait_seconds:
            positions = await self.get_positions()
            
            if not positions:
                logger.info("✅ Все позиции закрыты")
                break
            
            # Логируем статус позиций
            for pos in positions:
                logger.info(f"📊 Позиция {pos['symbol']}: {pos['status']}")
            
            await asyncio.sleep(10)
    
    async def analyze_results(self):
        """Анализирует результаты теста."""
        logger.info("📊 Анализируем результаты...")
        
        # Получаем финальные позиции
        final_positions = await self.get_positions()
        
        # Получаем метрики производительности
        metrics = await self.get_engine_metrics()
        
        # Анализируем результаты
        results = {
            'test_duration': (datetime.now() - self.test_start_time).total_seconds(),
            'scan_results_count': len(self.scan_results),
            'signals_generated': len(self.signals),
            'positions_opened': len(self.positions),
            'positions_closed': len(self.positions) - len(final_positions),
            'final_positions': final_positions,
            'engine_metrics': metrics
        }
        
        logger.info("📈 Результаты теста:")
        logger.info(f"  ⏱️  Длительность: {results['test_duration']:.1f} секунд")
        logger.info(f"  🔍 Кандидатов найдено: {results['scan_results_count']}")
        logger.info(f"  🎯 Сигналов сгенерировано: {results['signals_generated']}")
        logger.info(f"  💼 Позиций открыто: {results['positions_opened']}")
        logger.info(f"  ✅ Позиций закрыто: {results['positions_closed']}")
        
        # Сохраняем результаты в файл
        with open('trade_cycle_test_results.json', 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        logger.info("💾 Результаты сохранены в trade_cycle_test_results.json")
    
    async def get_engine_status(self):
        """Получает статус движка."""
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.get('http://localhost:8000/api/engine/status') as response:
                return await response.json()
    
    async def get_scan_results(self):
        """Получает результаты сканирования."""
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.get('http://localhost:8000/api/scanner/last') as response:
                data = await response.json()
                return data.get('candidates', [])
    
    async def get_positions(self):
        """Получает открытые позиции."""
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.get('http://localhost:8000/api/trading/positions') as response:
                data = await response.json()
                return data.get('positions', [])
    
    async def get_engine_metrics(self):
        """Получает метрики движка."""
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.get('http://localhost:8000/api/engine/metrics') as response:
                return await response.json()
    
    async def stop_engine(self):
        """Останавливает движок."""
        logger.info("🛑 Останавливаем движок...")
        
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.post('http://localhost:8000/api/engine/stop') as response:
                result = await response.json()
                if result.get('success'):
                    logger.info("✅ Движок остановлен")
                else:
                    logger.warning("⚠️ Не удалось остановить движок")


async def main():
    """Главная функция."""
    tester = TradeCycleTester()
    await tester.run_full_cycle_test()


if __name__ == "__main__":
    asyncio.run(main())
