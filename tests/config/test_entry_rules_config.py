"""
Unit tests for EntryRulesConfig configuration model.

Tests:
- Volume confirmation
- Density confirmation  
- Momentum requirements
- Level approach validation
- Safety filters
- Time-based filters
"""

import pytest
from pydantic import ValidationError
from breakout_bot.config.settings import EntryRulesConfig


class TestEntryRulesConfigValidation:
    """Test EntryRulesConfig validation rules."""
    
    def test_valid_entry_rules(self):
        """Test creating valid entry rules config."""
        er = EntryRulesConfig(
            require_volume_confirmation=True,
            volume_confirmation_multiplier=1.5,
            require_density_confirmation=True,
            density_confirmation_threshold=2.0,
            require_momentum=True,
            momentum_min_slope_pct=0.5,
            momentum_check_bars=3,
            validate_approach=True,
            approach_max_slope_pct=1.5,
            approach_min_consolidation_bars=3,
            max_distance_from_level_bps=30.0,
            require_clean_breakout=True,
            false_start_lookback_bars=10
        )
        
        assert er.require_volume_confirmation is True
        assert er.volume_confirmation_multiplier == 1.5
        assert er.require_density_confirmation is True
        assert er.density_confirmation_threshold == 2.0
        assert er.require_momentum is True
        assert er.momentum_min_slope_pct == 0.5
        assert er.validate_approach is True
    
    def test_volume_multiplier_minimum(self):
        """Test volume_confirmation_multiplier must be >= 1.0."""
        with pytest.raises(ValidationError) as exc_info:
            EntryRulesConfig(
                volume_confirmation_multiplier=0.5
            )
        
        assert "Confirmation multiplier must be >= 1.0" in str(exc_info.value)
    
    def test_density_threshold_minimum(self):
        """Test density_confirmation_threshold must be >= 1.0."""
        with pytest.raises(ValidationError) as exc_info:
            EntryRulesConfig(
                density_confirmation_threshold=0.8
            )
        
        assert "Confirmation multiplier must be >= 1.0" in str(exc_info.value)
    
    def test_bars_positive(self):
        """Test bar counts must be positive."""
        with pytest.raises(ValidationError) as exc_info:
            EntryRulesConfig(
                momentum_check_bars=0
            )
        
        assert "Bar count must be at least 1" in str(exc_info.value)


class TestEntryRulesConfigDefaults:
    """Test default values."""
    
    def test_default_values(self):
        """Test all default values are set correctly."""
        er = EntryRulesConfig()
        
        assert er.require_volume_confirmation is True
        assert er.volume_confirmation_multiplier == 1.5
        assert er.require_density_confirmation is True
        assert er.density_confirmation_threshold == 2.0
        assert er.require_momentum is True
        assert er.momentum_min_slope_pct == 0.5
        assert er.momentum_check_bars == 3
        assert er.validate_approach is True
        assert er.require_clean_breakout is True


class TestEntryRulesConfigEdgeCases:
    """Test edge cases and boundary conditions."""
    
    def test_disabled_all_confirmations(self):
        """Test disabling all confirmations."""
        er = EntryRulesConfig(
            require_volume_confirmation=False,
            require_density_confirmation=False,
            require_momentum=False,
            validate_approach=False,
            require_clean_breakout=False
        )
        
        assert er.require_volume_confirmation is False
        assert er.require_density_confirmation is False
        assert er.require_momentum is False
        assert er.validate_approach is False
    
    def test_minimal_multipliers(self):
        """Test minimum valid multipliers."""
        er = EntryRulesConfig(
            volume_confirmation_multiplier=1.0,
            density_confirmation_threshold=1.0
        )
        
        assert er.volume_confirmation_multiplier == 1.0
        assert er.density_confirmation_threshold == 1.0


class TestEntryRulesConfigUseCases:
    """Test real-world use cases."""
    
    def test_scalping_entry_rules(self):
        """Test entry rules for scalping."""
        er = EntryRulesConfig(
            require_volume_confirmation=True,
            volume_confirmation_multiplier=2.0,
            require_density_confirmation=True,
            density_confirmation_threshold=3.0,
            momentum_min_slope_pct=0.3,
            max_distance_from_level_bps=20.0
        )
        
        assert er.volume_confirmation_multiplier == 2.0
        assert er.density_confirmation_threshold == 3.0
        assert er.max_distance_from_level_bps == 20.0
    
    def test_swing_entry_rules(self):
        """Test entry rules for swing trading."""
        er = EntryRulesConfig(
            require_volume_confirmation=True,
            volume_confirmation_multiplier=1.3,
            require_density_confirmation=True,
            density_confirmation_threshold=1.5,
            momentum_min_slope_pct=1.0,
            max_distance_from_level_bps=50.0
        )
        
        assert er.volume_confirmation_multiplier == 1.3
        assert er.density_confirmation_threshold == 1.5
        assert er.momentum_min_slope_pct == 1.0
    
    def test_conservative_entry_rules(self):
        """Test entry rules for conservative strategy."""
        er = EntryRulesConfig(
            require_volume_confirmation=True,
            volume_confirmation_multiplier=1.5,
            require_density_confirmation=True,
            density_confirmation_threshold=2.0,
            require_momentum=True,
            validate_approach=True,
            require_clean_breakout=True,
            false_start_lookback_bars=15
        )
        
        assert er.require_volume_confirmation is True
        assert er.require_density_confirmation is True
        assert er.require_momentum is True
        assert er.validate_approach is True
