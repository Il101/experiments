"""
ExitRulesChecker: Universal exit condition checker.

This component implements configurable exit logic based on:
1. Failed breakout detection (price returns to breakout level)
2. Activity drop detection (volume/momentum decrease)
3. Weak impulse detection (insufficient movement after breakout)
4. Time-based exits (max hold time, time stops)

All logic is driven by ExitRulesConfig from settings.
"""

from decimal import Decimal
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from datetime import datetime, timedelta
import logging

from ..config.settings import ExitRulesConfig

logger = logging.getLogger(__name__)


@dataclass
class MarketState:
    """Current market state for exit rule evaluation."""
    current_price: Decimal
    current_volume: Decimal
    current_momentum: Decimal  # Price change rate
    bars_since_entry: int
    entry_price: Decimal
    breakout_level: Decimal  # Original breakout level (support/resistance)
    highest_price: Decimal  # For long positions
    lowest_price: Decimal   # For short positions
    entry_time: datetime
    is_long: bool
    
    # Historical data for comparison
    avg_volume_before_entry: Optional[Decimal] = None
    avg_momentum_before_entry: Optional[Decimal] = None


@dataclass
class ExitSignal:
    """Exit signal with reason and metadata."""
    position_id: str
    signal_type: str  # 'stop_loss', 'take_profit', 'time_exit', 'trailing_stop'
    price: float
    reason: str
    urgency: str  # 'immediate', 'normal'
    meta: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class ExitRulesChecker:
    """
    Universal exit rules checker.
    
    Evaluates all configured exit conditions and returns signals
    when any condition is met. All behavior controlled by ExitRulesConfig.
    """
    
    def __init__(self, config: ExitRulesConfig):
        """
        Initialize checker with exit rules config.
        
        Args:
            config: ExitRulesConfig with all exit rule settings
        """
        self.config = config
        
        # Count enabled rules
        enabled_rules = []
        if config.failed_breakout_enabled:
            enabled_rules.append("failed_breakout")
        if config.activity_drop_enabled:
            enabled_rules.append("activity_drop")
        if config.weak_impulse_enabled:
            enabled_rules.append("weak_impulse")
        if config.max_hold_time_hours is not None:
            enabled_rules.append("max_hold_time")
        if config.time_stop_minutes is not None:
            enabled_rules.append("time_stop")
        
        logger.info(
            f"ExitRulesChecker initialized with {len(enabled_rules)} enabled rules: "
            f"{', '.join(enabled_rules)}"
        )
    
    def check_all_rules(
        self,
        market_state: MarketState,
    ) -> List[ExitSignal]:
        """
        Check all enabled exit rules and return triggered signals.
        
        Args:
            market_state: Current market state
        
        Returns:
            List of exit signals (empty if no exits triggered)
        """
        signals = []
        
        # Check each rule if enabled
        if self.config.failed_breakout_enabled:
            signal = self._check_failed_breakout(market_state)
            if signal and signal.should_exit:
                signals.append(signal)
        
        if self.config.activity_drop_enabled:
            signal = self._check_activity_drop(market_state)
            if signal and signal.should_exit:
                signals.append(signal)
        
        if self.config.weak_impulse_enabled:
            signal = self._check_weak_impulse(market_state)
            if signal and signal.should_exit:
                signals.append(signal)
        
        # Time-based exits
        if self.config.max_hold_time_hours is not None:
            signal = self._check_max_hold_time(market_state)
            if signal and signal.should_exit:
                signals.append(signal)
        
        if self.config.time_stop_minutes is not None:
            signal = self._check_time_stop(market_state)
            if signal and signal.should_exit:
                signals.append(signal)
        
        if signals:
            logger.info(
                f"Exit signals triggered: {[s.rule_name for s in signals]}"
            )
        
        return signals
    
    def _check_failed_breakout(self, state: MarketState) -> Optional[ExitSignal]:
        """
        Check for failed breakout (price returning to breakout level).
        
        Logic:
        - For LONG: price drops back to or below breakout level
        - For SHORT: price rises back to or above breakout level
        - Only check after configured number of bars
        - Use retest threshold to determine if level was truly retested
        """
        # Wait for minimum bars
        if state.bars_since_entry < self.config.failed_breakout_bars:
            return None
        
        # Calculate distance to breakout level as % of entry price
        distance_to_level = abs(state.current_price - state.breakout_level)
        distance_pct = float(distance_to_level / state.entry_price)
        
        # Check if price is retesting the level
        is_retesting = distance_pct <= self.config.failed_breakout_retest_threshold
        
        failed = False
        reason = ""
        
        if state.is_long:
            # For long: failed if price dropped back to/below breakout level
            if state.current_price <= state.breakout_level:
                failed = True
                reason = (
                    f"Failed breakout (LONG): price {state.current_price} dropped to/below "
                    f"breakout level {state.breakout_level}"
                )
        else:
            # For short: failed if price rose back to/above breakout level
            if state.current_price >= state.breakout_level:
                failed = True
                reason = (
                    f"Failed breakout (SHORT): price {state.current_price} rose to/above "
                    f"breakout level {state.breakout_level}"
                )
        
        if not failed and is_retesting:
            # Price is close to level but hasn't crossed yet - warn
            logger.warning(
                f"Price approaching breakout level: {state.current_price} vs {state.breakout_level} "
                f"(distance: {distance_pct:.2%})"
            )
        
        if failed:
            return ExitSignal(
                should_exit=True,
                rule_name="failed_breakout",
                reason=reason,
                urgency="immediate",
                confidence=0.9,
                metadata={
                    "current_price": float(state.current_price),
                    "breakout_level": float(state.breakout_level),
                    "bars_since_entry": state.bars_since_entry,
                }
            )
        
        return None
    
    def _check_activity_drop(self, state: MarketState) -> Optional[ExitSignal]:
        """
        Check for activity drop (volume and momentum decrease).
        
        Logic:
        - Compare current volume to pre-entry average
        - Compare current momentum to pre-entry average
        - If both drop below threshold -> exit signal
        """
        # Need historical data for comparison
        if state.avg_volume_before_entry is None or state.avg_momentum_before_entry is None:
            return None
        
        # Wait for minimum bars
        if state.bars_since_entry < self.config.activity_drop_window_bars:
            return None
        
        # Calculate volume ratio
        volume_ratio = float(state.current_volume / state.avg_volume_before_entry) if state.avg_volume_before_entry > 0 else 1.0
        
        # Calculate momentum ratio
        momentum_ratio = float(state.current_momentum / state.avg_momentum_before_entry) if state.avg_momentum_before_entry > 0 else 1.0
        
        # Check if activity dropped below threshold
        activity_dropped = (
            volume_ratio < self.config.activity_drop_threshold or
            momentum_ratio < self.config.activity_drop_threshold
        )
        
        if activity_dropped:
            reason = (
                f"Activity drop detected: volume ratio {volume_ratio:.2f} "
                f"(threshold: {self.config.activity_drop_threshold}), "
                f"momentum ratio {momentum_ratio:.2f}"
            )
            
            # Calculate confidence based on how far below threshold
            min_ratio = min(volume_ratio, momentum_ratio)
            confidence = 0.5 + (0.5 * (1.0 - min_ratio / self.config.activity_drop_threshold))
            confidence = min(confidence, 0.95)
            
            return ExitSignal(
                should_exit=True,
                rule_name="activity_drop",
                reason=reason,
                urgency="normal",
                confidence=confidence,
                metadata={
                    "volume_ratio": volume_ratio,
                    "momentum_ratio": momentum_ratio,
                    "threshold": self.config.activity_drop_threshold,
                }
            )
        
        return None
    
    def _check_weak_impulse(self, state: MarketState) -> Optional[ExitSignal]:
        """
        Check for weak impulse (insufficient movement after breakout).
        
        Logic:
        - For LONG: check if price moved up enough from entry
        - For SHORT: check if price moved down enough from entry
        - Compare movement to configured minimum percentage
        """
        # Wait for minimum bars
        if state.bars_since_entry < self.config.weak_impulse_check_bars:
            return None
        
        # Calculate actual movement from entry
        if state.is_long:
            # For long: use highest price achieved
            move_distance = state.highest_price - state.entry_price
        else:
            # For short: use lowest price achieved
            move_distance = state.entry_price - state.lowest_price
        
        # Calculate movement as percentage of entry price
        move_pct = float(move_distance / state.entry_price) * 100
        
        # Check if movement is below minimum
        weak_impulse = move_pct < self.config.weak_impulse_min_move_pct
        
        if weak_impulse:
            reason = (
                f"Weak impulse: only {move_pct:.2f}% movement after {state.bars_since_entry} bars "
                f"(minimum required: {self.config.weak_impulse_min_move_pct}%)"
            )
            
            # Calculate confidence: further below minimum = higher confidence
            confidence = 0.6 + (0.3 * (1.0 - move_pct / self.config.weak_impulse_min_move_pct))
            confidence = min(confidence, 0.9)
            
            return ExitSignal(
                should_exit=True,
                rule_name="weak_impulse",
                reason=reason,
                urgency="normal",
                confidence=confidence,
                metadata={
                    "move_pct": move_pct,
                    "min_required_pct": self.config.weak_impulse_min_move_pct,
                    "bars_since_entry": state.bars_since_entry,
                    "highest_price": float(state.highest_price) if state.is_long else None,
                    "lowest_price": float(state.lowest_price) if not state.is_long else None,
                }
            )
        
        return None
    
    def _check_max_hold_time(self, state: MarketState) -> Optional[ExitSignal]:
        """
        Check if maximum hold time exceeded.
        
        Logic:
        - Calculate time since entry
        - If exceeds configured max hold time -> exit
        """
        time_held = datetime.now() - state.entry_time
        max_hold = timedelta(hours=self.config.max_hold_time_hours)
        
        if time_held >= max_hold:
            reason = (
                f"Maximum hold time reached: {time_held.total_seconds() / 3600:.1f} hours "
                f"(limit: {self.config.max_hold_time_hours} hours)"
            )
            
            return ExitSignal(
                should_exit=True,
                rule_name="max_hold_time",
                reason=reason,
                urgency="normal",
                confidence=1.0,  # Time-based is certain
                metadata={
                    "time_held_hours": time_held.total_seconds() / 3600,
                    "max_hold_hours": self.config.max_hold_time_hours,
                }
            )
        
        return None
    
    def _check_time_stop(self, state: MarketState) -> Optional[ExitSignal]:
        """
        Check if time stop triggered (early exit based on time).
        
        Logic:
        - If position not profitable after X minutes -> exit
        - This is a "stop wasting time" rule
        """
        time_held = datetime.now() - state.entry_time
        time_stop = timedelta(minutes=self.config.time_stop_minutes)
        
        if time_held >= time_stop:
            # Check if position is profitable
            if state.is_long:
                is_profitable = state.current_price > state.entry_price
            else:
                is_profitable = state.current_price < state.entry_price
            
            if not is_profitable:
                reason = (
                    f"Time stop triggered: not profitable after {time_held.total_seconds() / 60:.1f} minutes "
                    f"(limit: {self.config.time_stop_minutes} minutes)"
                )
                
                return ExitSignal(
                    should_exit=True,
                    rule_name="time_stop",
                    reason=reason,
                    urgency="low",
                    confidence=0.7,
                    metadata={
                        "time_held_minutes": time_held.total_seconds() / 60,
                        "time_stop_minutes": self.config.time_stop_minutes,
                        "is_profitable": is_profitable,
                    }
                )
        
        return None
    
    def get_highest_priority_signal(self, signals: List[ExitSignal]) -> Optional[ExitSignal]:
        """
        Get highest priority exit signal from list.
        
        Priority order:
        1. Immediate urgency signals
        2. Highest confidence among same urgency
        3. First signal if tied
        
        Args:
            signals: List of exit signals
        
        Returns:
            Highest priority signal or None if list empty
        """
        if not signals:
            return None
        
        # Sort by urgency (immediate > normal > low) then by confidence (high > low)
        urgency_order = {"immediate": 3, "normal": 2, "low": 1}
        
        sorted_signals = sorted(
            signals,
            key=lambda s: (urgency_order.get(s.urgency, 0), s.confidence),
            reverse=True,
        )
        
        return sorted_signals[0]
    
    def should_exit(self, market_state: MarketState) -> tuple[bool, Optional[ExitSignal]]:
        """
        Convenience method: check if should exit and return highest priority signal.
        
        Args:
            market_state: Current market state
        
        Returns:
            (should_exit, signal) tuple
        """
        signals = self.check_all_rules(market_state)
        
        if not signals:
            return False, None
        
        priority_signal = self.get_highest_priority_signal(signals)
        return True, priority_signal
