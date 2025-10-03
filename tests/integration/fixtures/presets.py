"""Test preset configurations for integration tests."""
from dataclasses import dataclass
from decimal import Decimal

from breakout_bot.config.settings import (
    PositionConfig,
    TakeProfitLevel,
    ExitRulesConfig,
    FSMConfig,
    EntryRulesConfig,
    MarketQualityConfig,
)


@dataclass
class TestStrategyConfig:
    """Test strategy configuration combining all components."""
    position: PositionConfig
    exit_rules: ExitRulesConfig
    fsm: FSMConfig
    entry_rules: EntryRulesConfig
    market_quality: MarketQualityConfig


def conservative_preset() -> TestStrategyConfig:
    """Conservative preset: strict quality filters, tight stops, cautious entry."""
    return TestStrategyConfig(
        position=PositionConfig(
            tp1_r=1.5,
            tp1_size_pct=50.0,
            tp2_r=3.0,
            tp2_size_pct=50.0,
            tp_levels=[
                TakeProfitLevel(
                    level_name="TP1",
                    reward_multiple=1.5,
                    size_pct=0.5
                ),
                TakeProfitLevel(
                    level_name="TP2",
                    reward_multiple=3.0,
                    size_pct=0.5
                ),
            ],
        ),
        exit_rules=ExitRulesConfig(),
        fsm=FSMConfig(
            entry_confirmation_bars=3,
            running_breakeven_trigger_r=1.5,
        ),
        entry_rules=EntryRulesConfig(
            require_volume_confirmation=True,
            volume_confirmation_multiplier=2.0,
            require_momentum=True,
            momentum_min_slope_pct=0.10,
            require_density_confirmation=True,
            max_distance_from_level_bps=50,
            false_start_lookback_bars=20,
        ),
        market_quality=MarketQualityConfig(
            flat_market_filter_enabled=True,
            consolidation_filter_enabled=True,
        ),
    )


def aggressive_preset() -> TestStrategyConfig:
    """Aggressive preset: loose quality filters, wide stops, aggressive entry."""
    return TestStrategyConfig(
        position=PositionConfig(
            tp1_r=2.0,
            tp1_size_pct=50.0,
            tp2_r=4.0,
            tp2_size_pct=50.0,
            tp_levels=[
                TakeProfitLevel(
                    level_name="TP1",
                    reward_multiple=2.0,
                    size_pct=0.5
                ),
                TakeProfitLevel(
                    level_name="TP2",
                    reward_multiple=4.0,
                    size_pct=0.5
                ),
            ],
        ),
        exit_rules=ExitRulesConfig(),
        fsm=FSMConfig(
            entry_confirmation_bars=1,
            running_breakeven_trigger_r=2.0,
        ),
        entry_rules=EntryRulesConfig(
            require_volume_confirmation=False,
            volume_confirmation_multiplier=1.2,
            require_momentum=True,
            momentum_min_slope_pct=0.05,
            require_density_confirmation=False,
            max_distance_from_level_bps=100,
            false_start_lookback_bars=10,
        ),
        market_quality=MarketQualityConfig(
            flat_market_filter_enabled=False,
            consolidation_filter_enabled=False,
        ),
    )


def balanced_preset() -> TestStrategyConfig:
    """Balanced preset: moderate quality filters, balanced risk/reward."""
    return TestStrategyConfig(
        position=PositionConfig(
            tp1_r=2.0,
            tp1_size_pct=50.0,
            tp2_r=3.5,
            tp2_size_pct=50.0,
            tp_levels=[
                TakeProfitLevel(
                    level_name="TP1",
                    reward_multiple=2.0,
                    size_pct=0.5
                ),
                TakeProfitLevel(
                    level_name="TP2",
                    reward_multiple=3.5,
                    size_pct=0.5
                ),
            ],
        ),
        exit_rules=ExitRulesConfig(),
        fsm=FSMConfig(
            entry_confirmation_bars=2,
            running_breakeven_trigger_r=1.2,
        ),
        entry_rules=EntryRulesConfig(
            require_volume_confirmation=True,
            volume_confirmation_multiplier=1.5,
            require_momentum=True,
            momentum_min_slope_pct=0.08,
            require_density_confirmation=True,
            max_distance_from_level_bps=75,
            false_start_lookback_bars=15,
        ),
        market_quality=MarketQualityConfig(
            flat_market_filter_enabled=True,
            consolidation_filter_enabled=True,
        ),
    )


__all__ = [
    "TestStrategyConfig",
    "conservative_preset",
    "aggressive_preset",
    "balanced_preset",
]
