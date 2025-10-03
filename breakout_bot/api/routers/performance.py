"""
Performance metrics router
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timedelta
from ..engine_manager import get_engine_optional

router = APIRouter()

class EquityPoint(BaseModel):
    timestamp: str
    value: float
    cumulativeR: float

class PerformanceMetrics(BaseModel):
    totalTrades: int
    winRate: float
    avgR: float
    sharpeRatio: float
    maxDrawdownR: float
    profitFactor: float
    consecutiveWins: int
    consecutiveLosses: int

class RDistributionPoint(BaseModel):
    r: float
    count: int

@router.get("/equity", response_model=List[EquityPoint])
async def get_equity_history(time_range: Optional[str] = None):
    """Get equity curve history"""
    try:
        engine = get_engine_optional()
        if not engine:
            return []
        
        # Получаем реальную историю эквити из движка
        equity_history = engine.get_equity_history(time_range=time_range or "1d")
        
        if equity_history:
            return [
                EquityPoint(
                    timestamp=point["timestamp"],
                    value=point.get("value", 10000.0),
                    cumulativeR=point.get("cumulativeR", 0.0)
                )
                for point in equity_history
            ]
    except HTTPException:
        # Re-raise HTTP exceptions (like 503 for uninitialized engine)
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get equity history: {str(e)}")

@router.get("/metrics", response_model=PerformanceMetrics)
async def get_performance_metrics():
    """Get overall performance metrics"""
    try:
        engine = get_engine_optional()
        if not engine:
            return PerformanceMetrics(
                totalTrades=0,
                winRate=0.0,
                avgR=0.0,
                sharpeRatio=0.0,
                maxDrawdownR=0.0,
                profitFactor=0.0,
                consecutiveWins=0,
                consecutiveLosses=0
            )
        # Get real performance metrics from engine
        metrics = engine.get_performance_metrics()
        
        return PerformanceMetrics(
            totalTrades=metrics.get('total_trades', 0),
            winRate=metrics.get('win_rate', 0.0),
            avgR=metrics.get('avg_r', 0.0),
            sharpeRatio=metrics.get('sharpe_ratio', 0.0),
            maxDrawdownR=metrics.get('max_drawdown_r', 0.0),
            profitFactor=metrics.get('profit_factor', 0.0),
            consecutiveWins=metrics.get('consecutive_wins', 0),
            consecutiveLosses=metrics.get('consecutive_losses', 0)
        )
    except HTTPException:
        # Re-raise HTTP exceptions (like 503 for uninitialized engine)
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get performance metrics: {str(e)}")

@router.get("/r-distribution", response_model=List[RDistributionPoint])
async def get_r_distribution():
    """Get R-multiple distribution"""
    try:
        engine = get_engine_optional()
        if not engine:
            return []
        # Get real R distribution data from engine
        # Note: get_r_distribution method doesn't exist yet, return empty list
        # distribution_data = engine.get_r_distribution()
        
        # For now, return empty list until R distribution tracking is implemented
        return []
    except HTTPException:
        # Re-raise HTTP exceptions (like 503 for uninitialized engine)
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get R distribution: {str(e)}")