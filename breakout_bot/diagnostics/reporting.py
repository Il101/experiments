"""Diagnostics reporting utilities."""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path
from statistics import median
from typing import Any, Dict, Iterable, List, Tuple


class DiagnosticsReportBuilder:
    """Builds aggregated diagnostics report from JSONL logs."""

    def __init__(self, log_paths: Iterable[Path]):
        self.log_paths = [Path(p) for p in log_paths if Path(p).exists()]

    def _load_events(self) -> List[Dict[str, Any]]:
        events: List[Dict[str, Any]] = []
        for path in self.log_paths:
            with path.open("r", encoding="utf-8") as fp:
                for line in fp:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        events.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
        return events

    def build(self) -> Dict[str, Any]:
        events = self._load_events()
        reason_counter = Counter()
        near_miss_metrics: Dict[str, List[Dict[str, Any]]] = defaultdict(list)

        for event in events:
            reason = event.get("reason")
            if reason:
                reason_counter[reason] += 1
            payload = event.get("payload", {})
            passed = event.get("passed")
            if passed is False and reason and reason.startswith("signal:"):
                near_miss_metrics[reason].append(payload)

        top_reasons = reason_counter.most_common()
        recommendations = self._build_recommendations(near_miss_metrics)

        return {
            "total_events": len(events),
            "unique_reasons": len(reason_counter),
            "reasons": top_reasons,
            "recommendations": recommendations,
        }

    def _build_recommendations(
        self, near_miss_metrics: Dict[str, List[Dict[str, Any]]]
    ) -> List[str]:
        recommendations: List[str] = []
        for reason, samples in near_miss_metrics.items():
            if not samples:
                continue
            condition = reason.split(":")[-1]
            values = [sample.get("value") for sample in samples if sample.get("value") is not None]
            thresholds = [
                sample.get("threshold")
                for sample in samples
                if sample.get("threshold") is not None and isinstance(sample.get("threshold"), (int, float))
            ]
            if not values or not thresholds:
                continue
            val_median = median(values)
            thr_median = median(thresholds)
            if isinstance(thr_median, (int, float)) and isinstance(val_median, (int, float)):
                delta = thr_median - val_median
                adjustment = thr_median - delta * 0.5
                recommendations.append(
                    f"{condition}: consider adjusting threshold from {thr_median:.4f} to {adjustment:.4f}"
                )
        return recommendations

