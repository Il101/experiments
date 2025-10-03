"""
Metrics API router for detailed performance tracking
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import time

from ...utils.metrics_logger import get_metrics_logger

router = APIRouter()

@router.get("/summary")
async def get_metrics_summary():
    """Get overall metrics summary"""
    try:
        metrics_logger = get_metrics_logger()
        
        # Get performance summary
        performance = metrics_logger.get_performance_summary()
        
        # Get key metrics summaries
        engine_cycle_time = metrics_logger.get_metrics_summary('engine_cycle_time', 100)
        engine_positions = metrics_logger.get_metrics_summary('engine_positions', 100)
        engine_signals = metrics_logger.get_metrics_summary('engine_signals', 100)
        engine_orders = metrics_logger.get_metrics_summary('engine_orders', 100)
        
        # Get trade metrics
        trade_events = metrics_logger.get_metrics_summary('trade_opened', 100)
        trade_pnl = metrics_logger.get_metrics_summary('trade_pnl', 100)
        
        # Get scanner metrics
        scanner_symbols = metrics_logger.get_metrics_summary('scanner_symbols_scanned', 100)
        scanner_candidates = metrics_logger.get_metrics_summary('scanner_candidates_found', 100)
        scanner_time = metrics_logger.get_metrics_summary('scanner_scan_time', 100)
        
        return {
            "performance": performance,
            "engine": {
                "cycle_time": engine_cycle_time,
                "positions": engine_positions,
                "signals": engine_signals,
                "orders": engine_orders
            },
            "trading": {
                "events": trade_events,
                "pnl": trade_pnl
            },
            "scanner": {
                "symbols_scanned": scanner_symbols,
                "candidates_found": scanner_candidates,
                "scan_time": scanner_time
            },
            "timestamp": int(time.time() * 1000)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get metrics summary: {str(e)}")

@router.get("/performance")
async def get_performance_metrics():
    """Get current performance metrics"""
    try:
        metrics_logger = get_metrics_logger()
        return metrics_logger.get_performance_summary()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get performance metrics: {str(e)}")

@router.get("/metric/{metric_name}")
async def get_metric_data(
    metric_name: str,
    last_n: int = Query(100, ge=1, le=1000, description="Number of recent data points to return")
):
    """Get data for a specific metric"""
    try:
        metrics_logger = get_metrics_logger()
        return metrics_logger.get_metrics_summary(metric_name, last_n)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get metric data: {str(e)}")

@router.get("/all")
async def get_all_metrics():
    """Get all collected metrics"""
    try:
        metrics_logger = get_metrics_logger()
        return metrics_logger.get_all_metrics()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get all metrics: {str(e)}")

@router.post("/clear")
async def clear_metrics():
    """Clear all collected metrics"""
    try:
        metrics_logger = get_metrics_logger()
        metrics_logger.clear_metrics()
        return {"success": True, "message": "All metrics cleared"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to clear metrics: {str(e)}")

@router.get("/health")
async def get_metrics_health():
    """Get metrics system health status"""
    try:
        metrics_logger = get_metrics_logger()
        performance = metrics_logger.get_performance_summary()
        
        # Check if metrics are being collected
        all_metrics = metrics_logger.get_all_metrics()
        metrics_count = sum(len(metrics) for metrics in all_metrics.values())
        
        # Check performance thresholds
        health_status = "healthy"
        issues = []
        
        if performance.get('cpu_percent', 0) > 90:
            health_status = "warning"
            issues.append("High CPU usage")
        
        if performance.get('memory_percent', 0) > 95:
            health_status = "warning"
            issues.append("High memory usage")
        
        if metrics_count == 0:
            health_status = "warning"
            issues.append("No metrics collected")
        
        return {
            "status": health_status,
            "issues": issues,
            "metrics_count": metrics_count,
            "performance": performance,
            "timestamp": int(time.time() * 1000)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get metrics health: {str(e)}")
