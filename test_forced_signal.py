#!/usr/bin/env python3
"""
Тест полного цикла с ФОРСИРОВАННЫМ сигналом на реальных данных.

Подход:
1. Запускаем реальный движок с реальными данными Bybit
2. Ждем завершения сканирования
3. ФОРСИРУЕМ создание тестового сигнала на одном из реальных активов
4. Наблюдаем полный цикл: SIZING → EXECUTION → MANAGING → закрытие

Это даст нам:
- ✅ Реальное API взаимодействие
- ✅ Реальные цены и данные рынка
- ✅ Гарантированное прохождение всех состояний
- ✅ Валидацию execution/management логики
"""

import asyncio
import sys
import time
from pathlib import Path
from datetime import datetime, timezone
from decimal import Decimal

sys.path.insert(0, str(Path(__file__).parent))

from breakout_bot.core.engine import OptimizedOrchestraEngine
from breakout_bot.core.state_machine import TradingState
from breakout_bot.data.models import Signal


class ForcedSignalTest:
    """Тест с форсированным сигналом на реальных данных"""
    
    def __init__(self):
        self.engine = None
        self.test_duration = 180  # 180 секунд (3 минуты) для наблюдения полного цикла до закрытия
        self.forced_signal = None
        self.start_time = None
        self.state_history = []
        
    async def setup_engine(self):
        """Инициализация реального движка"""
        print("\n" + "="*80)
        print("🎯 FORCED SIGNAL TEST - Full Trading Cycle on Real Data")
        print("="*80)
        print()
        print("📋 План теста:")
        print("   1. Запуск реального движка OptimizedOrchestraEngine")
        print("   2. Подключение к Bybit (paper trading mode)")
        print("   3. Сканирование рынка (реальные данные)")
        print("   4. ФОРСИРОВАНИЕ тестового сигнала на лучшем активе")
        print("   5. Наблюдение полного цикла:")
        print("      SIGNAL_WAIT → SIZING → EXECUTION → MANAGING → закрытие")
        print("   6. Продолжительность: 3 минуты")
        print()
        
        # Инициализация движка
        print("⚙️  Создание движка...")
        self.engine = OptimizedOrchestraEngine(preset_name="breakout_v1_working")
        
        print("🔧 Инициализация компонентов...")
        await self.engine.initialize()
        
        print("✅ Движок готов!")
        print(f"   Mode: {'Paper' if getattr(self.engine.exchange_client, 'paper_mode', True) else 'Live'}")
        print(f"   Capital: ${self.engine.starting_equity:,.2f}")
        print()
        
    async def wait_for_scanning_complete(self):
        """Ждем завершения сканирования"""
        print("⏳ Ожидание завершения сканирования...")
        
        while True:
            await asyncio.sleep(1)
            
            current_state = self.engine.state_machine.current_state
            
            if current_state == TradingState.SIGNAL_WAIT:
                print("✅ Сканирование завершено, движок в состоянии SIGNAL_WAIT")
                break
            elif current_state in [TradingState.ERROR, TradingState.STOPPED]:
                raise Exception(f"Движок в состоянии {current_state}")
                
        # Даем время на стабилизацию
        await asyncio.sleep(2)
        
    async def create_forced_signal(self):
        """Создание форсированного сигнала на лучшем активе"""
        print("\n" + "="*80)
        print("🎯 СОЗДАНИЕ ФОРСИРОВАННОГО СИГНАЛА")
        print("="*80)
        
        # Получаем результаты сканирования из scanning_manager
        scan_results = []
        if hasattr(self.engine, 'scanning_manager'):
            sm = self.engine.scanning_manager
            if hasattr(sm, 'last_scan_results') and sm.last_scan_results:
                scan_results = sm.last_scan_results
                
        if not scan_results:
            raise Exception(f"Список кандидатов пуст. ScanningManager: {self.engine.scanning_manager if hasattr(self.engine, 'scanning_manager') else 'N/A'}")
            
        print(f"\n📊 Доступно кандидатов: {len(scan_results)}")
        
        # Выбираем лучший кандидат (сортируем по объему)
        best_candidate = max(scan_results, key=lambda x: x.market_data.volume_24h_usd)
        symbol = best_candidate.symbol
        
        print(f"\n🎯 Выбран актив: {symbol}")
        print(f"   24h Volume: ${best_candidate.market_data.volume_24h_usd:,.0f}")
        print(f"   Price: ${best_candidate.market_data.price}")
        print(f"   ATR 5m: {best_candidate.market_data.atr_5m}")
        
        # Получаем текущую цену с биржи
        try:
            ticker = await self.engine.exchange_client.fetch_ticker(symbol)
            current_price = Decimal(str(ticker['last']))
            print(f"   Current Price (live): ${current_price}")
        except Exception as e:
            print(f"⚠️  Не удалось получить live цену: {e}")
            current_price = Decimal(str(best_candidate.market_data.price))
            
        # Создаем форсированный сигнал
        # Используем консервативные стоп и тейк-профит
        stop_loss = current_price * Decimal('0.98')  # -2%
        take_profit = current_price * Decimal('1.04')  # +4%
        
        self.forced_signal = Signal(
            symbol=symbol,
            side='long',  # Long позиция
            strategy='momentum',  # Используем momentum стратегию
            reason=f"FORCED TEST SIGNAL - Best scanned candidate with volume ${best_candidate.market_data.volume_24h_usd:,.0f}",
            entry=float(current_price),
            level=float(current_price),  # Level совпадает с entry
            sl=float(stop_loss),
            confidence=0.80,
            timestamp=int(datetime.now(timezone.utc).timestamp() * 1000),
            status="pending",
            correlation_id=f"forced_test_{int(datetime.now().timestamp())}",
            tp1=float(take_profit),
            tp2=float(take_profit * Decimal('1.02')),  # TP2 немного выше
            meta={
                'test_type': 'forced_signal',
                'scan_result': {
                    'volume_24h': best_candidate.market_data.volume_24h_usd,
                    'atr_5m': best_candidate.market_data.atr_5m,
                    'forced': True,
                }
            }
        )
        
        print(f"\n✅ Сигнал создан:")
        print(f"   Type: {self.forced_signal.strategy} {self.forced_signal.side}")
        print(f"   Entry: ${self.forced_signal.entry:.6f}")
        print(f"   Stop Loss: ${self.forced_signal.sl:.6f} (-2.00%)")
        print(f"   Take Profit: ${self.forced_signal.tp1:.6f} (+4.00%)")
        print(f"   Risk/Reward: 1:2")
        print(f"   Confidence: {self.forced_signal.confidence:.1%}")
        print()
        
    async def inject_signal(self):
        """Inject forced signal into engine."""
        if not self.forced_signal:
            raise Exception("Сигнал не создан!")
        
        signal = self.forced_signal
        
        print("\n💉 Внедрение сигнала в движок...")
        
        # Найти market_data для сигнала из scan_results
        scan_results = self.engine.scanning_manager.last_scan_results
        market_data = None
        for sr in scan_results:
            if sr.symbol == signal.symbol:
                market_data = sr.market_data
                break
        
        if not market_data:
            raise Exception(f"Не найден market_data для {signal.symbol}")
        
        # Сначала добавляем market_data в signal_manager
        self.engine.signal_manager.signal_market_data[signal.symbol] = market_data
        print(f"✅ Market data добавлен для {signal.symbol}")
        
        # Затем добавляем сигнал
        await self.engine.signal_manager._add_active_signal(signal)
        
        print(f"✅ Сигнал успешно добавлен в active_signals")
        print(f"   Всего активных сигналов: {len(self.engine.signal_manager.active_signals)}")
        
        # Принудительно переводим движок в SIZING, чтобы обработать сигнал
        print("\n⚡ Переключаем движок в состояние SIZING...")
        await self.engine.state_machine.transition_to(
            TradingState.SIZING,
            "Forced signal injected - moving to sizing"
        )
        print(f"✅ Состояние изменено на: {self.engine.state_machine.current_state}")
        print()
        
    async def monitor_trading_cycle(self):
        """Мониторинг полного торгового цикла"""
        print("="*80)
        print("📊 МОНИТОРИНГ ТОРГОВОГО ЦИКЛА")
        print("="*80)
        print()
        
        prev_state = self.engine.state_machine.current_state
        position_opened = False
        position_id = None
        last_pnl_time = time.time()
        
        start_time = datetime.now()
        
        while True:
            await asyncio.sleep(0.5)
            
            # Проверка таймаута
            elapsed = (datetime.now() - start_time).total_seconds()
            if elapsed > self.test_duration:
                print(f"\n⏰ Таймаут теста ({self.test_duration}с)")
                break
                
            current_state = self.engine.state_machine.current_state
            
            # Отслеживание изменений состояния
            if current_state != prev_state:
                timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
                self.state_history.append({
                    'timestamp': timestamp,
                    'from': prev_state,
                    'to': current_state
                })
                
                print(f"\n{'='*80}")
                print(f"[{timestamp}] 🔄 STATE: {prev_state.value} → {current_state.value}")
                print(f"{'='*80}")
                
                await self._print_state_info(current_state)
                
                prev_state = current_state
            
            # Отслеживание позиций
            if hasattr(self.engine, 'position_manager'):
                pm = self.engine.position_manager
                
                # Получаем активные позиции через async метод get_active_positions()
                active_positions_list = await pm.get_active_positions() if hasattr(pm, 'get_active_positions') else []
                
                # Проверка открытых позиций
                if active_positions_list:
                    if not position_opened:
                        position_opened = True
                        position = active_positions_list[0]
                        position_id = position.id if hasattr(position, 'id') else None
                        
                        print(f"\n{'='*80}")
                        print(f"💰 ПОЗИЦИЯ ОТКРЫТА!")
                        print(f"{'='*80}")
                        print(f"   Symbol: {position.symbol}")
                        print(f"   Side: {position.side}")
                        print(f"   Size: {position.qty}")
                        print(f"   Entry: ${position.entry:.6f}")
                        if hasattr(position, 'sl') and position.sl is not None:
                            print(f"   Stop: ${position.sl:.6f}")
                        if hasattr(position, 'tp') and position.tp is not None:
                            print(f"   Target: ${position.tp:.6f}")
                        print()
                        
                    # Обновление PnL
                    else:
                        position = active_positions_list[0]
                        if hasattr(position, 'unrealized_pnl') and position.unrealized_pnl is not None:
                            pnl = position.unrealized_pnl
                            pnl_pct = (pnl / (position.entry * position.qty)) * 100 if position.qty > 0 else 0
                            
                            # Выводим каждые 10 секунд
                            current_time = time.time()
                            if current_time - last_pnl_time > 10:
                                print(f"   📈 PnL: ${pnl:.2f} ({pnl_pct:+.2f}%) | Price: ${position.current_price:.2f}" if hasattr(position, 'current_price') else f"   📈 PnL: ${pnl:.2f} ({pnl_pct:+.2f}%)")
                                last_pnl_time = current_time
                                
                # Проверка закрытия позиции
                elif position_opened and not active_positions_list:
                    # Позиция закрыта!
                    print(f"\n{'='*80}")
                    print(f"🏁 ПОЗИЦИЯ ЗАКРЫТА!")
                    print(f"{'='*80}")
                    print(f"   Время удержания: {elapsed:.1f}s")
                    print()
                    break  # Выходим из цикла мониторинга
                        
            # Проверка на ошибки
            if current_state in [TradingState.ERROR, TradingState.EMERGENCY]:
                print(f"\n❌ Движок в состоянии {current_state.value}")
                break
                
    async def _print_state_info(self, state: TradingState):
        """Вывод информации о текущем состоянии"""
        if state == TradingState.SIZING:
            print("📏 Расчет размера позиции...")
            if hasattr(self.engine, 'signal_manager'):
                signals_count = len(self.engine.signal_manager.pending_signals) if hasattr(self.engine.signal_manager, 'pending_signals') else 0
                print(f"   Сигналов в обработке: {signals_count}")
                
        elif state == TradingState.EXECUTION:
            print("💰 Открытие позиции на бирже...")
            print("   (Paper Trading Mode - виртуальное исполнение)")
            
        elif state == TradingState.MANAGING:
            print("📊 Управление активной позицией...")
            if hasattr(self.engine, 'position_manager'):
                pm = self.engine.position_manager
                if hasattr(pm, 'active_positions'):
                    print(f"   Активных позиций: {len(pm.active_positions)}")
                    
        elif state == TradingState.IDLE:
            print("⏸️  Возврат в режим ожидания...")
            
        elif state == TradingState.SCANNING:
            print("🔍 Новый цикл сканирования...")
            
    async def print_summary(self):
        """Итоговая сводка теста"""
        print("\n" + "="*80)
        print("📊 ИТОГОВАЯ СВОДКА ТЕСТА")
        print("="*80)
        
        runtime = datetime.now() - self.start_time
        print(f"\n⏱️  Время работы: {runtime}")
        
        # История состояний
        print(f"\n🔄 История состояний ({len(self.state_history)} переходов):")
        for i, record in enumerate(self.state_history, 1):
            print(f"   {i}. [{record['timestamp']}] {record['from'].value} → {record['to'].value}")
            
        # Информация о сигнале
        if self.forced_signal:
            print(f"\n⚡ Форсированный сигнал:")
            print(f"   Symbol: {self.forced_signal.symbol}")
            print(f"   Type: {self.forced_signal.strategy} {self.forced_signal.side}")
            print(f"   Entry: ${self.forced_signal.entry:.6f}")
            print(f"   Stop: ${self.forced_signal.sl:.6f}")
            print(f"   Target: ${self.forced_signal.tp1:.6f}")
            
        # Информация о позициях
        if hasattr(self.engine, 'position_manager'):
            pm = self.engine.position_manager
            
            active_list = await pm.get_active_positions() if hasattr(pm, 'get_active_positions') else []
            closed_list = await pm.get_closed_positions() if hasattr(pm, 'get_closed_positions') else []
            
            print(f"\n💼 Позиции:")
            print(f"   Активных: {len(active_list)}")
            print(f"   Закрытых: {len(closed_list)}")
            
            if closed_list:
                total_pnl = 0
                for pos in closed_list:
                    if hasattr(pos, 'realized_pnl'):
                        total_pnl += pos.realized_pnl
                        
                print(f"   Итоговый PnL: ${total_pnl:.2f}")
                
                # Детали последней закрытой позиции
                last_pos = closed_list[-1]
                print(f"\n   Последняя позиция:")
                print(f"      Symbol: {last_pos.symbol}")
                print(f"      Entry: ${last_pos.entry_price:.6f}")
                if hasattr(last_pos, 'exit_price'):
                    print(f"      Exit: ${last_pos.exit_price:.6f}")
                if hasattr(last_pos, 'realized_pnl'):
                    print(f"      PnL: ${last_pos.realized_pnl:.2f}")
                if hasattr(last_pos, 'close_reason'):
                    print(f"      Close Reason: {last_pos.close_reason}")
                    
        # Проверка пройденных состояний
        print(f"\n✅ Проверка полного цикла:")
        required_states = [
            TradingState.SIGNAL_WAIT,
            TradingState.SIZING,
            TradingState.EXECUTION,
            TradingState.MANAGING
        ]
        
        passed_states = set(record['to'] for record in self.state_history)
        
        for state in required_states:
            status = "✅" if state in passed_states else "❌"
            print(f"   {status} {state.value}")
            
        all_passed = all(state in passed_states for state in required_states)
        
        print("\n" + "="*80)
        if all_passed:
            print("🎉 ВСЕ СОСТОЯНИЯ ПРОЙДЕНЫ! ТЕСТ УСПЕШЕН!")
        else:
            print("⚠️  НЕ ВСЕ СОСТОЯНИЯ ПРОЙДЕНЫ")
        print("="*80)
        
    async def run_test(self):
        """Запуск полного теста"""
        try:
            self.start_time = datetime.now()
            
            # 1. Инициализация движка
            await self.setup_engine()
            
            # 2. Запуск движка в фоне
            print("🚀 Запуск движка...")
            engine_task = asyncio.create_task(self.engine.start())
            
            # 3. Ожидание завершения сканирования
            await self.wait_for_scanning_complete()
            
            # 4. Создание и внедрение форсированного сигнала
            await self.create_forced_signal()
            await self.inject_signal()
            
            print("⏱️  Начинаем мониторинг торгового цикла...")
            print(f"   Максимальная длительность: {self.test_duration} секунд")
            print()
            
            # 5. Мониторинг торгового цикла
            await self.monitor_trading_cycle()
            
            # 6. Остановка движка
            print("\n🛑 Останавливаем движок...")
            await self.engine.stop()
            
            # Ждем завершения задачи движка
            engine_task.cancel()
            try:
                await engine_task
            except asyncio.CancelledError:
                pass
                
            # 7. Итоговая сводка
            await self.print_summary()
            
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


async def main():
    """Главная функция"""
    test = ForcedSignalTest()
    await test.run_test()


if __name__ == "__main__":
    print("\n" + "="*80)
    print("🎯 FORCED SIGNAL TEST")
    print("="*80)
    print("\nЦель: Проверка полного торгового цикла на реальных данных")
    print("Подход: Форсированный сигнал на лучшем активе из сканирования")
    print("Ожидаемый результат: Прохождение всех состояний до закрытия позиции")
    print("\nНажмите Ctrl+C для прерывания...")
    print("="*80)
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  Тест прерван пользователем")
    except Exception as e:
        print(f"\n\n❌ Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()
