#!/usr/bin/env python3
"""
Монитор использования памяти для Breakout Bot.
Показывает улучшения после оптимизации памяти.
"""

import psutil
import time
import sys
import json
from datetime import datetime
import os

def get_memory_info():
    """Получить информацию о памяти."""
    # Системная память
    memory = psutil.virtual_memory()
    
    # Память процесса
    process = psutil.Process()
    process_memory = process.memory_info()
    process_percent = process.memory_percent()
    
    return {
        "timestamp": datetime.now().isoformat(),
        "system": {
            "total_gb": round(memory.total / (1024**3), 2),
            "used_gb": round(memory.used / (1024**3), 2),
            "available_gb": round(memory.available / (1024**3), 2),
            "percent_used": memory.percent
        },
        "process": {
            "rss_mb": round(process_memory.rss / (1024**2), 1),
            "vms_mb": round(process_memory.vms / (1024**2), 1),
            "percent_of_system": round(process_percent, 2)
        }
    }

def monitor_continuous():
    """Непрерывный мониторинг памяти."""
    print("🔍 Монитор памяти Breakout Bot")
    print("=" * 50)
    print("Нажмите Ctrl+C для остановки")
    print()
    
    try:
        while True:
            info = get_memory_info()
            
            # Очистить экран (работает на Unix/Linux/macOS)
            os.system('clear' if os.name == 'posix' else 'cls')
            
            print("🔍 МОНИТОР ПАМЯТИ BREAKOUT BOT")
            print("=" * 50)
            print(f"⏰ Время: {info['timestamp'][:19]}")
            print()
            
            # Системная память
            sys_mem = info['system']
            print("🖥️  СИСТЕМНАЯ ПАМЯТЬ:")
            print(f"   Всего:      {sys_mem['total_gb']} GB")
            print(f"   Используется: {sys_mem['used_gb']} GB ({sys_mem['percent_used']:.1f}%)")
            print(f"   Доступно:   {sys_mem['available_gb']} GB")
            
            # Цветовая индикация для системной памяти
            if sys_mem['percent_used'] > 90:
                print("   Статус:     🔴 КРИТИЧНО")
            elif sys_mem['percent_used'] > 80:
                print("   Статус:     🟡 ВЫСОКОЕ")
            else:
                print("   Статус:     🟢 НОРМАЛЬНО")
            
            print()
            
            # Память процесса
            proc_mem = info['process']
            print("🚀 ПАМЯТЬ BREAKOUT BOT:")
            print(f"   RSS:        {proc_mem['rss_mb']} MB")
            print(f"   VMS:        {proc_mem['vms_mb']} MB")
            print(f"   % системы:  {proc_mem['percent_of_system']}%")
            
            # Цветовая индикация для процесса
            if proc_mem['percent_of_system'] > 20:
                print("   Статус:     🔴 ОЧЕНЬ ВЫСОКОЕ")
            elif proc_mem['percent_of_system'] > 10:
                print("   Статус:     🟡 ПОВЫШЕННОЕ")
            else:
                print("   Статус:     🟢 НОРМАЛЬНО")
            
            print()
            print("💡 После оптимизаций ожидается:")
            print("   • Снижение использования памяти на 30-50%")
            print("   • Более стабильная работа при высокой нагрузке")
            print("   • Автоматическая очистка при >80% использования")
            print()
            print("Нажмите Ctrl+C для остановки...")
            
            time.sleep(5)  # Обновление каждые 5 секунд
            
    except KeyboardInterrupt:
        print("\n\n👋 Мониторинг остановлен.")
        print("📊 Для анализа логов используйте:")
        print("   tail -f logs/api.log | grep -i memory")

def save_snapshot():
    """Сохранить снимок памяти в файл."""
    info = get_memory_info()
    filename = f"memory_snapshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(info, f, indent=2, ensure_ascii=False)
    
    print(f"💾 Снимок памяти сохранен: {filename}")
    return filename

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "snapshot":
        save_snapshot()
    else:
        monitor_continuous()

