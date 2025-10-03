// ============================================
// PATCH 002: Fix Type Mismatches (Backend)
// ============================================
// Priority: P0 - Critical
// Impact: Fixes data corruption and runtime errors
// Files: backend/api/routers/trading.py

"""
Trading data router (positions, orders) - FIXED VERSION
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from ..engine_manager import get_engine_optional

router = APIRouter()

# ✅ FIXED: Match frontend expectations
class Position(BaseModel):
    id: str
    symbol: str
    side: str
    entry: float
    sl: float
    size: float      # ✅ Changed from 'qty'
    mode: str        # ✅ Changed from 'strategy'
    openedAt: str
    pnlR: Optional[float] = None
    pnlUsd: Optional[float] = None
    unrealizedPnlR: Optional[float] = None
    unrealizedPnlUsd: Optional[float] = None

# ✅ FIXED: Match frontend expectations
class Order(BaseModel):
    id: str
    symbol: str
    side: str
    type: str        # ✅ Changed from 'order_type'
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
        return []
    
    try:
        positions_data = engine.get_positions()
        
        positions = []
        for pos in positions_data:
            opened_at = pos.timestamps.get('opened_at', 0)
            opened_at_str = datetime.fromtimestamp(opened_at / 1000).isoformat() + "Z" if opened_at else datetime.now().isoformat() + "Z"
            
            # ✅ FIXED: Use correct field names
            positions.append(Position(
                id=pos.id,
                symbol=pos.symbol,
                side=pos.side,
                entry=pos.entry,
                sl=pos.sl,
                size=pos.qty,           # Internal: qty -> External: size
                mode=pos.strategy,      # Internal: strategy -> External: mode
                openedAt=opened_at_str,
                pnlR=pos.pnl_r,
                pnlUsd=pos.pnl_usd,
                unrealizedPnlR=pos.pnl_r,
                unrealizedPnlUsd=pos.pnl_usd
            ))
        
        return positions
    except Exception as e:
        return []


@router.get("/orders", response_model=List[Order])
async def get_orders():
    """Get all orders"""
    engine = get_engine_optional()
    
    if not engine:
        return []
    
    try:
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

            # ✅ FIXED: Use correct field names
            orders.append(Order(
                id=order_dict.get('id', ''),
                symbol=order_dict.get('symbol', ''),
                side=order_dict.get('side', 'buy'),
                type=order_dict.get('order_type', 'market'),  # Map to 'type'
                qty=order_dict.get('qty', 0.0),
                price=order_dict.get('price'),
                status=order_dict.get('status', 'open'),
                createdAt=_format_ts(created_at) or datetime.now().isoformat() + "Z",
                filledAt=_format_ts(filled_at),
                fees=order_dict.get('fees_usd')
            ))

        return orders
    except Exception as e:
        return []


# ============================================
// ALTERNATIVE: Add mapping layer in frontend
// ============================================
// File: frontend/src/api/adapters/position.adapter.ts (NEW)

import type { Position } from '../types';

interface BackendPosition {
  id: string;
  symbol: string;
  side: string;
  entry: number;
  sl: number;
  qty: number;           // Backend uses 'qty'
  strategy: string;      // Backend uses 'strategy'
  openedAt: string;
  pnl_r?: number;
  pnl_usd?: number;
}

export function adaptBackendPosition(backendPos: BackendPosition): Position {
  return {
    id: backendPos.id,
    symbol: backendPos.symbol,
    side: backendPos.side as 'long' | 'short',
    entry: backendPos.entry,
    sl: backendPos.sl,
    size: backendPos.qty,                    // ✅ Map qty -> size
    mode: backendPos.strategy,               // ✅ Map strategy -> mode
    openedAt: backendPos.openedAt,
    pnlR: backendPos.pnl_r,
    pnlUsd: backendPos.pnl_usd,
    unrealizedPnlR: backendPos.pnl_r,
    unrealizedPnlUsd: backendPos.pnl_usd
  };
}

// File: frontend/src/api/adapters/order.adapter.ts (NEW)

import type { Order } from '../types';

interface BackendOrder {
  id: string;
  symbol: string;
  side: string;
  order_type: string;    // Backend uses 'order_type'
  qty: number;
  price?: number;
  status: string;
  createdAt: string;
  filledAt?: string;
  fees?: number;
}

export function adaptBackendOrder(backendOrder: BackendOrder): Order {
  return {
    id: backendOrder.id,
    symbol: backendOrder.symbol,
    side: backendOrder.side as 'buy' | 'sell',
    type: backendOrder.order_type,           // ✅ Map order_type -> type
    qty: backendOrder.qty,
    price: backendOrder.price,
    status: backendOrder.status as 'pending' | 'open' | 'filled' | 'cancelled' | 'rejected',
    createdAt: backendOrder.createdAt,
    filledAt: backendOrder.filledAt,
    fees: backendOrder.fees
  };
}

// File: frontend/src/api/endpoints.ts (MODIFIED)

import { adaptBackendPosition } from './adapters/position.adapter';
import { adaptBackendOrder } from './adapters/order.adapter';

export const tradingApi = {
  getPositions: async (): Promise<Position[]> => {
    const raw = await apiClient.get<any[]>('/api/trading/positions');
    return raw.map(adaptBackendPosition);  // ✅ Apply adapter
  },
  
  getPosition: async (id: string): Promise<Position> => {
    const raw = await apiClient.get<any>(`/api/trading/positions/${id}`);
    return adaptBackendPosition(raw);      // ✅ Apply adapter
  },
  
  getOrders: async (): Promise<Order[]> => {
    const raw = await apiClient.get<any[]>('/api/trading/orders');
    return raw.map(adaptBackendOrder);     // ✅ Apply adapter
  },
  
  // ... rest unchanged
};

// ============================================
// Installation:
// 
// OPTION 1 (Recommended): Update backend
// 1. Update backend/api/routers/trading.py with new field names
// 2. Test API endpoints return correct field names
// 3. Restart backend server
// 4. Verify frontend receives correct data
//
// OPTION 2: Add frontend adapters
// 1. Create frontend/src/api/adapters/ directory
// 2. Create position.adapter.ts and order.adapter.ts
// 3. Update frontend/src/api/endpoints.ts to use adapters
// 4. Test data mapping works correctly
//
// Testing:
// - Fetch positions and verify 'size' and 'mode' fields exist
// - Fetch orders and verify 'type' field exists
// - Check TypeScript compilation has no errors
