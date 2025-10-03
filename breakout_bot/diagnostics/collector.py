"""Structured diagnostics collection for breakout bot pipeline."""

from __future__ import annotations

import json
import os
import threading
import time
from collections import Counter
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, Optional
import re


@dataclass
class DiagnosticsEvent:
    """Single diagnostics event that can be serialized to JSON."""

    ts: float
    component: str
    stage: str
    symbol: Optional[str] = None
    payload: Dict[str, Any] = field(default_factory=dict)
    reason: Optional[str] = None
    passed: Optional[bool] = None


class DiagnosticsCollector:
    """Collects diagnostics events and aggregates failure reasons."""

    def __init__(
        self,
        enabled: bool,
        session_id: Optional[str] = None,
        output_dir: Optional[Path] = None,
    ) -> None:
        self.enabled = enabled
        raw_session = session_id or time.strftime("diag_%Y%m%d_%H%M%S")
        self.session_id = self._sanitize(raw_session)
        self.output_dir = output_dir or Path("logs") / "diag"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.output_path = self.output_dir / f"{self.session_id}.jsonl"
        self._lock = threading.Lock()
        self._reasons = Counter()
        self._event_count = 0

    @property
    def reasons(self) -> Counter:
        """Expose aggregated reasons counter."""
        return self._reasons

    @staticmethod
    def _default_serializer(obj):
        try:
            import numpy as np  # Local import to avoid hard dependency during module import
        except ImportError:  # pragma: no cover - numpy is expected to be installed
            np = None

        if np is not None and isinstance(obj, np.generic):
            return obj.item()
        if isinstance(obj, (set, tuple)):
            return list(obj)
        return str(obj)

    @staticmethod
    def _sanitize(name: str) -> str:
        return re.sub(r"[^A-Za-z0-9_.-]", "_", name)

    def record_signal_condition(
        self,
        symbol: str,
        condition: str,
        value: Any,
        threshold: Any,
        passed: bool,
        candle_ts: Optional[int] = None,
        correlation_id: Optional[str] = None,
        extra: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Record a signal condition check with optional correlation_id."""
        if not self.enabled:
            return

        record = {
            "type": "signal_condition",
            "symbol": symbol,
            "condition": condition,
            "value": value,
            "threshold": threshold,
            "passed": passed,
            "candle_ts": candle_ts,
            "correlation_id": correlation_id,
            "extra": extra or {},
            "timestamp": time.time()
        }

        self.signal_conditions.append(record)

        # Update reasons counter
        if not passed:
            self._reasons[condition] += 1

    def _write_event(self, event: DiagnosticsEvent) -> None:
        if not self.enabled:
            return

        record = asdict(event)
        with self._lock:
            self.output_dir.mkdir(parents=True, exist_ok=True)
            with self.output_path.open("a", encoding="utf-8") as fp:
                fp.write(json.dumps(record, ensure_ascii=True, default=self._default_serializer) + "\n")
            if event.reason:
                self._reasons[event.reason] += 1
            self._event_count += 1

    def record(
        self,
        component: str,
        stage: str,
        symbol: Optional[str] = None,
        payload: Optional[Dict[str, Any]] = None,
        reason: Optional[str] = None,
        passed: Optional[bool] = None,
    ) -> None:
        """Record a generic diagnostics event."""
        if not self.enabled:
            return

        event = DiagnosticsEvent(
            ts=time.time(),
            component=component,
            stage=stage,
            symbol=symbol,
            payload=payload or {},
            reason=reason,
            passed=passed,
        )
        self._write_event(event)

    def record_filter(
        self,
        stage: str,
        symbol: str,
        filter_name: str,
        value: Any,
        threshold: Any,
        passed: bool,
        extra: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Record filter evaluation diagnostics."""
        payload = {
            "filter": filter_name,
            "value": value,
            "threshold": threshold,
        }
        if extra:
            payload.update(extra)
        reason = None if passed else f"filter:{filter_name}"
        self.record(
            component="scanner",
            stage=stage,
            symbol=symbol,
            payload=payload,
            reason=reason,
            passed=passed,
        )

    def record_signal_condition(
        self,
        strategy: str,
        symbol: str,
        condition: str,
        value: Any,
        threshold: Any,
        passed: bool,
        candle_ts: Optional[int] = None,
        extra: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Record signal condition evaluation."""
        payload: Dict[str, Any] = {
            "condition": condition,
            "value": value,
            "threshold": threshold,
        }
        if candle_ts is not None:
            payload["candle_ts"] = candle_ts
        if extra:
            payload.update(extra)
        reason = None if passed else f"signal:{strategy}:{condition}"
        self.record(
            component="signal",
            stage=strategy,
            symbol=symbol,
            payload=payload,
            reason=reason,
            passed=passed,
        )

    def increment_reason(self, reason: str) -> None:
        """Manually increment a failure reason."""
        if not self.enabled:
            return
        with self._lock:
            self._reasons[reason] += 1
            self._event_count += 1

    def update_session(self, session_id: str) -> None:
        """Update session identifier and rotate diagnostics file."""
        if not self.enabled:
            return
        with self._lock:
            self.session_id = self._sanitize(session_id)
            self.output_path = self.output_dir / f"{self.session_id}.jsonl"
            self.output_dir.mkdir(parents=True, exist_ok=True)

    def snapshot(self) -> Dict[str, Any]:
        """Return a snapshot of diagnostics stats."""
        with self._lock:
            return {
                "session_id": self.session_id,
                "enabled": self.enabled,
                "events": self._event_count,
                "top_reasons": self._reasons.most_common(10),
                "output_path": str(self.output_path),
            }
