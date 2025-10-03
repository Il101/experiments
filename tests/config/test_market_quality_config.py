"""
Unit tests for MarketQualityConfig configuration model.

Tests:
- Flat market detection
- Consolidation detection
- Volatility quality filters
- Trend quality filters
- Market noise filter
"""

import pytest
from pydantic import ValidationError
from breakout_bot.config.settings import MarketQualityConfig


class TestMarketQualityConfigValidation:
    """Test MarketQualityConfig validation rules."""
    
    def test_valid_market_quality(self):
        """Test creating valid market quality config."""
        mq = MarketQualityConfig(
            flat_market_filter_enabled=True,
            flat_market_atr_threshold=0.3,
            flat_market_lookback_bars=20,
            consolidation_filter_enabled=True,
            consolidation_range_threshold_pct=0.5,
            consolidation_min_bars=10,
            require_stable_volatility=True,
            volatility_spike_threshold=2.0,
            volatility_lookback_bars=20,
            require_clear_trend=False,
            trend_slope_min_pct=0.3,
            trend_lookback_bars=20,
            noise_filter_enabled=True,
            noise_threshold=0.7
        )
        
        assert mq.flat_market_filter_enabled is True
        assert mq.flat_market_atr_threshold == 0.3
        assert mq.flat_market_lookback_bars == 20
        assert mq.consolidation_filter_enabled is True
        assert mq.require_stable_volatility is True
        assert mq.noise_filter_enabled is True
    
    def test_flat_market_atr_threshold_positive(self):
        """Test flat_market_atr_threshold must be positive."""
        with pytest.raises(ValidationError) as exc_info:
            MarketQualityConfig(
                flat_market_atr_threshold=0.0
            )
        
        assert "Threshold must be positive" in str(exc_info.value)
    
    def test_consolidation_range_threshold_positive(self):
        """Test consolidation_range_threshold_pct must be positive."""
        with pytest.raises(ValidationError) as exc_info:
            MarketQualityConfig(
                consolidation_range_threshold_pct=0.0
            )
        
        assert "Threshold must be positive" in str(exc_info.value)
    
    def test_bars_positive(self):
        """Test bar counts must be positive."""
        with pytest.raises(ValidationError) as exc_info:
            MarketQualityConfig(
                flat_market_lookback_bars=0
            )
        
        assert "Bar count must be at least 1" in str(exc_info.value)
    
    def test_noise_threshold_range(self):
        """Test noise_threshold must be between 0 and 1."""
        with pytest.raises(ValidationError) as exc_info:
            MarketQualityConfig(
                noise_threshold=1.5
            )
        
        assert "noise_threshold must be between 0 and 1" in str(exc_info.value)


class TestMarketQualityConfigDefaults:
    """Test default values."""
    
    def test_default_values(self):
        """Test all default values are set correctly."""
        mq = MarketQualityConfig()
        
        assert mq.flat_market_filter_enabled is True
        assert mq.flat_market_atr_threshold == 0.3
        assert mq.flat_market_lookback_bars == 20
        assert mq.consolidation_filter_enabled is True
        assert mq.consolidation_range_threshold_pct == 0.5
        assert mq.consolidation_min_bars == 10
        assert mq.require_stable_volatility is True
        assert mq.volatility_spike_threshold == 2.0
        assert mq.require_clear_trend is False
        assert mq.noise_filter_enabled is True
        assert mq.noise_threshold == 0.7


class TestMarketQualityConfigEdgeCases:
    """Test edge cases and boundary conditions."""
    
    def test_disabled_all_filters(self):
        """Test disabling all filters."""
        mq = MarketQualityConfig(
            flat_market_filter_enabled=False,
            consolidation_filter_enabled=False,
            require_stable_volatility=False,
            require_clear_trend=False,
            noise_filter_enabled=False
        )
        
        assert mq.flat_market_filter_enabled is False
        assert mq.consolidation_filter_enabled is False
        assert mq.require_stable_volatility is False
        assert mq.require_clear_trend is False
        assert mq.noise_filter_enabled is False
    
    def test_zero_noise_threshold(self):
        """Test zero noise threshold."""
        mq = MarketQualityConfig(noise_threshold=0.0)
        
        assert mq.noise_threshold == 0.0
    
    def test_max_noise_threshold(self):
        """Test maximum noise threshold."""
        mq = MarketQualityConfig(noise_threshold=1.0)
        
        assert mq.noise_threshold == 1.0


class TestMarketQualityConfigUseCases:
    """Test real-world use cases."""
    
    def test_scalping_market_quality(self):
        """Test market quality for scalping."""
        mq = MarketQualityConfig(
            flat_market_filter_enabled=True,
            flat_market_atr_threshold=0.2,
            consolidation_filter_enabled=True,
            consolidation_range_threshold_pct=0.3,
            require_stable_volatility=True,
            volatility_spike_threshold=1.5,
            noise_filter_enabled=True,
            noise_threshold=0.8
        )
        
        assert mq.flat_market_atr_threshold == 0.2
        assert mq.consolidation_range_threshold_pct == 0.3
        assert mq.noise_threshold == 0.8
    
    def test_swing_market_quality(self):
        """Test market quality for swing trading."""
        mq = MarketQualityConfig(
            flat_market_filter_enabled=True,
            flat_market_atr_threshold=0.5,
            consolidation_filter_enabled=True,
            consolidation_range_threshold_pct=1.0,
            require_stable_volatility=False,
            require_clear_trend=True,
            trend_slope_min_pct=0.5,
            noise_filter_enabled=True
        )
        
        assert mq.flat_market_atr_threshold == 0.5
        assert mq.require_clear_trend is True
        assert mq.trend_slope_min_pct == 0.5
    
    def test_conservative_market_quality(self):
        """Test market quality for conservative strategy."""
        mq = MarketQualityConfig(
            flat_market_filter_enabled=True,
            consolidation_filter_enabled=True,
            require_stable_volatility=True,
            require_clear_trend=False,
            noise_filter_enabled=True,
            noise_threshold=0.7
        )
        
        assert mq.flat_market_filter_enabled is True
        assert mq.require_stable_volatility is True
        assert mq.noise_filter_enabled is True
