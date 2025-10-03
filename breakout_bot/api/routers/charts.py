"""
Charts data router
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List
from datetime import datetime, timedelta
from ..engine_manager import get_engine_optional

router = APIRouter()

class Candle(BaseModel):
    time: int
    open: float
    high: float
    low: float
    close: float
    volume: float

class Level(BaseModel):
    price: float
    type: str  # "support" or "resistance"
    strength: float
    timestamp: str

@router.get("/candles", response_model=List[Candle])
async def get_candles(symbol: str, timeframe: str = "15m"):
    """Get candlestick data for symbol"""
    try:
        engine = get_engine_optional()
        if not engine:
            return []
        # Get real candle data from engine/exchange
        candle_data = engine.get_candle_data(symbol, timeframe)
        
        candles = []
        for candle in candle_data:
            candles.append(Candle(
                time=candle['time'],
                open=candle['open'],
                high=candle['high'],
                low=candle['low'],
                close=candle['close'],
                volume=candle['volume']
            ))
        
        return candles
    except HTTPException:
        # Re-raise HTTP exceptions (like 503 for uninitialized engine)
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get candle data: {str(e)}")

@router.get("/levels/{symbol}", response_model=List[Level])
async def get_levels(symbol: str):
    """Get support/resistance levels for symbol"""
    try:
        engine = get_engine_optional()
        if not engine:
            return []
        # Get real support/resistance levels from engine
        levels_data = engine.get_support_resistance_levels(symbol)
        
        levels = []
        for level in levels_data:
            levels.append(Level(
                price=level['price'],
                type=level['type'],
                strength=level['strength'],
                timestamp=level['timestamp']
            ))
        
        return levels
    except HTTPException:
        # Re-raise HTTP exceptions (like 503 for uninitialized engine)
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get levels: {str(e)}")