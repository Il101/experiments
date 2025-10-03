"""
Trades WebSocket Aggregator for real-time trade flow analysis with Bybit integration.

Subscribes to trade streams and calculates:
- Trades per minute (TPM)
- Trades per second (TPS)
- Buy/sell ratio
- Volume delta
"""

import asyncio
import logging
import time
from collections import deque
from dataclasses import dataclass
from typing import Dict, List, Optional, Any
import numpy as np


logger = logging.getLogger(__name__)


@dataclass
class Trade:
    """Individual trade data."""
    timestamp: int  # milliseconds
    price: float
    amount: float
    side: str  # 'buy' or 'sell'


@dataclass
class TradeMetrics:
    """Aggregated trade metrics for a symbol."""
    symbol: str
    tpm_10s: float = 0.0  # Trades per minute (10s window)
    tpm_60s: float = 0.0  # Trades per minute (60s window)
    tps_10s: float = 0.0  # Trades per second (10s window)
    buy_sell_ratio_60s: float = 0.0  # Buy/Sell ratio (60s window)
    vol_delta_10s: float = 0.0  # Volume delta (10s window)
    vol_delta_60s: float = 0.0  # Volume delta (60s window)
    vol_delta_300s: float = 0.0  # Volume delta (300s window)
    last_update: int = 0  # Timestamp of last update


class TradeWindow:
    """Rolling window for trade aggregation."""
    
    def __init__(self, window_seconds: int = 60):
        self.window_seconds = window_seconds
        self.trades: deque = deque()
        
    def add_trade(self, trade: Trade) -> None:
        """Add trade to window."""
        self.trades.append(trade)
        self._cleanup_old_trades(trade.timestamp)
    
    def _cleanup_old_trades(self, current_ts: int) -> None:
        """Remove trades older than window."""
        cutoff_ts = current_ts - (self.window_seconds * 1000)
        while self.trades and self.trades[0].timestamp < cutoff_ts:
            self.trades.popleft()
    
    def get_tpm(self, current_ts: int) -> float:
        """Get trades per minute."""
        self._cleanup_old_trades(current_ts)
        if not self.trades:
            return 0.0
        
        duration_minutes = self.window_seconds / 60
        return len(self.trades) / duration_minutes if duration_minutes > 0 else 0.0
    
    def get_tps(self, current_ts: int) -> float:
        """Get trades per second."""
        self._cleanup_old_trades(current_ts)
        if not self.trades:
            return 0.0
        
        return len(self.trades) / self.window_seconds if self.window_seconds > 0 else 0.0
    
    def get_buy_sell_ratio(self, current_ts: int) -> float:
        """Get buy/sell ratio."""
        self._cleanup_old_trades(current_ts)
        if not self.trades:
            return 0.0
        
        buy_count = sum(1 for t in self.trades if t.side == 'buy')
        sell_count = len(self.trades) - buy_count
        
        if sell_count == 0:
            return 1.0 if buy_count > 0 else 0.0
        
        return buy_count / sell_count
    
    def get_volume_delta(self, current_ts: int) -> float:
        """Get volume delta (buy_volume - sell_volume)."""
        self._cleanup_old_trades(current_ts)
        if not self.trades:
            return 0.0
        
        buy_volume = sum(t.amount for t in self.trades if t.side == 'buy')
        sell_volume = sum(t.amount for t in self.trades if t.side == 'sell')
        
        return buy_volume - sell_volume


class TradesAggregator:
    """
    Aggregates real-time trade data from Bybit WebSocket.
    
    Maintains rolling windows for different timeframes and calculates metrics.
    """
    
    def __init__(self, exchange_client=None):
        self.exchange_client = exchange_client
        self.active_symbols: Dict[str, bool] = {}
        self.windows: Dict[str, Dict[str, TradeWindow]] = {}
        self.metrics: Dict[str, TradeMetrics] = {}
        self.running = False
        self.tasks: List[asyncio.Task] = []
        self._latency_ms: float = 0.0
        
        # Bybit WebSocket integration
        self.bybit_ws = None
        self._use_real_ws = True  # Can be toggled for testing
        
        # Track subscribed symbols for property
        self.subscribed_symbols: set = set()
        
        logger.info("TradesAggregator initialized")
    
    async def start(self) -> None:
        """Start the aggregator."""
        if self.running:
            logger.warning("TradesAggregator already running")
            return
        
        self.running = True
        
        # Initialize Bybit WebSocket if using real data
        if self._use_real_ws:
            try:
                from ..exchange.bybit_websocket import BybitWebSocketClient
                
                self.bybit_ws = BybitWebSocketClient(
                    testnet=False,
                    on_trade=self._on_trade_update,
                    on_orderbook=None  # Not needed for trades
                )
                
                await self.bybit_ws.start()
                logger.info("Bybit WebSocket started for trades")
            
            except Exception as e:
                logger.error(f"Failed to start Bybit WebSocket: {e}")
                logger.warning("Falling back to simulation mode")
                self.bybit_ws = None
        
        logger.info("TradesAggregator started")
    
    async def stop(self) -> None:
        """Stop the aggregator."""
        if not self.running:
            return
        
        self.running = False
        
        # Stop Bybit WebSocket
        if self.bybit_ws:
            await self.bybit_ws.stop()
            self.bybit_ws = None
        
        # Cancel all tasks
        for task in self.tasks:
            task.cancel()
        
        if self.tasks:
            await asyncio.gather(*self.tasks, return_exceptions=True)
        
        self.tasks.clear()
        logger.info("TradesAggregator stopped")
    
    async def _on_trade_update(self, symbol: str, trade_data: Dict[str, Any]) -> None:
        """
        Callback for Bybit WebSocket trade updates.
        
        Args:
            symbol: Trading symbol
            trade_data: Trade data from Bybit
        """
        try:
            # Convert Bybit trade to our Trade format
            trade = Trade(
                timestamp=trade_data['timestamp'],
                price=trade_data['price'],
                amount=trade_data['amount'],
                side=trade_data['side']
            )
            
            # Add to windows
            self.add_trade(symbol, trade)
            
        except Exception as e:
            logger.error(f"Error processing trade update for {symbol}: {e}")
    
    async def subscribe(self, symbol: str) -> None:
        """Subscribe to trades for a symbol."""
        if symbol in self.active_symbols:
            logger.debug(f"Already subscribed to {symbol}")
            return
        
        self.active_symbols[symbol] = True
        self.subscribed_symbols.add(symbol)
        
        # Initialize windows
        self.windows[symbol] = {
            '10s': TradeWindow(10),
            '60s': TradeWindow(60),
            '300s': TradeWindow(300),
        }
        
        # Initialize metrics
        self.metrics[symbol] = TradeMetrics(symbol=symbol)
        
        # Subscribe via Bybit WebSocket
        if self.bybit_ws and self.bybit_ws.connected:
            try:
                await self.bybit_ws.subscribe_trades(symbol)
                logger.info(f"Subscribed to Bybit trades for {symbol}")
            except Exception as e:
                logger.error(f"Failed to subscribe to Bybit trades for {symbol}: {e}")
        else:
            logger.warning(f"Bybit WebSocket not connected, queuing subscription for {symbol}")
        
        # Start processing task for fallback simulation if WebSocket not available
        if not self.bybit_ws:
            task = asyncio.create_task(self._process_trades_simulated(symbol))
            self.tasks.append(task)
            logger.info(f"Started simulated trades for {symbol}")
    
    async def unsubscribe(self, symbol: str) -> None:
        """Unsubscribe from trades for a symbol."""
        if symbol not in self.active_symbols:
            return
        
        self.active_symbols[symbol] = False
        self.subscribed_symbols.discard(symbol)
        
        # Unsubscribe via Bybit WebSocket
        if self.bybit_ws and self.bybit_ws.connected:
            try:
                await self.bybit_ws.unsubscribe_trades(symbol)
                logger.info(f"Unsubscribed from Bybit trades for {symbol}")
            except Exception as e:
                logger.error(f"Failed to unsubscribe from Bybit trades for {symbol}: {e}")
        
        if symbol in self.windows:
            del self.windows[symbol]
        
        if symbol in self.metrics:
            del self.metrics[symbol]
        
        logger.info(f"Unsubscribed from trades for {symbol}")
    
    async def _process_trades_simulated(self, symbol: str) -> None:
        """
        Process incoming trades for a symbol (FALLBACK SIMULATION).
        
        This is only used when WebSocket is not available.
        In production with real WebSocket, this is not used.
        """
        try:
            while self.running and self.active_symbols.get(symbol, False):
                # Simulation mode - just update metrics periodically
                await asyncio.sleep(1)
                
                # Update metrics from windows
                current_ts = int(time.time() * 1000)
                self._update_metrics(symbol, current_ts)
                
        except asyncio.CancelledError:
            logger.debug(f"Trade processing for {symbol} cancelled")
        except Exception as e:
            logger.error(f"Error processing trades for {symbol}: {e}", exc_info=True)
    
    def _update_metrics(self, symbol: str, current_ts: int) -> None:
        """Update metrics for a symbol."""
        if symbol not in self.windows or symbol not in self.metrics:
            return
        
        windows = self.windows[symbol]
        metrics = self.metrics[symbol]
        
        # Update TPM and TPS
        metrics.tpm_10s = windows['10s'].get_tpm(current_ts)
        metrics.tpm_60s = windows['60s'].get_tpm(current_ts)
        metrics.tps_10s = windows['10s'].get_tps(current_ts)
        
        # Update buy/sell ratio
        metrics.buy_sell_ratio_60s = windows['60s'].get_buy_sell_ratio(current_ts)
        
        # Update volume deltas
        metrics.vol_delta_10s = windows['10s'].get_volume_delta(current_ts)
        metrics.vol_delta_60s = windows['60s'].get_volume_delta(current_ts)
        metrics.vol_delta_300s = windows['300s'].get_volume_delta(current_ts)
        
        metrics.last_update = current_ts
    
    def add_trade(self, symbol: str, trade: Trade) -> None:
        """
        Manually add a trade to the aggregator.
        
        Used for testing or when receiving trades from Bybit WebSocket.
        """
        if symbol not in self.windows:
            logger.warning(f"Symbol {symbol} not subscribed, ignoring trade")
            return
        
        # Add to all windows
        for window in self.windows[symbol].values():
            window.add_trade(trade)
        
        # Update metrics
        self._update_metrics(symbol, trade.timestamp)
    
    # Public API for accessing metrics
    
    def get_tpm(self, symbol: str, window: str = '60s') -> float:
        """Get trades per minute for a symbol."""
        if symbol not in self.metrics:
            return 0.0
        
        if window == '10s':
            return self.metrics[symbol].tpm_10s
        elif window == '60s':
            return self.metrics[symbol].tpm_60s
        else:
            return 0.0
    
    def get_tps(self, symbol: str, window: str = '10s') -> float:
        """Get trades per second for a symbol (10s window)."""
        if symbol not in self.metrics:
            return 0.0
        
        return self.metrics[symbol].tps_10s
    
    def get_vol_delta(self, symbol: str, window_s: int = 60) -> float:
        """Get volume delta for a symbol."""
        if symbol not in self.metrics:
            return 0.0
        
        metrics = self.metrics[symbol]
        
        if window_s <= 10:
            return metrics.vol_delta_10s
        elif window_s <= 60:
            return metrics.vol_delta_60s
        else:
            return metrics.vol_delta_300s
    
    def get_buy_sell_ratio(self, symbol: str) -> float:
        """Get buy/sell ratio for a symbol (60s window)."""
        if symbol not in self.metrics:
            return 0.0
        
        return self.metrics[symbol].buy_sell_ratio_60s
    
    def get_metrics(self, symbol: str) -> Optional[TradeMetrics]:
        """Get all metrics for a symbol."""
        return self.metrics.get(symbol)
    
    def get_latency_ms(self) -> float:
        """Get current WebSocket latency in milliseconds."""
        return self._latency_ms
    
    def is_subscribed(self, symbol: str) -> bool:
        """Check if subscribed to a symbol."""
        return symbol in self.active_symbols and self.active_symbols[symbol]
