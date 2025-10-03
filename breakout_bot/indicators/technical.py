"""
Technical indicators module for Breakout Bot Trading System.

This module implements various technical indicators used for market analysis,
including ATR, Bollinger Bands, VWAP, Donchian Channels, and more.
"""

import numpy as np
import pandas as pd
from typing import List, Tuple, Optional, Union
from functools import lru_cache
import hashlib
import time
from ..data.models import Candle


class IndicatorCache:
    """Cache for technical indicators to avoid redundant calculations."""
    
    def __init__(self, max_size: int = 1000, ttl: int = 300):
        self.cache = {}
        self.max_size = max_size
        self.ttl = ttl  # Time to live in seconds
        self.access_times = {}
    
    def _generate_key(self, func_name: str, *args, **kwargs) -> str:
        """Generate cache key from function name and arguments."""
        # Create a hash of the arguments
        key_data = f"{func_name}:{str(args)}:{str(sorted(kwargs.items()))}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def get(self, func_name: str, *args, **kwargs):
        """Get cached result if available and not expired."""
        key = self._generate_key(func_name, *args, **kwargs)
        now = time.time()
        
        if key in self.cache:
            # Check if cache entry is still valid
            if now - self.access_times[key] < self.ttl:
                self.access_times[key] = now  # Update access time
                return self.cache[key]
            else:
                # Remove expired entry
                del self.cache[key]
                del self.access_times[key]
        
        return None
    
    def set(self, func_name: str, result, *args, **kwargs):
        """Cache a result."""
        key = self._generate_key(func_name, *args, **kwargs)
        now = time.time()
        
        # Remove oldest entries if cache is full
        if len(self.cache) >= self.max_size:
            oldest_key = min(self.access_times.keys(), key=lambda k: self.access_times[k])
            del self.cache[oldest_key]
            del self.access_times[oldest_key]
        
        self.cache[key] = result
        self.access_times[key] = now
    
    def clear(self):
        """Clear all cached data."""
        self.cache.clear()
        self.access_times.clear()


# Global cache instance
_indicator_cache = IndicatorCache()


def clear_indicator_cache():
    """Clear all cached indicator calculations."""
    _indicator_cache.clear()


def get_cache_stats():
    """Get cache statistics for monitoring."""
    return {
        'cache_size': len(_indicator_cache.cache),
        'max_size': _indicator_cache.max_size,
        'ttl': _indicator_cache.ttl
    }


def cached_indicator(func):
    """Decorator for caching technical indicator calculations."""
    def wrapper(*args, **kwargs):
        func_name = func.__name__
        
        # Try to get from cache
        cached_result = _indicator_cache.get(func_name, *args, **kwargs)
        if cached_result is not None:
            return cached_result
        
        # Calculate and cache result
        result = func(*args, **kwargs)
        _indicator_cache.set(func_name, result, *args, **kwargs)
        
        return result
    
    return wrapper


def sma(values: Union[List[float], np.ndarray], period: int) -> np.ndarray:
    """Calculate Simple Moving Average."""
    values_array = np.array(values)
    if len(values_array) < period:
        return np.full(len(values_array), np.nan)
    
    result = np.full(len(values_array), np.nan)
    for i in range(period - 1, len(values_array)):
        result[i] = np.mean(values_array[i - period + 1:i + 1])
    
    return result


def ema(values: Union[List[float], np.ndarray], period: int) -> np.ndarray:
    """Calculate Exponential Moving Average."""
    values_array = np.array(values)
    if len(values_array) == 0:
        return np.array([])
    
    result = np.full(len(values_array), np.nan)
    alpha = 2.0 / (period + 1)
    
    # Initialize with first non-NaN value
    result[0] = values_array[0]
    
    for i in range(1, len(values_array)):
        if not np.isnan(values_array[i]):
            if np.isnan(result[i-1]):
                result[i] = values_array[i]
            else:
                result[i] = alpha * values_array[i] + (1 - alpha) * result[i-1]
        else:
            result[i] = result[i-1]
    
    return result


def true_range(high: np.ndarray, low: np.ndarray, close: np.ndarray) -> np.ndarray:
    """Calculate True Range for ATR calculation."""
    prev_close = np.roll(close, 1)
    prev_close[0] = close[0]  # Handle first value
    
    tr1 = high - low
    tr2 = np.abs(high - prev_close)
    tr3 = np.abs(low - prev_close)
    
    return np.maximum(tr1, np.maximum(tr2, tr3))


@cached_indicator
def atr(candles: List[Candle], period: int = 14) -> np.ndarray:
    """
    Calculate Average True Range (ATR) with caching.
    
    Args:
        candles: List of Candle objects
        period: ATR period (default 14)
    
    Returns:
        Array of ATR values
    """
    if len(candles) < 2:
        return np.array([np.nan] * len(candles))
    
    # Check if we have enough data for the period
    if len(candles) < period:
        return np.array([np.nan] * len(candles))
    
    highs = np.array([c.high for c in candles])
    lows = np.array([c.low for c in candles])
    closes = np.array([c.close for c in candles])
    
    tr_values = true_range(highs, lows, closes)
    atr_values = ema(tr_values, period)
    
    return atr_values


@cached_indicator
def bollinger_bands(values: Union[List[float], np.ndarray], 
                   period: int = 20, 
                   std_dev: float = 2.0) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Calculate Bollinger Bands with optimized O(n) complexity.
    
    Args:
        values: Price values (typically close prices)
        period: Moving average period (default 20)
        std_dev: Standard deviation multiplier (default 2.0)
    
    Returns:
        Tuple of (upper_band, middle_band, lower_band)
    """
    values_array = np.array(values)
    
    if len(values_array) < period:
        return (np.full(len(values_array), np.nan), 
                np.full(len(values_array), np.nan), 
                np.full(len(values_array), np.nan))
    
    # Calculate moving average (middle band) - O(n)
    middle_band = sma(values_array, period)
    
    # Calculate standard deviation using rolling window - O(n)
    std_values = np.full(len(values_array), np.nan)
    
    # Use vectorized operations for better performance
    for i in range(period - 1, len(values_array)):
        window = values_array[i - period + 1:i + 1]
        if len(window) == period:
            # Use numpy's optimized std calculation
            std_values[i] = np.std(window, ddof=0)
    
    # Calculate upper and lower bands - O(n)
    upper_band = middle_band + (std_dev * std_values)
    lower_band = middle_band - (std_dev * std_values)
    
    return upper_band, middle_band, lower_band


def bollinger_bands_optimized(values: Union[List[float], np.ndarray], 
                             period: int = 20, 
                             std_dev: float = 2.0) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Highly optimized Bollinger Bands using pandas rolling operations.
    This version is significantly faster for large datasets.
    
    Args:
        values: Price values (typically close prices)
        period: Moving average period (default 20)
        std_dev: Standard deviation multiplier (default 2.0)
    
    Returns:
        Tuple of (upper_band, middle_band, lower_band)
    """
    try:
        import pandas as pd
        
        values_array = np.array(values)
        if len(values_array) < period:
            return (np.full(len(values_array), np.nan), 
                    np.full(len(values_array), np.nan), 
                    np.full(len(values_array), np.nan))
        
        # Convert to pandas Series for efficient rolling operations
        series = pd.Series(values_array)
        
        # Calculate rolling mean and std - both O(n)
        middle_band = series.rolling(window=period, min_periods=period).mean()
        std_values = series.rolling(window=period, min_periods=period).std(ddof=0)
        
        # Calculate bands
        upper_band = middle_band + (std_dev * std_values)
        lower_band = middle_band - (std_dev * std_values)
        
        return upper_band.values, middle_band.values, lower_band.values
        
    except ImportError:
        # Fallback to numpy implementation if pandas not available
        return bollinger_bands(values, period, std_dev)


def bollinger_band_width(upper: np.ndarray, lower: np.ndarray, middle: np.ndarray) -> np.ndarray:
    """
    Calculate Bollinger Band Width as percentage.
    
    Args:
        upper: Upper Bollinger Band
        lower: Lower Bollinger Band  
        middle: Middle Bollinger Band (SMA)
    
    Returns:
        Array of BB width percentages
    """
    return ((upper - lower) / middle) * 100


def donchian_channels(candles: List[Candle], period: int = 20) -> Tuple[np.ndarray, np.ndarray]:
    """
    Calculate Donchian Channels (highest high and lowest low).
    
    Args:
        candles: List of Candle objects
        period: Lookback period (default 20)
    
    Returns:
        Tuple of (upper_channel, lower_channel)
    """
    if len(candles) < period:
        return (np.full(len(candles), np.nan), 
                np.full(len(candles), np.nan))
    
    highs = np.array([c.high for c in candles])
    lows = np.array([c.low for c in candles])
    
    upper_channel = np.full(len(candles), np.nan)
    lower_channel = np.full(len(candles), np.nan)
    
    for i in range(period - 1, len(candles)):
        window_highs = highs[i - period + 1:i + 1]
        window_lows = lows[i - period + 1:i + 1]
        
        upper_channel[i] = np.max(window_highs)
        lower_channel[i] = np.min(window_lows)
    
    return upper_channel, lower_channel


@cached_indicator
def vwap(candles: List[Candle]) -> np.ndarray:
    """
    Calculate Volume Weighted Average Price (VWAP) with caching.
    
    Args:
        candles: List of Candle objects
    
    Returns:
        Array of VWAP values
    """
    if not candles:
        return np.array([])
    
    typical_prices = np.array([c.typical_price for c in candles])
    volumes = np.array([c.volume for c in candles])
    
    cumulative_pv = np.cumsum(typical_prices * volumes)
    cumulative_volume = np.cumsum(volumes)
    
    # Avoid division by zero
    vwap_values = np.divide(cumulative_pv, cumulative_volume, 
                           out=np.zeros_like(cumulative_pv), 
                           where=cumulative_volume!=0)
    
    return vwap_values


def rsi(values: Union[List[float], np.ndarray], period: int = 14) -> np.ndarray:
    """
    Calculate Relative Strength Index (RSI).
    
    Args:
        values: Price values
        period: RSI period (default 14)
    
    Returns:
        Array of RSI values (0-100)
    """
    values_array = np.array(values)
    
    if len(values_array) < period + 1:
        return np.full(len(values_array), np.nan)
    
    # Calculate price changes
    delta = np.diff(values_array)
    
    # Separate gains and losses
    gains = np.where(delta > 0, delta, 0)
    losses = np.where(delta < 0, -delta, 0)
    
    # Calculate initial averages
    avg_gain = np.mean(gains[:period])
    avg_loss = np.mean(losses[:period])
    
    # Calculate RSI values
    rsi_values = np.full(len(values_array), np.nan)
    
    for i in range(period, len(delta)):
        if avg_loss == 0:
            rsi_values[i + 1] = 100
        else:
            rs = avg_gain / avg_loss
            rsi_values[i + 1] = 100 - (100 / (1 + rs))
        
        # Update averages using EMA
        alpha = 1.0 / period
        avg_gain = alpha * gains[i] + (1 - alpha) * avg_gain
        avg_loss = alpha * losses[i] + (1 - alpha) * avg_loss
    
    return rsi_values


def obv(candles: List[Candle]) -> np.ndarray:
    """
    Calculate On-Balance Volume (OBV).
    
    Args:
        candles: List of Candle objects
    
    Returns:
        Array of OBV values
    """
    if len(candles) < 2:
        return np.array([0] * len(candles))
    
    closes = np.array([c.close for c in candles])
    volumes = np.array([c.volume for c in candles])
    
    obv_values = np.zeros(len(candles))
    
    for i in range(1, len(candles)):
        if closes[i] > closes[i-1]:
            obv_values[i] = obv_values[i-1] + volumes[i]
        elif closes[i] < closes[i-1]:
            obv_values[i] = obv_values[i-1] - volumes[i]
        else:
            obv_values[i] = obv_values[i-1]
    
    return obv_values


def chandelier_exit(candles: List[Candle], 
                   period: int = 22, 
                   atr_multiplier: float = 3.0,
                   long: bool = True) -> np.ndarray:
    """
    Calculate Chandelier Exit levels.
    
    Args:
        candles: List of Candle objects
        period: Lookback period (default 22)
        atr_multiplier: ATR multiplier (default 3.0)
        long: True for long positions, False for short
    
    Returns:
        Array of Chandelier Exit levels
    """
    if len(candles) < period:
        return np.full(len(candles), np.nan)
    
    atr_values = atr(candles, period)
    
    if long:
        # For long positions: highest high - (ATR * multiplier)
        highs = np.array([c.high for c in candles])
        highest_high = np.full(len(candles), np.nan)
        
        for i in range(period - 1, len(candles)):
            highest_high[i] = np.max(highs[i - period + 1:i + 1])
        
        return highest_high - (atr_values * atr_multiplier)
    else:
        # For short positions: lowest low + (ATR * multiplier)
        lows = np.array([c.low for c in candles])
        lowest_low = np.full(len(candles), np.nan)
        
        for i in range(period - 1, len(candles)):
            lowest_low[i] = np.min(lows[i - period + 1:i + 1])
        
        return lowest_low + (atr_values * atr_multiplier)


def calculate_correlation(values1: np.ndarray, values2: np.ndarray, period: int = 50) -> np.ndarray:
    """
    Calculate rolling correlation between two price series.
    
    Args:
        values1: First price series
        values2: Second price series
        period: Rolling correlation period
    
    Returns:
        Array of correlation values
    """
    if len(values1) != len(values2):
        raise ValueError("Input arrays must have the same length")
    
    if len(values1) < period:
        return np.full(len(values1), np.nan)
    
    correlations = np.full(len(values1), np.nan)
    
    for i in range(period - 1, len(values1)):
        window1 = values1[i - period + 1:i + 1]
        window2 = values2[i - period + 1:i + 1]
        
        # Remove NaN values
        mask = ~(np.isnan(window1) | np.isnan(window2))
        if np.sum(mask) > 2:  # Need at least 3 points for correlation
            correlations[i] = np.corrcoef(window1[mask], window2[mask])[0, 1]
    
    return correlations


def volume_surge_ratio(candles: List[Candle], lookback_periods: int = 20) -> np.ndarray:
    """
    Calculate volume surge ratio (current volume / median volume).
    
    Args:
        candles: List of Candle objects
        lookback_periods: Number of periods for median calculation
    
    Returns:
        Array of volume surge ratios
    """
    if len(candles) < lookback_periods:
        return np.full(len(candles), np.nan)
    
    volumes = np.array([c.volume for c in candles])
    surge_ratios = np.full(len(candles), np.nan)
    
    for i in range(lookback_periods - 1, len(candles)):
        window_volumes = volumes[i - lookback_periods + 1:i + 1]
        median_volume = np.median(window_volumes[:-1])  # Exclude current candle
        
        if median_volume > 0:
            surge_ratios[i] = volumes[i] / median_volume
    
    return surge_ratios


def swing_highs_lows(candles: List[Candle], 
                    left_bars: int = 2, 
                    right_bars: int = 2) -> Tuple[np.ndarray, np.ndarray]:
    """
    Identify swing highs and lows.
    
    Args:
        candles: List of Candle objects
        left_bars: Number of bars to the left to check
        right_bars: Number of bars to the right to check
    
    Returns:
        Tuple of (swing_highs, swing_lows) with prices or NaN
    """
    if len(candles) < left_bars + right_bars + 1:
        return (np.full(len(candles), np.nan), 
                np.full(len(candles), np.nan))
    
    highs = np.array([c.high for c in candles])
    lows = np.array([c.low for c in candles])
    
    swing_highs = np.full(len(candles), np.nan)
    swing_lows = np.full(len(candles), np.nan)
    
    for i in range(left_bars, len(candles) - right_bars):
        # Check for swing high
        center_high = highs[i]
        is_swing_high = True
        
        # Check left side
        for j in range(i - left_bars, i):
            if highs[j] >= center_high:
                is_swing_high = False
                break
        
        # Check right side
        if is_swing_high:
            for j in range(i + 1, i + right_bars + 1):
                if highs[j] >= center_high:
                    is_swing_high = False
                    break
        
        if is_swing_high:
            swing_highs[i] = center_high
        
        # Check for swing low
        center_low = lows[i]
        is_swing_low = True
        
        # Check left side
        for j in range(i - left_bars, i):
            if lows[j] <= center_low:
                is_swing_low = False
                break
        
        # Check right side
        if is_swing_low:
            for j in range(i + 1, i + right_bars + 1):
                if lows[j] <= center_low:
                    is_swing_low = False
                    break
        
        if is_swing_low:
            swing_lows[i] = center_low
    
    return swing_highs, swing_lows