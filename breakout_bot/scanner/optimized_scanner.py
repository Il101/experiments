"""
Optimized Market Scanner for Breakout Bot Trading System.

This module implements a resource-optimized version of the market scanner
with improved memory management, CPU usage, and disk I/O optimization.
"""

import asyncio
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
import logging
import hashlib
import time
import gc
from functools import lru_cache
from concurrent.futures import ThreadPoolExecutor
import weakref
import psutil

from ..data.models import Candle, L2Depth, MarketData, ScanResult, TradingLevel
from ..config.settings import TradingPreset, LiquidityFilters, VolatilityFilters, ScannerConfig
from ..indicators.technical import (
    atr, bollinger_bands, bollinger_band_width, vwap, 
    calculate_correlation, volume_surge_ratio
)
from ..indicators.levels import LevelDetector
from ..utils.resource_monitor import get_resource_monitor

logger = logging.getLogger(__name__)


@dataclass
class OptimizedFilterResult:
    """Memory-efficient filter result."""
    passed: bool
    value: Optional[float] = None
    threshold: Optional[float] = None
    reason: str = ""


@dataclass
class OptimizedScanMetrics:
    """Memory-efficient scan metrics with reduced precision."""
    vol_surge_1h: float = 0.0
    vol_surge_5m: float = 0.0
    oi_delta_24h: float = 0.0
    atr_quality: float = 0.0
    bb_width_pct: float = 0.0
    btc_correlation: float = 0.0
    trades_per_minute: float = 0.0
    liquidity_score: float = 0.0


class OptimizedMarketFilter:
    """Memory-efficient market filter with caching."""
    
    def __init__(self, name: str, preset: TradingPreset):
        self.name = name
        self.preset = preset
        self.liquidity_filters = preset.liquidity_filters
        self.volatility_filters = preset.volatility_filters
        
        # Cache for filter results to avoid recalculation - memory optimized
        self._filter_cache = {}
        self._cache_ttl = 60  # 1 minute
        self._max_cache_size = 200  # Reduced from 500 to save memory
        self._cache_access_order = []  # Track access for LRU cleanup
    
    def _get_cache_key(self, market_data: MarketData) -> str:
        """Generate cache key for market data."""
        return f"{market_data.symbol}_{market_data.price}_{market_data.volume_24h_usd}"
    
    def _is_cache_valid(self, timestamp: float) -> bool:
        """Check if cache entry is still valid."""
        return time.time() - timestamp < self._cache_ttl
    
    def _cleanup_cache(self):
        """Remove expired cache entries and enforce size limits."""
        now = time.time()
        
        # Remove expired entries
        expired_keys = [
            k for k, (_, timestamp) in self._filter_cache.items() 
            if now - timestamp > self._cache_ttl
        ]
        for key in expired_keys:
            del self._filter_cache[key]
            if key in self._cache_access_order:
                self._cache_access_order.remove(key)
        
        # Enforce size limits using LRU
        while len(self._filter_cache) > self._max_cache_size:
            if self._cache_access_order:
                # Remove least recently used
                oldest_key = self._cache_access_order.pop(0)
                if oldest_key in self._filter_cache:
                    del self._filter_cache[oldest_key]
            else:
                # Fallback: remove first key
                if self._filter_cache:
                    first_key = next(iter(self._filter_cache))
                    del self._filter_cache[first_key]
                break
    
    def apply_liquidity_filters(self, market_data: MarketData) -> Dict[str, OptimizedFilterResult]:
        """Apply liquidity-based filters with caching."""
        cache_key = self._get_cache_key(market_data)
        
        # Check cache first
        if cache_key in self._filter_cache:
            cached_result, timestamp = self._filter_cache[cache_key]
            if self._is_cache_valid(timestamp):
                # Update access order for LRU
                if cache_key in self._cache_access_order:
                    self._cache_access_order.remove(cache_key)
                self._cache_access_order.append(cache_key)
                return cached_result
        
        # Cleanup cache if it's getting too large
        if len(self._filter_cache) > self._max_cache_size:
            self._cleanup_cache()
        
        results = {}
        
        # 24h Volume filter
        results['min_24h_volume'] = OptimizedFilterResult(
            passed=market_data.volume_24h_usd >= self.liquidity_filters.min_24h_volume_usd,
            value=market_data.volume_24h_usd,
            threshold=self.liquidity_filters.min_24h_volume_usd,
            reason=f"24h volume: ${market_data.volume_24h_usd:,.0f}"
        )
        
        # Spread filter (с проверкой на None)
        if market_data.l2_depth is not None:
            results['max_spread'] = OptimizedFilterResult(
                passed=market_data.l2_depth.spread_bps <= self.liquidity_filters.max_spread_bps,
                value=market_data.l2_depth.spread_bps,
                threshold=self.liquidity_filters.max_spread_bps,
                reason=f"Spread: {market_data.l2_depth.spread_bps:.1f} bps"
            )
        else:
            # Если нет данных о стакане, пропускаем фильтр по спреду
            results['max_spread'] = OptimizedFilterResult(
                passed=True,  # Пропускаем фильтр
                value=None,
                threshold=self.liquidity_filters.max_spread_bps,
                reason="No L2 depth data available"
            )
        
        # Depth filters (simplified, с проверкой на None)
        if market_data.l2_depth is not None:
            total_depth_0_5pct = market_data.l2_depth.bid_usd_0_5pct + market_data.l2_depth.ask_usd_0_5pct
            results['min_depth_0_5pct'] = OptimizedFilterResult(
                passed=total_depth_0_5pct >= self.liquidity_filters.min_depth_usd_0_5pct,
                value=total_depth_0_5pct,
                threshold=self.liquidity_filters.min_depth_usd_0_5pct,
                reason=f"Depth 0.5%: ${total_depth_0_5pct:,.0f}"
            )
        else:
            # Если нет данных о стакане, пропускаем фильтр по глубине
            results['min_depth_0_5pct'] = OptimizedFilterResult(
                passed=True,  # Пропускаем фильтр
                value=None,
                threshold=self.liquidity_filters.min_depth_usd_0_5pct,
                reason="No L2 depth data available"
            )
        
        # Trades per minute filter
        results['min_trades_per_minute'] = OptimizedFilterResult(
            passed=market_data.trades_per_minute >= self.liquidity_filters.min_trades_per_minute,
            value=market_data.trades_per_minute,
            threshold=self.liquidity_filters.min_trades_per_minute,
            reason=f"Trades/min: {market_data.trades_per_minute:.1f}"
        )
        
        # Cache the result and update access order
        self._filter_cache[cache_key] = (results, time.time())
        # Add to access order for LRU tracking
        if cache_key in self._cache_access_order:
            self._cache_access_order.remove(cache_key)
        self._cache_access_order.append(cache_key)
        
        return results
    
    def apply_volatility_filters(self, market_data: MarketData, metrics: OptimizedScanMetrics) -> Dict[str, OptimizedFilterResult]:
        """Apply volatility-based filters with caching."""
        results = {}
        
        # ATR range filter
        atr_ratio = market_data.atr_15m / market_data.price if market_data.price > 0 else 0
        results['atr_range'] = OptimizedFilterResult(
            passed=(self.volatility_filters.atr_range_min <= atr_ratio <= 
                   self.volatility_filters.atr_range_max),
            value=atr_ratio,
            threshold=f"{self.volatility_filters.atr_range_min}-{self.volatility_filters.atr_range_max}",
            reason=f"ATR ratio: {atr_ratio:.4f}"
        )
        
        # Bollinger Band width filter
        results['bb_width'] = OptimizedFilterResult(
            passed=market_data.bb_width_pct <= self.volatility_filters.bb_width_percentile_max,
            value=market_data.bb_width_pct,
            threshold=self.volatility_filters.bb_width_percentile_max,
            reason=f"BB width: {market_data.bb_width_pct:.1f}%"
        )
        
        # Volume surge filters
        results['volume_surge_1h'] = OptimizedFilterResult(
            passed=metrics.vol_surge_1h >= self.volatility_filters.volume_surge_1h_min,
            value=metrics.vol_surge_1h,
            threshold=self.volatility_filters.volume_surge_1h_min,
            reason=f"Vol surge 1h: {metrics.vol_surge_1h:.1f}x"
        )
        
        results['volume_surge_5m'] = OptimizedFilterResult(
            passed=metrics.vol_surge_5m >= self.volatility_filters.volume_surge_5m_min,
            value=metrics.vol_surge_5m,
            threshold=self.volatility_filters.volume_surge_5m_min,
            reason=f"Vol surge 5m: {metrics.vol_surge_5m:.1f}x"
        )
        
        return results
    
    def apply_correlation_filter(self, market_data: MarketData) -> Dict[str, OptimizedFilterResult]:
        """Apply correlation-based filters."""
        results = {}
        
        correlation_limit = self.preset.risk.correlation_limit
        abs_correlation = abs(market_data.btc_correlation)
        
        results['correlation'] = OptimizedFilterResult(
            passed=abs_correlation <= correlation_limit,
            value=abs_correlation,
            threshold=correlation_limit,
            reason=f"BTC correlation: {market_data.btc_correlation:.2f}"
        )
        
        return results


class OptimizedMarketScorer:
    """Memory-efficient market scoring system with optimized calculations."""
    
    def __init__(self, score_weights: Dict[str, float]):
        self.weights = score_weights
        self._validate_weights()
        
        # Memory-optimized cache with size limits and LRU eviction
        self._cache = {}
        self._cache_ttl = 300  # 5 minutes
        self._max_cache_size = 200  # Reduced from 500 to save memory
        self._cache_access_order = []  # For LRU tracking
        
        # Pre-computed constants for better performance
        self._vol_surge_mean = 1.5
        self._vol_surge_std = 1.0
        self._oi_delta_std = 0.05
        self._atr_quality_mean = 0.5
        self._atr_quality_std = 0.2
    
    def _validate_weights(self):
        """Validate that weights are reasonable."""
        total_abs_weight = sum(abs(w) for w in self.weights.values())
        if not 0.8 <= total_abs_weight <= 1.2:
            logger.warning(f"Score weights sum to {total_abs_weight:.2f}, expected ~1.0")
    
    def _generate_cache_key(self, metrics: OptimizedScanMetrics, market_data: MarketData) -> str:
        """Generate optimized cache key."""
        # Use only essential values for cache key
        key_data = f"{metrics.vol_surge_1h:.2f}_{metrics.vol_surge_5m:.2f}_{metrics.atr_quality:.2f}_{market_data.btc_correlation:.2f}_{market_data.trades_per_minute:.1f}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def _cleanup_cache(self):
        """Remove expired cache entries and enforce LRU eviction."""
        now = time.time()
        expired_keys = [k for k, (_, timestamp) in self._cache.items() if now - timestamp > self._cache_ttl]
        for key in expired_keys:
            del self._cache[key]
            if key in self._cache_access_order:
                self._cache_access_order.remove(key)
        
        # LRU eviction if still over limit
        while len(self._cache) > self._max_cache_size and self._cache_access_order:
            oldest_key = self._cache_access_order.pop(0)
            if oldest_key in self._cache:
                del self._cache[oldest_key]
    
    def calculate_score(self, metrics: OptimizedScanMetrics, market_data: MarketData) -> Tuple[float, Dict[str, float]]:
        """Calculate overall score with optimized computation."""
        # Create cache key
        cache_key = self._generate_cache_key(metrics, market_data)
        
        # Check cache first
        if cache_key in self._cache:
            cached_result, timestamp = self._cache[cache_key]
            if time.time() - timestamp < self._cache_ttl:
                # Update LRU order
                if cache_key in self._cache_access_order:
                    self._cache_access_order.remove(cache_key)
                self._cache_access_order.append(cache_key)
                return cached_result
        
        # Cleanup cache if needed
        if len(self._cache) > self._max_cache_size:
            self._cleanup_cache()
        
        # Calculate score components with optimized operations
        components = {}
        
        # Volume surge component (optimized)
        if 'vol_surge' in self.weights:
            vol_surge_score = self._normalize_volume_surge_optimized(metrics.vol_surge_1h, metrics.vol_surge_5m)
            components['vol_surge'] = vol_surge_score * self.weights['vol_surge']
        
        # ATR quality component (optimized)
        if 'atr_quality' in self.weights:
            atr_score = self._normalize_atr_quality_optimized(metrics.atr_quality)
            components['atr_quality'] = atr_score * self.weights['atr_quality']
        
        # Correlation component (optimized)
        if 'correlation' in self.weights:
            corr_score = self._normalize_correlation_optimized(market_data.btc_correlation)
            components['correlation'] = corr_score * self.weights['correlation']
        
        # Trades per minute component (optimized)
        if 'trades_per_minute' in self.weights:
            trades_score = self._normalize_trades_per_minute_optimized(market_data.trades_per_minute)
            components['trades_per_minute'] = trades_score * self.weights['trades_per_minute']
        
        # Calculate total score
        total_score = sum(components.values())
        
        result = (total_score, components)
        
        # Cache the result with size limit
        if len(self._cache) >= self._max_cache_size:
            # Remove oldest entries to make room
            oldest_key = min(self._cache.keys(), key=lambda k: self._cache[k][1])
            del self._cache[oldest_key]
            if oldest_key in self._cache_access_order:
                self._cache_access_order.remove(oldest_key)
        
        self._cache[cache_key] = (result, time.time())
        self._cache_access_order.append(cache_key)
        
        return result
    
    def _normalize_volume_surge_optimized(self, surge_1h: float, surge_5m: float) -> float:
        """Optimized volume surge normalization using pre-computed constants."""
        # Use pre-computed constants for better performance
        combined_surge = surge_1h * 0.6 + surge_5m * 0.4
        z_score = (combined_surge - self._vol_surge_mean) / self._vol_surge_std
        return np.clip(z_score, -3, 3)
    
    def _normalize_atr_quality_optimized(self, atr_quality: float) -> float:
        """Optimized ATR quality normalization."""
        z_score = (atr_quality - self._atr_quality_mean) / self._atr_quality_std
        return np.clip(z_score, -3, 3)
    
    def _normalize_correlation_optimized(self, correlation: float) -> float:
        """Optimized correlation normalization."""
        abs_corr = abs(correlation)
        score = 2 * (1 - abs_corr) - 1
        return np.clip(score, -3, 3)
    
    def _normalize_trades_per_minute_optimized(self, trades_per_minute: float) -> float:
        """Optimized trades per minute normalization."""
        if trades_per_minute <= 0:
            return -3
        
        log_trades = np.log(trades_per_minute)
        z_score = (log_trades - 2.0) / 1.0
        return np.clip(z_score, -3, 3)


class OptimizedBreakoutScanner:
    """Resource-optimized market scanner with parallel processing."""
    
    def __init__(self, preset: TradingPreset):
        self.preset = preset
        self.filter = OptimizedMarketFilter("breakout_filter", preset)
        self.scorer = OptimizedMarketScorer(preset.scanner_config.score_weights)
        self.level_detector = LevelDetector()
        
        # Resource monitoring
        self.resource_monitor = get_resource_monitor()
        
        # Thread pool for parallel processing
        self.thread_pool = ThreadPoolExecutor(
            max_workers=min(4, psutil.cpu_count()),
            thread_name_prefix="scanner"
        )
        
        # Batch processing settings
        self.batch_size = 20  # Process markets in batches
        self.max_concurrent_batches = 2
        
        logger.info(f"Initialized optimized scanner with preset: {preset.name}")
    
    async def scan_markets(self, market_data_list: List[MarketData], 
                          btc_data: Optional[MarketData] = None) -> List[ScanResult]:
        """
        Scan markets with resource optimization and parallel processing.
        """
        logger.info(f"Scanning {len(market_data_list)} markets with optimized scanner")
        
        # Check resource usage before starting
        current_metrics = self.resource_monitor.get_current_metrics()
        if current_metrics:
            if current_metrics.memory_percent > 85:
                logger.warning("High memory usage detected, reducing batch size")
                self.batch_size = 10
            elif current_metrics.memory_percent > 70:
                self.batch_size = 15
        
        # Apply symbol filters first
        filtered_markets = self._apply_symbol_filters(market_data_list)
        logger.info(f"After symbol filtering: {len(filtered_markets)} markets")
        
        # Apply volume-based filtering if configured
        if self.preset.scanner_config.top_n_by_volume:
            filtered_markets = self._filter_by_volume(filtered_markets, 
                                                    self.preset.scanner_config.top_n_by_volume)
            logger.info(f"After volume filtering: {len(filtered_markets)} markets")
        
        # Process markets in batches
        scan_results = []
        batches = [filtered_markets[i:i + self.batch_size] 
                  for i in range(0, len(filtered_markets), self.batch_size)]
        
        # Process batches with limited concurrency
        semaphore = asyncio.Semaphore(self.max_concurrent_batches)
        
        async def process_batch(batch):
            async with semaphore:
                return await self._process_market_batch(batch, btc_data)
        
        # Process all batches
        batch_tasks = [process_batch(batch) for batch in batches]
        batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
        
        # Collect results
        for batch_result in batch_results:
            if isinstance(batch_result, Exception):
                logger.error(f"Error processing batch: {batch_result}")
            else:
                scan_results.extend(batch_result)
        
        # Sort by score (highest first)
        scan_results.sort(key=lambda x: x.score, reverse=True)
        
        # Limit to max candidates
        max_candidates = self.preset.scanner_config.max_candidates
        final_results = scan_results[:max_candidates]
        
        # Update rankings
        for i, result in enumerate(final_results):
            result.rank = i + 1
        
        logger.info(f"Optimized scan complete: {len(final_results)} candidates found")
        
        # Force garbage collection after scanning
        gc.collect()
        
        return final_results
    
    async def _process_market_batch(self, market_batch: List[MarketData], 
                                   btc_data: Optional[MarketData]) -> List[ScanResult]:
        """Process a batch of markets."""
        results = []
        
        for market_data in market_batch:
            try:
                result = await self._scan_single_market_optimized(market_data, btc_data)
                if result:
                    results.append(result)
            except Exception as e:
                logger.error(f"Error scanning {market_data.symbol}: {e}")
                continue
        
        return results
    
    async def _scan_single_market_optimized(self, market_data: MarketData, 
                                          btc_data: Optional[MarketData]) -> Optional[ScanResult]:
        """Scan a single market with optimized processing."""
        
        # Calculate scan metrics
        metrics = self._calculate_scan_metrics_optimized(market_data, btc_data)
        
        # Apply all filters
        filter_results = {}
        
        # Liquidity filters
        liquidity_results = self.filter.apply_liquidity_filters(market_data)
        filter_results.update(liquidity_results)
        
        # Volatility filters
        volatility_results = self.filter.apply_volatility_filters(market_data, metrics)
        filter_results.update(volatility_results)
        
        # Correlation filters
        correlation_results = self.filter.apply_correlation_filter(market_data)
        filter_results.update(correlation_results)
        
        # Check if all filters passed
        all_passed = all(result.passed for result in filter_results.values())
        
        # Calculate score regardless of filter results (for analysis)
        score, score_components = self.scorer.calculate_score(metrics, market_data)
        
        # Detect levels (only if filters passed to save CPU)
        levels = []
        if all_passed and market_data.candles_5m:
            try:
                levels = self.level_detector.detect_levels(market_data.candles_5m)
            except Exception as e:
                logger.warning(f"Level detection failed for {market_data.symbol}: {e}")
        
        # Create scan result
        scan_result = ScanResult(
            symbol=market_data.symbol,
            score=score,
            rank=0,  # Will be set later
            market_data=market_data,
            filter_results={name: result.passed for name, result in filter_results.items()},
            score_components=score_components,
            levels=levels,
            timestamp=int(datetime.now().timestamp() * 1000),
            passed_all_filters=all_passed
        )
        
        # Log filter results for debugging
        if all_passed:
            logger.debug(f"{market_data.symbol}: PASSED - Score: {score:.3f}")
        else:
            failed_filters = [name for name, result in filter_results.items() if not result.passed]
            logger.debug(f"{market_data.symbol}: FAILED - {failed_filters}")
        
        return scan_result
    
    def _calculate_scan_metrics_optimized(self, market_data: MarketData, 
                                        btc_data: Optional[MarketData]) -> OptimizedScanMetrics:
        """Calculate scan metrics with optimized NumPy operations."""
        metrics = OptimizedScanMetrics()
        
        if market_data.candles_5m and len(market_data.candles_5m) >= 20:
            candles = market_data.candles_5m
            
            # Convert to numpy array once for better performance
            volumes = np.array([c.volume for c in candles], dtype=np.float32)  # Use float32 to save memory
            
            # Optimized volume surge calculations
            if len(volumes) >= 24:
                # 1h volume surge (last 12 candles vs previous 12)
                recent_vol = np.mean(volumes[-12:])
                older_vol = np.mean(volumes[-24:-12])
                metrics.vol_surge_1h = float(recent_vol / older_vol if older_vol > 0 else 1.0
            
            if len(volumes) >= 21:
                # 5m volume surge (last candle vs median of previous 20)
                current_vol = volumes[-1]
                median_vol = np.median(volumes[-21:-1])
                metrics.vol_surge_5m = current_vol / median_vol if median_vol > 0 else 1.0
            
            # ATR quality metric with optimized calculation
            atr_values = atr(candles, period=14)
            if not np.isnan(atr_values[-1]):
                atr_ratio = atr_values[-1] / market_data.price
                metrics.atr_quality = self._calculate_atr_quality_optimized(atr_ratio)
        
        # Other metrics from market data
        metrics.bb_width_pct = market_data.bb_width_pct
        metrics.btc_correlation = market_data.btc_correlation
        metrics.trades_per_minute = market_data.trades_per_minute
        metrics.liquidity_score = market_data.liquidity_score
        
        return metrics
    
    def _calculate_atr_quality_optimized(self, atr_ratio: float) -> float:
        """Calculate ATR quality metric with optimized logic."""
        optimal_min = 0.015
        optimal_max = 0.035
        optimal_mid = (optimal_min + optimal_max) / 2
        
        if optimal_min <= atr_ratio <= optimal_max:
            return 1.0 - abs(atr_ratio - optimal_mid) / (optimal_max - optimal_min)
        else:
            # Penalty for being outside optimal range
            if atr_ratio < optimal_min:
                return max(0, 1.0 - (optimal_min - atr_ratio) / optimal_min)
            else:
                return max(0, 1.0 - (atr_ratio - optimal_max) / optimal_max)
    
    def _apply_symbol_filters(self, market_data_list: List[MarketData]) -> List[MarketData]:
        """Apply whitelist/blacklist symbol filters."""
        filtered = market_data_list
        
        # Apply whitelist filter
        if self.preset.scanner_config.symbol_whitelist:
            whitelist = set(self.preset.scanner_config.symbol_whitelist)
            filtered = [md for md in filtered if md.symbol in whitelist]
        
        # Apply blacklist filter
        if self.preset.scanner_config.symbol_blacklist:
            blacklist = set(self.preset.scanner_config.symbol_blacklist)
            filtered = [md for md in filtered if md.symbol not in blacklist]
        
        return filtered
    
    def _filter_by_volume(self, market_data_list: List[MarketData], top_n: int) -> List[MarketData]:
        """Filter to top N markets by volume."""
        sorted_by_volume = sorted(market_data_list, 
                                key=lambda x: x.volume_24h_usd, 
                                reverse=True)
        return sorted_by_volume[:top_n]
    
    def cleanup(self):
        """Cleanup resources."""
        if hasattr(self, 'thread_pool'):
            self.thread_pool.shutdown(wait=True)
        
        # Clear caches
        self.filter._filter_cache.clear()
        self.scorer._cache.clear()
        
        # Force garbage collection
        gc.collect()
        
        logger.info("Optimized scanner cleanup completed")
