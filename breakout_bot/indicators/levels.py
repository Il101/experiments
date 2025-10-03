"""
Level detection module for identifying support and resistance levels.

This module implements algorithms for detecting and validating trading levels
using various methods including Donchian channels, swing points, and volume analysis.
"""

import logging
import numpy as np
import time
from typing import List, Optional, Tuple, Dict, Any
from dataclasses import dataclass
from ..data.models import Candle, TradingLevel
from .technical import donchian_channels, swing_highs_lows, atr

logger = logging.getLogger(__name__)


@dataclass
class LevelCandidate:
    """Intermediate level candidate before validation."""
    price: float
    level_type: str  # 'support' or 'resistance'
    first_touch_ts: int
    touches: List[Tuple[int, float]]  # (timestamp, touch_price)
    method: str  # Detection method used


class LevelDetector:
    """Level detection system using multiple methods."""
    
    def __init__(self, 
                 min_touches: int = 3,
                 max_pierce_pct: float = 0.002,  # 0.2%
                 min_level_separation_atr: float = 2.0,
                 touch_tolerance_atr: float = 0.5,
                 prefer_round_numbers: bool = True,
                 round_step_candidates: Optional[List[float]] = None,
                 cascade_min_levels: int = 2,
                 cascade_radius_bps: float = 15.0,
                 approach_slope_max_pct_per_bar: float = 1.5,
                 prebreakout_consolidation_min_bars: int = 3):
        """
        Initialize level detector.
        
        Args:
            min_touches: Minimum touches required for valid level
            max_pierce_pct: Maximum price pierce as percentage
            min_level_separation_atr: Minimum separation between levels in ATR
            touch_tolerance_atr: Tolerance for level touches in ATR
            prefer_round_numbers: Give bonus to round number levels
            round_step_candidates: List of round steps (e.g., [0.01, 0.05, 0.10, 1.00, 5.00])
            cascade_min_levels: Minimum levels for cascade detection
            cascade_radius_bps: Radius for cascade detection in basis points
            approach_slope_max_pct_per_bar: Max approach slope to avoid vertical moves
            prebreakout_consolidation_min_bars: Min bars of consolidation before breakout
        """
        self.min_touches = min_touches
        self.max_pierce_pct = max_pierce_pct
        self.min_level_separation_atr = min_level_separation_atr
        self.touch_tolerance_atr = touch_tolerance_atr
        self.prefer_round_numbers = prefer_round_numbers
        self.round_step_candidates = round_step_candidates or [0.01, 0.05, 0.10, 1.00, 5.00, 10.00]
        self.cascade_min_levels = cascade_min_levels
        self.cascade_radius_bps = cascade_radius_bps
        self.approach_slope_max_pct_per_bar = approach_slope_max_pct_per_bar
        self.prebreakout_consolidation_min_bars = prebreakout_consolidation_min_bars
    
    def detect_levels(self, candles: List[Candle]) -> List[TradingLevel]:
        """
        Detect and validate trading levels.
        
        Args:
            candles: List of Candle objects (should be sorted by timestamp)
        
        Returns:
            List of validated TradingLevel objects
        """
        import logging
        logger = logging.getLogger(__name__)
        
        logger.debug(f"Starting level detection with {len(candles)} candles")
        
        if len(candles) < 20:
            logger.debug("Not enough candles for level detection")
            return []
        
        try:
            # Calculate ATR for touch tolerance
            logger.debug("Calculating ATR")
            atr_values = atr(candles, period=14)
            current_atr = atr_values[-1] if not np.isnan(atr_values[-1]) else 0.01
            logger.debug(f"Current ATR: {current_atr}")
            
            # Detect level candidates using multiple methods
            candidates = []
            
            # Method 1: Donchian channel levels
            logger.debug("Detecting Donchian levels")
            donchian_candidates = self._detect_donchian_levels(candles, current_atr)
            candidates.extend(donchian_candidates)
            logger.debug(f"Found {len(donchian_candidates)} Donchian candidates")
            
            # Method 2: Swing point levels
            logger.debug("Detecting swing levels")
            swing_candidates = self._detect_swing_levels(candles, current_atr)
            candidates.extend(swing_candidates)
            logger.debug(f"Found {len(swing_candidates)} swing candidates")
            
            # Method 3: Volume-based levels
            logger.debug("Detecting volume levels")
            volume_candidates = self._detect_volume_levels(candles, current_atr)
            candidates.extend(volume_candidates)
            logger.debug(f"Found {len(volume_candidates)} volume candidates")
            
            logger.debug(f"Total candidates before merging: {len(candidates)}")
            
            # Merge similar levels and validate
            logger.debug("Merging similar levels")
            merged_candidates = self._merge_similar_levels(candidates, current_atr)
            logger.debug(f"Candidates after merging: {len(merged_candidates)}")
            
            logger.debug("Validating levels")
            validated_levels = self._validate_levels(merged_candidates, candles, current_atr)
            logger.debug(f"Final validated levels: {len(validated_levels)}")
            
            return validated_levels
            
        except Exception as e:
            logger.error(f"detect_levels failed: {type(e).__name__}: {str(e)}")
            return []
    
    def _detect_donchian_levels(self, candles: List[Candle], current_atr: float) -> List[LevelCandidate]:
        """Detect levels using Donchian channels."""
        candidates = []
        
        # Try different periods for Donchian channels
        for period in [10, 15, 20, 30]:
            if len(candles) < period:
                continue
                
            upper_channel, lower_channel = donchian_channels(candles, period)
            
            # Find recent Donchian levels
            for i in range(-min(10, len(candles)), 0):  # Look at last 10 periods
                if np.isnan(upper_channel[i]) or np.isnan(lower_channel[i]):
                    continue
                
                timestamp = candles[i].ts
                
                # Add resistance level (upper channel)
                candidates.append(LevelCandidate(
                    price=upper_channel[i],
                    level_type='resistance',
                    first_touch_ts=timestamp,
                    touches=[(timestamp, upper_channel[i])],
                    method=f'donchian_{period}'
                ))
                
                # Add support level (lower channel)
                candidates.append(LevelCandidate(
                    price=lower_channel[i],
                    level_type='support',
                    first_touch_ts=timestamp,
                    touches=[(timestamp, lower_channel[i])],
                    method=f'donchian_{period}'
                ))
        
        return candidates
    
    def _detect_swing_levels(self, candles: List[Candle], current_atr: float) -> List[LevelCandidate]:
        """Detect levels using swing highs and lows."""
        candidates = []
        
        swing_highs, swing_lows = swing_highs_lows(candles, left_bars=2, right_bars=2)
        
        # Process swing highs (resistance levels)
        for i, high_price in enumerate(swing_highs):
            if not np.isnan(high_price):
                candidates.append(LevelCandidate(
                    price=high_price,
                    level_type='resistance',
                    first_touch_ts=candles[i].ts,
                    touches=[(candles[i].ts, high_price)],
                    method='swing_high'
                ))
        
        # Process swing lows (support levels)
        for i, low_price in enumerate(swing_lows):
            if not np.isnan(low_price):
                candidates.append(LevelCandidate(
                    price=low_price,
                    level_type='support',
                    first_touch_ts=candles[i].ts,
                    touches=[(candles[i].ts, low_price)],
                    method='swing_low'
                ))
        
        return candidates
    
    def _detect_volume_levels(self, candles: List[Candle], current_atr: float) -> List[LevelCandidate]:
        """Detect levels using volume analysis."""
        candidates = []
        
        if len(candles) < 20:
            return candidates
        
        # Find high volume candles
        volumes = np.array([c.volume for c in candles])
        volume_threshold = np.percentile(volumes, 85)  # Top 15% volume
        
        high_volume_indices = np.where(volumes >= volume_threshold)[0]
        
        for idx in high_volume_indices:
            candle = candles[idx]
            
            # Add levels at high/low of high volume candles
            candidates.append(LevelCandidate(
                price=candle.high,
                level_type='resistance',
                first_touch_ts=candle.ts,
                touches=[(candle.ts, candle.high)],
                method='volume_high'
            ))
            
            candidates.append(LevelCandidate(
                price=candle.low,
                level_type='support',
                first_touch_ts=candle.ts,
                touches=[(candle.ts, candle.low)],
                method='volume_low'
            ))
        
        return candidates
    
    def _merge_similar_levels(self, candidates: List[LevelCandidate], current_atr: float) -> List[LevelCandidate]:
        """Merge level candidates that are close to each other."""
        if not candidates:
            return []
        
        # Sort by price
        candidates.sort(key=lambda x: x.price)
        
        merged = []
        tolerance = current_atr * self.touch_tolerance_atr
        
        for candidate in candidates:
            # Find if there's a similar level already in merged list
            similar_found = False
            
            for existing in merged:
                if (existing.level_type == candidate.level_type and
                    abs(existing.price - candidate.price) <= tolerance):
                    
                    # Merge with existing level
                    existing.touches.extend(candidate.touches)
                    
                    # Update price to weighted average
                    total_weight = len(existing.touches)
                    existing.price = sum(touch[1] for touch in existing.touches) / total_weight
                    
                    # Keep earliest timestamp
                    existing.first_touch_ts = min(existing.first_touch_ts, candidate.first_touch_ts)
                    
                    similar_found = True
                    break
            
            if not similar_found:
                merged.append(candidate)
        
        return merged
    
    def _validate_levels(self, candidates: List[LevelCandidate], 
                        candles: List[Candle], 
                        current_atr: float) -> List[TradingLevel]:
        """Validate level candidates and create TradingLevel objects."""
        validated = []
        
        for candidate in candidates:
            # Count actual touches by scanning through all candles
            touches = self._count_level_touches(candidate, candles, current_atr)
            
            # PATCH 003: Enforce min_touches requirement (was not checked before)
            if len(touches) < self.min_touches:
                logger.debug(
                    f"Level at {candidate.price:.2f} rejected - only {len(touches)} touches (min: {self.min_touches})"
                )
                continue
            
            if len(touches) >= self.min_touches:
                # Calculate level strength
                strength = self._calculate_level_strength(candidate, touches, candles)
                
                # Create TradingLevel object
                level = TradingLevel(
                    price=candidate.price,
                    level_type=candidate.level_type,
                    touch_count=len(touches),
                    strength=strength,
                    first_touch_ts=min(touch[0] for touch in touches),
                    last_touch_ts=max(touch[0] for touch in touches),
                    base_height=self._calculate_base_height(candidate, candles)
                )
                
                validated.append(level)
        
        # Sort by strength (strongest first)
        validated.sort(key=lambda x: x.strength, reverse=True)
        
        # Remove levels that are too close to each other
        final_levels = self._remove_overlapping_levels(validated, current_atr)
        
        return final_levels
    
    def _count_level_touches(self, candidate: LevelCandidate, 
                           candles: List[Candle], 
                           current_atr: float) -> List[Tuple[int, float]]:
        """Count all touches of a level by scanning through candles."""
        touches = []
        tolerance = current_atr * self.touch_tolerance_atr
        
        for candle in candles:
            # Check if candle touched the level
            if candidate.level_type == 'resistance':
                # For resistance, check if high touched or pierced level
                if (candle.high >= candidate.price - tolerance and 
                    candle.high <= candidate.price + tolerance):
                    touches.append((candle.ts, candle.high))
            else:  # support
                # For support, check if low touched or pierced level
                if (candle.low >= candidate.price - tolerance and 
                    candle.low <= candidate.price + tolerance):
                    touches.append((candle.ts, candle.low))
        
        # Remove duplicate touches (same timestamp)
        unique_touches = {}
        for ts, price in touches:
            if ts not in unique_touches:
                unique_touches[ts] = price
        
        return list(unique_touches.items())
    
    def _calculate_level_strength(self, candidate: LevelCandidate, 
                                touches: List[Tuple[int, float]], 
                                candles: List[Candle]) -> float:
        """Calculate level strength score (0-1)."""
        if not touches:
            return 0.0
        
        # Base strength from number of touches
        touch_strength = min(1.0, len(touches) / 5.0)  # Max at 5 touches
        
        # Time span factor (longer timespan = stronger)
        time_span_hours = (max(touch[0] for touch in touches) - 
                          min(touch[0] for touch in touches)) / (1000 * 60 * 60)
        time_strength = min(1.0, time_span_hours / 168)  # Max at 1 week
        
        # Volume factor (higher volume touches = stronger)
        volume_strength = 0.5  # Default if no volume data
        if candles:
            touch_timestamps = [touch[0] for touch in touches]
            touch_volumes = []
            
            for candle in candles:
                if candle.ts in touch_timestamps:
                    touch_volumes.append(candle.volume)
            
            if touch_volumes:
                avg_touch_volume = np.mean(touch_volumes)
                overall_avg_volume = np.mean([c.volume for c in candles])
                volume_strength = min(1.0, avg_touch_volume / overall_avg_volume)
        
        # Pierce analysis (fewer pierces = stronger)
        pierce_penalty = self._calculate_pierce_penalty(candidate, candles)
        
        # Combine factors
        final_strength = (touch_strength * 0.4 + 
                         time_strength * 0.2 + 
                         volume_strength * 0.2 + 
                         (1 - pierce_penalty) * 0.2)
        
        return max(0.0, min(1.0, final_strength))
    
    def _calculate_pierce_penalty(self, candidate: LevelCandidate, candles: List[Candle]) -> float:
        """Calculate penalty for level pierces."""
        pierces = 0
        total_candles = 0
        
        for candle in candles:
            if candidate.level_type == 'resistance':
                if candle.close > candidate.price * (1 + self.max_pierce_pct):
                    pierces += 1
            else:  # support
                if candle.close < candidate.price * (1 - self.max_pierce_pct):
                    pierces += 1
            total_candles += 1
        
        if total_candles == 0:
            return 0.0
        
        pierce_ratio = pierces / total_candles
        return min(1.0, pierce_ratio * 5)  # Scale up penalty
    
    def _calculate_base_height(self, candidate: LevelCandidate, candles: List[Candle]) -> Optional[float]:
        """Calculate base height for projection targets."""
        if not candles or len(candles) < 10:
            return None
        
        # Find recent high and low in vicinity of level
        recent_candles = candles[-20:]  # Last 20 candles
        
        if candidate.level_type == 'resistance':
            # For resistance, find the support below it
            lows = [c.low for c in recent_candles if c.low < candidate.price * 0.95]
            if lows:
                support_level = max(lows)  # Highest low below resistance
                return candidate.price - support_level
        else:  # support
            # For support, find the resistance above it
            highs = [c.high for c in recent_candles if c.high > candidate.price * 1.05]
            if highs:
                resistance_level = min(highs)  # Lowest high above support
                return resistance_level - candidate.price
        
        return None
    
    def _remove_overlapping_levels(self, levels: List[TradingLevel], current_atr: float) -> List[TradingLevel]:
        """Remove levels that are too close to each other."""
        if not levels:
            return []
        
        final_levels = []
        min_separation = current_atr * self.min_level_separation_atr
        
        for level in levels:
            # Check if this level is too close to any existing level
            too_close = False
            
            for existing in final_levels:
                if (existing.level_type == level.level_type and
                    abs(existing.price - level.price) < min_separation):
                    too_close = True
                    break
            
            if not too_close:
                final_levels.append(level)
        
        return final_levels
    
    def get_strongest_levels(self, levels: List[TradingLevel], 
                           max_levels: int = 5) -> List[TradingLevel]:
        """Get the strongest levels up to max_levels."""
        return sorted(levels, key=lambda x: x.strength, reverse=True)[:max_levels]
    
    def get_recent_levels(self, levels: List[TradingLevel], 
                         max_age_hours: int = 72,
                         reference_ts: Optional[int] = None) -> List[TradingLevel]:
        """Get levels that have been touched recently."""
        if reference_ts is None:
            reference_ts = int(time.time() * 1000)
        
        cutoff_time = reference_ts - (max_age_hours * 60 * 60 * 1000)
        
        return [level for level in levels if level.last_touch_ts >= cutoff_time]
    
    # New methods for extended features
    
    def is_round_number(self, price: float) -> Tuple[bool, float]:
        """
        Check if price is near a round number.
        
        Returns:
            (is_round, bonus_score)
        """
        if not self.prefer_round_numbers:
            return False, 0.0
        
        for step in sorted(self.round_step_candidates, reverse=True):
            # Check if price is close to a multiple of step
            remainder = price % step
            min_remainder = min(remainder, step - remainder)
            
            # If within 0.5% of round number
            if min_remainder / price < 0.005:
                # Larger steps get bigger bonus
                bonus = 0.1 + (0.05 * np.log10(step + 1))
                return True, min(bonus, 0.3)
        
        return False, 0.0
    
    def detect_cascade(self, levels: List[TradingLevel], target_price: float) -> Dict[str, Any]:
        """
        Detect cascade of levels near target price.
        
        Args:
            levels: All detected levels
            target_price: Price to check for cascade
        
        Returns:
            Dict with cascade info: {
                'has_cascade': bool,
                'count': int,
                'levels': List[TradingLevel],
                'bonus': float
            }
        """
        radius = target_price * (self.cascade_radius_bps / 10000)
        
        nearby_levels = [
            level for level in levels
            if abs(level.price - target_price) <= radius
        ]
        
        has_cascade = len(nearby_levels) >= self.cascade_min_levels
        bonus = 0.0
        
        if has_cascade:
            # Bonus increases with number of levels
            bonus = min(0.2, 0.05 * len(nearby_levels))
        
        return {
            'has_cascade': has_cascade,
            'count': len(nearby_levels),
            'levels': nearby_levels,
            'bonus': bonus
        }
    
    def check_approach_quality(
        self,
        candles: List[Candle],
        level_price: float,
        lookback_bars: int = 10
    ) -> Dict[str, Any]:
        """
        Check quality of price approach to level.
        
        Rejects vertical approaches and requires consolidation.
        
        Returns:
            Dict with approach info: {
                'is_valid': bool,
                'slope_pct_per_bar': float,
                'consolidation_bars': int,
                'reason': str
            }
        """
        if len(candles) < lookback_bars:
            return {
                'is_valid': False,
                'slope_pct_per_bar': 0.0,
                'consolidation_bars': 0,
                'reason': 'Not enough candles'
            }
        
        recent_candles = candles[-lookback_bars:]
        
        # Calculate approach slope
        start_price = recent_candles[0].close
        end_price = recent_candles[-1].close
        
        if start_price <= 0:
            return {
                'is_valid': False,
                'slope_pct_per_bar': 0.0,
                'consolidation_bars': 0,
                'reason': 'Invalid start price'
            }
        
        total_move_pct = abs(end_price - start_price) / start_price * 100
        slope_pct_per_bar = total_move_pct / lookback_bars
        
        # Check if slope is too steep (vertical approach)
        if slope_pct_per_bar > self.approach_slope_max_pct_per_bar:
            return {
                'is_valid': False,
                'slope_pct_per_bar': slope_pct_per_bar,
                'consolidation_bars': 0,
                'reason': f'Approach too steep: {slope_pct_per_bar:.2f}% per bar'
            }
        
        # Count consolidation bars near level
        level_tolerance = level_price * 0.005  # 0.5% tolerance
        consolidation_bars = 0
        
        for candle in recent_candles[-self.prebreakout_consolidation_min_bars:]:
            if abs(candle.close - level_price) <= level_tolerance:
                consolidation_bars += 1
        
        is_valid = consolidation_bars >= self.prebreakout_consolidation_min_bars
        reason = 'Valid approach' if is_valid else f'Insufficient consolidation: {consolidation_bars} bars'
        
        return {
            'is_valid': is_valid,
            'slope_pct_per_bar': slope_pct_per_bar,
            'consolidation_bars': consolidation_bars,
            'reason': reason
        }
    
    def enhance_level_scoring(
        self,
        level: TradingLevel,
        all_levels: List[TradingLevel],
        candles: List[Candle]
    ) -> float:
        """
        Enhance level scoring with round numbers, cascades, and approach quality.
        
        Returns:
            Enhanced strength score (0-1)
        """
        base_strength = level.strength
        bonus = 0.0
        
        # Round number bonus
        is_round, round_bonus = self.is_round_number(level.price)
        if is_round:
            bonus += round_bonus
        
        # Cascade bonus
        cascade_info = self.detect_cascade(all_levels, level.price)
        if cascade_info['has_cascade']:
            bonus += cascade_info['bonus']
        
        # Approach quality (only used for filtering, not bonus)
        approach_info = self.check_approach_quality(candles, level.price)
        
        # Apply bonus
        enhanced_strength = base_strength + bonus
        
        return max(0.0, min(1.0, enhanced_strength))