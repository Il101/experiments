"""
EntryValidator: Multi-factor entry confirmation and validation.

This component validates entry signals by checking multiple factors:
- Volume confirmation (sufficient volume)
- Density zone avoidance (avoid entering in congestion)
- Momentum confirmation (strong impulse)
- Market quality (not flat/consolidating)
- Breakout quality (clean break vs false break)

All validation rules are config-driven via EntryRulesConfig.
"""

from enum import Enum
from decimal import Decimal
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
import logging

from ..config.settings import EntryRulesConfig, MarketQualityConfig

logger = logging.getLogger(__name__)


class ValidationResult(Enum):
    """Result of validation check."""
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"  # Rule disabled


class ValidationPriority(Enum):
    """Priority of validation rules."""
    CRITICAL = "critical"  # Must pass
    HIGH = "high"  # Should pass
    MEDIUM = "medium"  # Nice to pass
    LOW = "low"  # Optional


@dataclass
class ValidationCheck:
    """Single validation check result."""
    rule_name: str
    result: ValidationResult
    priority: ValidationPriority
    score: Decimal  # 0.0 - 1.0
    reason: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EntrySignal:
    """Entry signal with market data."""
    # Price data
    breakout_price: Decimal
    current_price: Decimal
    entry_price: Decimal  # Proposed entry price
    stop_loss: Decimal
    
    # Volume data
    breakout_volume: Decimal
    avg_volume: Decimal  # Average volume over lookback period
    current_volume: Decimal
    
    # Momentum data
    price_change_pct: Decimal  # % change from breakout
    bars_since_breakout: int
    
    # Density/SR data
    density_zones: List[tuple[Decimal, Decimal]] = field(default_factory=list)  # [(low, high), ...]
    sr_levels: List[Decimal] = field(default_factory=list)  # [level1, level2, ...]
    
    # Market quality
    is_flat: bool = False
    is_consolidating: bool = False
    noise_level: Decimal = Decimal("0")  # 0.0 - 1.0
    
    # Direction
    is_long: bool = True


@dataclass
class ValidationReport:
    """Complete validation report."""
    is_valid: bool
    confidence: Decimal  # 0.0 - 1.0
    checks: List[ValidationCheck]
    failed_critical: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    def get_check(self, rule_name: str) -> Optional[ValidationCheck]:
        """Get specific check by name."""
        for check in self.checks:
            if check.rule_name == rule_name:
                return check
        return None
    
    def get_failed_checks(self) -> List[ValidationCheck]:
        """Get all failed checks."""
        return [c for c in self.checks if c.result == ValidationResult.FAILED]
    
    def get_passed_checks(self) -> List[ValidationCheck]:
        """Get all passed checks."""
        return [c for c in self.checks if c.result == ValidationResult.PASSED]


class EntryValidator:
    """
    Multi-factor entry validation component.
    
    Validates entry signals by checking:
    1. Volume confirmation - sufficient volume on breakout
    2. Density avoidance - not entering in congestion zone
    3. Momentum confirmation - strong price movement
    4. Market quality - good market conditions
    5. Breakout quality - clean break vs false break
    
    All behavior controlled by EntryRulesConfig and MarketQualityConfig.
    """
    
    def __init__(
        self,
        entry_config: EntryRulesConfig,
        market_config: Optional[MarketQualityConfig] = None,
    ):
        """
        Initialize entry validator.
        
        Args:
            entry_config: Entry rules configuration
            market_config: Market quality configuration (optional)
        """
        self.entry_config = entry_config
        self.market_config = market_config
        
        logger.info("EntryValidator initialized")
    
    def validate(self, signal: EntrySignal) -> ValidationReport:
        """
        Validate entry signal.
        
        Args:
            signal: Entry signal to validate
        
        Returns:
            ValidationReport with validation results
        """
        checks: List[ValidationCheck] = []
        
        # Run all validation checks
        checks.append(self._check_volume_confirmation(signal))
        checks.append(self._check_density_avoidance(signal))
        checks.append(self._check_momentum_confirmation(signal))
        checks.append(self._check_market_quality(signal))
        checks.append(self._check_breakout_quality(signal))
        
        # Analyze results
        failed_critical = []
        warnings = []
        total_score = Decimal("0")
        enabled_checks = 0
        
        for check in checks:
            if check.result == ValidationResult.SKIPPED:
                continue
            
            enabled_checks += 1
            
            if check.result == ValidationResult.FAILED:
                if check.priority == ValidationPriority.CRITICAL:
                    failed_critical.append(check.rule_name)
                elif check.priority in (ValidationPriority.HIGH, ValidationPriority.MEDIUM):
                    warnings.append(f"{check.rule_name}: {check.reason}")
            
            # Add to total score (failed = 0, passed = check.score)
            if check.result == ValidationResult.PASSED:
                total_score += check.score
        
        # Calculate confidence (average score of enabled checks)
        confidence = total_score / Decimal(str(enabled_checks)) if enabled_checks > 0 else Decimal("0")
        
        # Determine if valid (no critical failures)
        is_valid = len(failed_critical) == 0
        
        return ValidationReport(
            is_valid=is_valid,
            confidence=confidence,
            checks=checks,
            failed_critical=failed_critical,
            warnings=warnings,
        )
    
    def _check_volume_confirmation(self, signal: EntrySignal) -> ValidationCheck:
        """Check if volume confirms the breakout."""
        if not self.entry_config.require_volume_confirmation:
            return ValidationCheck(
                rule_name="volume_confirmation",
                result=ValidationResult.SKIPPED,
                priority=ValidationPriority.HIGH,
                score=Decimal("0"),
                reason="Volume confirmation disabled",
            )
        
        # Calculate volume ratio
        volume_ratio = signal.breakout_volume / signal.avg_volume if signal.avg_volume > 0 else Decimal("0")
        min_ratio = Decimal(str(self.entry_config.volume_confirmation_multiplier))
        
        # Check if volume is sufficient
        if volume_ratio >= min_ratio:
            # Score based on how much volume exceeds minimum
            excess = volume_ratio - min_ratio
            score = min(Decimal("1.0"), Decimal("0.7") + (excess / min_ratio) * Decimal("0.3"))
            
            return ValidationCheck(
                rule_name="volume_confirmation",
                result=ValidationResult.PASSED,
                priority=ValidationPriority.HIGH,
                score=score,
                reason=f"Volume confirmed: {volume_ratio:.2f}x average (required: {min_ratio}x)",
                metadata={
                    "volume_ratio": float(volume_ratio),
                    "min_ratio": float(min_ratio),
                    "breakout_volume": float(signal.breakout_volume),
                    "avg_volume": float(signal.avg_volume),
                }
            )
        else:
            return ValidationCheck(
                rule_name="volume_confirmation",
                result=ValidationResult.FAILED,
                priority=ValidationPriority.HIGH,
                score=Decimal("0"),
                reason=f"Insufficient volume: {volume_ratio:.2f}x (required: {min_ratio}x)",
                metadata={
                    "volume_ratio": float(volume_ratio),
                    "min_ratio": float(min_ratio),
                }
            )
    
    def _check_density_avoidance(self, signal: EntrySignal) -> ValidationCheck:
        """Check if entry avoids density zones."""
        # Note: require_density_confirmation means we want to CHECK density
        # For now, we'll interpret this as "avoid entering in density zones"
        if not self.entry_config.require_density_confirmation:
            return ValidationCheck(
                rule_name="density_avoidance",
                result=ValidationResult.SKIPPED,
                priority=ValidationPriority.MEDIUM,
                score=Decimal("0"),
                reason="Density check disabled",
            )
        
        # Check if entry price is in any density zone
        in_density_zone = False
        closest_zone = None
        min_distance = None
        
        for zone_low, zone_high in signal.density_zones:
            if zone_low <= signal.entry_price <= zone_high:
                in_density_zone = True
                closest_zone = (zone_low, zone_high)
                min_distance = Decimal("0")
                break
            
            # Calculate distance to zone
            if signal.entry_price < zone_low:
                distance = zone_low - signal.entry_price
            else:
                distance = signal.entry_price - zone_high
            
            if min_distance is None or distance < min_distance:
                min_distance = distance
                closest_zone = (zone_low, zone_high)
        
        if in_density_zone:
            return ValidationCheck(
                rule_name="density_avoidance",
                result=ValidationResult.FAILED,
                priority=ValidationPriority.MEDIUM,
                score=Decimal("0"),
                reason=f"Entry price in density zone: {closest_zone}",
                metadata={
                    "entry_price": float(signal.entry_price),
                    "density_zone": [float(closest_zone[0]), float(closest_zone[1])] if closest_zone else None,
                }
            )
        else:
            # Score based on distance from nearest zone
            if min_distance is None:
                score = Decimal("1.0")
                reason = "No density zones nearby"
            else:
                # Score higher if farther from zones
                distance_pct = (min_distance / signal.entry_price) * Decimal("100")
                score = min(Decimal("1.0"), Decimal("0.6") + distance_pct / Decimal("10"))
                reason = f"Clear of density zones (distance: {distance_pct:.1f}%)"
            
            return ValidationCheck(
                rule_name="density_avoidance",
                result=ValidationResult.PASSED,
                priority=ValidationPriority.MEDIUM,
                score=score,
                reason=reason,
                metadata={
                    "entry_price": float(signal.entry_price),
                    "min_distance": float(min_distance) if min_distance else None,
                }
            )
    
    def _check_momentum_confirmation(self, signal: EntrySignal) -> ValidationCheck:
        """Check if momentum confirms the breakout."""
        if not self.entry_config.require_momentum:
            return ValidationCheck(
                rule_name="momentum_confirmation",
                result=ValidationResult.SKIPPED,
                priority=ValidationPriority.HIGH,
                score=Decimal("0"),
                reason="Momentum confirmation disabled",
            )
        
        min_momentum = Decimal(str(self.entry_config.momentum_min_slope_pct))
        actual_momentum = abs(signal.price_change_pct)
        
        if actual_momentum >= min_momentum:
            # Score based on momentum strength
            excess = actual_momentum - min_momentum
            score = min(Decimal("1.0"), Decimal("0.7") + (excess / min_momentum) * Decimal("0.3"))
            
            return ValidationCheck(
                rule_name="momentum_confirmation",
                result=ValidationResult.PASSED,
                priority=ValidationPriority.HIGH,
                score=score,
                reason=f"Strong momentum: {actual_momentum:.2f}% (required: {min_momentum}%)",
                metadata={
                    "momentum_pct": float(actual_momentum),
                    "momentum_min_slope_pct": float(min_momentum),
                    "bars_since_breakout": signal.bars_since_breakout,
                }
            )
        else:
            return ValidationCheck(
                rule_name="momentum_confirmation",
                result=ValidationResult.FAILED,
                priority=ValidationPriority.HIGH,
                score=Decimal("0"),
                reason=f"Weak momentum: {actual_momentum:.2f}% (required: {min_momentum}%)",
                metadata={
                    "momentum_pct": float(actual_momentum),
                    "momentum_min_slope_pct": float(min_momentum),
                }
            )
    
    def _check_market_quality(self, signal: EntrySignal) -> ValidationCheck:
        """Check overall market quality."""
        if self.market_config is None:
            return ValidationCheck(
                rule_name="market_quality",
                result=ValidationResult.SKIPPED,
                priority=ValidationPriority.MEDIUM,
                score=Decimal("0"),
                reason="Market quality check disabled",
            )
        
        issues = []
        
        # Check if market is flat (filter_enabled means we REJECT flat)
        if signal.is_flat and self.market_config.flat_market_filter_enabled:
            issues.append("market is flat")
        
        # Check if market is consolidating (filter_enabled means we REJECT consolidation)
        if signal.is_consolidating and self.market_config.consolidation_filter_enabled:
            issues.append("market is consolidating")
        
        # Check noise level
        if self.market_config.noise_filter_enabled:
            noise_threshold = Decimal(str(self.market_config.noise_threshold))
            if signal.noise_level > noise_threshold:
                issues.append(f"high noise ({signal.noise_level:.2f} > {noise_threshold})")
        
        if issues:
            return ValidationCheck(
                rule_name="market_quality",
                result=ValidationResult.FAILED,
                priority=ValidationPriority.MEDIUM,
                score=Decimal("0"),
                reason=f"Poor market quality: {', '.join(issues)}",
                metadata={
                    "is_flat": signal.is_flat,
                    "is_consolidating": signal.is_consolidating,
                    "noise_level": float(signal.noise_level),
                }
            )
        else:
            # Score based on noise level (lower is better)
            if self.market_config.noise_filter_enabled:
                noise_threshold = Decimal(str(self.market_config.noise_threshold))
                noise_score = Decimal("1.0") - (signal.noise_level / noise_threshold)
                score = max(Decimal("0.5"), noise_score)
            else:
                score = Decimal("1.0")
            
            return ValidationCheck(
                rule_name="market_quality",
                result=ValidationResult.PASSED,
                priority=ValidationPriority.MEDIUM,
                score=score,
                reason="Good market quality",
                metadata={
                    "is_flat": signal.is_flat,
                    "is_consolidating": signal.is_consolidating,
                    "noise_level": float(signal.noise_level),
                }
            )
    
    def _check_breakout_quality(self, signal: EntrySignal) -> ValidationCheck:
        """Check breakout quality (clean vs false break)."""
        # Calculate breakout distance
        if signal.is_long:
            breakout_distance = signal.current_price - signal.breakout_price
        else:
            breakout_distance = signal.breakout_price - signal.current_price
        
        # Check if price pulled back too much
        risk = abs(signal.entry_price - signal.stop_loss)
        pullback_pct = (breakout_distance / risk) * Decimal("100") if risk > 0 else Decimal("0")
        
        # Check minimum distance
        min_distance_bps = Decimal(str(self.entry_config.max_distance_from_level_bps))
        distance_bps = (breakout_distance / signal.breakout_price) * Decimal("10000")
        
        issues = []
        
        if distance_bps < min_distance_bps:
            issues.append(f"insufficient distance ({distance_bps:.0f} bps < {min_distance_bps} bps)")
        
        # Check if too many bars since breakout
        max_bars = self.entry_config.false_start_lookback_bars
        if signal.bars_since_breakout > max_bars:
            issues.append(f"too late ({signal.bars_since_breakout} bars > {max_bars})")
        
        if issues:
            return ValidationCheck(
                rule_name="breakout_quality",
                result=ValidationResult.FAILED,
                priority=ValidationPriority.CRITICAL,
                score=Decimal("0"),
                reason=f"Poor breakout quality: {', '.join(issues)}",
                metadata={
                    "breakout_distance_bps": float(distance_bps),
                    "bars_since_breakout": signal.bars_since_breakout,
                    "pullback_pct": float(pullback_pct),
                }
            )
        else:
            # Score based on breakout strength
            distance_score = min(Decimal("1.0"), distance_bps / (min_distance_bps * Decimal("2")))
            timing_score = Decimal("1.0") - (Decimal(str(signal.bars_since_breakout)) / Decimal(str(max_bars)))
            score = (distance_score + timing_score) / Decimal("2")
            
            return ValidationCheck(
                rule_name="breakout_quality",
                result=ValidationResult.PASSED,
                priority=ValidationPriority.CRITICAL,
                score=score,
                reason=f"Clean breakout: {distance_bps:.0f} bps, {signal.bars_since_breakout} bars",
                metadata={
                    "breakout_distance_bps": float(distance_bps),
                    "bars_since_breakout": signal.bars_since_breakout,
                }
            )
