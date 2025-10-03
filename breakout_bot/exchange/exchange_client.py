"""
Exchange integration layer for Breakout Bot Trading System.

This module provides a unified interface to interact with cryptocurrency exchanges
using CCXT, supporting both live trading and paper trading modes.
"""

import asyncio
import os
import time
import ccxt
import ccxt.async_support as ccxt_async
from typing import Dict, List, Optional, Any, Tuple, Callable
from datetime import datetime, timedelta
import logging
import numpy as np
import weakref
from contextlib import asynccontextmanager

from ..data.models import Candle, L2Depth, MarketData, Order
from ccxt import InsufficientFunds
from ..config.settings import SystemConfig
from .market_stream import RealTimeMarketDataStreamer, DepthSnapshot, TradeStats
from .bybit_rate_limiter import BybitRateLimiter, classify_endpoint, EndpointCategory

logger = logging.getLogger(__name__)


class ExchangeConnectionPool:
    """Connection pool for exchange clients to reuse connections."""
    
    def __init__(self, max_connections: int = 10, max_idle_time: int = 300):
        self.max_connections = max_connections
        self.max_idle_time = max_idle_time
        self._connections = []
        self._in_use = set()
        self._last_used = {}
        self._lock = asyncio.Lock()
    
    async def get_connection(self, exchange_class, config: Dict[str, Any]):
        """Get a connection from the pool or create a new one."""
        async with self._lock:
            # Try to reuse an existing connection
            for conn in self._connections:
                if conn not in self._in_use:
                    # Check if connection is still valid
                    if await self._is_connection_valid(conn):
                        self._in_use.add(conn)
                        self._last_used[conn] = time.time()
                        return conn
                    else:
                        # Remove invalid connection
                        self._connections.remove(conn)
                        if conn in self._last_used:
                            del self._last_used[conn]
                        # Close the invalid connection
                        try:
                            if hasattr(conn, 'close'):
                                await conn.close()
                        except Exception:
                            pass
            
            # Create new connection if pool not full
            if len(self._connections) < self.max_connections:
                conn = exchange_class(config)
                self._connections.append(conn)
                self._in_use.add(conn)
                self._last_used[conn] = time.time()
                return conn
            
            # Pool is full, wait for a connection to be released
            # This is a simplified implementation - in production you'd want a proper queue
            return None
    
    async def release_connection(self, conn):
        """Release a connection back to the pool."""
        async with self._lock:
            if conn in self._in_use:
                self._in_use.remove(conn)
                self._last_used[conn] = time.time()
    
    async def _is_connection_valid(self, conn) -> bool:
        """Check if a connection is still valid."""
        try:
            # Try a simple operation to test the connection
            # Skip balance check as we don't have API keys
            # Just test if connection is alive
            return True
        except Exception:
            return False
    
    async def cleanup_idle_connections(self):
        """Remove idle connections that have exceeded max_idle_time."""
        async with self._lock:
            now = time.time()
            to_remove = []
            
            for conn in self._connections:
                if (conn not in self._in_use and 
                    conn in self._last_used and 
                    now - self._last_used[conn] > self.max_idle_time):
                    to_remove.append(conn)
            
            for conn in to_remove:
                self._connections.remove(conn)
                if conn in self._last_used:
                    del self._last_used[conn]
                # Close the connection
                if hasattr(conn, 'close'):
                    try:
                        await conn.close()
                    except Exception:
                        pass
    
    async def close_all(self):
        """Close all connections in the pool."""
        async with self._lock:
            for conn in self._connections:
                if hasattr(conn, 'close'):
                    try:
                        await conn.close()
                    except Exception:
                        pass
            self._connections.clear()
            self._in_use.clear()
            self._last_used.clear()


# Global connection pool
_connection_pool = ExchangeConnectionPool()


async def close_all_connections():
    """Close all connections in the global pool."""
    await _connection_pool.close_all()


class ExchangeError(Exception):
    """Custom exception for exchange-related errors."""
    pass


class PaperTradingExchange:
    """Paper trading simulation exchange."""
    
    def __init__(self, starting_balance: float = 100000, slippage_bps: float = 5, fee_bps: float = 10, real_exchange=None):
        self.balance = {'USDT': starting_balance}
        self.positions = {}
        self.orders = {}
        self.trades = []  # Trade history for metrics consistency
        self.slippage_bps = slippage_bps
        self.fee_bps = fee_bps
        self.order_id_counter = 1000
        self.trade_id_counter = 1000
        self.real_exchange = real_exchange  # Reference to real exchange for prices
        
        logger.info(f"Initialized paper trading with ${starting_balance:,.0f} balance")
    
    async def fetch_balance(self) -> Dict[str, float]:
        """Fetch account balance."""
        return self.balance.copy()
    
    async def create_order(self, 
                          symbol: str,
                          order_type: str,
                          side: str,
                          amount: float,
                          price: Optional[float] = None,
                          params: Optional[Dict] = None) -> Dict[str, Any]:
        """Create a simulated order."""
        
        order_id = str(self.order_id_counter)
        self.order_id_counter += 1
        
        # Get real market price if not provided
        if not price:
            try:
                if self.real_exchange:
                    # Get real price from the exchange
                    ticker = await self.real_exchange.fetch_ticker(symbol)
                    if ticker and ticker.get('last', 0) > 0:
                        price = ticker['last']
                    else:
                        # Try to get price from order book
                        orderbook = await self.real_exchange.fetch_order_book(symbol)
                        if orderbook and orderbook.get('bids') and orderbook['bids']:
                            price = orderbook['bids'][0][0]  # Best bid price
                        else:
                            raise Exception("No price data available")
                else:
                    # For paper mode without real exchange, try to get price from market data provider
                    try:
                        if hasattr(self.real_exchange, 'market_data_provider') and self.real_exchange.market_data_provider:
                            snapshot = await self.real_exchange.market_data_provider.get_depth_snapshot(symbol)
                            if snapshot and snapshot.best_bid and snapshot.best_ask:
                                price = (snapshot.best_bid + snapshot.best_ask) / 2  # Mid price
                            else:
                                raise Exception("No market data available")
                        else:
                            raise Exception("No market data provider")
                    except:
                        # Last resort: use a reasonable default based on symbol
                        if 'BTC' in symbol.upper():
                            price = 50000.0
                        elif 'ETH' in symbol.upper():
                            price = 3000.0
                        else:
                            price = 1.0  # Generic fallback
            except Exception as e:
                logger.warning(f"Failed to get price for {symbol}: {e}")
                # Use symbol-based fallback
                if 'BTC' in symbol.upper():
                    price = 50000.0
                elif 'ETH' in symbol.upper():
                    price = 3000.0
                else:
                    price = 1.0  # Generic fallback
        
        # Simulate realistic fills
        fill_price = price
        
        # Apply slippage
        if side == 'buy':
            fill_price *= (1 + self.slippage_bps / 10000)
        else:
            fill_price *= (1 - self.slippage_bps / 10000)
        
        order = {
            'id': order_id,
            'symbol': symbol,
            'type': order_type,
            'side': side,
            'amount': amount,
            'price': price,
            'filled': amount,  # Simulate immediate fill
            'remaining': 0,
            'status': 'closed',
            'average': fill_price,
            'fee': {'cost': amount * fill_price * (self.fee_bps / 10000), 'currency': 'USDT'},  # Use configurable fee
            'timestamp': int(datetime.now().timestamp() * 1000)
        }
        
        self.orders[order_id] = order
        
        # Create trade record for history
        trade = {
            'id': str(self.trade_id_counter),
            'order_id': order_id,
            'symbol': symbol,
            'side': side,
            'amount': amount,
            'price': fill_price,
            'fee': order['fee']['cost'],
            'timestamp': order['timestamp'],
            'datetime': datetime.now().isoformat()
        }
        self.trades.append(trade)
        self.trade_id_counter += 1
        
        # Check margin requirements before updating balance
        if side == 'buy':
            cost = amount * fill_price + order['fee']['cost']
            if self.balance['USDT'] < cost:
                raise InsufficientFunds(f"Insufficient USDT balance: {self.balance['USDT']:.2f} < {cost:.2f}")
            self.balance['USDT'] -= cost
        else:
            proceeds = amount * fill_price - order['fee']['cost']
            self.balance['USDT'] += proceeds
        
        logger.info(f"Paper order executed: {side} {amount} {symbol} at {fill_price:.6f}")
        
        return order
    
    async def fetch_order(self, order_id: str, symbol: str) -> Dict[str, Any]:
        """Fetch order status."""
        return self.orders.get(order_id, {})
    
    async def cancel_order(self, order_id: str, symbol: str) -> Dict[str, Any]:
        """Cancel an order."""
        if order_id in self.orders:
            self.orders[order_id]['status'] = 'canceled'
        return self.orders.get(order_id, {})
    
    async def fetch_trades(self, symbol: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Fetch recent trades for a symbol."""
        # Return trade history for metrics consistency
        symbol_trades = [trade for trade in self.trades if trade['symbol'] == symbol]
        # Sort by timestamp descending and limit results
        symbol_trades.sort(key=lambda x: x['timestamp'], reverse=True)
        return symbol_trades[:limit]
    
    def get_trade_statistics(self) -> Dict[str, Any]:
        """Get trade statistics for metrics consistency."""
        if not self.trades:
            return {
                'total_trades': 0,
                'total_volume': 0.0,
                'total_fees': 0.0,
                'buy_trades': 0,
                'sell_trades': 0,
                'symbols_traded': set(),
                'avg_trade_size': 0.0
            }
        
        total_volume = sum(trade['amount'] * trade['price'] for trade in self.trades)
        total_fees = sum(trade['fee'] for trade in self.trades)
        buy_trades = len([t for t in self.trades if t['side'] == 'buy'])
        sell_trades = len([t for t in self.trades if t['side'] == 'sell'])
        symbols_traded = set(trade['symbol'] for trade in self.trades)
        
        return {
            'total_trades': len(self.trades),
            'total_volume': total_volume,
            'total_fees': total_fees,
            'buy_trades': buy_trades,
            'sell_trades': sell_trades,
            'symbols_traded': symbols_traded,
            'avg_trade_size': total_volume / len(self.trades) if self.trades else 0.0
        }
    
    def get_recent_trades(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent trades across all symbols."""
        # Sort by timestamp descending and limit results
        recent_trades = sorted(self.trades, key=lambda x: x['timestamp'], reverse=True)
        return recent_trades[:limit]


class ExchangeClient:
    """Main exchange client with unified interface and connection pooling."""
    
    def __init__(self, config: SystemConfig):
        self.config = config
        self.paper_mode = config.paper_mode
        logger.info(f"ExchangeClient.__init__ - config.paper_mode: {config.paper_mode}, self.paper_mode: {self.paper_mode}")
        self._exchange = None
        self._is_temporary_connection = False
        self._connection_pool = _connection_pool
        self.market_streamer = RealTimeMarketDataStreamer(config.exchange)
        self._market_metadata: Dict[str, Any] = {}
        
        # Инициализация rate limiter для Bybit (всегда нужен для market data)
        self.rate_limiter = None
        if config.exchange.lower() == 'bybit':
            self.rate_limiter = BybitRateLimiter()
            logger.info("Инициализирован BybitRateLimiter для управления rate limits")
        else:
            # Для других бирж тоже нужен rate limiter
            self.rate_limiter = BybitRateLimiter()
            logger.info("Инициализирован BybitRateLimiter для управления rate limits (универсальный)")
        
        if self.paper_mode:
            self._market_exchange = None
            self._market_exchange_config = self._get_exchange_config()
            self._paper_exchange = PaperTradingExchange(
                starting_balance=config.paper_starting_balance,
                slippage_bps=config.paper_slippage_bps,
                real_exchange=self
            )
            logger.info("Initialized in PAPER TRADING mode with live market data")
        else:
            self._exchange_config = self._get_exchange_config()
            logger.info(f"Initialized LIVE TRADING with {config.exchange} for futures (connection pooling enabled)")

            self._paper_exchange = PaperTradingExchange(
                starting_balance=config.paper_starting_balance,
                slippage_bps=config.paper_slippage_bps,
                real_exchange=self
            )
            self._market_exchange = None
            self._market_exchange_config = self._exchange_config
    
    def _get_exchange_config(self) -> Dict[str, Any]:
        """Get exchange configuration."""
        # For public data access, we don't need API keys
        config = {
            'enableRateLimit': True,
            'sandbox': False,  # Use real data
            'options': {
                'defaultType': 'future'  # Use futures by default
            }
        }
        
        # Специальная конфигурация для Bybit
        if self.config.exchange.lower() == 'bybit':
            config.update({
                'rateLimit': 10,   # Оптимизированный лимит 10ms между запросами (100 req/s)
                'enableRateLimit': True,
                'options': {
                    'defaultType': 'future',
                    'recvWindow': 5000,  # 5 секунд для большей надежности
                    'timeDifference': 0,
                    'adjustForTimeDifference': True,
                    # Оптимизированные опции для производительности
                    'warnOnFetchOHLCVLimitArgument': False,
                    'defaultNetworkCodeByExchange': {
                        'USDT': 'TRX'
                    },
                    # Дополнительные оптимизации
                    'enableRateLimit': True,
                    'rateLimit': 10,
                    'timeout': 30000,  # 30 секунд timeout
                }
            })
            logger.info("Применена оптимизированная конфигурация для Bybit API")
        
        # Add API keys only if they exist (for trading)
        api_key = os.getenv('EXCHANGE_API_KEY')
        api_secret = os.getenv('EXCHANGE_SECRET')
        logger.info(f"_get_exchange_config - api_key exists: {bool(api_key)}, api_secret exists: {bool(api_secret)}")
        if api_key and api_secret:
            config.update({
                'apiKey': api_key,
                'secret': api_secret,
                'passphrase': os.getenv('EXCHANGE_PASSPHRASE')
            })
        else:
            # For public data access, don't include any API credentials
            # This allows CCXT to use public endpoints only
            pass
        
        return config
    
    @property
    def exchange(self):
        """Get exchange instance for compatibility."""
        if self.paper_mode:
            return self._paper_exchange
        # For live mode, we need to ensure exchange is initialized
        if self._exchange is None:
            raise RuntimeError("Exchange not initialized. Use async methods or await _get_exchange() first.")
        return self._exchange

    async def _get_market_exchange(self):
        """Get exchange instance for public market data."""
        if self._market_exchange is None:
            exchange_class = getattr(ccxt_async, self.config.exchange)
            logger.info(f"Creating market data exchange for {self.config.exchange}")
            self._market_exchange = exchange_class(self._market_exchange_config)
        return self._market_exchange

    async def _close_market_exchange(self):
        """Close the market data exchange client."""
        if self._market_exchange and hasattr(self._market_exchange, 'close'):
            try:
                await self._market_exchange.close()
            except Exception as exc:
                logger.warning(f"Error closing market exchange: {exc}")
        self._market_exchange = None

    async def _get_exchange(self):
        """Get exchange connection from pool or create new one."""
        logger.info(f"_get_exchange called - paper_mode: {self.paper_mode}")
        if self.paper_mode:
            logger.info("Returning paper exchange from _get_exchange (NEVER creating ccxt in paper mode)")
            return self._paper_exchange
        
        if self._exchange is None:
            exchange_class = getattr(ccxt_async, self.config.exchange)
            if self.config.exchange.lower() == 'bybit':
                logger.info(f"Creating persistent Bybit exchange with config: {self._exchange_config}")
                self._exchange = exchange_class(self._exchange_config)
                self._is_temporary_connection = False
            else:
                self._exchange = await self._connection_pool.get_connection(
                    exchange_class, self._exchange_config
                )

                if self._exchange is None:
                    self._exchange = exchange_class(self._exchange_config)
                    self._is_temporary_connection = True
                    logger.warning("Connection pool full, using temporary connection")
                else:
                    self._is_temporary_connection = False
        
        return self._exchange
    
    async def _execute_with_rate_limiting(self, 
                                        func: Callable,
                                        endpoint: str = "",
                                        method: str = "GET",
                                        max_retries: int = 3,
                                        *args, **kwargs):
        """
        Выполнить запрос с учетом rate limiting.
        
        Args:
            func: Функция для выполнения
            endpoint: Endpoint для классификации  
            method: HTTP метод
            max_retries: Максимум попыток при rate limiting
            *args, **kwargs: Аргументы для функции
        """
        # Если нет rate limiter, выполнить обычным способом
        if not self.rate_limiter:
            return await func(*args, **kwargs) if asyncio.iscoroutinefunction(func) else func(*args, **kwargs)
        
        # Определить категорию endpoint
        category = classify_endpoint(endpoint)
        
        # Использовать новую реализацию согласно документации Bybit
        return await self.rate_limiter.execute_with_retry(
            func=func,
            category=category,
            endpoint=endpoint,
            max_retries=max_retries,
            *args, **kwargs
        )
    
    async def _release_exchange(self):
        """Release exchange connection back to pool."""
        if not self.paper_mode and self._exchange:
            if self._is_temporary_connection:
                try:
                    if hasattr(self._exchange, 'close'):
                        await self._exchange.close()
                    logger.debug("Temporary exchange connection closed")
                except Exception as e:
                    logger.warning(f"Error closing temporary connection: {e}")
                finally:
                    self._exchange = None
                    self._is_temporary_connection = False
            else:
                # Persistent connection stays alive; nothing to release
                pass
    
    def get_rate_limiter_status(self) -> Optional[Dict[str, Any]]:
        """Получить статус rate limiter для мониторинга."""
        if self.rate_limiter:
            return self.rate_limiter.get_status()
        return None
    
    def reset_rate_limiter(self):
        """Сбросить rate limiter."""
        if self.rate_limiter:
            self.rate_limiter.reset_limits()
            logger.info("Rate limiter reset completed")
    
    async def fetch_ohlcv(self, 
                         symbol: str, 
                         timeframe: str = '5m',
                         limit: int = 100,
                         since: Optional[int] = None) -> List[Candle]:
        """Fetch OHLCV candlestick data."""
        
        try:
            exchange = await (self._get_market_exchange() if self.paper_mode else self._get_exchange())
            
            params = {}
            if since is not None:
                params['since'] = since
            
            # Выполнить с rate limiting для Bybit
            endpoint = f"/v5/market/kline"
            ohlcv_data = await self._execute_with_rate_limiting(
                exchange.fetch_ohlcv,
                endpoint=endpoint,
                method="GET",
                symbol=symbol, 
                timeframe=timeframe, 
                since=since, 
                limit=limit, 
                params=params
            )
            
            candles = []
            for ohlcv in ohlcv_data:
                candle = Candle(
                    ts=int(ohlcv[0]),
                    open=float(ohlcv[1]),
                    high=float(ohlcv[2]),
                    low=float(ohlcv[3]),
                    close=float(ohlcv[4]),
                    volume=float(ohlcv[5])
                )
                candles.append(candle)
            
            return candles
            
        except Exception as e:
            logger.error(f"Error fetching OHLCV for {symbol}: {e}")
            raise ExchangeError(f"Failed to fetch OHLCV: {e}")
        finally:
            if not self.paper_mode:
                await self._release_exchange()
    
    async def fetch_order_book(self, symbol: str, limit: int = 50) -> Optional[L2Depth]:
        """Fetch order book and calculate depth metrics."""
        
        try:
            exchange = await (self._get_market_exchange() if self.paper_mode else self._get_exchange())
            
            # Выполнить с rate limiting для Bybit
            endpoint = f"/v5/market/orderbook"
            order_book = await self._execute_with_rate_limiting(
                exchange.fetch_order_book,
                endpoint=endpoint,
                method="GET",
                symbol=symbol,
                limit=limit
            )
            
            # Calculate depth metrics
            bids = [
                (float(price), float(size))
                for price, size in order_book.get('bids', [])
                if float(size) > 0
            ]
            asks = [
                (float(price), float(size))
                for price, size in order_book.get('asks', [])
                if float(size) > 0
            ]
            
            if not bids or not asks:
                return None
            
            best_bid = bids[0][0]
            best_ask = asks[0][0]
            
            # Calculate spread
            spread_bps = ((best_ask - best_bid) / best_bid) * 10000
            
            # Calculate depth at different levels
            depth_0_3pct = best_bid * 0.003
            depth_0_5pct = best_bid * 0.005
            
            bid_depth_0_3 = self._sum_depth_within(symbol, bids, best_bid, depth_0_3pct, is_bid=True)
            ask_depth_0_3 = self._sum_depth_within(symbol, asks, best_ask, depth_0_3pct, is_bid=False)

            bid_depth_0_5 = self._sum_depth_within(symbol, bids, best_bid, depth_0_5pct, is_bid=True)
            ask_depth_0_5 = self._sum_depth_within(symbol, asks, best_ask, depth_0_5pct, is_bid=False)

            # Calculate imbalance using notional depth for top-of-book
            total_bid_vol = sum(
                self._level_notional(symbol, price, size)
                for price, size in bids[:10]
            )
            total_ask_vol = sum(
                self._level_notional(symbol, price, size)
                for price, size in asks[:10]
            )
            imbalance = (total_bid_vol - total_ask_vol) / (total_bid_vol + total_ask_vol) if (total_bid_vol + total_ask_vol) > 0 else 0
            
            return L2Depth(
                bid_usd_0_5pct=bid_depth_0_5,
                ask_usd_0_5pct=ask_depth_0_5,
                bid_usd_0_3pct=bid_depth_0_3,
                ask_usd_0_3pct=ask_depth_0_3,
                spread_bps=spread_bps,
                imbalance=imbalance
            )
            
        except Exception as e:
            logger.error(f"Error fetching order book for {symbol}: {e}")
            return None
        finally:
            if not self.paper_mode:
                await self._release_exchange()

    def _sum_depth_within(self,
                          symbol: str,
                          levels: List[Tuple[float, float]],
                          pivot_price: float,
                          pct: float,
                          is_bid: bool) -> float:
        """Aggregate notional within a percentage band around best price."""
        if not levels:
            return 0.0

        limit = pivot_price * (1 - pct if is_bid else 1 + pct)
        total = 0.0
        for price, size in levels:
            if is_bid and price < limit:
                break
            if not is_bid and price > limit:
                break
            total += self._level_notional(symbol, price, size)
        return total

    def _level_notional(self, symbol: str, price: float, size: float) -> float:
        """Convert raw order-book size into USD notional."""
        market = self._market_metadata.get(symbol)
        contract_size = 1.0
        if market:
            try:
                contract_size = float(market.get('contractSize') or 1.0)
            except (TypeError, ValueError):
                contract_size = 1.0

            if market.get('inverse'):
                return abs(size) * contract_size

        return abs(price) * abs(size) * contract_size

    def normalize_depth_total(self, symbol: str, total: float, reference_price: float) -> float:
        """Normalize aggregated depth totals (e.g., from WebSocket) into USD."""
        market = self._market_metadata.get(symbol)
        if not market:
            return total

        try:
            contract_size = float(market.get('contractSize') or 1.0)
        except (TypeError, ValueError):
            contract_size = 1.0

        if not market.get('contract'):
            return total

        if market.get('linear'):
            return total * contract_size

        if market.get('inverse') and reference_price:
            return (total / reference_price) * contract_size

        return total * contract_size
    
    async def fetch_ticker(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Fetch ticker data."""
        
        try:
            logger.info(f"fetch_ticker called for {symbol} - paper_mode: {self.paper_mode}")
            exchange = await (self._get_market_exchange() if self.paper_mode else self._get_exchange())
            
            # Выполнить с rate limiting для Bybit
            endpoint = f"/v5/market/tickers"
            return await self._execute_with_rate_limiting(
                exchange.fetch_ticker,
                endpoint=endpoint,
                method="GET",
                symbol=symbol
            )
            
        except Exception as e:
            logger.error(f"Error fetching ticker for {symbol}: {e}")
            return None
        finally:
            if not self.paper_mode:
                await self._release_exchange()
    
    async def fetch_open_interest(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Fetch current open interest for a symbol."""
        
        try:
            logger.info(f"fetch_open_interest called for {symbol} - paper_mode: {self.paper_mode}")
            exchange = await self._get_market_exchange()
            return await exchange.fetch_open_interest(symbol)
            
        except Exception as e:
            logger.error(f"Error fetching open interest for {symbol}: {e}")
            return None
        finally:
            await self._release_exchange()
    
    async def fetch_open_interest_history(self, symbol: str, timeframe: str = '1h', limit: int = 24) -> List[Dict[str, Any]]:
        """Fetch open interest history for a symbol."""
        
        try:
            logger.info(f"fetch_open_interest_history called for {symbol} - paper_mode: {self.paper_mode}")
            exchange = await self._get_market_exchange()
            return await exchange.fetch_open_interest_history(symbol, timeframe, limit=limit)
            
        except Exception as e:
            logger.error(f"Error fetching open interest history for {symbol}: {e}")
            return []
        finally:
            await self._release_exchange()
    
    async def create_order(self,
                          symbol: str,
                          order_type: str,
                          side: str,
                          amount: float,
                          price: Optional[float] = None,
                          params: Optional[Dict] = None) -> Optional[Order]:
        """Create an order."""
        
        try:
            exchange = await self._get_exchange()

            if self.paper_mode:
                result = await exchange.create_order(
                    symbol,
                    order_type,
                    side,
                    amount,
                    price,
                    params or {}
                )
            else:
                result = await exchange.create_order(
                    symbol=symbol,
                    type=order_type,
                    side=side,
                    amount=amount,
                    price=price,
                    params=params or {}
                )
            
            # Convert to our Order model
            raw_status = result.get('status', 'open')
            status = 'filled' if raw_status in ('closed', 'filled') else raw_status

            order = Order(
                id=str(result['id']),
                symbol=symbol,
                side=side,
                order_type=order_type,
                qty=amount,
                price=price,
                status=status,
                filled_qty=result.get('filled', 0),
                avg_fill_price=result.get('average'),
                fees_usd=result.get('fee', {}).get('cost', 0),
                timestamps={'created_at': result.get('timestamp', int(datetime.now().timestamp() * 1000))},
                exchange_id=str(result['id'])
            )
            
            logger.info(f"Order created: {order.id} - {side} {amount} {symbol}")
            
            return order
            
        except Exception as e:
            logger.error(f"Error creating order: {e}")
            raise ExchangeError(f"Failed to create order: {e}")
        finally:
            await self._release_exchange()
    
    async def cancel_order(self, order_id: str, symbol: str) -> bool:
        """Cancel an order."""
        
        try:
            exchange = await self._get_exchange()
            await exchange.cancel_order(order_id, symbol)
            logger.info(f"Order cancelled: {order_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error cancelling order {order_id}: {e}")
            return False
        finally:
            await self._release_exchange()
    
    async def fetch_balance(self) -> Dict[str, float]:
        """Fetch account balance."""
        
        try:
            logger.info(f"fetch_balance called - paper_mode: {self.paper_mode}")
            
            # Always return paper trading balance in paper mode
            if self.paper_mode:
                logger.info("Returning paper trading balance")
                return self._paper_exchange.balance.copy()
            
            # Only fetch live balance if we have API keys
            api_key = os.getenv('EXCHANGE_API_KEY')
            api_secret = os.getenv('EXCHANGE_SECRET')
            
            if not api_key or not api_secret:
                logger.info("No API keys available, returning paper balance")
                return self._paper_exchange.balance.copy()
            
            logger.info("Fetching live balance from exchange")
            exchange = await self._get_exchange()
            balance = await exchange.fetch_balance()
            
            # Extract free balances
            free_balances = {}
            for currency, amounts in balance.items():
                if isinstance(amounts, dict) and 'free' in amounts:
                    free_balances[currency] = amounts['free']
            
            return free_balances
            
        except Exception as e:
            logger.error(f"Error fetching balance: {type(e).__name__}: {str(e)}")
            # Return paper balance as fallback
            if hasattr(self, '_paper_exchange'):
                return self._paper_exchange.balance.copy()
            return {'USDT': 10000.0}
        finally:
            if not self.paper_mode:
                await self._release_exchange()
    
    async def fetch_markets(self) -> List[str]:
        """Fetch available trading markets."""
        
        try:
            exchange = await (self._get_market_exchange() if self.paper_mode else self._get_exchange())
            markets = await exchange.load_markets()
            if isinstance(markets, dict):
                self._market_metadata.update(markets)
            
            # Filter for USDT-M futures pairs only
            futures_pairs = []
            for symbol, market in markets.items():
                if (symbol.endswith('/USDT:USDT') and 
                    market.get('active', False) and
                    market.get('type', '') == 'swap' and
                    market.get('linear', True)):
                    status = market.get('info', {}).get('status')
                    if status and status.lower() not in ('trading', 'listed'):
                        continue
                    futures_pairs.append(symbol)
            
            # Sort by popularity (major coins first)
            major_coins = ['BTC', 'ETH', 'BNB', 'ADA', 'SOL', 'DOT', 'MATIC', 'AVAX', 'LINK', 'UNI']
            sorted_pairs = []
            
            # Add major coins first
            for coin in major_coins:
                for pair in futures_pairs:
                    if pair.startswith(f'{coin}/USDT:USDT'):
                        sorted_pairs.append(pair)
                        break
            
            # Add remaining pairs
            for pair in futures_pairs:
                if pair not in sorted_pairs:
                    sorted_pairs.append(pair)
            
            logger.info(f"Found {len(sorted_pairs)} active USDT-M futures pairs")
            return sorted_pairs  # Return all available futures pairs
            
        except Exception as e:
            logger.error(f"Error fetching markets: {e}")
            return []
        finally:
            if not self.paper_mode:
                await self._release_exchange()
    
    async def fetch_trades(self, symbol: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Fetch recent trades for a symbol."""
        if self.paper_mode:
            return await self.paper_exchange.fetch_trades(symbol, limit)
        
        try:
            await self._ensure_exchange()
            trades = await self._exchange.fetch_trades(symbol, limit=limit)
            return trades
        except Exception as e:
            logger.error(f"Error fetching trades for {symbol}: {e}")
            return []
        finally:
            if not self.paper_mode:
                await self._release_exchange()
    
    async def close(self):
        """Close exchange connection and release from pool."""
        if not self.paper_mode and self._exchange:
            try:
                if hasattr(self._exchange, 'close'):
                    await self._exchange.close()
                logger.debug("Exchange connection closed")
            except Exception as e:
                logger.warning(f"Error closing exchange connection: {e}")
            finally:
                await self._release_exchange()
                self._exchange = None
                self._is_temporary_connection = False
                await self._connection_pool.cleanup_idle_connections()

        await self._close_market_exchange()
        try:
            await self.market_streamer.stop()
        except Exception as exc:
            logger.debug(f"Error stopping market streamer: {exc}")
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit - automatically close connections."""
        await self.close()
    
    @property
    def paper_exchange(self):
        """Get paper exchange instance."""
        return self._paper_exchange
    
    async def _ensure_exchange(self):
        """Ensure exchange connection is established."""
        if self.paper_mode:
            return  # No need to ensure exchange in paper mode
        
        if self._exchange is None:
            self._exchange = await self._connection_pool.get_connection(
                getattr(ccxt_async, self.config.exchange),
                self._exchange_config
            )
            self._is_temporary_connection = True


class MarketDataProvider:
    """Provides aggregated market data for analysis."""
    
    def __init__(self, exchange_client: ExchangeClient, enable_websocket: bool = True):
        self.exchange_client = exchange_client
        self.enable_websocket = enable_websocket
        # Cache for frequently reused series (e.g., BTC correlation calculations)
        self._btc_cache: Dict[str, Dict[str, Any]] = {}
        # Expose rate limiter status if the underlying client provides it
        self.rate_limiter = getattr(exchange_client, 'rate_limiter', None)
        self._oi_cache: Dict[str, Tuple[float, Optional[Dict[str, Any]]]] = {}
        self._oi_ttl_seconds = 60.0
    
    async def get_market_data(self, symbol: str) -> Optional[MarketData]:
        """Get comprehensive market data for a symbol."""
        
        try:
            streamer = None
            stream_depth: Optional[DepthSnapshot] = None
            trade_stats: Optional[TradeStats] = None

            # Only use WebSocket if explicitly enabled
            if self.enable_websocket:
                streamer = getattr(self.exchange_client, 'market_streamer', None)
                if streamer:
                    await streamer.ensure_symbol(symbol)
                    stream_depth, trade_stats = await asyncio.gather(
                        streamer.get_depth_snapshot(symbol),
                        streamer.get_trade_stats(symbol)
                    )

            # Оптимизированное получение данных с параллельными запросами
            # Все запросы выполняются параллельно для максимальной скорости

            all_tasks = [
                self.exchange_client.fetch_ticker(symbol),
                self.exchange_client.fetch_order_book(symbol),
                self.exchange_client.fetch_ohlcv(symbol, '5m', 150)
            ]
            
            # Выполняем все запросы параллельно
            ticker, l2_depth, candles_5m = await asyncio.gather(*all_tasks, return_exceptions=True)
            
            # Минимальная задержка только после всех запросов
            await asyncio.sleep(0.005)
            
            # Group 3: Open interest data
            oi_current = await self._get_cached_open_interest(symbol)
            
            # Handle exceptions
            if isinstance(ticker, BaseException) or not ticker:
                if isinstance(ticker, asyncio.CancelledError):
                    logger.debug(f"Ticker fetch cancelled for {symbol}")
                else:
                    logger.warning(f"Failed to fetch ticker for {symbol}: {ticker}")
                return None
            
            if isinstance(l2_depth, BaseException):
                if isinstance(l2_depth, asyncio.CancelledError):
                    logger.debug(f"Order book fetch cancelled for {symbol}")
                l2_depth = None
            
            if isinstance(candles_5m, BaseException):
                if isinstance(candles_5m, asyncio.CancelledError):
                    logger.debug(f"OHLCV 5m fetch cancelled for {symbol}")
                candles_5m = []
            
            # Handle OI data exceptions
            if isinstance(oi_current, BaseException):
                if isinstance(oi_current, asyncio.CancelledError):
                    logger.debug(f"Open interest fetch cancelled for {symbol}")
                oi_current = None

            # Use WebSocket depth data if available, otherwise use REST API data
            if stream_depth:
                bid_05 = getattr(stream_depth, "bid_depth_0_5pct", None)
                if bid_05 is None:
                    bid_05 = getattr(stream_depth, "bid_depth_0_5", 0)
                ask_05 = getattr(stream_depth, "ask_depth_0_5pct", None)
                if ask_05 is None:
                    ask_05 = getattr(stream_depth, "ask_depth_0_5", 0)
                bid_03 = getattr(stream_depth, "bid_depth_0_3pct", None)
                if bid_03 is None:
                    bid_03 = getattr(stream_depth, "bid_depth_0_3", 0)
                ask_03 = getattr(stream_depth, "ask_depth_0_3pct", None)
                if ask_03 is None:
                    ask_03 = getattr(stream_depth, "ask_depth_0_3", 0)

                if bid_05 > 0 or ask_05 > 0:
                    best_bid = getattr(stream_depth, "best_bid", ticker.get('bid'))
                    best_ask = getattr(stream_depth, "best_ask", ticker.get('ask'))
                    bid_05 = self.exchange_client.normalize_depth_total(symbol, bid_05, best_bid or ticker.get('last', 1))
                    ask_05 = self.exchange_client.normalize_depth_total(symbol, ask_05, best_ask or ticker.get('last', 1))
                    bid_03 = self.exchange_client.normalize_depth_total(symbol, bid_03, best_bid or ticker.get('last', 1))
                    ask_03 = self.exchange_client.normalize_depth_total(symbol, ask_03, best_ask or ticker.get('last', 1))
                    l2_depth = L2Depth(
                        bid_usd_0_5pct=bid_05,
                        ask_usd_0_5pct=ask_05,
                        bid_usd_0_3pct=bid_03,
                        ask_usd_0_3pct=ask_03,
                        spread_bps=getattr(stream_depth, "spread_bps", 0.0),
                        imbalance=getattr(stream_depth, "imbalance", 0.0)
                    )
            elif not l2_depth:
                # Fallback to default values if no depth data available
                l2_depth = L2Depth(
                    bid_usd_0_5pct=0, ask_usd_0_5pct=0,
                    bid_usd_0_3pct=0, ask_usd_0_3pct=0,
                    spread_bps=100, imbalance=0
                )

            # Calculate derived metrics
            from ..indicators.technical import atr, bollinger_bands, bollinger_band_width
            
            atr_5m = 0.0
            atr_15m = 0.0
            bb_width_pct = 0.0
            
            if candles_5m and len(candles_5m) >= 20:
                atr_values = atr(candles_5m, 14)
                if not np.isnan(atr_values[-1]):
                    atr_5m = atr_values[-1]
                
                closes = [c.close for c in candles_5m]
                upper, middle, lower = bollinger_bands(closes, 20, 2.0)
                if not np.isnan(upper[-1]):
                    bb_width_pct = bollinger_band_width(upper, lower, middle)[-1]
            
            # Calculate ATR_15m for volatility filtering with fallback
            if atr_5m > 0:
                atr_15m = atr_5m * 1.5
            elif ticker and ticker.get('percentage'):
                # Fallback: estimate ATR from 24h change
                daily_change_pct = abs(ticker['percentage']) / 100
                atr_15m = daily_change_pct * ticker.get('last', 0) * 0.1  # Rough estimate
            
            # Calculate OI data with fallbacks
            oi_usd = 0.0
            oi_change_24h = None
            
            if isinstance(oi_current, dict) and oi_current.get('openInterestValue'):
                oi_usd = oi_current['openInterestValue']
            elif ticker and ticker.get('info', {}).get('openInterest'):
                # Fallback to ticker OI if available
                oi_value = ticker['info']['openInterest']
                if ticker.get('last'):
                    oi_usd = float(oi_value) * ticker['last']
            elif ticker and ticker.get('quoteVolume'):
                # Estimate OI as 10% of 24h volume for futures
                oi_usd = ticker['quoteVolume'] * 0.1
                
                # Calculate 24h OI change if we have history
                oi_change_24h = None

            # Calculate real metrics with better fallbacks
            trades_per_minute = 0.0
            if trade_stats:
                # Use WebSocket trade stats if available
                trades_per_minute = trade_stats.trades_per_minute
                if ticker and trade_stats.last_price:
                    ticker['last'] = trade_stats.last_price
            elif candles_5m and len(candles_5m) > 0:
                # Estimate trades per minute from volume data
                recent_candles = candles_5m[-12:] if len(candles_5m) >= 12 else candles_5m
                recent_volume = sum(c.volume for c in recent_candles)
                time_window_minutes = len(recent_candles) * 5  # 5-minute candles
                if recent_volume > 0 and time_window_minutes > 0:
                    # Estimate: higher volume = more trades
                    trades_per_minute = (recent_volume / time_window_minutes) * 0.001  # Rough estimate
                    trades_per_minute = max(1.0, trades_per_minute)  # Ensure minimum 1 trade/min for active symbols
            elif ticker and ticker.get('quoteVolume'):
                # Fallback: estimate from 24h volume
                volume_24h = ticker['quoteVolume']
                if volume_24h > 1000000:  # > 1M USD volume
                    trades_per_minute = max(1.0, volume_24h / 1440000)  # Rough estimate

            # Calculate BTC correlation if we have BTC data
            btc_correlation = 0.0
            if symbol != 'BTC/USDT' and candles_5m:
                try:
                    btc_candles = await self._get_btc_candles(len(candles_5m))
                    if btc_candles and len(btc_candles) == len(candles_5m):
                        # Calculate price correlation
                        symbol_prices = [candle.close for candle in candles_5m]
                        btc_prices = [candle[4] for candle in btc_candles]  # Close prices
                        
                        if len(symbol_prices) > 1 and len(btc_prices) > 1:
                            # Calculate correlation coefficient
                            from ..indicators.technical import calculate_correlation
                            
                            # Convert to numpy arrays
                            # Use float32 for 50% memory savings
                            symbol_array = np.array(symbol_prices, dtype=np.float32)
                            btc_array = np.array(btc_prices, dtype=np.float32)
                            
                            # Calculate rolling correlation and take the last valid value
                            correlations = calculate_correlation(symbol_array, btc_array, period=min(20, len(symbol_prices)))
                            valid_correlations = correlations[~np.isnan(correlations)]
                            
                            if len(valid_correlations) > 0:
                                btc_correlation = float(valid_correlations[-1])
                            else:
                                btc_correlation = 0.0
                        else:
                            btc_correlation = 0.0
                    else:
                        # Fallback to default correlation for crypto
                        btc_correlation = 0.6
                except Exception as e:
                    logger.debug(f"Failed to calculate BTC correlation for {symbol}: {e}")
                    btc_correlation = 0.6  # Default correlation for crypto
            
            # Create market data object with real data and proper fallbacks
            if not candles_5m or len(candles_5m) < 20:
                logger.debug("Skipping %s: insufficient candle history", symbol)
                return None

            if not l2_depth or (l2_depth.bid_usd_0_5pct <= 0 and l2_depth.ask_usd_0_5pct <= 0):
                logger.debug("Skipping %s: depth snapshot unavailable", symbol)
                return None

            if not ticker.get('last'):
                logger.debug("Skipping %s: ticker has no last price", symbol)
                return None

            if trades_per_minute <= 0:
                logger.debug("Skipping %s: trades per minute unavailable", symbol)
                return None

            market_data = MarketData(
                symbol=symbol,
                price=ticker['last'],
                volume_24h_usd=ticker.get('quoteVolume', 0),
                oi_usd=oi_usd or 0.0,  # Ensure not None
                oi_change_24h=oi_change_24h,
                trades_per_minute=trades_per_minute,
                atr_5m=atr_5m,
                atr_15m=atr_15m,
                bb_width_pct=bb_width_pct,
                btc_correlation=btc_correlation,
                l2_depth=l2_depth,
                candles_5m=candles_5m,
                timestamp=int(datetime.now().timestamp() * 1000)
            )

            return market_data

        except Exception as e:
            logger.error(f"Error getting market data for {symbol}: {e}")
            return None
    
    async def get_multiple_market_data(self, symbols: List[str]) -> Dict[str, MarketData]:
        """Get market data for multiple symbols concurrently."""
        # Remove symbol limit to scan all available tokens
        # symbol_limit = int(os.getenv('LIVE_SCAN_SYMBOL_LIMIT', '40'))
        # if symbol_limit > 0:
        #     symbols = symbols[:symbol_limit]

        # Increased concurrency to 10 for faster scanning (respects rate limiter)
        semaphore = asyncio.Semaphore(int(os.getenv('LIVE_SCAN_CONCURRENCY', '10')))

        async def _bounded_fetch(symbol: str):
            async with semaphore:
                return await self.get_market_data(symbol)

        tasks = [_bounded_fetch(symbol) for symbol in symbols]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        market_data = {}
        for symbol, result in zip(symbols, results):
            if isinstance(result, asyncio.CancelledError):
                logger.debug(f"Market data fetch cancelled for {symbol}")
                continue
            if not isinstance(result, Exception) and result:
                market_data[symbol] = result
        
        logger.info(f"Fetched market data for {len(market_data)} of {len(symbols)} symbols")
        
        return market_data

    async def _get_cached_open_interest(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Fetch open interest with a short-lived cache to limit API traffic."""
        now = time.time()
        cached = self._oi_cache.get(symbol)
        if cached and now - cached[0] < self._oi_ttl_seconds:
            return cached[1]

        oi = await self.exchange_client.fetch_open_interest(symbol)
        self._oi_cache[symbol] = (now, oi)
        return oi

    async def _get_btc_candles(self, limit: int) -> Optional[List[Any]]:
        """Fetch BTC candles with short-lived caching to avoid hammering REST."""
        if limit <= 0:
            return None

        cache_key = "btc_5m"
        cached = self._btc_cache.get(cache_key)
        if cached:
            if time.time() - cached.get("ts", 0) < 30 and len(cached.get("data", [])) >= limit:
                return cached["data"][:limit]

        fetch_limit = max(limit, 100)
        candles = await self.exchange_client.fetch_ohlcv('BTC/USDT', '5m', limit=fetch_limit)
        if candles:
            self._btc_cache[cache_key] = {"ts": time.time(), "data": candles}
            return candles[:limit]

        return None
    
    def get_rate_limiter_status(self) -> Optional[Dict[str, Any]]:
        """Получить статус rate limiter для мониторинга."""
        if self.rate_limiter:
            return self.rate_limiter.get_status()
        return None
    
    def reset_rate_limiter(self):
        """Сбросить rate limiter."""
        if self.rate_limiter:
            self.rate_limiter.reset_limits()
            logger.info("Rate limiter reset completed")
