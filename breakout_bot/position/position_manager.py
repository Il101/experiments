"""
Position management system for Breakout Bot Trading System.

This module handles dynamic position management including stop-loss updates,
take-profit execution, trailing mechanisms, and add-on position logic.
"""

import asyncio
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
from dataclasses import dataclass
import logging
from concurrent.futures import ThreadPoolExecutor
import time
from collections import deque

from ..data.models import Position, Order, Candle, MarketData
from ..config.settings import TradingPreset, PositionConfig
from ..indicators.technical import atr, chandelier_exit, ema

logger = logging.getLogger(__name__)


@dataclass
class PositionUpdate:
    """Position update instruction."""
    position_id: str
    action: str  # 'update_stop', 'take_profit', 'close', 'add_on'
    price: Optional[float] = None
    quantity: Optional[float] = None
    reason: str = ""
    meta: Optional[Dict[str, Any]] = None


class PositionTracker:
    """Tracks individual position state and conditions."""
    
    def __init__(self, position: Position, config: PositionConfig):
        self.position = position
        self.config = config
        self.tp1_executed = False
        self.tp2_executed = False
        self.breakeven_moved = False
        self.trailing_active = False
        self.add_on_executed = False
        
    def should_update_stop(self, current_price: float, candles: List[Candle]) -> Optional[float]:
        """Check if stop loss should be updated."""
        if not candles:
            return None
            
        current_candle = candles[-1]
        
        # Move to breakeven after TP1
        if self.tp1_executed and not self.breakeven_moved:
            if self.position.side == 'long':
                # Move stop to entry + fees
                new_stop = self.position.entry * 1.001  # 0.1% above entry for fees
                if new_stop > self.position.sl:
                    self.breakeven_moved = True
                    return new_stop
            else:  # short
                new_stop = self.position.entry * 0.999  # 0.1% below entry for fees
                if new_stop < self.position.sl:
                    self.breakeven_moved = True
                    return new_stop
        
        # Chandelier exit trailing
        if self.breakeven_moved and len(candles) >= 22:
            chandelier_levels = chandelier_exit(
                candles, 
                period=22, 
                atr_multiplier=self.config.chandelier_atr_mult,
                long=(self.position.side == 'long')
            )
            
            if not np.isnan(chandelier_levels[-1]):
                new_stop = chandelier_levels[-1]
                
                if self.position.side == 'long':
                    # Only move stop up for longs
                    if new_stop > self.position.sl:
                        return new_stop
                else:
                    # Only move stop down for shorts
                    if new_stop < self.position.sl:
                        return new_stop
        
        return None
    
    def should_take_profit(self, current_price: float) -> Optional[Tuple[str, float, float]]:
        """Проверить, необходимо ли выполнить take profit."""
        entry = self.position.entry
        stop = self.position.sl
        if stop is None:
            return None
        r_distance = abs(entry - stop)
        
        if self.position.side == 'long':
            # TP1 at 1R
            tp1_r = self.config.tp1_r if self.config.tp1_r is not None else 1.0
            tp1_price = entry + (r_distance * tp1_r)
            if not self.tp1_executed and current_price >= tp1_price:
                tp1_size_pct = self.config.tp1_size_pct if self.config.tp1_size_pct is not None else 0.5
                tp1_qty = self.position.qty * tp1_size_pct
                return ('tp1', tp1_price, tp1_qty)
            
            # TP2 at 2R (after TP1)
            tp2_r = self.config.tp2_r if self.config.tp2_r is not None else 2.0
            tp2_price = entry + (r_distance * tp2_r)
            if self.tp1_executed and not self.tp2_executed and current_price >= tp2_price:
                tp2_size_pct = self.config.tp2_size_pct if self.config.tp2_size_pct is not None else 0.5
                tp2_qty = self.position.qty * tp2_size_pct
                return ('tp2', tp2_price, tp2_qty)
        
        else:  # short
            # TP1 at 1R
            tp1_r = self.config.tp1_r if self.config.tp1_r is not None else 1.0
            tp1_price = entry - (r_distance * tp1_r)
            if not self.tp1_executed and current_price <= tp1_price:
                tp1_size_pct = self.config.tp1_size_pct if self.config.tp1_size_pct is not None else 0.5
                tp1_qty = self.position.qty * tp1_size_pct
                return ('tp1', tp1_price, tp1_qty)
            
            # TP2 at 2R (after TP1)
            tp2_r = self.config.tp2_r if self.config.tp2_r is not None else 2.0
            tp2_price = entry - (r_distance * tp2_r)
            if self.tp1_executed and not self.tp2_executed and current_price <= tp2_price:
                tp2_size_pct = self.config.tp2_size_pct if self.config.tp2_size_pct is not None else 0.5
                tp2_qty = self.position.qty * tp2_size_pct
                return ('tp2', tp2_price, tp2_qty)
        
        return None
    
    def should_close_position(
        self, 
        current_time: int,
        activity_tracker=None,
        symbol: Optional[str] = None
    ) -> Optional[str]:
        """
        Check if position should be closed due to time or other factors.
        
        Args:
            current_time: Current timestamp in milliseconds
            activity_tracker: Optional ActivityTracker for panic exit
            symbol: Symbol for activity checking
        """
        
        # Time-based close
        if 'opened_at' in self.position.timestamps:
            position_age_hours = (current_time - self.position.timestamps['opened_at']) / (1000 * 60 * 60)
            if position_age_hours > self.config.max_hold_time_hours:
                return f"Maximum hold time exceeded: {position_age_hours:.1f}h"
        
        # New: Time-stop in minutes
        if self.config.time_stop_minutes is not None and 'opened_at' in self.position.timestamps:
            position_age_minutes = (current_time - self.position.timestamps['opened_at']) / (1000 * 60)
            if position_age_minutes > self.config.time_stop_minutes:
                return f"Time stop triggered: {position_age_minutes:.1f}m"
        
        # New: Panic exit on activity drop
        if (self.config.panic_exit_on_activity_drop and 
            activity_tracker is not None and 
            symbol is not None):
            
            if activity_tracker.is_activity_dropping(
                symbol=symbol,
                drop_frac=self.config.activity_drop_threshold
            ):
                metrics = activity_tracker.get_metrics(symbol)
                if metrics:
                    return (f"Panic exit: activity drop detected, "
                           f"drop_fraction={metrics.drop_fraction:.2f}")
        
        # No progress close (if not reached 1R within reasonable time)
        if not self.tp1_executed:
            if 'opened_at' in self.position.timestamps:
                hours_since_open = (current_time - self.position.timestamps['opened_at']) / (1000 * 60 * 60)
                if hours_since_open > 8:  # 8 hours without progress
                    unrealized_r = self.position.pnl_r
                    if unrealized_r < 0.3:  # Less than 0.3R progress
                        return f"No progress after {hours_since_open:.1f}h, R: {unrealized_r:.2f}"
        
        return None
    
    def should_add_on(self, current_price: float, candles: List[Candle]) -> Optional[float]:
        """Check if add-on position should be opened."""
        if not self.config.add_on_enabled or self.add_on_executed:
            return None
        
        # Only add on for liquid markets and after reaching profit
        if self.position.pnl_r < 0.5:  # Must be at least 0.5R in profit
            return None
        
        if len(candles) < 9:
            return None
        
        # Check for 9-EMA pullback
        closes = [c.close for c in candles]
        ema9 = ema(closes, 9)
        
        if np.isnan(ema9[-1]):
            return None
        
        ema_price = ema9[-1]
        
        # Check if price is pulling back to EMA
        if self.position.side == 'long':
            # For longs, price should be near or slightly above EMA
            if 0.995 <= current_price / ema_price <= 1.005:  # Within 0.5%
                return ema_price
        else:  # short
            # For shorts, price should be near or slightly below EMA
            if 0.995 <= ema_price / current_price <= 1.005:
                return ema_price
        
        return None


class PositionManager:
    """Main position management system with async computations."""
    
    def __init__(self, preset: TradingPreset):
        self.preset = preset
        self.config = preset.position_config
        self.position_trackers: Dict[str, PositionTracker] = {}
        self.thread_pool = ThreadPoolExecutor(max_workers=4)
        self.recent_positions: deque = deque(maxlen=100)  # Keep last 100 positions
        
        # ✅ CRITICAL: Add synchronization to prevent race conditions
        self._position_lock = asyncio.Lock()
        self._recent_positions_lock = asyncio.Lock()
        
        # Activity tracker for panic exit detection (set by engine)
        self.activity_tracker: Optional[Any] = None
        
        logger.info(f"Initialized position manager with preset: {preset.name}")
    
    def initialize(self):
        """Initialize position manager (placeholder for future setup)."""
        # Clear any existing trackers
        self.position_trackers.clear()
        logger.debug("Position manager initialization complete")
    
    async def add_position(self, position: Position):
        """Add a new position to management (thread-safe)."""
        async with self._position_lock:
            tracker = PositionTracker(position, self.config)
            self.position_trackers[position.id] = tracker
            
        async with self._recent_positions_lock:
            self.recent_positions.append(position)
            
        logger.info(f"Added position to management: {position.id} - {position.symbol} {position.side}")
    
    async def remove_position(self, position_id: str):
        """Remove position from management (thread-safe)."""
        async with self._position_lock:
            if position_id in self.position_trackers:
                del self.position_trackers[position_id]
                logger.info(f"Removed position from management: {position_id}")
    
    async def update_position(self, position: Position):
        """Update existing position data (thread-safe)."""
        async with self._position_lock:
            if position.id in self.position_trackers:
                self.position_trackers[position.id].position = position
                
        # Update in recent positions if it exists
        async with self._recent_positions_lock:
            for i, recent_pos in enumerate(self.recent_positions):
                if recent_pos.id == position.id:
                    self.recent_positions[i] = position
                    break
    
    async def process_position_updates(self, 
                                     positions: List[Position],
                                     market_data_dict: Dict[str, MarketData]) -> List[PositionUpdate]:
        """Process all positions and generate update instructions asynchronously."""
        
        if not positions:
            return []
        
        # Process positions in parallel using thread pool
        tasks = []
        for position in positions:
            if position.status != 'open':
                continue
            
            # Get market data
            market_data = market_data_dict.get(position.symbol)
            if not market_data:
                continue
            
            # Create task for async processing
            task = asyncio.create_task(
                self._process_single_position_async(position, market_data)
            )
            tasks.append(task)
        
        # Wait for all tasks to complete
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Collect all updates
            updates = []
            for result in results:
                if isinstance(result, Exception):
                    logger.error(f"Error processing position: {result}")
                elif result and isinstance(result, list):
                    if isinstance(result, list):
                        updates.extend(result)
            
            if updates:
                logger.info(f"Generated {len(updates)} position updates")
            
            return updates
        
        return []
    
    async def _process_single_position_async(self, position: Position, market_data: MarketData) -> List[PositionUpdate]:
        """Process a single position asynchronously."""
        updates = []
        current_time = int(datetime.now().timestamp() * 1000)
        
        try:
            # Get or create tracker
            if position.id not in self.position_trackers:
                await self.add_position(position)
            
            tracker = self.position_trackers[position.id]
            current_price = market_data.price
            candles = market_data.candles_5m
            
            # Run heavy computations in thread pool
            loop = asyncio.get_running_loop()
            
            # Check for stop loss updates (async)
            new_stop = await loop.run_in_executor(
                self.thread_pool, 
                tracker.should_update_stop, 
                current_price, 
                candles
            )
            
            if new_stop and new_stop != position.sl:
                updates.append(PositionUpdate(
                    position_id=position.id,
                    action='update_stop',
                    price=new_stop,
                    reason=f"Stop update: {position.sl:.6f} -> {new_stop:.6f}",
                    meta={'old_stop': position.sl}
                ))
            
            # Check for take profits (async)
            tp_result = await loop.run_in_executor(
                self.thread_pool,
                tracker.should_take_profit,
                current_price
            )
            
            if tp_result:
                tp_type, tp_price, tp_qty = tp_result
                
                updates.append(PositionUpdate(
                    position_id=position.id,
                    action='take_profit',
                    price=tp_price,
                    quantity=tp_qty,
                    reason=f"{tp_type.upper()} execution at {tp_price:.6f}",
                    meta={'tp_type': tp_type}
                ))
                
                # Mark as executed
                if tp_type == 'tp1':
                    tracker.tp1_executed = True
                elif tp_type == 'tp2':
                    tracker.tp2_executed = True
            
            # Check for position close (async)
            close_reason = await loop.run_in_executor(
                self.thread_pool,
                tracker.should_close_position,
                current_time
            )
            
            if close_reason:
                updates.append(PositionUpdate(
                    position_id=position.id,
                    action='close',
                    price=current_price,
                    quantity=position.qty,
                    reason=close_reason
                ))
            
            # Check for add-on positions (async)
            if self.config.add_on_enabled:
                add_on_price = await loop.run_in_executor(
                    self.thread_pool,
                    tracker.should_add_on,
                    current_price,
                    candles
                )
                
                if add_on_price:
                    add_on_qty = position.qty * self.config.add_on_max_size_pct
                    
                    updates.append(PositionUpdate(
                        position_id=position.id,
                        action='add_on',
                        price=add_on_price,
                        quantity=add_on_qty,
                        reason=f"Add-on at EMA pullback: {add_on_price:.6f}",
                        meta={'parent_position': position.id}
                    ))
                    
                    tracker.add_on_executed = True
            
        except Exception as e:
            logger.error(f"Error processing position {position.id}: {e}")
        
        return updates
    
    def calculate_position_metrics(self, positions: List[Position]) -> Dict[str, Any]:
        """Calculate position management metrics."""
        
        open_positions = [p for p in positions if p.status == 'open']
        closed_positions = [p for p in positions if p.status == 'closed']
        
        metrics = {
            'total_positions': len(positions),
            'open_positions': len(open_positions),
            'closed_positions': len(closed_positions),
            'avg_hold_time_hours': 0.0,
            'tp1_hit_rate': 0.0,
            'tp2_hit_rate': 0.0,
            'avg_r_realized': 0.0,
            'breakeven_moved_count': 0,
            'trailing_active_count': 0,
            'add_on_count': 0
        }
        
        # Calculate average hold time for closed positions
        if closed_positions:
            total_hold_time = 0
            valid_positions = 0
            
            for pos in closed_positions:
                if 'opened_at' in pos.timestamps and 'closed_at' in pos.timestamps:
                    hold_time = (pos.timestamps['closed_at'] - pos.timestamps['opened_at']) / (1000 * 60 * 60)
                    total_hold_time += hold_time
                    valid_positions += 1
            
            if valid_positions > 0:
                metrics['avg_hold_time_hours'] = total_hold_time / valid_positions
        
        # Calculate TP hit rates
        tp1_hits = sum(1 for p in closed_positions if p.pnl_r >= 1.0)
        tp2_hits = sum(1 for p in closed_positions if p.pnl_r >= 2.0)
        
        if closed_positions:
            metrics['tp1_hit_rate'] = tp1_hits / len(closed_positions)
            metrics['tp2_hit_rate'] = tp2_hits / len(closed_positions)
            metrics['avg_r_realized'] = sum(p.pnl_r for p in closed_positions) / len(closed_positions)
        
        # Count active management features
        for tracker in self.position_trackers.values():
            if tracker.breakeven_moved:
                metrics['breakeven_moved_count'] += 1
            if tracker.trailing_active:
                metrics['trailing_active_count'] += 1
            if tracker.add_on_executed:
                metrics['add_on_count'] += 1
        
        return metrics
    
    def get_position_status(self, position_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed status of a specific position."""
        
        if position_id not in self.position_trackers:
            return None
        
        tracker = self.position_trackers[position_id]
        position = tracker.position
        
        return {
            'position_id': position_id,
            'symbol': position.symbol,
            'side': position.side,
            'qty': position.qty,
            'entry': position.entry,
            'current_sl': position.sl,
            'current_pnl_r': position.pnl_r,
            'tp1_executed': tracker.tp1_executed,
            'tp2_executed': tracker.tp2_executed,
            'breakeven_moved': tracker.breakeven_moved,
            'trailing_active': tracker.trailing_active,
            'add_on_executed': tracker.add_on_executed,
            'age_hours': position.duration_hours,
            'status': position.status
        }
    
    async def cleanup_closed_positions(self):
        """Remove trackers for closed positions (thread-safe)."""
        
        closed_trackers = []
        
        # First pass: identify closed positions safely
        async with self._position_lock:
            for position_id, tracker in self.position_trackers.items():
                if tracker.position.status in ['closed', 'partially_closed']:
                    closed_trackers.append(position_id)
        
        # Second pass: remove positions (this will acquire locks internally)
        for position_id in closed_trackers:
            await self.remove_position(position_id)
        
        if closed_trackers:
            logger.info(f"Cleaned up {len(closed_trackers)} closed position trackers")
    
    def close(self):
        """Close position manager and cleanup resources."""
        if hasattr(self, 'thread_pool'):
            self.thread_pool.shutdown(wait=True)
            logger.info("Position manager thread pool closed")

    async def cancel_all_orders(self) -> None:
        """Placeholder for external integrations with open OCO orders."""
        # The live exchange executor handles order cancellations directly.
        return None

    async def get_recent_positions(self, limit: int = 50) -> List[Position]:
        """Get recent positions from the position manager (thread-safe)."""
        async with self._recent_positions_lock:
            return list(self.recent_positions)[-limit:]
    
    async def get_active_positions(self) -> List[Position]:
        """Get all active (open) positions (thread-safe)."""
        async with self._position_lock:
            return [tracker.position for tracker in self.position_trackers.values() 
                    if tracker.position.status == 'open']