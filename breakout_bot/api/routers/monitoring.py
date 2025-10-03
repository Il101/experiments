"""
Trading process monitoring API endpoints
"""

from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

from ..engine_manager import get_engine_optional
from ...utils.monitoring_manager import get_monitoring_manager
from ...data.monitoring import TradingSession, ProcessVisualization, RealTimeMetrics

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/sessions", response_model=List[Dict[str, Any]])
async def get_active_sessions():
    """Get all active trading sessions."""
    try:
        monitoring_manager = get_monitoring_manager()
        
        sessions = []
        # ✅ FIX: Фильтруем только активные сессии
        for session_id, session in monitoring_manager.active_sessions.items():
            # Пропускаем неактивные сессии
            if not session.is_active:
                continue
                
            session_data = {
                "session_id": session_id,
                "preset": session.preset,
                "start_time": session.start_time.isoformat(),
                "end_time": session.end_time.isoformat() if session.end_time else None,
                "status": session.status,
                "current_state": session.current_state,
                "is_active": session.is_active,
                "success_rate": session.success_rate,
                "total_duration_ms": session.total_duration_ms,
                "symbols_scanned": session.symbols_scanned,
                "candidates_found": session.candidates_found,
                "signals_generated": session.signals_generated,
                "positions_opened": session.positions_opened,
                "orders_executed": session.orders_executed
            }
            sessions.append(session_data)
        
        return sessions
        
    except Exception as e:
        logger.error(f"Error getting active sessions: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get sessions: {str(e)}")


@router.get("/sessions/{session_id}", response_model=Dict[str, Any])
async def get_session_details(session_id: str):
    """Get detailed information about a specific session."""
    try:
        monitoring_manager = get_monitoring_manager()
        
        if session_id not in monitoring_manager.active_sessions:
            raise HTTPException(status_code=404, detail="Session not found")
        
        session = monitoring_manager.active_sessions[session_id]
        checkpoints = list(monitoring_manager.session_checkpoints.get(session_id, []))
        
        # Convert checkpoints to dict format
        checkpoint_data = []
        for checkpoint in checkpoints:
            checkpoint_data.append({
                "id": checkpoint.id,
                "type": checkpoint.type.value,
                "status": checkpoint.status.value,
                "timestamp": checkpoint.timestamp.isoformat(),
                "duration_ms": checkpoint.duration_ms,
                "symbol": checkpoint.symbol,
                "message": checkpoint.message,
                "metrics": checkpoint.metrics,
                "data": checkpoint.data,
                "error": checkpoint.error
            })
        
        return {
            "session": {
                "session_id": session_id,
                "preset": session.preset,
                "start_time": session.start_time.isoformat(),
                "end_time": session.end_time.isoformat() if session.end_time else None,
                "status": session.status,
                "current_state": session.current_state,
                "is_active": session.is_active,
                "success_rate": session.success_rate,
                "total_duration_ms": session.total_duration_ms,
                "symbols_scanned": session.symbols_scanned,
                "candidates_found": session.candidates_found,
                "signals_generated": session.signals_generated,
                "positions_opened": session.positions_opened,
                "orders_executed": session.orders_executed
            },
            "checkpoints": checkpoint_data
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting session details: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get session details: {str(e)}")


@router.get("/sessions/{session_id}/visualization", response_model=ProcessVisualization)
async def get_session_visualization(session_id: str):
    """Get process visualization for a specific session."""
    try:
        monitoring_manager = get_monitoring_manager()
        
        visualization = monitoring_manager.get_session_visualization(session_id)
        if not visualization:
            raise HTTPException(status_code=404, detail="Session not found")
        
        return visualization
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting session visualization: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get visualization: {str(e)}")


@router.get("/metrics", response_model=RealTimeMetrics)
async def get_real_time_metrics():
    """Get current real-time metrics."""
    try:
        monitoring_manager = get_monitoring_manager()
        metrics = monitoring_manager.get_real_time_metrics()
        return metrics
        
    except Exception as e:
        logger.error(f"Error getting real-time metrics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get metrics: {str(e)}")


@router.get("/rate-limiter", response_model=Dict[str, Any])
async def get_rate_limiter_status():
    """Получить статус rate limiter для мониторинга API лимитов."""
    try:
        engine = get_engine_optional()
        if not engine:
            return {
                "status": "engine_not_running",
                "rate_limiter_active": False
            }
        
        # Получить статус от exchange client
        if hasattr(engine, 'exchange_client') and engine.exchange_client:
            rate_status = engine.exchange_client.get_rate_limiter_status()
            if rate_status:
                return {
                    "status": "active",
                    "rate_limiter_active": True,
                    "rate_limits": rate_status
                }
        
        return {
            "status": "not_configured", 
            "rate_limiter_active": False,
            "message": "Rate limiter не настроен для данной биржи"
        }
        
    except Exception as e:
        logger.error(f"Error getting rate limiter status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get rate limiter status: {str(e)}")


@router.post("/rate-limiter/reset")
async def reset_rate_limiter():
    """Сбросить rate limiter."""
    try:
        engine = get_engine_optional()
        if not engine:
            raise HTTPException(status_code=503, detail="Engine not available")
        
        # Сбросить rate limiter
        if hasattr(engine, 'exchange_client') and engine.exchange_client:
            engine.exchange_client.reset_rate_limiter()
            return {
                "status": "success",
                "message": "Rate limiter reset successfully"
            }
        
        return {
            "status": "not_configured",
            "message": "Rate limiter not available"
        }
        
    except Exception as e:
        logger.error(f"Error resetting rate limiter: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to reset rate limiter: {str(e)}")


@router.get("/state-machine/status", response_model=Dict[str, Any])
async def get_state_machine_status(session_id: Optional[str] = None):
    """Получить текущий статус state machine."""
    try:
        engine = get_engine_optional()
        if not engine:
            return {
                "current_state": "stopped",
                "previous_state": None,
                "is_terminal": True,
                "is_error": False,
                "is_trading_active": False,
                "valid_next_states": [],
                "transition_count": 0,
                "engine_available": False
            }
        
        # Получить статус от state machine
        if hasattr(engine, 'state_machine'):
            state_status = engine.state_machine.get_status()
            state_status["engine_available"] = True
            return state_status
        else:
            return {
                "current_state": "unknown",
                "previous_state": None,
                "is_terminal": False,
                "is_error": True,
                "is_trading_active": False,
                "valid_next_states": [],
                "transition_count": 0,
                "engine_available": True,
                "error": "State machine not available"
            }
        
    except Exception as e:
        logger.error(f"Error getting state machine status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get state machine status: {e}")


@router.get("/state-machine/transitions", response_model=List[Dict[str, Any]])
async def get_state_transitions(session_id: Optional[str] = None, limit: int = 20):
    """Получить историю переходов состояний."""
    try:
        engine = get_engine_optional()
        if not engine:
            return []
        
        # Получить историю переходов от state machine
        if hasattr(engine, 'state_machine'):
            transitions = engine.state_machine.get_transition_history(limit)
            return [
                {
                    "from_state": transition.from_state.value,
                    "to_state": transition.to_state.value,
                    "reason": transition.reason,
                    "timestamp": transition.timestamp,
                    "metadata": transition.metadata or {}
                }
                for transition in transitions
            ]
        else:
            return []
        
    except Exception as e:
        logger.error(f"Error getting state transitions: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get state transitions: {e}")


@router.get("/state-machine/performance", response_model=Dict[str, Any])
async def get_state_machine_performance(session_id: Optional[str] = None):
    """Получить метрики производительности state machine."""
    try:
        engine = get_engine_optional()
        if not engine:
            return {
                "status": "engine_not_available",
                "metrics": {}
            }
        
        # Получить метрики от state machine
        if hasattr(engine, 'state_machine'):
            transitions = engine.state_machine.get_transition_history(100)
            
            # Подсчитать время в каждом состоянии
            state_durations = {}
            state_counts = {}
            
            for i, transition in enumerate(transitions):
                state = transition.to_state.value
                state_counts[state] = state_counts.get(state, 0) + 1
                
                # Примерная длительность (в реальности нужно отслеживать время входа/выхода)
                if i > 0:
                    duration = transition.timestamp - transitions[i-1].timestamp
                    state_durations[state] = state_durations.get(state, 0) + duration
            
            return {
                "status": "success",
                "metrics": {
                    "total_transitions": len(transitions),
                    "state_counts": state_counts,
                    "state_durations_ms": state_durations,
                    "current_state": engine.state_machine.current_state.value,
                    "is_trading_active": engine.state_machine.is_trading_active(),
                    "is_error_state": engine.state_machine.is_error_state()
                }
            }
        else:
            return {
                "status": "state_machine_not_available",
                "metrics": {}
            }
        
    except Exception as e:
        logger.error(f"Error getting state machine performance: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get state machine performance: {e}")


@router.get("/sessions/{session_id}/summary", response_model=Dict[str, Any])
async def get_session_summary(session_id: str):
    """Get summary of a trading session."""
    try:
        monitoring_manager = get_monitoring_manager()
        
        summary = monitoring_manager.get_session_summary(session_id)
        if not summary:
            raise HTTPException(status_code=404, detail="Session not found")
        
        return summary
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting session summary: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get session summary: {str(e)}")


@router.post("/sessions/{session_id}/end")
async def end_session(session_id: str, status: str = "completed"):
    """End a trading session."""
    try:
        monitoring_manager = get_monitoring_manager()
        
        if session_id not in monitoring_manager.active_sessions:
            raise HTTPException(status_code=404, detail="Session not found")
        
        monitoring_manager.end_session(session_id, status)
        
        return {
            "success": True,
            "message": f"Session {session_id} ended with status '{status}'",
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error ending session: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to end session: {str(e)}")


@router.get("/checkpoints/{session_id}", response_model=List[Dict[str, Any]])
async def get_session_checkpoints(session_id: str, limit: int = 100):
    """Get checkpoints for a specific session."""
    try:
        monitoring_manager = get_monitoring_manager()
        
        if session_id not in monitoring_manager.session_checkpoints:
            raise HTTPException(status_code=404, detail="Session not found")
        
        checkpoints = list(monitoring_manager.session_checkpoints[session_id])
        
        # Limit results
        if limit > 0:
            checkpoints = checkpoints[-limit:]
        
        # Convert to dict format
        checkpoint_data = []
        for checkpoint in checkpoints:
            checkpoint_data.append({
                "id": checkpoint.id,
                "type": checkpoint.type.value,
                "status": checkpoint.status.value,
                "timestamp": checkpoint.timestamp.isoformat(),
                "duration_ms": checkpoint.duration_ms,
                "symbol": checkpoint.symbol,
                "message": checkpoint.message,
                "metrics": checkpoint.metrics,
                "data": checkpoint.data,
                "error": checkpoint.error
            })
        
        return checkpoint_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting session checkpoints: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get checkpoints: {str(e)}")


@router.get("/current-session")
async def get_current_session():
    """Get the current active session."""
    try:
        # ✅ IMPROVED: Get current session from monitoring manager, not engine
        monitoring_manager = get_monitoring_manager()
        
        if not monitoring_manager.current_session_id:
            return {"session_id": None, "message": "No active session"}
        
        session = monitoring_manager.active_sessions.get(monitoring_manager.current_session_id)
        
        if not session:
            return {"session_id": None, "message": "Session not found"}
        
        return {
            "session_id": monitoring_manager.current_session_id,
            "preset": session.preset,
            "status": session.status,
            "current_state": session.current_state,
            "start_time": session.start_time.isoformat(),
            "is_active": session.is_active
        }
        
    except Exception as e:
        logger.error(f"Error getting current session: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get current session: {str(e)}")


@router.post("/sessions/cleanup")
async def cleanup_sessions():
    """Manually cleanup all inactive sessions. Useful for debugging."""
    try:
        monitoring_manager = get_monitoring_manager()
        
        # Подсчитать неактивные сессии
        inactive_count = sum(1 for s in monitoring_manager.active_sessions.values() if not s.is_active)
        
        # Завершить и очистить все сессии
        monitoring_manager.end_all_sessions("Manual cleanup requested", cleanup=True)
        
        return {
            "success": True,
            "message": f"Cleaned up {inactive_count} inactive sessions",
            "remaining_sessions": len(monitoring_manager.active_sessions)
        }
        
    except Exception as e:
        logger.error(f"Error cleaning up sessions: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to cleanup sessions: {str(e)}")
