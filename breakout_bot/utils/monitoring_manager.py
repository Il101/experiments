"""
Trading process monitoring manager
"""

import asyncio
import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import logging
from collections import deque
import psutil

from ..data.monitoring import (
    TradingCheckpoint, TradingSession, ProcessVisualization, 
    RealTimeMetrics, CheckpointType, CheckpointStatus
)

logger = logging.getLogger(__name__)


class MonitoringManager:
    """Manages trading process monitoring and visualization."""
    
    def __init__(self, max_sessions: int = 10, max_checkpoints_per_session: int = 1000):
        self.max_sessions = max_sessions
        self.max_checkpoints_per_session = max_checkpoints_per_session
        
        # Active sessions
        self.active_sessions: Dict[str, TradingSession] = {}
        self.session_checkpoints: Dict[str, deque] = {}
        
        # Process tracking
        self.current_session_id: Optional[str] = None
        self.step_timers: Dict[str, float] = {}
        
        # Real-time metrics
        self.metrics_history: deque = deque(maxlen=1000)
        self.last_metrics_update = 0
        
        logger.info("MonitoringManager initialized")
    
    def start_session(self, preset: str) -> str:
        """Start a new trading session."""
        session_id = str(uuid.uuid4())
        
        session = TradingSession(
            session_id=session_id,
            preset=preset,
            start_time=datetime.now(),
            status="active",
            current_state="initializing"
        )
        
        self.active_sessions[session_id] = session
        self.session_checkpoints[session_id] = deque(maxlen=self.max_checkpoints_per_session)
        self.current_session_id = session_id
        
        # Add initial checkpoint
        self.add_checkpoint(
            CheckpointType.SCAN_START,
            f"Started trading session with preset '{preset}'",
            session_id=session_id,
            data={"preset": preset}
        )
        
        logger.info(f"Started trading session {session_id} with preset {preset}")
        return session_id
    
    def end_session(self, session_id: str, status: str = "completed"):
        """End a trading session."""
        if session_id not in self.active_sessions:
            return
        
        session = self.active_sessions[session_id]
        session.end_time = datetime.now()
        session.status = status
        session.is_active = False  # Mark as inactive
        
        if session.start_time:
            duration = session.end_time - session.start_time
            session.total_duration_ms = int(duration.total_seconds() * 1000)
        
        # Calculate summary metrics
        checkpoints = list(self.session_checkpoints.get(session_id, []))
        session.successful_checkpoints = len([c for c in checkpoints if c.status == CheckpointStatus.COMPLETED])
        session.failed_checkpoints = len([c for c in checkpoints if c.status == CheckpointStatus.FAILED])
        
        # Count trading activities
        session.symbols_scanned = len([c for c in checkpoints if c.type == CheckpointType.SCAN_COMPLETE])
        session.candidates_found = len([c for c in checkpoints if c.type == CheckpointType.LEVEL_BUILDING_COMPLETE])
        session.signals_generated = len([c for c in checkpoints if c.type == CheckpointType.SIGNAL_DETECTED])
        session.positions_opened = len([c for c in checkpoints if c.type == CheckpointType.POSITION_OPENED])
        session.orders_executed = len([c for c in checkpoints if c.type == CheckpointType.ORDER_FILLED])
        
        # Clear current session if this was the active one
        if self.current_session_id == session_id:
            self.current_session_id = None
        
        logger.info(f"Ended trading session {session_id} with status {status}")
    
    def end_all_sessions(self, reason: str = "Engine stopped", cleanup: bool = True):
        """End all active sessions.
        
        Args:
            reason: Reason for ending sessions
            cleanup: If True, immediately remove inactive sessions from memory
        """
        sessions_to_end = list(self.active_sessions.keys())
        
        for session_id in sessions_to_end:
            self.end_session(session_id, "stopped")
            logger.info(f"Ended session {session_id} due to: {reason}")
        
        # Clear current session
        self.current_session_id = None
        
        # Immediately cleanup inactive sessions if requested
        if cleanup:
            inactive_sessions = [sid for sid, s in self.active_sessions.items() if not s.is_active]
            for session_id in inactive_sessions:
                del self.active_sessions[session_id]
                if session_id in self.session_checkpoints:
                    del self.session_checkpoints[session_id]
            logger.info(f"Cleaned up {len(inactive_sessions)} inactive sessions")
        
        logger.info(f"Ended {len(sessions_to_end)} active sessions")
    
    def add_checkpoint(
        self,
        checkpoint_type: CheckpointType,
        message: str,
        status: CheckpointStatus = CheckpointStatus.COMPLETED,
        session_id: Optional[str] = None,
        symbol: Optional[str] = None,
        metrics: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None
    ) -> str:
        """Add a checkpoint to the current or specified session."""
        if session_id is None:
            session_id = self.current_session_id
        
        if session_id is None:
            logger.warning("No active session for checkpoint")
            return ""
        
        if session_id not in self.active_sessions:
            logger.warning(f"Session {session_id} not found")
            return ""
        
        # Calculate duration if this is a completion checkpoint
        duration_ms = None
        checkpoint_key = f"{session_id}_{checkpoint_type.value}"
        
        if status == CheckpointStatus.COMPLETED and checkpoint_key in self.step_timers:
            start_time = self.step_timers[checkpoint_key]
            duration_ms = int((time.time() - start_time) * 1000)
            del self.step_timers[checkpoint_key]
        elif status == CheckpointStatus.IN_PROGRESS:
            self.step_timers[checkpoint_key] = time.time()
        
        # Create checkpoint
        checkpoint = TradingCheckpoint(
            id=str(uuid.uuid4()),
            type=checkpoint_type,
            status=status,
            timestamp=datetime.now(),
            duration_ms=duration_ms,
            symbol=symbol,
            preset=self.active_sessions[session_id].preset,
            message=message,
            metrics=metrics or {},
            data=data or {},
            error=error
        )
        
        # Add to session
        self.session_checkpoints[session_id].append(checkpoint)
        self.active_sessions[session_id].checkpoints.append(checkpoint)
        
        # Update session state based on checkpoint type
        self._update_session_state(session_id, checkpoint_type)
        
        logger.debug(f"Added checkpoint {checkpoint_type.value} for session {session_id}: {message}")
        return checkpoint.id
    
    def _update_session_state(self, session_id: str, checkpoint_type: CheckpointType):
        """Update session state based on checkpoint type."""
        if session_id not in self.active_sessions:
            return
        
        session = self.active_sessions[session_id]
        
        # Map checkpoint types to states
        state_mapping = {
            CheckpointType.SCAN_START: "scanning",
            CheckpointType.SCAN_COMPLETE: "level_building",
            CheckpointType.LEVEL_BUILDING_COMPLETE: "signal_wait",
            CheckpointType.SIGNAL_DETECTED: "execution",
            CheckpointType.POSITION_OPENED: "managing",
            CheckpointType.ERROR: "error"
        }
        
        if checkpoint_type in state_mapping:
            session.current_state = state_mapping[checkpoint_type]
        
        # Update real-time statistics
        self._update_session_statistics(session_id)
    
    def get_session_visualization(self, session_id: str) -> Optional[ProcessVisualization]:
        """Get process visualization for a session."""
        if session_id not in self.active_sessions:
            return None
        
        session = self.active_sessions[session_id]
        checkpoints = list(self.session_checkpoints.get(session_id, []))
        
        # Define process steps
        steps = [
            {"name": "Scanning Markets", "key": "scan", "status": "pending"},
            {"name": "Building Levels", "key": "levels", "status": "pending"},
            {"name": "Signal Detection", "key": "signals", "status": "pending"},
            {"name": "Position Sizing", "key": "sizing", "status": "pending"},
            {"name": "Order Execution", "key": "execution", "status": "pending"},
            {"name": "Position Management", "key": "management", "status": "pending"}
        ]
        
        # Update step statuses based on checkpoints
        step_status_map = {
            "scan": [CheckpointType.SCAN_START, CheckpointType.SCAN_COMPLETE],
            "levels": [CheckpointType.LEVEL_BUILDING_START, CheckpointType.LEVEL_BUILDING_COMPLETE],
            "signals": [CheckpointType.SIGNAL_DETECTED, CheckpointType.SIGNAL_VALIDATED],
            "sizing": [CheckpointType.POSITION_SIZING],
            "execution": [CheckpointType.ORDER_PLACED, CheckpointType.ORDER_FILLED],
            "management": [CheckpointType.POSITION_OPENED, CheckpointType.POSITION_MANAGED]
        }
        
        for step in steps:
            step_key = step["key"]
            step_types = step_status_map.get(step_key, [])
            
            # Check if any checkpoint of this type exists
            has_checkpoint = any(cp.type in step_types for cp in checkpoints)
            if has_checkpoint:
                # Check if completed
                completed_types = [t for t in step_types if t in [CheckpointType.SCAN_COMPLETE, CheckpointType.LEVEL_BUILDING_COMPLETE, CheckpointType.SIGNAL_VALIDATED, CheckpointType.ORDER_FILLED, CheckpointType.POSITION_OPENED]]
                is_completed = any(cp.type in completed_types and cp.status == CheckpointStatus.COMPLETED for cp in checkpoints)
                
                if is_completed:
                    step["status"] = "completed"
                else:
                    step["status"] = "in_progress"
        
        # Calculate progress
        completed_steps = len([s for s in steps if s["status"] == "completed"])
        progress_percentage = (completed_steps / len(steps)) * 100
        
        # Calculate average step duration
        completed_checkpoints = [c for c in checkpoints if c.duration_ms is not None]
        avg_duration = sum(c.duration_ms for c in completed_checkpoints) / len(completed_checkpoints) if completed_checkpoints else 0
        
        # Estimate completion
        remaining_steps = len([s for s in steps if s["status"] == "pending"])
        estimated_completion = None
        if remaining_steps > 0 and avg_duration > 0:
            estimated_ms = remaining_steps * avg_duration
            estimated_completion = datetime.now() + timedelta(milliseconds=estimated_ms)
        
        # Get current activity
        current_activity = "Idle"
        current_symbol = None
        
        if checkpoints:
            last_checkpoint = checkpoints[-1]
            current_activity = last_checkpoint.message
            current_symbol = last_checkpoint.symbol
        
        return ProcessVisualization(
            session_id=session_id,
            current_step=completed_steps + 1,
            total_steps=len(steps),
            steps=steps,
            progress_percentage=progress_percentage,
            estimated_completion=estimated_completion,
            current_activity=current_activity,
            current_symbol=current_symbol,
            avg_step_duration_ms=avg_duration,
            remaining_steps=remaining_steps
        )
    
    def get_real_time_metrics(self) -> RealTimeMetrics:
        """Get current real-time metrics."""
        now = time.time()
        
        # Update metrics only every 5 seconds
        if now - self.last_metrics_update < 5:
            if self.metrics_history:
                return self.metrics_history[-1]
        
        # Get system metrics
        cpu_usage = psutil.cpu_percent()
        memory = psutil.virtual_memory()
        memory_usage = memory.percent
        
        # Calculate latency (simplified)
        latency_ms = 50.0  # This would be calculated from actual measurements
        
        # Count active sessions and trading activity
        active_sessions = len([s for s in self.active_sessions.values() if s.is_active])
        
        # Count recent activity
        recent_checkpoints = []
        for checkpoints in self.session_checkpoints.values():
            recent_checkpoints.extend([c for c in checkpoints if (datetime.now() - c.timestamp).seconds < 60])
        
        markets_scanned = len([c for c in recent_checkpoints if c.type == CheckpointType.SCAN_COMPLETE])
        candidates_found = len([c for c in recent_checkpoints if c.type == CheckpointType.LEVEL_BUILDING_COMPLETE])
        signals_generated = len([c for c in recent_checkpoints if c.type == CheckpointType.SIGNAL_DETECTED])
        
        # Count positions and orders (simplified)
        positions_open = len([c for c in recent_checkpoints if c.type == CheckpointType.POSITION_OPENED])
        orders_pending = len([c for c in recent_checkpoints if c.type == CheckpointType.ORDER_PLACED])
        
        metrics = RealTimeMetrics(
            timestamp=datetime.now(),
            engine_state=self.active_sessions[self.current_session_id].current_state if self.current_session_id else "idle",
            is_running=self.current_session_id is not None,
            cpu_usage=cpu_usage,
            memory_usage=memory_usage,
            latency_ms=latency_ms,
            active_sessions=active_sessions,
            positions_open=positions_open,
            orders_pending=orders_pending,
            markets_scanned=markets_scanned,
            candidates_found=candidates_found,
            signals_generated=signals_generated,
            daily_pnl=0.0,  # This would be calculated from actual trading data
            max_drawdown=0.0,  # This would be calculated from actual trading data
            risk_utilization=0.0  # This would be calculated from actual risk data
        )
        
        self.metrics_history.append(metrics)
        self.last_metrics_update = now
        
        return metrics
    
    def get_session_summary(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get summary of a trading session."""
        if session_id not in self.active_sessions:
            return None
        
        session = self.active_sessions[session_id]
        checkpoints = list(self.session_checkpoints.get(session_id, []))
        
        # Group checkpoints by type
        checkpoint_counts = {}
        for checkpoint in checkpoints:
            checkpoint_type = checkpoint.type.value
            checkpoint_counts[checkpoint_type] = checkpoint_counts.get(checkpoint_type, 0) + 1
        
        # Calculate timing
        total_duration = session.total_duration_ms or 0
        avg_checkpoint_duration = 0
        if checkpoints:
            durations = [c.duration_ms for c in checkpoints if c.duration_ms is not None]
            avg_checkpoint_duration = sum(durations) / len(durations) if durations else 0
        
        return {
            "session_id": session_id,
            "preset": session.preset,
            "status": session.status,
            "duration_ms": total_duration,
            "success_rate": session.success_rate,
            "checkpoint_counts": checkpoint_counts,
            "avg_checkpoint_duration_ms": avg_checkpoint_duration,
            "symbols_scanned": session.symbols_scanned,
            "candidates_found": session.candidates_found,
            "signals_generated": session.signals_generated,
            "positions_opened": session.positions_opened,
            "orders_executed": session.orders_executed
        }
    
    def cleanup_old_sessions(self):
        """Clean up old completed sessions."""
        now = datetime.now()
        sessions_to_remove = []
        
        for session_id, session in self.active_sessions.items():
            if not session.is_active and session.end_time:
                # Remove sessions older than 1 hour
                if (now - session.end_time).total_seconds() > 3600:
                    sessions_to_remove.append(session_id)
        
        for session_id in sessions_to_remove:
            del self.active_sessions[session_id]
            if session_id in self.session_checkpoints:
                del self.session_checkpoints[session_id]
        
        if sessions_to_remove:
            logger.info(f"Cleaned up {len(sessions_to_remove)} old sessions")


    def _update_session_statistics(self, session_id: str):
        """Update session statistics in real-time."""
        if session_id not in self.active_sessions:
            return
        
        session = self.active_sessions[session_id]
        checkpoints = list(self.session_checkpoints.get(session_id, []))
        
        # Count trading activities
        session.symbols_scanned = len([c for c in checkpoints if c.type == CheckpointType.SCAN_COMPLETE])
        session.candidates_found = len([c for c in checkpoints if c.type == CheckpointType.LEVEL_BUILDING_COMPLETE])
        session.signals_generated = len([c for c in checkpoints if c.type == CheckpointType.SIGNAL_DETECTED])
        session.positions_opened = len([c for c in checkpoints if c.type == CheckpointType.POSITION_OPENED])
        session.orders_executed = len([c for c in checkpoints if c.type == CheckpointType.ORDER_FILLED])


# Global monitoring manager instance
_monitoring_manager = None

def get_monitoring_manager() -> MonitoringManager:
    """Get the global monitoring manager instance."""
    global _monitoring_manager
    if _monitoring_manager is None:
        _monitoring_manager = MonitoringManager()
    return _monitoring_manager
