"""
Signal generation module for Breakout Bot Trading System.

This module implements momentum and retest strategies for generating
entry signals based on level breakouts and market conditions.
"""

import numpy as np
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
import logging

from ..data.models import (
    Candle, L2Depth, MarketData, TradingLevel, Signal, ScanResult
)
from ..config.settings import TradingPreset, SignalConfig
from ..indicators.technical import atr, vwap, ema, obv
from ..diagnostics import DiagnosticsCollector

logger = logging.getLogger(__name__)


class SignalValidator:
    """Validates signal conditions and market state."""
    
    def __init__(self, signal_config: SignalConfig, diagnostics: Optional[DiagnosticsCollector] = None):
        self.config = signal_config
        self.diagnostics = diagnostics

    def _log_condition(
        self,
        strategy: str,
        symbol: str,
        condition: str,
        value: Any,
        threshold: Any,
        passed: bool,
        candle_ts: Optional[int],
        extra: Optional[Dict[str, Any]] = None,
    ) -> None:
        if not self.diagnostics or not self.diagnostics.enabled:
            return
        self.diagnostics.record_signal_condition(
            strategy=strategy,
            symbol=symbol,
            condition=condition,
            value=value,
            threshold=threshold,
            passed=passed,
            candle_ts=candle_ts,
            extra=extra,
        )
    
    def validate_momentum_conditions(
        self,
        symbol: str,
        candles: List[Candle],
        level: TradingLevel,
        l2_depth: L2Depth,
        current_price: float,
    ) -> Dict[str, Any]:
        """Validate conditions for momentum breakout signal."""
        conditions = {
            'price_breakout': False,
            'volume_surge': False,
            'body_ratio': False,
            'l2_imbalance': False,
            'vwap_gap': False,
            'details': {}
        }
        
        if not candles or len(candles) < 5:
            return conditions
        
        current_candle = candles[-1]
        
        # 1. Price breakout condition
        if level.level_type == 'resistance':
            breakout_price = level.price * (1 + self.config.momentum_epsilon)
            conditions['price_breakout'] = current_candle.close > breakout_price
            conditions['details']['breakout_price'] = breakout_price
        else:  # support breakdown for shorts
            breakout_price = level.price * (1 - self.config.momentum_epsilon)
            conditions['price_breakout'] = current_candle.close < breakout_price
            conditions['details']['breakout_price'] = breakout_price
        conditions['details']['close'] = current_candle.close
        self._log_condition(
            'momentum',
            symbol,
            'price_breakout',
            current_candle.close,
            breakout_price,
            conditions['price_breakout'],
            current_candle.ts,
        )
        
        # 2. Volume surge condition
        if len(candles) >= 20:
            volumes = [c.volume for c in candles]
            current_volume = volumes[-1]
            median_volume = np.median(volumes[-20:-1])  # Exclude current
            volume_ratio = current_volume / median_volume if median_volume > 0 else 0
            
            conditions['volume_surge'] = volume_ratio >= self.config.momentum_volume_multiplier
            conditions['details']['volume_ratio'] = volume_ratio
            conditions['details']['volume_threshold'] = self.config.momentum_volume_multiplier
            self._log_condition(
                'momentum',
                symbol,
                'volume_surge',
                volume_ratio,
                self.config.momentum_volume_multiplier,
                conditions['volume_surge'],
                current_candle.ts,
            )
        
        # 3. Candle body ratio condition
        candle_range = current_candle.high - current_candle.low
        if candle_range > 0:
            body_size = abs(current_candle.close - current_candle.open)
            body_ratio = body_size / candle_range
            
            conditions['body_ratio'] = body_ratio >= self.config.momentum_body_ratio_min
            conditions['details']['body_ratio'] = body_ratio
            conditions['details']['body_threshold'] = self.config.momentum_body_ratio_min
            self._log_condition(
                'momentum',
                symbol,
                'body_ratio',
                body_ratio,
                self.config.momentum_body_ratio_min,
                conditions['body_ratio'],
                current_candle.ts,
            )

        # 4. L2 order book imbalance condition
        if l2_depth:
            imbalance = abs(l2_depth.imbalance)
            conditions['l2_imbalance'] = imbalance >= self.config.l2_imbalance_threshold
            conditions['details']['l2_imbalance'] = l2_depth.imbalance
            conditions['details']['imbalance_threshold'] = self.config.l2_imbalance_threshold
            self._log_condition(
                'momentum',
                symbol,
                'l2_imbalance',
                imbalance,
                self.config.l2_imbalance_threshold,
                conditions['l2_imbalance'],
                current_candle.ts,
                extra={'raw_imbalance': l2_depth.imbalance},
            )

        # 5. VWAP gap condition
        if len(candles) >= 20:
            vwap_values = vwap(candles)
            if not np.isnan(vwap_values[-1]):
                current_vwap = vwap_values[-1]
                vwap_gap = abs(current_price - current_vwap) / current_price
                
                atr_values = atr(candles, period=14)
                atr_current = atr_values[-1] if not np.isnan(atr_values[-1]) else 0.01
                max_gap = (atr_current / current_price) * self.config.vwap_gap_max_atr
                
                conditions['vwap_gap'] = vwap_gap <= max_gap
                conditions['details']['vwap_gap'] = vwap_gap
                conditions['details']['max_vwap_gap'] = max_gap
                self._log_condition(
                    'momentum',
                    symbol,
                    'vwap_gap',
                    vwap_gap,
                    max_gap,
                    conditions['vwap_gap'],
                    current_candle.ts,
                )
        
        return conditions
    
    def validate_retest_conditions(
        self,
        symbol: str,
        candles: List[Candle],
        level: TradingLevel,
        l2_depth: L2Depth,
        current_price: float,
        previous_breakout: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Validate conditions for retest signal."""
        conditions = {
            'level_retest': False,
            'pierce_tolerance': False,
            'l2_imbalance': False,
            'trading_activity': False,
            'previous_breakout': False,
            'details': {}
        }
        
        if not candles or len(candles) < 10:
            return conditions
        
        current_candle = candles[-1]
        
        # 1. Level retest condition
        if level.level_type == 'resistance':
            # For resistance retest (after breakout), price should come back to test level
            distance_from_level = abs(current_price - level.price) / level.price
            conditions['level_retest'] = distance_from_level <= 0.005  # Within 0.5%
        else:  # support retest
            distance_from_level = abs(current_price - level.price) / level.price
            conditions['level_retest'] = distance_from_level <= 0.005

        conditions['details']['distance_from_level'] = distance_from_level
        self._log_condition(
            'retest',
            symbol,
            'level_retest',
            distance_from_level,
            0.005,
            conditions['level_retest'],
            current_candle.ts,
        )
        
        # 2. Pierce tolerance condition
        atr_values = atr(candles, period=14)
        atr_current = atr_values[-1] if not np.isnan(atr_values[-1]) else 0.01
        max_pierce = atr_current * self.config.retest_max_pierce_atr
        
        if level.level_type == 'resistance':
            pierce_amount = max(0, level.price - current_candle.low)
        else:  # support
            pierce_amount = max(0, current_candle.high - level.price)
        
        conditions['pierce_tolerance'] = pierce_amount <= max_pierce
        conditions['details']['pierce_amount'] = pierce_amount
        conditions['details']['max_pierce'] = max_pierce
        self._log_condition(
            'retest',
            symbol,
            'pierce_tolerance',
            pierce_amount,
            max_pierce,
            conditions['pierce_tolerance'],
            current_candle.ts,
        )
        
        # 3. L2 imbalance condition (same as momentum)
        if l2_depth:
            imbalance = abs(l2_depth.imbalance)
            conditions['l2_imbalance'] = imbalance >= self.config.l2_imbalance_threshold
            conditions['details']['l2_imbalance'] = l2_depth.imbalance
            self._log_condition(
                'retest',
                symbol,
                'l2_imbalance',
                imbalance,
                self.config.l2_imbalance_threshold,
                conditions['l2_imbalance'],
                current_candle.ts,
                extra={'raw_imbalance': l2_depth.imbalance},
            )
        
        # 4. Trading activity condition
        if len(candles) >= 5:
            recent_volumes = [c.volume for c in candles[-5:]]
            avg_recent_volume = np.mean(recent_volumes)
            
            # Check if recent volume is above minimum threshold
            if len(candles) >= 20:
                historical_volumes = [c.volume for c in candles[-20:-5]]
                avg_historical = np.mean(historical_volumes)
                volume_ratio = avg_recent_volume / avg_historical if avg_historical > 0 else 0
                
                conditions['trading_activity'] = volume_ratio >= 0.8  # 80% of historical
                conditions['details']['volume_activity_ratio'] = volume_ratio
                self._log_condition(
                    'retest',
                    symbol,
                    'trading_activity',
                    volume_ratio,
                    0.8,
                    conditions['trading_activity'],
                    current_candle.ts,
                )
        
        # 5. Previous breakout condition
        if previous_breakout:
            breakout_time = previous_breakout.get('timestamp', 0)
            current_time = current_candle.ts
            time_since_breakout = (current_time - breakout_time) / (1000 * 60 * 60)  # hours
            
            # Breakout should be recent (within 24 hours) but not too recent (> 1 hour)
            conditions['previous_breakout'] = 1 <= time_since_breakout <= 24
            conditions['details']['hours_since_breakout'] = time_since_breakout
            self._log_condition(
                'retest',
                symbol,
                'previous_breakout',
                time_since_breakout,
                '1-24h',
                conditions['previous_breakout'],
                current_candle.ts,
            )

        return conditions


class MomentumStrategy:
    """Momentum breakout strategy implementation."""
    
    def __init__(self, preset: TradingPreset, diagnostics: Optional[DiagnosticsCollector] = None):
        self.preset = preset
        self.signal_config = preset.signal_config
        self.validator = SignalValidator(self.signal_config, diagnostics=diagnostics)
        self.diagnostics = diagnostics
    
    def generate_signal(self, 
                       scan_result: ScanResult,
                       target_level: TradingLevel) -> Optional[Signal]:
        """Generate momentum breakout signal."""
        market_data = scan_result.market_data
        
        if not market_data.candles_5m or len(market_data.candles_5m) < 20:
            logger.debug(f"Insufficient candle data for {market_data.symbol}")
            return None
        
        candles = market_data.candles_5m
        current_price = market_data.price
        
        # Validate momentum conditions
        conditions = self.validator.validate_momentum_conditions(
            market_data.symbol,
            candles,
            target_level,
            market_data.l2_depth,
            current_price
        )
        
        # Check if all conditions are met (l2_imbalance optional if no L2 data)
        required_conditions = ['price_breakout', 'volume_surge', 'body_ratio']
        optional_conditions = ['l2_imbalance'] if market_data.l2_depth is not None else []
        
        conditions_met = (
            all(conditions.get(cond, False) for cond in required_conditions) and
            all(conditions.get(cond, False) for cond in optional_conditions)
        )
        
        if not conditions_met:
            failed = [cond for cond in required_conditions if not conditions.get(cond, False)]
            logger.debug(f"Momentum conditions not met for {market_data.symbol}: {failed}")
            if self.diagnostics and self.diagnostics.enabled:
                self.diagnostics.record(
                    component="signal",
                    stage="momentum_summary",
                    symbol=market_data.symbol,
                    payload={
                        'failed_conditions': failed,
                        'level_price': target_level.price,
                        'close': candles[-1].close,
                    },
                    reason="signal:momentum:summary",
                    passed=False,
                )
            return None
        
        # Determine signal direction
        if target_level.level_type == 'resistance':
            side = 'long'
            entry_price = target_level.price * (1 + self.signal_config.momentum_epsilon)
            stop_loss = self._calculate_momentum_stop_loss(candles, entry_price, 'long')
        else:
            side = 'short'
            entry_price = target_level.price * (1 - self.signal_config.momentum_epsilon)
            stop_loss = self._calculate_momentum_stop_loss(candles, entry_price, 'short')
        
        # Calculate confidence based on condition strength
        confidence = self._calculate_momentum_confidence(conditions, scan_result)
        
        # Create signal
        signal = Signal(
            symbol=market_data.symbol,
            side=side,
            strategy='momentum',
            reason=f"Momentum breakout of {target_level.level_type} at {target_level.price:.6f}",
            entry=entry_price,
            level=target_level.price,
            sl=stop_loss,
            confidence=confidence,
            timestamp=int(datetime.now().timestamp() * 1000),
            meta={
                'level_strength': target_level.strength,
                'level_touches': target_level.touch_count,
                'scan_score': scan_result.score,
                'conditions': conditions,
                'base_height': target_level.base_height,
                'tp1': entry_price + (entry_price - stop_loss) * self.preset.position_config.tp1_r,
                'tp2': entry_price + (entry_price - stop_loss) * self.preset.position_config.tp2_r,
            }
        )
        
        logger.info(f"Generated momentum signal for {market_data.symbol}: "
                   f"{side} at {entry_price:.6f}, SL: {stop_loss:.6f}")

        if self.diagnostics and self.diagnostics.enabled:
            self.diagnostics.record(
                component="signal",
                stage="momentum_summary",
                symbol=market_data.symbol,
                payload={
                    'level_price': target_level.price,
                    'entry': entry_price,
                    'sl': stop_loss,
                    'confidence': confidence,
                    'conditions': conditions,
                },
                passed=True,
            )

        return signal
    
    def _calculate_momentum_stop_loss(self, 
                                    candles: List[Candle], 
                                    entry_price: float,
                                    side: str) -> float:
        """Calculate stop loss for momentum entry."""
        atr_values = atr(candles, period=14)
        atr_current = atr_values[-1] if not np.isnan(atr_values[-1]) else 0.01
        
        # Find swing low/high in last 10 candles
        recent_candles = candles[-10:]
        
        if side == 'long':
            # For long, stop below swing low or entry - 1.2*ATR
            swing_low = min(c.low for c in recent_candles)
            atr_stop = entry_price - (1.2 * atr_current)
            return max(swing_low, atr_stop)
        else:
            # For short, stop above swing high or entry + 1.2*ATR
            swing_high = max(c.high for c in recent_candles)
            atr_stop = entry_price + (1.2 * atr_current)
            return min(swing_high, atr_stop)
    
    def _calculate_momentum_confidence(self, 
                                     conditions: Dict[str, Any],
                                     scan_result: ScanResult) -> float:
        """Calculate signal confidence based on conditions and scan score."""
        # Base confidence from scan score (normalized)
        scan_confidence = min(1.0, max(0.0, (scan_result.score + 2) / 4))  # Assuming score range -2 to +2
        
        # Condition strength factors
        details = conditions.get('details', {})
        
        # Volume strength
        volume_ratio = details.get('volume_ratio', 1.0)
        volume_strength = min(1.0, volume_ratio / 5.0)  # Max at 5x volume
        
        # Body ratio strength  
        body_ratio = details.get('body_ratio', 0.5)
        body_strength = min(1.0, body_ratio / 0.8)  # Max at 80% body
        
        # L2 imbalance strength
        l2_imbalance = abs(details.get('l2_imbalance', 0.0))
        imbalance_strength = min(1.0, l2_imbalance / 0.5)  # Max at 50% imbalance
        
        # Combine factors
        confidence = (scan_confidence * 0.4 + 
                     volume_strength * 0.3 +
                     body_strength * 0.2 +
                     imbalance_strength * 0.1)
        
        return max(0.1, min(1.0, confidence))


class RetestStrategy:
    """Retest strategy implementation."""
    
    def __init__(self, preset: TradingPreset, diagnostics: Optional[DiagnosticsCollector] = None):
        self.preset = preset
        self.signal_config = preset.signal_config
        self.validator = SignalValidator(self.signal_config, diagnostics=diagnostics)
        self.breakout_history: Dict[str, List[Dict[str, Any]]] = {}
        self.diagnostics = diagnostics
    
    def add_breakout_history(self, symbol: str, breakout_info: Dict[str, Any]):
        """Add breakout to history for retest detection."""
        if symbol not in self.breakout_history:
            self.breakout_history[symbol] = []
        
        self.breakout_history[symbol].append(breakout_info)
        
        # Keep only recent breakouts (last 7 days)
        cutoff_time = int((datetime.now() - timedelta(days=7)).timestamp() * 1000)
        self.breakout_history[symbol] = [
            bo for bo in self.breakout_history[symbol] 
            if bo.get('timestamp', 0) >= cutoff_time
        ]
    
    def generate_signal(self, 
                       scan_result: ScanResult,
                       target_level: TradingLevel) -> Optional[Signal]:
        """Generate retest signal."""
        market_data = scan_result.market_data
        
        if not market_data.candles_5m or len(market_data.candles_5m) < 20:
            return None
        
        # Check for previous breakout
        previous_breakout = self._find_relevant_breakout(market_data.symbol, target_level)
        
        candles = market_data.candles_5m
        current_price = market_data.price
        
        # Validate retest conditions
        conditions = self.validator.validate_retest_conditions(
            market_data.symbol,
            candles,
            target_level,
            market_data.l2_depth,
            current_price,
            previous_breakout
        )
        
        # Check if all conditions are met (l2_imbalance optional if no L2 data)
        required_conditions = ['level_retest', 'pierce_tolerance', 'trading_activity']
        optional_conditions = ['l2_imbalance'] if market_data.l2_depth is not None else []
        
        conditions_met = (
            all(conditions.get(cond, False) for cond in required_conditions) and
            all(conditions.get(cond, False) for cond in optional_conditions)
        )
        
        if not conditions_met:
            failed = [cond for cond in required_conditions if not conditions.get(cond, False)]
            logger.debug(f"Retest conditions not met for {market_data.symbol}: {failed}")
            if self.diagnostics and self.diagnostics.enabled:
                self.diagnostics.record(
                    component="signal",
                    stage="retest_summary",
                    symbol=market_data.symbol,
                    payload={
                        'failed_conditions': failed,
                        'level_price': target_level.price,
                        'close': candles[-1].close,
                    },
                    reason="signal:retest:summary",
                    passed=False,
                )
            return None
        
        # Determine signal direction based on previous breakout
        if previous_breakout:
            side = previous_breakout.get('side', 'long')
        else:
            # Default logic if no previous breakout found
            side = 'long' if target_level.level_type == 'support' else 'short'
        
        # Calculate entry and stop loss
        if side == 'long':
            entry_price = target_level.price * (1 + self.signal_config.retest_pierce_tolerance)
            stop_loss = target_level.price - (atr(candles, 14)[-1] * 1.0)
        else:
            entry_price = target_level.price * (1 - self.signal_config.retest_pierce_tolerance)
            stop_loss = target_level.price + (atr(candles, 14)[-1] * 1.0)
        
        # Calculate confidence
        confidence = self._calculate_retest_confidence(conditions, scan_result, previous_breakout)
        
        # Create signal
        signal = Signal(
            symbol=market_data.symbol,
            side=side,
            strategy='retest',
            reason=f"Retest of {target_level.level_type} at {target_level.price:.6f}",
            entry=entry_price,
            level=target_level.price,
            sl=stop_loss,
            confidence=confidence,
            timestamp=int(datetime.now().timestamp() * 1000),
            meta={
                'level_strength': target_level.strength,
                'level_touches': target_level.touch_count,
                'scan_score': scan_result.score,
                'conditions': conditions,
                'previous_breakout': previous_breakout,
                'base_height': target_level.base_height,
                'tp1': entry_price + (entry_price - stop_loss) * self.preset.position_config.tp1_r,
                'tp2': entry_price + (entry_price - stop_loss) * self.preset.position_config.tp2_r,
            }
        )
        
        logger.info(f"Generated retest signal for {market_data.symbol}: "
                   f"{side} at {entry_price:.6f}, SL: {stop_loss:.6f}")

        if self.diagnostics and self.diagnostics.enabled:
            self.diagnostics.record(
                component="signal",
                stage="retest_summary",
                symbol=market_data.symbol,
                payload={
                    'level_price': target_level.price,
                    'entry': entry_price,
                    'sl': stop_loss,
                    'confidence': confidence,
                    'conditions': conditions,
                },
                passed=True,
            )

        return signal
    
    def _find_relevant_breakout(self, symbol: str, level: TradingLevel) -> Optional[Dict[str, Any]]:
        """Find relevant previous breakout for this level."""
        if symbol not in self.breakout_history:
            return None
        
        for breakout in reversed(self.breakout_history[symbol]):  # Most recent first
            breakout_level = breakout.get('level_price', 0)
            level_tolerance = 0.01  # 1% tolerance
            
            if abs(breakout_level - level.price) / level.price <= level_tolerance:
                return breakout
        
        return None
    
    def _calculate_retest_confidence(self, 
                                   conditions: Dict[str, Any],
                                   scan_result: ScanResult,
                                   previous_breakout: Optional[Dict[str, Any]]) -> float:
        """Calculate retest signal confidence."""
        # Base confidence from scan score
        scan_confidence = min(1.0, max(0.0, (scan_result.score + 2) / 4))
        
        # Previous breakout factor
        breakout_factor = 0.8 if previous_breakout else 0.5
        
        # Time factor (recent retest is better)
        details = conditions.get('details', {})
        hours_since_breakout = details.get('hours_since_breakout', 12)
        time_factor = max(0.3, 1.0 - (hours_since_breakout / 24))  # Decay over 24 hours
        
        # Level quality factor
        level_touches = scan_result.strongest_level.touch_count if scan_result.strongest_level else 3
        level_factor = min(1.0, level_touches / 5.0)
        
        # Activity factor
        activity_ratio = details.get('volume_activity_ratio', 0.8)
        activity_factor = min(1.0, activity_ratio)
        
        # Combine factors
        confidence = (scan_confidence * 0.3 +
                     breakout_factor * 0.3 +
                     time_factor * 0.2 +
                     level_factor * 0.1 +
                     activity_factor * 0.1)
        
        return max(0.1, min(1.0, confidence))


class SignalGenerator:
    """Main signal generation coordinator."""
    
    def __init__(self, preset: TradingPreset, diagnostics: Optional[DiagnosticsCollector] = None):
        self.preset = preset
        self.momentum_strategy = MomentumStrategy(preset, diagnostics=diagnostics)
        self.retest_strategy = RetestStrategy(preset, diagnostics=diagnostics)
        self.diagnostics = diagnostics
        
        logger.info(f"Initialized signal generator with preset: {preset.name}")
        logger.info(f"Primary strategy: {preset.strategy_priority}")
    
    def generate_signals(self, scan_results: List[ScanResult]) -> List[Signal]:
        """Generate signals from scan results."""
        signals = []
        
        for scan_result in scan_results:
            try:
                # Only generate signals for results that passed all filters
                if not scan_result.passed_all_filters:
                    continue
                
                # Get strongest levels for signal generation
                if not scan_result.levels:
                    continue
                
                strongest_levels = sorted(scan_result.levels, 
                                        key=lambda x: x.strength, 
                                        reverse=True)[:2]  # Top 2 levels
                
                for level in strongest_levels:
                    signal = self._generate_level_signal(scan_result, level)
                    if signal:
                        signals.append(signal)
                        break  # Only one signal per symbol
                
            except Exception as e:
                logger.error(f"Error generating signal for {scan_result.symbol}: {e}")
                continue
        
        # Sort signals by confidence
        signals.sort(key=lambda x: x.confidence, reverse=True)
        
        logger.info(f"Generated {len(signals)} signals from {len(scan_results)} scan results")
        
        return signals
    
    def _generate_level_signal(self, scan_result: ScanResult, level: TradingLevel) -> Optional[Signal]:
        """Generate signal for a specific level."""
        
        # Determine strategy based on preset and market conditions
        if self.preset.strategy_priority == 'momentum':
            # Try momentum first, fall back to retest
            signal = self.momentum_strategy.generate_signal(scan_result, level)
            if not signal:
                signal = self.retest_strategy.generate_signal(scan_result, level)
        else:  # retest priority
            # Try retest first, fall back to momentum
            signal = self.retest_strategy.generate_signal(scan_result, level)
            if not signal:
                signal = self.momentum_strategy.generate_signal(scan_result, level)
        
        return signal
    
    def add_breakout_history(self, symbol: str, breakout_info: Dict[str, Any]):
        """Add breakout to history for retest strategy."""
        self.retest_strategy.add_breakout_history(symbol, breakout_info)
    
    def get_signal_summary(self, signals: List[Signal]) -> Dict[str, Any]:
        """Get summary statistics of generated signals."""
        if not signals:
            return {
                'total_signals': 0,
                'by_strategy': {},
                'by_side': {},
                'avg_confidence': 0.0,
                'top_symbols': []
            }
        
        # Count by strategy
        by_strategy = {}
        for signal in signals:
            strategy = signal.strategy
            by_strategy[strategy] = by_strategy.get(strategy, 0) + 1
        
        # Count by side
        by_side = {}
        for signal in signals:
            side = signal.side
            by_side[side] = by_side.get(side, 0) + 1
        
        # Calculate average confidence
        avg_confidence = sum(s.confidence for s in signals) / len(signals)
        
        # Get top symbols
        top_symbols = [s.symbol for s in signals[:5]]
        
        return {
            'total_signals': len(signals),
            'by_strategy': by_strategy,
            'by_side': by_side,
            'avg_confidence': avg_confidence,
            'top_symbols': top_symbols
        }
    
    async def generate_signal(self, scan_result: ScanResult) -> Optional[Signal]:
        """Generate a signal for a scan result."""
        try:
            # Check if scan result passed all filters
            if not getattr(scan_result, 'passed_all_filters', True):
                logger.debug(f"Scan result for {scan_result.symbol} failed filters, skipping signal generation")
                if self.diagnostics and self.diagnostics.enabled:
                    self.diagnostics.record(
                        component="signal",
                        stage="gate",
                        symbol=scan_result.symbol,
                        payload={'reason': 'filters_failed'},
                        reason="signal:gate:filters",
                        passed=False,
                    )
                return None
            
            if not scan_result.levels:
                if self.diagnostics and self.diagnostics.enabled:
                    self.diagnostics.record(
                        component="signal",
                        stage="gate",
                        symbol=scan_result.symbol,
                        payload={'reason': 'no_levels'},
                        reason="signal:gate:no_levels",
                        passed=False,
                    )
                return None
            
            # Try all levels, starting with strongest
            sorted_levels = sorted(scan_result.levels, key=lambda x: x.strength, reverse=True)
            
            for level in sorted_levels:
                # Try momentum strategy first
                momentum_signal = self.momentum_strategy.generate_signal(scan_result, level)
                if momentum_signal:
                    return momentum_signal
                
                # Try retest strategy
                retest_signal = self.retest_strategy.generate_signal(scan_result, level)
                if retest_signal:
                    return retest_signal
            
            if self.diagnostics and self.diagnostics.enabled:
                self.diagnostics.record(
                    component="signal",
                    stage="gate",
                    symbol=scan_result.symbol,
                    payload={'reason': 'strategies_rejected'},
                    reason="signal:gate:no_strategy",
                    passed=False,
                )
            return None
            
        except Exception as e:
            logger.error(f"Error generating signal for {scan_result.symbol}: {e}")
            if self.diagnostics and self.diagnostics.enabled:
                self.diagnostics.record(
                    component="signal",
                    stage="error",
                    symbol=scan_result.symbol,
                    payload={'exception': str(e)},
                    reason="signal:error",
                    passed=False,
                )
            return None
