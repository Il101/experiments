"""
Unit tests for TakeProfitSmartPlacement configuration model.

Tests:
- Smart TP placement parameters
- Density zone avoidance
- S/R level avoidance
- Round number targeting
"""

import pytest
from pydantic import ValidationError
from breakout_bot.config.settings import TakeProfitSmartPlacement


class TestTakeProfitSmartPlacementValidation:
    """Test TakeProfitSmartPlacement validation rules."""
    
    def test_valid_smart_placement(self):
        """Test creating valid smart placement config."""
        sp = TakeProfitSmartPlacement(
            enabled=True,
            avoid_density_zones=True,
            density_zone_buffer_bps=10.0,
            avoid_sr_levels=True,
            sr_level_buffer_bps=15.0,
            prefer_round_numbers=True,
            round_number_step=0.10,
            max_adjustment_bps=20.0
        )
        
        assert sp.enabled is True
        assert sp.avoid_density_zones is True
        assert sp.density_zone_buffer_bps == 10.0
        assert sp.avoid_sr_levels is True
        assert sp.sr_level_buffer_bps == 15.0
        assert sp.prefer_round_numbers is True
        assert sp.round_number_step == 0.10
        assert sp.max_adjustment_bps == 20.0
    
    def test_density_zone_buffer_bps_non_negative(self):
        """Test density_zone_buffer_bps must be non-negative."""
        with pytest.raises(ValidationError) as exc_info:
            TakeProfitSmartPlacement(
                density_zone_buffer_bps=-5.0
            )
        
        assert "Buffer/adjustment must be non-negative" in str(exc_info.value)
    
    def test_sr_level_buffer_bps_non_negative(self):
        """Test sr_level_buffer_bps must be non-negative."""
        with pytest.raises(ValidationError) as exc_info:
            TakeProfitSmartPlacement(
                sr_level_buffer_bps=-10.0
            )
        
        assert "Buffer/adjustment must be non-negative" in str(exc_info.value)
    
    def test_max_adjustment_bps_non_negative(self):
        """Test max_adjustment_bps must be non-negative."""
        with pytest.raises(ValidationError) as exc_info:
            TakeProfitSmartPlacement(
                max_adjustment_bps=-15.0
            )
        
        assert "Buffer/adjustment must be non-negative" in str(exc_info.value)


class TestTakeProfitSmartPlacementDefaults:
    """Test default values."""
    
    def test_default_values(self):
        """Test all default values are set correctly."""
        sp = TakeProfitSmartPlacement()
        
        assert sp.enabled is True
        assert sp.avoid_density_zones is True
        assert sp.density_zone_buffer_bps == 10.0
        assert sp.avoid_sr_levels is True
        assert sp.sr_level_buffer_bps == 15.0
        assert sp.prefer_round_numbers is True
        assert sp.round_number_step == 0.10
        assert sp.max_adjustment_bps == 20.0


class TestTakeProfitSmartPlacementEdgeCases:
    """Test edge cases and boundary conditions."""
    
    def test_disabled_smart_placement(self):
        """Test disabling smart placement."""
        sp = TakeProfitSmartPlacement(enabled=False)
        
        assert sp.enabled is False
    
    def test_zero_buffers(self):
        """Test zero buffer values."""
        sp = TakeProfitSmartPlacement(
            density_zone_buffer_bps=0.0,
            sr_level_buffer_bps=0.0,
            max_adjustment_bps=0.0
        )
        
        assert sp.density_zone_buffer_bps == 0.0
        assert sp.sr_level_buffer_bps == 0.0
        assert sp.max_adjustment_bps == 0.0


class TestTakeProfitSmartPlacementUseCases:
    """Test real-world use cases."""
    
    def test_scalping_config(self):
        """Test smart placement for scalping."""
        sp = TakeProfitSmartPlacement(
            enabled=True,
            density_zone_buffer_bps=5.0,
            sr_level_buffer_bps=8.0,
            max_adjustment_bps=10.0
        )
        
        assert sp.density_zone_buffer_bps == 5.0
        assert sp.max_adjustment_bps == 10.0
    
    def test_swing_config(self):
        """Test smart placement for swing trading."""
        sp = TakeProfitSmartPlacement(
            enabled=True,
            density_zone_buffer_bps=30.0,
            sr_level_buffer_bps=40.0,
            max_adjustment_bps=50.0
        )
        
        assert sp.density_zone_buffer_bps == 30.0
        assert sp.max_adjustment_bps == 50.0
