"""
Activity tracking and decay detection for market momentum.

Calculates activity index from multiple trade flow metrics and detects
when activity is dropping (momentum decay).
"""

import logging
import time
from collections import deque
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
import numpy as np

from ..data.streams.trades_ws import TradesAggregator, TradeMetrics


logger = logging.getLogger(__name__)


@dataclass
class ActivityMetrics:
    """Activity metrics for a symbol."""
    symbol: str
    activity_index: float = 0.0  # Z-score based composite index
    tpm_60s_z: float = 0.0  # Z-score of TPM 60s
    tps_10s_z: float = 0.0  # Z-score of TPS 10s
    vol_delta_z: float = 0.0  # Z-score of abs(volume delta)
    is_dropping: bool = False  # Activity is dropping
    drop_fraction: float = 0.0  # How much activity dropped
    last_update: int = 0


class ActivityTracker:
    """
    Tracks trading activity and detects momentum decay.
    
    Features:
    - Composite activity index from TPM, TPS, vol_delta
    - Activity decay detection
    - Historical activity tracking
    """
    
    def __init__(
        self,
        trades_aggregator: TradesAggregator,
        lookback_periods: int = 60,
        drop_threshold: float = 0.3
    ):
        """
        Initialize activity tracker.
        
        Args:
            trades_aggregator: Trades WebSocket aggregator
            lookback_periods: Number of periods for historical tracking
            drop_threshold: Threshold for detecting activity drop (fraction)
        """
        self.trades_aggregator = trades_aggregator
        self.lookback_periods = lookback_periods
        self.drop_threshold = drop_threshold
        
        # Historical activity by symbol
        self.activity_history: Dict[str, deque] = {}
        
        # Current metrics
        self.metrics: Dict[str, ActivityMetrics] = {}
        
        logger.info(
            f"ActivityTracker initialized: lookback={lookback_periods}, "
            f"drop_threshold={drop_threshold}"
        )
    
    def update_activity(self, symbol: str) -> ActivityMetrics:
        """
        Update activity metrics for a symbol.
        
        Returns:
            Updated ActivityMetrics
        """
        trade_metrics = self.trades_aggregator.get_metrics(symbol)
        if not trade_metrics:
            return ActivityMetrics(symbol=symbol)
        
        current_ts = int(time.time() * 1000)
        
        # Initialize history if needed
        if symbol not in self.activity_history:
            self.activity_history[symbol] = deque(maxlen=self.lookback_periods)
        
        # Calculate raw metrics
        tpm_60s = trade_metrics.tpm_60s
        tps_10s = trade_metrics.tps_10s
        vol_delta_abs = abs(trade_metrics.vol_delta_60s)
        
        # Store in history
        self.activity_history[symbol].append({
            'timestamp': current_ts,
            'tpm_60s': tpm_60s,
            'tps_10s': tps_10s,
            'vol_delta_abs': vol_delta_abs
        })
        
        # Calculate Z-scores
        tpm_z = self._calculate_z_score(symbol, 'tpm_60s', tpm_60s)
        tps_z = self._calculate_z_score(symbol, 'tps_10s', tps_10s)
        vol_delta_z = self._calculate_z_score(symbol, 'vol_delta_abs', vol_delta_abs)
        
        # Composite activity index
        activity_index = tpm_z + tps_z + vol_delta_z
        
        # Check for activity drop
        is_dropping, drop_fraction = self._check_activity_drop(symbol, activity_index)
        
        # Create metrics
        metrics = ActivityMetrics(
            symbol=symbol,
            activity_index=activity_index,
            tpm_60s_z=tpm_z,
            tps_10s_z=tps_z,
            vol_delta_z=vol_delta_z,
            is_dropping=is_dropping,
            drop_fraction=drop_fraction,
            last_update=current_ts
        )
        
        self.metrics[symbol] = metrics
        
        return metrics
    
    def _calculate_z_score(self, symbol: str, metric_name: str, current_value: float) -> float:
        """
        Calculate Z-score for a metric.
        
        Z = (X - μ) / σ
        """
        if symbol not in self.activity_history:
            return 0.0
        
        history = self.activity_history[symbol]
        if len(history) < 2:
            return 0.0
        
        values = [h[metric_name] for h in history]
        
        mean = np.mean(values)
        std = np.std(values)
        
        if std == 0:
            return 0.0
        
        z_score = (current_value - mean) / std
        
        return z_score
    
    def _check_activity_drop(
        self,
        symbol: str,
        current_activity: float
    ) -> Tuple[bool, float]:
        """
        Check if activity is dropping significantly.
        
        Returns:
            (is_dropping, drop_fraction)
        """
        if symbol not in self.activity_history:
            return False, 0.0
        
        history = self.activity_history[symbol]
        if len(history) < 10:
            return False, 0.0
        
        # Get recent activity indices
        recent_activities = []
        for entry in history:
            # Reconstruct activity index from stored metrics
            tpm_z = self._calculate_z_score(symbol, 'tpm_60s', entry['tpm_60s'])
            tps_z = self._calculate_z_score(symbol, 'tps_10s', entry['tps_10s'])
            vol_delta_z = self._calculate_z_score(symbol, 'vol_delta_abs', entry['vol_delta_abs'])
            activity_idx = tpm_z + tps_z + vol_delta_z
            recent_activities.append(activity_idx)
        
        # Compare current vs recent average
        recent_avg = np.mean(recent_activities[-10:-1])  # Exclude current
        
        if recent_avg <= 0:
            return False, 0.0
        
        drop_fraction = (recent_avg - current_activity) / abs(recent_avg)
        
        is_dropping = drop_fraction >= self.drop_threshold
        
        return is_dropping, drop_fraction
    
    def is_activity_dropping(
        self,
        symbol: str,
        drop_frac: Optional[float] = None,
        lookback_s: Optional[int] = None
    ) -> bool:
        """
        Check if activity is dropping for a symbol.
        
        Args:
            symbol: Trading pair symbol
            drop_frac: Custom drop fraction threshold (uses default if None)
            lookback_s: Custom lookback in seconds (not implemented yet)
        
        Returns:
            True if activity is dropping
        """
        if symbol not in self.metrics:
            return False
        
        metrics = self.metrics[symbol]
        
        if drop_frac is not None:
            return metrics.drop_fraction >= drop_frac
        
        return metrics.is_dropping
    
    def get_activity_index(self, symbol: str) -> float:
        """Get current activity index for a symbol."""
        if symbol not in self.metrics:
            return 0.0
        
        return self.metrics[symbol].activity_index
    
    def get_metrics(self, symbol: str) -> Optional[ActivityMetrics]:
        """Get all activity metrics for a symbol."""
        return self.metrics.get(symbol)
    
    def get_activity_history(self, symbol: str, periods: int = 20) -> List[float]:
        """
        Get historical activity indices.
        
        Args:
            symbol: Trading pair symbol
            periods: Number of recent periods to return
        
        Returns:
            List of activity indices (most recent last)
        """
        if symbol not in self.activity_history:
            return []
        
        history = self.activity_history[symbol]
        
        # Reconstruct activity indices
        activities = []
        for entry in list(history)[-periods:]:
            tpm_z = self._calculate_z_score(symbol, 'tpm_60s', entry['tpm_60s'])
            tps_z = self._calculate_z_score(symbol, 'tps_10s', entry['tps_10s'])
            vol_delta_z = self._calculate_z_score(symbol, 'vol_delta_abs', entry['vol_delta_abs'])
            activity_idx = tpm_z + tps_z + vol_delta_z
            activities.append(activity_idx)
        
        return activities
