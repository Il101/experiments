"""
MarketQualityFilter: Pre-entry market condition filtering.

This component filters out poor market conditions before entry:
- Flat market detection (low volatility)
- Consolidation detection (ranging)
- Volatility spike detection (unstable)
- Trend quality assessment
- Market noise filtering

All filtering rules are config-driven via MarketQualityConfig.
"""

from enum import Enum
from decimal import Decimal
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
import logging

from ..config.settings import MarketQualityConfig

logger = logging.getLogger(__name__)


class MarketCondition(Enum):
    """Market condition classification."""
    TRENDING = "trending"
    CONSOLIDATING = "consolidating"
    FLAT = "flat"
    VOLATILE = "volatile"
    NOISY = "noisy"
    ACCEPTABLE = "acceptable"


@dataclass
class MarketMetrics:
    """Market quality metrics."""
    # Volatility
    atr: Decimal  # Average True Range
    atr_pct: Decimal  # ATR as % of price
    volatility_spike: bool = False
    
    # Price range
    price_range_pct: Decimal = Decimal("0")  # High-low range %
    consolidation_bars: int = 0
    
    # Trend
    trend_slope_pct: Decimal = Decimal("0")  # Trend slope % per bar
    trend_strength: Decimal = Decimal("0")  # 0.0 - 1.0
    
    # Noise
    noise_level: Decimal = Decimal("0")  # 0.0 - 1.0
    
    # Current price
    current_price: Decimal = Decimal("0")


@dataclass
class FilterResult:
    """Result of market quality filtering."""
    passed: bool
    condition: MarketCondition
    score: Decimal  # 0.0 - 1.0, higher is better
    reason: str
    metrics: MarketMetrics
    warnings: List[str] = field(default_factory=list)
    
    def is_acceptable(self) -> bool:
        """Check if market condition is acceptable for trading."""
        return self.passed


class MarketQualityFilter:
    """
    Market quality filter for pre-entry conditions.
    
    Filters based on:
    1. Flat market detection - reject low volatility
    2. Consolidation detection - reject ranging markets
    3. Volatility spikes - reject unstable conditions
    4. Trend quality - require clear trends (optional)
    5. Market noise - reject noisy/choppy conditions
    
    All behavior controlled by MarketQualityConfig.
    """
    
    def __init__(self, config: MarketQualityConfig):
        """
        Initialize market quality filter.
        
        Args:
            config: Market quality configuration
        """
        self.config = config
        logger.info("MarketQualityFilter initialized")
    
    def filter(self, metrics: MarketMetrics) -> FilterResult:
        """
        Filter market based on quality metrics.
        
        Args:
            metrics: Current market metrics
        
        Returns:
            FilterResult with pass/fail and classification
        """
        warnings = []
        issues = []
        
        # Check flat market
        is_flat = self._check_flat_market(metrics)
        if is_flat and self.config.flat_market_filter_enabled:
            issues.append("market is flat")
        
        # Check consolidation
        is_consolidating = self._check_consolidation(metrics)
        if is_consolidating and self.config.consolidation_filter_enabled:
            issues.append("market is consolidating")
        
        # Check volatility spike
        if metrics.volatility_spike and self.config.require_stable_volatility:
            issues.append("volatility spike detected")
        
        # Check trend quality
        trend_weak = self._check_weak_trend(metrics)
        if trend_weak and self.config.require_clear_trend:
            issues.append("trend is weak or unclear")
        
        # Check noise level
        noise_high = self._check_high_noise(metrics)
        if noise_high and self.config.noise_filter_enabled:
            issues.append("high market noise")
        
        # Determine condition
        condition = self._classify_condition(metrics, is_flat, is_consolidating, noise_high)
        
        # Calculate quality score
        score = self._calculate_quality_score(metrics, is_flat, is_consolidating, trend_weak, noise_high)
        
        # Determine if passed
        passed = len(issues) == 0
        
        # Build reason
        if passed:
            reason = f"Market quality acceptable ({condition.value})"
            # Add warnings for borderline cases
            if score < Decimal("0.7"):
                warnings.append("Market quality is marginal")
        else:
            reason = f"Market quality poor: {', '.join(issues)}"
        
        return FilterResult(
            passed=passed,
            condition=condition,
            score=score,
            reason=reason,
            metrics=metrics,
            warnings=warnings,
        )
    
    def _check_flat_market(self, metrics: MarketMetrics) -> bool:
        """Check if market is flat (low volatility)."""
        if not self.config.flat_market_filter_enabled:
            return False
        
        threshold = Decimal(str(self.config.flat_market_atr_threshold))
        return metrics.atr_pct < threshold
    
    def _check_consolidation(self, metrics: MarketMetrics) -> bool:
        """Check if market is consolidating (ranging)."""
        if not self.config.consolidation_filter_enabled:
            return False
        
        # Check if price range is small
        threshold = Decimal(str(self.config.consolidation_range_threshold_pct))
        if metrics.price_range_pct > threshold:
            return False
        
        # Check if enough bars in consolidation
        min_bars = self.config.consolidation_min_bars
        return metrics.consolidation_bars >= min_bars
    
    def _check_weak_trend(self, metrics: MarketMetrics) -> bool:
        """Check if trend is weak or unclear."""
        if not self.config.require_clear_trend:
            return False
        
        min_slope = Decimal(str(self.config.trend_slope_min_pct))
        return abs(metrics.trend_slope_pct) < min_slope
    
    def _check_high_noise(self, metrics: MarketMetrics) -> bool:
        """Check if market noise is high."""
        if not self.config.noise_filter_enabled:
            return False
        
        threshold = Decimal(str(self.config.noise_threshold))
        return metrics.noise_level > threshold
    
    def _classify_condition(
        self,
        metrics: MarketMetrics,
        is_flat: bool,
        is_consolidating: bool,
        noise_high: bool,
    ) -> MarketCondition:
        """Classify current market condition."""
        if is_flat:
            return MarketCondition.FLAT
        
        if is_consolidating:
            return MarketCondition.CONSOLIDATING
        
        if metrics.volatility_spike:
            return MarketCondition.VOLATILE
        
        if noise_high:
            return MarketCondition.NOISY
        
        # Check if trending
        min_slope = Decimal(str(self.config.trend_slope_min_pct)) if self.config.require_clear_trend else Decimal("0.1")
        if abs(metrics.trend_slope_pct) >= min_slope:
            return MarketCondition.TRENDING
        
        return MarketCondition.ACCEPTABLE
    
    def _calculate_quality_score(
        self,
        metrics: MarketMetrics,
        is_flat: bool,
        is_consolidating: bool,
        trend_weak: bool,
        noise_high: bool,
    ) -> Decimal:
        """
        Calculate overall market quality score.
        
        Returns:
            Score from 0.0 (poor) to 1.0 (excellent)
        """
        scores = []
        
        # Volatility score (0.0 = flat, 1.0 = good volatility)
        if self.config.flat_market_filter_enabled:
            threshold = Decimal(str(self.config.flat_market_atr_threshold))
            if metrics.atr_pct >= threshold * Decimal("2"):
                vol_score = Decimal("1.0")
            elif metrics.atr_pct >= threshold:
                vol_score = (metrics.atr_pct - threshold) / threshold
            else:
                vol_score = metrics.atr_pct / threshold
            scores.append(vol_score)
        
        # Consolidation score (1.0 = not consolidating, 0.0 = tight consolidation)
        if self.config.consolidation_filter_enabled:
            threshold = Decimal(str(self.config.consolidation_range_threshold_pct))
            if metrics.price_range_pct >= threshold * Decimal("2"):
                cons_score = Decimal("1.0")
            elif metrics.price_range_pct >= threshold:
                cons_score = Decimal("0.7")
            else:
                cons_score = metrics.price_range_pct / threshold
            scores.append(cons_score)
        
        # Volatility stability score (1.0 = stable, 0.0 = spike)
        if self.config.require_stable_volatility:
            stability_score = Decimal("0.3") if metrics.volatility_spike else Decimal("1.0")
            scores.append(stability_score)
        
        # Trend score (1.0 = strong trend, 0.0 = no trend)
        if self.config.require_clear_trend:
            min_slope = Decimal(str(self.config.trend_slope_min_pct))
            if abs(metrics.trend_slope_pct) >= min_slope * Decimal("2"):
                trend_score = Decimal("1.0")
            elif abs(metrics.trend_slope_pct) >= min_slope:
                trend_score = Decimal("0.7")
            else:
                trend_score = abs(metrics.trend_slope_pct) / min_slope
            scores.append(trend_score)
        
        # Noise score (1.0 = low noise, 0.0 = high noise)
        if self.config.noise_filter_enabled:
            threshold = Decimal(str(self.config.noise_threshold))
            if metrics.noise_level <= threshold / Decimal("2"):
                noise_score = Decimal("1.0")
            elif metrics.noise_level <= threshold:
                noise_score = Decimal("1.0") - (metrics.noise_level / threshold)
            else:
                noise_score = max(Decimal("0"), Decimal("1.0") - (metrics.noise_level / threshold))
            scores.append(noise_score)
        
        # Calculate average score
        if scores:
            return sum(scores) / Decimal(str(len(scores)))
        else:
            return Decimal("1.0")  # No filters enabled, pass by default
    
    def get_acceptable_conditions(self) -> List[MarketCondition]:
        """Get list of acceptable market conditions based on config."""
        acceptable = [MarketCondition.ACCEPTABLE, MarketCondition.TRENDING]
        
        # Add conditions that are not filtered
        if not self.config.flat_market_filter_enabled:
            acceptable.append(MarketCondition.FLAT)
        
        if not self.config.consolidation_filter_enabled:
            acceptable.append(MarketCondition.CONSOLIDATING)
        
        if not self.config.require_stable_volatility:
            acceptable.append(MarketCondition.VOLATILE)
        
        if not self.config.noise_filter_enabled:
            acceptable.append(MarketCondition.NOISY)
        
        return acceptable
    
    def should_enter(self, metrics: MarketMetrics) -> tuple[bool, str]:
        """
        Quick check if entry should be allowed.
        
        Args:
            metrics: Market metrics
        
        Returns:
            Tuple of (should_enter, reason)
        """
        result = self.filter(metrics)
        return result.passed, result.reason
