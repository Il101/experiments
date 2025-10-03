#!/usr/bin/env python3
"""
Тестирование расслабленного пресета для увеличения количества сигналов.
"""

import asyncio
import json
import logging
from datetime import datetime
import sys
import os

# Добавляем путь к модулю
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from breakout_bot.config.settings import load_preset
from breakout_bot.core.engine import OptimizedOrchestraEngine
from breakout_bot.config.settings import SystemConfig

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_relaxed_preset():
    """Тестирует расслабленный пресет."""
    print("🧪 ТЕСТИРОВАНИЕ РАССЛАБЛЕННОГО ПРЕСЕТА")
    print("=" * 50)
    
    try:
        # Загружаем расслабленный пресет
        preset = load_preset("breakout_v1_relaxed")
        print(f"✅ Загружен пресет: {preset.name}")
        print(f"📋 Описание: {preset.description}")
        
        # Создаем конфигурацию системы
        config = SystemConfig(
            trading_mode="paper",
            paper_mode=True,
            preset_name="breakout_v1_relaxed"
        )
        
        # Создаем движок
        engine = OptimizedOrchestraEngine(config)
        print("✅ Движок создан")
        
        # Запускаем инициализацию
        await engine.initialize()
        print("✅ Движок инициализирован")
        
        # Запускаем сканирование
        print("\n🔍 Запуск сканирования...")
        await engine._scan_markets()
        
        # Получаем результаты сканирования
        if hasattr(engine, 'scanner') and hasattr(engine.scanner, 'last_scan_results'):
            results = engine.scanner.last_scan_results
            print(f"📊 Найдено кандидатов: {len(results)}")
            
            # Показываем топ-5 результатов
            if results:
                print("\n🏆 ТОП-5 КАНДИДАТОВ:")
                for i, result in enumerate(results[:5], 1):
                    print(f"  {i}. {result.symbol}: оценка {result.score:.2f}")
                    if hasattr(result, 'filter_results'):
                        passed = sum(1 for r in result.filter_results.values() if r.passed)
                        total = len(result.filter_results)
                        print(f"     Фильтры: {passed}/{total} пройдено")
            
            # Генерируем сигналы
            print("\n⚡ Генерация сигналов...")
            if hasattr(engine, 'signal_generator'):
                signals = engine.signal_generator.generate_signals(results)
                print(f"🎯 Сгенерировано сигналов: {len(signals)}")
                
                if signals:
                    print("\n📈 СИГНАЛЫ:")
                    for i, signal in enumerate(signals[:3], 1):
                        print(f"  {i}. {signal.symbol}: {signal.strategy} (уверенность: {signal.confidence:.2f})")
                        print(f"     Направление: {signal.direction}, Уровень: {signal.level_price:.4f}")
        else:
            print("❌ Нет результатов сканирования")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка тестирования: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Главная функция."""
    success = await test_relaxed_preset()
    
    if success:
        print("\n✅ Тестирование завершено успешно")
        print("💡 Рекомендация: Используйте расслабленный пресет для увеличения сигналов")
    else:
        print("\n❌ Тестирование завершилось с ошибками")

if __name__ == "__main__":
    asyncio.run(main())

