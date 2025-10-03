"""Mock market data generators for integration tests."""

from decimal import Decimal
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from dataclasses import dataclass

from breakout_bot.strategy.market_quality_filter import MarketMetrics
from breakout_bot.strategy.entry_validator import EntrySignal
from breakout_bot.strategy.position_state_machine import PositionSnapshot


@dataclass
class PriceBar:
    """Represents a single price bar."""
    timestamp: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal


def create_market_metrics(
    atr: Decimal = Decimal("100"),
    atr_pct: Decimal = Decimal("0.002"),  # 0.2%
    current_price: Decimal = Decimal("50000"),
    price_range_pct: Decimal = Decimal("0.02"),  # 2%
    consolidation_bars: int = 0,
    trend_slope_pct: Decimal = Decimal("0.01"),  # 1% per bar
    trend_strength: Decimal = Decimal("0.7"),
    noise_level: Decimal = Decimal("0.3"),
    volatility_spike: bool = False,
) -> MarketMetrics:
    """
    Create mock MarketMetrics for testing.
    
    Args:
        atr: Average True Range
        atr_pct: ATR as percentage of price
        current_price: Current market price
        price_range_pct: Price range as percentage
        consolidation_bars: Number of consolidation bars
        trend_slope_pct: Slope of trend per bar (percentage)
        trend_strength: Trend strength (0-1)
        noise_level: Market noise level (0-1)
        volatility_spike: Whether volatility spike detected
    
    Returns:
        MarketMetrics instance
    """
    return MarketMetrics(
        atr=atr,
        atr_pct=atr_pct,
        current_price=current_price,
        price_range_pct=price_range_pct,
        consolidation_bars=consolidation_bars,
        trend_slope_pct=trend_slope_pct,
        trend_strength=trend_strength,
        noise_level=noise_level,
        volatility_spike=volatility_spike,
    )


def create_price_data(
    start_price: Decimal = Decimal("50000"),
    num_bars: int = 100,
    trend: str = "up",  # "up", "down", "flat", "choppy"
    volatility: str = "normal",  # "low", "normal", "high"
    base_volume: Decimal = Decimal("1000000"),
) -> List[PriceBar]:
    """
    Generate mock price bar data.
    
    Args:
        start_price: Starting price
        num_bars: Number of bars to generate
        trend: Type of trend (up/down/flat/choppy)
        volatility: Volatility level
        base_volume: Base trading volume
    
    Returns:
        List of PriceBar objects
    """
    bars = []
    current_price = start_price
    current_time = datetime.now()
    
    # Volatility multipliers
    vol_multipliers = {
        "low": Decimal("0.001"),
        "normal": Decimal("0.005"),
        "high": Decimal("0.02"),
    }
    vol_mult = vol_multipliers.get(volatility, vol_multipliers["normal"])
    
    for i in range(num_bars):
        # Trend adjustment
        if trend == "up":
            trend_adjustment = vol_mult * Decimal("2")
        elif trend == "down":
            trend_adjustment = -vol_mult * Decimal("2")
        elif trend == "choppy":
            trend_adjustment = vol_mult * (Decimal("1") if i % 2 == 0 else Decimal("-1"))
        else:  # flat
            trend_adjustment = Decimal("0")
        
        # Calculate OHLC
        open_price = current_price
        high_price = current_price * (Decimal("1") + vol_mult)
        low_price = current_price * (Decimal("1") - vol_mult)
        close_price = current_price * (Decimal("1") + trend_adjustment)
        
        # Volume variation
        volume = base_volume * (Decimal("0.8") + Decimal("0.4") * Decimal(str(i % 10 / 10)))
        
        bar = PriceBar(
            timestamp=current_time + timedelta(minutes=i),
            open=open_price,
            high=high_price,
            low=low_price,
            close=close_price,
            volume=volume,
        )
        bars.append(bar)
        
        current_price = close_price
        current_time = bar.timestamp
    
    return bars


def create_density_zones(
    current_price: Decimal = Decimal("50000"),
    num_zones: int = 3,
    distance_multiplier: Decimal = Decimal("1.0"),
) -> List[Dict[str, Decimal]]:
    """
    Create mock density zones.
    
    Args:
        current_price: Current market price
        num_zones: Number of zones to create
        distance_multiplier: Distance from current price (in ATR)
    
    Returns:
        List of density zone dictionaries
    """
    zones = []
    base_distance = current_price * Decimal("0.02") * distance_multiplier
    
    for i in range(num_zones):
        zone_center = current_price + (base_distance * Decimal(str(i + 1)))
        zone_width = current_price * Decimal("0.005")
        
        zones.append({
            "level": zone_center,
            "lower": zone_center - zone_width,
            "upper": zone_center + zone_width,
            "strength": Decimal("0.7"),
            "touches": 5 + i,
        })
    
    return zones


def create_trending_market() -> MarketMetrics:
    """Create metrics for a trending market (good quality)."""
    return create_market_metrics(
        atr=Decimal("1000"),  # High ATR
        atr_pct=Decimal("0.5"),  # > 0.3 threshold
        volatility_spike=False,
        price_range_pct=Decimal("1.2"),  # Wide range
        consolidation_bars=0,
        trend_slope_pct=Decimal("0.4"),  # Strong trend
        trend_strength=Decimal("0.8"),  # Strong
        noise_level=Decimal("0.3"),  # Low noise
        current_price=Decimal("50000"),
    )


def create_flat_market() -> MarketMetrics:
    """Create metrics for a flat market (bad for entries)."""
    return create_market_metrics(
        atr=Decimal("20"),  # Low ATR
        atr_pct=Decimal("0.0004"),  # 0.04% - very low
        current_price=Decimal("50000"),
        price_range_pct=Decimal("0.005"),  # Narrow range - 0.5%
        consolidation_bars=0,
        trend_slope_pct=Decimal("0.001"),  # No trend
        trend_strength=Decimal("0.1"),  # Weak trend
        noise_level=Decimal("0.5"),  # Moderate noise
        volatility_spike=False,
    )


def create_choppy_market() -> MarketMetrics:
    """Create metrics for a choppy/noisy market (bad for entries)."""
    return create_market_metrics(
        atr=Decimal("150"),
        atr_pct=Decimal("0.003"),  # 0.3% - elevated
        current_price=Decimal("50000"),
        price_range_pct=Decimal("0.02"),
        consolidation_bars=0,
        trend_slope_pct=Decimal("0.005"),  # Weak trend
        trend_strength=Decimal("0.3"),  # Poor trend
        noise_level=Decimal("0.8"),  # High noise
        volatility_spike=False,
    )


def create_volatile_market() -> MarketMetrics:
    """Create metrics for a volatile market (volatility spike)."""
    return create_market_metrics(
        atr=Decimal("200"),
        atr_pct=Decimal("0.004"),  # 0.4% - high
        current_price=Decimal("50000"),
        price_range_pct=Decimal("0.04"),
        consolidation_bars=0,
        trend_slope_pct=Decimal("0.01"),
        trend_strength=Decimal("0.6"),
        noise_level=Decimal("0.4"),
        volatility_spike=True,  # Volatility spike detected
    )


__all__ = [
    "PriceBar",
    "create_market_metrics",
    "create_price_data",
    "create_density_zones",
    "create_trending_market",
    "create_flat_market",
    "create_choppy_market",
    "create_volatile_market",
]
