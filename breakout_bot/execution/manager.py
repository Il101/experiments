"""Execution management utilities for Breakout Bot.

This module adds depth-aware execution including TWAP slicing, iceberg
behaviour, and slippage-aware fee calculations. It converts execution
configuration parameters from presets into actionable order placement
strategies and consolidates child fills into a single synthetic order
object for the rest of the system.
"""

from __future__ import annotations

import asyncio
import math
import time
import uuid
import logging
from dataclasses import dataclass
from typing import Dict, List, Optional
from collections import deque

from ..config.settings import ExecutionConfig, TradingPreset
from ..data.models import Order, MarketData, L2Depth
from ..risk.risk_manager import PositionSize

logger = logging.getLogger(__name__)


@dataclass
class DepthEnvelope:
    """Simplified depth snapshot used for execution decisions."""

    best_bid: float
    best_ask: float
    spread_bps: float
    bid_depth_0_3: float
    ask_depth_0_3: float
    bid_depth_0_5: float
    ask_depth_0_5: float
    bid_depth_5_bps: float
    ask_depth_5_bps: float
    imbalance: float
    timestamp_ms: int

    @property
    def mid_price(self) -> float:
        return (self.best_bid + self.best_ask) / 2 if self.best_bid and self.best_ask else max(self.best_bid, self.best_ask)


class ExecutionManager:
    """Depth-aware order execution helper."""

    def __init__(self, exchange_client, preset: TradingPreset):
        self.exchange_client = exchange_client
        self.preset = preset
        self.config: ExecutionConfig = preset.execution_config
        self.recent_orders: deque = deque(maxlen=100)  # Keep last 100 orders

    async def execute_trade(
        self,
        symbol: str,
        side: str,
        total_quantity: float,
        market_data: MarketData,
        position_size: Optional[PositionSize] = None,
        reduce_only: bool = False,
        intent: str = "entry",
    ) -> Optional[Order]:
        """Execute a trade with TWAP/iceberg handling.

        Args:
            symbol: Trading pair symbol (e.g., BTC/USDT)
            side: 'buy' or 'sell'
            total_quantity: Target fill quantity
            market_data: Recent market snapshot
            position_size: Optional position sizing output for additional metadata
            reduce_only: Whether the order should only reduce exposure
            intent: Execution context (entry/exit/add_on)
        """

        if total_quantity <= 0:
            logger.warning("execute_trade called with non-positive quantity for %s", symbol)
            return None

        depth = await self._get_depth(symbol, market_data)
        if not depth:
            logger.warning("No depth snapshot available for %s, falling back to market order", symbol)

        total_notional = self._resolve_notional(total_quantity, market_data, position_size)
        
        # PATCH 002: Add execution depth guard to prevent high slippage
        if depth:
            is_buy = side.lower() == 'buy'
            available_depth = depth.ask_depth_5_bps if is_buy else depth.bid_depth_5_bps
            max_allowed_notional = available_depth * self.config.max_depth_fraction
            
            if abs(total_notional) > max_allowed_notional:
                logger.warning(
                    "Order size %.2f USD exceeds max allowed depth fraction (%.2f%% of %.2f USD = %.2f USD) for %s",
                    abs(total_notional),
                    self.config.max_depth_fraction * 100,
                    available_depth,
                    max_allowed_notional,
                    symbol
                )
                # Scale down to max allowed or reject
                if max_allowed_notional < abs(total_notional) * 0.3:  # Too much slippage expected
                    logger.error("Rejecting order for %s - insufficient liquidity", symbol)
                    return None
                else:
                    logger.info("Scaling down order size from %.2f to %.2f USD", abs(total_notional), max_allowed_notional)
                    total_notional = max_allowed_notional if total_notional > 0 else -max_allowed_notional
                    total_quantity = abs(total_notional) / market_data.price  # Recalculate quantity using current price
        
        slices = self._determine_slices(total_notional, depth, side)

        orders: List[Order] = []
        filled_qty = 0.0
        total_cost = 0.0
        total_fees = 0.0
        order_types_used: List[str] = []
        start_time = time.time()

        for slice_index in range(slices):
            if time.time() - start_time > self.config.deadman_timeout_ms / 1000:
                logger.error("Deadman switch triggered while executing %s on %s", intent, symbol)
                break

            remaining_qty = max(0.0, total_quantity - filled_qty)
            if remaining_qty <= 0:
                break

            chunk_qty = min(remaining_qty, total_quantity / slices)
            price_hint = self._price_hint(market_data, depth, side)
            order_type, price, params = self._build_order(side, chunk_qty, depth, reduce_only)

            order_types_used.append(order_type)

            try:
                order = await self.exchange_client.create_order(
                    symbol=symbol,
                    order_type=order_type,
                    side=side,
                    amount=chunk_qty,
                    price=price,
                    params=params,
                )
            except Exception as exc:  # pragma: no cover - defensive path
                logger.error("Slice execution failed for %s (%s): %s", symbol, intent, exc)
                break

            if not order:
                logger.error("Exchange returned empty order for %s slice", symbol)
                break

            fill_qty = order.filled_qty or chunk_qty
            fill_price = order.avg_fill_price or price or price_hint
            fee = order.fees_usd
            if fee == 0 and fill_price:
                fee_rate = self.config.taker_fee_bps if order_type == 'market' else self.config.maker_fee_bps
                fee = (fee_rate / 10000.0) * fill_price * fill_qty
                order.fees_usd = fee

            filled_qty += fill_qty
            total_cost += fill_price * fill_qty
            total_fees += fee
            orders.append(order)

            if slice_index < slices - 1 and filled_qty < total_quantity:
                await asyncio.sleep(self.config.twap_interval_seconds)

        if filled_qty <= 0:
            logger.warning("No fills recorded for %s on %s", intent, symbol)
            return None

        average_fill = total_cost / filled_qty if filled_qty else 0.0
        slippage_bps = self._calculate_slippage_bps(average_fill, market_data.price)

        metadata: Dict[str, object] = {
            "intent": intent,
            "slices": len(orders),
            "configured_slices": slices,
            "reduce_only": reduce_only,
            "order_types": order_types_used,
            "slippage_bps": slippage_bps,
        }

        if depth:
            metadata.update(
                {
                    "spread_bps": depth.spread_bps,
                    "imbalance": depth.imbalance,
                    "depth_notional_0_3": depth.ask_depth_0_3 if side == 'buy' else depth.bid_depth_0_3,
                }
            )

        metadata.update(
            {
                "child_order_ids": [child.id for child in orders],
                "fees_usd": total_fees,
            }
        )

        composite = Order(
            id=str(uuid.uuid4()),
            symbol=symbol,
            side=side,
            order_type='limit' if 'limit' in order_types_used and 'market' not in order_types_used else order_types_used[-1],
            qty=total_quantity,
            price=None,
            status='filled' if filled_qty >= total_quantity * 0.999 else 'open',
            filled_qty=filled_qty,
            avg_fill_price=average_fill,
            fees_usd=total_fees,
            timestamps={'created_at': int(time.time() * 1000)},
            exchange_id=orders[-1].exchange_id if orders else None,
            metadata=metadata,
        )

        # Add to recent orders
        self.recent_orders.append(composite)

        return composite

    async def _get_depth(self, symbol: str, market_data: MarketData) -> Optional[DepthEnvelope]:
        streamer = getattr(self.exchange_client, 'market_streamer', None)
        depth = None
        if streamer:
            depth_snapshot = await streamer.get_depth_snapshot(symbol)
            if depth_snapshot:
                # Calculate 5 bps depth from 0.3% depth (5 bps = 0.05%)
                bid_depth_5_bps = depth_snapshot.bid_depth_0_3 * (5.0 / 30.0)  # 5/30 = 0.05/0.3
                ask_depth_5_bps = depth_snapshot.ask_depth_0_3 * (5.0 / 30.0)
                
                depth = DepthEnvelope(
                    best_bid=depth_snapshot.best_bid,
                    best_ask=depth_snapshot.best_ask,
                    spread_bps=depth_snapshot.spread_bps,
                    bid_depth_0_3=depth_snapshot.bid_depth_0_3,
                    ask_depth_0_3=depth_snapshot.ask_depth_0_3,
                    bid_depth_0_5=depth_snapshot.bid_depth_0_5,
                    ask_depth_0_5=depth_snapshot.ask_depth_0_5,
                    bid_depth_5_bps=bid_depth_5_bps,
                    ask_depth_5_bps=ask_depth_5_bps,
                    imbalance=depth_snapshot.imbalance,
                    timestamp_ms=depth_snapshot.timestamp_ms,
                )
        if not depth and market_data.l2_depth:
            l2: L2Depth = market_data.l2_depth
            # Calculate 5 bps depth from 0.3% depth (5 bps = 0.05%)
            bid_depth_5_bps = l2.bid_usd_0_3pct * (5.0 / 30.0)  # 5/30 = 0.05/0.3
            ask_depth_5_bps = l2.ask_usd_0_3pct * (5.0 / 30.0)
            
            depth = DepthEnvelope(
                best_bid=market_data.price * (1 - l2.spread_bps / 20000),
                best_ask=market_data.price * (1 + l2.spread_bps / 20000),
                spread_bps=l2.spread_bps,
                bid_depth_0_3=l2.bid_usd_0_3pct,
                ask_depth_0_3=l2.ask_usd_0_3pct,
                bid_depth_0_5=l2.bid_usd_0_5pct,
                ask_depth_0_5=l2.ask_usd_0_5pct,
                bid_depth_5_bps=bid_depth_5_bps,
                ask_depth_5_bps=ask_depth_5_bps,
                imbalance=l2.imbalance,
                timestamp_ms=market_data.timestamp,
            )
        return depth

    def _determine_slices(self, total_notional: float, depth: Optional[DepthEnvelope], side: str) -> int:
        if not depth or not self.config.enable_twap:
            return 1

        is_buy = side.lower() == 'buy'
        depth_reference = depth.ask_depth_5_bps if is_buy else depth.bid_depth_5_bps
        if depth_reference <= 0:
            return 1

        allowed_notional = max(depth_reference * self.config.max_depth_fraction, 1.0)
        desired_slices = math.ceil(abs(total_notional) / allowed_notional)
        return max(self.config.twap_min_slices, min(self.config.twap_max_slices, desired_slices))

    def _build_order(self, side: str, qty: float, depth: Optional[DepthEnvelope], reduce_only: bool):
        params: Dict[str, object] = {'reduceOnly': reduce_only}
        if depth and self.config.enable_iceberg:
            if depth.spread_bps <= self.config.spread_widen_bps:
                offset = self.config.limit_offset_bps / 10000.0
                if side == 'buy':
                    price = depth.best_bid * (1 - offset)
                else:
                    price = depth.best_ask * (1 + offset)
                params['postOnly'] = True
                params['timeInForce'] = 'GoodTillCancel'
                return 'limit', price, params
        return 'market', None, params

    def _price_hint(self, market_data: MarketData, depth: Optional[DepthEnvelope], side: str) -> float:
        if depth:
            return depth.best_ask if side == 'buy' else depth.best_bid
        return market_data.price

    def _resolve_notional(self, qty: float, market_data: MarketData, position_size: Optional[PositionSize]) -> float:
        if position_size and position_size.notional_usd:
            return position_size.notional_usd
        return qty * market_data.price

    def _calculate_slippage_bps(self, fill_price: float, reference_price: float) -> float:
        if not fill_price or not reference_price:
            return 0.0
        return ((fill_price - reference_price) / reference_price) * 10000

    def get_recent_orders(self, limit: int = 50) -> List[Order]:
        """Get recent orders from the execution manager."""
        return list(self.recent_orders)[-limit:]
