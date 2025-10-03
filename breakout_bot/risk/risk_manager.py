"""
Risk management system for Breakout Bot Trading System.

This module implements R-based position sizing, risk controls, and portfolio
risk management with kill-switch mechanisms.
"""

import math
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
from dataclasses import dataclass
import logging

from ..data.models import Signal, Position, Order, MarketData, L2Depth
from ..config.settings import TradingPreset, RiskConfig
from ..utils.safe_math import safe_divide, validate_positive, safe_percentage

logger = logging.getLogger(__name__)


@dataclass
class RiskMetrics:
    """Risk metrics for portfolio monitoring."""
    total_equity: float
    used_equity: float
    available_equity: float
    total_risk_usd: float
    daily_pnl: float
    daily_risk_used: float
    max_drawdown: float
    open_positions_count: int
    correlation_exposure: Dict[str, float]


@dataclass
class PositionSize:
    """Position sizing calculation result."""
    quantity: float
    notional_usd: float
    risk_usd: float
    risk_r: float
    stop_distance: float
    is_valid: bool
    reason: str
    precision_adjusted: bool = False


class PositionSizer:
    """R-based position sizing calculator."""
    
    def __init__(self, risk_config: RiskConfig):
        self.config = risk_config
        
    def calculate_position_size(self,
                              signal: Signal,
                              account_equity: float,
                              current_price: float,
                              market_data: MarketData) -> PositionSize:
        """
        Calculate position size using R-model.
        
        Args:
            signal: Trading signal with entry and stop loss
            account_equity: Current account equity
            current_price: Current market price
            market_data: Market data for precision and depth checks
        
        Returns:
            PositionSize object with calculation results
        """
        
        # ✅ CRITICAL: Validate input parameters
        if not signal or not market_data:
            return PositionSize(
                quantity=0, notional_usd=0, risk_usd=0, risk_r=0, stop_distance=0,
                is_valid=False, reason="Missing signal or market data"
            )
        
        # Validate numeric inputs
        account_equity = validate_positive(account_equity, "account_equity", 10000.0)
        signal_entry = validate_positive(signal.entry, "signal.entry", current_price or 1.0)
        signal_sl = validate_positive(signal.sl, "signal.sl", signal_entry * 0.99)  # Default 1% SL
        
        if signal_entry == 0:
            return PositionSize(
                quantity=0, notional_usd=0, risk_usd=0, risk_r=0, stop_distance=0,
                is_valid=False, reason="Invalid signal entry price (zero)"
            )
        
        # Calculate R dollar amount
        r_dollar = account_equity * self.config.risk_per_trade
        
        # Calculate stop distance using validated values
        if signal.side == 'long':
            stop_distance = abs(signal_entry - signal_sl)
        else:  # short
            stop_distance = abs(signal_sl - signal_entry)
        
        if stop_distance <= 0:
            return PositionSize(
                quantity=0,
                notional_usd=0,
                risk_usd=0,
                risk_r=0,
                stop_distance=0,
                is_valid=False,
                reason="Invalid stop distance"
            )
        
        # Calculate raw position quantity
        raw_quantity = r_dollar / stop_distance
        
        # Apply maximum position size constraint
        max_notional = self.config.max_position_size_usd or float('inf')
        max_quantity_by_size = safe_divide(max_notional, signal_entry, float('inf'), log_warning=False)
        
        if raw_quantity > max_quantity_by_size:
            raw_quantity = max_quantity_by_size
            logger.warning(f"Position size limited by max USD constraint: ${max_notional:,.0f}")
        
        # Check depth constraints (create temporary signal with validated entry)
        validated_signal = signal
        validated_signal.entry = signal_entry
        depth_adjusted_qty = self._check_depth_constraints(raw_quantity, validated_signal, market_data)
        
        # Apply precision rounding
        precision_adjusted_qty = self._apply_precision_rounding(depth_adjusted_qty, market_data)
        
        # Final calculations
        final_notional = precision_adjusted_qty * signal_entry
        final_risk_usd = precision_adjusted_qty * stop_distance
        final_risk_r = safe_divide(final_risk_usd, r_dollar, 0.0, log_warning=False)
        
        # Validation
        is_valid, reason = self._validate_position_size(
            precision_adjusted_qty, final_notional, final_risk_usd, 
            account_equity, market_data
        )
        
        return PositionSize(
            quantity=precision_adjusted_qty,
            notional_usd=final_notional,
            risk_usd=final_risk_usd,
            risk_r=final_risk_r,
            stop_distance=stop_distance,
            is_valid=is_valid,
            reason=reason,
            precision_adjusted=(precision_adjusted_qty != raw_quantity)
        )
    
    def _check_depth_constraints(self, 
                               quantity: float, 
                               signal: Signal, 
                               market_data: MarketData) -> float:
        """Adjust quantity based on order book depth."""
        if not market_data.l2_depth:
            return quantity
        
        l2 = market_data.l2_depth
        
        # Calculate order size in USD
        order_usd = quantity * signal.entry
        
        # Check available depth at different levels
        if signal.side == 'long':
            # For long positions, check ask side depth
            if order_usd > l2.ask_usd_0_3pct:
                # Limit to available depth at 0.3%
                adjusted_qty = (l2.ask_usd_0_3pct * 0.8) / signal.entry  # 80% of available depth
                logger.warning(f"Position size limited by depth: {quantity:.6f} -> {adjusted_qty:.6f}")
                return adjusted_qty
        else:
            # For short positions, check bid side depth
            if order_usd > l2.bid_usd_0_3pct:
                adjusted_qty = (l2.bid_usd_0_3pct * 0.8) / signal.entry
                logger.warning(f"Position size limited by depth: {quantity:.6f} -> {adjusted_qty:.6f}")
                return adjusted_qty
        
        return quantity
    
    def _apply_precision_rounding(self, quantity: float, market_data: MarketData) -> float:
        """Apply exchange precision rounding."""
        # This is a simplified implementation
        # In practice, would need actual exchange precision rules
        
        # Round to 6 decimal places for most crypto pairs
        precision = 6
        
        # Adjust precision based on price level
        if market_data.price > 1000:
            precision = 4
        elif market_data.price > 100:
            precision = 5
        elif market_data.price < 0.001:
            precision = 8
        
        rounded_qty = round(quantity, precision)
        
        # Ensure minimum notional value (e.g., $10)
        min_notional = 10.0
        if rounded_qty * market_data.price < min_notional:
            return 0  # Position too small
        
        return rounded_qty
    
    def _validate_position_size(self,
                              quantity: float,
                              notional_usd: float,
                              risk_usd: float,
                              account_equity: float,
                              market_data: MarketData) -> Tuple[bool, str]:
        """Validate final position size."""
        
        if quantity <= 0:
            return False, "Zero or negative quantity"
        
        if notional_usd <= 0:
            return False, "Zero or negative notional value"
        
        # Check minimum notional
        min_notional = 10.0  # $10 minimum
        if notional_usd < min_notional:
            return False, f"Below minimum notional: ${notional_usd:.2f} < ${min_notional}"
        
        # Check maximum position size
        if (self.config.max_position_size_usd and 
            notional_usd > self.config.max_position_size_usd):
            return False, f"Exceeds max position size: ${notional_usd:.0f}"
        
        # Check risk percentage
        risk_pct = risk_usd / account_equity
        if risk_pct > self.config.risk_per_trade * 1.1:  # 10% tolerance
            return False, f"Risk too high: {risk_pct:.3f} > {self.config.risk_per_trade:.3f}"
        
        return True, "Valid position size"


class RiskMonitor:
    """Portfolio risk monitoring and control."""
    
    def __init__(self, risk_config: RiskConfig):
        self.config = risk_config
        self.daily_start_equity: Optional[float] = None
        self.daily_start_time: Optional[datetime] = None
        self.portfolio_high_water_mark: float = 0.0
        
    def check_risk_limits(self,
                         positions: List[Position],
                         account_equity: float,
                         btc_prices: Optional[Dict[str, float]] = None) -> Dict[str, Any]:
        """
        Check all risk limits and return status.
        
        Returns:
            Dict with risk status and any limit breaches
        """
        risk_status = {
            'overall_status': 'SAFE',
            'warnings': [],
            'violations': [],
            'kill_switch_triggered': False,
            'metrics': None
        }
        
        # Calculate risk metrics
        metrics = self._calculate_risk_metrics(positions, account_equity)
        risk_status['metrics'] = metrics
        
        # Check daily risk limit
        daily_violation = self._check_daily_risk_limit(metrics)
        if daily_violation:
            risk_status['violations'].append(daily_violation)
            risk_status['overall_status'] = 'RISK_LIMIT_BREACH'
        
        # Check maximum concurrent positions
        if metrics.open_positions_count > self.config.max_concurrent_positions:
            violation = f"Too many positions: {metrics.open_positions_count} > {self.config.max_concurrent_positions}"
            risk_status['violations'].append(violation)
            risk_status['overall_status'] = 'POSITION_LIMIT_BREACH'
        
        # Check correlation exposure
        if btc_prices:
            correlation_warnings = self._check_correlation_exposure(positions, btc_prices)
            risk_status['warnings'].extend(correlation_warnings)
        
        # Check kill switch conditions
        kill_switch = self._check_kill_switch(metrics)
        if kill_switch:
            risk_status['kill_switch_triggered'] = True
            risk_status['overall_status'] = 'KILL_SWITCH'
            risk_status['violations'].append(kill_switch)
        
        # Check portfolio drawdown
        drawdown_warning = self._check_drawdown(metrics)
        if drawdown_warning:
            risk_status['warnings'].append(drawdown_warning)
        
        return risk_status
    
    def _calculate_risk_metrics(self, positions: List[Position], account_equity: float) -> RiskMetrics:
        """Calculate current portfolio risk metrics."""
        
        # Initialize daily tracking if needed (always reset in paper mode)
        current_date = datetime.now().date()
        if (self.daily_start_time is None or 
            self.daily_start_time.date() != current_date or
            self.daily_start_equity is None or
            account_equity > self.daily_start_equity):  # Reset if equity increased (new session/deposit)
            # Always reset daily start equity to current balance
            self.daily_start_equity = account_equity
            self.daily_start_time = datetime.now()
        elif account_equity < self.daily_start_equity:
            # In paper mode, if equity decreased significantly, reset to avoid false kill switch
            # This handles cases where different equity values are passed between calls
            equity_change_pct = abs(account_equity - self.daily_start_equity) / self.daily_start_equity
            if equity_change_pct > 0.1:  # Reset if equity changed by more than 10%
                self.daily_start_equity = account_equity
                self.daily_start_time = datetime.now()
        
        # Calculate position metrics
        open_positions = [p for p in positions if p.status == 'open']
        total_risk_usd = sum(abs(p.pnl_usd) for p in open_positions if p.pnl_usd < 0)
        used_equity = sum(p.qty * p.entry for p in open_positions)
        
        # Calculate daily P&L (only if we have a valid daily start)
        if self.daily_start_equity and self.daily_start_equity > 0:
            daily_pnl = account_equity - self.daily_start_equity
            daily_risk_used = abs(daily_pnl) / self.daily_start_equity if self.daily_start_equity > 0 else 0
        else:
            # No daily start set, assume no losses
            daily_pnl = 0.0
            daily_risk_used = 0.0
        
        # Initialize high water mark if not set
        if self.portfolio_high_water_mark == 0.0:
            self.portfolio_high_water_mark = account_equity
        
        # Update high water mark (only increase, never decrease)
        if account_equity > self.portfolio_high_water_mark:
            self.portfolio_high_water_mark = account_equity
        
        # Calculate maximum drawdown (only if there are actual losses)
        # Only calculate drawdown if we have actual losses from daily start
        if self.daily_start_equity and self.daily_start_equity > 0 and account_equity < self.daily_start_equity:
            max_drawdown = max(0, (self.daily_start_equity - account_equity) / self.daily_start_equity)
        else:
            # No actual losses, no drawdown
            max_drawdown = 0.0
        
        # Calculate correlation exposure
        correlation_exposure = self._calculate_correlation_exposure(open_positions)
        
        return RiskMetrics(
            total_equity=account_equity,
            used_equity=used_equity,
            available_equity=account_equity - used_equity,
            total_risk_usd=total_risk_usd,
            daily_pnl=daily_pnl,
            daily_risk_used=daily_risk_used,
            max_drawdown=max_drawdown,
            open_positions_count=len(open_positions),
            correlation_exposure=correlation_exposure
        )
    
    def _check_daily_risk_limit(self, metrics: RiskMetrics) -> Optional[str]:
        """Check daily risk limit."""
        if metrics.daily_risk_used > self.config.daily_risk_limit:
            return (f"Daily risk limit exceeded: {metrics.daily_risk_used:.2%} > "
                   f"{self.config.daily_risk_limit:.2%}")
        return None
    
    def _check_kill_switch(self, metrics: RiskMetrics) -> Optional[str]:
        """Check kill switch conditions."""
        # Only trigger kill switch if there are actual losses
        if metrics.daily_pnl < 0:  # Only check if there are actual losses
            # Check max drawdown only if there are losses
            if metrics.max_drawdown > self.config.kill_switch_loss_limit:
                return (f"Kill switch triggered - Max drawdown: {metrics.max_drawdown:.2%} > "
                       f"{self.config.kill_switch_loss_limit:.2%}")
            
            # Additional kill switch: massive daily loss
            extreme_daily_loss = self.config.daily_risk_limit * 3  # 3x daily limit
            if abs(metrics.daily_pnl) / metrics.total_equity > extreme_daily_loss:
                return (f"Kill switch triggered - Extreme daily loss: "
                       f"{abs(metrics.daily_pnl)/metrics.total_equity:.2%}")
        
        return None
    
    def _check_correlation_exposure(self, 
                                  positions: List[Position], 
                                  btc_prices: Dict[str, float]) -> List[str]:
        """Check correlation exposure limits."""
        warnings = []
        
        # Calculate total exposure to correlated assets
        total_equity = sum(p.qty * p.entry for p in positions if p.status == 'open')
        correlated_exposure = 0
        
        for position in positions:
            if position.status != 'open':
                continue
                
            # Get BTC correlation from position metadata
            correlation = position.meta.get('btc_correlation', 0.0)
            
            if abs(correlation) > self.config.correlation_limit:
                position_usd = position.qty * position.entry
                correlated_exposure += position_usd
        
        if total_equity > 0:
            correlation_pct = correlated_exposure / total_equity
            if correlation_pct > 0.5:  # More than 50% in correlated assets
                warnings.append(f"High correlation exposure: {correlation_pct:.1%} of portfolio")
        
        return warnings
    
    def _calculate_correlation_exposure(self, positions: List[Position]) -> Dict[str, float]:
        """Calculate exposure by correlation bucket."""
        exposure = {
            'high_correlation': 0.0,  # |corr| > 0.7
            'medium_correlation': 0.0,  # 0.3 < |corr| <= 0.7
            'low_correlation': 0.0,  # |corr| <= 0.3
        }
        
        for position in positions:
            if position.status != 'open':
                continue
                
            position_usd = position.qty * position.entry
            correlation = abs(position.meta.get('btc_correlation', 0.0))
            
            if correlation > 0.7:
                exposure['high_correlation'] += position_usd
            elif correlation > 0.3:
                exposure['medium_correlation'] += position_usd
            else:
                exposure['low_correlation'] += position_usd
        
        return exposure
    
    def _check_drawdown(self, metrics: RiskMetrics) -> Optional[str]:
        """Check portfolio drawdown warnings."""
        warning_threshold = self.config.kill_switch_loss_limit * 0.6  # 60% of kill switch
        
        if metrics.max_drawdown > warning_threshold:
            return (f"High drawdown warning: {metrics.max_drawdown:.2%} approaching "
                   f"kill switch at {self.config.kill_switch_loss_limit:.2%}")
        
        return None
    
    def should_reduce_risk(self, metrics: RiskMetrics) -> bool:
        """Determine if risk should be reduced."""
        # Reduce risk if approaching daily limit
        if metrics.daily_risk_used > self.config.daily_risk_limit * 0.8:
            return True
        
        # Reduce risk if drawdown is high
        if metrics.max_drawdown > self.config.kill_switch_loss_limit * 0.5:
            return True
        
        # Reduce risk if too many positions
        if metrics.open_positions_count >= self.config.max_concurrent_positions:
            return True
        
        return False


class RiskManager:
    """Main risk management coordinator."""
    
    def __init__(self, preset: TradingPreset):
        self.preset = preset
        self.risk_config = preset.risk
        self.position_sizer = PositionSizer(self.risk_config)
        self.risk_monitor = RiskMonitor(self.risk_config)
        
        logger.info(f"Initialized risk manager with preset: {preset.name}")
        logger.info(f"Risk per trade: {self.risk_config.risk_per_trade:.1%}")
        logger.info(f"Max positions: {self.risk_config.max_concurrent_positions}")
    
    def evaluate_signal_risk(self,
                           signal: Signal,
                           account_equity: float,
                           current_positions: List[Position],
                           market_data: MarketData,
                           btc_prices: Optional[Dict[str, float]] = None) -> Dict[str, Any]:
        """
        Evaluate risk for a new signal and determine if it should be traded.
        
        Returns:
            Dict with risk evaluation results and position sizing
        """
        
        # Check current risk status
        risk_status = self.risk_monitor.check_risk_limits(
            current_positions, account_equity, btc_prices
        )
        
        # If kill switch is triggered, reject all new signals
        if risk_status['kill_switch_triggered']:
            return {
                'approved': False,
                'reason': 'Kill switch triggered',
                'risk_status': risk_status,
                'position_size': None
            }
        
        # If risk limits are breached, reject new signals
        if risk_status['overall_status'] in ['RISK_LIMIT_BREACH', 'POSITION_LIMIT_BREACH']:
            return {
                'approved': False,
                'reason': f"Risk limits breached: {risk_status['violations']}",
                'risk_status': risk_status,
                'position_size': None
            }
        
        # Calculate position size
        position_size = self.position_sizer.calculate_position_size(
            signal, account_equity, market_data.price, market_data
        )
        
        # Check if position size is valid
        if not position_size.is_valid:
            return {
                'approved': False,
                'reason': f"Invalid position size: {position_size.reason}",
                'risk_status': risk_status,
                'position_size': position_size
            }
        
        # Check correlation limits
        correlation_check = self._check_signal_correlation(signal, current_positions)
        if not correlation_check['approved']:
            return {
                'approved': False,
                'reason': correlation_check['reason'],
                'risk_status': risk_status,
                'position_size': position_size
            }
        
        # Risk reduction logic
        if 'metrics' in risk_status and self.risk_monitor.should_reduce_risk(risk_status['metrics']):
            # Reduce position size by 50%
            position_size.quantity *= 0.5
            position_size.notional_usd *= 0.5
            position_size.risk_usd *= 0.5
            logger.info(f"Reduced position size due to risk conditions: {signal.symbol}")
        
        return {
            'approved': True,
            'reason': 'Signal approved',
            'risk_status': risk_status,
            'position_size': position_size,
            'risk_adjusted': self.risk_monitor.should_reduce_risk(risk_status['metrics'])
        }
    
    def _check_signal_correlation(self, 
                                signal: Signal, 
                                current_positions: List[Position]) -> Dict[str, Any]:
        """Check correlation constraints for new signal."""
        
        # Get signal correlation from metadata
        signal_correlation = abs(signal.meta.get('btc_correlation', 0.0))
        
        # Check if signal itself exceeds correlation limit
        if signal_correlation > self.risk_config.correlation_limit:
            return {
                'approved': False,
                'reason': f"Signal correlation too high: {signal_correlation:.2f} > {self.risk_config.correlation_limit:.2f}"
            }
        
        # Check total correlated exposure
        current_correlated_exposure = 0
        total_exposure = 0
        
        for position in current_positions:
            if position.status != 'open':
                continue
                
            position_usd = position.qty * position.entry
            total_exposure += position_usd
            
            pos_correlation = abs(position.meta.get('btc_correlation', 0.0))
            if pos_correlation > self.risk_config.correlation_limit:
                current_correlated_exposure += position_usd
        
        # Add proposed signal exposure
        signal_usd = signal.meta.get('notional_usd', 0)
        if signal_correlation > self.risk_config.correlation_limit:
            projected_correlated = current_correlated_exposure + signal_usd
            projected_total = total_exposure + signal_usd
            
            if projected_total > 0 and projected_correlated / projected_total > 0.6:  # 60% limit
                return {
                    'approved': False,
                    'reason': f"Would exceed correlation exposure limit: {projected_correlated/projected_total:.1%}"
                }
        
        return {'approved': True, 'reason': 'Correlation check passed'}
    
    def get_risk_summary(self, 
                        positions: List[Position], 
                        account_equity: float) -> Dict[str, Any]:
        """Get comprehensive risk summary."""
        
        risk_status = self.risk_monitor.check_risk_limits(positions, account_equity)
        
        # Handle case where metrics might not be available
        if 'metrics' in risk_status and risk_status['metrics']:
            metrics = risk_status['metrics']
            total_equity = getattr(metrics, 'total_equity', account_equity)
            used_equity = getattr(metrics, 'used_equity', 0)
            daily_pnl = getattr(metrics, 'daily_pnl', 0)
            daily_risk_used = getattr(metrics, 'daily_risk_used', 0)
            max_drawdown = getattr(metrics, 'max_drawdown', 0)
            open_positions_count = getattr(metrics, 'open_positions_count', len(positions))
            correlation_exposure = getattr(metrics, 'correlation_exposure', 0)
        else:
            # Fallback values
            total_equity = account_equity
            used_equity = 0
            daily_pnl = 0
            daily_risk_used = 0
            max_drawdown = 0
            open_positions_count = len(positions)
            correlation_exposure = 0
        
        return {
            'account_equity': account_equity,
            'equity_utilization': used_equity / total_equity if total_equity > 0 else 0,
            'daily_pnl': daily_pnl,
            'daily_pnl_pct': daily_pnl / total_equity if total_equity > 0 else 0,
            'daily_risk_used': daily_risk_used,
            'daily_risk_remaining': max(0, self.risk_config.daily_risk_limit - daily_risk_used),
            'max_drawdown': max_drawdown,
            'open_positions': open_positions_count,
            'max_positions': self.risk_config.max_concurrent_positions,
            'positions_available': max(0, self.risk_config.max_concurrent_positions - open_positions_count),
            'correlation_exposure': correlation_exposure,
            'risk_status': risk_status.get('overall_status', 'UNKNOWN'),
            'warnings': risk_status.get('warnings', []),
            'violations': risk_status.get('violations', []),
            'kill_switch_triggered': risk_status.get('kill_switch_triggered', False)
        }
