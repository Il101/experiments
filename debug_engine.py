"""
Отладка проблем с движком.
"""

import asyncio
import sys
import os
import traceback

# Добавить путь к проекту
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from breakout_bot.core.engine import OptimizedOrchestraEngine
from breakout_bot.config.settings import SystemConfig


async def debug_engine_startup():
    """Отладка запуска движка."""
    print("🔍 Отладка движка...")
    
    try:
        print("1. Создание системной конфигурации...")
        system_config = SystemConfig()
        system_config.trading_mode = 'paper'
        print("✅ SystemConfig создан")
        
        print("2. Создание движка...")
        engine = OptimizedOrchestraEngine(
            preset_name=None,
            system_config=system_config
        )
        print("✅ Движок создан")
        
        print("3. Инициализация движка...")
        await engine.initialize()
        print("✅ Движок инициализирован")
        
        print("4. Проверка статуса...")
        status = engine.get_status()
        print(f"✅ Статус: {status['status']}")
        print(f"   Состояние: {status.get('orchestrator', {}).get('current_state', 'unknown')}")
        
        print("5. Попытка запуска...")
        # Не запускаем полный цикл, только проверяем что start работает
        await engine.start()
        
        print("✅ Движок запущен успешно!")
        
        # Остановим для корректного завершения
        await engine.stop()
        print("✅ Движок остановлен")
        
        return True
        
    except Exception as e:
        print(f"❌ ОШИБКА: {e}")
        print("📍 Stack trace:")
        traceback.print_exc()
        return False


async def test_individual_components():
    """Тест отдельных компонентов."""
    print("\n🔧 Тестирование отдельных компонентов...")
    
    try:
        # Тест StateMachine
        from breakout_bot.core.state_machine import StateMachine, TradingState
        sm = StateMachine()
        print("✅ StateMachine работает")
        
        # Тест ErrorHandler  
        from breakout_bot.core.error_handler import ErrorHandler
        eh = ErrorHandler(max_retries=3)
        print("✅ ErrorHandler работает")
        
        # Тест других компонентов
        from breakout_bot.core.scanning_manager import ScanningManager
        from breakout_bot.core.signal_manager import SignalManager
        from breakout_bot.core.resource_manager import ResourceManager
        print("✅ Все компоненты импортируются корректно")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка в компонентах: {e}")
        traceback.print_exc()
        return False


async def check_dependencies():
    """Проверка зависимостей."""
    print("\n📦 Проверка зависимостей...")
    
    critical_imports = [
        'asyncio', 'logging', 'time', 'os', 
        'typing', 'datetime', 'uuid',
        'pydantic', 'psutil'
    ]
    
    for module_name in critical_imports:
        try:
            __import__(module_name)
            print(f"✅ {module_name}")
        except ImportError as e:
            print(f"❌ {module_name}: {e}")
            return False
    
    # Проверка внутренних модулей
    internal_modules = [
        'breakout_bot.config',
        'breakout_bot.exchange', 
        'breakout_bot.scanner',
        'breakout_bot.signals',
        'breakout_bot.risk',
        'breakout_bot.position'
    ]
    
    for module_name in internal_modules:
        try:
            __import__(module_name)
            print(f"✅ {module_name}")
        except ImportError as e:
            print(f"❌ {module_name}: {e}")
            return False
    
    return True


async def main():
    """Главная функция отладки."""
    print("🚨 ОТЛАДКА ПРОБЛЕМ С ДВИЖКОМ\n")
    
    # 1. Проверка зависимостей
    deps_ok = await check_dependencies()
    if not deps_ok:
        print("\n❌ Проблемы с зависимостями!")
        return False
    
    # 2. Тест компонентов
    components_ok = await test_individual_components()
    if not components_ok:
        print("\n❌ Проблемы с компонентами!")
        return False
    
    # 3. Тест запуска движка
    engine_ok = await debug_engine_startup()
    if not engine_ok:
        print("\n❌ Проблемы с запуском движка!")
        return False
    
    print("\n🎉 ВСЕ РАБОТАЕТ НОРМАЛЬНО!")
    print("Возможно проблема в способе запуска или конфигурации.")
    print("Как именно вы пытаетесь запустить движок?")
    
    return True


if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        if not success:
            print("\n💡 РЕКОМЕНДАЦИИ:")
            print("1. Проверьте переменные окружения")
            print("2. Убедитесь что все зависимости установлены")
            print("3. Проверьте файлы конфигурации")
            print("4. Попробуйте запустить в режиме paper trading")
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⏹️ Отладка прервана")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Критическая ошибка в отладке: {e}")
        traceback.print_exc()
        sys.exit(1)



