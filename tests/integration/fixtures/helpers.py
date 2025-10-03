"""Helper functions for integration testing."""
from decimal import Decimal
from datetime import datetime
from typing import Optional, List
from breakout_bot.strategy.position_state_machine import PositionSnapshot
from breakout_bot.strategy.entry_validator import EntrySignal


def create_position(
    entry_price: Decimal = Decimal("50000"),
    stop_loss: Decimal = Decimal("49000"),
    current_price: Optional[Decimal] = None,
    side: str = "long",
    state: str = "pending",
    entry_time: Optional[datetime] = None,
    bars_since_entry: int = 0,
) -> PositionSnapshot:
    """Create a mock position for testing."""
    if entry_time is None:
        entry_time = datetime.now()
    
    if current_price is None:
        current_price = entry_price
    
    is_long = (side == "long")
    
    return PositionSnapshot(
        current_price=current_price,
        entry_price=entry_price,
        stop_loss=stop_loss,
        is_long=is_long,
        bars_since_entry=bars_since_entry,
        highest_price=max(entry_price, current_price) if is_long else entry_price,
        lowest_price=min(entry_price, current_price) if not is_long else entry_price,
    )


def create_entry_signal(
    breakout_price: Decimal = Decimal("49500"),
    current_price: Decimal = Decimal("50000"),
    entry_price: Decimal = Decimal("50000"),
    stop_loss: Decimal = Decimal("49000"),
    is_long: bool = True,
    breakout_volume: Decimal = Decimal("1200000"),
    avg_volume: Decimal = Decimal("1000000"),
    current_volume: Decimal = Decimal("1100000"),
    price_change_pct: Decimal = Decimal("1.0"),
    bars_since_breakout: int = 2,
    density_zones: Optional[List[tuple[Decimal, Decimal]]] = None,
    sr_levels: Optional[List[Decimal]] = None,
    is_flat: bool = False,
    is_consolidating: bool = False,
    noise_level: Decimal = Decimal("0.2"),
) -> EntrySignal:
    """Create a mock entry signal for testing."""
    if density_zones is None:
        density_zones = []
    if sr_levels is None:
        sr_levels = []
    
    return EntrySignal(
        breakout_price=breakout_price,
        current_price=current_price,
        entry_price=entry_price,
        stop_loss=stop_loss,
        is_long=is_long,
        breakout_volume=breakout_volume,
        avg_volume=avg_volume,
        current_volume=current_volume,
        price_change_pct=price_change_pct,
        bars_since_breakout=bars_since_breakout,
        density_zones=density_zones,
        sr_levels=sr_levels,
        is_flat=is_flat,
        is_consolidating=is_consolidating,
        noise_level=noise_level,
    )


def calculate_risk(entry: Decimal, stop: Decimal) -> Decimal:
    """Calculate risk amount per unit."""
    return abs(entry - stop)


def calculate_position_pnl(
    entry_price: Decimal,
    current_price: Decimal,
    position_size: Decimal,
    side: str,
) -> Decimal:
    """Calculate current P&L for a position."""
    if side == "long":
        return (current_price - entry_price) * position_size
    else:
        return (entry_price - current_price) * position_size


def calculate_r_multiple(
    entry_price: Decimal,
    current_price: Decimal,
    stop_loss: Decimal,
    side: str,
) -> Decimal:
    """Calculate R-multiple (profit in terms of initial risk)."""
    risk = calculate_risk(entry_price, stop_loss)
    if risk == 0:
        return Decimal("0")
    
    pnl = current_price - entry_price if side == "long" else entry_price - current_price
    return pnl / risk


def simulate_price_move(
    current_price: Decimal,
    move_pct: Decimal,
    direction: str = "up",
) -> Decimal:
    """Simulate price movement by percentage."""
    multiplier = Decimal("1") + (move_pct / Decimal("100"))
    if direction == "down":
        multiplier = Decimal("1") - (move_pct / Decimal("100"))
    
    return current_price * multiplier


def create_price_series(
    start_price: Decimal,
    num_bars: int,
    volatility: Decimal = Decimal("0.01"),
) -> List[Decimal]:
    """Create a series of mock prices."""
    prices = [start_price]
    for _ in range(num_bars - 1):
        # Simple random walk
        change = volatility * (Decimal("0.5") if len(prices) % 2 else Decimal("-0.5"))
        next_price = prices[-1] * (Decimal("1") + change)
        prices.append(next_price)
    
    return prices
