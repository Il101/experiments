"""
Diagnostic tests for signal generation (momentum & retest).

Tests that signal gates work correctly with synthetic data.
"""

import pytest
import numpy as np
from breakout_bot.data.models import Candle, L2Depth, TradingLevel
from breakout_bot.signals.signal_generator import SignalValidator
from breakout_bot.config.settings import SignalConfig


@pytest.fixture
def signal_config():
    """Standard signal configuration."""
    return SignalConfig(
        momentum_epsilon=0.002,  # 0.2% breakout buffer
        momentum_volume_multiplier=1.5,  # 150% volume surge
        momentum_body_ratio_min=0.6,  # 60% body
        l2_imbalance_threshold=0.2,  # 20% imbalance
        vwap_gap_max_atr=1.5,  # 1.5 ATR from VWAP
        retest_max_pierce_atr=0.5  # 0.5 ATR pierce allowed
    )


@pytest.fixture
def resistance_level():
    """A resistance level at $50,000."""
    return TradingLevel(
        price=50000.0,
        level_type="resistance",
        touch_count=5,
        strength=0.8,
        first_touch_ts=1000000,
        last_touch_ts=1010000
    )


@pytest.fixture
def breakout_candles():
    """Candles showing a momentum breakout."""
    candles = []
    
    # Build up: price consolidating below resistance
    for i in range(18):
        candles.append(Candle(
            ts=i*1000,
            open=49800 + i*5,
            high=49900 + i*5,
            low=49700 + i*5,
            close=49850 + i*5,
            volume=1000.0
        ))
    
    # Breakout candle: strong volume, large body
    candles.append(Candle(
        ts=18*1000,
        open=49950,
        high=50250,  # Breaks 50000 resistance
        low=49900,
        close=50200,  # Strong close near high
        volume=5000.0  # 5x normal volume
    ))
    
    return candles


@pytest.fixture
def no_breakout_candles():
    """Candles that approach but don't break resistance."""
    candles = []
    
    for i in range(19):
        candles.append(Candle(
            ts=i*1000,
            open=49800,
            high=49950,  # Never breaks 50000
            low=49700,
            close=49850,
            volume=1000.0
        ))
    
    return candles


@pytest.fixture
def high_imbalance_depth():
    """L2 depth with strong buy-side imbalance."""
    return L2Depth(
        bid_usd_0_5pct=100_000,  # Strong bids
        ask_usd_0_5pct=30_000,   # Weak asks
        bid_usd_0_3pct=50_000,
        ask_usd_0_3pct=15_000,
        spread_bps=10.0,
        imbalance=0.5  # (100k - 30k) / 130k ≈ 0.54
    )


@pytest.fixture
def balanced_depth():
    """L2 depth with balanced books."""
    return L2Depth(
        bid_usd_0_5pct=50_000,
        ask_usd_0_5pct=50_000,
        bid_usd_0_3pct=25_000,
        ask_usd_0_3pct=25_000,
        spread_bps=10.0,
        imbalance=0.0  # Balanced
    )


def test_momentum_price_breakout_passes(signal_config, breakout_candles, resistance_level, high_imbalance_depth):
    """Price breaks resistance → breakout condition passes."""
    validator = SignalValidator(signal_config)
    
    conditions = validator.validate_momentum_conditions(
        symbol="BTC/USDT",
        candles=breakout_candles,
        level=resistance_level,
        l2_depth=high_imbalance_depth,
        current_price=50200
    )
    
    assert conditions['price_breakout'], "Price should break resistance"
    assert conditions['details']['close'] > conditions['details']['breakout_price']


def test_momentum_price_no_breakout_fails(signal_config, no_breakout_candles, resistance_level, high_imbalance_depth):
    """Price doesn't break resistance → breakout condition fails."""
    validator = SignalValidator(signal_config)
    
    conditions = validator.validate_momentum_conditions(
        symbol="BTC/USDT",
        candles=no_breakout_candles,
        level=resistance_level,
        l2_depth=high_imbalance_depth,
        current_price=49850
    )
    
    assert not conditions['price_breakout'], "Price should not break resistance"


def test_momentum_volume_surge_passes(signal_config, breakout_candles, resistance_level, high_imbalance_depth):
    """High volume on breakout → volume surge passes."""
    validator = SignalValidator(signal_config)
    
    conditions = validator.validate_momentum_conditions(
        symbol="BTC/USDT",
        candles=breakout_candles,
        level=resistance_level,
        l2_depth=high_imbalance_depth,
        current_price=50200
    )
    
    assert conditions['volume_surge'], "Volume surge should be detected"
    # Current volume (5000) vs median of previous (1000) = 5x surge
    assert conditions['details']['volume_ratio'] >= signal_config.momentum_volume_multiplier


def test_momentum_body_ratio_strong_candle(signal_config, breakout_candles, resistance_level, high_imbalance_depth):
    """Strong body (close near high) → body ratio passes."""
    validator = SignalValidator(signal_config)
    
    conditions = validator.validate_momentum_conditions(
        symbol="BTC/USDT",
        candles=breakout_candles,
        level=resistance_level,
        l2_depth=high_imbalance_depth,
        current_price=50200
    )
    
    assert conditions['body_ratio'], "Body ratio should pass"
    # Breakout candle: body = |50200 - 49950| = 250, range = 50250 - 49900 = 350
    # body_ratio = 250 / 350 = 0.714 > 0.6 ✓
    assert conditions['details']['body_ratio'] >= signal_config.momentum_body_ratio_min


def test_momentum_l2_imbalance_passes(signal_config, breakout_candles, resistance_level, high_imbalance_depth):
    """Strong L2 imbalance → imbalance condition passes."""
    validator = SignalValidator(signal_config)
    
    conditions = validator.validate_momentum_conditions(
        symbol="BTC/USDT",
        candles=breakout_candles,
        level=resistance_level,
        l2_depth=high_imbalance_depth,
        current_price=50200
    )
    
    assert conditions['l2_imbalance'], "L2 imbalance should pass"
    assert abs(conditions['details']['l2_imbalance']) >= signal_config.l2_imbalance_threshold


def test_momentum_l2_balanced_fails(signal_config, breakout_candles, resistance_level, balanced_depth):
    """Balanced L2 → imbalance condition fails."""
    validator = SignalValidator(signal_config)
    
    conditions = validator.validate_momentum_conditions(
        symbol="BTC/USDT",
        candles=breakout_candles,
        level=resistance_level,
        l2_depth=balanced_depth,
        current_price=50200
    )
    
    assert not conditions['l2_imbalance'], "Balanced L2 should fail imbalance check"


def test_retest_level_proximity_passes(signal_config, resistance_level, high_imbalance_depth):
    """Price near level after breakout → retest condition passes."""
    validator = SignalValidator(signal_config)
    
    # Simulate retest: price came back to resistance after breaking it
    retest_candles = [
        Candle(ts=i*1000, open=50000, high=50100, low=49900, close=50050, volume=1000)
        for i in range(20)
    ]
    
    conditions = validator.validate_retest_conditions(
        symbol="BTC/USDT",
        candles=retest_candles,
        level=resistance_level,
        l2_depth=high_imbalance_depth,
        current_price=50050,  # Within 0.5% of level (50000)
        previous_breakout={'timestamp': 1000000}
    )
    
    assert conditions['level_retest'], "Price should be near level for retest"
    assert conditions['details']['distance_from_level'] <= 0.005  # 0.5%


def test_retest_too_far_from_level_fails(signal_config, resistance_level, high_imbalance_depth):
    """Price too far from level → retest condition fails."""
    validator = SignalValidator(signal_config)
    
    retest_candles = [
        Candle(ts=i*1000, open=51000, high=51100, low=50900, close=51050, volume=1000)
        for i in range(20)
    ]
    
    conditions = validator.validate_retest_conditions(
        symbol="BTC/USDT",
        candles=retest_candles,
        level=resistance_level,
        l2_depth=high_imbalance_depth,
        current_price=51050,  # 2% away from level
        previous_breakout={'timestamp': 1000000}
    )
    
    assert not conditions['level_retest'], "Price too far for retest"


def test_all_conditions_must_pass_for_signal():
    """Test that all momentum conditions must pass for valid signal."""
    config = SignalConfig()
    validator = SignalValidator(config)
    
    # Create scenario where only 3/5 conditions pass
    partial_candles = [
        Candle(ts=i*1000, open=50000, high=50050, low=49950, close=50010, volume=1000)
        for i in range(20)
    ]
    
    level = TradingLevel(
        price=50000, level_type="resistance", touch_count=3,
        strength=0.7, first_touch_ts=1000, last_touch_ts=2000
    )
    
    weak_depth = L2Depth(
        bid_usd_0_5pct=50_000, ask_usd_0_5pct=50_000,
        bid_usd_0_3pct=25_000, ask_usd_0_3pct=25_000,
        spread_bps=10.0, imbalance=0.05  # Weak imbalance
    )
    
    conditions = validator.validate_momentum_conditions(
        symbol="BTC/USDT",
        candles=partial_candles,
        level=level,
        l2_depth=weak_depth,
        current_price=50010
    )
    
    # Count passing conditions
    passing = sum([
        conditions['price_breakout'],
        conditions['volume_surge'],
        conditions['body_ratio'],
        conditions['l2_imbalance'],
        conditions.get('vwap_gap', False)
    ])
    
    # In current implementation, all must pass (AND logic)
    # This test documents current behavior
    assert passing < 5, "Not all conditions should pass in weak scenario"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
