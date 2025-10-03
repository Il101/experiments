#!/usr/bin/env python3
"""
Сравнение оригинального и расслабленного пресетов.
"""

import json
import sys
import os

# Добавляем путь к модулю
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from breakout_bot.config.settings import load_preset

def compare_presets():
    """Сравнивает два пресета."""
    print("📊 СРАВНЕНИЕ ПРЕСЕТОВ")
    print("=" * 60)
    
    try:
        # Загружаем оба пресета
        original = load_preset("breakout_v1")
        relaxed = load_preset("breakout_v1_relaxed")
        
        print(f"🔍 Оригинальный: {original.name}")
        print(f"🔍 Расслабленный: {relaxed.name}")
        print()
        
        # Сравниваем фильтры ликвидности
        print("💧 ФИЛЬТРЫ ЛИКВИДНОСТИ:")
        print("-" * 40)
        
        fields = [
            ("min_24h_volume_usd", "Мин. объем 24ч", "USD"),
            ("min_oi_usd", "Мин. OI", "USD"),
            ("max_spread_bps", "Макс. спред", "bps"),
            ("min_depth_usd_0_5pct", "Мин. глубина 0.5%", "USD"),
            ("min_depth_usd_0_3pct", "Мин. глубина 0.3%", "USD"),
            ("min_trades_per_minute", "Мин. сделок/мин", "шт")
        ]
        
        for field, name, unit in fields:
            orig_val = getattr(original.liquidity_filters, field)
            relax_val = getattr(relaxed.liquidity_filters, field)
            
            if unit == "USD":
                orig_str = f"${orig_val:,.0f}"
                relax_str = f"${relax_val:,.0f}"
            else:
                orig_str = f"{orig_val:.1f}"
                relax_str = f"{relax_val:.1f}"
            
            change = "📈" if relax_val < orig_val else "📉" if relax_val > orig_val else "➡️"
            print(f"  {name:20} | {orig_str:>12} → {relax_str:>12} {change}")
        
        print()
        
        # Сравниваем фильтры волатильности
        print("📊 ФИЛЬТРЫ ВОЛАТИЛЬНОСТИ:")
        print("-" * 40)
        
        vol_fields = [
            ("atr_range_min", "ATR мин", ""),
            ("atr_range_max", "ATR макс", ""),
            ("bb_width_percentile_max", "BB ширина макс", "%"),
            ("volume_surge_1h_min", "Всплеск 1ч", "x"),
            ("volume_surge_5m_min", "Всплеск 5м", "x"),
            ("oi_delta_threshold", "OI дельта", "")
        ]
        
        for field, name, unit in vol_fields:
            orig_val = getattr(original.volatility_filters, field)
            relax_val = getattr(relaxed.volatility_filters, field)
            
            if unit == "%":
                orig_str = f"{orig_val:.1f}%"
                relax_str = f"{relax_val:.1f}%"
            elif unit == "x":
                orig_str = f"{orig_val:.1f}x"
                relax_str = f"{relax_val:.1f}x"
            else:
                orig_str = f"{orig_val:.3f}"
                relax_str = f"{relax_val:.3f}"
            
            change = "📈" if relax_val < orig_val else "📉" if relax_val > orig_val else "➡️"
            print(f"  {name:20} | {orig_str:>12} → {relax_str:>12} {change}")
        
        print()
        
        # Сравниваем настройки сканера
        print("🎯 НАСТРОЙКИ СКАНЕРА:")
        print("-" * 40)
        
        scanner_fields = [
            ("max_candidates", "Макс. кандидатов", "шт"),
            ("scan_interval_seconds", "Интервал сканирования", "с"),
            ("top_n_by_volume", "Топ по объему", "шт")
        ]
        
        for field, name, unit in scanner_fields:
            orig_val = getattr(original.scanner_config, field)
            relax_val = getattr(relaxed.scanner_config, field)
            
            if unit == "с":
                orig_str = f"{orig_val}с"
                relax_str = f"{relax_val}с"
            else:
                orig_str = f"{orig_val}"
                relax_str = f"{relax_val}"
            
            change = "📈" if relax_val > orig_val else "📉" if relax_val < orig_val else "➡️"
            print(f"  {name:20} | {orig_str:>12} → {relax_str:>12} {change}")
        
        print()
        
        # Сравниваем настройки сигналов
        print("⚡ НАСТРОЙКИ СИГНАЛОВ:")
        print("-" * 40)
        
        signal_fields = [
            ("momentum_volume_multiplier", "Моментум множитель", ""),
            ("momentum_body_ratio_min", "Мин. соотношение тела", ""),
            ("momentum_epsilon", "Эпсилон", ""),
            ("retest_pierce_tolerance", "Толерантность ретеста", ""),
            ("retest_max_pierce_atr", "Макс. проникновение ATR", ""),
            ("l2_imbalance_threshold", "Порог L2 дисбаланса", "")
        ]
        
        for field, name, unit in signal_fields:
            orig_val = getattr(original.signal_config, field)
            relax_val = getattr(relaxed.signal_config, field)
            
            orig_str = f"{orig_val:.3f}"
            relax_str = f"{relax_val:.3f}"
            
            change = "📈" if relax_val < orig_val else "📉" if relax_val > orig_val else "➡️"
            print(f"  {name:20} | {orig_str:>12} → {relax_str:>12} {change}")
        
        print()
        print("💡 ИНТЕРПРЕТАЦИЯ ИЗМЕНЕНИЙ:")
        print("-" * 40)
        print("📈 = Более мягкие требования (больше кандидатов пройдет)")
        print("📉 = Более строгие требования (меньше кандидатов пройдет)")
        print("➡️ = Без изменений")
        
        print()
        print("🎯 ОЖИДАЕМЫЕ РЕЗУЛЬТАТЫ:")
        print("-" * 40)
        print("✅ Больше рынков пройдет фильтры ликвидности")
        print("✅ Больше рынков пройдет фильтры волатильности")
        print("✅ Увеличится пул кандидатов для анализа")
        print("✅ Больше шансов на генерацию сигналов")
        print("✅ Более частые сканирования (180с vs 300с)")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка сравнения: {e}")
        return False

def main():
    """Главная функция."""
    success = compare_presets()
    
    if success:
        print("\n✅ Сравнение завершено")
        print("🚀 Рекомендация: Переключитесь на расслабленный пресет")
    else:
        print("\n❌ Сравнение завершилось с ошибками")

if __name__ == "__main__":
    main()

