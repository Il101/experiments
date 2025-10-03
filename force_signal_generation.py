#!/usr/bin/env python3
"""
Принудительная генерация сигналов для тестирования.

Этот скрипт:
1. Получает лучшего кандидата с уровнями
2. Принудительно генерирует сигнал
3. Отправляет его в движок для тестирования
"""

import asyncio
import aiohttp
import json
from datetime import datetime

async def force_signal_generation():
    """Принудительно генерирует сигнал для тестирования."""
    print("🎯 Принудительная генерация сигнала для тестирования")
    print("=" * 60)
    
    # 1. Получаем лучшего кандидата с уровнями
    async with aiohttp.ClientSession() as session:
        async with session.get('http://localhost:8000/api/scanner/last') as response:
            scan_data = await response.json()
            candidates = scan_data.get('candidates', [])
            
            if not candidates:
                print("❌ Нет кандидатов для генерации сигнала")
                return
            
            # Ищем кандидата с уровнями
            best_candidate = None
            for candidate in candidates:
                if candidate.get('levels') and len(candidate['levels']) > 0:
                    best_candidate = candidate
                    break
            
            if not best_candidate:
                print("❌ Нет кандидатов с уровнями")
                return
            
            print(f"🏆 Выбран кандидат: {best_candidate['symbol']}")
            print(f"📊 Score: {best_candidate['score']:.3f}")
            print(f"📈 Уровней: {len(best_candidate['levels'])}")
            print(f"✅ Пройдено фильтров: {sum(1 for v in best_candidate['filters'].values() if v)}/10")
            
            # 2. Берем лучший уровень
            best_level = best_candidate['levels'][0]
            print(f"🎯 Лучший уровень:")
            print(f"  Тип: {best_level['level_type']}")
            print(f"  Цена: {best_level['price']:.6f}")
            print(f"  Сила: {best_level['strength']:.3f}")
            print(f"  Касаний: {best_level['touch_count']}")
            
            # 3. Создаем принудительный сигнал
            signal = {
                "symbol": best_candidate['symbol'],
                "side": "long" if best_level['level_type'] == 'resistance' else 'short',
                "strategy": "momentum",
                "entry_price": best_level['price'] * 1.001,  # Немного выше уровня
                "stop_loss": best_level['price'] * 0.995,   # Немного ниже уровня
                "confidence": 0.8,
                "meta": {
                    "forced": True,
                    "reason": "Принудительная генерация для тестирования полного цикла",
                    "level_price": best_level['price'],
                    "level_strength": best_level['strength'],
                    "timestamp": int(datetime.now().timestamp() * 1000)
                }
            }
            
            print(f"\n📝 Создан принудительный сигнал:")
            print(f"  Symbol: {signal['symbol']}")
            print(f"  Side: {signal['side']}")
            print(f"  Entry: {signal['entry_price']:.6f}")
            print(f"  Stop Loss: {signal['stop_loss']:.6f}")
            print(f"  Confidence: {signal['confidence']}")
            
            # 4. Показываем, что мы не можем отправить сигнал через API
            print(f"\n⚠️  Примечание:")
            print(f"  API не поддерживает принудительную генерацию сигналов.")
            print(f"  Сигналы генерируются только для кандидатов, прошедших ВСЕ фильтры.")
            print(f"  Текущий кандидат прошел только {sum(1 for v in best_candidate['filters'].values() if v)}/10 фильтров.")
            
            # 5. Предлагаем решение
            print(f"\n💡 Решения:")
            print(f"  1. Ослабить фильтры в пресете breakout_v1")
            print(f"  2. Добавить whitelist качественных токенов")
            print(f"  3. Создать тестовый режим с принудительными сигналами")
            
            # 6. Показываем, какие фильтры не прошли
            failed_filters = [name for name, passed in best_candidate['filters'].items() if not passed]
            print(f"\n❌ Не пройденные фильтры:")
            for filter_name in failed_filters:
                print(f"  - {filter_name}")
            
            # 7. Показываем, как можно исправить
            print(f"\n🔧 Рекомендации по исправлению:")
            if 'min_24h_volume' in failed_filters:
                print(f"  - Увеличить min_24h_volume_usd в пресете")
            if 'max_spread' in failed_filters:
                print(f"  - Увеличить max_spread_bps в пресете")
            if 'min_depth_0_5pct' in failed_filters or 'min_depth_0_3pct' in failed_filters:
                print(f"  - Уменьшить min_depth_usd_0_5pct и min_depth_usd_0_3pct в пресете")
            if 'atr_range' in failed_filters:
                print(f"  - Настроить atr_range_min и atr_range_max в пресете")

if __name__ == "__main__":
    asyncio.run(force_signal_generation())