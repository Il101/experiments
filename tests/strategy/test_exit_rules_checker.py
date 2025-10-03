"""
Unit tests for ExitRulesChecker.

Tests cover:
1. Failed breakout detection (long and short)
2. Activity drop detection
3. Weak impulse detection
4. Time-based exits (max hold time, time stop)
5. Signal prioritization
6. Edge cases
"""

import pytest
from decimal import Decimal
from datetime import datetime, timedelta

from breakout_bot.strategy.exit_rules_checker import (
    ExitRulesChecker,
    MarketState,
    ExitSignal,
)
from breakout_bot.config.settings import ExitRulesConfig


@pytest.fixture
def basic_exit_config():
    """Basic exit config with all rules enabled."""
    return ExitRulesConfig(
        failed_breakout_enabled=True,
        failed_breakout_bars=3,
        failed_breakout_retest_threshold=0.5,
        activity_drop_enabled=True,
        activity_drop_threshold=0.3,
        activity_drop_window_bars=5,
        weak_impulse_enabled=True,
        weak_impulse_min_move_pct=0.3,
        weak_impulse_check_bars=5,
        max_hold_time_hours=24.0,
        time_stop_minutes=30,
    )


@pytest.fixture
def long_market_state():
    """Market state for long position."""
    return MarketState(
        current_price=Decimal("105"),
        current_volume=Decimal("1000"),
        current_momentum=Decimal("0.5"),
        bars_since_entry=10,
        entry_price=Decimal("100"),
        breakout_level=Decimal("98"),
        highest_price=Decimal("106"),
        lowest_price=Decimal("99"),
        entry_time=datetime.now() - timedelta(hours=1),
        is_long=True,
        avg_volume_before_entry=Decimal("2000"),
        avg_momentum_before_entry=Decimal("1.0"),
    )


@pytest.fixture
def short_market_state():
    """Market state for short position."""
    return MarketState(
        current_price=Decimal("95"),
        current_volume=Decimal("1000"),
        current_momentum=Decimal("0.5"),
        bars_since_entry=10,
        entry_price=Decimal("100"),
        breakout_level=Decimal("102"),
        highest_price=Decimal("101"),
        lowest_price=Decimal("94"),
        entry_time=datetime.now() - timedelta(hours=1),
        is_long=False,
        avg_volume_before_entry=Decimal("2000"),
        avg_momentum_before_entry=Decimal("1.0"),
    )


class TestFailedBreakout:
    """Test failed breakout detection."""
    
    def test_long_failed_breakout(self, basic_exit_config, long_market_state):
        """Test failed breakout for long position."""
        checker = ExitRulesChecker(basic_exit_config)
        
        # Price drops below breakout level
        long_market_state.current_price = Decimal("97")  # Below 98
        
        signals = checker.check_all_rules(long_market_state)
        
        # Should trigger failed breakout
        failed_signals = [s for s in signals if s.rule_name == "failed_breakout"]
        assert len(failed_signals) == 1
        assert failed_signals[0].should_exit
        assert failed_signals[0].urgency == "immediate"
        assert failed_signals[0].confidence == 0.9
    
    def test_short_failed_breakout(self, basic_exit_config, short_market_state):
        """Test failed breakout for short position."""
        checker = ExitRulesChecker(basic_exit_config)
        
        # Price rises above breakout level
        short_market_state.current_price = Decimal("103")  # Above 102
        
        signals = checker.check_all_rules(short_market_state)
        
        # Should trigger failed breakout
        failed_signals = [s for s in signals if s.rule_name == "failed_breakout"]
        assert len(failed_signals) == 1
        assert failed_signals[0].should_exit
    
    def test_no_failed_breakout_too_early(self, basic_exit_config, long_market_state):
        """Test that failed breakout doesn't trigger if too few bars."""
        checker = ExitRulesChecker(basic_exit_config)
        
        # Only 2 bars (config requires 3)
        long_market_state.bars_since_entry = 2
        long_market_state.current_price = Decimal("97")  # Below breakout
        
        signals = checker.check_all_rules(long_market_state)
        
        # Should NOT trigger (too early)
        failed_signals = [s for s in signals if s.rule_name == "failed_breakout"]
        assert len(failed_signals) == 0


class TestActivityDrop:
    """Test activity drop detection."""
    
    def test_activity_drop_volume(self, basic_exit_config, long_market_state):
        """Test activity drop due to low volume."""
        checker = ExitRulesChecker(basic_exit_config)
        
        # Volume drops to 25% of average (threshold is 30%)
        long_market_state.current_volume = Decimal("500")  # 500/2000 = 0.25
        
        signals = checker.check_all_rules(long_market_state)
        
        # Should trigger activity drop
        activity_signals = [s for s in signals if s.rule_name == "activity_drop"]
        assert len(activity_signals) == 1
        assert activity_signals[0].should_exit
        assert activity_signals[0].urgency == "normal"
    
    def test_activity_drop_momentum(self, basic_exit_config, long_market_state):
        """Test activity drop due to low momentum."""
        checker = ExitRulesChecker(basic_exit_config)
        
        # Momentum drops to 20% of average
        long_market_state.current_momentum = Decimal("0.2")  # 0.2/1.0 = 0.2
        
        signals = checker.check_all_rules(long_market_state)
        
        # Should trigger activity drop
        activity_signals = [s for s in signals if s.rule_name == "activity_drop"]
        assert len(activity_signals) == 1
    
    def test_no_activity_drop_sufficient_activity(self, basic_exit_config, long_market_state):
        """Test that activity drop doesn't trigger with sufficient activity."""
        checker = ExitRulesChecker(basic_exit_config)
        
        # Volume and momentum above threshold
        long_market_state.current_volume = Decimal("800")  # 40% of average
        long_market_state.current_momentum = Decimal("0.5")  # 50% of average
        
        signals = checker.check_all_rules(long_market_state)
        
        # Should NOT trigger
        activity_signals = [s for s in signals if s.rule_name == "activity_drop"]
        assert len(activity_signals) == 0


class TestWeakImpulse:
    """Test weak impulse detection."""
    
    def test_weak_impulse_long(self, basic_exit_config, long_market_state):
        """Test weak impulse for long position."""
        checker = ExitRulesChecker(basic_exit_config)
        
        # Only 0.2% movement (config requires 0.3%)
        long_market_state.highest_price = Decimal("100.2")  # 0.2% from entry
        
        signals = checker.check_all_rules(long_market_state)
        
        # Should trigger weak impulse
        weak_signals = [s for s in signals if s.rule_name == "weak_impulse"]
        assert len(weak_signals) == 1
        assert weak_signals[0].should_exit
    
    def test_weak_impulse_short(self, basic_exit_config, short_market_state):
        """Test weak impulse for short position."""
        checker = ExitRulesChecker(basic_exit_config)
        
        # Only 0.15% movement (config requires 0.3%)
        short_market_state.lowest_price = Decimal("99.85")  # 0.15% from entry
        
        signals = checker.check_all_rules(short_market_state)
        
        # Should trigger weak impulse
        weak_signals = [s for s in signals if s.rule_name == "weak_impulse"]
        assert len(weak_signals) == 1
    
    def test_no_weak_impulse_strong_move(self, basic_exit_config, long_market_state):
        """Test that weak impulse doesn't trigger with strong movement."""
        checker = ExitRulesChecker(basic_exit_config)
        
        # Strong 2% movement
        long_market_state.highest_price = Decimal("102")  # 2% from entry
        
        signals = checker.check_all_rules(long_market_state)
        
        # Should NOT trigger
        weak_signals = [s for s in signals if s.rule_name == "weak_impulse"]
        assert len(weak_signals) == 0


class TestTimeBasedExits:
    """Test time-based exit rules."""
    
    def test_max_hold_time_exceeded(self, basic_exit_config, long_market_state):
        """Test max hold time exit."""
        checker = ExitRulesChecker(basic_exit_config)
        
        # Position held for 25 hours (limit is 24)
        long_market_state.entry_time = datetime.now() - timedelta(hours=25)
        
        signals = checker.check_all_rules(long_market_state)
        
        # Should trigger max hold time
        time_signals = [s for s in signals if s.rule_name == "max_hold_time"]
        assert len(time_signals) == 1
        assert time_signals[0].should_exit
        assert time_signals[0].confidence == 1.0  # Time-based is certain
    
    def test_time_stop_not_profitable(self, basic_exit_config, long_market_state):
        """Test time stop when position not profitable."""
        checker = ExitRulesChecker(basic_exit_config)
        
        # Position held for 31 minutes (limit is 30)
        long_market_state.entry_time = datetime.now() - timedelta(minutes=31)
        
        # Position not profitable (price below entry)
        long_market_state.current_price = Decimal("99")  # Below entry of 100
        
        signals = checker.check_all_rules(long_market_state)
        
        # Should trigger time stop
        time_signals = [s for s in signals if s.rule_name == "time_stop"]
        assert len(time_signals) == 1
        assert time_signals[0].should_exit
    
    def test_time_stop_profitable_no_exit(self, basic_exit_config, long_market_state):
        """Test that time stop doesn't trigger if position is profitable."""
        checker = ExitRulesChecker(basic_exit_config)
        
        # Position held for 31 minutes
        long_market_state.entry_time = datetime.now() - timedelta(minutes=31)
        
        # Position IS profitable (price above entry)
        long_market_state.current_price = Decimal("105")  # Above entry of 100
        
        signals = checker.check_all_rules(long_market_state)
        
        # Should NOT trigger time stop (position is profitable)
        time_signals = [s for s in signals if s.rule_name == "time_stop"]
        assert len(time_signals) == 0


class TestSignalPrioritization:
    """Test signal prioritization logic."""
    
    def test_get_highest_priority_immediate_wins(self, basic_exit_config):
        """Test that immediate urgency signals have highest priority."""
        checker = ExitRulesChecker(basic_exit_config)
        
        signals = [
            ExitSignal(
                should_exit=True,
                rule_name="activity_drop",
                reason="Low activity",
                urgency="normal",
                confidence=0.9,
            ),
            ExitSignal(
                should_exit=True,
                rule_name="failed_breakout",
                reason="Failed breakout",
                urgency="immediate",
                confidence=0.7,
            ),
        ]
        
        priority = checker.get_highest_priority_signal(signals)
        
        # Immediate urgency should win even with lower confidence
        assert priority.rule_name == "failed_breakout"
        assert priority.urgency == "immediate"
    
    def test_get_highest_priority_confidence_tiebreaker(self, basic_exit_config):
        """Test that confidence is tiebreaker for same urgency."""
        checker = ExitRulesChecker(basic_exit_config)
        
        signals = [
            ExitSignal(
                should_exit=True,
                rule_name="activity_drop",
                reason="Low activity",
                urgency="normal",
                confidence=0.6,
            ),
            ExitSignal(
                should_exit=True,
                rule_name="weak_impulse",
                reason="Weak movement",
                urgency="normal",
                confidence=0.8,
            ),
        ]
        
        priority = checker.get_highest_priority_signal(signals)
        
        # Higher confidence should win
        assert priority.rule_name == "weak_impulse"
        assert priority.confidence == 0.8


class TestEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_disabled_rules_dont_trigger(self, long_market_state):
        """Test that disabled rules don't trigger."""
        config = ExitRulesConfig(
            failed_breakout_enabled=False,  # Disabled
            activity_drop_enabled=False,    # Disabled
            weak_impulse_enabled=False,     # Disabled
        )
        checker = ExitRulesChecker(config)
        
        # Set conditions that would trigger all rules if enabled
        long_market_state.current_price = Decimal("97")  # Failed breakout
        long_market_state.current_volume = Decimal("200")  # Activity drop
        long_market_state.highest_price = Decimal("100.1")  # Weak impulse
        
        signals = checker.check_all_rules(long_market_state)
        
        # Should NOT trigger any signals
        assert len(signals) == 0
    
    def test_should_exit_convenience_method(self, basic_exit_config, long_market_state):
        """Test should_exit convenience method."""
        checker = ExitRulesChecker(basic_exit_config)
        
        # Trigger failed breakout
        long_market_state.current_price = Decimal("97")
        
        should_exit, signal = checker.should_exit(long_market_state)
        
        assert should_exit is True
        assert signal is not None
        assert signal.rule_name == "failed_breakout"
    
    def test_no_exit_returns_false(self, basic_exit_config, long_market_state):
        """Test that should_exit returns False when no rules triggered."""
        checker = ExitRulesChecker(basic_exit_config)
        
        # Normal state, no exit conditions
        should_exit, signal = checker.should_exit(long_market_state)
        
        assert should_exit is False
        assert signal is None
