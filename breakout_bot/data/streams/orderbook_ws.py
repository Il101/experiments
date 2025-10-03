"""
OrderBook WebSocket Manager for real-time order book tracking.

Maintains up-to-date order book state and provides depth analysis.
"""

import asyncio
import logging
import time
from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Any, Callable
import numpy as np


logger = logging.getLogger(__name__)


@dataclass
class OrderBookLevel:
    """Single order book level."""
    price: float
    size: float


@dataclass
class OrderBookSnapshot:
    """Order book snapshot at a point in time."""
    timestamp: int  # milliseconds
    bids: List[OrderBookLevel]
    asks: List[OrderBookLevel]
    
    @property
    def best_bid(self) -> Optional[float]:
        """Get best bid price."""
        return self.bids[0].price if self.bids else None
    
    @property
    def best_ask(self) -> Optional[float]:
        """Get best ask price."""
        return self.asks[0].price if self.asks else None
    
    @property
    def mid_price(self) -> Optional[float]:
        """Get mid price."""
        if self.best_bid and self.best_ask:
            return (self.best_bid + self.best_ask) / 2
        return None
    
    @property
    def spread_bps(self) -> float:
        """Get spread in basis points."""
        if not self.best_bid or not self.best_ask:
            return 0.0
        
        spread = self.best_ask - self.best_bid
        mid = self.mid_price
        
        if mid and mid > 0:
            return (spread / mid) * 10000
        
        return 0.0


class OrderBookManager:
    """
    Manages real-time order book data from WebSocket.
    
    Features:
    - Snapshot + delta updates
    - Depth aggregation by price buckets
    - Imbalance calculation
    - Historical depth tracking
    - **NEW**: Real Bybit WebSocket integration
    """
    
    def __init__(self, exchange_client=None, use_real_ws: bool = True):
        self.exchange_client = exchange_client
        self.active_symbols: Dict[str, bool] = {}
        self.snapshots: Dict[str, OrderBookSnapshot] = {}
        self.running = False
        self.tasks: List[asyncio.Task] = []
        
        # Bybit WebSocket integration
        self._use_real_ws = use_real_ws
        self.bybit_ws = None
        self._orderbook_depth = 50  # Default depth for Bybit
        
        logger.info("OrderBookManager initialized")
    
    async def start(self) -> None:
        """Start the manager."""
        if self.running:
            logger.warning("OrderBookManager already running")
            return
        
        self.running = True
        
        # Initialize Bybit WebSocket if enabled
        if self._use_real_ws:
            try:
                from breakout_bot.exchange.bybit_websocket import BybitWebSocketClient
                
                self.bybit_ws = BybitWebSocketClient(
                    testnet=False,
                    on_orderbook=self._on_orderbook_update
                )
                await self.bybit_ws.start()
                logger.info("OrderBookManager: Bybit WebSocket connected")
                
            except ImportError:
                logger.warning("BybitWebSocketClient not available, using simulation mode")
                self.bybit_ws = None
            except Exception as e:
                logger.error(f"Failed to initialize Bybit WebSocket: {e}", exc_info=True)
                self.bybit_ws = None
        
        logger.info("OrderBookManager started")
    
    async def stop(self) -> None:
        """Stop the manager."""
        if not self.running:
            return
        
        self.running = False
        
        # Stop Bybit WebSocket
        if self.bybit_ws:
            try:
                await self.bybit_ws.stop()
                logger.info("OrderBookManager: Bybit WebSocket disconnected")
            except Exception as e:
                logger.error(f"Error stopping Bybit WebSocket: {e}", exc_info=True)
        
        # Cancel all tasks
        for task in self.tasks:
            task.cancel()
        
        if self.tasks:
            await asyncio.gather(*self.tasks, return_exceptions=True)
        
        self.tasks.clear()
        logger.info("OrderBookManager stopped")
    
    async def subscribe(self, symbol: str) -> None:
        """Subscribe to order book for a symbol."""
        if symbol in self.active_symbols:
            logger.debug(f"Already subscribed to {symbol}")
            return
        
        self.active_symbols[symbol] = True
        logger.info(f"Subscribed to order book for {symbol}")
        
        # Subscribe via Bybit WebSocket if available
        if self.bybit_ws and self.bybit_ws.connected:
            try:
                await self.bybit_ws.subscribe_orderbook(symbol, depth=self._orderbook_depth)
                logger.info(f"Subscribed to Bybit orderbook stream for {symbol}")
            except Exception as e:
                logger.error(f"Failed to subscribe to Bybit orderbook for {symbol}: {e}", exc_info=True)
        
        # Start processing task (for simulation fallback)
        if not self.bybit_ws or not self.bybit_ws.connected:
            task = asyncio.create_task(self._process_orderbook(symbol))
            self.tasks.append(task)
    
    async def unsubscribe(self, symbol: str) -> None:
        """Unsubscribe from order book for a symbol."""
        if symbol not in self.active_symbols:
            return
        
        self.active_symbols[symbol] = False
        
        # Unsubscribe from Bybit WebSocket if connected
        if self.bybit_ws and self.bybit_ws.connected:
            try:
                await self.bybit_ws.unsubscribe_orderbook(symbol, depth=self._orderbook_depth)
                logger.info(f"Unsubscribed from Bybit orderbook stream for {symbol}")
            except Exception as e:
                logger.error(f"Failed to unsubscribe from Bybit orderbook for {symbol}: {e}", exc_info=True)
        
        if symbol in self.snapshots:
            del self.snapshots[symbol]
        
        logger.info(f"Unsubscribed from order book for {symbol}")
    
    async def _on_orderbook_update(self, symbol: str, orderbook_data: Dict[str, Any]) -> None:
        """
        Callback for Bybit orderbook updates.
        
        Args:
            symbol: Trading pair symbol
            orderbook_data: Orderbook data from Bybit:
                {
                    'symbol': 'BTCUSDT',
                    'bids': [[price, size], ...],
                    'asks': [[price, size], ...],
                    'timestamp': 1672304484978,
                    'update_id': 177400507,
                    'type': 'snapshot' or 'delta'
                }
        """
        try:
            # Check if still subscribed
            if not self.active_symbols.get(symbol, False):
                return
            
            # Convert Bybit format to OrderBookSnapshot
            bids = [
                OrderBookLevel(price=float(bid[0]), size=float(bid[1]))
                for bid in orderbook_data.get('bids', [])
            ]
            
            asks = [
                OrderBookLevel(price=float(ask[0]), size=float(ask[1]))
                for ask in orderbook_data.get('asks', [])
            ]
            
            snapshot = OrderBookSnapshot(
                timestamp=orderbook_data.get('timestamp', int(time.time() * 1000)),
                bids=bids,
                asks=asks
            )
            
            # Update snapshot
            self.snapshots[symbol] = snapshot
            
            logger.debug(
                f"OrderBook update for {symbol}: "
                f"bids={len(bids)}, asks={len(asks)}, "
                f"mid={snapshot.mid_price:.2f if snapshot.mid_price else 'N/A'}"
            )
            
        except Exception as e:
            logger.error(f"Error processing orderbook update for {symbol}: {e}", exc_info=True)
    
    async def _process_orderbook(self, symbol: str) -> None:
        """
        Process incoming order book updates for a symbol.
        
        Fallback simulation mode when WebSocket is not available.
        """
        try:
            logger.info(f"Starting orderbook simulation for {symbol} (WebSocket unavailable)")
            
            while self.running and self.active_symbols.get(symbol, False):
                # Simulation: generate fake orderbook
                await asyncio.sleep(1)
                
                # Create mock orderbook snapshot
                mid_price = 50000.0  # Example price
                spread = 0.01  # 1% spread
                
                bids = [
                    OrderBookLevel(price=mid_price * (1 - spread * (i + 1) / 10), size=1.0 + i * 0.5)
                    for i in range(10)
                ]
                
                asks = [
                    OrderBookLevel(price=mid_price * (1 + spread * (i + 1) / 10), size=1.0 + i * 0.5)
                    for i in range(10)
                ]
                
                snapshot = OrderBookSnapshot(
                    timestamp=int(time.time() * 1000),
                    bids=bids,
                    asks=asks
                )
                
                self.snapshots[symbol] = snapshot
                
        except asyncio.CancelledError:
            logger.debug(f"OrderBook processing for {symbol} cancelled")
        except Exception as e:
            logger.error(f"Error processing order book for {symbol}: {e}", exc_info=True)
    
    def update_snapshot(self, symbol: str, snapshot: OrderBookSnapshot) -> None:
        """
        Manually update order book snapshot.
        
        Used for testing or when receiving data from external source.
        """
        self.snapshots[symbol] = snapshot
    
    def get_snapshot(self, symbol: str) -> Optional[OrderBookSnapshot]:
        """Get current order book snapshot for a symbol."""
        return self.snapshots.get(symbol)
    
    def get_aggregated_depth(
        self,
        symbol: str,
        side: str,
        range_bps: float = 50
    ) -> List[Tuple[float, float]]:
        """
        Get aggregated depth within price range.
        
        Args:
            symbol: Trading pair symbol
            side: 'bid' or 'ask'
            range_bps: Price range in basis points from best price
        
        Returns:
            List of (price, cumulative_size) tuples
        """
        snapshot = self.snapshots.get(symbol)
        if not snapshot:
            return []
        
        if side == 'bid':
            levels = snapshot.bids
            best_price = snapshot.best_bid
            price_multiplier = 1 - (range_bps / 10000)
        else:  # ask
            levels = snapshot.asks
            best_price = snapshot.best_ask
            price_multiplier = 1 + (range_bps / 10000)
        
        if not best_price:
            return []
        
        price_limit = best_price * price_multiplier
        
        result = []
        cumulative_size = 0.0
        
        for level in levels:
            if side == 'bid':
                if level.price < price_limit:
                    break
            else:
                if level.price > price_limit:
                    break
            
            cumulative_size += level.size
            result.append((level.price, cumulative_size))
        
        return result
    
    def get_imbalance(self, symbol: str, range_bps: float = 30) -> float:
        """
        Calculate order book imbalance within price range.
        
        Returns value between -1 (all asks) and 1 (all bids).
        """
        snapshot = self.snapshots.get(symbol)
        if not snapshot or not snapshot.mid_price:
            return 0.0
        
        mid = snapshot.mid_price
        range_price = mid * (range_bps / 10000)
        
        bid_volume = sum(
            level.size for level in snapshot.bids
            if level.price >= mid - range_price
        )
        
        ask_volume = sum(
            level.size for level in snapshot.asks
            if level.price <= mid + range_price
        )
        
        total = bid_volume + ask_volume
        if total == 0:
            return 0.0
        
        return (bid_volume - ask_volume) / total
    
    def is_subscribed(self, symbol: str) -> bool:
        """Check if subscribed to a symbol."""
        return symbol in self.active_symbols and self.active_symbols[symbol]
