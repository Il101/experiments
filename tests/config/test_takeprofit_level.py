"""
Unit tests for TakeProfitLevel configuration model.

Tests:
- Field validation (reward_multiple, size_pct, placement_mode)
- Value ranges and constraints
- Invalid inputs handling
"""

import pytest
from pydantic import ValidationError
from breakout_bot.config.settings import TakeProfitLevel


class TestTakeProfitLevelValidation:
    """Test TakeProfitLevel validation rules."""
    
    def test_valid_tp_level(self):
        """Test creating a valid TP level."""
        tp = TakeProfitLevel(
            level_name="TP1",
            reward_multiple=2.0,
            size_pct=0.5,
            placement_mode="smart"
        )
        
        assert tp.level_name == "TP1"
        assert tp.reward_multiple == 2.0
        assert tp.size_pct == 0.5
        assert tp.placement_mode == "smart"
    
    def test_reward_multiple_positive(self):
        """Test reward_multiple must be positive."""
        with pytest.raises(ValidationError) as exc_info:
            TakeProfitLevel(
                level_name="TP1",
                reward_multiple=0.0,  # Invalid: must be positive
                size_pct=0.5,
                placement_mode="fixed"
            )
        
        assert "reward_multiple must be positive" in str(exc_info.value)
    
    def test_reward_multiple_negative(self):
        """Test reward_multiple cannot be negative."""
        with pytest.raises(ValidationError) as exc_info:
            TakeProfitLevel(
                level_name="TP1",
                reward_multiple=-1.0,  # Invalid: negative
                size_pct=0.5,
                placement_mode="fixed"
            )
        
        assert "reward_multiple must be positive" in str(exc_info.value)
    
    def test_size_pct_valid_range(self):
        """Test size_pct accepts values between 0 and 1."""
        # Test minimum valid
        tp_min = TakeProfitLevel(
            level_name="TP1",
            reward_multiple=1.0,
            size_pct=0.01,
            placement_mode="fixed"
        )
        assert tp_min.size_pct == 0.01
        
        # Test maximum valid
        tp_max = TakeProfitLevel(
            level_name="TP1",
            reward_multiple=1.0,
            size_pct=1.0,
            placement_mode="fixed"
        )
        assert tp_max.size_pct == 1.0
    
    def test_size_pct_zero_invalid(self):
        """Test size_pct cannot be zero."""
        with pytest.raises(ValidationError) as exc_info:
            TakeProfitLevel(
                level_name="TP1",
                reward_multiple=1.0,
                size_pct=0.0,  # Invalid: must be > 0
                placement_mode="fixed"
            )
        
        assert "size_pct must be between 0 and 1" in str(exc_info.value)
    
    def test_size_pct_over_one_invalid(self):
        """Test size_pct cannot exceed 1.0."""
        with pytest.raises(ValidationError) as exc_info:
            TakeProfitLevel(
                level_name="TP1",
                reward_multiple=1.0,
                size_pct=1.1,  # Invalid: > 1.0
                placement_mode="fixed"
            )
        
        assert "size_pct must be between 0 and 1" in str(exc_info.value)
    
    def test_size_pct_negative_invalid(self):
        """Test size_pct cannot be negative."""
        with pytest.raises(ValidationError) as exc_info:
            TakeProfitLevel(
                level_name="TP1",
                reward_multiple=1.0,
                size_pct=-0.1,  # Invalid: negative
                placement_mode="fixed"
            )
        
        assert "size_pct must be between 0 and 1" in str(exc_info.value)
    
    def test_placement_mode_valid_values(self):
        """Test placement_mode accepts valid values."""
        valid_modes = ["fixed", "smart", "adaptive"]
        
        for mode in valid_modes:
            tp = TakeProfitLevel(
                level_name="TP1",
                reward_multiple=1.0,
                size_pct=0.5,
                placement_mode=mode
            )
            assert tp.placement_mode == mode
    
    def test_placement_mode_invalid_value(self):
        """Test placement_mode rejects invalid values."""
        with pytest.raises(ValidationError) as exc_info:
            TakeProfitLevel(
                level_name="TP1",
                reward_multiple=1.0,
                size_pct=0.5,
                placement_mode="invalid_mode"  # Invalid
            )
        
        assert "placement_mode must be one of" in str(exc_info.value)
    
    def test_placement_mode_default(self):
        """Test placement_mode has default value."""
        tp = TakeProfitLevel(
            level_name="TP1",
            reward_multiple=1.0,
            size_pct=0.5
            # placement_mode not specified
        )
        
        assert tp.placement_mode == "fixed"  # Default value


class TestTakeProfitLevelEdgeCases:
    """Test edge cases and boundary conditions."""
    
    def test_very_small_reward_multiple(self):
        """Test very small but valid reward_multiple."""
        tp = TakeProfitLevel(
            level_name="TP_scalp",
            reward_multiple=0.1,  # Very small R:R
            size_pct=1.0,
            placement_mode="fixed"
        )
        
        assert tp.reward_multiple == 0.1
    
    def test_very_large_reward_multiple(self):
        """Test very large reward_multiple."""
        tp = TakeProfitLevel(
            level_name="TP_moonshot",
            reward_multiple=100.0,  # Very large R:R
            size_pct=0.01,
            placement_mode="adaptive"
        )
        
        assert tp.reward_multiple == 100.0
    
    def test_fractional_size_pct(self):
        """Test fractional size_pct values."""
        tp = TakeProfitLevel(
            level_name="TP1",
            reward_multiple=1.0,
            size_pct=0.333333,  # 33.33%
            placement_mode="smart"
        )
        
        assert abs(tp.size_pct - 0.333333) < 0.000001
    
    def test_level_name_special_characters(self):
        """Test level_name with special characters."""
        tp = TakeProfitLevel(
            level_name="TP_1_aggressive_🚀",
            reward_multiple=2.0,
            size_pct=0.5,
            placement_mode="smart"
        )
        
        assert "🚀" in tp.level_name


class TestTakeProfitLevelUseCases:
    """Test real-world use cases."""
    
    def test_scalping_tp_level(self):
        """Test typical scalping TP level."""
        tp = TakeProfitLevel(
            level_name="TP1",
            reward_multiple=0.6,
            size_pct=0.4,
            placement_mode="smart"
        )
        
        assert tp.reward_multiple == 0.6
        assert tp.size_pct == 0.4
    
    def test_swing_tp_level(self):
        """Test typical swing trading TP level."""
        tp = TakeProfitLevel(
            level_name="TP5",
            reward_multiple=12.0,
            size_pct=0.1,
            placement_mode="adaptive"
        )
        
        assert tp.reward_multiple == 12.0
        assert tp.size_pct == 0.1
    
    def test_conservative_tp_level(self):
        """Test typical conservative TP level."""
        tp = TakeProfitLevel(
            level_name="TP2",
            reward_multiple=2.5,
            size_pct=0.25,
            placement_mode="smart"
        )
        
        assert tp.reward_multiple == 2.5
        assert tp.size_pct == 0.25
    
    def test_multiple_tp_levels_in_list(self):
        """Test creating a list of TP levels."""
        tp_levels = [
            TakeProfitLevel(
                level_name="TP1",
                reward_multiple=1.5,
                size_pct=0.25,
                placement_mode="smart"
            ),
            TakeProfitLevel(
                level_name="TP2",
                reward_multiple=2.5,
                size_pct=0.25,
                placement_mode="smart"
            ),
            TakeProfitLevel(
                level_name="TP3",
                reward_multiple=4.0,
                size_pct=0.25,
                placement_mode="smart"
            ),
            TakeProfitLevel(
                level_name="TP4",
                reward_multiple=6.0,
                size_pct=0.25,
                placement_mode="adaptive"
            )
        ]
        
        assert len(tp_levels) == 4
        assert sum(tp.size_pct for tp in tp_levels) == 1.0
        
        # Verify R:R is increasing
        for i in range(1, len(tp_levels)):
            assert tp_levels[i].reward_multiple > tp_levels[i-1].reward_multiple


class TestTakeProfitLevelSerialization:
    """Test serialization and deserialization."""
    
    def test_to_dict(self):
        """Test converting TP level to dict."""
        tp = TakeProfitLevel(
            level_name="TP1",
            reward_multiple=2.0,
            size_pct=0.5,
            placement_mode="smart"
        )
        
        tp_dict = tp.model_dump()
        
        assert tp_dict["level_name"] == "TP1"
        assert tp_dict["reward_multiple"] == 2.0
        assert tp_dict["size_pct"] == 0.5
        assert tp_dict["placement_mode"] == "smart"
    
    def test_from_dict(self):
        """Test creating TP level from dict."""
        tp_dict = {
            "level_name": "TP2",
            "reward_multiple": 3.0,
            "size_pct": 0.3,
            "placement_mode": "adaptive"
        }
        
        tp = TakeProfitLevel(**tp_dict)
        
        assert tp.level_name == "TP2"
        assert tp.reward_multiple == 3.0
        assert tp.size_pct == 0.3
        assert tp.placement_mode == "adaptive"
    
    def test_json_serialization(self):
        """Test JSON serialization."""
        tp = TakeProfitLevel(
            level_name="TP1",
            reward_multiple=2.0,
            size_pct=0.5,
            placement_mode="smart"
        )
        
        json_str = tp.model_dump_json()
        
        assert "TP1" in json_str
        assert "2.0" in json_str
        assert "smart" in json_str
