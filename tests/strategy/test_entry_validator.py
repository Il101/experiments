"""
Tests for EntryValidator component.
"""

import pytest
from decimal import Decimal

from breakout_bot.strategy.entry_validator import (
    EntryValidator,
    EntrySignal,
    ValidationResult,
    ValidationPriority,
    ValidationReport,
)
from breakout_bot.config.settings import EntryRulesConfig, MarketQualityConfig


@pytest.fixture
def default_entry_config():
    """Default entry rules configuration."""
    return EntryRulesConfig(
        require_volume_confirmation=True,
        volume_confirmation_multiplier=1.5,
        require_momentum=True,
        momentum_min_slope_pct=0.5,
        require_density_confirmation=True,
        max_distance_from_level_bps=10.0,
        false_start_lookback_bars=3,
    )


@pytest.fixture
def default_market_config():
    """Default market quality configuration."""
    return MarketQualityConfig(
        flat_market_filter_enabled=True,
        consolidation_filter_enabled=True,
        noise_filter_enabled=True,
        noise_threshold=0.3,
    )


@pytest.fixture
def validator(default_entry_config, default_market_config):
    """Create validator instance."""
    return EntryValidator(default_entry_config, default_market_config)


@pytest.fixture
def good_long_signal():
    """Good long entry signal."""
    return EntrySignal(
        breakout_price=Decimal("100"),
        current_price=Decimal("100.5"),
        entry_price=Decimal("100.3"),
        stop_loss=Decimal("99"),
        breakout_volume=Decimal("1000"),
        avg_volume=Decimal("500"),  # 2x ratio
        current_volume=Decimal("800"),
        price_change_pct=Decimal("0.5"),  # 0.5% momentum
        bars_since_breakout=2,
        density_zones=[],
        sr_levels=[],
        is_flat=False,
        is_consolidating=False,
        noise_level=Decimal("0.15"),
        is_long=True,
    )


@pytest.fixture
def good_short_signal():
    """Good short entry signal."""
    return EntrySignal(
        breakout_price=Decimal("100"),
        current_price=Decimal("99.5"),
        entry_price=Decimal("99.7"),
        stop_loss=Decimal("101"),
        breakout_volume=Decimal("1000"),
        avg_volume=Decimal("500"),
        current_volume=Decimal("800"),
        price_change_pct=Decimal("-0.5"),
        bars_since_breakout=2,
        density_zones=[],
        sr_levels=[],
        is_flat=False,
        is_consolidating=False,
        noise_level=Decimal("0.15"),
        is_long=False,
    )


class TestVolumeConfirmation:
    """Test volume confirmation validation."""
    
    def test_sufficient_volume(self, validator, good_long_signal):
        """Test entry with sufficient volume."""
        report = validator.validate(good_long_signal)
        
        volume_check = report.get_check("volume_confirmation")
        assert volume_check is not None
        assert volume_check.result == ValidationResult.PASSED
        assert volume_check.score > Decimal("0.7")
    
    def test_insufficient_volume(self, validator, good_long_signal):
        """Test entry with insufficient volume."""
        good_long_signal.breakout_volume = Decimal("600")  # 1.2x, need 1.5x
        report = validator.validate(good_long_signal)
        
        volume_check = report.get_check("volume_confirmation")
        assert volume_check is not None
        assert volume_check.result == ValidationResult.FAILED
        assert report.is_valid  # Should still be valid (HIGH priority, not CRITICAL)
        assert len(report.warnings) > 0  # But should have warning
    
    def test_volume_check_disabled(self, good_long_signal):
        """Test volume check when disabled."""
        config = EntryRulesConfig(
            require_volume_confirmation=False,
            volume_confirmation_multiplier=1.5,
            require_momentum=True,
            momentum_min_slope_pct=0.5,
        )
        validator = EntryValidator(config)
        
        report = validator.validate(good_long_signal)
        volume_check = report.get_check("volume_confirmation")
        
        assert volume_check.result == ValidationResult.SKIPPED


class TestDensityAvoidance:
    """Test density zone avoidance."""
    
    def test_entry_clear_of_density(self, validator, good_long_signal):
        """Test entry clear of density zones."""
        good_long_signal.density_zones = [
            (Decimal("95"), Decimal("97")),
            (Decimal("105"), Decimal("107")),
        ]
        
        report = validator.validate(good_long_signal)
        density_check = report.get_check("density_avoidance")
        
        assert density_check.result == ValidationResult.PASSED
        assert density_check.score > Decimal("0.6")
    
    def test_entry_in_density_zone(self, validator, good_long_signal):
        """Test entry in density zone."""
        good_long_signal.density_zones = [
            (Decimal("100"), Decimal("101")),  # Entry at 100.3
        ]
        
        report = validator.validate(good_long_signal)
        density_check = report.get_check("density_avoidance")
        
        assert density_check.result == ValidationResult.FAILED
        assert "density zone" in density_check.reason.lower()
    
    def test_no_density_zones(self, validator, good_long_signal):
        """Test when no density zones exist."""
        good_long_signal.density_zones = []
        
        report = validator.validate(good_long_signal)
        density_check = report.get_check("density_avoidance")
        
        assert density_check.result == ValidationResult.PASSED
        assert density_check.score == Decimal("1.0")


class TestMomentumConfirmation:
    """Test momentum confirmation."""
    
    def test_strong_momentum(self, validator, good_long_signal):
        """Test strong momentum."""
        good_long_signal.price_change_pct = Decimal("1.0")  # 1% momentum
        
        report = validator.validate(good_long_signal)
        momentum_check = report.get_check("momentum_confirmation")
        
        assert momentum_check.result == ValidationResult.PASSED
        assert momentum_check.score > Decimal("0.7")
    
    def test_weak_momentum(self, validator, good_long_signal):
        """Test weak momentum."""
        good_long_signal.price_change_pct = Decimal("0.2")  # 0.2%, need 0.5%
        
        report = validator.validate(good_long_signal)
        momentum_check = report.get_check("momentum_confirmation")
        
        assert momentum_check.result == ValidationResult.FAILED
        assert "weak momentum" in momentum_check.reason.lower()
    
    def test_short_momentum(self, validator, good_short_signal):
        """Test momentum for short position."""
        good_short_signal.price_change_pct = Decimal("-0.8")  # -0.8% (strong down)
        
        report = validator.validate(good_short_signal)
        momentum_check = report.get_check("momentum_confirmation")
        
        assert momentum_check.result == ValidationResult.PASSED


class TestMarketQuality:
    """Test market quality validation."""
    
    def test_good_market_quality(self, validator, good_long_signal):
        """Test good market quality."""
        report = validator.validate(good_long_signal)
        quality_check = report.get_check("market_quality")
        
        assert quality_check.result == ValidationResult.PASSED
    
    def test_flat_market_rejected(self, validator, good_long_signal):
        """Test flat market rejected."""
        good_long_signal.is_flat = True
        
        report = validator.validate(good_long_signal)
        quality_check = report.get_check("market_quality")
        
        assert quality_check.result == ValidationResult.FAILED
        assert "flat" in quality_check.reason.lower()
    
    def test_consolidating_market_rejected(self, validator, good_long_signal):
        """Test consolidating market rejected."""
        good_long_signal.is_consolidating = True
        
        report = validator.validate(good_long_signal)
        quality_check = report.get_check("market_quality")
        
        assert quality_check.result == ValidationResult.FAILED
        assert "consolidating" in quality_check.reason.lower()
    
    def test_high_noise_rejected(self, validator, good_long_signal):
        """Test high noise level rejected."""
        good_long_signal.noise_level = Decimal("0.5")  # > 0.3 max
        
        report = validator.validate(good_long_signal)
        quality_check = report.get_check("market_quality")
        
        assert quality_check.result == ValidationResult.FAILED
        assert "noise" in quality_check.reason.lower()
    
    def test_market_quality_disabled(self, default_entry_config, good_long_signal):
        """Test market quality check when disabled."""
        validator = EntryValidator(default_entry_config, market_config=None)
        
        report = validator.validate(good_long_signal)
        quality_check = report.get_check("market_quality")
        
        assert quality_check.result == ValidationResult.SKIPPED


class TestBreakoutQuality:
    """Test breakout quality validation."""
    
    def test_clean_breakout(self, validator, good_long_signal):
        """Test clean breakout."""
        report = validator.validate(good_long_signal)
        breakout_check = report.get_check("breakout_quality")
        
        assert breakout_check.result == ValidationResult.PASSED
        assert breakout_check.priority == ValidationPriority.CRITICAL
    
    def test_insufficient_distance(self, validator, good_long_signal):
        """Test insufficient breakout distance."""
        good_long_signal.current_price = Decimal("100.05")  # Too close
        
        report = validator.validate(good_long_signal)
        breakout_check = report.get_check("breakout_quality")
        
        assert breakout_check.result == ValidationResult.FAILED
        assert not report.is_valid  # Critical failure
        assert "breakout_quality" in report.failed_critical
    
    def test_too_many_bars(self, validator, good_long_signal):
        """Test too many bars since breakout."""
        good_long_signal.bars_since_breakout = 5  # > 3 max
        
        report = validator.validate(good_long_signal)
        breakout_check = report.get_check("breakout_quality")
        
        assert breakout_check.result == ValidationResult.FAILED
        assert "too late" in breakout_check.reason.lower()


class TestValidationReport:
    """Test validation report functionality."""
    
    def test_all_passed(self, validator, good_long_signal):
        """Test when all checks pass."""
        report = validator.validate(good_long_signal)
        
        assert report.is_valid
        assert len(report.failed_critical) == 0
        assert report.confidence > Decimal("0.7")
        assert len(report.get_passed_checks()) > 0
        assert len(report.get_failed_checks()) == 0
    
    def test_critical_failure(self, validator, good_long_signal):
        """Test critical failure makes signal invalid."""
        good_long_signal.bars_since_breakout = 10  # Critical failure
        
        report = validator.validate(good_long_signal)
        
        assert not report.is_valid
        assert len(report.failed_critical) > 0
        assert "breakout_quality" in report.failed_critical
    
    def test_high_priority_failure_still_valid(self, validator, good_long_signal):
        """Test high priority failure doesn't invalidate signal."""
        good_long_signal.breakout_volume = Decimal("600")  # Volume too low (HIGH priority)
        
        report = validator.validate(good_long_signal)
        
        # Should still be valid (no critical failures)
        assert report.is_valid
        assert len(report.warnings) > 0
    
    def test_confidence_calculation(self, validator, good_long_signal):
        """Test confidence calculation."""
        report = validator.validate(good_long_signal)
        
        # All checks passed, confidence should be high
        assert report.confidence > Decimal("0.6")
        assert report.confidence <= Decimal("1.0")
    
    def test_get_check_by_name(self, validator, good_long_signal):
        """Test getting specific check by name."""
        report = validator.validate(good_long_signal)
        
        volume_check = report.get_check("volume_confirmation")
        assert volume_check is not None
        assert volume_check.rule_name == "volume_confirmation"
        
        nonexistent = report.get_check("nonexistent_check")
        assert nonexistent is None


class TestEdgeCases:
    """Test edge cases."""
    
    def test_zero_average_volume(self, validator, good_long_signal):
        """Test zero average volume."""
        good_long_signal.avg_volume = Decimal("0")
        
        report = validator.validate(good_long_signal)
        volume_check = report.get_check("volume_confirmation")
        
        # Should handle gracefully
        assert volume_check is not None
    
    def test_zero_risk(self, validator, good_long_signal):
        """Test zero risk position."""
        good_long_signal.entry_price = good_long_signal.stop_loss
        
        report = validator.validate(good_long_signal)
        
        # Should handle gracefully
        assert report is not None
    
    def test_all_checks_disabled(self, good_long_signal):
        """Test when all checks are disabled."""
        config = EntryRulesConfig(
            require_volume_confirmation=False,
            volume_confirmation_multiplier=1.5,
            require_momentum=False,
            momentum_min_slope_pct=0.5,
            require_density_confirmation=False,
        )
        validator = EntryValidator(config, market_config=None)
        
        report = validator.validate(good_long_signal)
        
        # Only breakout_quality is always enabled
        enabled_checks = [c for c in report.checks if c.result != ValidationResult.SKIPPED]
        assert len(enabled_checks) == 1
        assert enabled_checks[0].rule_name == "breakout_quality"


class TestMultipleFailures:
    """Test scenarios with multiple failures."""
    
    def test_multiple_non_critical_failures(self, validator, good_long_signal):
        """Test multiple non-critical failures."""
        good_long_signal.breakout_volume = Decimal("600")  # Volume too low
        good_long_signal.density_zones = [(Decimal("100"), Decimal("101"))]  # In density
        good_long_signal.price_change_pct = Decimal("0.2")  # Weak momentum
        
        report = validator.validate(good_long_signal)
        
        # Should still be valid (no critical failures)
        assert report.is_valid
        assert len(report.get_failed_checks()) >= 3
        assert len(report.warnings) > 0
        assert report.confidence < Decimal("0.5")  # Low confidence
    
    def test_critical_and_non_critical_failures(self, validator, good_long_signal):
        """Test mix of critical and non-critical failures."""
        good_long_signal.bars_since_breakout = 10  # Critical
        good_long_signal.breakout_volume = Decimal("600")  # Non-critical
        
        report = validator.validate(good_long_signal)
        
        assert not report.is_valid
        assert len(report.failed_critical) > 0
        assert len(report.warnings) > 0
