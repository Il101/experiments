"""
Unit tests for TakeProfitOptimizer.

Tests cover:
1. Base TP level generation from config
2. Density zone avoidance
3. S/R level avoidance
4. Expected reward calculation
5. Level validation
6. Edge cases (no zones, disabled features, etc.)
"""

import pytest
from decimal import Decimal

from breakout_bot.strategy.takeprofit_optimizer import (
    TakeProfitOptimizer,
    DensityZone,
    SRLevel,
    OptimizedTPLevel,
)
from breakout_bot.config.settings import (
    PositionConfig,
    TakeProfitLevel,
    TakeProfitSmartPlacement,
)


@pytest.fixture
def basic_position_config():
    """Basic position config with 3 TP levels."""
    return PositionConfig(
        tp1_r=2.0,
        tp1_size_pct=30.0,
        tp2_r=4.0,
        tp2_size_pct=40.0,
        tp_levels=[
            TakeProfitLevel(
                level_name="TP1",
                reward_multiple=2.0,
                size_pct=0.3,  # 30%
            ),
            TakeProfitLevel(
                level_name="TP2",
                reward_multiple=4.0,
                size_pct=0.4,  # 40%
            ),
            TakeProfitLevel(
                level_name="TP3",
                reward_multiple=6.0,
                size_pct=0.3,  # 30%
            ),
        ],
        tp_smart_placement=TakeProfitSmartPlacement(
            enabled=False,  # Disabled by default for basic config
        ),
    )


@pytest.fixture
def smart_placement_config():
    """Position config with smart placement enabled."""
    return PositionConfig(
        tp1_r=2.0,
        tp1_size_pct=30.0,
        tp2_r=4.0,
        tp2_size_pct=40.0,
        tp_levels=[
            TakeProfitLevel(
                level_name="TP1",
                reward_multiple=2.0,
                size_pct=0.3,
            ),
            TakeProfitLevel(
                level_name="TP2",
                reward_multiple=4.0,
                size_pct=0.4,
            ),
            TakeProfitLevel(
                level_name="TP3",
                reward_multiple=6.0,
                size_pct=0.3,
            ),
        ],
        tp_smart_placement=TakeProfitSmartPlacement(
            enabled=True,
            avoid_density_zones=True,
            avoid_sr_levels=True,
        ),
    )


class TestBasicTPGeneration:
    """Test base TP level generation without optimization."""
    
    def test_basic_long_position(self, basic_position_config):
        """Test TP generation for long position."""
        optimizer = TakeProfitOptimizer(basic_position_config)
        
        entry = Decimal("100")
        stop_loss = Decimal("95")  # Risk = 5
        
        levels = optimizer.optimize(
            entry_price=entry,
            stop_loss=stop_loss,
            is_long=True,
        )
        
        assert len(levels) == 3
        
        # TP1: 100 + (5 * 2.0) = 110
        assert levels[0].optimized_price == Decimal("110")
        assert levels[0].reward_multiple == Decimal("2.0")
        assert levels[0].size_percent == Decimal("30")  # 0.3 * 100
        assert not levels[0].was_adjusted
        
        # TP2: 100 + (5 * 4.0) = 120
        assert levels[1].optimized_price == Decimal("120")
        assert levels[1].reward_multiple == Decimal("4.0")
        
        # TP3: 100 + (5 * 6.0) = 130
        assert levels[2].optimized_price == Decimal("130")
        assert levels[2].reward_multiple == Decimal("6.0")
    
    def test_basic_short_position(self, basic_position_config):
        """Test TP generation for short position."""
        optimizer = TakeProfitOptimizer(basic_position_config)
        
        entry = Decimal("100")
        stop_loss = Decimal("105")  # Risk = 5
        
        levels = optimizer.optimize(
            entry_price=entry,
            stop_loss=stop_loss,
            is_long=False,
        )
        
        assert len(levels) == 3
        
        # TP1: 100 - (5 * 2.0) = 90
        assert levels[0].optimized_price == Decimal("90")
        
        # TP2: 100 - (5 * 4.0) = 80
        assert levels[1].optimized_price == Decimal("80")
        
        # TP3: 100 - (5 * 6.0) = 70
        assert levels[2].optimized_price == Decimal("70")
    
    def test_zero_risk_raises_error(self, basic_position_config):
        """Test that zero risk raises ValueError."""
        optimizer = TakeProfitOptimizer(basic_position_config)
        
        with pytest.raises(ValueError, match="Risk.*cannot be zero"):
            optimizer.optimize(
                entry_price=Decimal("100"),
                stop_loss=Decimal("100"),  # Same as entry!
                is_long=True,
            )


class TestDensityZoneAvoidance:
    """Test density zone avoidance logic."""
    
    def test_tp_inside_density_zone_long(self, basic_position_config, smart_placement_config):
        """Test TP nudged before density zone for long position."""
        # Use smart_placement_config which has tp_smart_placement configured
        optimizer = TakeProfitOptimizer(smart_placement_config)
        
        entry = Decimal("100")
        stop_loss = Decimal("95")
        
        # Create density zone that conflicts with TP2 (120)
        density_zones = [
            DensityZone(
                price_start=Decimal("118"),
                price_end=Decimal("122"),
                volume=Decimal("10000"),
                strength=0.9,
            )
        ]
        
        levels = optimizer.optimize(
            entry_price=entry,
            stop_loss=stop_loss,
            is_long=True,
            density_zones=density_zones,
        )
        
        # TP1 (110) - not affected
        assert not levels[0].was_adjusted
        assert levels[0].optimized_price == Decimal("110")
        
        # TP2 (120) - should be nudged before zone
        assert levels[1].was_adjusted
        # Should be moved to: 118 - (120 * 0.001) = 118 - 0.12 = 117.88
        assert levels[1].optimized_price == Decimal("117.88")
        assert levels[1].adjustment_reason is not None
        assert "Density zone avoidance" in levels[1].adjustment_reason
        
        # TP3 (130) - not in zone
        assert not levels[2].was_adjusted
    
    def test_avoidance_disabled(self, basic_position_config):
        """Test that density zones are ignored when avoidance is disabled."""
        smart_placement = TakeProfitSmartPlacement(
            density_zone_buffer_bps=10.0,
            sr_level_buffer_bps=15.0,
            avoid_density_zones=False,  # Disabled!
            avoid_sr_levels=False,
        )
        optimizer = TakeProfitOptimizer(basic_position_config, smart_placement)
        
        entry = Decimal("100")
        stop_loss = Decimal("95")
        
        density_zones = [
            DensityZone(
                price_start=Decimal("118"),
                price_end=Decimal("122"),
                volume=Decimal("10000"),
                strength=0.9,
            )
        ]
        
        levels = optimizer.optimize(
            entry_price=entry,
            stop_loss=stop_loss,
            is_long=True,
            density_zones=density_zones,
        )
        
        # No adjustments should happen
        assert all(not level.was_adjusted for level in levels)


class TestExpectedReward:
    """Test expected reward calculation."""
    
    def test_expected_reward_no_adjustments(self, basic_position_config):
        """Test expected reward with no TP adjustments."""
        optimizer = TakeProfitOptimizer(basic_position_config)
        
        entry = Decimal("100")
        stop_loss = Decimal("95")
        
        levels = optimizer.optimize(
            entry_price=entry,
            stop_loss=stop_loss,
            is_long=True,
        )
        
        expected_r = optimizer.calculate_expected_reward(
            optimized_levels=levels,
            entry_price=entry,
            stop_loss=stop_loss,
            is_long=True,
        )
        
        # Expected R = (0.3 * 2.0) + (0.4 * 4.0) + (0.3 * 6.0)
        #            = 0.6 + 1.6 + 1.8 = 4.0R
        assert expected_r == Decimal("4.0")


class TestEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_no_tp_levels_raises_error(self):
        """Test that config with no TP levels raises error."""
        with pytest.raises(ValueError, match="at least one TP level"):
            invalid_config = PositionConfig(
                tp1_r=1.0,
                tp1_size_pct=100.0,
                tp2_r=2.0,
                tp2_size_pct=0.0,
                tp_levels=[],  # Empty!
            )
            TakeProfitOptimizer(invalid_config)
    
    def test_no_smart_placement_no_optimization(self, basic_position_config):
        """Test that without smart placement, no optimization occurs."""
        # Explicitly pass None to disable smart placement
        optimizer = TakeProfitOptimizer(basic_position_config, smart_placement=None)
        
        entry = Decimal("100")
        stop_loss = Decimal("95")
        
        density_zones = [
            DensityZone(
                price_start=Decimal("118"),
                price_end=Decimal("122"),
                volume=Decimal("10000"),
                strength=0.9,
            )
        ]
        
        levels = optimizer.optimize(
            entry_price=entry,
            stop_loss=stop_loss,
            is_long=True,
            density_zones=density_zones,
        )
        
        # No adjustments should happen when smart placement is explicitly disabled
        # (basic_position_config may have tp_smart_placement, so we override with None)
        assert all(not level.was_adjusted for level in levels)
