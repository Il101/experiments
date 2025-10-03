"""
Unit tests for FSMConfig (Finite State Machine Configuration) model.

Tests:
- Entry state configuration
- Running state configuration
- Partial closed state configuration
- Breakeven and trailing stops
- Exiting state configuration
"""

import pytest
from pydantic import ValidationError
from breakout_bot.config.settings import FSMConfig


class TestFSMConfigValidation:
    """Test FSMConfig validation rules."""
    
    def test_valid_fsm_config(self):
        """Test creating valid FSM config."""
        fsm = FSMConfig(
            enabled=True,
            entry_confirmation_bars=2,
            entry_max_slippage_bps=10.0,
            running_monitor_interval_s=5,
            running_breakeven_trigger_r=1.0,
            partial_closed_trail_enabled=True,
            partial_closed_trail_trigger_r=2.0,
            partial_closed_trail_step_bps=20.0,
            breakeven_buffer_bps=5.0,
            trailing_activation_r=2.0,
            trailing_step_bps=20.0
        )
        
        assert fsm.enabled is True
        assert fsm.entry_confirmation_bars == 2
        assert fsm.entry_max_slippage_bps == 10.0
        assert fsm.running_monitor_interval_s == 5
        assert fsm.running_breakeven_trigger_r == 1.0
        assert fsm.partial_closed_trail_enabled is True
    
    def test_entry_confirmation_bars_positive(self):
        """Test entry_confirmation_bars must be positive."""
        with pytest.raises(ValidationError) as exc_info:
            FSMConfig(
                entry_confirmation_bars=0
            )
        
        assert "entry_confirmation_bars must be at least 1" in str(exc_info.value)
    
    def test_bps_values_non_negative(self):
        """Test BPS values must be non-negative."""
        with pytest.raises(ValidationError) as exc_info:
            FSMConfig(
                entry_max_slippage_bps=-5.0
            )
        
        assert "BPS values must be non-negative" in str(exc_info.value)


class TestFSMConfigDefaults:
    """Test default values."""
    
    def test_default_values(self):
        """Test all default values are set correctly."""
        fsm = FSMConfig()
        
        assert fsm.enabled is True
        assert fsm.entry_confirmation_bars == 2
        assert fsm.entry_max_slippage_bps == 10.0
        assert fsm.running_monitor_interval_s == 5
        assert fsm.running_breakeven_trigger_r == 1.0
        assert fsm.partial_closed_trail_enabled is True
        assert fsm.partial_closed_trail_trigger_r == 2.0
        assert fsm.breakeven_buffer_bps == 5.0
        assert fsm.trailing_activation_r == 2.0


class TestFSMConfigEdgeCases:
    """Test edge cases and boundary conditions."""
    
    def test_disabled_fsm(self):
        """Test disabling FSM."""
        fsm = FSMConfig(enabled=False)
        
        assert fsm.enabled is False
    
    def test_disabled_trailing(self):
        """Test disabling trailing after partial close."""
        fsm = FSMConfig(partial_closed_trail_enabled=False)
        
        assert fsm.partial_closed_trail_enabled is False
    
    def test_disabled_acceleration(self):
        """Test disabling trailing acceleration."""
        fsm = FSMConfig(trailing_acceleration_enabled=False)
        
        assert fsm.trailing_acceleration_enabled is False


class TestFSMConfigUseCases:
    """Test real-world use cases."""
    
    def test_scalping_fsm_config(self):
        """Test FSM config for scalping."""
        fsm = FSMConfig(
            enabled=True,
            entry_confirmation_bars=1,
            entry_max_slippage_bps=5.0,
            running_breakeven_trigger_r=0.5,
            trailing_activation_r=1.0,
            trailing_step_bps=10.0
        )
        
        assert fsm.entry_confirmation_bars == 1
        assert fsm.running_breakeven_trigger_r == 0.5
        assert fsm.trailing_activation_r == 1.0
    
    def test_swing_fsm_config(self):
        """Test FSM config for swing trading."""
        fsm = FSMConfig(
            enabled=True,
            entry_confirmation_bars=3,
            running_breakeven_trigger_r=2.0,
            trailing_activation_r=4.0,
            trailing_step_bps=30.0,
            trailing_acceleration_enabled=True
        )
        
        assert fsm.entry_confirmation_bars == 3
        assert fsm.running_breakeven_trigger_r == 2.0
        assert fsm.trailing_activation_r == 4.0
        assert fsm.trailing_acceleration_enabled is True
