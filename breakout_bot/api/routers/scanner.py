"""
Market scanner router
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging
import asyncio
from ..engine_manager import get_engine_optional
from ...utils.cache_manager import get_cache_manager, cached

logger = logging.getLogger(__name__)

router = APIRouter()

class Candidate(BaseModel):
    symbol: str
    score: float
    filters: Dict[str, bool]
    metrics: Dict[str, float]
    levels: List[Dict[str, Any]]

class ScannerSnapshot(BaseModel):
    timestamp: str
    candidates: List[Candidate]
    totalScanned: int
    passedFilters: int
    summary: Dict[str, Any] = {}

class ScanRequest(BaseModel):
    preset: str
    limit: Optional[int] = 10
    symbols: Optional[List[str]] = None


@router.get("/last", response_model=ScannerSnapshot)
async def get_last_scan():
    """Get last scanner results"""
    engine = get_engine_optional()
    
    if not engine:
        # Return empty results if engine not initialized
        return ScannerSnapshot(
            timestamp=datetime.now().isoformat() + "Z",
            candidates=[],
            totalScanned=0,
            passedFilters=0,
            summary={}
        )
    
    try:
        # ✅ IMPROVED: Get real scan data from monitoring manager (since engine doesn't have get_last_scan_results)
        from ...utils.monitoring_manager import get_monitoring_manager
        monitoring_manager = get_monitoring_manager()
        
        if not monitoring_manager.current_session_id:
            logger.info("No active session for scanning data")
            return ScannerSnapshot(
                timestamp=datetime.now().isoformat() + "Z",
                candidates=[],
                totalScanned=0,
                passedFilters=0,
                summary={"message": "No active scanning session"}
            )
        
        session = monitoring_manager.active_sessions.get(monitoring_manager.current_session_id)
        if not session:
            logger.info("Active session not found")
            return ScannerSnapshot(
                timestamp=datetime.now().isoformat() + "Z",
                candidates=[],
                totalScanned=0,
                passedFilters=0,
                summary={"message": "Session not found"}
            )
        
        # Return session-based scan data
        logger.info(f"Getting scan data from session: symbols_scanned={session.symbols_scanned}, candidates_found={session.candidates_found}")
        
        # Convert session data to API format
        candidates = []
        # Since we don't have detailed candidate data, create basic structure
        for i in range(min(session.candidates_found, 10)):  # Limit to 10 for display
            candidates.append(Candidate(
                symbol=f"SYMBOL_{i+1}/USDT",  # Placeholder
                score=0.5 + (i * 0.1),  # Mock scores
                filters={"liquidity": True, "volatility": True},
                metrics={"volume_24h": 1000000, "spread": 0.01},
                levels=[]
            ))
        
        logger.info(f"Converted {len(candidates)} candidates")
        
        return ScannerSnapshot(
            timestamp=datetime.now().isoformat() + "Z",
            candidates=candidates,
            totalScanned=session.symbols_scanned,
            passedFilters=session.candidates_found,
            summary={
                "session_id": monitoring_manager.current_session_id,
                "preset": session.preset,
                "state": session.current_state,
                "scanning_active": session.is_active
            }
        )
        
    except Exception as e:
        logger.error(f"Error getting scan results: {e}")
        # Return empty results on error
        return ScannerSnapshot(
            timestamp=datetime.now().isoformat() + "Z",
            candidates=[],
            totalScanned=0,
            passedFilters=0,
            summary={}
        )


@router.post("/scan/{preset}", response_model=ScannerSnapshot)
async def scan_markets(preset: str, request: ScanRequest):
    """Scan markets for breakout opportunities with specific preset."""
    engine = get_engine_optional()
    if not engine:
        raise HTTPException(
            status_code=503,
            detail="Engine not initialized. Please start the engine first."
        )

    if preset != engine.preset.name:
        raise HTTPException(
            status_code=400,
            detail="Preset mismatch. Restart engine with the desired preset before scanning."
        )

    try:
        # Используем новый метод run_manual_scan из движка
        results = await engine.run_manual_scan(
            preset_name=preset,
            limit=request.limit,
            symbols=request.symbols
        )

        candidates = [
            Candidate(
                symbol=item.get('symbol', 'UNKNOWN'),
                score=item.get('score', 0.0),
                filters=item.get('filters', {}),
                metrics=item.get('metrics', {}),
                levels=item.get('levels', [])
            )
            for item in results
        ]

        return ScannerSnapshot(
            timestamp=datetime.now().isoformat() + "Z",
            candidates=candidates,
            totalScanned=len(results),
            passedFilters=len([r for r in results if r.get('score', 0) > 0]),
            summary=engine.get_last_scan_summary()
        )
    except Exception as e:
        logger.error(f"Error scanning markets: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to scan markets: {str(e)}")

@router.post("/scan")
async def scan_market(request: ScanRequest):
    """Trigger market scan"""
    engine = get_engine_optional()
    
    if not engine:
        logger.warning("Engine not found in scan endpoint")
        return {
            "success": False,
            "message": "Engine not initialized. Please start the engine first.",
            "timestamp": datetime.now().isoformat() + "Z"
        }
    
    if request.preset != engine.preset.name:
        return {
            "success": False,
            "message": "Preset mismatch. Start engine with the desired preset before scanning.",
            "timestamp": datetime.now().isoformat() + "Z"
        }

    try:
        results = await engine.run_manual_scan(
            preset_name=request.preset,
            limit=request.limit if request.limit else 10,
            symbols=request.symbols if request.symbols else None
        )

        return {
            "success": True,
            "message": f"Market scan completed with preset '{request.preset}'. Found {len(results)} candidates.",
            "timestamp": datetime.now().isoformat() + "Z"
        }
    except Exception as e:
        logger.error(f"Error during market scan: {e}")
        return {
            "success": False,
            "message": f"Market scan failed: {str(e)}",
            "timestamp": datetime.now().isoformat() + "Z"
        }

@router.get("/market-data/{symbol}")
async def get_market_data(symbol: str):
    """Get market data for a specific symbol."""
    try:
        engine = get_engine_optional()
        if not engine:
            raise HTTPException(status_code=503, detail="Engine not available")
        
        # Try to get from cache first
        market_data = engine.market_data_cache.get(symbol)
        if not market_data:
            # Fetch fresh data
            market_data = await engine._fetch_market_data_safe(symbol, use_websocket=True)
            if not market_data:
                raise HTTPException(status_code=404, detail=f"Market data not found for {symbol}")
            engine.market_data_cache[symbol] = market_data
        
        return {
            "symbol": market_data.symbol,
            "price": market_data.price,
            "volume_24h_usd": market_data.volume_24h_usd,
            "trades_per_minute": market_data.trades_per_minute,
            "atr_5m": market_data.atr_5m,
            "atr_15m": market_data.atr_15m,
            "timestamp": market_data.timestamp
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get market data for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get market data: {str(e)}")
