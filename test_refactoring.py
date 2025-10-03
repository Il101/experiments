"""
Тест рефакторинга движка - проверка новых компонентов.
"""

import asyncio
import sys
import os

# Добавить путь к проекту
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from breakout_bot.core.state_machine import StateMachine, TradingState
from breakout_bot.core.error_handler import ErrorHandler, ErrorSeverity, ErrorCategory


async def test_state_machine():
    """Тест работы StateMachine."""
    print("🔄 Тестирование StateMachine...")
    
    # Создать StateMachine
    sm = StateMachine(initial_state=TradingState.IDLE)
    
    # Проверить начальное состояние
    assert sm.current_state == TradingState.IDLE
    print(f"✅ Начальное состояние: {sm.current_state.value}")
    
    # Тест валидных переходов
    success = await sm.transition_to(TradingState.INITIALIZING, "Test initialization")
    assert success == True
    assert sm.current_state == TradingState.INITIALIZING
    print(f"✅ Валидный переход: {sm.current_state.value}")
    
    # Тест невалидного перехода
    success = await sm.transition_to(TradingState.EXECUTION, "Invalid transition")
    assert success == False
    assert sm.current_state == TradingState.INITIALIZING  # Состояние не изменилось
    print(f"✅ Невалидный переход заблокирован: {sm.current_state.value}")
    
    # Тест валидной цепочки переходов
    await sm.transition_to(TradingState.SCANNING, "Start scanning")
    await sm.transition_to(TradingState.LEVEL_BUILDING, "Found candidates")
    await sm.transition_to(TradingState.SIGNAL_WAIT, "Levels built")
    assert sm.current_state == TradingState.SIGNAL_WAIT
    print(f"✅ Цепочка переходов работает: {sm.current_state.value}")
    
    # Тест истории переходов
    history = sm.get_transition_history()
    assert len(history) > 0
    print(f"✅ История переходов: {len(history)} записей")
    
    # Тест статуса
    status = sm.get_status()
    assert "current_state" in status
    assert status["is_trading_active"] == True
    print(f"✅ Статус: активная торговля = {status['is_trading_active']}")


async def test_error_handler():
    """Тест работы ErrorHandler."""
    print("\n⚠️  Тестирование ErrorHandler...")
    
    # Создать ErrorHandler
    eh = ErrorHandler(max_retries=2, retry_backoff=1.0)
    
    # Тест классификации ошибок
    connection_error = ConnectionError("Failed to connect to exchange")
    error_info = eh.classify_error(connection_error, "exchange", "fetch_balance")
    
    assert error_info.severity == ErrorSeverity.HIGH
    assert error_info.category == ErrorCategory.NETWORK
    print(f"✅ Классификация ошибки: {error_info.severity.value}/{error_info.category.value}")
    
    # Тест обработки ошибки с retry стратегией
    recovery_action = await eh.handle_error(connection_error, "exchange", "fetch_balance")
    assert "should_retry" in recovery_action
    print(f"✅ Стратегия восстановления: retry = {recovery_action['should_retry']}")
    
    # Тест Circuit Breaker - создать несколько ошибок подряд
    for i in range(6):  # Больше чем failure_threshold (5)
        await eh.handle_error(ConnectionError(f"Error {i}"), "test", "operation")
    
    # Circuit Breaker должен быть открыт
    cb_status = eh.get_circuit_breaker_status("test", "operation")
    assert cb_status == "open"
    print(f"✅ Circuit Breaker: {cb_status}")
    
    # Тест успешной операции для восстановления
    eh.record_success("test", "operation")
    print("✅ Успешная операция записана")
    
    # Тест статистики
    stats = eh.get_error_statistics()
    assert stats["total_errors"] > 0
    print(f"✅ Статистика ошибок: {stats['total_errors']} всего")


async def test_integration():
    """Тест интеграции компонентов.""" 
    print("\n🔗 Тестирование интеграции...")
    
    # Создать StateMachine и ErrorHandler
    sm = StateMachine(initial_state=TradingState.IDLE)
    eh = ErrorHandler(max_retries=1)
    
    # Симуляция ошибки в торговом состоянии
    await sm.transition_to(TradingState.SCANNING, "Start scanning")
    
    # Обработка ошибки должна предложить переход в ERROR состояние
    recovery_action = await eh.handle_error(
        ValueError("Invalid market data"),
        "scanner", 
        "market_scan"
    )
    
    # Проверить, что предложен корректный переход
    if recovery_action["next_state"]:
        success = await sm.transition_to(recovery_action["next_state"], "Error recovery")
        assert success == True
        print(f"✅ Восстановление после ошибки: {sm.current_state.value}")
    
    print("✅ Интеграция работает корректно")


def run_tests():
    """Запустить все тесты."""
    print("🚀 Запуск тестов рефакторинга движка...\n")
    
    try:
        # Запустить асинхронные тесты
        asyncio.run(test_state_machine())
        asyncio.run(test_error_handler())
        asyncio.run(test_integration())
        
        print("\n🎉 Все тесты прошли успешно!")
        print("✅ StateMachine работает корректно")
        print("✅ ErrorHandler обрабатывает ошибки правильно")
        print("✅ Интеграция между компонентами функционирует")
        print("\n💡 Рефакторинг движка завершен успешно!")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Тест провален: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)



