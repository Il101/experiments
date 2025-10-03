"""
Tests for MarketQualityFilter component.
"""

import pytest
from decimal import Decimal

from breakout_bot.strategy.market_quality_filter import (
    MarketQualityFilter,
    MarketMetrics,
    MarketCondition,
    FilterResult,
)
from breakout_bot.config.settings import MarketQualityConfig


@pytest.fixture
def default_config():
    """Default market quality configuration."""
    return MarketQualityConfig(
        flat_market_filter_enabled=True,
        flat_market_atr_threshold=0.3,
        consolidation_filter_enabled=True,
        consolidation_range_threshold_pct=0.5,
        consolidation_min_bars=10,
        require_stable_volatility=True,
        require_clear_trend=False,
        trend_slope_min_pct=0.3,
        noise_filter_enabled=True,
        noise_threshold=0.7,
    )


@pytest.fixture
def filter_obj(default_config):
    """Create filter instance."""
    return MarketQualityFilter(default_config)


@pytest.fixture
def good_metrics():
    """Good market metrics."""
    return MarketMetrics(
        atr=Decimal("1.5"),
        atr_pct=Decimal("0.5"),  # > 0.3 threshold
        volatility_spike=False,
        price_range_pct=Decimal("1.2"),  # > 0.5 threshold
        consolidation_bars=5,
        trend_slope_pct=Decimal("0.4"),
        trend_strength=Decimal("0.8"),
        noise_level=Decimal("0.3"),  # < 0.7 threshold
        current_price=Decimal("100"),
    )


class TestFlatMarketDetection:
    """Test flat market detection."""
    
    def test_normal_volatility(self, filter_obj, good_metrics):
        """Test with normal volatility."""
        result = filter_obj.filter(good_metrics)
        
        assert result.passed
        assert result.condition != MarketCondition.FLAT
        assert result.score > Decimal("0.5")
    
    def test_flat_market_rejected(self, filter_obj, good_metrics):
        """Test flat market rejection."""
        good_metrics.atr_pct = Decimal("0.2")  # < 0.3 threshold
        result = filter_obj.filter(good_metrics)
        
        assert not result.passed
        assert result.condition == MarketCondition.FLAT
        assert "flat" in result.reason.lower()
    
    def test_flat_market_disabled(self, good_metrics):
        """Test with flat market filter disabled."""
        config = MarketQualityConfig(
            flat_market_filter_enabled=False,
            flat_market_atr_threshold=0.3,
        )
        filter_obj = MarketQualityFilter(config)
        
        good_metrics.atr_pct = Decimal("0.1")  # Very low
        result = filter_obj.filter(good_metrics)
        
        assert result.passed  # Should pass since filter disabled


class TestConsolidationDetection:
    """Test consolidation detection."""
    
    def test_trending_market(self, filter_obj, good_metrics):
        """Test with trending market (wide range)."""
        good_metrics.price_range_pct = Decimal("1.5")
        good_metrics.consolidation_bars = 15
        result = filter_obj.filter(good_metrics)
        
        assert result.passed
        assert result.condition != MarketCondition.CONSOLIDATING
    
    def test_consolidation_rejected(self, filter_obj, good_metrics):
        """Test consolidation rejection."""
        good_metrics.price_range_pct = Decimal("0.3")  # < 0.5 threshold
        good_metrics.consolidation_bars = 15  # >= 10 minimum
        result = filter_obj.filter(good_metrics)
        
        assert not result.passed
        assert result.condition == MarketCondition.CONSOLIDATING
        assert "consolidating" in result.reason.lower()
    
    def test_consolidation_insufficient_bars(self, filter_obj, good_metrics):
        """Test consolidation with insufficient bars."""
        good_metrics.price_range_pct = Decimal("0.3")  # Narrow range
        good_metrics.consolidation_bars = 5  # < 10 minimum
        result = filter_obj.filter(good_metrics)
        
        # Should pass - not enough bars to confirm consolidation
        assert result.passed


class TestVolatilitySpike:
    """Test volatility spike detection."""
    
    def test_stable_volatility(self, filter_obj, good_metrics):
        """Test with stable volatility."""
        good_metrics.volatility_spike = False
        result = filter_obj.filter(good_metrics)
        
        assert result.passed
        assert result.condition != MarketCondition.VOLATILE
    
    def test_volatility_spike_rejected(self, filter_obj, good_metrics):
        """Test volatility spike rejection."""
        good_metrics.volatility_spike = True
        result = filter_obj.filter(good_metrics)
        
        assert not result.passed
        assert result.condition == MarketCondition.VOLATILE
        assert "volatility spike" in result.reason.lower()
    
    def test_volatility_spike_disabled(self, good_metrics):
        """Test with volatility spike check disabled."""
        config = MarketQualityConfig(
            require_stable_volatility=False,
        )
        filter_obj = MarketQualityFilter(config)
        
        good_metrics.volatility_spike = True
        result = filter_obj.filter(good_metrics)
        
        assert result.passed  # Should pass since check disabled


class TestTrendQuality:
    """Test trend quality assessment."""
    
    def test_strong_trend_required(self, good_metrics):
        """Test with strong trend requirement."""
        config = MarketQualityConfig(
            require_clear_trend=True,
            trend_slope_min_pct=0.3,
        )
        filter_obj = MarketQualityFilter(config)
        
        good_metrics.trend_slope_pct = Decimal("0.5")  # > 0.3
        result = filter_obj.filter(good_metrics)
        
        assert result.passed
        assert result.condition == MarketCondition.TRENDING
    
    def test_weak_trend_rejected(self, good_metrics):
        """Test weak trend rejection."""
        config = MarketQualityConfig(
            require_clear_trend=True,
            trend_slope_min_pct=0.3,
        )
        filter_obj = MarketQualityFilter(config)
        
        good_metrics.trend_slope_pct = Decimal("0.1")  # < 0.3
        result = filter_obj.filter(good_metrics)
        
        assert not result.passed
        assert "trend" in result.reason.lower()
    
    def test_trend_not_required(self, filter_obj, good_metrics):
        """Test when trend is not required."""
        good_metrics.trend_slope_pct = Decimal("0.05")  # Very weak
        result = filter_obj.filter(good_metrics)
        
        # Should pass - trend not required by default config
        assert result.passed


class TestNoiseFiltering:
    """Test market noise filtering."""
    
    def test_low_noise(self, filter_obj, good_metrics):
        """Test with low noise."""
        good_metrics.noise_level = Decimal("0.2")  # < 0.7 threshold
        result = filter_obj.filter(good_metrics)
        
        assert result.passed
        assert result.condition != MarketCondition.NOISY
    
    def test_high_noise_rejected(self, filter_obj, good_metrics):
        """Test high noise rejection."""
        good_metrics.noise_level = Decimal("0.8")  # > 0.7 threshold
        result = filter_obj.filter(good_metrics)
        
        assert not result.passed
        assert result.condition == MarketCondition.NOISY
        assert "noise" in result.reason.lower()
    
    def test_noise_filter_disabled(self, good_metrics):
        """Test with noise filter disabled."""
        config = MarketQualityConfig(
            noise_filter_enabled=False,
            noise_threshold=0.7,
        )
        filter_obj = MarketQualityFilter(config)
        
        good_metrics.noise_level = Decimal("0.9")  # Very high
        result = filter_obj.filter(good_metrics)
        
        assert result.passed  # Should pass since filter disabled


class TestQualityScoring:
    """Test quality score calculation."""
    
    def test_excellent_quality(self, filter_obj, good_metrics):
        """Test excellent market quality."""
        # Perfect conditions
        good_metrics.atr_pct = Decimal("0.8")  # High volatility
        good_metrics.price_range_pct = Decimal("2.0")  # Wide range
        good_metrics.volatility_spike = False
        good_metrics.noise_level = Decimal("0.1")  # Low noise
        
        result = filter_obj.filter(good_metrics)
        
        assert result.passed
        assert result.score > Decimal("0.8")
    
    def test_marginal_quality(self, filter_obj, good_metrics):
        """Test marginal market quality."""
        # Borderline conditions
        good_metrics.atr_pct = Decimal("0.35")  # Just above threshold
        good_metrics.price_range_pct = Decimal("0.6")  # Just above threshold
        good_metrics.noise_level = Decimal("0.6")  # Near threshold
        
        result = filter_obj.filter(good_metrics)
        
        assert result.passed
        assert Decimal("0.4") < result.score < Decimal("0.8")
        assert len(result.warnings) > 0  # Should have warnings
    
    def test_poor_quality(self, filter_obj, good_metrics):
        """Test poor market quality."""
        # Multiple issues
        good_metrics.atr_pct = Decimal("0.15")  # Flat
        good_metrics.price_range_pct = Decimal("0.3")  # Consolidating
        good_metrics.consolidation_bars = 20
        good_metrics.noise_level = Decimal("0.8")  # Noisy
        
        result = filter_obj.filter(good_metrics)
        
        assert not result.passed
        assert result.score < Decimal("0.6")  # Poor quality score


class TestConditionClassification:
    """Test market condition classification."""
    
    def test_trending_classification(self, filter_obj, good_metrics):
        """Test trending market classification."""
        good_metrics.trend_slope_pct = Decimal("0.5")  # Strong trend
        result = filter_obj.filter(good_metrics)
        
        assert result.condition == MarketCondition.TRENDING
    
    def test_flat_classification(self, filter_obj, good_metrics):
        """Test flat market classification."""
        good_metrics.atr_pct = Decimal("0.1")
        result = filter_obj.filter(good_metrics)
        
        assert result.condition == MarketCondition.FLAT
    
    def test_consolidating_classification(self, filter_obj, good_metrics):
        """Test consolidating market classification."""
        good_metrics.price_range_pct = Decimal("0.3")
        good_metrics.consolidation_bars = 15
        result = filter_obj.filter(good_metrics)
        
        assert result.condition == MarketCondition.CONSOLIDATING
    
    def test_volatile_classification(self, filter_obj, good_metrics):
        """Test volatile market classification."""
        good_metrics.volatility_spike = True
        result = filter_obj.filter(good_metrics)
        
        assert result.condition == MarketCondition.VOLATILE
    
    def test_noisy_classification(self, filter_obj, good_metrics):
        """Test noisy market classification."""
        good_metrics.noise_level = Decimal("0.85")
        result = filter_obj.filter(good_metrics)
        
        assert result.condition == MarketCondition.NOISY


class TestHelperMethods:
    """Test helper methods."""
    
    def test_should_enter(self, filter_obj, good_metrics):
        """Test should_enter convenience method."""
        should_enter, reason = filter_obj.should_enter(good_metrics)
        
        assert should_enter
        assert "acceptable" in reason.lower()
    
    def test_should_not_enter(self, filter_obj, good_metrics):
        """Test should_enter with poor conditions."""
        good_metrics.atr_pct = Decimal("0.1")  # Flat
        should_enter, reason = filter_obj.should_enter(good_metrics)
        
        assert not should_enter
        assert "flat" in reason.lower()
    
    def test_get_acceptable_conditions(self, filter_obj):
        """Test get_acceptable_conditions."""
        acceptable = filter_obj.get_acceptable_conditions()
        
        # Should include ACCEPTABLE and TRENDING
        assert MarketCondition.ACCEPTABLE in acceptable
        assert MarketCondition.TRENDING in acceptable
        
        # Should not include filtered conditions
        assert MarketCondition.FLAT not in acceptable
        assert MarketCondition.CONSOLIDATING not in acceptable
    
    def test_get_acceptable_conditions_all_disabled(self):
        """Test get_acceptable_conditions with all filters disabled."""
        config = MarketQualityConfig(
            flat_market_filter_enabled=False,
            consolidation_filter_enabled=False,
            require_stable_volatility=False,
            noise_filter_enabled=False,
        )
        filter_obj = MarketQualityFilter(config)
        
        acceptable = filter_obj.get_acceptable_conditions()
        
        # Should include all conditions
        assert len(acceptable) >= 5


class TestEdgeCases:
    """Test edge cases."""
    
    def test_all_filters_disabled(self, good_metrics):
        """Test with all filters disabled."""
        config = MarketQualityConfig(
            flat_market_filter_enabled=False,
            consolidation_filter_enabled=False,
            require_stable_volatility=False,
            require_clear_trend=False,
            noise_filter_enabled=False,
        )
        filter_obj = MarketQualityFilter(config)
        
        # Even with terrible conditions, should pass
        good_metrics.atr_pct = Decimal("0.01")
        good_metrics.noise_level = Decimal("0.99")
        good_metrics.volatility_spike = True
        
        result = filter_obj.filter(good_metrics)
        
        assert result.passed
        assert result.score == Decimal("1.0")  # No filters = perfect score
    
    def test_multiple_issues(self, filter_obj, good_metrics):
        """Test with multiple issues."""
        good_metrics.atr_pct = Decimal("0.1")  # Flat
        good_metrics.price_range_pct = Decimal("0.2")  # Consolidating
        good_metrics.consolidation_bars = 20
        good_metrics.volatility_spike = True  # Volatile
        good_metrics.noise_level = Decimal("0.9")  # Noisy
        
        result = filter_obj.filter(good_metrics)
        
        assert not result.passed
        assert len(result.reason.split(',')) >= 3  # Multiple issues mentioned


class TestFilterResult:
    """Test FilterResult functionality."""
    
    def test_is_acceptable(self, filter_obj, good_metrics):
        """Test is_acceptable method."""
        result = filter_obj.filter(good_metrics)
        
        assert result.is_acceptable() == result.passed
    
    def test_result_with_warnings(self, filter_obj, good_metrics):
        """Test result with warnings."""
        # Marginal quality
        good_metrics.atr_pct = Decimal("0.32")
        good_metrics.price_range_pct = Decimal("0.55")
        
        result = filter_obj.filter(good_metrics)
        
        if result.score < Decimal("0.7"):
            assert len(result.warnings) > 0
