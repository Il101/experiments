"""
Diagnostic tests for technical indicators.

Tests ATR, BB, Donchian calculations against known synthetic data.
"""

import pytest
import numpy as np
from breakout_bot.data.models import Candle
from breakout_bot.indicators.technical import atr, bollinger_bands, bollinger_band_width, donchian_channels


@pytest.fixture
def synthetic_candles_flat():
    """Flat price (no volatility) - ATR should approach 0."""
    return [
        Candle(ts=i*1000, open=100.0, high=100.5, low=99.5, close=100.0, volume=1000.0)
        for i in range(100)
    ]


@pytest.fixture
def synthetic_candles_volatile():
    """High volatility - ATR should be significant."""
    candles = []
    price = 100.0
    for i in range(100):
        # Simulate 5% intraday range
        high = price * 1.025
        low = price * 0.975
        close = price + np.random.uniform(-2.5, 2.5)
        
        candles.append(Candle(
            ts=i*1000,
            open=price,
            high=high,
            low=low,
            close=close,
            volume=1000.0
        ))
        price = close
    
    return candles


@pytest.fixture
def synthetic_candles_trend():
    """Trending price with Bollinger Band expansion."""
    candles = []
    for i in range(100):
        price = 100 + i * 0.5  # Linear uptrend
        candles.append(Candle(
            ts=i*1000,
            open=price,
            high=price + 1,
            low=price - 1,
            close=price + 0.5,
            volume=1000.0
        ))
    
    return candles


def test_atr_flat_market(synthetic_candles_flat):
    """ATR should be small for flat market."""
    atr_values = atr(synthetic_candles_flat, period=14)
    
    # Skip first 14 NaN values
    valid_atr = atr_values[14:]
    
    assert len(valid_atr) > 0
    assert all(atr_val < 1.5 for atr_val in valid_atr), "ATR should be < 1.5 for flat market"
    assert np.mean(valid_atr) < 1.0, "Mean ATR should be < 1.0"


def test_atr_volatile_market(synthetic_candles_volatile):
    """ATR should be significant for volatile market."""
    atr_values = atr(synthetic_candles_volatile, period=14)
    
    valid_atr = atr_values[14:]
    
    assert len(valid_atr) > 0
    assert all(atr_val > 2.0 for atr_val in valid_atr), "ATR should be > 2.0 for volatile market (5% range)"
    assert np.mean(valid_atr) > 3.0, "Mean ATR should be > 3.0"


def test_bollinger_bands_trend(synthetic_candles_trend):
    """Bollinger Bands should expand during trends."""
    upper, lower = bollinger_bands(synthetic_candles_trend, period=20, std_dev=2)
    
    # Check that bands exist and are valid
    valid_upper = upper[~np.isnan(upper)]
    valid_lower = lower[~np.isnan(lower)]
    
    assert len(valid_upper) > 0
    assert len(valid_lower) > 0
    
    # Upper band should always be above lower band
    for u, l in zip(valid_upper, valid_lower):
        assert u > l, "Upper band must be > lower band"
    
    # Bands should expand as trend continues (last band wider than first)
    first_width = valid_upper[0] - valid_lower[0]
    last_width = valid_upper[-1] - valid_lower[-1]
    
    # In a trend, bands typically widen
    assert last_width > first_width * 0.8, "Bands should not shrink significantly in trend"


def test_bollinger_band_width(synthetic_candles_flat):
    """BB width should be small for flat market."""
    bb_width_pct = bollinger_band_width(synthetic_candles_flat, period=20, std_dev=2)
    
    valid_width = bb_width_pct[~np.isnan(bb_width_pct)]
    
    assert len(valid_width) > 0
    assert all(w < 5.0 for w in valid_width), "BB width should be < 5% for flat market"


def test_donchian_channels(synthetic_candles_trend):
    """Donchian channels should track high/low correctly."""
    upper, lower = donchian_channels(synthetic_candles_trend, period=20)
    
    valid_upper = upper[~np.isnan(upper)]
    valid_lower = lower[~np.isnan(lower)]
    
    assert len(valid_upper) > 0
    assert len(valid_lower) > 0
    
    # Upper should be >= lower
    for u, l in zip(valid_upper, valid_lower):
        assert u >= l, "Upper channel must be >= lower channel"
    
    # In an uptrend, upper channel should increase
    assert valid_upper[-1] > valid_upper[0], "Upper channel should rise in uptrend"


def test_atr_handles_nan():
    """ATR should handle missing data gracefully."""
    candles = [
        Candle(ts=i*1000, open=100.0, high=100.0, low=100.0, close=100.0, volume=1000.0)
        for i in range(5)
    ]
    
    # Too few candles for ATR(14)
    atr_values = atr(candles, period=14)
    
    assert len(atr_values) == 5
    assert all(np.isnan(v) for v in atr_values), "All values should be NaN with insufficient data"


def test_indicators_with_zero_volume():
    """Indicators should work even with zero volume."""
    candles = [
        Candle(ts=i*1000, open=100.0, high=101.0, low=99.0, close=100.5, volume=0.0)
        for i in range(50)
    ]
    
    # ATR doesn't depend on volume
    atr_values = atr(candles, period=14)
    valid_atr = atr_values[~np.isnan(atr_values)]
    
    assert len(valid_atr) > 0
    assert all(v > 0 for v in valid_atr), "ATR should be positive even with zero volume"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
