"""
WebSocket handler for real-time updates
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import List, Dict, Any
import json
import asyncio
import time
import logging
from breakout_bot.api.routers.engine import get_engine_instance

router = APIRouter()
logger = logging.getLogger(__name__)

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        try:
            await websocket.send_text(message)
        except Exception as e:
            print(f"Failed to send message to WebSocket: {e}")
            self.disconnect(websocket)

    async def broadcast(self, message: str):
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception as e:
                print(f"Failed to broadcast to WebSocket: {e}")
                disconnected.append(connection)
        
        # Remove disconnected clients
        for connection in disconnected:
            self.disconnect(connection)

manager = ConnectionManager()

def create_websocket_message(event_type: str, data: Any) -> str:
    """Create standardized WebSocket message"""
    return json.dumps({
        "type": event_type,
        "ts": int(time.time() * 1000),
        "data": data
    })

@router.websocket("/")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    
    # Send initial heartbeat
    await manager.send_personal_message(
        create_websocket_message("HEARTBEAT", {"latencyMs": 45}),
        websocket
    )
    
    try:
        while True:
            # Send heartbeat every 30 seconds
            await asyncio.sleep(30)
            
            await manager.send_personal_message(
                create_websocket_message("HEARTBEAT", {"latencyMs": 45}),
                websocket
            )
            
                    # Send real-time engine updates
            try:
                engine = get_engine_instance()
                
                if engine:
                    # Send engine state update
                    await manager.send_personal_message(
                        create_websocket_message("ENGINE_UPDATE", {
                            "state": engine.current_state.value if hasattr(engine, 'current_state') else "unknown",
                            "running": engine.is_running() if hasattr(engine, 'is_running') else False,
                            "timestamp": int(time.time() * 1000)
                        }),
                        websocket
                    )
                    
                    # Send scan results if available
                    scan_results = engine.get_last_scan_results() if hasattr(engine, 'get_last_scan_results') else []
                    if scan_results:
                        await manager.send_personal_message(
                            create_websocket_message("SCAN_RESULT", {
                                "results": scan_results,
                                "timestamp": int(time.time() * 1000)
                            }),
                            websocket
                        )
                    
                    # Send signals if available
                    signals = engine.get_active_signals() if hasattr(engine, 'get_active_signals') else []
                    if signals:
                        await manager.send_personal_message(
                            create_websocket_message("SIGNAL", {
                                "signals": [signal.dict() if hasattr(signal, 'dict') else str(signal) for signal in signals],
                                "timestamp": int(time.time() * 1000)
                            }),
                            websocket
                        )
                    
                    # Send positions if available
                    positions = engine.get_positions() if hasattr(engine, 'get_positions') else []
                    if positions:
                        await manager.send_personal_message(
                            create_websocket_message("POSITION_UPDATE", {
                                "positions": [pos.dict() if hasattr(pos, 'dict') else str(pos) for pos in positions],
                                "timestamp": int(time.time() * 1000)
                            }),
                            websocket
                        )
                    
                    # Send orders if available
                    orders = engine.get_orders() if hasattr(engine, 'get_orders') else []
                    if orders:
                        await manager.send_personal_message(
                            create_websocket_message("ORDER_UPDATE", {
                                "orders": [order.dict() if hasattr(order, 'dict') else str(order) for order in orders],
                                "timestamp": int(time.time() * 1000)
                            }),
                            websocket
                        )
                    
                    # Send order events (placed, updated, canceled)
                    order_events = engine.get_recent_order_events() if hasattr(engine, 'get_recent_order_events') else []
                    for event in order_events:
                        status = event.get('status', 'UNKNOWN').upper()
                        if status == 'FILLED':
                            event_type = "ORDER_UPDATED"
                        elif status == 'CANCELLED':
                            event_type = "ORDER_CANCELED"
                        else:
                            event_type = "ORDER_PLACED"
                        
                        await manager.send_personal_message(
                            create_websocket_message(event_type, {
                                "order": event,
                                "timestamp": int(time.time() * 1000)
                            }),
                            websocket
                        )
                    
                    # Send position events (open, update, close)
                    position_events = engine.get_recent_position_events() if hasattr(engine, 'get_recent_position_events') else []
                    for event in position_events:
                        action = event.get('action', 'UNKNOWN').upper()
                        if action == 'OPENED':
                            event_type = "POSITION_OPEN"
                        elif action == 'CLOSED':
                            event_type = "POSITION_CLOSE"
                        else:
                            event_type = "POSITION_UPDATE"
                        
                        await manager.send_personal_message(
                            create_websocket_message(event_type, {
                                "position": event,
                                "timestamp": int(time.time() * 1000)
                            }),
                            websocket
                        )
                    
                    # New: Send density updates
                    # TODO: Integrate with DensityDetector
                    # density_events = engine.get_recent_density_events() if hasattr(engine, 'get_recent_density_events') else []
                    # for event in density_events:
                    #     await manager.send_personal_message(
                    #         create_websocket_message("DENSITY_UPDATE", {
                    #             "symbol": event.get('symbol'),
                    #             "price": event.get('price'),
                    #             "side": event.get('side'),
                    #             "strength": event.get('strength'),
                    #             "eaten_ratio": event.get('eaten_ratio'),
                    #             "timestamp": int(time.time() * 1000)
                    #         }),
                    #         websocket
                    #     )
                    
                    # New: Send activity updates
                    # TODO: Integrate with ActivityTracker
                    # activity_data = engine.get_activity_snapshot() if hasattr(engine, 'get_activity_snapshot') else {}
                    # if activity_data:
                    #     await manager.send_personal_message(
                    #         create_websocket_message("ACTIVITY", {
                    #             "symbol": activity_data.get('symbol'),
                    #             "tpm": activity_data.get('tpm'),
                    #             "tps": activity_data.get('tps'),
                    #             "vol_delta": activity_data.get('vol_delta'),
                    #             "activity_index": activity_data.get('activity_index'),
                    #             "is_dropping": activity_data.get('is_dropping', False),
                    #             "timestamp": int(time.time() * 1000)
                    #         }),
                    #         websocket
                    #     )
                        
            except Exception as e:
                logger.warning(f"Error sending engine updates: {e}")
            
    except WebSocketDisconnect:
        manager.disconnect(websocket)
