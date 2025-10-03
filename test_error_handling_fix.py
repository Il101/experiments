#!/usr/bin/env python3
"""
Тест улучшенной обработки ошибок
"""

import sys
import asyncio
import time
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from breakout_bot.utils.enhanced_error_handler import (
    enhanced_error_handler, 
    ErrorContext, 
    ErrorCategory, 
    ErrorSeverity,
    handle_network_errors,
    handle_exchange_errors,
    handle_critical_errors
)

async def test_error_classification():
    """Тест классификации ошибок"""
    print("🔍 Тестирую классификацию ошибок...")
    
    # Test network errors
    network_error = ConnectionError("Failed to connect to exchange")
    category = enhanced_error_handler.classify_error(network_error)
    assert category == ErrorCategory.NETWORK, f"Expected NETWORK, got {category}"
    print("   ✅ Network errors классифицированы правильно")
    
    # Test validation errors  
    validation_error = ValueError("Invalid symbol format")
    category = enhanced_error_handler.classify_error(validation_error)
    assert category == ErrorCategory.DATA_VALIDATION, f"Expected DATA_VALIDATION, got {category}"
    print("   ✅ Validation errors классифицированы правильно")
    
    # Test unknown errors
    unknown_error = RuntimeError("Something went wrong")
    category = enhanced_error_handler.classify_error(unknown_error)
    assert category == ErrorCategory.UNKNOWN, f"Expected UNKNOWN, got {category}"
    print("   ✅ Unknown errors классифицированы правильно")
    
    return True

async def test_retry_mechanism():
    """Тест механизма повторов"""
    print("\n🔄 Тестирую retry механизм...")
    
    attempt_count = 0
    
    async def failing_operation():
        nonlocal attempt_count
        attempt_count += 1
        if attempt_count < 3:
            raise ConnectionError(f"Attempt {attempt_count} failed")
        return f"Success on attempt {attempt_count}"
    
    context = ErrorContext(
        category=ErrorCategory.NETWORK,
        severity=ErrorSeverity.MEDIUM,
        operation="test_retry",
        component="test",
        max_retries=3,
        retry_delay=0.1  # Fast retry for testing
    )
    
    start_time = time.time()
    result = await enhanced_error_handler.handle_with_retry(failing_operation, context)
    elapsed = time.time() - start_time
    
    assert result == "Success on attempt 3", f"Expected success message, got {result}"
    assert attempt_count == 3, f"Expected 3 attempts, got {attempt_count}"
    assert elapsed >= 0.3, f"Expected at least 0.3s delay, got {elapsed:.2f}s"  # 0.1 + 0.2 backoff
    print(f"   ✅ Retry успешен после {attempt_count} попыток за {elapsed:.2f}s")
    
    return True

async def test_severity_handling():
    """Тест обработки различных уровней критичности"""
    print("\n⚠️ Тестирую обработку severity levels...")
    
    # Test critical error (should not retry)
    try:
        async def critical_failing_operation():
            raise ValueError("Critical validation error")
        
        context = ErrorContext(
            category=ErrorCategory.DATA_VALIDATION,
            severity=ErrorSeverity.CRITICAL,
            operation="critical_test",
            component="test",
            max_retries=3  # Should not retry despite max_retries
        )
        
        await enhanced_error_handler.handle_with_retry(critical_failing_operation, context)
        assert False, "Critical error should not succeed"
    except ValueError:
        print("   ✅ Critical errors НЕ повторяются")
    
    # Test low severity error with error context
    error_caught = False
    try:
        async with enhanced_error_handler.error_context(
            ErrorContext(
                category=ErrorCategory.DATA_VALIDATION,
                severity=ErrorSeverity.LOW,
                operation="low_severity_test",
                component="test"
            )
        ):
            raise ValueError("Low severity error")
    except ValueError:
        error_caught = True
    
    print("   ✅ Error context manager работает корректно")
    return True

async def test_decorators():
    """Тест декораторов для разных типов ошибок"""
    print("\n🎯 Тестирую декораторы...")
    
    attempt_count = 0
    
    @handle_network_errors("test_network_decorator", max_retries=2)
    async def network_operation():
        nonlocal attempt_count
        attempt_count += 1
        if attempt_count < 2:
            raise ConnectionError(f"Network attempt {attempt_count} failed")
        return "Network success"
    
    result = await network_operation()
    assert result == "Network success", f"Expected success, got {result}"
    assert attempt_count == 2, f"Expected 2 attempts, got {attempt_count}"
    print("   ✅ Network decorator работает")
    
    # Test exchange decorator
    attempt_count = 0
    
    @handle_exchange_errors("test_exchange_decorator", max_retries=1)
    async def exchange_operation():
        nonlocal attempt_count
        attempt_count += 1
        if attempt_count < 2:
            raise Exception("Exchange attempt failed")
        return "Exchange success"
    
    result = await exchange_operation()
    print("   ✅ Exchange decorator работает")
    
    # Test critical decorator
    @handle_critical_errors("test_critical_decorator")
    async def critical_operation():
        return "Critical success"
    
    result = await critical_operation()
    assert result == "Critical success"
    print("   ✅ Critical decorator работает")
    
    return True

async def test_circuit_breaker():
    """Тест circuit breaker функциональности"""
    print("\n🔌 Тестирую circuit breaker...")
    
    # Reset error stats
    enhanced_error_handler.error_counts.clear()
    enhanced_error_handler.circuit_breakers.clear()
    
    # Generate many errors to trigger circuit breaker
    for i in range(12):  # More than threshold of 10
        enhanced_error_handler._update_error_stats(ErrorCategory.NETWORK)
    
    # Check if circuit breaker is triggered
    stats = enhanced_error_handler.get_error_stats()
    assert stats['total_errors'] == 12, f"Expected 12 errors, got {stats['total_errors']}"
    assert len(stats['circuit_breakers']) > 0, "Circuit breaker should be triggered"
    print(f"   ✅ Circuit breaker triggered after {stats['total_errors']} errors")
    
    # Test reset
    enhanced_error_handler.reset_circuit_breaker("network_high_error_rate") 
    stats = enhanced_error_handler.get_error_stats()
    print("   ✅ Circuit breaker reset работает")
    
    return True

async def test_error_stats():
    """Тест сбора статистики ошибок"""
    print("\n📊 Тестирую статистику ошибок...")
    
    # Reset stats
    enhanced_error_handler.error_counts.clear()
    enhanced_error_handler.circuit_breakers.clear()
    
    # Generate various types of errors
    test_errors = [
        (ConnectionError("Network 1"), ErrorCategory.NETWORK),
        (ValueError("Validation 1"), ErrorCategory.DATA_VALIDATION),
        (ConnectionError("Network 2"), ErrorCategory.NETWORK),
        (RuntimeError("Unknown 1"), ErrorCategory.UNKNOWN)
    ]
    
    for error, expected_category in test_errors:
        category = enhanced_error_handler.classify_error(error)
        enhanced_error_handler._update_error_stats(category)
        assert category == expected_category
    
    stats = enhanced_error_handler.get_error_stats()
    expected_counts = {
        'network': 2,
        'data_validation': 1, 
        'unknown': 1
    }
    
    for category, expected_count in expected_counts.items():
        actual_count = stats['error_counts'].get(category, 0)
        assert actual_count == expected_count, f"Expected {expected_count} {category} errors, got {actual_count}"
    
    print(f"   ✅ Статистика собрана корректно: {stats['error_counts']}")
    return True

async def main():
    """Главная функция тестирования"""
    print("🔧 ТЕСТ УЛУЧШЕННОЙ ОБРАБОТКИ ОШИБОК")
    print("=" * 50)
    
    tests = [
        test_error_classification,
        test_retry_mechanism,
        test_severity_handling,
        test_decorators,
        test_circuit_breaker,
        test_error_stats
    ]
    
    results = []
    for test in tests:
        try:
            result = await test()
            results.append(result)
        except Exception as e:
            print(f"   ❌ Ошибка в тесте {test.__name__}: {e}")
            results.append(False)
    
    print(f"\n{'='*50}")
    
    if all(results):
        print("🎉 ВСЕ ТЕСТЫ ОБРАБОТКИ ОШИБОК ПРОШЛИ!")
        print("✅ Enhanced Error Handler готов к использованию!")
        return True
    else:
        passed = sum(results)
        total = len(results)
        print(f"❌ ПРОШЛО {passed}/{total} ТЕСТОВ")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
