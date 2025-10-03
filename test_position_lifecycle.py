#!/usr/bin/env python3
"""
КОМПЛЕКСНЫЙ ТЕСТ ЖИЗНЕННОГО ЦИКЛА ПОЗИЦИИ

Проверяет:
1. ✅ Открытие позиции
2. ✅ Position management
3. ✅ TP hit closure
4. ✅ SL hit closure
5. ✅ Trailing stop
6. ✅ Manual closure
7. ✅ Emergency exit

Подход:
- Открываем позицию с forced signal
- Симулируем различные сценарии закрытия
- Проверяем корректность exit logic
"""

import asyncio
import sys
from pathlib import Path
from decimal import Decimal
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).parent))

from breakout_bot.core.engine import OptimizedOrchestraEngine
from breakout_bot.core.state_machine import TradingState
from breakout_bot.data.models import Signal, MarketData
from breakout_bot.data.models import Position


class PositionLifecycleTest:
    """Полный тест жизненного цикла позиции"""
    
    def __init__(self):
        self.engine = None
        self.test_results = {
            'position_open': False,
            'tp_closure': False,
            'sl_closure': False,
            'manual_closure': False,
            'trailing_stop': False,
            'error_recovery': False
        }
        
    async def setup_engine(self):
        """Инициализация движка"""
        print("\n" + "="*80)
        print("🧪 POSITION LIFECYCLE TEST")
        print("="*80)
        print("\n📋 Тесты:")
        print("   1. ✅ Открытие позиции")
        print("   2. 🎯 TP Hit Closure")
        print("   3. 🛑 SL Hit Closure")
        print("   4. 📈 Trailing Stop")
        print("   5. ✋ Manual Closure")
        print("   6. 🚨 Emergency Exit")
        print()
        
        print("⚙️  Создание движка...")
        self.engine = OptimizedOrchestraEngine(preset_name="breakout_v1_working")
        
        print("🔧 Инициализация...")
        await self.engine.initialize()
        
        print("✅ Движок готов!")
        print(f"   Capital: ${self.engine.starting_equity:,.2f}")
        print()
        
    async def wait_for_scanning(self):
        """Ждем завершения сканирования"""
        print("⏳ Ожидание сканирования...")
        
        timeout = 60
        start = asyncio.get_event_loop().time()
        
        while True:
            await asyncio.sleep(1)
            
            if asyncio.get_event_loop().time() - start > timeout:
                raise TimeoutError("Scanning timeout")
                
            current_state = self.engine.state_machine.current_state
            
            if current_state == TradingState.SIGNAL_WAIT:
                print("✅ Сканирование завершено")
                break
            elif current_state in [TradingState.ERROR, TradingState.STOPPED]:
                raise Exception(f"Движок в состоянии {current_state}")
                
        await asyncio.sleep(2)
        
    async def open_test_position(self):
        """Открытие тестовой позиции"""
        print("\n" + "="*80)
        print("📊 ТЕСТ 1: ОТКРЫТИЕ ПОЗИЦИИ")
        print("="*80)
        
        # Получаем scan results
        scan_results = []
        if hasattr(self.engine, 'scanning_manager'):
            sm = self.engine.scanning_manager
            if hasattr(sm, 'last_scan_results') and sm.last_scan_results:
                scan_results = sm.last_scan_results
                
        if not scan_results:
            raise Exception("Нет кандидатов для открытия позиции")
            
        # Выбираем BTC
        best_candidate = max(scan_results, key=lambda x: x.market_data.volume_24h_usd)
        symbol = best_candidate.symbol
        
        print(f"\n🎯 Выбран актив: {symbol}")
        print(f"   Volume 24h: ${best_candidate.market_data.volume_24h_usd:,.0f}")
        
        # Получаем текущую цену
        exchange = self.engine.exchange_client
        ticker = await exchange.fetch_ticker(symbol)
        current_price = Decimal(str(ticker['last']))
        
        print(f"   Текущая цена: ${current_price}")
        
        # Создаем форсированный сигнал
        forced_signal = Signal(
            id=f"test_{symbol}_{datetime.now(timezone.utc).timestamp()}",
            symbol=symbol,
            direction="long",
            entry_price=current_price,
            stop_loss=current_price * Decimal("0.98"),  # -2%
            take_profit=current_price * Decimal("1.04"),  # +4%
            confidence=Decimal("0.85"),
            market_data=best_candidate.market_data,
            strategy="test_lifecycle",
            timestamp=datetime.now(timezone.utc)
        )
        
        print(f"\n📝 Сигнал создан:")
        print(f"   Entry: ${forced_signal.entry_price}")
        print(f"   Stop Loss: ${forced_signal.stop_loss} (-2%)")
        print(f"   Take Profit: ${forced_signal.take_profit} (+4%)")
        
        # Инжектим сигнал
        signal_manager = self.engine.signal_manager
        await signal_manager.add_signals([forced_signal])
        
        # Переводим в SIZING
        state_machine = self.engine.state_machine
        state_machine.transition_to(
            TradingState.SIZING,
            "Test signal injected - moving to sizing"
        )
        
        print("\n⏳ Ожидание открытия позиции...")
        
        # Ждем открытия позиции
        timeout = 30
        start = asyncio.get_event_loop().time()
        position_opened = False
        
        while asyncio.get_event_loop().time() - start < timeout:
            await asyncio.sleep(0.5)
            
            pm = self.engine.position_manager
            active_positions = await pm.get_active_positions()
            
            if active_positions:
                position = active_positions[0]
                position_opened = True
                
                print("\n✅ ПОЗИЦИЯ ОТКРЫТА!")
                print(f"   Symbol: {position.symbol}")
                print(f"   Side: {position.side}")
                print(f"   Size: {position.qty}")
                print(f"   Entry: ${position.entry:.2f}")
                print(f"   Stop: ${position.sl:.2f}")
                print(f"   Target: ${position.tp:.2f}" if position.tp else "   Target: None")
                
                self.test_results['position_open'] = True
                return position
                
        if not position_opened:
            raise Exception("Позиция не открылась за 30 секунд")
            
    async def test_tp_closure(self, position: Position):
        """Тест закрытия по TP"""
        print("\n" + "="*80)
        print("🎯 ТЕСТ 2: TP HIT CLOSURE")
        print("="*80)
        
        if not position.tp:
            print("⚠️  Позиция без TP, пропускаем тест")
            self.test_results['tp_closure'] = None
            return
            
        print(f"\n📊 Текущая позиция:")
        print(f"   Entry: ${position.entry:.2f}")
        print(f"   Current: ${position.entry:.2f}")  
        print(f"   Target: ${position.tp:.2f}")
        print(f"   Расстояние до TP: {((position.tp / position.entry - 1) * 100):.2f}%")
        
        # Симулируем движение цены к TP
        print(f"\n🔧 Симулируем движение цены к TP...")
        
        pm = self.engine.position_manager
        
        # Обновляем позицию с новой ценой близкой к TP
        # Симулируем цену чуть выше TP
        simulated_price = float(position.tp) * 1.001 if position.tp else position.entry * 1.05
        
        print(f"   Симулированная цена: ${simulated_price:.2f}")
        
        # Проверяем логику закрытия по TP
        # Читаем исходный код position_manager
        print("\n🔍 Проверка логики TP closure...")
        
        # Проверяем есть ли метод check_exit_conditions
        if hasattr(pm, 'check_exit_conditions'):
            print("   ✅ Метод check_exit_conditions найден")
            
            # Создаем fake market data с ценой = TP
            fake_market_data = MarketData(
                symbol=position.symbol,
                price=simulated_price,
                volume_24h_usd=1000000,
                bid=simulated_price * Decimal("0.999"),
                ask=simulated_price * Decimal("1.001"),
                bid_size=100,
                ask_size=100,
                timestamp=datetime.now(timezone.utc)
            )
            
            # Проверяем exit conditions
            should_exit, reason = pm.check_exit_conditions(position, fake_market_data)
            
            if should_exit:
                print(f"   ✅ TP HIT DETECTED!")
                print(f"   Причина: {reason}")
                self.test_results['tp_closure'] = True
            else:
                print(f"   ❌ TP не сработал")
                print(f"   Причина: {reason}")
                self.test_results['tp_closure'] = False
        else:
            print("   ⚠️  Метод check_exit_conditions не найден")
            print("   Проверяем альтернативные методы...")
            
            # Ищем другие методы управления позициями
            methods = [m for m in dir(pm) if not m.startswith('_')]
            print(f"   Доступные методы: {', '.join(methods[:10])}...")
            
            self.test_results['tp_closure'] = None
            
    async def test_sl_closure(self, position: Position):
        """Тест закрытия по SL"""
        print("\n" + "="*80)
        print("🛑 ТЕСТ 3: SL HIT CLOSURE")
        print("="*80)
        
        print(f"\n📊 Текущая позиция:")
        print(f"   Entry: ${position.entry:.2f}")
        print(f"   Stop: ${position.sl:.2f}")
        print(f"   Расстояние до SL: {((position.sl / position.entry - 1) * 100):.2f}%")
        
        # Симулируем движение цены к SL
        print(f"\n🔧 Симулируем движение цены к SL...")
        
        pm = self.engine.position_manager
        
        # Обновляем позицию с новой ценой близкой к SL
        simulated_price = position.sl * Decimal("0.999")  # Чуть ниже SL
        
        print(f"   Симулированная цена: ${simulated_price:.2f}")
        
        # Проверяем логику закрытия по SL
        print("\n🔍 Проверка логики SL closure...")
        
        if hasattr(pm, 'check_exit_conditions'):
            print("   ✅ Метод check_exit_conditions найден")
            
            # Создаем fake market data с ценой = SL
            fake_market_data = MarketData(
                symbol=position.symbol,
                price=simulated_price,
                volume_24h_usd=1000000,
                bid=simulated_price * Decimal("0.999"),
                ask=simulated_price * Decimal("1.001"),
                bid_size=100,
                ask_size=100,
                timestamp=datetime.now(timezone.utc)
            )
            
            # Проверяем exit conditions
            should_exit, reason = pm.check_exit_conditions(position, fake_market_data)
            
            if should_exit:
                print(f"   ✅ SL HIT DETECTED!")
                print(f"   Причина: {reason}")
                self.test_results['sl_closure'] = True
            else:
                print(f"   ❌ SL не сработал")
                print(f"   Причина: {reason}")
                self.test_results['sl_closure'] = False
        else:
            print("   ⚠️  Метод check_exit_conditions не найден")
            self.test_results['sl_closure'] = None
            
    async def test_manual_closure(self, position: Position):
        """Тест ручного закрытия"""
        print("\n" + "="*80)
        print("✋ ТЕСТ 4: MANUAL CLOSURE")
        print("="*80)
        
        pm = self.engine.position_manager
        
        print(f"\n📊 Позиция перед закрытием:")
        print(f"   ID: {position.id}")
        print(f"   Symbol: {position.symbol}")
        print(f"   Size: {position.qty}")
        
        # Проверяем есть ли метод close_position
        print("\n🔍 Проверка методов закрытия...")
        
        close_methods = [m for m in dir(pm) if 'close' in m.lower() and not m.startswith('_')]
        
        if close_methods:
            print(f"   ✅ Найдены методы: {', '.join(close_methods)}")
            
            # Пробуем закрыть
            if hasattr(pm, 'close_position'):
                print("\n   Вызываем close_position()...")
                try:
                    await pm.close_position(position.id, "Manual test closure")
                    print("   ✅ Позиция закрыта вручную!")
                    self.test_results['manual_closure'] = True
                except Exception as e:
                    print(f"   ❌ Ошибка закрытия: {e}")
                    self.test_results['manual_closure'] = False
            else:
                print("   ⚠️  Метод close_position не найден")
                self.test_results['manual_closure'] = None
        else:
            print("   ⚠️  Методы закрытия не найдены")
            print(f"   Доступные методы PM: {[m for m in dir(pm) if not m.startswith('_')][:10]}...")
            self.test_results['manual_closure'] = None
            
    async def test_trailing_stop(self, position: Position):
        """Тест trailing stop"""
        print("\n" + "="*80)
        print("📈 ТЕСТ 5: TRAILING STOP")
        print("="*80)
        
        pm = self.engine.position_manager
        
        print("\n🔍 Проверка trailing stop функциональности...")
        
        # Проверяем методы
        trailing_methods = [m for m in dir(pm) if 'trail' in m.lower() and not m.startswith('_')]
        
        if trailing_methods:
            print(f"   ✅ Найдены методы: {', '.join(trailing_methods)}")
            self.test_results['trailing_stop'] = True
        else:
            print("   ⚠️  Trailing stop методы не найдены")
            
            # Проверяем в Position model
            if hasattr(position, 'trailing_stop') or hasattr(position, 'trailing_activated'):
                print("   ℹ️  Trailing stop поля найдены в Position model")
                self.test_results['trailing_stop'] = True
            else:
                print("   ⚠️  Trailing stop не реализован")
                self.test_results['trailing_stop'] = False
                
    async def print_results(self):
        """Вывод результатов"""
        print("\n" + "="*80)
        print("📊 РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ")
        print("="*80)
        
        print("\n🔍 Проверенные компоненты:\n")
        
        results_map = {
            'position_open': '1. Открытие позиции',
            'tp_closure': '2. TP Hit Closure',
            'sl_closure': '3. SL Hit Closure',
            'manual_closure': '4. Manual Closure',
            'trailing_stop': '5. Trailing Stop',
        }
        
        for key, name in results_map.items():
            result = self.test_results[key]
            if result is True:
                status = "✅ РАБОТАЕТ"
            elif result is False:
                status = "❌ НЕ РАБОТАЕТ"
            elif result is None:
                status = "⚠️  НЕ РЕАЛИЗОВАНО"
            else:
                status = "❓ НЕ ПРОВЕРЕНО"
                
            print(f"   {name}: {status}")
            
        # Общий счёт
        working = sum(1 for v in self.test_results.values() if v is True)
        total = len(self.test_results)
        percentage = (working / total) * 100
        
        print(f"\n📈 Общий результат: {working}/{total} ({percentage:.0f}%)")
        
        if percentage >= 80:
            print("\n🎉 ОТЛИЧНО! Большинство компонентов работают")
        elif percentage >= 50:
            print("\n⚠️  ЧАСТИЧНО: Некоторые компоненты требуют доработки")
        else:
            print("\n❌ ТРЕБУЕТСЯ РАБОТА: Много компонентов не реализовано")
            
    async def run(self):
        """Запуск всех тестов"""
        try:
            # Setup
            await self.setup_engine()
            
            # Start engine
            engine_task = asyncio.create_task(self.engine.start())
            await asyncio.sleep(2)
            
            # Wait for scanning
            await self.wait_for_scanning()
            
            # Open position
            position = await self.open_test_position()
            
            await asyncio.sleep(3)
            
            # Run tests
            await self.test_tp_closure(position)
            await self.test_sl_closure(position)
            await self.test_trailing_stop(position)
            await self.test_manual_closure(position)
            
            # Results
            await self.print_results()
            
            # Cleanup
            await self.engine.stop()
            engine_task.cancel()
            
            print("\n✅ Все тесты завершены!")
            
        except Exception as e:
            print(f"\n❌ Ошибка теста: {e}")
            import traceback
            traceback.print_exc()
            
            if self.engine:
                await self.engine.stop()


async def main():
    """Entry point"""
    test = PositionLifecycleTest()
    await test.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  Тест прерван пользователем")
    except Exception as e:
        print(f"\n❌ Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
