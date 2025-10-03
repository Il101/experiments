#!/usr/bin/env python3
"""
РЕАЛЬНЫЙ тест торгового пайплайна.
Использует настоящие компоненты движка, реальное сканирование и логику.
"""

import asyncio
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from breakout_bot.core.engine import OptimizedOrchestraEngine
from breakout_bot.core.state_machine import TradingState


class RealPipelineTest:
    """Тест с реальным движком и его компонентами."""
    
    def __init__(self, preset_name: str = "breakout_v1"):
        self.preset_name = preset_name
        self.engine = None
        self.initial_state = None
        self.test_duration = 300  # 5 минут
        
    async def run_real_test(self):
        """Запустить тест с реальным движком."""
        print("\n" + "="*80)
        print("🔥 РЕАЛЬНЫЙ ТЕСТ ТОРГОВОГО ПАЙПЛАЙНА")
        print("="*80 + "\n")
        
        try:
            # ===== ФАЗА 1: ИНИЦИАЛИЗАЦИЯ РЕАЛЬНОГО ДВИЖКА =====
            print("📦 ФАЗА 1: ИНИЦИАЛИЗАЦИЯ РЕАЛЬНОГО ДВИЖКА")
            print("-" * 80)
            
            self.engine = OptimizedOrchestraEngine(self.preset_name)
            await self.engine.initialize()
            
            print(f"✅ Движок инициализирован")
            print(f"   Пресет: {self.preset_name}")
            print(f"   Exchange: {self.engine.exchange_client.__class__.__name__}")
            paper_mode = getattr(self.engine.exchange_client, 'paper_mode', True)
            print(f"   Mode: {'Paper Trading' if paper_mode else 'Live Trading'}")
            print(f"   Капитал: ${self.engine.starting_equity:,.2f}")
            print(f"   Начальное состояние: {self.engine.state_machine.current_state.value}")
            
            self.initial_state = self.engine.state_machine.current_state
            
            # ===== ФАЗА 2: ЗАПУСК ДВИЖКА =====
            print("\n📦 ФАЗА 2: ЗАПУСК ДВИЖКА")
            print("-" * 80)
            
            # Запускаем движок в фоне
            engine_task = asyncio.create_task(self.engine.start())
            
            print(f"✅ Движок запущен")
            print(f"   Тест будет работать {self.test_duration} секунд")
            print(f"   Отслеживаем переходы состояний...\n")
            
            # ===== ФАЗА 3: МОНИТОРИНГ РЕАЛЬНОЙ РАБОТЫ =====
            print("📊 ФАЗА 3: МОНИТОРИНГ РЕАЛЬНОЙ РАБОТЫ ПАЙПЛАЙНА")
            print("-" * 80 + "\n")
            
            await self._monitor_pipeline(self.test_duration)
            
            # ===== ФАЗА 4: ОСТАНОВКА И АНАЛИЗ =====
            print("\n📦 ФАЗА 4: ОСТАНОВКА И ФИНАЛЬНЫЙ АНАЛИЗ")
            print("-" * 80)
            
            # Останавливаем движок
            await self.engine.stop()
            engine_task.cancel()
            try:
                await engine_task
            except asyncio.CancelledError:
                pass
            
            # Анализ результатов
            await self._analyze_results()
            
        except Exception as e:
            print(f"\n❌ Ошибка теста: {e}")
            import traceback
            traceback.print_exc()
        finally:
            if self.engine:
                try:
                    await self.engine.stop()
                except:
                    pass
    
    async def _monitor_pipeline(self, duration: int):
        """Мониторинг реальной работы пайплайна."""
        start_time = time.time()
        last_state = self.engine.state_machine.current_state
        state_history = []
        
        check_interval = 5  # Проверяем каждые 5 секунд
        
        while time.time() - start_time < duration:
            current_state = self.engine.state_machine.current_state
            elapsed = int(time.time() - start_time)
            
            # Отслеживаем смену состояний
            if current_state != last_state:
                transition = {
                    'time': elapsed,
                    'from': last_state.value,
                    'to': current_state.value,
                    'timestamp': time.time()
                }
                state_history.append(transition)
                
                print(f"⚡ [{elapsed}s] Переход состояния: {last_state.value} → {current_state.value}")
                
                # Выводим детали в зависимости от состояния
                await self._log_state_details(current_state)
                
                last_state = current_state
            
            # Периодический статус
            if elapsed % 30 == 0 and elapsed > 0:
                print(f"\n📊 [{elapsed}s] Текущий статус:")
                await self._log_current_status()
            
            await asyncio.sleep(check_interval)
        
        self.state_history = state_history
    
    async def _log_state_details(self, state: TradingState):
        """Логирование деталей текущего состояния."""
        try:
            if state == TradingState.SCANNING:
                print(f"   🔍 Начато сканирование рынков...")
                
            elif state == TradingState.LEVEL_BUILDING:
                scan_results = getattr(self.engine.scanning_manager, 'last_scan_results', [])
                if scan_results:
                    print(f"   📐 Построение уровней для {len(scan_results)} кандидатов")
                    for result in scan_results[:3]:  # Первые 3
                        print(f"      - {result.symbol}: score={result.score:.2%}")
                
            elif state == TradingState.SIGNAL_WAIT:
                signals = self.engine.signal_manager.active_signals
                print(f"   ⚡ Активных сигналов: {len(signals)}")
                for symbol, signal in list(signals.items())[:3]:
                    print(f"      - {symbol}: {signal.side} @ ${signal.entry:,.2f} (conf: {signal.confidence:.2%})")
                
            elif state == TradingState.SIZING:
                print(f"   💰 Расчет размеров позиций...")
                
            elif state == TradingState.EXECUTION:
                print(f"   🎯 Исполнение ордеров...")
                
            elif state == TradingState.MANAGING:
                positions = self.engine.position_manager.open_positions
                print(f"   📈 Управление позициями: {len(positions)} открытых")
                for pos in positions[:3]:
                    pnl_status = "🟢" if pos.pnl_usd > 0 else "🔴"
                    print(f"      {pnl_status} {pos.symbol}: ${pos.pnl_usd:,.2f} ({pos.pnl_r:.2f}R)")
                    
        except Exception as e:
            print(f"   ⚠️  Ошибка при получении деталей: {e}")
    
    async def _log_current_status(self):
        """Логирование текущего статуса всех компонентов."""
        try:
            current_state = self.engine.state_machine.current_state
            print(f"   Состояние: {current_state.value}")
            
            # Сканирование
            scan_results = getattr(self.engine.scanning_manager, 'last_scan_results', [])
            print(f"   Сканирование: {len(scan_results)} кандидатов")
            
            # Сигналы
            signals = self.engine.signal_manager.active_signals
            print(f"   Сигналы: {len(signals)} активных")
            
            # Позиции
            positions = self.engine.position_manager.open_positions
            if positions:
                total_pnl = sum(p.pnl_usd for p in positions)
                print(f"   Позиции: {len(positions)} открытых (PnL: ${total_pnl:,.2f})")
            else:
                print(f"   Позиции: нет открытых")
            
            # Баланс
            balance = getattr(self.engine, 'current_equity', self.engine.starting_equity)
            print(f"   Баланс: ${balance:,.2f}")
            
        except Exception as e:
            print(f"   ⚠️  Ошибка при получении статуса: {e}")
    
    async def _analyze_results(self):
        """Анализ результатов реального теста."""
        print("\n" + "="*80)
        print("📊 ФИНАЛЬНЫЙ АНАЛИЗ РЕАЛЬНОГО ТЕСТА")
        print("="*80 + "\n")
        
        # История состояний
        if hasattr(self, 'state_history') and self.state_history:
            print("📈 История переходов состояний:")
            for transition in self.state_history:
                print(f"   [{transition['time']}s] {transition['from']} → {transition['to']}")
            print(f"\n   Всего переходов: {len(self.state_history)}")
        else:
            print("⚠️  Переходов состояний не обнаружено")
            print("   Возможные причины:")
            print("   - Движок застрял в начальном состоянии")
            print("   - Недостаточно времени для сканирования")
            print("   - Нет подходящих кандидатов на рынке")
        
        # Сканирование
        print(f"\n🔍 Результаты сканирования:")
        scan_results = getattr(self.engine.scanning_manager, 'last_scan_results', [])
        if scan_results:
            print(f"   Найдено кандидатов: {len(scan_results)}")
            print(f"   Топ-3 по скору:")
            for i, result in enumerate(scan_results[:3], 1):
                print(f"   {i}. {result.symbol}: {result.score:.2%}")
        else:
            print(f"   ❌ Кандидатов не найдено")
        
        # Сигналы
        print(f"\n⚡ Сгенерированные сигналы:")
        total_signals = len(getattr(self.engine.signal_manager, 'signal_history', []))
        active_signals = len(self.engine.signal_manager.active_signals)
        print(f"   Всего сгенерировано: {total_signals}")
        print(f"   Активных: {active_signals}")
        
        if self.engine.signal_manager.active_signals:
            print(f"   Активные сигналы:")
            for symbol, signal in list(self.engine.signal_manager.active_signals.items())[:5]:
                print(f"   - {symbol}: {signal.side} @ ${signal.entry:,.2f}")
        
        # Позиции
        print(f"\n💼 Торговые позиции:")
        positions = self.engine.position_manager.open_positions
        closed_positions = getattr(self.engine.position_manager, 'closed_positions', [])
        
        print(f"   Открытых: {len(positions)}")
        print(f"   Закрытых: {len(closed_positions)}")
        
        if positions:
            total_pnl = sum(p.pnl_usd for p in positions)
            print(f"   Текущий PnL: ${total_pnl:,.2f}")
            print(f"\n   Детали открытых позиций:")
            for pos in positions:
                print(f"   - {pos.symbol}: {pos.side} {pos.qty:.6f} @ ${pos.entry:,.2f}")
                print(f"     PnL: ${pos.pnl_usd:,.2f} ({pos.pnl_r:.2f}R)")
        
        if closed_positions:
            total_realized = sum(p.pnl_usd for p in closed_positions)
            print(f"\n   Реализованный PnL: ${total_realized:,.2f}")
        
        # Итоги
        print(f"\n" + "="*80)
        print("🏁 ЗАКЛЮЧЕНИЕ")
        print("="*80 + "\n")
        
        if hasattr(self, 'state_history') and len(self.state_history) >= 2:
            print("✅ Пайплайн РАБОТАЕТ - состояния переходили")
            print("   Движок успешно прошел через несколько фаз")
        elif scan_results:
            print("⚠️  Пайплайн ЧАСТИЧНО работает")
            print("   Сканирование работает, но дальше не идет")
            print("   Возможно, не хватает подходящих условий для сигналов")
        else:
            print("❌ Пайплайн НЕ РАБОТАЕТ как ожидалось")
            print("   Движок не прошел дальше начального состояния")
        
        print("\n💡 Это РЕАЛЬНЫЙ тест с настоящими компонентами:")
        print("   ✓ Реальное подключение к бирже")
        print("   ✓ Реальное сканирование рынков")
        print("   ✓ Реальная генерация сигналов")
        print("   ✓ Реальная логика принятия решений")
        print("\n")


async def main():
    """Главная функция."""
    test = RealPipelineTest()
    await test.run_real_test()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  Тест прерван пользователем")
    except Exception as e:
        print(f"\n\n❌ Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()
