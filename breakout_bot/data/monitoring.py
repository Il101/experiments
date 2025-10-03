"""
Trading process monitoring and visualization models
"""

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field


class CheckpointType(Enum):
    """Types of trading checkpoints."""
    SCAN_START = "scan_start"
    SCAN_COMPLETE = "scan_complete"
    LEVEL_BUILDING_START = "level_building_start"
    LEVEL_BUILDING_COMPLETE = "level_building_complete"
    SIGNAL_DETECTED = "signal_detected"
    SIGNAL_VALIDATED = "signal_validated"
    POSITION_SIZING = "position_sizing"
    ORDER_PLACED = "order_placed"
    ORDER_FILLED = "order_filled"
    POSITION_OPENED = "position_opened"
    STOP_LOSS_SET = "stop_loss_set"
    TAKE_PROFIT_SET = "take_profit_set"
    POSITION_MANAGED = "position_managed"
    POSITION_CLOSED = "position_closed"
    ERROR = "error"
    WARNING = "warning"


class CheckpointStatus(Enum):
    """Checkpoint execution status."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class TradingCheckpoint(BaseModel):
    """Individual trading checkpoint."""
    
    id: str = Field(..., description="Unique checkpoint ID")
    type: CheckpointType = Field(..., description="Checkpoint type")
    status: CheckpointStatus = Field(..., description="Execution status")
    timestamp: datetime = Field(..., description="Checkpoint timestamp")
    duration_ms: Optional[int] = Field(None, description="Duration in milliseconds")
    
    # Context data
    symbol: Optional[str] = Field(None, description="Trading symbol")
    preset: Optional[str] = Field(None, description="Trading preset")
    message: str = Field(..., description="Human readable message")
    
    # Metrics and data
    metrics: Dict[str, Any] = Field(default_factory=dict, description="Checkpoint metrics")
    data: Dict[str, Any] = Field(default_factory=dict, description="Additional data")
    
    # Error information
    error: Optional[str] = Field(None, description="Error message if failed")
    stack_trace: Optional[str] = Field(None, description="Stack trace if error")


class TradingSession(BaseModel):
    """Complete trading session with all checkpoints."""
    
    session_id: str = Field(..., description="Unique session ID")
    preset: str = Field(..., description="Trading preset used")
    start_time: datetime = Field(..., description="Session start time")
    end_time: Optional[datetime] = Field(None, description="Session end time")
    
    # Session status
    status: str = Field(..., description="Session status")
    current_state: str = Field(..., description="Current trading state")
    
    # Checkpoints
    checkpoints: List[TradingCheckpoint] = Field(default_factory=list, description="All checkpoints")
    
    # Summary metrics
    total_duration_ms: Optional[int] = Field(None, description="Total session duration")
    successful_checkpoints: int = Field(default=0, description="Number of successful checkpoints")
    failed_checkpoints: int = Field(default=0, description="Number of failed checkpoints")
    
    # Trading results
    symbols_scanned: int = Field(default=0, description="Number of symbols scanned")
    candidates_found: int = Field(default=0, description="Number of candidates found")
    signals_generated: int = Field(default=0, description="Number of signals generated")
    positions_opened: int = Field(default=0, description="Number of positions opened")
    orders_executed: int = Field(default=0, description="Number of orders executed")
    
    @property
    def is_active(self) -> bool:
        """Check if session is currently active."""
        return self.end_time is None
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate of checkpoints."""
        total = self.successful_checkpoints + self.failed_checkpoints
        return self.successful_checkpoints / total if total > 0 else 0.0


class ProcessVisualization(BaseModel):
    """Visual representation of trading process."""
    
    session_id: str = Field(..., description="Session ID")
    current_step: int = Field(..., description="Current step number")
    total_steps: int = Field(..., description="Total steps in process")
    
    # Process flow
    steps: List[Dict[str, Any]] = Field(..., description="Process steps with status")
    
    # Progress metrics
    progress_percentage: float = Field(..., description="Overall progress percentage")
    estimated_completion: Optional[datetime] = Field(None, description="Estimated completion time")
    
    # Current activity
    current_activity: str = Field(..., description="Current activity description")
    current_symbol: Optional[str] = Field(None, description="Current symbol being processed")
    
    # Performance metrics
    avg_step_duration_ms: float = Field(..., description="Average step duration")
    remaining_steps: int = Field(..., description="Number of remaining steps")


class RealTimeMetrics(BaseModel):
    """Real-time trading metrics."""
    
    timestamp: datetime = Field(..., description="Metrics timestamp")
    
    # System status
    engine_state: str = Field(..., description="Current engine state")
    is_running: bool = Field(..., description="Is engine running")
    
    # Performance
    cpu_usage: float = Field(..., description="CPU usage percentage")
    memory_usage: float = Field(..., description="Memory usage percentage")
    latency_ms: float = Field(..., description="Average latency in milliseconds")
    
    # Trading activity
    active_sessions: int = Field(..., description="Number of active sessions")
    positions_open: int = Field(..., description="Number of open positions")
    orders_pending: int = Field(..., description="Number of pending orders")
    
    # Market data
    markets_scanned: int = Field(..., description="Markets scanned in last cycle")
    candidates_found: int = Field(..., description="Candidates found in last cycle")
    signals_generated: int = Field(..., description="Signals generated in last cycle")
    
    # Risk metrics
    daily_pnl: float = Field(..., description="Daily P&L")
    max_drawdown: float = Field(..., description="Maximum drawdown")
    risk_utilization: float = Field(..., description="Risk utilization percentage")
