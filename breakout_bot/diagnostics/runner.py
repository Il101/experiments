"""Diagnostics runner to replay scanner/signal pipeline on historical data."""

from __future__ import annotations

import asyncio
import math
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Sequence

import numpy as np

from ..config.settings import SystemConfig, TradingPreset
from ..data.models import Candle, L2Depth, MarketData
from ..diagnostics import DiagnosticsCollector
from ..exchange.exchange_client import ExchangeClient, close_all_connections
from ..indicators.technical import (
    atr,
    bollinger_band_width,
    bollinger_bands,
    calculate_correlation,
)
from ..scanner import BreakoutScanner
from ..signals import SignalGenerator


@dataclass
class DiagnosticsProfileResult:
    profile_name: str
    bars: int
    candidates: int
    passed_filters: int
    momentum_signals: int
    retest_signals: int
    total_signals: int
    diagnostics_log: Path
    reasons: List[tuple]

    @property
    def pass_rate(self) -> float:
        if not self.candidates:
            return 0.0
        return self.passed_filters / self.candidates


class DiagnosticsRunner:
    """Runs diagnostics profiles over historical market data."""

    def __init__(
        self,
        system_config: SystemConfig,
        symbol: str,
        start: datetime,
        end: datetime,
        concurrency: int = 1,
    ) -> None:
        if end <= start:
            raise ValueError("End datetime must be after start datetime")

        self.system_config = system_config
        self.symbol = symbol.upper()
        self.start = start
        self.end = end
        self.concurrency = max(1, concurrency)
        self._dataset: Optional[List[MarketData]] = None
        self._exchange_client: Optional[ExchangeClient] = None

    async def _ensure_client(self) -> ExchangeClient:
        if self._exchange_client is None:
            self._exchange_client = ExchangeClient(self.system_config)
        return self._exchange_client

    async def close(self) -> None:
        if self._exchange_client is not None:
            await self._exchange_client.close()
            self._exchange_client = None
        await close_all_connections()

    async def _fetch_candles(
        self,
        symbol: str,
        timeframe: str,
        limit: int,
        since: Optional[int] = None,
    ) -> List[Candle]:
        client = await self._ensure_client()
        candles = await client.fetch_ohlcv(symbol, timeframe, limit=limit, since=since)
        candles.sort(key=lambda c: c.ts)
        return candles

    async def _fetch_depth(self, symbol: str) -> L2Depth:
        client = await self._ensure_client()
        depth = await client.fetch_order_book(symbol)
        if not depth:
            depth = L2Depth(
                bid_usd_0_5pct=0.0,
                ask_usd_0_5pct=0.0,
                bid_usd_0_3pct=0.0,
                ask_usd_0_3pct=0.0,
                spread_bps=100.0,
                imbalance=0.0,
            )
        return depth

    async def _fetch_open_interest(self, symbol: str) -> Optional[float]:
        client = await self._ensure_client()
        data = await client.fetch_open_interest(symbol)
        if isinstance(data, dict):
            for key in ("openInterestUsd", "openInterest", "totalVolumeUsd"):
                if key in data:
                    try:
                        return float(data[key])
                    except (TypeError, ValueError):
                        continue
        try:
            return float(data) if data is not None else None
        except (TypeError, ValueError):
            return None

    async def _fetch_open_interest_history(self, symbol: str) -> List[float]:
        client = await self._ensure_client()
        history = await client.fetch_open_interest_history(symbol, '1h', limit=48)
        values: List[float] = []
        for entry in history:
            for key in ("openInterestUsd", "openInterest", "sumOpenInterest"):
                if key in entry:
                    try:
                        values.append(float(entry[key]))
                    except (TypeError, ValueError):
                        continue
                    break
        return values

    async def _build_dataset(self) -> List[MarketData]:
        if self._dataset is not None:
            return self._dataset

        start_ts = int(self.start.timestamp() * 1000)
        end_ts = int(self.end.timestamp() * 1000)
        total_bars = max(1, math.ceil((end_ts - start_ts) / (5 * 60 * 1000)))
        warmup = 320  # provide enough history for indicators
        fetch_limit = min(2000, total_bars + warmup)

        since_5m = max(0, start_ts - warmup * 5 * 60 * 1000)
        candles_5m = await self._fetch_candles(self.symbol, '5m', fetch_limit, since=since_5m)
        if not candles_5m:
            raise RuntimeError(f"No 5m candles fetched for {self.symbol}")

        since_15m = max(0, start_ts - warmup * 15 * 60 * 1000)
        candles_15m = await self._fetch_candles(self.symbol, '15m', max(200, fetch_limit // 3), since=since_15m)
        btc_candles = await self._fetch_candles('BTC/USDT', '5m', fetch_limit, since=since_5m)

        depth_snapshot = await self._fetch_depth(self.symbol)
        oi_latest = await self._fetch_open_interest(self.symbol)
        oi_series = await self._fetch_open_interest_history(self.symbol)
        oi_change = None
        if len(oi_series) >= 2 and oi_series[0] > 0:
            oi_change = (oi_series[-1] - oi_series[0]) / oi_series[0]

        closes = np.array([c.close for c in candles_5m], dtype=float)
        atr_5m_series = atr(candles_5m, period=14)
        upper, middle, lower = bollinger_bands(closes, period=20, std_dev=2.0)
        bb_width_series = bollinger_band_width(upper, lower, middle)

        atr_15m_series = atr(candles_15m, period=14) if candles_15m else np.array([])
        atr_15m_map: Dict[int, float] = {}
        if len(atr_15m_series):
            for candle, value in zip(candles_15m, atr_15m_series):
                if not np.isnan(value):
                    atr_15m_map[candle.ts] = float(value)

        btc_closes = np.array([c.close for c in btc_candles], dtype=float)
        corr_series = calculate_correlation(closes, btc_closes, period=20) if len(btc_closes) == len(closes) else np.full(len(closes), 0.0)

        dataset: List[MarketData] = []
        for idx, candle in enumerate(candles_5m):
            if candle.ts < start_ts or candle.ts > end_ts:
                continue
            if idx < 60:
                # ensure we have at least minimal history for scanners
                continue

            candles_slice = candles_5m[max(0, idx - 120):idx + 1]
            volume_window = candles_5m[max(0, idx - 288): idx + 1]
            volume_24h_usd = sum(c.close * c.volume for c in volume_window)

            trades_per_minute = max(candle.volume / 5.0, 0.0)
            atr_5m_value = float(atr_5m_series[idx]) if idx < len(atr_5m_series) and not np.isnan(atr_5m_series[idx]) else 0.0
            bb_width_pct = float(bb_width_series[idx]) if idx < len(bb_width_series) and not np.isnan(bb_width_series[idx]) else 0.0

            # Find latest 15m ATR value not exceeding current timestamp
            atr_15m_value = 0.0
            if atr_15m_map:
                keys = [ts for ts in atr_15m_map.keys() if ts <= candle.ts]
                if keys:
                    latest_ts = max(keys)
                    atr_15m_value = atr_15m_map.get(latest_ts, 0.0)

            btc_corr_value = 0.0
            if idx < len(corr_series) and not np.isnan(corr_series[idx]):
                btc_corr_value = float(corr_series[idx])

            market_data = MarketData(
                symbol=self.symbol,
                price=candle.close,
                volume_24h_usd=volume_24h_usd,
                oi_usd=oi_latest,
                oi_change_24h=oi_change,
                trades_per_minute=trades_per_minute,
                atr_5m=atr_5m_value,
                atr_15m=atr_15m_value,
                bb_width_pct=bb_width_pct,
                btc_correlation=btc_corr_value,
                l2_depth=depth_snapshot.model_copy(),
                candles_5m=candles_slice,
                timestamp=candle.ts,
            )
            dataset.append(market_data)

        if not dataset:
            raise RuntimeError("Dataset construction produced no market data in selected window")

        self._dataset = dataset
        return dataset

    async def run_profile(self, profile_name: str, preset: TradingPreset) -> DiagnosticsProfileResult:
        dataset = await self._build_dataset()
        collector = DiagnosticsCollector(enabled=True, session_id=f"diag_{profile_name}_{self.symbol}_{int(self.start.timestamp())}")
        scanner = BreakoutScanner(preset, diagnostics=collector)
        signal_generator = SignalGenerator(preset, diagnostics=collector)

        bars = 0
        candidates = 0
        passed_filters = 0
        momentum_signals = 0
        retest_signals = 0

        for market_data in dataset:
            bars += 1
            scan_results = await scanner.scan_markets([market_data])
            if not scan_results:
                continue
            candidates += len(scan_results)
            primary = scan_results[0]
            if primary.passed_all_filters:
                passed_filters += 1
                signal = await signal_generator.generate_signal(primary)
                if signal:
                    if signal.strategy == 'momentum':
                        momentum_signals += 1
                    elif signal.strategy == 'retest':
                        retest_signals += 1

        return DiagnosticsProfileResult(
            profile_name=profile_name,
            bars=bars,
            candidates=candidates,
            passed_filters=passed_filters,
            momentum_signals=momentum_signals,
            retest_signals=retest_signals,
            total_signals=momentum_signals + retest_signals,
            diagnostics_log=collector.output_path,
            reasons=collector.reasons.most_common(20),
        )

    async def run_profiles(self, profiles: Dict[str, TradingPreset]) -> Dict[str, DiagnosticsProfileResult]:
        results: Dict[str, DiagnosticsProfileResult] = {}
        for name, preset in profiles.items():
            results[name] = await self.run_profile(name, preset)
        return results
