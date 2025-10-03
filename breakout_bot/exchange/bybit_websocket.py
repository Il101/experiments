"""
Bybit WebSocket Client for real-time market data.

Handles:
- Public trades stream
- Order book (level 2) stream
- Connection management and reconnection
- Rate limiting and subscription management
"""

import asyncio
import json
import logging
import time
from typing import Dict, List, Optional, Callable, Any
import websockets
from websockets.client import WebSocketClientProtocol


logger = logging.getLogger(__name__)


class BybitWebSocketClient:
    """
    Bybit WebSocket client for public market data.
    
    Docs: https://bybit-exchange.github.io/docs/v5/ws/connect
    """
    
    # Bybit WebSocket URLs
    WS_URL_MAINNET = "wss://stream.bybit.com/v5/public/spot"
    WS_URL_TESTNET = "wss://stream-testnet.bybit.com/v5/public/spot"
    
    def __init__(
        self,
        testnet: bool = False,
        on_trade: Optional[Callable] = None,
        on_orderbook: Optional[Callable] = None,
        ping_interval: int = 20
    ):
        """
        Initialize Bybit WebSocket client.
        
        Args:
            testnet: Use testnet if True
            on_trade: Callback for trade updates: fn(symbol, trade_data)
            on_orderbook: Callback for orderbook updates: fn(symbol, orderbook_data)
            ping_interval: Ping interval in seconds
        """
        self.ws_url = self.WS_URL_TESTNET if testnet else self.WS_URL_MAINNET
        self.on_trade = on_trade
        self.on_orderbook = on_orderbook
        self.ping_interval = ping_interval
        
        # Connection state
        self.ws: Optional[WebSocketClientProtocol] = None
        self.running = False
        self.connected = False
        
        # Subscription tracking
        self.subscribed_symbols: Dict[str, Dict[str, bool]] = {}  # {symbol: {topic: True}}
        self.pending_subscriptions: List[Dict[str, Any]] = []
        
        # Tasks
        self.connection_task: Optional[asyncio.Task] = None
        self.ping_task: Optional[asyncio.Task] = None
        self.receive_task: Optional[asyncio.Task] = None
        
        # Reconnection
        self.reconnect_delay = 5
        self.max_reconnect_delay = 60
        
        logger.info(f"BybitWebSocketClient initialized (testnet={testnet})")
    
    async def start(self) -> None:
        """Start the WebSocket connection."""
        if self.running:
            logger.warning("WebSocket already running")
            return
        
        self.running = True
        self.connection_task = asyncio.create_task(self._connection_loop())
        logger.info("Bybit WebSocket client started")
    
    async def stop(self) -> None:
        """Stop the WebSocket connection."""
        if not self.running:
            return
        
        logger.info("Stopping Bybit WebSocket client...")
        self.running = False
        
        # Cancel tasks
        tasks = [
            self.connection_task,
            self.ping_task,
            self.receive_task
        ]
        
        for task in tasks:
            if task and not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        
        # Close WebSocket
        if self.ws and not self.ws.closed:
            await self.ws.close()
        
        self.connected = False
        logger.info("Bybit WebSocket client stopped")
    
    async def subscribe_trades(self, symbol: str) -> None:
        """
        Subscribe to public trades for a symbol.
        
        Args:
            symbol: Trading pair (e.g., 'BTCUSDT')
        """
        topic = f"publicTrade.{symbol}"
        await self._subscribe(symbol, topic, 'trades')
    
    async def subscribe_orderbook(self, symbol: str, depth: int = 50) -> None:
        """
        Subscribe to order book updates for a symbol.
        
        Args:
            symbol: Trading pair (e.g., 'BTCUSDT')
            depth: Order book depth (1, 50, 200, 500)
        """
        topic = f"orderbook.{depth}.{symbol}"
        await self._subscribe(symbol, topic, 'orderbook')
    
    async def unsubscribe_trades(self, symbol: str) -> None:
        """Unsubscribe from trades for a symbol."""
        topic = f"publicTrade.{symbol}"
        await self._unsubscribe(symbol, topic, 'trades')
    
    async def unsubscribe_orderbook(self, symbol: str, depth: int = 50) -> None:
        """Unsubscribe from orderbook for a symbol."""
        topic = f"orderbook.{depth}.{symbol}"
        await self._unsubscribe(symbol, topic, 'orderbook')
    
    async def _subscribe(self, symbol: str, topic: str, stream_type: str) -> None:
        """Internal subscribe method."""
        # Track subscription
        if symbol not in self.subscribed_symbols:
            self.subscribed_symbols[symbol] = {}
        
        if topic in self.subscribed_symbols[symbol]:
            logger.debug(f"Already subscribed to {topic}")
            return
        
        self.subscribed_symbols[symbol][topic] = True
        
        # Send subscription if connected
        if self.connected and self.ws:
            await self._send_subscribe([topic])
            logger.info(f"Subscribed to {topic}")
        else:
            # Queue for later
            self.pending_subscriptions.append({'op': 'subscribe', 'args': [topic]})
            logger.debug(f"Queued subscription to {topic}")
    
    async def _unsubscribe(self, symbol: str, topic: str, stream_type: str) -> None:
        """Internal unsubscribe method."""
        if symbol not in self.subscribed_symbols:
            return
        
        if topic not in self.subscribed_symbols[symbol]:
            return
        
        del self.subscribed_symbols[symbol][topic]
        
        if not self.subscribed_symbols[symbol]:
            del self.subscribed_symbols[symbol]
        
        # Send unsubscribe if connected
        if self.connected and self.ws:
            await self._send_unsubscribe([topic])
            logger.info(f"Unsubscribed from {topic}")
    
    async def _connection_loop(self) -> None:
        """Main connection loop with reconnection logic."""
        reconnect_delay = self.reconnect_delay
        
        while self.running:
            try:
                logger.info(f"Connecting to Bybit WebSocket: {self.ws_url}")
                
                async with websockets.connect(
                    self.ws_url,
                    ping_interval=None,  # We handle ping ourselves
                    close_timeout=10
                ) as ws:
                    self.ws = ws
                    self.connected = True
                    reconnect_delay = self.reconnect_delay  # Reset delay on successful connection
                    
                    logger.info("Bybit WebSocket connected")
                    
                    # Start ping task
                    self.ping_task = asyncio.create_task(self._ping_loop())
                    
                    # Resubscribe to all topics
                    await self._resubscribe_all()
                    
                    # Start receiving messages
                    self.receive_task = asyncio.create_task(self._receive_loop())
                    
                    # Wait for receive task to finish (connection lost or error)
                    await self.receive_task
                    
            except asyncio.CancelledError:
                logger.debug("Connection loop cancelled")
                break
            
            except Exception as e:
                logger.error(f"WebSocket connection error: {e}")
            
            finally:
                self.connected = False
                
                # Cancel ping task
                if self.ping_task and not self.ping_task.done():
                    self.ping_task.cancel()
                    try:
                        await self.ping_task
                    except asyncio.CancelledError:
                        pass
            
            # Reconnect with exponential backoff
            if self.running:
                logger.info(f"Reconnecting in {reconnect_delay} seconds...")
                await asyncio.sleep(reconnect_delay)
                reconnect_delay = min(reconnect_delay * 2, self.max_reconnect_delay)
    
    async def _receive_loop(self) -> None:
        """Receive and process messages from WebSocket."""
        try:
            async for message in self.ws:
                if isinstance(message, bytes):
                    message = message.decode('utf-8')
                
                try:
                    data = json.loads(message)
                    await self._handle_message(data)
                
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to decode message: {e}")
                except Exception as e:
                    logger.error(f"Error handling message: {e}", exc_info=True)
        
        except asyncio.CancelledError:
            logger.debug("Receive loop cancelled")
        except Exception as e:
            logger.error(f"Receive loop error: {e}")
    
    async def _ping_loop(self) -> None:
        """Send ping messages to keep connection alive."""
        try:
            while self.connected:
                await asyncio.sleep(self.ping_interval)
                
                if self.ws and not self.ws.closed:
                    ping_msg = json.dumps({"op": "ping"})
                    await self.ws.send(ping_msg)
                    logger.debug("Sent ping")
        
        except asyncio.CancelledError:
            logger.debug("Ping loop cancelled")
        except Exception as e:
            logger.error(f"Ping loop error: {e}")
    
    async def _handle_message(self, data: Dict[str, Any]) -> None:
        """Handle incoming WebSocket message."""
        # Response to operations
        if 'op' in data:
            op = data['op']
            
            if op == 'pong':
                logger.debug("Received pong")
                return
            
            elif op == 'subscribe':
                if data.get('success'):
                    logger.debug(f"Subscription confirmed: {data.get('req_id')}")
                else:
                    logger.error(f"Subscription failed: {data}")
                return
            
            elif op == 'unsubscribe':
                if data.get('success'):
                    logger.debug(f"Unsubscription confirmed: {data.get('req_id')}")
                return
        
        # Market data updates
        if 'topic' in data:
            topic = data['topic']
            
            # Public trades
            if topic.startswith('publicTrade.'):
                symbol = topic.split('.')[1]
                await self._handle_trade_update(symbol, data)
            
            # Order book
            elif topic.startswith('orderbook.'):
                parts = topic.split('.')
                symbol = parts[2] if len(parts) >= 3 else None
                if symbol:
                    await self._handle_orderbook_update(symbol, data)
    
    async def _handle_trade_update(self, symbol: str, data: Dict[str, Any]) -> None:
        """Handle trade update message."""
        try:
            if 'data' not in data:
                return
            
            trades = data['data']
            if not isinstance(trades, list):
                trades = [trades]
            
            for trade in trades:
                # Bybit trade format:
                # {
                #   "i": "2290000000061666327",  # Trade ID
                #   "T": 1672304486868,          # Timestamp
                #   "p": "16578.50",             # Price
                #   "v": "0.141596",             # Volume
                #   "S": "Buy"                   # Side (Buy/Sell)
                # }
                
                trade_data = {
                    'id': trade.get('i'),
                    'timestamp': trade.get('T'),
                    'price': float(trade.get('p', 0)),
                    'amount': float(trade.get('v', 0)),
                    'side': 'buy' if trade.get('S') == 'Buy' else 'sell'
                }
                
                if self.on_trade:
                    await self.on_trade(symbol, trade_data)
        
        except Exception as e:
            logger.error(f"Error handling trade update for {symbol}: {e}")
    
    async def _handle_orderbook_update(self, symbol: str, data: Dict[str, Any]) -> None:
        """Handle orderbook update message."""
        try:
            if 'data' not in data:
                return
            
            ob_data = data['data']
            update_type = data.get('type', 'snapshot')
            
            # Bybit orderbook format:
            # {
            #   "s": "BTCUSDT",
            #   "b": [["16493.50", "0.006"], ...],  # Bids
            #   "a": [["16611.00", "0.029"], ...],  # Asks
            #   "u": 177400507,                      # Update ID
            #   "seq": 7961638724                    # Sequence number
            # }
            
            orderbook_data = {
                'symbol': ob_data.get('s', symbol),
                'bids': [[float(p), float(v)] for p, v in ob_data.get('b', [])],
                'asks': [[float(p), float(v)] for p, v in ob_data.get('a', [])],
                'timestamp': data.get('ts', int(time.time() * 1000)),
                'update_id': ob_data.get('u'),
                'type': update_type  # 'snapshot' or 'delta'
            }
            
            if self.on_orderbook:
                await self.on_orderbook(symbol, orderbook_data)
        
        except Exception as e:
            logger.error(f"Error handling orderbook update for {symbol}: {e}")
    
    async def _send_subscribe(self, topics: List[str]) -> None:
        """Send subscribe message."""
        if not self.ws or self.ws.closed:
            return
        
        msg = {
            "op": "subscribe",
            "args": topics
        }
        
        await self.ws.send(json.dumps(msg))
    
    async def _send_unsubscribe(self, topics: List[str]) -> None:
        """Send unsubscribe message."""
        if not self.ws or self.ws.closed:
            return
        
        msg = {
            "op": "unsubscribe",
            "args": topics
        }
        
        await self.ws.send(json.dumps(msg))
    
    async def _resubscribe_all(self) -> None:
        """Resubscribe to all topics after reconnection."""
        # Process pending subscriptions first
        if self.pending_subscriptions:
            for sub in self.pending_subscriptions:
                topics = sub.get('args', [])
                if topics:
                    await self._send_subscribe(topics)
            
            self.pending_subscriptions.clear()
        
        # Resubscribe to active topics
        all_topics = []
        for symbol_topics in self.subscribed_symbols.values():
            all_topics.extend(symbol_topics.keys())
        
        if all_topics:
            # Subscribe in batches of 10 (Bybit limit)
            batch_size = 10
            for i in range(0, len(all_topics), batch_size):
                batch = all_topics[i:i + batch_size]
                await self._send_subscribe(batch)
                await asyncio.sleep(0.1)  # Small delay between batches
            
            logger.info(f"Resubscribed to {len(all_topics)} topics")
