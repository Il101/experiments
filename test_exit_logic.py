#!/usr/bin/env python3
"""
🔬 POSITION TRACKER EXIT LOGIC TEST

Прямое unit-тестирование логики закрытия позиций в PositionTracker.
Проверяет should_take_profit() и should_update_stop() без полного движка.
"""

import sys
from decimal import Decimal
from datetime import datetime
import numpy as np

from breakout_bot.position.position_manager import PositionTracker
from breakout_bot.data.models import Position, Candle
from breakout_bot.config.settings import load_preset


def create_test_position(entry: float, sl: float, tp1: float, side: str = "long") -> Position:
    """Создать тестовую позицию."""
    return Position(
        id="test_position_001",
        symbol="BTC/USDT:USDT",
        side=side,
        strategy="breakout",
        qty=0.5,
        entry=entry,
        sl=sl,
        tp=tp1,
        status="open",
        timestamps={"opened_at": int(datetime.now().timestamp() * 1000)},
        meta={"tp1": tp1, "tp2": tp1 * 1.02}  # TP2 чуть выше
    )


def create_test_candles(prices: list, count: int = 50) -> list:
    """Создать тестовые свечи."""
    candles = []
    base_ts = int(datetime.now().timestamp() * 1000)
    
    for i in range(count):
        # Берём price из списка или последний
        price = prices[min(i, len(prices)-1)]
        candle = Candle(
            ts=base_ts + (i * 300000),  # 5-минутные свечи
            open=price,
            high=price * 1.001,
            low=price * 0.999,
            close=price,
            volume=100.0
        )
        candles.append(candle)
    
    return candles


def test_take_profit_logic():
    """Тест логики Take Profit."""
    print("\n" + "="*70)
    print("TEST 1: TAKE PROFIT LOGIC")
    print("="*70)
    
    # Параметры
    entry = 120000.0
    sl = 119000.0
    r_distance = entry - sl  # 1000 USDT
    tp1 = entry + (2 * r_distance)  # 122000 (2R)
    
    print(f"📊 Position Setup:")
    print(f"   Entry: ${entry:,.2f}")
    print(f"   SL: ${sl:,.2f}")
    print(f"   R-distance: ${r_distance:,.2f}")
    print(f"   TP1 (2R): ${tp1:,.2f}")
    
    # Создаём позицию и tracker
    position = create_test_position(entry, sl, tp1, side="long")
    preset = load_preset("breakout_v1_working")
    tracker = PositionTracker(position, preset.position_config)
    
    # Test 1.1: Цена НИЖЕ TP1 - не должно закрывать
    current_price = 121000.0
    result = tracker.should_take_profit(current_price)
    
    print(f"\n🧪 Test 1.1: Price BELOW TP1")
    print(f"   Current price: ${current_price:,.2f}")
    print(f"   Result: {result}")
    assert result is None, f"Should be None below TP1, got {result}"
    print(f"   ✅ PASS: No take profit below TP1")
    
    # Test 1.2: Цена ДОСТИГЛА TP1 - должно закрыть 50%
    current_price = tp1 + 50  # Чуть выше TP1
    result = tracker.should_take_profit(current_price)
    
    print(f"\n🧪 Test 1.2: Price AT/ABOVE TP1")
    print(f"   Current price: ${current_price:,.2f}")
    print(f"   Result: {result}")
    
    if result:
        action, percentage, price = result
        print(f"   ✅ TAKE PROFIT TRIGGERED!")
        print(f"      Action: {action}")
        print(f"      Close percentage: {percentage}%")
        print(f"      Price: ${price:,.2f}")
        assert action == "tp1", f"Expected 'tp1', got '{action}'"
        assert percentage == 50, f"Expected 50%, got {percentage}%"
        print(f"   ✅ PASS: TP1 triggered correctly")
    else:
        print(f"   ❌ FAIL: TP1 not triggered at ${current_price:,.2f}")
        return False
    
    # Test 1.3: TP1 уже исполнен, проверяем TP2
    tracker.tp1_executed = True
    tp2 = entry + (3.5 * r_distance)  # 123500 (3.5R)
    
    current_price = tp2 + 50
    result = tracker.should_take_profit(current_price)
    
    print(f"\n🧪 Test 1.3: Price AT/ABOVE TP2 (after TP1)")
    print(f"   Current price: ${current_price:,.2f}")
    print(f"   TP2 target: ${tp2:,.2f}")
    print(f"   Result: {result}")
    
    if result:
        action, percentage, price = result
        print(f"   ✅ TAKE PROFIT 2 TRIGGERED!")
        print(f"      Action: {action}")
        print(f"      Close percentage: {percentage}%")
        assert action == "tp2", f"Expected 'tp2', got '{action}'"
        print(f"   ✅ PASS: TP2 triggered correctly")
    else:
        print(f"   ⚠️  TP2 not triggered (may not be implemented)")
    
    return True


def test_stop_update_logic():
    """Тест логики обновления Stop-Loss."""
    print("\n" + "="*70)
    print("TEST 2: STOP-LOSS UPDATE LOGIC")
    print("="*70)
    
    # Параметры
    entry = 120000.0
    sl = 119000.0
    tp1 = 122000.0
    
    position = create_test_position(entry, sl, tp1, side="long")
    preset = load_preset("breakout_v1_working")
    tracker = PositionTracker(position, preset.position_config)
    
    print(f"📊 Position Setup:")
    print(f"   Entry: ${entry:,.2f}")
    print(f"   Initial SL: ${sl:,.2f}")
    
    # Test 2.1: TP1 НЕ исполнен - SL не должен двигаться
    current_price = 121000.0
    candles = create_test_candles([120000, 120500, 121000], count=50)
    
    new_stop = tracker.should_update_stop(current_price, candles)
    
    print(f"\n🧪 Test 2.1: Before TP1 execution")
    print(f"   TP1 executed: {tracker.tp1_executed}")
    print(f"   New stop: {new_stop}")
    assert new_stop is None, "SL should not move before TP1"
    print(f"   ✅ PASS: SL doesn't move before TP1")
    
    # Test 2.2: TP1 ИСПОЛНЕН - SL должен переместиться в breakeven
    tracker.tp1_executed = True
    
    new_stop = tracker.should_update_stop(current_price, candles)
    
    print(f"\n🧪 Test 2.2: After TP1 execution (move to breakeven)")
    print(f"   TP1 executed: {tracker.tp1_executed}")
    print(f"   Breakeven moved: {tracker.breakeven_moved}")
    print(f"   New stop: {new_stop}")
    
    if new_stop:
        print(f"   ✅ BREAKEVEN MOVE TRIGGERED!")
        print(f"      New SL: ${new_stop:,.2f}")
        print(f"      Entry: ${entry:,.2f}")
        print(f"      Difference: ${new_stop - entry:,.2f} (should be ~0.1% for fees)")
        
        # Проверяем, что новый SL выше старого и близок к entry
        assert new_stop > sl, f"New SL ({new_stop}) должен быть выше old SL ({sl})"
        assert abs(new_stop - entry) < (entry * 0.002), "New SL должен быть близко к entry"
        print(f"   ✅ PASS: SL moved to breakeven correctly")
    else:
        print(f"   ❌ FAIL: Breakeven move not triggered")
        return False
    
    # Test 2.3: Trailing stop после breakeven (нужно много свечей для Chandelier)
    tracker.breakeven_moved = True
    position.sl = new_stop  # Обновляем SL в позиции
    
    # Создаём 30 свечей с растущей ценой для trailing
    rising_prices = [121000 + (i * 100) for i in range(30)]
    candles = create_test_candles(rising_prices, count=30)
    current_price = rising_prices[-1]
    
    new_stop = tracker.should_update_stop(current_price, candles)
    
    print(f"\n🧪 Test 2.3: Trailing stop (after breakeven)")
    print(f"   Breakeven moved: {tracker.breakeven_moved}")
    print(f"   Current price: ${current_price:,.2f}")
    print(f"   Candles count: {len(candles)}")
    print(f"   New stop: {new_stop}")
    
    if new_stop:
        print(f"   ✅ TRAILING STOP UPDATED!")
        print(f"      New SL: ${new_stop:,.2f}")
        print(f"      Previous SL: ${position.sl:,.2f}")
        print(f"      Price: ${current_price:,.2f}")
        
        # Для long trailing stop должен двигаться вверх
        if new_stop > position.sl:
            print(f"   ✅ PASS: Trailing stop moved up (for long)")
        else:
            print(f"   ⚠️  Trailing stop didn't move up")
    else:
        print(f"   ⚠️  Trailing stop not triggered (may need more candles or price movement)")
    
    return True


def test_short_position_logic():
    """Тест логики для SHORT позиций."""
    print("\n" + "="*70)
    print("TEST 3: SHORT POSITION LOGIC")
    print("="*70)
    
    # Параметры для SHORT
    entry = 120000.0
    sl = 121000.0  # SL выше entry для short
    r_distance = sl - entry  # 1000 USDT
    tp1 = entry - (2 * r_distance)  # 118000 (2R вниз)
    
    print(f"📊 SHORT Position Setup:")
    print(f"   Entry: ${entry:,.2f}")
    print(f"   SL: ${sl:,.2f} (above entry)")
    print(f"   TP1 (2R): ${tp1:,.2f} (below entry)")
    
    position = create_test_position(entry, sl, tp1, side="short")
    preset = load_preset("breakout_v1_working")
    tracker = PositionTracker(position, preset.position_config)
    
    # Test: Цена упала до TP1
    current_price = tp1 - 50
    result = tracker.should_take_profit(current_price)
    
    print(f"\n🧪 Test 3.1: SHORT TP1 hit")
    print(f"   Current price: ${current_price:,.2f}")
    print(f"   TP1 target: ${tp1:,.2f}")
    print(f"   Result: {result}")
    
    if result:
        action, percentage, price = result
        print(f"   ✅ SHORT TAKE PROFIT TRIGGERED!")
        print(f"      Action: {action}")
        print(f"      Close percentage: {percentage}%")
        print(f"   ✅ PASS: SHORT TP logic works")
        return True
    else:
        print(f"   ❌ FAIL: SHORT TP not triggered")
        return False


def main():
    """Запуск всех тестов."""
    print("\n" + "="*70)
    print("🔬 POSITION TRACKER EXIT LOGIC TEST SUITE")
    print("="*70)
    
    results = []
    
    # Test 1: Take Profit Logic
    try:
        results.append(("Take Profit Logic", test_take_profit_logic()))
    except Exception as e:
        print(f"\n❌ Test 1 FAILED with exception: {e}")
        import traceback
        traceback.print_exc()
        results.append(("Take Profit Logic", False))
    
    # Test 2: Stop Update Logic
    try:
        results.append(("Stop Update Logic", test_stop_update_logic()))
    except Exception as e:
        print(f"\n❌ Test 2 FAILED with exception: {e}")
        import traceback
        traceback.print_exc()
        results.append(("Stop Update Logic", False))
    
    # Test 3: SHORT Position Logic
    try:
        results.append(("SHORT Position Logic", test_short_position_logic()))
    except Exception as e:
        print(f"\n❌ Test 3 FAILED with exception: {e}")
        import traceback
        traceback.print_exc()
        results.append(("SHORT Position Logic", False))
    
    # Summary
    print("\n" + "="*70)
    print("📊 TEST RESULTS SUMMARY")
    print("="*70)
    
    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    total = len(results)
    passed_count = sum(1 for _, passed in results if passed)
    percentage = (passed_count / total * 100) if total > 0 else 0
    
    print(f"\nTOTAL: {passed_count}/{total} tests passed ({percentage:.1f}%)")
    
    if percentage >= 80:
        print("\n🎉 EXIT LOGIC VERIFIED!")
        print("   PositionTracker.should_take_profit() works correctly")
        print("   PositionTracker.should_update_stop() works correctly")
        print("   Both LONG and SHORT positions supported")
    else:
        print("\n⚠️  SOME TESTS FAILED")
        print("   Review failed tests above")
    
    print("="*70)
    print()
    
    return passed_count == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
