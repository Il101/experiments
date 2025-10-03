#!/usr/bin/env python3
"""
Простой тест для проверки работы системы с новым пресетом.
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

def test_preset_loading():
    """Тестирует загрузку пресетов."""
    print("🧪 ТЕСТИРОВАНИЕ ЗАГРУЗКИ ПРЕСЕТОВ")
    print("=" * 50)
    
    presets = ["breakout_v1", "breakout_v1_relaxed", "breakout_v1_aggressive"]
    
    for preset_name in presets:
        try:
            preset = load_preset(preset_name)
            print(f"✅ {preset_name}: Загружен успешно")
            print(f"   📋 Описание: {preset.description}")
            print(f"   💰 Мин. объем: ${preset.liquidity_filters.min_24h_volume_usd:,}")
            print(f"   📊 Макс. спред: {preset.liquidity_filters.max_spread_bps} bps")
            print(f"   🎯 Кандидатов: {preset.scanner_config.max_candidates}")
            print()
        except Exception as e:
            print(f"❌ {preset_name}: Ошибка загрузки - {e}")
            print()

def main():
    """Главная функция."""
    test_preset_loading()
    
    print("💡 РЕКОМЕНДАЦИИ:")
    print("1. Используйте 'breakout_v1_relaxed' для более мягких фильтров")
    print("2. Используйте 'breakout_v1_aggressive' для максимального количества сигналов")
    print("3. Перезапустите систему с новым пресетом:")
    print("   curl -X POST http://localhost:8000/api/engine/start \\")
    print("     -H 'Content-Type: application/json' \\")
    print("     -d '{\"preset\": \"breakout_v1_relaxed\"}'")

if __name__ == "__main__":
    main()

