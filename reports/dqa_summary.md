"""
DQA Summary Report Generator.

Generates a markdown summary of data quality assessment results.
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any
from datetime import datetime


logger = logging.getLogger(__name__)


def generate_dqa_summary(dqa_results: Dict[str, Any], output_path: Path) -> None:
    """
    Generate DQA summary markdown report.
    
    Args:
        dqa_results: DQA assessment results
        output_path: Path to save markdown report
    """
    summary = dqa_results.get('summary', {})
    
    md_lines = [
        "# Data Quality Assessment (DQA) Summary",
        "",
        f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"**Symbols Assessed:** {summary.get('total_symbols', 0)}",
        f"**Data Window:** {summary.get('data_window_hours', 48)} hours",
        "",
        "---",
        "",
        "## Overall Quality Scores",
        "",
        "| Dimension | Score | Status |",
        "|-----------|-------|--------|",
        f"| **Completeness** | {summary.get('average_completeness', 0):.2f}/10 | {_score_status(summary.get('average_completeness', 0))} |",
        f"| **Freshness** | {summary.get('average_freshness', 0):.2f}/10 | {_score_status(summary.get('average_freshness', 0))} |",
        f"| **Consistency** | {summary.get('average_consistency', 0):.2f}/10 | {_score_status(summary.get('average_consistency', 0))} |",
        f"| **Stability** | {summary.get('average_stability', 0):.2f}/10 | {_score_status(summary.get('average_stability', 0))} |",
        f"| **Overall** | {summary.get('average_overall_score', 0):.2f}/10 | {_score_status(summary.get('average_overall_score', 0))} |",
        "",
        "---",
        "",
        "## Key Findings",
        "",
        f"- **Total Gaps (OHLCV):** {summary.get('total_gaps', 0)}",
        f"- **Symbols with Errors:** {summary.get('symbols_with_errors', 0)}",
        f"- **Price Teleports:** {summary.get('total_teleports', 0)} (spikes > 5×ATR)",
        "",
        "---",
        "",
        "## Per-Symbol Details",
        ""
    ]
    
    # Add per-symbol table
    if 'metrics' in dqa_results:
        md_lines.extend([
            "| Symbol | Overall | Completeness | Freshness | Consistency | Stability | Gaps | Teleports |",
            "|--------|---------|--------------|-----------|-------------|-----------|------|-----------|"
        ])
        
        for symbol, metrics in dqa_results['metrics'].items():
            md_lines.append(
                f"| {symbol} | "
                f"{metrics.get('overall_score', 0):.2f} | "
                f"{metrics.get('completeness_score', 0):.2f} | "
                f"{metrics.get('freshness_score', 0):.2f} | "
                f"{metrics.get('consistency_score', 0):.2f} | "
                f"{metrics.get('stability_score', 0):.2f} | "
                f"{metrics.get('ohlcv_gaps', 0)} | "
                f"{metrics.get('price_teleports', 0)} |"
            )
    
    md_lines.extend([
        "",
        "---",
        "",
        "## Recommendations",
        ""
    ])
    
    # Generate recommendations based on scores
    avg_completeness = summary.get('average_completeness', 10)
    avg_freshness = summary.get('average_freshness', 10)
    avg_consistency = summary.get('average_consistency', 10)
    avg_stability = summary.get('average_stability', 10)
    
    if avg_completeness < 7.0:
        md_lines.append("- ⚠️ **Completeness Issue:** High rate of missing data. Consider:")
        md_lines.append("  - Implementing gap interpolation (forward-fill)")
        md_lines.append("  - Monitoring exchange API uptime")
        md_lines.append("  - Adding redundant data sources")
        md_lines.append("")
    
    if avg_freshness < 8.0:
        md_lines.append("- ⚠️ **Freshness Issue:** Data latency is high. Consider:")
        md_lines.append("  - Using WebSocket streams instead of REST polling")
        md_lines.append("  - Optimizing network latency")
        md_lines.append("  - Adding timestamp drift monitoring")
        md_lines.append("")
    
    if avg_consistency < 7.0:
        md_lines.append("- ⚠️ **Consistency Issue:** Data validation errors detected. Consider:")
        md_lines.append("  - Adding pre-ingestion validation")
        md_lines.append("  - Filtering out malformed candles")
        md_lines.append("  - Reporting issues to exchange")
        md_lines.append("")
    
    if avg_stability < 7.0:
        md_lines.append("- ⚠️ **Stability Issue:** Frequent price anomalies. Consider:")
        md_lines.append("  - Implementing teleport bar detection and filtering")
        md_lines.append("  - Adding ATR spike alerts")
        md_lines.append("  - Excluding symbols with high anomaly rate")
        md_lines.append("")
    
    if all(score >= 8.0 for score in [avg_completeness, avg_freshness, avg_consistency, avg_stability]):
        md_lines.append("- ✅ **All systems nominal.** Data quality is excellent across all dimensions.")
        md_lines.append("")
    
    md_lines.extend([
        "---",
        "",
        "**End of DQA Summary**"
    ])
    
    # Write to file
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(md_lines))
    
    logger.info(f"DQA summary saved to {output_path}")


def _score_status(score: float) -> str:
    """Convert score to status emoji."""
    if score >= 8.0:
        return "✅ Good"
    elif score >= 6.0:
        return "⚠️ Acceptable"
    else:
        return "🔴 Poor"


if __name__ == "__main__":
    # Example usage
    mock_results = {
        'summary': {
            'total_symbols': 5,
            'data_window_hours': 48,
            'average_overall_score': 8.0,
            'average_completeness': 8.5,
            'average_freshness': 9.0,
            'average_consistency': 7.5,
            'average_stability': 7.0,
            'total_gaps': 12,
            'symbols_with_errors': 1,
            'total_teleports': 5
        },
        'metrics': {
            'BTC/USDT': {
                'overall_score': 8.5,
                'completeness_score': 9.0,
                'freshness_score': 9.5,
                'consistency_score': 8.0,
                'stability_score': 7.5,
                'ohlcv_gaps': 2,
                'price_teleports': 1
            }
        }
    }
    
    output_path = Path("reports/dqa_summary.md")
    generate_dqa_summary(mock_results, output_path)
    print(f"Generated: {output_path}")
