"""
Density Detection for order book concentration analysis.

Detects significant liquidity concentrations (walls) and tracks their consumption.
"""

import logging
import time
from collections import deque
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
import numpy as np

from ..data.streams.orderbook_ws import OrderBookManager, OrderBookSnapshot


logger = logging.getLogger(__name__)


@dataclass
class DensityLevel:
    """Detected density level in order book."""
    price: float
    side: str  # 'bid' or 'ask'
    size: float
    strength: float  # Relative strength vs median
    timestamp: int
    initial_size: float  # Size when first detected
    
    @property
    def eaten_ratio(self) -> float:
        """Ratio of density that has been consumed."""
        if self.initial_size <= 0:
            return 0.0
        return 1.0 - (self.size / self.initial_size)


@dataclass
class DensityEvent:
    """Event triggered by density changes."""
    event_type: str  # 'detected', 'eaten', 'refreshed', 'removed'
    symbol: str
    density: DensityLevel
    timestamp: int


class DensityDetector:
    """
    Detects and tracks liquidity density in order book.
    
    Key features:
    - Detects walls (large orders)
    - Tracks consumption of density
    - Alerts when density is eaten significantly
    """
    
    def __init__(
        self,
        orderbook_manager: OrderBookManager,
        k_density: float = 7.0,
        bucket_ticks: int = 3,
        lookback_window_s: int = 300,
        enter_on_density_eat_ratio: float = 0.75
    ):
        """
        Initialize density detector.
        
        Args:
            orderbook_manager: OrderBook WebSocket manager
            k_density: Multiplier for density threshold (size >= k × median)
            bucket_ticks: Number of ticks to aggregate into bucket
            lookback_window_s: Lookback window for median calculation
            enter_on_density_eat_ratio: Ratio of eaten density to trigger event
        """
        self.orderbook_manager = orderbook_manager
        self.k_density = k_density
        self.bucket_ticks = bucket_ticks
        self.lookback_window_s = lookback_window_s
        self.enter_on_density_eat_ratio = enter_on_density_eat_ratio
        
        # Tracked densities by symbol
        self.densities: Dict[str, List[DensityLevel]] = {}
        
        # Historical bucket sizes for median calculation
        self.bucket_history: Dict[str, deque] = {}
        
        logger.info(
            f"DensityDetector initialized: k={k_density}, "
            f"bucket_ticks={bucket_ticks}, eat_ratio={enter_on_density_eat_ratio}"
        )
    
    def detect_densities(
        self,
        symbol: str,
        range_bps: float = 50
    ) -> List[DensityLevel]:
        """
        Detect current density levels in order book.
        
        Args:
            symbol: Trading pair symbol
            range_bps: Price range to scan in basis points
        
        Returns:
            List of detected density levels
        """
        snapshot = self.orderbook_manager.get_snapshot(symbol)
        if not snapshot or not snapshot.mid_price:
            return []
        
        current_ts = int(time.time() * 1000)
        mid_price = snapshot.mid_price
        
        # Calculate buckets for both sides
        bid_buckets = self._aggregate_to_buckets(snapshot.bids, mid_price, 'bid', range_bps)
        ask_buckets = self._aggregate_to_buckets(snapshot.asks, mid_price, 'ask', range_bps)
        
        # Update historical bucket sizes
        if symbol not in self.bucket_history:
            self.bucket_history[symbol] = deque(maxlen=self.lookback_window_s)
        
        all_bucket_sizes = [size for _, size in bid_buckets + ask_buckets]
        if all_bucket_sizes:
            self.bucket_history[symbol].append((current_ts, all_bucket_sizes))
        
        # Calculate threshold
        threshold = self._calculate_density_threshold(symbol)
        
        # Detect densities
        densities = []
        
        for price, size in bid_buckets:
            if size >= threshold:
                strength = size / threshold if threshold > 0 else 1.0
                densities.append(DensityLevel(
                    price=price,
                    side='bid',
                    size=size,
                    strength=strength,
                    timestamp=current_ts,
                    initial_size=size
                ))
        
        for price, size in ask_buckets:
            if size >= threshold:
                strength = size / threshold if threshold > 0 else 1.0
                densities.append(DensityLevel(
                    price=price,
                    side='ask',
                    size=size,
                    strength=strength,
                    timestamp=current_ts,
                    initial_size=size
                ))
        
        return densities
    
    def _aggregate_to_buckets(
        self,
        levels: List,
        mid_price: float,
        side: str,
        range_bps: float
    ) -> List[Tuple[float, float]]:
        """
        Aggregate order book levels into price buckets.
        
        Returns list of (bucket_price, total_size) tuples.
        """
        if not levels:
            return []
        
        # Calculate bucket size based on price and ticks
        # Assume 1 tick = 0.01% for crypto
        tick_size = mid_price * 0.0001
        bucket_size = tick_size * self.bucket_ticks
        
        # Determine price range
        if side == 'bid':
            price_limit = mid_price * (1 - range_bps / 10000)
        else:
            price_limit = mid_price * (1 + range_bps / 10000)
        
        # Group levels into buckets
        buckets: Dict[float, float] = {}
        
        for level in levels:
            if side == 'bid':
                if level.price < price_limit:
                    break
            else:
                if level.price > price_limit:
                    break
            
            # Calculate bucket
            bucket_price = round(level.price / bucket_size) * bucket_size
            buckets[bucket_price] = buckets.get(bucket_price, 0.0) + level.size
        
        # Return sorted buckets
        return sorted(buckets.items(), reverse=(side == 'bid'))
    
    def _calculate_density_threshold(self, symbol: str) -> float:
        """
        Calculate density detection threshold.
        
        Returns k × median(bucket_sizes) over lookback window.
        """
        if symbol not in self.bucket_history or not self.bucket_history[symbol]:
            return 0.0
        
        # Collect all bucket sizes from lookback window
        current_ts = int(time.time() * 1000)
        cutoff_ts = current_ts - (self.lookback_window_s * 1000)
        
        all_sizes = []
        for ts, sizes in self.bucket_history[symbol]:
            if ts >= cutoff_ts:
                all_sizes.extend(sizes)
        
        if not all_sizes:
            return 0.0
        
        median_size = np.median(all_sizes)
        return median_size * self.k_density
    
    def update_tracked_densities(self, symbol: str) -> List[DensityEvent]:
        """
        Update tracked densities and detect changes.
        
        Returns list of density events (eaten, refreshed, removed).
        """
        current_densities = self.detect_densities(symbol)
        previous_densities = self.densities.get(symbol, [])
        
        events = []
        current_ts = int(time.time() * 1000)
        
        # Match previous densities with current ones
        updated_densities = []
        
        for prev_density in previous_densities:
            # Find matching density (same price and side)
            matched = None
            for curr_density in current_densities:
                if (abs(curr_density.price - prev_density.price) / prev_density.price < 0.001 and
                    curr_density.side == prev_density.side):
                    matched = curr_density
                    break
            
            if matched:
                # Update existing density
                matched.initial_size = prev_density.initial_size
                updated_densities.append(matched)
                
                # Check if eaten significantly
                if matched.eaten_ratio >= self.enter_on_density_eat_ratio:
                    events.append(DensityEvent(
                        event_type='eaten',
                        symbol=symbol,
                        density=matched,
                        timestamp=current_ts
                    ))
                    logger.info(
                        f"Density eaten on {symbol}: {matched.side} @ {matched.price:.4f}, "
                        f"eaten_ratio={matched.eaten_ratio:.2f}"
                    )
            else:
                # Density removed
                events.append(DensityEvent(
                    event_type='removed',
                    symbol=symbol,
                    density=prev_density,
                    timestamp=current_ts
                ))
        
        # Add new densities
        for curr_density in current_densities:
            is_new = True
            for prev_density in previous_densities:
                if (abs(curr_density.price - prev_density.price) / prev_density.price < 0.001 and
                    curr_density.side == prev_density.side):
                    is_new = False
                    break
            
            if is_new:
                updated_densities.append(curr_density)
                events.append(DensityEvent(
                    event_type='detected',
                    symbol=symbol,
                    density=curr_density,
                    timestamp=current_ts
                ))
                logger.info(
                    f"New density detected on {symbol}: {curr_density.side} @ {curr_density.price:.4f}, "
                    f"strength={curr_density.strength:.2f}"
                )
        
        # Update stored densities
        self.densities[symbol] = updated_densities
        
        return events
    
    def get_densities(self, symbol: str) -> List[DensityLevel]:
        """Get currently tracked densities for a symbol."""
        return self.densities.get(symbol, [])
    
    def get_density_at_price(
        self,
        symbol: str,
        price: float,
        side: str,
        tolerance_bps: float = 10
    ) -> Optional[DensityLevel]:
        """
        Get density at specific price level.
        
        Args:
            symbol: Trading pair symbol
            price: Target price
            side: 'bid' or 'ask'
            tolerance_bps: Price tolerance in basis points
        
        Returns:
            DensityLevel if found, None otherwise
        """
        densities = self.densities.get(symbol, [])
        
        for density in densities:
            if density.side != side:
                continue
            
            price_diff_bps = abs(density.price - price) / price * 10000
            if price_diff_bps <= tolerance_bps:
                return density
        
        return None
