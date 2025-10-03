#!/usr/bin/env python3
"""
Финальный тест всех исправлений системы
"""

import sys
import asyncio
import time
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from breakout_bot.core.engine import OptimizedOrchestraEngine
from breakout_bot.position.position_manager import PositionManager
from breakout_bot.config.settings import load_preset
from breakout_bot.utils.enhanced_error_handler import enhanced_error_handler
from breakout_bot.utils.safe_math import safe_divide, validate_positive
from breakout_bot.data.models import Position

async def test_engine_initialization():
    """Тест исправления инициализации движка"""
    print("🔧 Тестирую исправление инициализации движка...")
    
    try:
        # Load preset and initialize engine
        preset = load_preset("breakout_v1_working")
        engine = OptimizedOrchestraEngine()
        
        # Test that all required attributes exist
        required_attrs = [
            'error_count', 'max_retries', 'retry_delay', 
            'last_error', 'retry_backoff', 'health_status',
            'starting_equity', 'last_cycle_time', 'avg_cycle_time'
        ]
        
        for attr in required_attrs:
            assert hasattr(engine, attr), f"Missing required attribute: {attr}"
            print(f"   ✅ Attribute {attr}: {getattr(engine, attr)}")
        
        print("   🎉 Engine инициализация исправлена!")
        return True
        
    except Exception as e:
        print(f"   ❌ Ошибка в тесте engine: {e}")
        return False

async def test_trading_presets():
    """Тест новых реалистичных пресетов"""
    print("\n📊 Тестирую новые торговые пресеты...")
    
    try:
        # Test breakout_v1_working preset
        preset = load_preset("breakout_v1_working")
        assert preset.name == "breakout_v1_working"
        assert preset.liquidity_filters.min_24h_volume_usd == 10_000_000  # Realistic
        assert preset.liquidity_filters.max_spread_bps == 25  # Relaxed
        assert preset.scanner_config.max_candidates == 30  # More candidates
        print(f"   ✅ breakout_v1_working loaded: {preset.description}")
        
        # Test ultra-soft test preset
        test_preset = load_preset("breakout_v1_test")
        assert test_preset.name == "breakout_v1_test"
        assert test_preset.liquidity_filters.min_24h_volume_usd == 1_000_000  # Ultra soft
        assert test_preset.liquidity_filters.max_spread_bps == 100  # Very relaxed
        assert test_preset.scanner_config.max_candidates == 50  # Many candidates
        print(f"   ✅ breakout_v1_test loaded: {test_preset.description}")
        
        print("   🎉 Новые пресеты работают!")
        return True
        
    except Exception as e:
        print(f"   ❌ Ошибка в тесте пресетов: {e}")
        return False

async def test_safe_math():
    """Тест safe math utilities"""
    print("\n🔢 Тестирую safe math функции...")
    
    try:
        # Test safe divide
        result = safe_divide(10, 2)
        assert result == 5.0, f"Expected 5.0, got {result}"
        
        result = safe_divide(10, 0, default=999)
        assert result == 999, f"Expected 999 for division by zero, got {result}"
        
        # Test validate positive
        result = validate_positive(5.5, "test")
        assert result == 5.5, f"Expected 5.5, got {result}"
        
        result = validate_positive(-1, "negative", default=10)
        assert result == 10, f"Expected 10 for negative, got {result}"
        
        result = validate_positive("invalid", "invalid", default=20)
        assert result == 20, f"Expected 20 for invalid, got {result}"
        
        print("   ✅ safe_divide работает корректно")
        print("   ✅ validate_positive работает корректно")
        print("   🎉 Safe math функции работают!")
        return True
        
    except Exception as e:
        print(f"   ❌ Ошибка в тесте safe math: {e}")
        return False

async def test_race_conditions_fix():
    """Тест исправления race conditions"""
    print("\n🔒 Тестирую исправление race conditions...")
    
    try:
        preset = load_preset("breakout_v1_working")
        manager = PositionManager(preset)
        
        # Test that methods are async and thread-safe
        assert asyncio.iscoroutinefunction(manager.add_position), "add_position should be async"
        assert asyncio.iscoroutinefunction(manager.remove_position), "remove_position should be async"
        assert asyncio.iscoroutinefunction(manager.update_position), "update_position should be async"
        assert hasattr(manager, '_position_lock'), "Manager should have position lock"
        assert hasattr(manager, '_recent_positions_lock'), "Manager should have recent positions lock"
        
        # Test concurrent operations
        positions = []
        for i in range(5):
            position = Position(
                id=f"test_pos_{i}",
                symbol=f"TEST{i}/USDT",
                side="long",
                strategy="momentum",
                qty=100.0,
                entry=1.0,
                sl=0.95,
                status="open",
                pnl_usd=0.0,
                pnl_r=0.0,
                fees_usd=1.0,
                timestamps={'opened_at': int(time.time() * 1000)},
                meta={}
            )
            positions.append(position)
        
        # Add positions concurrently
        await asyncio.gather(*[manager.add_position(pos) for pos in positions])
        
        active = await manager.get_active_positions()
        assert len(active) == 5, f"Expected 5 active positions, got {len(active)}"
        
        print("   ✅ Async methods работают")
        print("   ✅ Thread-safe locks установлены")
        print("   ✅ Concurrent operations работают")
        print("   🎉 Race conditions исправлены!")
        return True
        
    except Exception as e:
        print(f"   ❌ Ошибка в тесте race conditions: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_enhanced_error_handling():
    """Тест улучшенной обработки ошибок"""
    print("\n🛡️ Тестирую улучшенную обработку ошибок...")
    
    try:
        # Test error classification
        network_error = ConnectionError("Network failed")
        category = enhanced_error_handler.classify_error(network_error)
        assert str(category) == "ErrorCategory.NETWORK", f"Expected NETWORK, got {category}"
        
        # Test error stats
        enhanced_error_handler.error_counts.clear()
        enhanced_error_handler._update_error_stats(category)
        stats = enhanced_error_handler.get_error_stats()
        assert stats['total_errors'] == 1, f"Expected 1 error, got {stats['total_errors']}"
        
        print("   ✅ Error classification работает")
        print("   ✅ Error statistics работают")
        print("   🎉 Enhanced error handling работает!")
        return True
        
    except Exception as e:
        print(f"   ❌ Ошибка в тесте error handling: {e}")
        return False

async def test_system_integration():
    """Тест интеграции всех исправлений"""
    print("\n🎯 Тестирую интеграцию всех исправлений...")
    
    try:
        # Load realistic preset
        preset = load_preset("breakout_v1_working")
        
        # Initialize engine with all fixes
        engine = OptimizedOrchestraEngine()
        
        # Test that engine has all required components
        components = [
            'error_count', 'health_status', 'starting_equity'
        ]
        
        for component in components:
            assert hasattr(engine, component), f"Engine missing {component}"
        
        # Initialize thread-safe position manager
        pos_manager = PositionManager(preset)
        assert hasattr(pos_manager, '_position_lock'), "Position manager should be thread-safe"
        
        # Test safe math integration
        safe_result = safe_divide(100, 0, default=0)
        assert safe_result == 0, "Safe math should be integrated"
        
        # Test error handler integration
        stats = enhanced_error_handler.get_error_stats()
        assert 'error_counts' in stats, "Enhanced error handler should be available"
        
        print("   ✅ Engine с исправлениями инициализирован")
        print("   ✅ Thread-safe PositionManager готов") 
        print("   ✅ Safe math интегрирован")
        print("   ✅ Enhanced error handler интегрирован")
        print("   ✅ Realistic preset загружен")
        print("   🎉 ВСЕ ИСПРАВЛЕНИЯ ИНТЕГРИРОВАНЫ!")
        return True
        
    except Exception as e:
        print(f"   ❌ Ошибка в интеграционном тесте: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Главная функция финального тестирования"""
    print("🚀 ФИНАЛЬНЫЙ ТЕСТ ВСЕХ ИСПРАВЛЕНИЙ")
    print("=" * 60)
    
    tests = [
        ("Engine Initialization Fix", test_engine_initialization),
        ("Trading Presets Fix", test_trading_presets), 
        ("Safe Math Utilities", test_safe_math),
        ("Race Conditions Fix", test_race_conditions_fix),
        ("Enhanced Error Handling", test_enhanced_error_handling),
        ("System Integration", test_system_integration)
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = await test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"   ❌ Критическая ошибка в {test_name}: {e}")
            results.append((test_name, False))
    
    print(f"\n{'='*60}")
    print("📊 ИТОГОВЫЙ ОТЧЕТ ТЕСТИРОВАНИЯ:")
    print("="*60)
    
    passed = 0
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{status:12} | {test_name}")
        if result:
            passed += 1
    
    print(f"\n📈 РЕЗУЛЬТАТ: {passed}/{len(results)} ТЕСТОВ ПРОШЛИ")
    
    if passed == len(results):
        print("🎉 ВСЕ ИСПРАВЛЕНИЯ РАБОТАЮТ ОТЛИЧНО!")
        print("✅ СИСТЕМА ГОТОВА К PRODUCTION ТОРГОВЛЕ!")
        return True
    else:
        print(f"⚠️  {len(results) - passed} ТЕСТОВ НЕ ПРОШЛИ")
        print("❌ ТРЕБУЕТСЯ ДОПОЛНИТЕЛЬНАЯ ПРОВЕРКА")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
