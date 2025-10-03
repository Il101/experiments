"""
Unit tests for ExitRulesConfig configuration model.

Tests:
- Failed breakout detection
- Activity drop exit
- Weak impulse exit
- Time-based exits
- Volatility-based exit
"""

import pytest
from pydantic import ValidationError
from breakout_bot.config.settings import ExitRulesConfig


class TestExitRulesConfigValidation:
    """Test ExitRulesConfig validation rules."""
    
    def test_valid_exit_rules(self):
        """Test creating valid exit rules config."""
        er = ExitRulesConfig(
            failed_breakout_enabled=True,
            failed_breakout_bars=3,
            failed_breakout_retest_threshold=0.5,
            activity_drop_enabled=True,
            activity_drop_threshold=0.3,
            activity_drop_window_bars=5,
            weak_impulse_enabled=True,
            weak_impulse_min_move_pct=0.3,
            weak_impulse_check_bars=5,
            max_hold_time_hours=48.0,
            volatility_exit_enabled=False
        )
        
        assert er.failed_breakout_enabled is True
        assert er.failed_breakout_bars == 3
        assert er.failed_breakout_retest_threshold == 0.5
        assert er.activity_drop_enabled is True
        assert er.activity_drop_threshold == 0.3
        assert er.weak_impulse_enabled is True
        assert er.max_hold_time_hours == 48.0
    
    def test_failed_breakout_bars_positive(self):
        """Test failed_breakout_bars must be positive."""
        with pytest.raises(ValidationError) as exc_info:
            ExitRulesConfig(
                failed_breakout_bars=0
            )
        
        assert "Bar count must be at least 1" in str(exc_info.value)
    
    def test_activity_drop_window_bars_positive(self):
        """Test activity_drop_window_bars must be positive."""
        with pytest.raises(ValidationError) as exc_info:
            ExitRulesConfig(
                activity_drop_window_bars=0
            )
        
        assert "Bar count must be at least 1" in str(exc_info.value)
    
    def test_threshold_range_valid(self):
        """Test thresholds must be between 0 and 1."""
        with pytest.raises(ValidationError) as exc_info:
            ExitRulesConfig(
                failed_breakout_retest_threshold=1.5
            )
        
        assert "Threshold must be between 0 and 1" in str(exc_info.value)


class TestExitRulesConfigDefaults:
    """Test default values."""
    
    def test_default_values(self):
        """Test all default values are set correctly."""
        er = ExitRulesConfig()
        
        assert er.failed_breakout_enabled is True
        assert er.failed_breakout_bars == 3
        assert er.failed_breakout_retest_threshold == 0.5
        assert er.activity_drop_enabled is True
        assert er.activity_drop_threshold == 0.3
        assert er.weak_impulse_enabled is True
        assert er.volatility_exit_enabled is False


class TestExitRulesConfigEdgeCases:
    """Test edge cases and boundary conditions."""
    
    def test_disabled_all_exits(self):
        """Test disabling all exit rules."""
        er = ExitRulesConfig(
            failed_breakout_enabled=False,
            activity_drop_enabled=False,
            weak_impulse_enabled=False,
            volatility_exit_enabled=False
        )
        
        assert er.failed_breakout_enabled is False
        assert er.activity_drop_enabled is False
        assert er.weak_impulse_enabled is False
    
    def test_optional_time_stops(self):
        """Test optional time stop fields."""
        er = ExitRulesConfig(
            max_hold_time_hours=None,
            time_stop_minutes=None
        )
        
        assert er.max_hold_time_hours is None
        assert er.time_stop_minutes is None


class TestExitRulesConfigUseCases:
    """Test real-world use cases."""
    
    def test_scalping_exit_rules(self):
        """Test exit rules for scalping."""
        er = ExitRulesConfig(
            failed_breakout_enabled=True,
            failed_breakout_bars=2,
            weak_impulse_enabled=True,
            weak_impulse_min_move_pct=0.2,
            max_hold_time_hours=2.0
        )
        
        assert er.failed_breakout_bars == 2
        assert er.max_hold_time_hours == 2.0
    
    def test_swing_exit_rules(self):
        """Test exit rules for swing trading."""
        er = ExitRulesConfig(
            failed_breakout_enabled=True,
            failed_breakout_bars=5,
            max_hold_time_hours=168.0,
            volatility_exit_enabled=True
        )
        
        assert er.failed_breakout_bars == 5
        assert er.max_hold_time_hours == 168.0
        assert er.volatility_exit_enabled is True
