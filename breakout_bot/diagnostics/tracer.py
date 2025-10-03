"""
Pipeline Tracer for Data Lineage and Event Correlation.

Provides correlation_id tracking and structured logging across the entire
trading pipeline: scanning → levels → signals → sizing → execution → managing.
"""

import json
import logging
import time
from contextlib import contextmanager
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime


logger = logging.getLogger(__name__)


@dataclass
class TraceEvent:
    """Single trace event in the pipeline."""
    correlation_id: str
    step: str  # SCANNING, LEVEL_BUILDING, SIGNAL_WAIT, SIGNAL, SIZING, EXECUTION, MANAGING
    timestamp_ms: int
    symbol: str
    metric: Optional[str] = None
    value: Optional[Any] = None
    threshold: Optional[Any] = None
    passed: Optional[bool] = None
    reason: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class PipelineTracer:
    """
    Traces data flow through the trading pipeline with correlation IDs.
    
    Usage:
        tracer = PipelineTracer()
        with tracer.trace(symbol="BTC/USDT", bar_ts=1234567890):
            tracer.log_scan_filter("atr15m_pct", value=0.0123, threshold_min=0.01, passed=True)
            tracer.log_level("resistance", price=50000.0, touches=5)
            tracer.log_signal_gate("epsilon", value=0.001, threshold=0.002, passed=True)
            tracer.log_sizing(risk_r=0.01, size_usd=1000, depth_share=0.05)
    """
    
    def __init__(self, log_dir: Optional[Path] = None, enabled: bool = True):
        self.enabled = enabled
        self.log_dir = log_dir or Path("logs/trace")
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Current trace context
        self._current_correlation_id: Optional[str] = None
        self._current_symbol: Optional[str] = None
        
        # Event buffer
        self._events: List[TraceEvent] = []
        self._max_buffer_size = 1000
        
        # Daily log file
        self._current_date = None
        self._log_file = None
        
        logger.info(f"PipelineTracer initialized: enabled={enabled}, log_dir={self.log_dir}")
    
    def _ensure_log_file(self) -> None:
        """Ensure we have a valid log file for today."""
        today = datetime.now().strftime("%Y%m%d")
        if today != self._current_date:
            if self._log_file:
                self._log_file.close()
            
            self._current_date = today
            log_path = self.log_dir / f"trace_{today}.jsonl"
            self._log_file = open(log_path, "a", encoding="utf-8")
            logger.info(f"Opened trace log: {log_path}")
    
    @contextmanager
    def trace(self, symbol: str, bar_ts: int):
        """
        Context manager for tracing a single bar/event.
        
        Args:
            symbol: Trading symbol
            bar_ts: Bar timestamp (epoch seconds or milliseconds)
        """
        if not self.enabled:
            yield
            return
        
        # Generate correlation ID
        if bar_ts > 10**12:  # Milliseconds
            bar_ts_s = bar_ts // 1000
        else:
            bar_ts_s = bar_ts
        
        correlation_id = f"{symbol}:{bar_ts_s}"
        
        self._current_correlation_id = correlation_id
        self._current_symbol = symbol
        
        try:
            yield
        finally:
            self._current_correlation_id = None
            self._current_symbol = None
    
    def _log_event(self, event: TraceEvent) -> None:
        """Log a trace event."""
        if not self.enabled:
            return
        
        self._events.append(event)
        
        # Write to file
        self._ensure_log_file()
        json_line = json.dumps(asdict(event), ensure_ascii=False)
        self._log_file.write(json_line + "\n")
        self._log_file.flush()
        
        # Flush buffer if too large
        if len(self._events) > self._max_buffer_size:
            self._events = self._events[-self._max_buffer_size // 2:]
    
    def log_scan_filter(
        self,
        metric: str,
        value: Any,
        threshold_min: Optional[Any] = None,
        threshold_max: Optional[Any] = None,
        passed: bool = False,
        reason: str = "",
        **extra_metadata
    ) -> None:
        """Log a scanning filter result."""
        threshold = threshold_min if threshold_min is not None else threshold_max
        
        event = TraceEvent(
            correlation_id=self._current_correlation_id or "unknown",
            step="SCANNING",
            timestamp_ms=int(time.time() * 1000),
            symbol=self._current_symbol or "unknown",
            metric=metric,
            value=value,
            threshold=threshold,
            passed=passed,
            reason=reason,
            metadata={
                "threshold_min": threshold_min,
                "threshold_max": threshold_max,
                **extra_metadata
            }
        )
        self._log_event(event)
    
    def log_level(
        self,
        level_type: str,
        price: float,
        touches: int,
        strength: float = 0.0,
        method: str = "",
        **extra_metadata
    ) -> None:
        """Log level detection."""
        event = TraceEvent(
            correlation_id=self._current_correlation_id or "unknown",
            step="LEVEL_BUILDING",
            timestamp_ms=int(time.time() * 1000),
            symbol=self._current_symbol or "unknown",
            metric="level_detected",
            value=price,
            metadata={
                "level_type": level_type,
                "touches": touches,
                "strength": strength,
                "method": method,
                **extra_metadata
            }
        )
        self._log_event(event)
    
    def log_signal_gate(
        self,
        gate: str,
        value: Any,
        threshold: Any,
        passed: bool,
        strategy: str = "",
        near_miss: bool = False,
        **extra_metadata
    ) -> None:
        """Log signal gate/condition check."""
        step = "SIGNAL" if passed else "SIGNAL_WAIT"
        
        event = TraceEvent(
            correlation_id=self._current_correlation_id or "unknown",
            step=step,
            timestamp_ms=int(time.time() * 1000),
            symbol=self._current_symbol or "unknown",
            metric=gate,
            value=value,
            threshold=threshold,
            passed=passed,
            metadata={
                "strategy": strategy,
                "near_miss": near_miss,
                **extra_metadata
            }
        )
        self._log_event(event)
    
    def log_sizing(
        self,
        risk_r: float,
        size_usd: float,
        depth_share: float,
        max_position_size: float,
        passed: bool = True,
        **extra_metadata
    ) -> None:
        """Log position sizing."""
        event = TraceEvent(
            correlation_id=self._current_correlation_id or "unknown",
            step="SIZING",
            timestamp_ms=int(time.time() * 1000),
            symbol=self._current_symbol or "unknown",
            metric="position_size",
            value=size_usd,
            passed=passed,
            metadata={
                "risk_r": risk_r,
                "depth_share": depth_share,
                "max_position_size": max_position_size,
                **extra_metadata
            }
        )
        self._log_event(event)
    
    def log_execution(
        self,
        order_type: str,
        quantity: float,
        price: float,
        slices: int = 1,
        intent: str = "entry",
        **extra_metadata
    ) -> None:
        """Log execution event."""
        event = TraceEvent(
            correlation_id=self._current_correlation_id or "unknown",
            step="EXECUTION",
            timestamp_ms=int(time.time() * 1000),
            symbol=self._current_symbol or "unknown",
            metric="order_placed",
            value=quantity,
            metadata={
                "order_type": order_type,
                "price": price,
                "slices": slices,
                "intent": intent,
                **extra_metadata
            }
        )
        self._log_event(event)
    
    def log_managing(
        self,
        action: str,
        trigger: str,
        value: Any,
        **extra_metadata
    ) -> None:
        """Log position management action."""
        event = TraceEvent(
            correlation_id=self._current_correlation_id or "unknown",
            step="MANAGING",
            timestamp_ms=int(time.time() * 1000),
            symbol=self._current_symbol or "unknown",
            metric=action,
            value=value,
            metadata={
                "trigger": trigger,
                **extra_metadata
            }
        )
        self._log_event(event)
    
    def get_events(self, correlation_id: Optional[str] = None) -> List[TraceEvent]:
        """Get events for a correlation ID or all recent events."""
        if correlation_id:
            return [e for e in self._events if e.correlation_id == correlation_id]
        return list(self._events)
    
    def close(self) -> None:
        """Close tracer and flush logs."""
        if self._log_file:
            self._log_file.close()
            self._log_file = None
        logger.info("PipelineTracer closed")


# Global tracer instance
_tracer: Optional[PipelineTracer] = None


def get_tracer(enabled: bool = True) -> PipelineTracer:
    """Get or create global tracer instance."""
    global _tracer
    if _tracer is None:
        _tracer = PipelineTracer(enabled=enabled)
    return _tracer


def close_tracer() -> None:
    """Close global tracer."""
    global _tracer
    if _tracer:
        _tracer.close()
        _tracer = None
