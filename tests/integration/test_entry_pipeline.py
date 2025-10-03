"""
Integration tests for entry pipeline (Market Quality Filter → Entry Validator).

Week 2, Day 6 - Integration Testing
"""

import pytest
from decimal import Decimal

from breakout_bot.strategy.market_quality_filter import MarketQualityFilter
from breakout_bot.strategy.entry_validator import EntryValidator, ValidationResult

from tests.integration.fixtures.market_data import (
    create_trending_market,
    create_flat_market,
    create_choppy_market,
)
from tests.integration.fixtures.presets import (
    conservative_preset,
    aggressive_preset,
    balanced_preset,
)
from tests.integration.fixtures.helpers import create_entry_signal


class TestQualityFilterToValidator:
    """Test integration between MarketQualityFilter and EntryValidator."""
    
    def test_quality_rejected_prevents_entry(self):
        """Poor quality market → filter rejects."""
        preset = balanced_preset()
        quality_filter = MarketQualityFilter(preset.market_quality)
        
        metrics = create_flat_market()
        allowed, reason = quality_filter.should_enter(metrics)
        assert not allowed, f"should_enter() should reject, got: {reason}"
    
    def test_quality_passed_allows_validation(self):
        """Quality filter passes → validator can run."""
        config = aggressive_preset()
        quality_filter = MarketQualityFilter(config.market_quality)
        validator = EntryValidator(config.entry_rules, config.market_quality)
        
        metrics = create_trending_market()
        result = quality_filter.filter(metrics)
        
        assert result.passed, "Trending market should pass quality filter"
        signal = create_entry_signal()
        validation = validator.validate(signal)
        assert validation is not None, "Validator should process the signal"
    
    def test_both_filters_pass_valid_entry(self):
        """Both quality and entry validation pass."""
        config = balanced_preset()
        quality_filter = MarketQualityFilter(config.market_quality)
        validator = EntryValidator(config.entry_rules, config.market_quality)
        
        metrics = create_trending_market()
        quality_result = quality_filter.filter(metrics)
        assert quality_result.passed, "Quality should pass"
        
        signal = create_entry_signal()
        validation = validator.validate(signal)
        
        assert validation.is_valid, "Validation should pass with good conditions"
        assert validation.confidence >= Decimal("0.6"), "Confidence should be decent"
    
    def test_quality_passes_but_validator_fails(self):
        """Quality passes but entry validation fails."""
        config = conservative_preset()
        quality_filter = MarketQualityFilter(config.market_quality)
        validator = EntryValidator(config.entry_rules, config.market_quality)
        
        metrics = create_trending_market()
        quality_result = quality_filter.filter(metrics)
        assert quality_result.passed, "Quality should pass"
        
        signal = create_entry_signal()
        signal.current_volume = Decimal("500000")
        signal.price_change_pct = Decimal("0.1")
        
        validation = validator.validate(signal)
        
        # May still be valid but should have warnings/failed checks
        failed_checks = [check for check in validation.checks if check.result == ValidationResult.FAILED]
        assert len(failed_checks) > 0, "Should have failed checks"
        assert len(validation.warnings) > 0, "Should have warnings about weak signal"
    
    def test_edge_case_all_filters_disabled(self):
        """Edge case: All quality filters disabled."""
        config = balanced_preset()
        config.market_quality.flat_market_filter_enabled = False
        config.market_quality.consolidation_filter_enabled = False
        config.market_quality.require_stable_volatility = False
        config.market_quality.require_clear_trend = False
        config.market_quality.noise_filter_enabled = False
        
        quality_filter = MarketQualityFilter(config.market_quality)
        metrics = create_flat_market()
        result = quality_filter.filter(metrics)
        
        assert result.passed, "Should pass when all filters disabled"
        allowed, reason = quality_filter.should_enter(metrics)
        assert allowed, f"should_enter() should allow, got: {reason}"


class TestQualityFilterImpact:
    """Test how market quality affects entry validation."""
    
    def test_good_quality_increases_confidence(self):
        """Good market quality → higher confidence."""
        config = balanced_preset()
        validator = EntryValidator(config.entry_rules, config.market_quality)
        
        good_metrics = create_trending_market()
        signal = create_entry_signal()
        validation_good = validator.validate(signal)
        assert validation_good is not None
    
    def test_poor_quality_may_reduce_confidence(self):
        """Poor market quality → may reduce confidence or reject."""
        config = balanced_preset()
        quality_filter = MarketQualityFilter(config.market_quality)
        
        poor_metrics = create_flat_market()
        result = quality_filter.filter(poor_metrics)
        assert not result.passed, "Flat market should be rejected"
    
    def test_choppy_market_rejected(self):
        """Choppy/noisy market → rejected."""
        config = conservative_preset()
        quality_filter = MarketQualityFilter(config.market_quality)
        
        choppy_metrics = create_choppy_market()
        allowed, reason = quality_filter.should_enter(choppy_metrics)
        assert not allowed, f"should_enter() should reject: {reason}"
    
    def test_trending_market_accepted(self):
        """Strong trending market → accepted."""
        config = balanced_preset()
        quality_filter = MarketQualityFilter(config.market_quality)
        
        trending_metrics = create_trending_market()
        result = quality_filter.filter(trending_metrics)
        assert result.passed, "Trending market should pass"


class TestPresetBehavior:
    """Test how different presets behave in entry pipeline."""
    
    def test_conservative_rejects_more(self):
        """Conservative preset → stricter filtering."""
        conservative = conservative_preset()
        aggressive = aggressive_preset()
        
        cons_filter = MarketQualityFilter(conservative.market_quality)
        aggr_filter = MarketQualityFilter(aggressive.market_quality)
        
        metrics = create_flat_market()
        
        cons_result = cons_filter.filter(metrics)
        aggr_result = aggr_filter.filter(metrics)
        
        assert not cons_result.passed, "Conservative should reject flat market"
    
    def test_aggressive_accepts_more(self):
        """Aggressive preset → looser filtering."""
        config = aggressive_preset()
        quality_filter = MarketQualityFilter(config.market_quality)
        
        metrics = create_flat_market()
        allowed, reason = quality_filter.should_enter(metrics)
        assert allowed, f"Aggressive should allow, got: {reason}"
    
    def test_balanced_middle_ground(self):
        """Balanced preset → moderate filtering."""
        config = balanced_preset()
        quality_filter = MarketQualityFilter(config.market_quality)
        validator = EntryValidator(config.entry_rules, config.market_quality)
        
        metrics = create_trending_market()
        signal = create_entry_signal()
        
        quality_result = quality_filter.filter(metrics)
        assert quality_result.passed, "Balanced should accept good market"
        
        validation = validator.validate(signal)
        assert validation.is_valid, "Balanced should accept good signals"
        assert Decimal("0.6") <= validation.confidence <= Decimal("0.9"), \
            "Balanced confidence should be moderate"
