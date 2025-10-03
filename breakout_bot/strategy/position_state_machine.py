"""
PositionStateMachine: Finite State Machine for position lifecycle management.

This component implements a state machine for position management:

States:
- ENTRY_CONFIRMATION: Waiting for entry confirmation bars
- RUNNING: Position is active, watching for exits
- BREAKEVEN: Stop loss moved to breakeven
- TRAILING: Trailing stop activated
- PARTIAL_CLOSED: Some TP levels hit
- CLOSED: Position fully closed

Transitions are config-driven via FSMConfig.
"""

from enum import Enum
from decimal import Decimal
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from datetime import datetime
import logging

from ..config.settings import FSMConfig

logger = logging.getLogger(__name__)


class PositionState(Enum):
    """Position states in the lifecycle."""
    ENTRY_CONFIRMATION = "entry_confirmation"
    RUNNING = "running"
    BREAKEVEN = "breakeven"
    TRAILING = "trailing"
    PARTIAL_CLOSED = "partial_closed"
    CLOSED = "closed"


@dataclass
class StateTransition:
    """Records a state transition."""
    from_state: PositionState
    to_state: PositionState
    timestamp: datetime
    reason: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PositionSnapshot:
    """Snapshot of position at current moment."""
    current_price: Decimal
    entry_price: Decimal
    stop_loss: Decimal
    is_long: bool
    bars_since_entry: int
    highest_price: Decimal  # For long positions
    lowest_price: Decimal   # For short positions
    
    # TP tracking
    tp_levels_hit: List[int] = field(default_factory=list)  # Indices of hit TP levels
    remaining_size_pct: Decimal = Decimal("100")  # Percentage still open
    
    # P&L tracking
    unrealized_pnl_r: Decimal = Decimal("0")  # Current P&L in R multiples
    max_unrealized_pnl_r: Decimal = Decimal("0")  # Maximum P&L achieved
    
    def calculate_current_r(self) -> Decimal:
        """Calculate current R multiple (profit in terms of risk)."""
        risk = abs(self.entry_price - self.stop_loss)
        if risk == 0:
            return Decimal("0")
        
        if self.is_long:
            pnl = self.current_price - self.entry_price
        else:
            pnl = self.entry_price - self.current_price
        
        return pnl / risk


class PositionStateMachine:
    """
    Finite State Machine for position lifecycle management.
    
    Manages state transitions based on:
    - Entry confirmation (minimum bars)
    - Breakeven triggers (price reaches threshold)
    - Trailing stop activation (price reaches threshold)
    - Partial closures (TP levels hit)
    - Exit conditions
    
    All behavior controlled by FSMConfig.
    """
    
    def __init__(self, config: FSMConfig):
        """
        Initialize state machine.
        
        Args:
            config: FSM configuration
        """
        self.config = config
        self.current_state = PositionState.ENTRY_CONFIRMATION
        self.history: List[StateTransition] = []
        
        logger.info(
            f"PositionStateMachine initialized in state: {self.current_state.value}"
        )
    
    def update(self, snapshot: PositionSnapshot) -> Optional[StateTransition]:
        """
        Update state based on current position snapshot.
        
        Args:
            snapshot: Current position state
        
        Returns:
            StateTransition if state changed, None otherwise
        """
        # Calculate current R
        current_r = snapshot.calculate_current_r()
        snapshot.unrealized_pnl_r = current_r
        
        # Update max P&L
        if current_r > snapshot.max_unrealized_pnl_r:
            snapshot.max_unrealized_pnl_r = current_r
        
        # Check state transitions
        transition = None
        
        if self.current_state == PositionState.ENTRY_CONFIRMATION:
            transition = self._check_entry_confirmation(snapshot)
        
        elif self.current_state == PositionState.RUNNING:
            # Check multiple possible transitions
            transition = (
                self._check_breakeven_trigger(snapshot) or
                self._check_trailing_activation(snapshot) or
                self._check_partial_closure(snapshot)
            )
        
        elif self.current_state == PositionState.BREAKEVEN:
            transition = (
                self._check_trailing_activation(snapshot) or
                self._check_partial_closure(snapshot)
            )
        
        elif self.current_state == PositionState.TRAILING:
            transition = self._check_partial_closure(snapshot)
        
        elif self.current_state == PositionState.PARTIAL_CLOSED:
            # Already partially closed, just monitor
            pass
        
        # If transition occurred, record it
        if transition:
            self._record_transition(transition)
            logger.info(
                f"State transition: {transition.from_state.value} → {transition.to_state.value} "
                f"(reason: {transition.reason})"
            )
        
        return transition
    
    def _check_entry_confirmation(self, snapshot: PositionSnapshot) -> Optional[StateTransition]:
        """Check if entry confirmation period is complete."""
        if snapshot.bars_since_entry >= self.config.entry_confirmation_bars:
            return StateTransition(
                from_state=self.current_state,
                to_state=PositionState.RUNNING,
                timestamp=datetime.now(),
                reason=f"Entry confirmed after {snapshot.bars_since_entry} bars",
                metadata={
                    "bars_since_entry": snapshot.bars_since_entry,
                    "required_bars": self.config.entry_confirmation_bars,
                }
            )
        return None
    
    def _check_breakeven_trigger(self, snapshot: PositionSnapshot) -> Optional[StateTransition]:
        """Check if breakeven should be triggered."""
        if not self.config.breakeven_lock_profit_enabled:
            return None
        
        current_r = snapshot.unrealized_pnl_r
        
        # Check if we've reached breakeven trigger
        if current_r >= self.config.running_breakeven_trigger_r:
            return StateTransition(
                from_state=self.current_state,
                to_state=PositionState.BREAKEVEN,
                timestamp=datetime.now(),
                reason=f"Breakeven triggered at {current_r:.2f}R (threshold: {self.config.running_breakeven_trigger_r}R)",
                metadata={
                    "current_r": float(current_r),
                    "trigger_r": float(self.config.running_breakeven_trigger_r),
                    "new_stop_loss": float(snapshot.entry_price),  # Move SL to entry
                }
            )
        return None
    
    def _check_trailing_activation(self, snapshot: PositionSnapshot) -> Optional[StateTransition]:
        """Check if trailing stop should be activated."""
        # Trailing is enabled if activation_r > 0
        if self.config.trailing_activation_r <= 0:
            return None
        
        current_r = snapshot.unrealized_pnl_r
        
        # Check if we've reached trailing activation threshold
        if current_r >= self.config.trailing_activation_r:
            return StateTransition(
                from_state=self.current_state,
                to_state=PositionState.TRAILING,
                timestamp=datetime.now(),
                reason=f"Trailing stop activated at {current_r:.2f}R (threshold: {self.config.trailing_activation_r}R)",
                metadata={
                    "current_r": float(current_r),
                    "activation_r": float(self.config.trailing_activation_r),
                    "trailing_step_bps": float(self.config.trailing_step_bps),
                }
            )
        return None
    
    def _check_partial_closure(self, snapshot: PositionSnapshot) -> Optional[StateTransition]:
        """Check if any TP levels were hit (partial closure)."""
        if not self.config.partial_closed_trail_enabled:
            return None
        
        # Check if position was partially closed (some TP hit)
        if len(snapshot.tp_levels_hit) > 0 and snapshot.remaining_size_pct < Decimal("100"):
            # Only transition if not already in PARTIAL_CLOSED state
            if self.current_state != PositionState.PARTIAL_CLOSED:
                return StateTransition(
                    from_state=self.current_state,
                    to_state=PositionState.PARTIAL_CLOSED,
                    timestamp=datetime.now(),
                    reason=f"Position partially closed: {len(snapshot.tp_levels_hit)} TP levels hit, {snapshot.remaining_size_pct}% remaining",
                    metadata={
                        "tp_levels_hit": snapshot.tp_levels_hit,
                        "remaining_size_pct": float(snapshot.remaining_size_pct),
                        "trail_tighter": self.config.partial_closed_trail_step_bps is not None,
                    }
                )
        return None
    
    def close_position(self, reason: str) -> StateTransition:
        """
        Close position (final state transition).
        
        Args:
            reason: Reason for closure
        
        Returns:
            StateTransition to CLOSED state
        """
        transition = StateTransition(
            from_state=self.current_state,
            to_state=PositionState.CLOSED,
            timestamp=datetime.now(),
            reason=reason,
        )
        
        self._record_transition(transition)
        logger.info(f"Position closed: {reason}")
        
        return transition
    
    def _record_transition(self, transition: StateTransition):
        """Record state transition in history."""
        self.history.append(transition)
        self.current_state = transition.to_state
    
    def get_state(self) -> PositionState:
        """Get current state."""
        return self.current_state
    
    def is_closed(self) -> bool:
        """Check if position is closed."""
        return self.current_state == PositionState.CLOSED
    
    def get_history(self) -> List[StateTransition]:
        """Get full transition history."""
        return self.history.copy()
    
    def get_time_in_state(self) -> Optional[float]:
        """Get time spent in current state (in seconds)."""
        if not self.history:
            return None
        
        last_transition = self.history[-1]
        time_in_state = (datetime.now() - last_transition.timestamp).total_seconds()
        return time_in_state
    
    def calculate_new_stop_loss(
        self,
        snapshot: PositionSnapshot,
    ) -> Optional[Decimal]:
        """
        Calculate new stop loss based on current state.
        
        Args:
            snapshot: Current position snapshot
        
        Returns:
            New stop loss price or None if no adjustment needed
        """
        if self.current_state == PositionState.BREAKEVEN:
            # Move SL to entry (breakeven)
            buffer = snapshot.entry_price * (Decimal(str(self.config.breakeven_buffer_bps)) / Decimal("10000"))
            if snapshot.is_long:
                # For long: SL slightly above entry
                return snapshot.entry_price + buffer
            else:
                # For short: SL slightly below entry
                return snapshot.entry_price - buffer
        
        elif self.current_state == PositionState.TRAILING:
            # Trail stop below/above current price
            trail_distance = snapshot.current_price * (Decimal(str(self.config.trailing_step_bps)) / Decimal("10000"))
            if snapshot.is_long:
                # For long: SL below current price
                return snapshot.current_price - trail_distance
            else:
                # For short: SL above current price
                return snapshot.current_price + trail_distance
        
        elif self.current_state == PositionState.PARTIAL_CLOSED:
            # If configured, trail tighter after partial closure
            if self.config.partial_closed_trail_step_bps is not None:
                tighter_distance = snapshot.current_price * (Decimal(str(self.config.partial_closed_trail_step_bps)) / Decimal("10000"))
                if snapshot.is_long:
                    return snapshot.current_price - tighter_distance
                else:
                    return snapshot.current_price + tighter_distance
        
        # No adjustment needed
        return None
    
    def should_update_stop_loss(self, snapshot: PositionSnapshot, current_sl: Decimal) -> bool:
        """
        Check if stop loss should be updated.
        
        Args:
            snapshot: Current position snapshot
            current_sl: Current stop loss
        
        Returns:
            True if SL should be updated
        """
        new_sl = self.calculate_new_stop_loss(snapshot)
        
        if new_sl is None:
            return False
        
        # Only update if new SL is better (more favorable)
        if snapshot.is_long:
            # For long: new SL should be higher than current
            return new_sl > current_sl
        else:
            # For short: new SL should be lower than current
            return new_sl < current_sl
