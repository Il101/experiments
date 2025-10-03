"""
TakeProfitOptimizer: Smart Take Profit placement with density zone and SR level avoidance.

This component implements intelligent TP placement based on:
1. Base TP levels from config (reward multiples in R)
2. Density zone detection and avoidance (high volume areas that can reject price)
3. S/R level detection and avoidance (psychological levels that can cause rejection)
4. Smart placement: nudge TP before problematic zones if configured

All logic is driven by TakeProfitLevel and TakeProfitSmartPlacement configs.
"""

from decimal import Decimal
from typing import List, Optional, Tuple
from dataclasses import dataclass
import logging

from ..config.settings import (
    TakeProfitLevel,
    TakeProfitSmartPlacement,
    PositionConfig,
)

logger = logging.getLogger(__name__)


@dataclass
class DensityZone:
    """Represents a density zone (high volume area in orderbook/historical data)."""
    price_start: Decimal
    price_end: Decimal
    volume: Decimal  # Total volume in this zone
    strength: float  # Normalized strength 0-1 (1 = highest volume zone)
    
    def contains(self, price: Decimal) -> bool:
        """Check if price falls within this density zone."""
        return self.price_start <= price <= self.price_end
    
    def distance_to(self, price: Decimal) -> Decimal:
        """Calculate distance from price to nearest zone boundary."""
        if price < self.price_start:
            return self.price_start - price
        elif price > self.price_end:
            return price - self.price_end
        else:
            return Decimal(0)  # Price is inside zone


@dataclass
class SRLevel:
    """Represents a Support/Resistance level."""
    price: Decimal
    touches: int  # Number of times price touched this level
    last_touch_bars_ago: int  # Recency of last touch
    strength: float  # Normalized strength 0-1 based on touches and recency
    
    def distance_to(self, price: Decimal) -> Decimal:
        """Calculate distance from price to SR level."""
        return abs(price - self.price)


@dataclass
class OptimizedTPLevel:
    """Result of TP optimization."""
    level_index: int  # Original level index (0, 1, 2...)
    original_price: Decimal  # Original TP price from config
    optimized_price: Decimal  # Final optimized price
    size_percent: Decimal  # Size to close at this level
    reward_multiple: Decimal  # R multiple (1.0 = 1R, 2.0 = 2R, etc.)
    was_adjusted: bool  # Whether price was nudged
    adjustment_reason: Optional[str] = None  # Why it was adjusted


class TakeProfitOptimizer:
    """
    Smart Take Profit optimizer.
    
    Takes base TP levels from config and optimizes them based on:
    - Density zones from Level 2 data / volume profile
    - Support/Resistance levels from historical price action
    
    All behavior is controlled by TakeProfitSmartPlacement config.
    """
    
    def __init__(
        self,
        position_config: PositionConfig,
        smart_placement: Optional[TakeProfitSmartPlacement] = None,
    ):
        """
        Initialize optimizer.
        
        Args:
            position_config: Position configuration with TP levels
            smart_placement: Smart placement settings (if None, uses position_config.tp_smart_placement)
        """
        self.position_config = position_config
        # Use provided smart_placement or fall back to position_config's setting
        self.smart_placement = smart_placement if smart_placement is not None else position_config.tp_smart_placement
        
        # Validate config
        if not position_config.tp_levels:
            raise ValueError("PositionConfig must have at least one TP level")
        
        logger.info(
            f"TakeProfitOptimizer initialized with {len(position_config.tp_levels)} TP levels, "
            f"smart_placement={'enabled' if self.smart_placement and self.smart_placement.enabled else 'disabled'}"
        )
    
    def optimize(
        self,
        entry_price: Decimal,
        stop_loss: Decimal,
        is_long: bool,
        density_zones: Optional[List[DensityZone]] = None,
        sr_levels: Optional[List[SRLevel]] = None,
    ) -> List[OptimizedTPLevel]:
        """
        Optimize TP levels based on market microstructure.
        
        Args:
            entry_price: Position entry price
            stop_loss: Stop loss price
            is_long: True if long position, False if short
            density_zones: List of detected density zones (optional)
            sr_levels: List of detected S/R levels (optional)
        
        Returns:
            List of optimized TP levels sorted by price
        """
        # Calculate risk (distance from entry to SL)
        risk = abs(entry_price - stop_loss)
        
        if risk == 0:
            raise ValueError("Risk (entry - stop_loss) cannot be zero")
        
        # Generate base TP levels from config
        base_levels = self._generate_base_levels(entry_price, risk, is_long)
        
        # If smart placement is disabled or no zones/levels provided, return base levels
        if not self.smart_placement or (not density_zones and not sr_levels):
            logger.debug("Smart placement disabled or no zones/levels provided, using base TP levels")
            return base_levels
        
        # Optimize each TP level
        optimized_levels = []
        for base_level in base_levels:
            optimized = self._optimize_single_level(
                base_level=base_level,
                is_long=is_long,
                density_zones=density_zones or [],
                sr_levels=sr_levels or [],
            )
            optimized_levels.append(optimized)
        
        # Log optimization summary
        adjusted_count = sum(1 for level in optimized_levels if level.was_adjusted)
        logger.info(
            f"TP optimization complete: {adjusted_count}/{len(optimized_levels)} levels adjusted"
        )
        
        return optimized_levels
    
    def _generate_base_levels(
        self,
        entry_price: Decimal,
        risk: Decimal,
        is_long: bool,
    ) -> List[OptimizedTPLevel]:
        """Generate base TP levels from config without optimization."""
        base_levels = []
        
        for i, tp_config in enumerate(self.position_config.tp_levels):
            # Calculate TP price: entry + (R * reward_multiple) for long
            # or entry - (R * reward_multiple) for short
            reward_distance = risk * Decimal(str(tp_config.reward_multiple))
            
            if is_long:
                tp_price = entry_price + reward_distance
            else:
                tp_price = entry_price - reward_distance
            
            # Convert size_pct (0.0-1.0) to percent (0-100)
            size_percent = Decimal(str(tp_config.size_pct * 100))
            
            base_level = OptimizedTPLevel(
                level_index=i,
                original_price=tp_price,
                optimized_price=tp_price,
                size_percent=size_percent,
                reward_multiple=Decimal(str(tp_config.reward_multiple)),
                was_adjusted=False,
            )
            base_levels.append(base_level)
        
        return base_levels
    
    def _optimize_single_level(
        self,
        base_level: OptimizedTPLevel,
        is_long: bool,
        density_zones: List[DensityZone],
        sr_levels: List[SRLevel],
    ) -> OptimizedTPLevel:
        """
        Optimize a single TP level.
        
        Logic:
        1. Check if TP falls into density zone or near SR level
        2. If yes and avoidance is enabled -> nudge TP before the zone
        3. Buffer is defined in config (density_zone_buffer_bps, sr_level_buffer_bps)
        """
        original_price = base_level.original_price
        optimized_price = original_price
        was_adjusted = False
        adjustment_reason = None
        
        # Check density zones
        if self.smart_placement and self.smart_placement.enabled and self.smart_placement.avoid_density_zones and density_zones:
            for zone in density_zones:
                if zone.contains(original_price):
                    # TP is inside density zone - nudge it before the zone
                    buffer_bps = self.smart_placement.density_zone_buffer_bps if self.smart_placement else 10.0
                    buffer_amount = original_price * (Decimal(str(buffer_bps)) / Decimal(10000))
                    
                    if is_long:
                        # For long, nudge TP down (before resistance)
                        optimized_price = zone.price_start - buffer_amount
                    else:
                        # For short, nudge TP up (before support)
                        optimized_price = zone.price_end + buffer_amount
                    
                    was_adjusted = True
                    adjustment_reason = (
                        f"Density zone avoidance: moved from {original_price} to {optimized_price} "
                        f"(zone: {zone.price_start}-{zone.price_end}, strength: {zone.strength:.2f})"
                    )
                    logger.debug(adjustment_reason)
                    break  # Only adjust for first conflicting zone
        
        # Check S/R levels (if not already adjusted)
        if not was_adjusted and self.smart_placement and self.smart_placement.enabled and self.smart_placement.avoid_sr_levels and sr_levels:
            for sr in sr_levels:
                distance = sr.distance_to(original_price)
                # Check if TP is too close to SR level
                buffer_bps = self.smart_placement.sr_level_buffer_bps if self.smart_placement else 15.0
                threshold = original_price * (Decimal(str(buffer_bps)) / Decimal(10000))
                
                if distance <= threshold:
                    # TP is too close to SR level - nudge it before the level
                    buffer_bps = self.smart_placement.sr_level_buffer_bps if self.smart_placement else 15.0
                    buffer_amount = original_price * (Decimal(str(buffer_bps)) / Decimal(10000))
                    
                    if is_long and original_price > sr.price:
                        # TP is above SR resistance - nudge down
                        optimized_price = sr.price - buffer_amount
                    elif not is_long and original_price < sr.price:
                        # TP is below SR support - nudge up
                        optimized_price = sr.price + buffer_amount
                    else:
                        # TP is on wrong side of SR level, don't adjust
                        continue
                    
                    was_adjusted = True
                    adjustment_reason = (
                        f"SR level avoidance: moved from {original_price} to {optimized_price} "
                        f"(SR: {sr.price}, touches: {sr.touches}, strength: {sr.strength:.2f})"
                    )
                    logger.debug(adjustment_reason)
                    break  # Only adjust for first conflicting SR level
        
        # Create optimized level
        return OptimizedTPLevel(
            level_index=base_level.level_index,
            original_price=original_price,
            optimized_price=optimized_price,
            size_percent=base_level.size_percent,
            reward_multiple=base_level.reward_multiple,
            was_adjusted=was_adjusted,
            adjustment_reason=adjustment_reason,
        )
    
    def calculate_expected_reward(
        self,
        optimized_levels: List[OptimizedTPLevel],
        entry_price: Decimal,
        stop_loss: Decimal,
        is_long: bool,
    ) -> Decimal:
        """
        Calculate expected reward considering partial closures.
        
        Expected Reward = Σ (size_percent * reward_multiple)
        
        Example:
        - TP1: 30% at 2R -> 0.3 * 2 = 0.6R
        - TP2: 40% at 4R -> 0.4 * 4 = 1.6R
        - TP3: 30% at 6R -> 0.3 * 6 = 1.8R
        Total Expected R = 4.0R
        """
        risk = abs(entry_price - stop_loss)
        total_expected_r = Decimal(0)
        
        for level in optimized_levels:
            # Calculate actual reward for this level
            actual_distance = abs(level.optimized_price - entry_price)
            actual_r = actual_distance / risk
            
            # Weight by size percent
            contribution = (level.size_percent / Decimal(100)) * actual_r
            total_expected_r += contribution
        
        return total_expected_r
    
    def validate_levels(self, optimized_levels: List[OptimizedTPLevel], is_long: bool) -> bool:
        """
        Validate that TP levels are in correct order and sizes sum to 100%.
        
        Args:
            optimized_levels: List of optimized TP levels
            is_long: True if long position
        
        Returns:
            True if valid, raises ValueError if invalid
        """
        if not optimized_levels:
            raise ValueError("No TP levels to validate")
        
        # Check total size = 100%
        total_size = sum(level.size_percent for level in optimized_levels)
        if abs(total_size - Decimal(100)) > Decimal("0.01"):
            raise ValueError(f"TP sizes must sum to 100%, got {total_size}%")
        
        # Check prices are in correct order (ascending for long, descending for short)
        sorted_levels = sorted(optimized_levels, key=lambda x: x.optimized_price)
        if not is_long:
            sorted_levels = list(reversed(sorted_levels))
        
        for i, level in enumerate(sorted_levels):
            if level.level_index != i:
                raise ValueError(
                    f"TP levels out of order: expected index {i}, got {level.level_index}"
                )
        
        return True
