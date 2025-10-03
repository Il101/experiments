"""
Strategy components for config-driven trading logic.

This module contains universal, reusable strategy components that are fully
controlled by configuration objects. Each component is designed to work with
presets and provides no hardcoded business logic.

Components:
- TakeProfitOptimizer: Smart TP placement with density/SR level avoidance
- ExitRulesChecker: Universal exit condition checker (failed breakout, weak impulse, etc.)
- PositionStateMachine: FSM for position state management (entry -> running -> partial_closed -> closed)
- EntryValidator: Multi-factor entry confirmation (volume, density, momentum)
- MarketQualityFilter: Market condition filters (flat, consolidation, noise)

All components are config-driven and testable.
"""

from .takeprofit_optimizer import TakeProfitOptimizer
from .exit_rules_checker import ExitRulesChecker
from .position_state_machine import PositionStateMachine, PositionState, PositionSnapshot
from .entry_validator import EntryValidator, EntrySignal, ValidationReport
from .market_quality_filter import MarketQualityFilter, MarketMetrics, MarketCondition, FilterResult

__all__ = [
    "TakeProfitOptimizer",
    "ExitRulesChecker",
    "PositionStateMachine",
    "PositionState",
    "PositionSnapshot",
    "EntryValidator",
    "EntrySignal",
    "ValidationReport",
    "MarketQualityFilter",
    "MarketMetrics",
    "MarketCondition",
    "FilterResult",
]
