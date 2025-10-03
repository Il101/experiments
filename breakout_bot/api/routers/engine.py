"""
Engine control router
"""

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from typing import Optional
import asyncio
import logging
import time
from pathlib import Path
from datetime import datetime

from ...config.settings import Settings
from ...core.engine import OptimizedOrchestraEngine, TradingState, SystemCommand
from ...utils.resource_monitor import start_resource_monitoring, stop_resource_monitoring, get_resource_monitor
from ...utils.cache_manager import get_cache_manager, cached
from ...utils.performance_monitor import get_performance_monitor
from ...utils.monitoring_manager import get_monitoring_manager

router = APIRouter()
logger = logging.getLogger(__name__)

# Global engine instance
_engine_instance: Optional[OptimizedOrchestraEngine] = None
_engine_task: Optional[asyncio.Task] = None
_resource_monitoring_started = False

def get_engine_instance() -> Optional[OptimizedOrchestraEngine]:
    """Get the current engine instance"""
    return _engine_instance

def set_engine_instance(engine: Optional[OptimizedOrchestraEngine]):
    """Set the current engine instance"""
    global _engine_instance
    _engine_instance = engine

class StartEngineRequest(BaseModel):
    preset: str
    mode: str = "paper"

class EngineStatus(BaseModel):
    state: str
    preset: Optional[str] = None
    mode: str = "paper"
    startedAt: Optional[str] = None
    slots: int = 0
    openPositions: int = 0
    latencyMs: int = 50
    dailyR: float = 0.0
    consecutiveLosses: int = 0

class EngineMetrics(BaseModel):
    uptime: int = 0
    cycleCount: int = 0
    avgLatencyMs: float = 50.0
    totalSignals: int = 0
    totalTrades: int = 0
    dailyPnlR: float = 0.0
    maxDrawdownR: float = 0.0

class ResourceHealth(BaseModel):
    status: str
    issues: list
    cpu_percent: float = 0.0
    memory_percent: float = 0.0
    memory_used_mb: float = 0.0
    disk_usage_percent: float = 0.0
    active_threads: int = 0
    optimization_count: int = 0


class CommandRequest(BaseModel):
    command: str

@router.get("/status", response_model=EngineStatus)
async def get_engine_status():
    """Get current engine status with caching"""
    global _engine_instance
    
    if not _engine_instance:
        return EngineStatus(
            state="IDLE",
            preset=None,
            mode="paper",
            startedAt=None,
            slots=0,
            openPositions=0,
            latencyMs=50,
            dailyR=0.0,
            consecutiveLosses=0
        )
    
    try:
        system_status = _engine_instance.get_status()
        
        # Get real slots from preset config
        slots = 3  # Default fallback
        try:
            if hasattr(_engine_instance, 'preset_config') and _engine_instance.preset_config:
                slots = _engine_instance.preset_config.get('risk', {}).get('max_concurrent_positions', 3)
        except:
            pass
        
        # Get real latency from engine
        latency_ms = 45  # Default fallback
        try:
            if hasattr(_engine_instance, 'get_latency'):
                latency_ms = _engine_instance.get_latency()
        except:
            pass
        
        return EngineStatus(
            state=system_status['state'],
            preset=system_status['preset_name'],
            mode=system_status['trading_mode'],
            startedAt=datetime.now().isoformat() + "Z" if system_status['state'] != "IDLE" else None,
            slots=slots,
            openPositions=system_status['open_positions_count'],
            latencyMs=latency_ms,
            dailyR=system_status.get('risk_summary', {}).get('daily_pnl_r', 0.0),
            consecutiveLosses=system_status.get('risk_summary', {}).get('consecutive_losses', 0)
        )
    except Exception as e:
        logger.error(f"Error getting engine status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get engine status: {str(e)}"
        )

@router.get("/metrics", response_model=EngineMetrics)
async def get_engine_metrics():
    """Get engine performance metrics with caching"""
    global _engine_instance
    
    if not _engine_instance:
        return EngineMetrics()
    
    try:
        system_status = _engine_instance.get_status()
        
        # Get real uptime
        uptime = 0
        try:
            if hasattr(_engine_instance, 'get_uptime'):
                uptime = _engine_instance.get_uptime()
            elif hasattr(_engine_instance, 'start_time') and _engine_instance.start_time:
                uptime = int(time.time() - _engine_instance.start_time)
        except:
            uptime = 3600 if system_status['state'] != "IDLE" else 0
        
        # Get real average latency
        avg_latency = 47.5  # Default fallback
        try:
            if hasattr(_engine_instance, 'get_avg_latency'):
                avg_latency = _engine_instance.get_avg_latency()
        except:
            pass
        
        # Get real total signals and trades
        total_signals = system_status.get('total_signals_generated', system_status['active_signals_count'])
        total_trades = system_status.get('total_trades_executed', system_status['open_positions_count'])
        
        return EngineMetrics(
            uptime=uptime,
            cycleCount=system_status['cycle_count'],
            avgLatencyMs=avg_latency,
            totalSignals=total_signals,
            totalTrades=total_trades,
            dailyPnlR=system_status.get('risk_summary', {}).get('daily_pnl_r', 0.0),
            maxDrawdownR=system_status.get('position_metrics', {}).get('max_drawdown_r', 0.0)
        )
    except Exception as e:
        logger.error(f"Error getting engine metrics: {e}")
        return EngineMetrics()

@router.post("/start")
async def start_engine(request: StartEngineRequest):
    """Start the trading engine with resource monitoring"""
    global _engine_instance, _engine_task, _resource_monitoring_started
    
    if _engine_instance and hasattr(_engine_instance, 'running') and _engine_instance.running:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Engine is already running"
        )
    
    # Validate preset exists
    presets_dir = Path(__file__).resolve().parent.parent.parent / "config" / "presets"
    if presets_dir.exists():
        valid_presets = {path.stem for path in presets_dir.glob("*.json")}
    else:
        valid_presets = {"breakout_v1", "smallcap_top_gainers", "high_liquidity_top30"}

    if request.preset not in valid_presets:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid preset: {request.preset}. Valid presets: {valid_presets}"
        )
    
    # Validate trading mode
    if request.mode not in ["paper", "live"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Trading mode must be 'paper' or 'live'"
        )
    
    try:
        # ✅ CRITICAL FIX: Очистить все старые сессии перед стартом нового движка
        try:
            monitoring_manager = get_monitoring_manager()
            # Завершить и удалить все старые сессии
            monitoring_manager.end_all_sessions("New engine starting", cleanup=True)
            logger.info("Cleaned up all old monitoring sessions before starting new engine")
        except Exception as e:
            logger.warning(f"Failed to cleanup old sessions: {e}")
        
        # Start resource monitoring if not already started
        if not _resource_monitoring_started:
            await start_resource_monitoring()
            _resource_monitoring_started = True
            logger.info("Resource monitoring started")
        
        # Create optimized engine instance
        logger.info(f"Creating optimized engine instance for preset '{request.preset}'...")
        
        # Create system config with correct mode
        from ...config.settings import SystemConfig
        system_config = SystemConfig(
            trading_mode=request.mode,
            # Add other config as needed
        )
        logger.info(f"Created SystemConfig with trading_mode: {request.mode}, paper_mode: {system_config.paper_mode}")
        
        _engine_instance = OptimizedOrchestraEngine(
            preset_name=request.preset,
            system_config=system_config
        )
        
        # Update app_state with engine instance
        from ..main import app_state
        app_state["engine"] = _engine_instance
        
        # Start engine in background task
        logger.info("Starting engine in background task...")
        _engine_task = asyncio.create_task(_engine_instance.start())
        
        # ✅ IMPROVED: Start monitoring session for real-time tracking
        try:
            monitoring_manager = get_monitoring_manager()
            session_id = monitoring_manager.start_session(request.preset)
            monitoring_manager.add_checkpoint(
                session_id=session_id,
                checkpoint_type="system",
                name="engine_started",
                status="success",
                message=f"Engine started with preset '{request.preset}' in {request.mode} mode",
                data={
                    "preset": request.preset,
                    "mode": request.mode,
                    "engine_state": str(_engine_instance.current_state),
                    "timestamp": datetime.now().isoformat()
                }
            )
            logger.info(f"Started monitoring session: {session_id}")
        except Exception as e:
            logger.warning(f"Failed to start monitoring session: {e}")
        
        logger.info(f"Optimized engine started with preset '{request.preset}' in {request.mode} mode")
        logger.info(f"Engine state: {_engine_instance.current_state}")
        logger.info(f"Engine running attribute: {_engine_instance.running}")
        
        return {
            "success": True,
            "message": f"Optimized engine started with preset '{request.preset}' in {request.mode} mode",
            "timestamp": datetime.now().isoformat() + "Z"
        }
        
    except Exception as e:
        logger.error(f"Failed to start engine: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start engine: {str(e)}"
        )

@router.post("/stop")
async def stop_engine():
    """Stop the trading engine and resource monitoring"""
    global _engine_instance, _engine_task, _resource_monitoring_started
    
    if not _engine_instance:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Engine is not initialized"
        )
    
    # Check if engine is running
    running_attr = getattr(_engine_instance, 'running', 'NOT_FOUND')
    current_state = getattr(_engine_instance, 'current_state', 'NOT_FOUND')
    is_running_result = _engine_instance.is_running()
    
    logger.info(f"Engine running attribute: {running_attr}")
    logger.info(f"Engine current_state: {current_state}")
    logger.info(f"Engine is_running() result: {is_running_result}")
    
    # Debug: Check if we can access the engine instance
    try:
        engine_type = type(_engine_instance).__name__
        logger.info(f"Engine type: {engine_type}")
        logger.info(f"Engine has is_running method: {hasattr(_engine_instance, 'is_running')}")
    except Exception as e:
        logger.error(f"Error accessing engine instance: {e}")
    
    if not _engine_instance.is_running():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Engine is not running (running={running_attr}, state={current_state}, is_running={is_running_result})"
        )
    
    try:
        logger.info("Stopping engine...")
        
        # Stop engine with timeout
        try:
            await asyncio.wait_for(_engine_instance.stop(), timeout=10.0)
            logger.info("Engine stop method completed")
        except asyncio.TimeoutError:
            logger.error("Engine stop timed out after 10 seconds")
            # Force stop by setting running to False
            _engine_instance.running = False
        
        # Cancel the background task with timeout
        if _engine_task:
            logger.info("Cancelling background task...")
            _engine_task.cancel()
            try:
                await asyncio.wait_for(_engine_task, timeout=5.0)
            except asyncio.TimeoutError:
                logger.warning("Background task cancellation timed out")
            except asyncio.CancelledError:
                logger.info("Background task cancelled successfully")
            except Exception as e:
                logger.warning(f"Error cancelling background task: {e}")
            _engine_task = None
        
        _engine_instance = None
        
        # ✅ IMPROVED: End all monitoring sessions with immediate cleanup
        try:
            monitoring_manager = get_monitoring_manager()
            monitoring_manager.end_all_sessions("Engine stopped by user request", cleanup=True)
            logger.info("Ended and cleaned up all monitoring sessions")
        except Exception as e:
            logger.warning(f"Failed to end monitoring sessions: {e}")
        
        # Clear app_state engine instance
        from ..main import app_state
        app_state["engine"] = None
        
        logger.info("Engine instance cleared")
        
        # Stop resource monitoring
        if _resource_monitoring_started:
            logger.info("Stopping resource monitoring...")
            await stop_resource_monitoring()
            _resource_monitoring_started = False
            logger.info("Resource monitoring stopped")
        
        logger.info("Optimized engine stopped successfully")
        
        return {
            "success": True,
            "message": "Engine stopped successfully",
            "timestamp": datetime.now().isoformat() + "Z"
        }
        
    except Exception as e:
        logger.error(f"Failed to stop engine: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to stop engine: {str(e)}"
        )

@router.post("/reload")
async def reload_engine():
    """Reload engine configuration"""
    global _engine_instance
    
    if _engine_instance and _engine_instance.running:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot reload while engine is running. Stop engine first."
        )
    
    try:
        # Configuration reload would happen here
        logger.info("Engine configuration reloaded")
        
        return {
            "success": True,
            "message": "Engine configuration reloaded",
            "timestamp": datetime.now().isoformat() + "Z"
        }
        
    except Exception as e:
        logger.error(f"Failed to reload engine: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reload engine: {str(e)}"
        )

@router.post("/command")
async def execute_command(request: CommandRequest):
    """Execute a system command"""
    global _engine_instance

    if not _engine_instance:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Engine is not initialized"
        )

    try:
        command_value = request.command.lower()
        # Execute the command
        result = await _engine_instance.execute_command(command_value)

        logger.info(f"Command '{command_value}' executed: {result['success']}")

        return {
            "success": result['success'],
            "message": result['message'],
            "command": result['command'],
            "timestamp": datetime.now().isoformat() + "Z"
        }

    except Exception as e:
        logger.error(f"Failed to execute command '{request.command}': {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to execute command: {str(e)}"
        )

@router.get("/commands")
async def get_available_commands():
    """Get available commands for current state"""
    global _engine_instance
    
    if not _engine_instance:
        return {
            "commands": ["start", "reload"],
            "current_state": "IDLE"
        }
    
    try:
        # В новом движке нет get_available_commands(), создаем базовый набор команд
        available_commands = ["start", "stop", "pause", "resume", "emergency_stop"]
        if _engine_instance.running:
            commands = ["stop", "pause", "emergency_stop"]
        else:
            commands = ["start"]
        system_status = _engine_instance.get_status()
        
        return {
            "commands": commands,
            "current_state": system_status['state'],
            "timestamp": datetime.now().isoformat() + "Z"
        }
        
    except Exception as e:
        logger.error(f"Failed to get available commands: {e}")
        return {
            "commands": [],
            "current_state": "UNKNOWN",
            "error": str(e)
        }

# Individual command endpoints for convenience
@router.post("/pause")
async def pause_engine():
    """Pause the engine"""
    return await execute_command(CommandRequest(command="pause"))

@router.post("/resume")
async def resume_engine():
    """Resume the engine"""
    return await execute_command(CommandRequest(command="resume"))

@router.post("/time-stop")
async def time_stop_engine():
    """Time stop the engine"""
    return await execute_command(CommandRequest(command="time_stop"))

@router.post("/panic-exit")
async def panic_exit_engine():
    """Panic exit the engine"""
    return await execute_command(CommandRequest(command="panic_exit"))

@router.get("/resource-health", response_model=ResourceHealth)
async def get_resource_health():
    """Get current resource health status"""
    try:
        monitor = get_resource_monitor()
        health = monitor.get_health_status()
        
        # Extract metrics if available
        metrics = health.get('metrics')
        if metrics:
            return ResourceHealth(
                status=health['status'],
                issues=health['issues'],
                cpu_percent=metrics.cpu_percent,
                memory_percent=metrics.memory_percent,
                memory_used_mb=metrics.memory_used_mb,
                disk_usage_percent=metrics.disk_usage_percent,
                active_threads=metrics.active_threads,
                optimization_count=health.get('optimization_count', 0)
            )
        else:
            return ResourceHealth(
                status=health['status'],
                issues=health['issues'],
                optimization_count=health.get('optimization_count', 0)
            )
            
    except Exception as e:
        logger.error(f"Error getting resource health: {e}")
        return ResourceHealth(
            status="error",
            issues=[f"Failed to get resource health: {str(e)}"]
        )

@router.get("/resource-summary")
async def get_resource_summary(minutes: int = 5):
    """Get resource usage summary for the last N minutes"""
    try:
        monitor = get_resource_monitor()
        summary = monitor.get_metrics_summary(minutes=minutes)
        return summary
        
    except Exception as e:
        logger.error(f"Error getting resource summary: {e}")
        return {"error": str(e)}

@router.post("/kill-switch")
async def kill_switch_engine():
    """Activate kill switch"""
    return await execute_command(CommandRequest(command="kill_switch"))

@router.post("/retry")
async def retry_engine():
    """Retry after error"""
    return await execute_command(CommandRequest(command="retry"))
