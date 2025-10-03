#!/usr/bin/env python3
"""
Тестирование исправленного пайплайна.
Проверяет, что все состояния обрабатываются без задержек.
"""

import asyncio
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from breakout_bot.core.engine import OptimizedOrchestraEngine
from breakout_bot.core.state_machine import TradingState


async def test_pipeline_flow():
    """Тест потока пайплайна."""
    print("\n" + "="*80)
    print("🧪 ТЕСТИРОВАНИЕ ПОТОКА ПАЙПЛАЙНА")
    print("="*80 + "\n")
    
    engine = None
    try:
        # Инициализация
        print("📦 Инициализация движка...")
        engine = OptimizedOrchestraEngine("breakout_v1")
        await engine.initialize()
        print("✅ Движок инициализирован\n")
        
        # Отслеживание переходов состояний
        state_transitions = []
        transition_times = []
        
        def track_transition(transition):
            state_transitions.append((transition.from_state, transition.to_state))
            transition_times.append(time.time())
            print(f"🔄 Переход: {transition.from_state.value} → {transition.to_state.value}")
        
        engine.state_machine._notify_callback = track_transition
        
        # Запустить один торговый цикл
        print("🚀 Запуск торгового цикла...\n")
        start_time = time.time()
        
        # Запустить цикл на 30 секунд
        async def run_limited_cycle():
            engine.running = True
            task = asyncio.create_task(engine._main_trading_loop())
            await asyncio.sleep(30)  # Дать 30 секунд на работу
            engine.running = False
            await task
        
        await run_limited_cycle()
        
        total_time = time.time() - start_time
        
        # Анализ результатов
        print("\n" + "="*80)
        print("📊 РЕЗУЛЬТАТЫ ТЕСТА")
        print("="*80 + "\n")
        
        print(f"Общее время работы: {total_time:.2f}s")
        print(f"Количество переходов состояний: {len(state_transitions)}\n")
        
        if state_transitions:
            print("Последовательность переходов:")
            for i, (from_state, to_state) in enumerate(state_transitions, 1):
                if i < len(transition_times):
                    time_diff = transition_times[i] - transition_times[i-1] if i > 0 else 0
                    print(f"  {i}. {from_state.value:20} → {to_state.value:20} ({time_diff:.3f}s)")
                else:
                    print(f"  {i}. {from_state.value:20} → {to_state.value:20}")
        
        # Проверка, что пайплайн прошел дальше сканирования
        states_visited = set(to_state for _, to_state in state_transitions)
        
        print("\nПосещенные состояния:")
        for state in [TradingState.SCANNING, TradingState.LEVEL_BUILDING, 
                      TradingState.SIGNAL_WAIT, TradingState.SIZING, 
                      TradingState.EXECUTION]:
            visited = "✅" if state in states_visited else "❌"
            print(f"  {visited} {state.value}")
        
        # Оценка успеха
        print("\n" + "="*80)
        if TradingState.SIGNAL_WAIT in states_visited:
            print("✅ УСПЕХ: Пайплайн прошел дальше сканирования!")
            if TradingState.SIZING in states_visited:
                print("✅ ОТЛИЧНО: Достигнуто состояние SIZING!")
        else:
            print("❌ ПРОВАЛ: Пайплайн застрял на сканировании")
        print("="*80 + "\n")
        
    except Exception as e:
        print(f"\n❌ Ошибка теста: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if engine:
            await engine.stop()


if __name__ == "__main__":
    try:
        asyncio.run(test_pipeline_flow())
    except KeyboardInterrupt:
        print("\n\n⚠️  Тест прерван пользователем")
