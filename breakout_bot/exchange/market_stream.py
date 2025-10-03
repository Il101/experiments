"""Real-time market data streaming helpers."""

from __future__ import annotations

import asyncio
import json
import logging
import time
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Deque, Dict, Optional, Tuple

from websockets import connect

logger = logging.getLogger(__name__)


@dataclass
class DepthSnapshot:
    best_bid: float
    best_ask: float
    spread_bps: float
    bid_depth_0_3: float
    ask_depth_0_3: float
    bid_depth_0_5: float
    ask_depth_0_5: float
    imbalance: float
    timestamp_ms: int


@dataclass
class TradeStats:
    trades_per_minute: float
    volume_per_minute: float
    last_price: float
    timestamp_ms: int


class RealTimeMarketDataStreamer:
    """Maintain live depth and trade statistics via exchange WebSocket feeds."""

    def __init__(self, exchange: str):
        self.exchange = exchange.lower()
        self._depth_cache: Dict[str, DepthSnapshot] = {}
        self._trade_cache: Dict[str, TradeStats] = {}
        self._trade_windows: Dict[str, Deque[Tuple[float, float]]] = defaultdict(lambda: deque(maxlen=1000))
        self._locks: Dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)
        self._global_lock = asyncio.Lock()
        self._tasks: Dict[str, Tuple[asyncio.Task, asyncio.Task]] = {}
        self._stop_event = asyncio.Event()

    async def ensure_symbol(self, symbol: str) -> None:
        async with self._global_lock:
            if symbol in self._tasks:
                return

            depth_task = asyncio.create_task(self._depth_loop(symbol))
            trade_task = asyncio.create_task(self._trade_loop(symbol))
            self._tasks[symbol] = (depth_task, trade_task)
            logger.info("Started real-time streams for %s", symbol)

    async def stop(self) -> None:
        self._stop_event.set()
        async with self._global_lock:
            for depth_task, trade_task in self._tasks.values():
                for task in (depth_task, trade_task):
                    task.cancel()
            self._tasks.clear()
        logger.info("Stopped all real-time market streams")

    async def get_depth_snapshot(self, symbol: str) -> Optional[DepthSnapshot]:
        lock = self._locks[symbol]
        async with lock:
            return self._depth_cache.get(symbol)

    async def get_trade_stats(self, symbol: str) -> Optional[TradeStats]:
        lock = self._locks[symbol]
        async with lock:
            return self._trade_cache.get(symbol)

    async def _depth_loop(self, symbol: str) -> None:
        while not self._stop_event.is_set():
            try:
                if self.exchange == 'binance':
                    await self._binance_depth(symbol)
                elif self.exchange == 'bybit':
                    await self._bybit_depth(symbol)
                else:
                    logger.warning("No WebSocket depth implementation for %s", self.exchange)
                    return
            except asyncio.CancelledError:
                return
            except Exception as exc:  # pragma: no cover - defensive logging
                logger.warning("Depth stream error for %s on %s: %s", symbol, self.exchange, exc)
                await asyncio.sleep(1.0)

    async def _trade_loop(self, symbol: str) -> None:
        while not self._stop_event.is_set():
            try:
                if self.exchange == 'binance':
                    await self._binance_trades(symbol)
                elif self.exchange == 'bybit':
                    await self._bybit_trades(symbol)
                else:
                    logger.warning("No WebSocket trade implementation for %s", self.exchange)
                    return
            except asyncio.CancelledError:
                return
            except Exception as exc:  # pragma: no cover
                logger.warning("Trade stream error for %s on %s: %s", symbol, self.exchange, exc)
                await asyncio.sleep(1.0)

    async def _binance_depth(self, symbol: str) -> None:
        ws_symbol = symbol.replace('/', '').lower()
        url = f"wss://fstream.binance.com/ws/{ws_symbol}@depth20@100ms"
        async with connect(url, ping_interval=20, ping_timeout=20) as ws:
            async for raw in ws:
                if self._stop_event.is_set():
                    break
                message = json.loads(raw)
                bids = message.get('b', [])
                asks = message.get('a', [])
                if not bids or not asks:
                    continue
                snapshot = self._build_depth_snapshot(bids, asks, message.get('E'))
                await self._store_depth(symbol, snapshot)

    async def _binance_trades(self, symbol: str) -> None:
        ws_symbol = symbol.replace('/', '').lower()
        url = f"wss://fstream.binance.com/ws/{ws_symbol}@trade"
        async with connect(url, ping_interval=20, ping_timeout=20) as ws:
            async for raw in ws:
                if self._stop_event.is_set():
                    break
                data = json.loads(raw)
                price = float(data['p'])
                qty = float(data['q'])
                timestamp = int(data['T'])
                await self._store_trade(symbol, price, qty, timestamp)

    async def _bybit_depth(self, symbol: str) -> None:
        url = "wss://stream.bybit.com/v5/public/linear"
        # Convert BTC/USDT:USDT -> BTCUSDT for Bybit API
        bybit_symbol = symbol.replace('/USDT:USDT', 'USDT').replace('/', '').upper()
        topic = f"orderbook.50.{bybit_symbol}"
        async with connect(url, ping_interval=None) as ws:
            await ws.send(json.dumps({"op": "subscribe", "args": [topic]}))
            local_book: Dict[str, Dict[float, float]] = {'bids': {}, 'asks': {}}
            async for raw in ws:
                if self._stop_event.is_set():
                    break
                message = json.loads(raw)
                if message.get('op') == 'ping':
                    await ws.send(json.dumps({"op": "pong", "ts": message.get('ts')}))
                    continue
                if message.get('topic') != topic:
                    continue
                data = message.get('data', {})
                msg_type = message.get('type')
                timestamp = int(message.get('ts', int(time.time() * 1000)))
                if msg_type == 'snapshot':
                    local_book['bids'] = {float(price): float(size) for price, size in data.get('b', [])}
                    local_book['asks'] = {float(price): float(size) for price, size in data.get('a', [])}
                elif msg_type == 'delta':
                    for price, size in data.get('b', []):
                        price_f = float(price)
                        size_f = float(size)
                        if size_f == 0:
                            local_book['bids'].pop(price_f, None)
                        else:
                            local_book['bids'][price_f] = size_f
                    for price, size in data.get('a', []):
                        price_f = float(price)
                        size_f = float(size)
                        if size_f == 0:
                            local_book['asks'].pop(price_f, None)
                        else:
                            local_book['asks'][price_f] = size_f
                else:
                    continue
                bids_sorted = sorted(local_book['bids'].items(), key=lambda x: x[0], reverse=True)[:50]
                asks_sorted = sorted(local_book['asks'].items(), key=lambda x: x[0])[:50]
                if not bids_sorted or not asks_sorted:
                    continue
                snapshot = self._build_depth_snapshot(bids_sorted, asks_sorted, timestamp)
                await self._store_depth(symbol, snapshot)

    async def _bybit_trades(self, symbol: str) -> None:
        url = "wss://stream.bybit.com/v5/public/linear"
        # Convert BTC/USDT:USDT -> BTCUSDT for Bybit API
        bybit_symbol = symbol.replace('/USDT:USDT', 'USDT').replace('/', '').upper()
        topic = f"publicTrade.{bybit_symbol}"
        async with connect(url, ping_interval=None) as ws:
            await ws.send(json.dumps({"op": "subscribe", "args": [topic]}))
            async for raw in ws:
                if self._stop_event.is_set():
                    break
                message = json.loads(raw)
                if message.get('op') == 'ping':
                    await ws.send(json.dumps({"op": "pong", "ts": message.get('ts')}))
                    continue
                if message.get('topic') != topic:
                    continue
                for trade in message.get('data', []):
                    price = float(trade['p'])
                    qty = float(trade['v'])
                    timestamp = int(trade.get('T', trade.get('ts', int(time.time() * 1000))))
                    await self._store_trade(symbol, price, qty, timestamp)

    async def _store_depth(self, symbol: str, snapshot: DepthSnapshot) -> None:
        lock = self._locks[symbol]
        async with lock:
            self._depth_cache[symbol] = snapshot

    async def _store_trade(self, symbol: str, price: float, qty: float, timestamp: int) -> None:
        window = self._trade_windows[symbol]
        window.append((timestamp, qty))
        cutoff = timestamp - 60_000
        while window and window[0][0] < cutoff:
            window.popleft()
        trades_per_minute = len(window)
        volume_per_minute = sum(q for _, q in window)
        stats = TradeStats(
            trades_per_minute=trades_per_minute,
            volume_per_minute=volume_per_minute,
            last_price=price,
            timestamp_ms=timestamp,
        )
        lock = self._locks[symbol]
        async with lock:
            self._trade_cache[symbol] = stats

    def _build_depth_snapshot(self, bids, asks, timestamp: Optional[int]) -> DepthSnapshot:
        bid_levels = [(float(price), float(size)) for price, size in bids if float(size) > 0]
        ask_levels = [(float(price), float(size)) for price, size in asks if float(size) > 0]
        if not bid_levels or not ask_levels:
            raise ValueError("Insufficient depth data")
        best_bid = bid_levels[0][0]
        best_ask = ask_levels[0][0]
        spread_bps = ((best_ask - best_bid) / best_bid) * 10000 if best_bid else 0
        bid_depth_0_3 = self._sum_depth_within(bid_levels, best_bid, 0.003, is_bid=True)
        ask_depth_0_3 = self._sum_depth_within(ask_levels, best_ask, 0.003, is_bid=False)
        bid_depth_0_5 = self._sum_depth_within(bid_levels, best_bid, 0.005, is_bid=True)
        ask_depth_0_5 = self._sum_depth_within(ask_levels, best_ask, 0.005, is_bid=False)
        bid_vol = sum(size for _, size in bid_levels[:10])
        ask_vol = sum(size for _, size in ask_levels[:10])
        imbalance = (bid_vol - ask_vol) / (bid_vol + ask_vol) if (bid_vol + ask_vol) > 0 else 0
        ts = int(timestamp) if timestamp is not None else int(time.time() * 1000)
        return DepthSnapshot(
            best_bid=best_bid,
            best_ask=best_ask,
            spread_bps=spread_bps,
            bid_depth_0_3=bid_depth_0_3,
            ask_depth_0_3=ask_depth_0_3,
            bid_depth_0_5=bid_depth_0_5,
            ask_depth_0_5=ask_depth_0_5,
            imbalance=imbalance,
            timestamp_ms=ts,
        )

    def _sum_depth_within(self, levels, pivot_price: float, pct: float, is_bid: bool) -> float:
        limit = pivot_price * (1 + pct if not is_bid else 1 - pct)
        total = 0.0
        for price, size in levels:
            if is_bid and price < limit:
                break
            if not is_bid and price > limit:
                break
            total += price * size
        return total
