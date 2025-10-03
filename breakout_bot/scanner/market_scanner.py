"""
Market scanner for Breakout Bot Trading System.

This module implements the market scanning system with multi-stage filtering
and scoring algorithms to identify the best breakout candidates.
"""

import asyncio
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
import logging
import hashlib
import time
from functools import lru_cache

from ..data.models import Candle, L2Depth, MarketData, ScanResult, TradingLevel
from ..config.settings import TradingPreset, LiquidityFilters, VolatilityFilters, ScannerConfig
from ..indicators.technical import (
    atr, bollinger_bands, bollinger_band_width, vwap, 
    calculate_correlation, volume_surge_ratio
)
from ..indicators.levels import LevelDetector
from ..diagnostics import DiagnosticsCollector

logger = logging.getLogger(__name__)


@dataclass
class FilterResult:
    """Result of a single filter application."""
    passed: bool
    value: Optional[float] = None
    threshold: Optional[float] = None
    reason: str = ""


@dataclass
class ScanMetrics:
    """Metrics calculated during scanning."""
    vol_surge_1h: float = 0.0
    vol_surge_5m: float = 0.0
    oi_delta_24h: float = 0.0
    atr_quality: float = 0.0
    bb_width_pct: float = 0.0
    btc_correlation: float = 0.0
    trades_per_minute: float = 0.0
    liquidity_score: float = 0.0
    depth_score: float = 0.0
    spread_score: float = 0.0


class MarketFilter:
    """Individual market filter implementation."""
    
    def __init__(self, name: str, preset: TradingPreset):
        self.name = name
        self.preset = preset
        self.liquidity_filters = preset.liquidity_filters
        self.volatility_filters = preset.volatility_filters
    
    def apply_liquidity_filters(self, market_data: MarketData) -> Dict[str, FilterResult]:
        """Apply liquidity-based filters."""
        results = {}
        
        # 24h Volume filter
        results['min_24h_volume'] = FilterResult(
            passed=market_data.volume_24h_usd >= self.liquidity_filters.min_24h_volume_usd,
            value=market_data.volume_24h_usd,
            threshold=self.liquidity_filters.min_24h_volume_usd,
            reason=f"24h volume: ${market_data.volume_24h_usd:,.0f}"
        )
        
        # Open Interest filter (if available)
        # Skip OI filter for spot markets (they don't have OI)
        market_type = getattr(market_data, 'market_type', 'unknown')
        
        if self.liquidity_filters.min_oi_usd is not None:
            if market_type == 'spot':
                # Spot markets don't have OI - skip this filter
                results['min_oi'] = FilterResult(
                    passed=True,
                    value=None,
                    threshold=self.liquidity_filters.min_oi_usd,
                    reason="Spot market (OI filter skipped)"
                )
            elif market_data.oi_usd is not None:
                results['min_oi'] = FilterResult(
                    passed=market_data.oi_usd >= self.liquidity_filters.min_oi_usd,
                    value=market_data.oi_usd,
                    threshold=self.liquidity_filters.min_oi_usd,
                    reason=f"OI: ${market_data.oi_usd:,.0f}"
                )
        
        # Spread filter (с проверкой на None)
        if market_data.l2_depth is not None:
            results['max_spread'] = FilterResult(
                passed=market_data.l2_depth.spread_bps <= self.liquidity_filters.max_spread_bps,
                value=market_data.l2_depth.spread_bps,
                threshold=self.liquidity_filters.max_spread_bps,
                reason=f"Spread: {market_data.l2_depth.spread_bps:.1f} bps"
            )
        else:
            # Если нет данных о стакане, пропускаем фильтр по спреду
            results['max_spread'] = FilterResult(
                passed=True,  # Пропускаем фильтр
                value=None,
                threshold=self.liquidity_filters.max_spread_bps,
                reason="No L2 depth data available"
            )
        
        # Depth filters (с проверкой на None)
        if market_data.l2_depth is not None:
            results['min_depth_0_5pct'] = FilterResult(
                passed=market_data.l2_depth.bid_usd_0_5pct + market_data.l2_depth.ask_usd_0_5pct >= 
                       self.liquidity_filters.min_depth_usd_0_5pct,
                value=market_data.l2_depth.bid_usd_0_5pct + market_data.l2_depth.ask_usd_0_5pct,
                threshold=self.liquidity_filters.min_depth_usd_0_5pct,
                reason=f"Depth 0.5%: ${market_data.l2_depth.total_depth_usd_0_5pct:,.0f}"
            )
            
            results['min_depth_0_3pct'] = FilterResult(
                passed=market_data.l2_depth.bid_usd_0_3pct + market_data.l2_depth.ask_usd_0_3pct >= 
                       self.liquidity_filters.min_depth_usd_0_3pct,
                value=market_data.l2_depth.bid_usd_0_3pct + market_data.l2_depth.ask_usd_0_3pct,
                threshold=self.liquidity_filters.min_depth_usd_0_3pct,
                reason=f"Depth 0.3%: ${market_data.l2_depth.total_depth_usd_0_3pct:,.0f}"
            )
        else:
            # Если нет данных о стакане, пропускаем фильтры по глубине
            results['min_depth_0_5pct'] = FilterResult(
                passed=True,  # Пропускаем фильтр
                value=None,
                threshold=self.liquidity_filters.min_depth_usd_0_5pct,
                reason="No L2 depth data available"
            )
            
            results['min_depth_0_3pct'] = FilterResult(
                passed=True,  # Пропускаем фильтр
                value=None,
                threshold=self.liquidity_filters.min_depth_usd_0_3pct,
                reason="No L2 depth data available"
            )
        
        # Trades per minute filter
        results['min_trades_per_minute'] = FilterResult(
            passed=market_data.trades_per_minute >= self.liquidity_filters.min_trades_per_minute,
            value=market_data.trades_per_minute,
            threshold=self.liquidity_filters.min_trades_per_minute,
            reason=f"Trades/min: {market_data.trades_per_minute:.1f}"
        )
        
        return results
    
    def apply_volatility_filters(self, market_data: MarketData, metrics: ScanMetrics) -> Dict[str, FilterResult]:
        """Apply volatility-based filters."""
        results = {}
        
        # ATR range filter
        atr_ratio = market_data.atr_15m / market_data.price if market_data.price > 0 else 0
        results['atr_range'] = FilterResult(
            passed=(self.volatility_filters.atr_range_min <= atr_ratio <= 
                   self.volatility_filters.atr_range_max),
            value=atr_ratio,
            threshold=f"{self.volatility_filters.atr_range_min}-{self.volatility_filters.atr_range_max}",
            reason=f"ATR ratio: {atr_ratio:.4f}"
        )
        
        # Bollinger Band width filter
        results['bb_width'] = FilterResult(
            passed=market_data.bb_width_pct <= self.volatility_filters.bb_width_percentile_max,
            value=market_data.bb_width_pct,
            threshold=self.volatility_filters.bb_width_percentile_max,
            reason=f"BB width: {market_data.bb_width_pct:.1f}%"
        )
        
        # Volume surge filters
        results['volume_surge_1h'] = FilterResult(
            passed=metrics.vol_surge_1h >= self.volatility_filters.volume_surge_1h_min,
            value=metrics.vol_surge_1h,
            threshold=self.volatility_filters.volume_surge_1h_min,
            reason=f"Vol surge 1h: {metrics.vol_surge_1h:.1f}x"
        )
        
        results['volume_surge_5m'] = FilterResult(
            passed=metrics.vol_surge_5m >= self.volatility_filters.volume_surge_5m_min,
            value=metrics.vol_surge_5m,
            threshold=self.volatility_filters.volume_surge_5m_min,
            reason=f"Vol surge 5m: {metrics.vol_surge_5m:.1f}x"
        )
        
        # OI delta filter (if available)
        if (market_data.oi_change_24h is not None and 
            self.volatility_filters.oi_delta_threshold is not None):
            results['oi_delta'] = FilterResult(
                passed=abs(market_data.oi_change_24h) >= self.volatility_filters.oi_delta_threshold,
                value=market_data.oi_change_24h,
                threshold=self.volatility_filters.oi_delta_threshold,
                reason=f"OI delta: {market_data.oi_change_24h:.2f}"
            )
        
        return results
    
    def apply_correlation_filter(self, market_data: MarketData) -> Dict[str, FilterResult]:
        """Apply correlation-based filters."""
        results = {}
        
        correlation_limit = self.preset.risk.correlation_limit
        abs_correlation = abs(market_data.btc_correlation)
        
        # More lenient correlation filter - only reject extremely high correlations
        # Allow moderate correlations (0.3-0.8) as they can still provide opportunities
        effective_limit = max(correlation_limit, 0.85)  # At least 0.85 limit
        
        results['correlation'] = FilterResult(
            passed=abs_correlation <= effective_limit,
            value=abs_correlation,
            threshold=effective_limit,
            reason=f"BTC correlation: {market_data.btc_correlation:.2f} (limit: {effective_limit:.2f})"
        )
        
        return results


class MarketScorer:
    """Market scoring system using weighted metrics with caching."""
    
    def __init__(self, score_weights: Dict[str, float]):
        self.weights = score_weights
        self._validate_weights()
        self._cache = {}
        self._cache_ttl = 300  # 5 minutes
    
    def _validate_weights(self):
        """Validate that weights are reasonable."""
        total_abs_weight = sum(abs(w) for w in self.weights.values())
        if not 0.8 <= total_abs_weight <= 1.2:
            logger.warning(f"Score weights sum to {total_abs_weight:.2f}, expected ~1.0")
    
    def calculate_score(self, metrics: ScanMetrics, market_data: MarketData) -> Tuple[float, Dict[str, float]]:
        """Calculate overall score and component scores with caching."""
        # Create cache key based on metrics and market data
        cache_key = self._generate_cache_key(metrics, market_data)
        
        # Check cache first
        if cache_key in self._cache:
            cached_result, timestamp = self._cache[cache_key]
            if time.time() - timestamp < self._cache_ttl:
                return cached_result
        
        # Calculate score if not in cache
        components = {}
        
        # Volume surge component
        if 'vol_surge' in self.weights:
            vol_surge_score = self._normalize_volume_surge(metrics.vol_surge_1h, metrics.vol_surge_5m)
            components['vol_surge'] = vol_surge_score * self.weights['vol_surge']
        
        # OI delta component
        if 'oi_delta' in self.weights:
            oi_score = self._normalize_oi_delta(metrics.oi_delta_24h)
            components['oi_delta'] = oi_score * self.weights['oi_delta']
        
        # ATR quality component
        if 'atr_quality' in self.weights:
            atr_score = self._normalize_atr_quality(metrics.atr_quality)
            components['atr_quality'] = atr_score * self.weights['atr_quality']
        
        # Correlation component (negative correlation is good)
        if 'correlation' in self.weights:
            corr_score = self._normalize_correlation(market_data.btc_correlation)
            components['correlation'] = corr_score * self.weights['correlation']
        
        # Trades per minute component
        if 'trades_per_minute' in self.weights:
            trades_score = self._normalize_trades_per_minute(market_data.trades_per_minute)
            components['trades_per_minute'] = trades_score * self.weights['trades_per_minute']
        
        # Special components for specific presets
        if 'gainers_momentum' in self.weights:
            gainers_score = self._calculate_gainers_momentum(market_data)
            components['gainers_momentum'] = gainers_score * self.weights['gainers_momentum']
        
        # Calculate total score
        total_score = sum(components.values())
        
        result = (total_score, components)
        
        # Cache the result
        self._cache[cache_key] = (result, time.time())
        
        # Clean up old cache entries
        self._cleanup_cache()
        
        return result
    
    def _generate_cache_key(self, metrics: ScanMetrics, market_data: MarketData) -> str:
        """Generate cache key for metrics and market data."""
        key_data = f"{metrics.vol_surge_1h}_{metrics.vol_surge_5m}_{metrics.oi_delta_24h}_{metrics.atr_quality}_{market_data.btc_correlation}_{market_data.trades_per_minute}_{market_data.price}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def _cleanup_cache(self):
        """Remove expired cache entries."""
        now = time.time()
        expired_keys = [k for k, (_, timestamp) in self._cache.items() if now - timestamp > self._cache_ttl]
        for key in expired_keys:
            del self._cache[key]
    
    def _normalize_volume_surge(self, surge_1h: float, surge_5m: float) -> float:
        """Normalize volume surge to z-score-like value with optimized calculation."""
        # Combine 1h and 5m surges with weighting using vectorized operations
        combined_surge = np.dot([surge_1h, surge_5m], [0.6, 0.4])
        
        # Convert to z-score (assume mean=1.5, std=1.0 for volume surges)
        z_score = (combined_surge - 1.5) / 1.0
        
        # Cap at reasonable bounds using numpy clip for better performance
        return np.clip(z_score, -3, 3)
    
    def _normalize_oi_delta(self, oi_delta: float) -> float:
        """Normalize OI delta to z-score-like value."""
        if oi_delta is None:
            return 0.0
        
        # Convert to z-score (assume mean=0, std=0.05 for OI changes)
        z_score = abs(oi_delta) / 0.05
        
        return np.clip(z_score, -3, 3)
    
    def _normalize_atr_quality(self, atr_quality: float) -> float:
        """Normalize ATR quality metric."""
        # Higher ATR quality means better volatility for breakouts
        # Convert to z-score (assume mean=0.5, std=0.2)
        z_score = (atr_quality - 0.5) / 0.2
        
        return np.clip(z_score, -3, 3)
    
    def _normalize_correlation(self, correlation: float) -> float:
        """Normalize correlation (moderate correlation is better than extreme correlation)."""
        # Handle NaN or invalid correlation
        if np.isnan(correlation) or correlation is None:
            return 0.0
            
        abs_corr = abs(correlation)
        
        # Optimal correlation range is 0.3-0.7 (moderate correlation)
        # Score peaks at 0.5 correlation, decreases towards 0 and 1
        if abs_corr <= 0.3:
            # Low correlation - good for diversification
            score = 1.0 - (abs_corr / 0.3) * 0.5
        elif abs_corr <= 0.7:
            # Moderate correlation - optimal range
            score = 1.0
        else:
            # High correlation - less desirable
            score = 1.0 - ((abs_corr - 0.7) / 0.3) * 1.5
        
        return np.clip(score, -2, 2)
    
    def _normalize_trades_per_minute(self, trades_per_minute: float) -> float:
        """Normalize trades per minute metric."""
        # Convert to log scale and normalize
        if trades_per_minute <= 0:
            return -3
        
        log_trades = np.log(trades_per_minute)
        # Assume mean log(trades) = 2.0, std = 1.0
        z_score = (log_trades - 2.0) / 1.0
        
        return np.clip(z_score, -3, 3)
    
    def _calculate_gainers_momentum(self, market_data: MarketData) -> float:
        """Calculate momentum score for gainers strategy with optimized NumPy operations."""
        if not market_data.candles_5m or len(market_data.candles_5m) < 5:
            return 0.0
        
        recent_candles = market_data.candles_5m[-5:]  # Last 5 candles
        
        # Convert to numpy arrays for vectorized operations
        # Use float32 for memory efficiency (50% memory savings)
        closes = np.array([c.close for c in recent_candles], dtype=np.float32)
        opens = np.array([c.open for c in recent_candles], dtype=np.float32)
        volumes = np.array([c.volume for c in recent_candles], dtype=np.float32)
        
        # Calculate price momentum using vectorized operations
        price_change = (closes[-1] - opens[0]) / opens[0]
        
        # Calculate volume momentum using numpy operations
        recent_vol = np.mean(volumes[-3:])
        older_vol = np.mean(volumes[:2])
        vol_momentum = recent_vol / older_vol if older_vol > 0 else 1.0
        
        # Combine price and volume momentum
        momentum_score = price_change * 100 + np.log(vol_momentum)
        
        return np.clip(momentum_score, -3, 3)


class BreakoutScanner:
    """Main market scanner for breakout opportunities."""
    
    def __init__(self, preset: TradingPreset, diagnostics: Optional[DiagnosticsCollector] = None):
        self.preset = preset
        self.filter = MarketFilter("breakout_filter", preset)
        self.scorer = MarketScorer(preset.scanner_config.score_weights)
        self.level_detector = LevelDetector()
        self.diagnostics = diagnostics
        
        logger.info(f"Initialized scanner with preset: {preset.name}")
    
    async def scan_markets(self, market_data_list: List[MarketData], 
                          btc_data: Optional[MarketData] = None) -> List[ScanResult]:
        """
        Оптимизированное сканирование рынков с batch processing.
        
        Args:
            market_data_list: List of market data for all symbols
            btc_data: BTC market data for correlation analysis
        
        Returns:
            List of ScanResult objects, ranked by score
        """
        logger.info(f"Scanning {len(market_data_list)} markets with preset {self.preset.name}")
        
        # Apply symbol filters first
        filtered_markets = self._apply_symbol_filters(market_data_list)
        logger.info(f"After symbol filtering: {len(filtered_markets)} markets")
        
        # Apply volume-based filtering if configured
        if self.preset.scanner_config.top_n_by_volume is not None:
            filtered_markets = self._filter_by_volume(filtered_markets, 
                                                    self.preset.scanner_config.top_n_by_volume)
            logger.info(f"After volume filtering: {len(filtered_markets)} markets")
        
        # Оптимизированная обработка с batch processing
        scan_results = await self._scan_markets_batch(filtered_markets, btc_data)
        
        # Sort by score and assign ranks
        scan_results.sort(key=lambda x: x.score, reverse=True)
        for i, result in enumerate(scan_results):
            result.rank = i + 1
        
        logger.info(f"Scan completed: {len(scan_results)} results")
        return scan_results
    
    async def _scan_markets_batch(self, market_data_list: List[MarketData], 
                                 btc_data: Optional[MarketData] = None) -> List[ScanResult]:
        """Оптимизированное batch сканирование с параллельной обработкой."""
        import asyncio
        
        # Обрабатываем рынки батчами для оптимизации
        batch_size = 5  # Оптимальный размер батча
        scan_results = []
        
        for i in range(0, len(market_data_list), batch_size):
            batch = market_data_list[i:i + batch_size]
            
            # Создаем задачи для параллельной обработки батча
            batch_tasks = [
                self._scan_single_market_optimized(market_data, btc_data) 
                for market_data in batch
            ]
            
            # Выполняем батч параллельно
            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
            
            # Собираем успешные результаты
            for result in batch_results:
                if isinstance(result, ScanResult):
                    scan_results.append(result)
                elif isinstance(result, Exception):
                    logger.warning(f"Scan error: {result}")
        
        return scan_results
    
    async def _scan_single_market_optimized(self, market_data: MarketData, 
                                          btc_data: Optional[MarketData] = None) -> Optional[ScanResult]:
        """Оптимизированное сканирование одного рынка."""
        try:
            # Используем существующий метод сканирования
            return await self._scan_single_market(market_data, btc_data)
        except Exception as e:
            logger.error(f"Error scanning {market_data.symbol}: {e}")
            return None
    
    async def build_levels(self, scan_result: ScanResult) -> List[TradingLevel]:
        """Build trading levels for a scan result."""
        try:
            logger.debug(f"Building levels for {scan_result.symbol}")
            
            if not scan_result.market_data.candles_5m:
                logger.debug(f"No candles data for {scan_result.symbol}")
                return []
            
            logger.debug(f"Found {len(scan_result.market_data.candles_5m)} candles for {scan_result.symbol}")
            
            # Use LevelDetector to find levels
            level_detector = LevelDetector()
            logger.debug(f"Created LevelDetector for {scan_result.symbol}")
            
            levels = level_detector.detect_levels(
                scan_result.market_data.candles_5m
            )
            
            logger.debug(f"Detected {len(levels)} levels for {scan_result.symbol}")
            return levels
            
        except Exception as e:
            logger.error(f"Level building failed for {scan_result.symbol}: {type(e).__name__}: {str(e)}")
            return []
    
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
    
    async def _scan_single_market(self, market_data: MarketData, 
                                btc_data: Optional[MarketData] = None) -> Optional[ScanResult]:
        """Scan a single market and return result if it passes filters."""
        
        # PATCH 004: Generate correlation_id for end-to-end tracing
        import time
        correlation_id = f"{market_data.symbol}:{int(time.time() * 1000)}"
        
        # Calculate scan metrics
        metrics = self._calculate_scan_metrics(market_data, btc_data)

        if self.diagnostics and self.diagnostics.enabled:
            l2 = market_data.l2_depth or L2Depth(
                bid_usd_0_5pct=0,
                ask_usd_0_5pct=0,
                bid_usd_0_3pct=0,
                ask_usd_0_3pct=0,
                spread_bps=0,
                imbalance=0,
            )
            self.diagnostics.record(
                component="scanner",
                stage="metrics",
                symbol=market_data.symbol,
                payload={
                    "vol_24h_usd": market_data.volume_24h_usd,
                    "oi_usd": market_data.oi_usd,
                    "spread_bps": l2.spread_bps,
                    "depth_0_5": l2.total_depth_usd_0_5pct,
                    "depth_0_3": l2.total_depth_usd_0_3pct,
                    "trades_per_min": market_data.trades_per_minute,
                    "atr15m_pct": market_data.atr_15m / market_data.price if market_data.price else 0,
                    "bbwidth_pct": market_data.bb_width_pct,
                    "corr_btc": market_data.btc_correlation,
                    "vol_surge_1h": metrics.vol_surge_1h,
                    "vol_surge_5m": metrics.vol_surge_5m,
                },
            )

        # Apply all filters
        filter_results = {}

        # Liquidity filters
        liquidity_results = self.filter.apply_liquidity_filters(market_data)
        filter_results.update(liquidity_results)

        if self.diagnostics and self.diagnostics.enabled:
            for name, result in liquidity_results.items():
                self.diagnostics.record_filter(
                    stage="liquidity",
                    symbol=market_data.symbol,
                    filter_name=name,
                    value=result.value,
                    threshold=result.threshold,
                    passed=result.passed,
                    extra={"reason_text": result.reason},
                )

        # Volatility filters
        volatility_results = self.filter.apply_volatility_filters(market_data, metrics)
        filter_results.update(volatility_results)

        if self.diagnostics and self.diagnostics.enabled:
            for name, result in volatility_results.items():
                self.diagnostics.record_filter(
                    stage="volatility",
                    symbol=market_data.symbol,
                    filter_name=name,
                    value=result.value,
                    threshold=result.threshold,
                    passed=result.passed,
                    extra={"reason_text": result.reason},
                )

        # Correlation filters
        correlation_results = self.filter.apply_correlation_filter(market_data)
        filter_results.update(correlation_results)

        if self.diagnostics and self.diagnostics.enabled:
            for name, result in correlation_results.items():
                self.diagnostics.record_filter(
                    stage="correlation",
                    symbol=market_data.symbol,
                    filter_name=name,
                    value=result.value,
                    threshold=result.threshold,
                    passed=result.passed,
                    extra={"reason_text": result.reason},
                )

        data_health_result = self._check_data_health(market_data)
        filter_results['data_health'] = data_health_result
        if self.diagnostics and self.diagnostics.enabled:
            self.diagnostics.record_filter(
                stage="data_health",
                symbol=market_data.symbol,
                filter_name="data_health",
                value=data_health_result.value,
                threshold=data_health_result.threshold,
                passed=data_health_result.passed,
                extra={"reason_text": data_health_result.reason},
            )
            if not data_health_result.passed:
                self.diagnostics.increment_reason("data:health_check_failed")
                for token in data_health_result.reason.split(';'):
                    token = token.strip()
                    if token and token != 'ok':
                        self.diagnostics.increment_reason(f"data:{token}")

        # Check if all filters passed
        all_passed = all(result.passed for result in filter_results.values())
        
        # Calculate score regardless of filter results (for analysis)
        score, score_components = self.scorer.calculate_score(metrics, market_data)
        
        # Detect levels
        levels = []
        if market_data.candles_5m:
            try:
                levels = self.level_detector.detect_levels(market_data.candles_5m)
            except Exception as e:
                logger.warning(f"Level detection failed for {market_data.symbol}: {e}")
        
        # Create scan result
        filter_bool_results = {name: result.passed for name, result in filter_results.items()}
        filter_details = {
            name: {
                'passed': result.passed,
                'value': result.value,
                'threshold': result.threshold,
                'reason': result.reason
            }
            for name, result in filter_results.items()
        }

        scan_result = ScanResult(
            symbol=market_data.symbol,
            score=score,
            rank=0,  # Will be set later
            market_data=market_data,
            filter_results=filter_bool_results,
            filter_details=filter_details,
            score_components=score_components,
            levels=levels,
            timestamp=int(time.time() * 1000),
            correlation_id=correlation_id  # PATCH 004: Add correlation_id for tracing
        )
        
        # Log filter results for debugging
        if all_passed:
            logger.debug(f"{market_data.symbol}: PASSED - Score: {score:.3f}")
        else:
            failed_filters = [name for name, result in filter_results.items() if not result.passed]
            logger.debug(f"{market_data.symbol}: FAILED - {failed_filters}")
        
        return scan_result
    
    def _calculate_scan_metrics(self, market_data: MarketData, 
                              btc_data: Optional[MarketData] = None) -> ScanMetrics:
        """Calculate all metrics needed for scanning with optimized NumPy operations."""
        metrics = ScanMetrics()
        
        if market_data.candles_5m and len(market_data.candles_5m) >= 20:
            candles = market_data.candles_5m

            try:
                # Convert to numpy array once for better performance (float32 saves 50% memory)
                volumes = np.array([c.volume for c in candles], dtype=np.float32)

                # Optimized volume surge calculations using vectorized operations
                if len(volumes) >= 24:
                    # 1h volume surge (last 12 candles vs previous 12)
                    recent_vol = np.median(volumes[-12:])  # Use median for robustness to outliers
                    older_vol = np.median(volumes[-24:-12])  # Use median for robustness to outliers
                    if older_vol > 0:
                        metrics.vol_surge_1h = float(recent_vol / older_vol)

                if len(volumes) >= 21:
                    # 5m volume surge (last candle vs median of previous 20)
                    current_vol = volumes[-1]
                    median_vol = np.median(volumes[-21:-1])
                    if median_vol > 0:
                        metrics.vol_surge_5m = float(current_vol / median_vol)

                # ATR quality metric with optimized calculation
            except Exception as e:
                logger.error(f"Error calculating volume metrics: {e}")
                atr_values = atr(candles, period=14)
                if len(atr_values) and not np.isnan(atr_values[-1]) and market_data.price:
                    atr_ratio = atr_values[-1] / market_data.price
                    metrics.atr_quality = self._calculate_atr_quality(atr_ratio)

            except Exception as exc:
                logger.debug(
                    "Failed to calculate scan metrics for %s: %s",
                    market_data.symbol,
                    exc,
                )

        # OI delta (from market data)
        if market_data.oi_change_24h is not None:
            metrics.oi_delta_24h = market_data.oi_change_24h

        # Other metrics from market data
        metrics.bb_width_pct = market_data.bb_width_pct
        metrics.btc_correlation = market_data.btc_correlation
        metrics.trades_per_minute = market_data.trades_per_minute
        metrics.liquidity_score = market_data.liquidity_score
        
        return metrics

    def _check_data_health(self, market_data: MarketData) -> FilterResult:
        """Perform lightweight data quality checks for diagnostics."""
        issues = []

        candles = market_data.candles_5m or []
        if not candles:
            issues.append("no_candles")
        else:
            sorted_ts = sorted(c.ts for c in candles)
            expected_interval = 5 * 60 * 1000
            gap_count = 0
            duplicate_count = 0
            for prev, cur in zip(sorted_ts[:-1], sorted_ts[1:]):
                delta = cur - prev
                if delta == 0:
                    duplicate_count += 1
                elif delta > expected_interval * 1.2:
                    gap_count += 1
            if gap_count:
                issues.append(f"gaps:{gap_count}")
            if duplicate_count:
                issues.append(f"duplicates:{duplicate_count}")

        depth = market_data.l2_depth
        if not depth:
            issues.append("no_depth")
        else:
            if depth.spread_bps > max(self.preset.liquidity_filters.max_spread_bps * 2, 20):
                issues.append("wide_spread")
            if depth.total_depth_usd_0_3pct <= 0 and depth.total_depth_usd_0_5pct <= 0:
                issues.append("zero_depth")

        if market_data.trades_per_minute <= 0:
            issues.append("no_trades")

        passed = not issues
        reason = "ok" if passed else ";".join(issues)
        return FilterResult(
            passed=passed,
            value=len(issues),
            threshold=0,
            reason=reason
        )
    
    def _calculate_atr_quality(self, atr_ratio: float) -> float:
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
