"""
Утилиты для безопасных математических операций.

Предотвращает crashes от деления на ноль и других математических ошибок.
"""

import numpy as np
import logging
from typing import Union, Optional, List

logger = logging.getLogger(__name__)


def safe_divide(
    numerator: Union[float, int], 
    denominator: Union[float, int], 
    default: Union[float, int] = 0.0,
    log_warning: bool = True
) -> float:
    """
    Безопасное деление с обработкой деления на ноль.
    
    Args:
        numerator: Числитель
        denominator: Знаменатель  
        default: Значение по умолчанию при делении на ноль
        log_warning: Логировать ли предупреждение
        
    Returns:
        Результат деления или default значение
    """
    try:
        if denominator == 0 or np.isnan(denominator) or np.isinf(denominator):
            if log_warning:
                logger.warning(f"Safe divide: denominator is {denominator}, returning {default}")
            return float(default)
        
        result = numerator / denominator
        
        if np.isnan(result) or np.isinf(result):
            if log_warning:
                logger.warning(f"Safe divide: result is {result}, returning {default}")
            return float(default)
            
        return float(result)
        
    except Exception as e:
        if log_warning:
            logger.warning(f"Safe divide error: {e}, returning {default}")
        return float(default)


def safe_percentage(
    part: Union[float, int],
    total: Union[float, int],
    default: float = 0.0,
    multiply_by_100: bool = True,
    log_warning: bool = False
) -> float:
    """
    Безопасное вычисление процента.
    
    Args:
        part: Часть
        total: Целое
        default: Значение по умолчанию
        multiply_by_100: Умножать ли на 100 для процентов
        log_warning: Логировать ли предупреждение
        
    Returns:
        Процент или default значение
    """
    result = safe_divide(part, total, default, log_warning)
    return result * 100 if multiply_by_100 else result


def validate_positive(value: Union[float, int], name: str, default: float = 0.0) -> float:
    """
    Валидация положительного числа.
    
    Args:
        value: Значение для проверки
        name: Имя значения для логирования
        default: Значение по умолчанию
        
    Returns:
        Валидированное значение
    """
    try:
        if value is None or np.isnan(value) or np.isinf(value) or value < 0:
            logger.warning(f"Invalid {name}: {value}, using default {default}")
            return float(default)
        return float(value)
    except Exception as e:
        logger.warning(f"Error validating {name}: {e}, using default {default}")
        return float(default)


def validate_candles(candles: Optional[List], min_count: int = 20, symbol: str = "") -> bool:
    """
    Валидация списка свечей.
    
    Args:
        candles: Список свечей
        min_count: Минимальное количество свечей
        symbol: Символ для логирования
        
    Returns:
        True если валидны, False иначе
    """
    if not candles:
        logger.debug(f"No candles data for {symbol}")
        return False
        
    if len(candles) < min_count:
        logger.debug(f"Insufficient candles for {symbol}: {len(candles)} < {min_count}")
        return False
        
    return True


def safe_ratio(
    numerator: Union[float, int],
    denominator: Union[float, int], 
    min_ratio: float = 0.001,
    max_ratio: float = 1000.0,
    default: float = 1.0
) -> float:
    """
    Безопасное вычисление коэффициента с ограничениями.
    
    Args:
        numerator: Числитель
        denominator: Знаменатель
        min_ratio: Минимальный коэффициент
        max_ratio: Максимальный коэффициент
        default: Значение по умолчанию
        
    Returns:
        Ограниченный коэффициент
    """
    ratio = safe_divide(numerator, denominator, default, log_warning=False)
    return max(min_ratio, min(max_ratio, ratio))


def safe_array_operation(
    array: Optional[List[Union[float, int]]],
    operation: str = "mean",
    default: float = 0.0
) -> float:
    """
    Безопасные операции с массивами.
    
    Args:
        array: Массив значений
        operation: Операция ('mean', 'median', 'sum', 'std')
        default: Значение по умолчанию
        
    Returns:
        Результат операции или default
    """
    try:
        if not array:
            return float(default)
            
        # Фильтруем валидные значения
        valid_values = [
            float(x) for x in array 
            if x is not None and not np.isnan(x) and not np.isinf(x)
        ]
        
        if not valid_values:
            return float(default)
            
        np_array = np.array(valid_values)
        
        if operation == "mean":
            return float(np.mean(np_array))
        elif operation == "median":
            return float(np.median(np_array))
        elif operation == "sum":
            return float(np.sum(np_array))
        elif operation == "std":
            return float(np.std(np_array))
        else:
            logger.warning(f"Unknown operation: {operation}, returning default")
            return float(default)
            
    except Exception as e:
        logger.warning(f"Safe array operation error: {e}, returning default")
        return float(default)


# Aliases для удобства
safe_mean = lambda arr, default=0.0: safe_array_operation(arr, "mean", default)
safe_median = lambda arr, default=0.0: safe_array_operation(arr, "median", default)
safe_sum = lambda arr, default=0.0: safe_array_operation(arr, "sum", default)
