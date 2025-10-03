"""
Data Quality Assessment (DQA) Module.

Checks completeness, freshness, uniqueness, consistency, and stability
of market data across the pipeline.
"""

import asyncio
import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import numpy as np
import json

from ..data.models import Candle, MarketData, L2Depth
from ..exchange import ExchangeClient


logger = logging.getLogger(__name__)


@dataclass
class DQAMetrics:
    """Data quality metrics for a symbol."""
    symbol: str
    
    # Completeness
    ohlcv_gaps: int = 0  # Missing bars
    ohlcv_total_expected: int = 0
    ws_trades_gaps: int = 0  # Gaps in trade stream
    ws_orderbook_gaps: int = 0  # Gaps in orderbook updates
    
    # Freshness
    ohlcv_latency_p50_ms: float = 0.0
    ohlcv_latency_p95_ms: float = 0.0
    ws_latency_p50_ms: float = 0.0
    ws_latency_p95_ms: float = 0.0
    time_drift_ms: float = 0.0
    
    # Uniqueness
    duplicate_candles: int = 0
    duplicate_trades: int = 0
    
    # Consistency
    ohlcv_trade_volume_mismatch_pct: float = 0.0  # OHLCV vs trades volume diff
    negative_spreads: int = 0
    negative_depths: int = 0
    ask_below_bid: int = 0
    
    # Stability
    price_teleports: int = 0  # bar range > k*ATR
    atr_spikes: int = 0
    
    # Overall score
    completeness_score: float = 0.0  # 0-1
    freshness_score: float = 0.0
    consistency_score: float = 0.0
    stability_score: float = 0.0
    overall_score: float = 0.0
    
    # Metadata
    checked_at: int = field(default_factory=lambda: int(time.time()))
    data_window_hours: int = 48
    errors: List[str] = field(default_factory=list)


class DataQualityAssessment:
    """
    Assesses data quality across multiple dimensions.
    
    Usage:
        dqa = DataQualityAssessment(exchange_client)
        await dqa.assess_symbols(["BTC/USDT", "ETH/USDT"], hours=48)
        summary = dqa.get_summary()
    """
    
    def __init__(
        self,
        exchange_client: ExchangeClient,
        log_dir: Optional[Path] = None,
        teleport_atr_multiplier: float = 5.0
    ):
        self.exchange_client = exchange_client
        self.log_dir = log_dir or Path("logs/dqa")
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        self.teleport_atr_multiplier = teleport_atr_multiplier
        
        # Results storage
        self.metrics: Dict[str, DQAMetrics] = {}
        
        logger.info(f"DataQualityAssessment initialized: log_dir={self.log_dir}")
    
    async def assess_symbols(
        self,
        symbols: List[str],
        hours: int = 48,
        timeframe: str = "15m"
    ) -> Dict[str, DQAMetrics]:
        """
        Assess data quality for a list of symbols.
        
        Args:
            symbols: List of trading pairs
            hours: Hours of historical data to check
            timeframe: Candle timeframe
            
        Returns:
            Dictionary of symbol -> DQAMetrics
        """
        logger.info(f"Starting DQA for {len(symbols)} symbols over {hours}h")
        
        tasks = []
        for symbol in symbols:
            task = self._assess_symbol(symbol, hours, timeframe)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for symbol, result in zip(symbols, results):
            if isinstance(result, Exception):
                logger.error(f"DQA failed for {symbol}: {result}")
                self.metrics[symbol] = DQAMetrics(
                    symbol=symbol,
                    errors=[str(result)]
                )
            else:
                self.metrics[symbol] = result
        
        # Save results
        self._save_results()
        
        return self.metrics
    
    async def _assess_symbol(
        self,
        symbol: str,
        hours: int,
        timeframe: str
    ) -> DQAMetrics:
        """Assess data quality for a single symbol."""
        logger.info(f"Assessing {symbol}...")
        
        metrics = DQAMetrics(
            symbol=symbol,
            data_window_hours=hours
        )
        
        try:
            # Fetch OHLCV data
            since_ts = int((time.time() - hours * 3600) * 1000)
            candles = await self.exchange_client.fetch_ohlcv(
                symbol=symbol,
                timeframe=timeframe,
                limit=1000,
                since=since_ts
            )
            
            if not candles:
                metrics.errors.append("No OHLCV data available")
                return metrics
            
            # 1. Completeness checks
            self._check_completeness(candles, timeframe, metrics)
            
            # 2. Freshness checks
            self._check_freshness(candles, metrics)
            
            # 3. Uniqueness checks
            self._check_uniqueness(candles, metrics)
            
            # 4. Consistency checks
            self._check_consistency(candles, metrics)
            
            # 5. Stability checks
            self._check_stability(candles, metrics)
            
            # Calculate overall scores
            self._calculate_scores(metrics)
            
            logger.info(f"{symbol}: Overall DQA score = {metrics.overall_score:.2f}")
            
        except Exception as e:
            logger.error(f"Error assessing {symbol}: {e}", exc_info=True)
            metrics.errors.append(str(e))
        
        return metrics
    
    def _check_completeness(
        self,
        candles: List[Candle],
        timeframe: str,
        metrics: DQAMetrics
    ) -> None:
        """Check for missing data (gaps in OHLCV)."""
        if len(candles) < 2:
            return
        
        # Parse timeframe to seconds
        tf_map = {
            "1m": 60, "3m": 180, "5m": 300, "15m": 900,
            "30m": 1800, "1h": 3600, "4h": 14400, "1d": 86400
        }
        tf_seconds = tf_map.get(timeframe, 900)
        tf_ms = tf_seconds * 1000
        
        # Check for gaps
        gaps = 0
        for i in range(1, len(candles)):
            expected_ts = candles[i-1].ts + tf_ms
            actual_ts = candles[i].ts
            
            if actual_ts - expected_ts > tf_ms * 1.5:  # Allow 50% tolerance
                gaps += 1
        
        # Calculate expected bars
        time_range_ms = candles[-1].ts - candles[0].ts
        expected_bars = int(time_range_ms / tf_ms) + 1
        
        metrics.ohlcv_gaps = gaps
        metrics.ohlcv_total_expected = expected_bars
        
        # Score: 1.0 if no gaps, decreasing with more gaps
        if expected_bars > 0:
            gap_ratio = gaps / expected_bars
            metrics.completeness_score = max(0.0, 1.0 - gap_ratio * 5)  # Penalize gaps heavily
    
    def _check_freshness(
        self,
        candles: List[Candle],
        metrics: DQAMetrics
    ) -> None:
        """Check data freshness (latency)."""
        if not candles:
            return
        
        now_ms = int(time.time() * 1000)
        latest_candle_ts = candles[-1].ts
        
        # Latency = how old is the latest data
        latency_ms = now_ms - latest_candle_ts
        
        # For simplicity, use this as both p50 and p95
        # In production, would track actual distribution
        metrics.ohlcv_latency_p50_ms = latency_ms
        metrics.ohlcv_latency_p95_ms = latency_ms
        
        # Check time drift (are timestamps consistent?)
        timestamps = [c.ts for c in candles]
        if len(timestamps) > 1:
            diffs = np.diff(timestamps)
            median_diff = np.median(diffs)
            drift = np.std(diffs)
            metrics.time_drift_ms = float(drift)
        
        # Score: 1.0 if very fresh (< 30s), decreasing with age
        max_acceptable_latency_ms = 60000  # 60s
        if latency_ms < max_acceptable_latency_ms:
            metrics.freshness_score = 1.0 - (latency_ms / max_acceptable_latency_ms)
        else:
            metrics.freshness_score = 0.0
    
    def _check_uniqueness(
        self,
        candles: List[Candle],
        metrics: DQAMetrics
    ) -> None:
        """Check for duplicate data."""
        if not candles:
            return
        
        # Check for duplicate timestamps
        timestamps = [c.ts for c in candles]
        unique_ts = set(timestamps)
        duplicates = len(timestamps) - len(unique_ts)
        
        metrics.duplicate_candles = duplicates
    
    def _check_consistency(
        self,
        candles: List[Candle],
        metrics: DQAMetrics
    ) -> None:
        """Check data consistency (internal contradictions)."""
        if not candles:
            return
        
        # Check OHLC relationships
        for candle in candles:
            # High should be >= low
            if candle.low > candle.high:
                metrics.errors.append(
                    f"Invalid OHLC at {candle.ts}: low ({candle.low}) > high ({candle.high})"
                )
            
            # Open/close should be within [low, high]
            if not (candle.low <= candle.open <= candle.high):
                metrics.errors.append(
                    f"Invalid open at {candle.ts}: {candle.open} not in [{candle.low}, {candle.high}]"
                )
            
            if not (candle.low <= candle.close <= candle.high):
                metrics.errors.append(
                    f"Invalid close at {candle.ts}: {candle.close} not in [{candle.low}, {candle.high}]"
                )
        
        # Consistency score: 1.0 if no errors, 0 if many
        error_ratio = len(metrics.errors) / len(candles) if candles else 0
        metrics.consistency_score = max(0.0, 1.0 - error_ratio * 10)
    
    def _check_stability(
        self,
        candles: List[Candle],
        metrics: DQAMetrics
    ) -> None:
        """Check for anomalies (price teleports, spikes)."""
        if len(candles) < 20:
            return
        
        # Calculate ATR
        from ..indicators.technical import atr
        atr_values = atr(candles, period=14)
        
        # Check for price teleports (bar range > k*ATR)
        teleports = 0
        for i in range(14, len(candles)):
            bar_range = candles[i].high - candles[i].low
            atr_val = atr_values[i]
            
            if atr_val > 0 and bar_range > self.teleport_atr_multiplier * atr_val:
                teleports += 1
        
        metrics.price_teleports = teleports
        
        # Check for ATR spikes (sudden volatility changes)
        if len(atr_values) > 20:
            atr_valid = atr_values[~np.isnan(atr_values)]
            if len(atr_valid) > 1:
                atr_changes = np.abs(np.diff(atr_valid)) / atr_valid[:-1]
                atr_spikes = np.sum(atr_changes > 2.0)  # 200% change
                metrics.atr_spikes = int(atr_spikes)
        
        # Stability score
        total_checks = len(candles) - 14
        anomaly_ratio = (teleports + metrics.atr_spikes) / total_checks if total_checks > 0 else 0
        metrics.stability_score = max(0.0, 1.0 - anomaly_ratio * 5)
    
    def _calculate_scores(self, metrics: DQAMetrics) -> None:
        """Calculate overall quality score."""
        scores = [
            metrics.completeness_score,
            metrics.freshness_score,
            metrics.consistency_score,
            metrics.stability_score
        ]
        
        # Overall = weighted average
        # Completeness and consistency are most important
        weights = [0.3, 0.2, 0.3, 0.2]
        metrics.overall_score = sum(s * w for s, w in zip(scores, weights))
    
    def _save_results(self) -> None:
        """Save DQA results to file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = self.log_dir / f"dqa_{timestamp}.jsonl"
        
        with open(output_path, "w", encoding="utf-8") as f:
            for symbol, metrics in self.metrics.items():
                json_line = json.dumps(asdict(metrics), ensure_ascii=False)
                f.write(json_line + "\n")
        
        logger.info(f"DQA results saved to {output_path}")
    
    def get_summary(self) -> Dict[str, Any]:
        """Get summary statistics across all assessed symbols."""
        if not self.metrics:
            return {}
        
        scores = [m.overall_score for m in self.metrics.values()]
        completeness = [m.completeness_score for m in self.metrics.values()]
        freshness = [m.freshness_score for m in self.metrics.values()]
        consistency = [m.consistency_score for m in self.metrics.values()]
        stability = [m.stability_score for m in self.metrics.values()]
        
        return {
            "total_symbols": len(self.metrics),
            "average_overall_score": np.mean(scores),
            "min_overall_score": np.min(scores),
            "max_overall_score": np.max(scores),
            "average_completeness": np.mean(completeness),
            "average_freshness": np.mean(freshness),
            "average_consistency": np.mean(consistency),
            "average_stability": np.mean(stability),
            "symbols_with_errors": sum(1 for m in self.metrics.values() if m.errors),
            "total_gaps": sum(m.ohlcv_gaps for m in self.metrics.values()),
            "total_teleports": sum(m.price_teleports for m in self.metrics.values()),
        }
