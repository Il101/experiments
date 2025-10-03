#!/usr/bin/env python3
"""
Быстрая диагностика бота - одна команда для проверки всего.
"""

import subprocess
import sys
import os


def print_header(text: str):
    """Печать заголовка."""
    print("\n" + "="*80)
    print(f"  {text}")
    print("="*80 + "\n")


def check_env_settings():
    """Проверка настроек в .env."""
    print_header("🔧 НАСТРОЙКИ .env")
    
    if not os.path.exists('.env'):
        print("❌ Файл .env не найден!")
        return False
        
    with open('.env', 'r') as f:
        content = f.read()
        
    settings = {
        'ENGINE_MARKET_FETCH_LIMIT': None,
        'LIVE_SCAN_CONCURRENCY': None,
        'MARKET_DATA_TIMEOUT': None
    }
    
    for line in content.split('\n'):
        for key in settings.keys():
            if line.startswith(key):
                # Extract value
                value = line.split('=')[1].split('#')[0].strip()
                settings[key] = value
                
    print("Текущие настройки:")
    for key, value in settings.items():
        if value:
            print(f"  ✅ {key}: {value}")
        else:
            print(f"  ❌ {key}: НЕ УСТАНОВЛЕН")
            
    # Проверка рекомендованных значений
    print("\nРекомендации:")
    
    all_good = True
    
    if not settings['ENGINE_MARKET_FETCH_LIMIT']:
        print("  ⚠️  Установите ENGINE_MARKET_FETCH_LIMIT=50")
        all_good = False
    elif int(settings['ENGINE_MARKET_FETCH_LIMIT']) > 100:
        print(f"  ⚠️  {settings['ENGINE_MARKET_FETCH_LIMIT']} символов может быть слишком много")
        print("     Рекомендуется 30-50 для стабильной работы")
        
    if not settings['LIVE_SCAN_CONCURRENCY']:
        print("  ⚠️  Установите LIVE_SCAN_CONCURRENCY=15")
        all_good = False
    elif int(settings['LIVE_SCAN_CONCURRENCY']) > 25:
        print(f"  ⚠️  Concurrency {settings['LIVE_SCAN_CONCURRENCY']} может вызвать rate limits")
        
    if not settings['MARKET_DATA_TIMEOUT']:
        print("  ⚠️  Установите MARKET_DATA_TIMEOUT=120")
        all_good = False
        
    if all_good:
        print("  ✅ Все настройки оптимальны!")
        
    return all_good


def check_bot_status():
    """Проверка статуса бота."""
    print_header("🤖 СТАТУС БОТА")
    
    # Проверка процесса
    result = subprocess.run(
        ['ps', 'aux'],
        capture_output=True,
        text=True
    )
    
    if 'breakout_bot' in result.stdout or 'start.sh' in result.stdout:
        print("✅ Бот запущен")
        
        # Показать процессы
        for line in result.stdout.split('\n'):
            if 'breakout_bot' in line or 'start.sh' in line:
                # Упростить вывод
                parts = line.split()
                if len(parts) >= 11:
                    cpu = parts[2]
                    mem = parts[3]
                    print(f"   PID: {parts[1]}, CPU: {cpu}%, MEM: {mem}%")
        
        return True
    else:
        print("❌ Бот не запущен")
        print("\nЗапустите бот командой:")
        print("   ./start.sh")
        return False


def run_pipeline_check():
    """Запуск проверки пайплайна."""
    print_header("🔍 ПРОВЕРКА ПАЙПЛАЙНА")
    
    try:
        subprocess.run(
            ['python3', 'check_bot_pipeline.py'],
            check=True
        )
        return True
    except subprocess.CalledProcessError:
        print("❌ Ошибка при проверке пайплайна")
        return False
    except FileNotFoundError:
        print("❌ Скрипт check_bot_pipeline.py не найден")
        return False


def print_summary(env_ok: bool, bot_running: bool):
    """Печать итоговой сводки."""
    print_header("📋 ИТОГОВАЯ СВОДКА")
    
    if env_ok and bot_running:
        print("✅ Все проверки пройдены!")
        print("\n📊 Следующие шаги:")
        print("   1. Мониторьте логи: tail -f logs/general.log")
        print("   2. Проверяйте метрики периодически")
        print("   3. При проблемах запустите: python3 test_bybit_data_fetching.py")
    elif not bot_running:
        print("⚠️  Бот не запущен")
        print("\n🔧 Действия:")
        print("   1. Запустите бот: ./start.sh")
        print("   2. Подождите 2-3 минуты")
        print("   3. Запустите эту проверку снова")
    elif not env_ok:
        print("⚠️  Настройки не оптимальны")
        print("\n🔧 Действия:")
        print("   1. Обновите .env согласно рекомендациям выше")
        print("   2. Перезапустите бот: ./stop.sh && ./start.sh")
        print("   3. Запустите эту проверку снова")
    else:
        print("⚠️  Обнаружены проблемы")
        print("\n🔧 Действия:")
        print("   1. Проверьте детали выше")
        print("   2. Исправьте проблемы")
        print("   3. Перезапустите бот")


def main():
    """Главная функция."""
    print("="*80)
    print("  🚀 БЫСТРАЯ ДИАГНОСТИКА БОТА")
    print("="*80)
    
    # Проверки
    env_ok = check_env_settings()
    bot_running = check_bot_status()
    
    if bot_running:
        run_pipeline_check()
    
    print_summary(env_ok, bot_running)
    
    print("\n✅ Диагностика завершена!\n")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Диагностика прервана")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
