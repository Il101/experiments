"""
Diagnostic tests for scanner filters.

Tests each filter (liquidity, volatility, correlation) with synthetic data.
"""

import pytest
import numpy as np
from breakout_bot.data.models import Candle, L2Depth, MarketData
from breakout_bot.scanner.market_scanner import MarketFilter
from breakout_bot.config.settings import TradingPreset, LiquidityFilters, VolatilityFilters


@pytest.fixture
def base_preset():
    """Create a base preset with standard filters."""
    return TradingPreset(
        name="test_preset",
        liquidity_filters=LiquidityFilters(
            min_24h_volume_usd=1_000_000,
            min_oi_usd=500_000,
            max_spread_bps=20,
            min_depth_0_3pct_usd=10_000,
            min_trades_per_minute=5.0
        ),
        volatility_filters=VolatilityFilters(
            atr_range_min=0.01,
            atr_range_max=0.05,
            bb_width_percentile_max=80,
            volume_surge_1h_min=1.2,
            volume_surge_5m_min=1.1
        )
    )


@pytest.fixture
def high_liquid_market_data():
    """High liquidity market that should pass filters."""
    return MarketData(
        symbol="BTC/USDT",
        price=50000.0,
        volume_24h_usd=5_000_000_000,  # $5B
        oi_usd=2_000_000_000,  # $2B
        oi_change_24h=0.05,
        trades_per_minute=50.0,
        btc_correlation=0.1,  # Low correlation (good)
        atr_15m=500.0,  # 1% ATR
        bb_width_pct=50.0,
        l2_depth=L2Depth(
            bid_usd_0_5pct=100_000,
            ask_usd_0_5pct=100_000,
            bid_usd_0_3pct=50_000,
            ask_usd_0_3pct=50_000,
            spread_bps=5.0,
            imbalance=0.1
        )
    )


@pytest.fixture
def low_liquid_market_data():
    """Low liquidity market that should fail filters."""
    return MarketData(
        symbol="SHITCOIN/USDT",
        price=0.001,
        volume_24h_usd=50_000,  # Only $50k
        oi_usd=10_000,  # $10k OI
        oi_change_24h=0.0,
        trades_per_minute=0.5,  # Very low
        btc_correlation=0.95,  # High correlation (bad)
        atr_15m=0.00001,  # 1% ATR
        bb_width_pct=90.0,  # Too wide
        l2_depth=L2Depth(
            bid_usd_0_5pct=500,
            ask_usd_0_5pct=500,
            bid_usd_0_3pct=200,
            ask_usd_0_3pct=200,
            spread_bps=100.0,  # 1% spread (bad)
            imbalance=0.5
        )
    )


def test_liquidity_filter_high_volume_passes(base_preset, high_liquid_market_data):
    """High volume market should pass 24h volume filter."""
    filter_obj = MarketFilter("test", base_preset)
    results = filter_obj.apply_liquidity_filters(high_liquid_market_data)
    
    assert results['min_24h_volume'].passed, "High volume should pass filter"
    assert results['min_24h_volume'].value == 5_000_000_000


def test_liquidity_filter_low_volume_fails(base_preset, low_liquid_market_data):
    """Low volume market should fail 24h volume filter."""
    filter_obj = MarketFilter("test", base_preset)
    results = filter_obj.apply_liquidity_filters(low_liquid_market_data)
    
    assert not results['min_24h_volume'].passed, "Low volume should fail filter"
    assert results['min_24h_volume'].value == 50_000


def test_liquidity_filter_spread(base_preset, high_liquid_market_data, low_liquid_market_data):
    """Test spread filter."""
    filter_obj = MarketFilter("test", base_preset)
    
    # High liquid should pass (5 bps < 20 bps)
    results_pass = filter_obj.apply_liquidity_filters(high_liquid_market_data)
    assert results_pass['max_spread'].passed
    
    # Low liquid should fail (100 bps > 20 bps)
    results_fail = filter_obj.apply_liquidity_filters(low_liquid_market_data)
    assert not results_fail['max_spread'].passed


def test_liquidity_filter_trades_per_minute(base_preset, high_liquid_market_data, low_liquid_market_data):
    """Test trades per minute filter."""
    filter_obj = MarketFilter("test", base_preset)
    
    # High liquid: 50 TPM > 5 TPM (pass)
    results_pass = filter_obj.apply_liquidity_filters(high_liquid_market_data)
    assert results_pass['min_trades_per_minute'].passed
    
    # Low liquid: 0.5 TPM < 5 TPM (fail)
    results_fail = filter_obj.apply_liquidity_filters(low_liquid_market_data)
    assert not results_fail['min_trades_per_minute'].failed


def test_volatility_filter_atr_range(base_preset):
    """Test ATR range filter."""
    filter_obj = MarketFilter("test", base_preset)
    
    # Create market with ATR in acceptable range
    market_in_range = MarketData(
        symbol="TEST/USDT",
        price=100.0,
        volume_24h_usd=5_000_000,
        atr_15m=2.0,  # 2% ATR (in range 1%-5%)
        bb_width_pct=50.0,
        btc_correlation=0.5
    )
    
    # Create market with ATR too high
    market_too_volatile = MarketData(
        symbol="TEST/USDT",
        price=100.0,
        volume_24h_usd=5_000_000,
        atr_15m=10.0,  # 10% ATR (too high)
        bb_width_pct=50.0,
        btc_correlation=0.5
    )
    
    results_pass = filter_obj.apply_volatility_filters(market_in_range, None)
    results_fail = filter_obj.apply_volatility_filters(market_too_volatile, None)
    
    assert results_pass['atr_range'].passed
    assert not results_fail['atr_range'].passed


def test_correlation_filter_high_correlation_fails(base_preset, low_liquid_market_data):
    """High BTC correlation should fail filter."""
    filter_obj = MarketFilter("test", base_preset)
    results = filter_obj.apply_correlation_filter(low_liquid_market_data)
    
    # Correlation 0.95 > 0.85 limit (with lenient adjustment)
    assert not results['correlation'].passed


def test_correlation_filter_low_correlation_passes(base_preset, high_liquid_market_data):
    """Low BTC correlation should pass filter."""
    filter_obj = MarketFilter("test", base_preset)
    results = filter_obj.apply_correlation_filter(high_liquid_market_data)
    
    # Correlation 0.1 < 0.85 limit
    assert results['correlation'].passed


def test_filter_with_missing_l2_depth(base_preset):
    """Filter should handle missing L2 depth gracefully."""
    market_no_depth = MarketData(
        symbol="TEST/USDT",
        price=100.0,
        volume_24h_usd=5_000_000,
        trades_per_minute=10.0,
        btc_correlation=0.5,
        atr_15m=2.0,
        bb_width_pct=50.0,
        l2_depth=None  # No depth data
    )
    
    filter_obj = MarketFilter("test", base_preset)
    results = filter_obj.apply_liquidity_filters(market_no_depth)
    
    # Should skip spread filter gracefully
    assert 'max_spread' in results
    assert results['max_spread'].passed  # Skipped = passed


def test_filter_reasons_populated(base_preset, high_liquid_market_data):
    """Filter results should include human-readable reasons."""
    filter_obj = MarketFilter("test", base_preset)
    results = filter_obj.apply_liquidity_filters(high_liquid_market_data)
    
    for filter_name, result in results.items():
        assert result.reason != "", f"Filter {filter_name} should have a reason"
        assert isinstance(result.reason, str)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
