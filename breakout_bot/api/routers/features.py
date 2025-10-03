"""
API endpoints for market microstructure features.

Provides access to:
- Level analysis (with round numbers, cascades, approach quality)
- Activity metrics (TPM, TPS, vol_delta, activity_index)
- Density information
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional, Dict, Any, List
import time
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/features", tags=["features"])


@router.get("/levels")
async def get_levels_analysis(
    symbol: str = Query(..., description="Trading pair symbol"),
    include_metrics: bool = Query(True, description="Include extended metrics")
) -> Dict[str, Any]:
    """
    Get level analysis for a symbol including:
    - Detected levels
    - Round number levels
    - Cascade information
    - Approach quality metrics
    """
    try:
        # TODO: Integrate with actual LevelDetector instance
        # For now, return mock structure
        
        response = {
            "symbol": symbol,
            "timestamp": int(time.time() * 1000),
            "levels": [
                {
                    "price": 50000.0,
                    "level_type": "resistance",
                    "touch_count": 3,
                    "strength": 0.85,
                    "is_round_number": True,
                    "round_bonus": 0.15,
                    "has_cascade": True,
                    "cascade_count": 3
                }
            ],
            "round_levels": [50000.0, 49000.0],
            "cascade_info": {
                "detected": True,
                "levels_in_cascade": 3,
                "center_price": 50000.0,
                "radius_bps": 15.0
            }
        }
        
        if include_metrics:
            response["approach_metrics"] = {
                "is_valid": True,
                "slope_pct_per_bar": 0.8,
                "consolidation_bars": 4,
                "reason": "Valid gradual approach"
            }
        
        return response
        
    except Exception as e:
        logger.error(f"Error getting levels analysis for {symbol}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/activity")
async def get_activity_metrics(
    symbol: str = Query(..., description="Trading pair symbol")
) -> Dict[str, Any]:
    """
    Get real-time activity metrics for a symbol:
    - TPM (trades per minute)
    - TPS (trades per second)
    - Volume delta
    - Activity index
    - Drop detection
    """
    try:
        # TODO: Integrate with actual ActivityTracker instance
        # For now, return mock structure
        
        response = {
            "symbol": symbol,
            "timestamp": int(time.time() * 1000),
            "tpm_60s": 45.5,
            "tpm_10s": 52.3,
            "tps_10s": 0.87,
            "buy_sell_ratio": 1.35,
            "vol_delta_10s": 1250.5,
            "vol_delta_60s": 5420.3,
            "vol_delta_300s": 18500.0,
            "activity_index": 2.45,
            "activity_components": {
                "tpm_z": 1.2,
                "tps_z": 0.8,
                "vol_delta_z": 0.45
            },
            "is_dropping": False,
            "drop_fraction": 0.0
        }
        
        return response
        
    except Exception as e:
        logger.error(f"Error getting activity metrics for {symbol}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/density")
async def get_density_info(
    symbol: str = Query(..., description="Trading pair symbol"),
    range_bps: float = Query(50, description="Price range to scan in bps")
) -> Dict[str, Any]:
    """
    Get order book density information for a symbol:
    - Current density levels
    - Eaten ratios
    - Strength metrics
    """
    try:
        # TODO: Integrate with actual DensityDetector instance
        # For now, return mock structure
        
        response = {
            "symbol": symbol,
            "timestamp": int(time.time() * 1000),
            "densities": [
                {
                    "price": 49970.0,
                    "side": "bid",
                    "size": 125.5,
                    "strength": 8.2,
                    "initial_size": 150.0,
                    "eaten_ratio": 0.16
                },
                {
                    "price": 50030.0,
                    "side": "ask",
                    "size": 98.3,
                    "strength": 7.5,
                    "initial_size": 100.0,
                    "eaten_ratio": 0.02
                }
            ],
            "threshold": 15.3,
            "k_density": 7.0
        }
        
        return response
        
    except Exception as e:
        logger.error(f"Error getting density info for {symbol}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def features_health() -> Dict[str, Any]:
    """Health check for features endpoints."""
    return {
        "status": "healthy",
        "timestamp": int(time.time() * 1000),
        "endpoints": [
            "/api/features/levels",
            "/api/features/activity",
            "/api/features/density"
        ]
    }
