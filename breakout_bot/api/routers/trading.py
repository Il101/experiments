"""
Trading data router (positions, orders)
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from ..engine_manager import get_engine_optional

router = APIRouter()

class Position(BaseModel):
    id: str
    symbol: str
    side: str
    entry: float
    sl: float
    size: float
    mode: str
    openedAt: str
    pnlR: Optional[float] = None
    pnlUsd: Optional[float] = None
    unrealizedPnlR: Optional[float] = None
    unrealizedPnlUsd: Optional[float] = None

class Order(BaseModel):
    id: str
    symbol: str
    side: str
    type: str
    qty: float
    price: Optional[float] = None
    status: str
    createdAt: str
    filledAt: Optional[str] = None
    fees: Optional[float] = None


@router.get("/positions", response_model=List[Position])
async def get_positions():
    """Get all open positions"""
    engine = get_engine_optional()
    
    if not engine:
        # Return empty list if engine is not running
        return []
    
    try:
        # Get real positions from engine
        positions_data = engine.get_positions()
        
        positions = []
        for pos in positions_data:
            # Map the data model fields to API response fields
            opened_at = pos.timestamps.get('opened_at', 0)
            opened_at_str = datetime.fromtimestamp(opened_at / 1000).isoformat() + "Z" if opened_at else datetime.now().isoformat() + "Z"
            
            positions.append(Position(
                id=pos.id,
                symbol=pos.symbol,
                side=pos.side,
                entry=pos.entry,
                sl=pos.sl,
                size=pos.qty,  # Map qty to size
                mode=pos.strategy,  # Map strategy to mode
                openedAt=opened_at_str,
                pnlR=pos.pnl_r,
                pnlUsd=pos.pnl_usd,
                unrealizedPnlR=pos.pnl_r,  # Use same as pnlR for now
                unrealizedPnlUsd=pos.pnl_usd  # Use same as pnlUsd for now
            ))
        
        return positions
    except Exception as e:
        # Return empty list on error
        return []

@router.get("/positions/{position_id}", response_model=Position)
async def get_position(position_id: str):
    """Get specific position"""
    try:
        engine = get_engine_optional()
        if not engine:
            raise HTTPException(status_code=404, detail="Position not found")
        # Get specific position from engine
        pos = engine.get_position(position_id)
        
        if not pos:
            raise HTTPException(status_code=404, detail=f"Position {position_id} not found")
        
        # Map the data model fields to API response fields
        opened_at = pos.timestamps.get('opened_at', 0)
        opened_at_str = datetime.fromtimestamp(opened_at / 1000).isoformat() + "Z" if opened_at else datetime.now().isoformat() + "Z"
        
        return Position(
            id=pos.id,
            symbol=pos.symbol,
            side=pos.side,
            entry=pos.entry,
            sl=pos.sl,
            size=pos.qty,  # Map qty to size
            mode=pos.strategy,  # Map strategy to mode
            openedAt=opened_at_str,
            pnlR=pos.pnl_r,
            pnlUsd=pos.pnl_usd,
            unrealizedPnlR=pos.pnl_r,  # Use same as pnlR for now
            unrealizedPnlUsd=pos.pnl_usd  # Use same as pnlUsd for now
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Position not found: {str(e)}")

@router.get("/orders", response_model=List[Order])
async def get_orders():
    """Get all orders"""
    engine = get_engine_optional()
    
    if not engine:
        # Return empty list if engine is not running
        return []
    
    try:
        # Get real orders from engine
        orders_data = engine.get_orders()

        orders = []
        for order in orders_data:
            if hasattr(order, 'model_dump'):
                order_dict = order.model_dump()
            else:
                order_dict = order

            timestamps = order_dict.get('timestamps', {})
            created_at = timestamps.get('created_at')
            filled_at = timestamps.get('filled_at')

            def _format_ts(ts):
                if not ts:
                    return None
                return datetime.fromtimestamp(ts / 1000).isoformat() + "Z"

            orders.append(Order(
                id=order_dict.get('id', ''),
                symbol=order_dict.get('symbol', ''),
                side=order_dict.get('side', 'buy'),
                type=order_dict.get('order_type', 'market'),
                qty=order_dict.get('qty', 0.0),
                price=order_dict.get('price'),
                status=order_dict.get('status', 'open'),
                createdAt=_format_ts(created_at) or datetime.now().isoformat() + "Z",
                filledAt=_format_ts(filled_at),
                fees=order_dict.get('fees_usd')
            ))

        return orders
    except Exception as e:
        # Return empty list on error
        return []

@router.delete("/orders/{order_id}")
async def cancel_order(order_id: str):
    """Cancel specific order"""
    try:
        engine = get_engine_optional()
        if not engine:
            raise HTTPException(status_code=404, detail="Position not found")
        # Cancel real order through engine
        success = await engine.cancel_order(order_id)

        if not success:
            raise HTTPException(status_code=500, detail=f"Failed to cancel order {order_id}")

        return {
            "success": True,
            "message": f"Order {order_id} canceled successfully",
            "timestamp": datetime.now().isoformat() + "Z"
        }
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except HTTPException:
        # Re-raise HTTP exceptions (like 503 for uninitialized engine)
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to cancel order: {str(e)}")
