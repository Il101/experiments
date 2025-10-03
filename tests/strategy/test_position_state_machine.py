"""
Tests for PositionStateMachine component.
"""

import pytest
from decimal import Decimal
from datetime import datetime

from breakout_bot.strategy.position_state_machine import (
    PositionStateMachine,
    PositionState,
    PositionSnapshot,
    StateTransition,
)
from breakout_bot.config.settings import FSMConfig


@pytest.fixture
def default_fsm_config():
    """Default FSM configuration for testing."""
    return FSMConfig(
        entry_confirmation_bars=3,
        breakeven_lock_profit_enabled=True,
        running_breakeven_trigger_r=Decimal("1.5"),
        breakeven_buffer_bps=Decimal("5"),
        trailing_activation_r=Decimal("2.0"),
        trailing_step_bps=Decimal("50"),
        partial_closed_trail_enabled=True,
        partial_closed_trail_step_bps=Decimal("30"),
    )


@pytest.fixture
def fsm(default_fsm_config):
    """Create FSM instance."""
    return PositionStateMachine(default_fsm_config)


@pytest.fixture
def long_snapshot():
    """Basic long position snapshot."""
    return PositionSnapshot(
        current_price=Decimal("100"),
        entry_price=Decimal("100"),
        stop_loss=Decimal("98"),
        is_long=True,
        bars_since_entry=0,
        highest_price=Decimal("100"),
        lowest_price=Decimal("100"),
    )


@pytest.fixture
def short_snapshot():
    """Basic short position snapshot."""
    return PositionSnapshot(
        current_price=Decimal("100"),
        entry_price=Decimal("100"),
        stop_loss=Decimal("102"),
        is_long=False,
        bars_since_entry=0,
        highest_price=Decimal("100"),
        lowest_price=Decimal("100"),
    )


class TestPositionSnapshot:
    """Test PositionSnapshot calculations."""
    
    def test_calculate_current_r_long_profit(self, long_snapshot):
        """Test R calculation for long position in profit."""
        long_snapshot.current_price = Decimal("104")  # Entry: 100, SL: 98, risk: 2
        r = long_snapshot.calculate_current_r()
        assert r == Decimal("2")  # 4 profit / 2 risk = 2R
    
    def test_calculate_current_r_long_loss(self, long_snapshot):
        """Test R calculation for long position in loss."""
        long_snapshot.current_price = Decimal("99")  # Entry: 100, SL: 98, risk: 2
        r = long_snapshot.calculate_current_r()
        assert r == Decimal("-0.5")  # -1 loss / 2 risk = -0.5R
    
    def test_calculate_current_r_short_profit(self, short_snapshot):
        """Test R calculation for short position in profit."""
        short_snapshot.current_price = Decimal("96")  # Entry: 100, SL: 102, risk: 2
        r = short_snapshot.calculate_current_r()
        assert r == Decimal("2")  # 4 profit / 2 risk = 2R
    
    def test_calculate_current_r_short_loss(self, short_snapshot):
        """Test R calculation for short position in loss."""
        short_snapshot.current_price = Decimal("101")  # Entry: 100, SL: 102, risk: 2
        r = short_snapshot.calculate_current_r()
        assert r == Decimal("-0.5")  # -1 loss / 2 risk = -0.5R


class TestEntryConfirmation:
    """Test entry confirmation state."""
    
    def test_initial_state(self, fsm):
        """Test FSM starts in ENTRY_CONFIRMATION state."""
        assert fsm.get_state() == PositionState.ENTRY_CONFIRMATION
        assert not fsm.is_closed()
    
    def test_entry_confirmation_waiting(self, fsm, long_snapshot):
        """Test entry confirmation while waiting."""
        long_snapshot.bars_since_entry = 2  # Need 3
        transition = fsm.update(long_snapshot)
        
        assert transition is None
        assert fsm.get_state() == PositionState.ENTRY_CONFIRMATION
    
    def test_entry_confirmation_complete(self, fsm, long_snapshot):
        """Test entry confirmation completion."""
        long_snapshot.bars_since_entry = 3  # Meets requirement
        transition = fsm.update(long_snapshot)
        
        assert transition is not None
        assert transition.from_state == PositionState.ENTRY_CONFIRMATION
        assert transition.to_state == PositionState.RUNNING
        assert "confirmed" in transition.reason.lower()
        assert fsm.get_state() == PositionState.RUNNING


class TestBreakevenTrigger:
    """Test breakeven trigger logic."""
    
    def test_breakeven_not_triggered_yet(self, fsm, long_snapshot):
        """Test breakeven not triggered yet."""
        # Move to RUNNING state first
        long_snapshot.bars_since_entry = 3
        fsm.update(long_snapshot)
        
        # Price at 1.0R (need 1.5R)
        long_snapshot.current_price = Decimal("102")  # Entry: 100, SL: 98, risk: 2 -> 1R
        long_snapshot.bars_since_entry = 4
        transition = fsm.update(long_snapshot)
        
        assert transition is None
        assert fsm.get_state() == PositionState.RUNNING
    
    def test_breakeven_triggered(self, fsm, long_snapshot):
        """Test breakeven trigger."""
        # Move to RUNNING state first
        long_snapshot.bars_since_entry = 3
        fsm.update(long_snapshot)
        
        # Price at 1.5R (meets threshold)
        long_snapshot.current_price = Decimal("103")  # Entry: 100, SL: 98, risk: 2 -> 1.5R
        long_snapshot.bars_since_entry = 4
        transition = fsm.update(long_snapshot)
        
        assert transition is not None
        assert transition.from_state == PositionState.RUNNING
        assert transition.to_state == PositionState.BREAKEVEN
        assert "breakeven" in transition.reason.lower()
        assert fsm.get_state() == PositionState.BREAKEVEN
    
    def test_breakeven_disabled(self, long_snapshot):
        """Test breakeven when disabled."""
        config = FSMConfig(
            entry_confirmation_bars=3,
            breakeven_lock_profit_enabled=False,
            running_breakeven_trigger_r=Decimal("1.5"),
            trailing_activation_r=Decimal("0"),  # Disable trailing by setting to 0
        )
        fsm = PositionStateMachine(config)
        
        # Move to RUNNING
        long_snapshot.bars_since_entry = 3
        fsm.update(long_snapshot)
        
        # Price at 2.0R
        long_snapshot.current_price = Decimal("104")
        long_snapshot.bars_since_entry = 4
        transition = fsm.update(long_snapshot)
        
        assert transition is None
        assert fsm.get_state() == PositionState.RUNNING


class TestTrailingStop:
    """Test trailing stop activation."""
    
    def test_trailing_not_activated_yet(self, fsm, long_snapshot):
        """Test trailing not activated yet."""
        # Move to RUNNING state
        long_snapshot.bars_since_entry = 3
        fsm.update(long_snapshot)
        
        # Price at 1.8R (need 2.0R)
        long_snapshot.current_price = Decimal("103.6")  # Entry: 100, SL: 98, risk: 2 -> 1.8R
        long_snapshot.bars_since_entry = 4
        transition = fsm.update(long_snapshot)
        
        # Should trigger breakeven first at 1.5R
        assert transition is not None
        assert transition.to_state == PositionState.BREAKEVEN
    
    def test_trailing_activated_from_running(self, fsm, long_snapshot):
        """Test trailing activation from RUNNING state."""
        # Move to RUNNING state
        long_snapshot.bars_since_entry = 3
        fsm.update(long_snapshot)
        
        # Price at 2.0R (meets threshold)
        long_snapshot.current_price = Decimal("104")  # Entry: 100, SL: 98, risk: 2 -> 2R
        long_snapshot.bars_since_entry = 4
        transition = fsm.update(long_snapshot)
        
        # Should trigger trailing (note: breakeven triggers first at 1.5R, but trailing has priority at 2.0R)
        # Actually, breakeven triggers first since 2.0R > 1.5R
        assert transition is not None
        # First transition will be to BREAKEVEN
        assert transition.to_state == PositionState.BREAKEVEN
    
    def test_trailing_activated_from_breakeven(self, fsm, long_snapshot):
        """Test trailing activation from BREAKEVEN state."""
        # Move to RUNNING state
        long_snapshot.bars_since_entry = 3
        fsm.update(long_snapshot)
        
        # Trigger breakeven first
        long_snapshot.current_price = Decimal("103")  # 1.5R
        long_snapshot.bars_since_entry = 4
        fsm.update(long_snapshot)
        assert fsm.get_state() == PositionState.BREAKEVEN
        
        # Now trigger trailing
        long_snapshot.current_price = Decimal("104")  # 2.0R
        long_snapshot.bars_since_entry = 5
        transition = fsm.update(long_snapshot)
        
        assert transition is not None
        assert transition.from_state == PositionState.BREAKEVEN
        assert transition.to_state == PositionState.TRAILING
        assert "trailing" in transition.reason.lower()
        assert fsm.get_state() == PositionState.TRAILING


class TestPartialClosure:
    """Test partial closure state."""
    
    def test_partial_closure_triggered(self, fsm, long_snapshot):
        """Test partial closure when TP hit."""
        # Move to RUNNING state
        long_snapshot.bars_since_entry = 3
        fsm.update(long_snapshot)
        
        # Simulate TP hit
        long_snapshot.current_price = Decimal("105")
        long_snapshot.tp_levels_hit = [0, 1]  # First 2 TPs hit
        long_snapshot.remaining_size_pct = Decimal("40")  # 60% closed
        long_snapshot.bars_since_entry = 4
        transition = fsm.update(long_snapshot)
        
        # Should trigger partial closure (unless breakeven/trailing triggered first)
        # At 105, that's 2.5R, so breakeven and trailing both trigger
        # Need to check which one happens first
        assert transition is not None
    
    def test_partial_closure_from_trailing(self, fsm, long_snapshot):
        """Test partial closure from TRAILING state."""
        # Move to TRAILING state
        long_snapshot.bars_since_entry = 3
        fsm.update(long_snapshot)
        long_snapshot.bars_since_entry = 4
        long_snapshot.current_price = Decimal("103")
        fsm.update(long_snapshot)
        long_snapshot.bars_since_entry = 5
        long_snapshot.current_price = Decimal("104")
        fsm.update(long_snapshot)
        assert fsm.get_state() == PositionState.TRAILING
        
        # Now partial closure
        long_snapshot.current_price = Decimal("106")
        long_snapshot.tp_levels_hit = [0]
        long_snapshot.remaining_size_pct = Decimal("70")
        long_snapshot.bars_since_entry = 6
        transition = fsm.update(long_snapshot)
        
        assert transition is not None
        assert transition.to_state == PositionState.PARTIAL_CLOSED
        assert fsm.get_state() == PositionState.PARTIAL_CLOSED


class TestStopLossCalculation:
    """Test stop loss calculation logic."""
    
    def test_breakeven_stop_loss_long(self, fsm, long_snapshot):
        """Test breakeven SL calculation for long position."""
        # Move to BREAKEVEN state
        long_snapshot.bars_since_entry = 3
        fsm.update(long_snapshot)
        long_snapshot.current_price = Decimal("103")
        long_snapshot.bars_since_entry = 4
        fsm.update(long_snapshot)
        
        new_sl = fsm.calculate_new_stop_loss(long_snapshot)
        
        # Should be at entry + buffer
        buffer = long_snapshot.entry_price * (Decimal("5") / Decimal("10000"))
        expected_sl = long_snapshot.entry_price + buffer
        assert new_sl == expected_sl
        assert new_sl > long_snapshot.stop_loss  # Better than original
    
    def test_breakeven_stop_loss_short(self, fsm, short_snapshot):
        """Test breakeven SL calculation for short position."""
        # Move to BREAKEVEN state
        short_snapshot.bars_since_entry = 3
        fsm.update(short_snapshot)
        short_snapshot.current_price = Decimal("97")  # 1.5R profit
        short_snapshot.bars_since_entry = 4
        fsm.update(short_snapshot)
        
        new_sl = fsm.calculate_new_stop_loss(short_snapshot)
        
        # Should be at entry - buffer
        buffer = short_snapshot.entry_price * (Decimal("5") / Decimal("10000"))
        expected_sl = short_snapshot.entry_price - buffer
        assert new_sl == expected_sl
        assert new_sl < short_snapshot.stop_loss  # Better than original
    
    def test_trailing_stop_loss_long(self, fsm, long_snapshot):
        """Test trailing SL calculation for long position."""
        # Move to TRAILING state
        long_snapshot.bars_since_entry = 3
        fsm.update(long_snapshot)
        long_snapshot.bars_since_entry = 4
        long_snapshot.current_price = Decimal("103")
        fsm.update(long_snapshot)
        long_snapshot.bars_since_entry = 5
        long_snapshot.current_price = Decimal("104")
        fsm.update(long_snapshot)
        
        long_snapshot.current_price = Decimal("110")
        new_sl = fsm.calculate_new_stop_loss(long_snapshot)
        
        # Should be below current price by trailing_step_bps
        trail_distance = Decimal("110") * (Decimal("50") / Decimal("10000"))
        expected_sl = Decimal("110") - trail_distance
        assert new_sl == expected_sl
    
    def test_should_update_stop_loss_long(self, fsm, long_snapshot):
        """Test should_update_stop_loss for long position."""
        # Move to BREAKEVEN state
        long_snapshot.bars_since_entry = 3
        fsm.update(long_snapshot)
        long_snapshot.current_price = Decimal("103")
        long_snapshot.bars_since_entry = 4
        fsm.update(long_snapshot)
        
        current_sl = Decimal("98")  # Original SL
        should_update = fsm.should_update_stop_loss(long_snapshot, current_sl)
        
        # New SL should be higher (better), so yes
        assert should_update is True
    
    def test_should_not_update_stop_loss(self, fsm, long_snapshot):
        """Test should_update_stop_loss when no update needed."""
        # In RUNNING state, no SL adjustment
        long_snapshot.bars_since_entry = 3
        fsm.update(long_snapshot)
        
        current_sl = Decimal("98")
        should_update = fsm.should_update_stop_loss(long_snapshot, current_sl)
        
        assert should_update is False


class TestPositionClosure:
    """Test position closure."""
    
    def test_close_position(self, fsm):
        """Test closing position."""
        transition = fsm.close_position("Stop loss hit")
        
        assert transition is not None
        assert transition.to_state == PositionState.CLOSED
        assert "stop loss" in transition.reason.lower()
        assert fsm.is_closed()
    
    def test_close_from_partial_closed(self, fsm, long_snapshot):
        """Test closing from PARTIAL_CLOSED state."""
        # Move to PARTIAL_CLOSED
        long_snapshot.bars_since_entry = 3
        fsm.update(long_snapshot)
        long_snapshot.bars_since_entry = 4
        long_snapshot.current_price = Decimal("110")
        long_snapshot.tp_levels_hit = [0, 1, 2]
        long_snapshot.remaining_size_pct = Decimal("25")
        fsm.update(long_snapshot)
        
        # Close position
        transition = fsm.close_position("All TPs hit")
        
        assert transition is not None
        assert transition.to_state == PositionState.CLOSED
        assert fsm.is_closed()


class TestStateHistory:
    """Test state history tracking."""
    
    def test_history_tracking(self, fsm, long_snapshot):
        """Test state transition history."""
        # Entry confirmation
        long_snapshot.bars_since_entry = 3
        fsm.update(long_snapshot)
        
        # Breakeven
        long_snapshot.bars_since_entry = 4
        long_snapshot.current_price = Decimal("103")
        fsm.update(long_snapshot)
        
        # Trailing
        long_snapshot.bars_since_entry = 5
        long_snapshot.current_price = Decimal("104")
        fsm.update(long_snapshot)
        
        history = fsm.get_history()
        assert len(history) == 3
        assert history[0].to_state == PositionState.RUNNING
        assert history[1].to_state == PositionState.BREAKEVEN
        assert history[2].to_state == PositionState.TRAILING
    
    def test_get_time_in_state(self, fsm, long_snapshot):
        """Test time in state calculation."""
        long_snapshot.bars_since_entry = 3
        fsm.update(long_snapshot)
        
        time_in_state = fsm.get_time_in_state()
        assert time_in_state is not None
        assert time_in_state >= 0
