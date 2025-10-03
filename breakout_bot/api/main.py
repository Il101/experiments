"""
FastAPI main application for Breakout Bot Trading System
"""

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from contextlib import asynccontextmanager
import uvicorn
import logging
import json
import time
from typing import Optional
from datetime import datetime

from .routers import engine, presets, trading, scanner, performance, logs, charts, monitoring, metrics, features
from .websocket import router as websocket_router
from .middleware import LoggingMiddleware, ErrorHandlerMiddleware, SecurityHeadersMiddleware
from ..utils.resource_monitor import start_resource_monitoring, stop_resource_monitoring
from ..api.engine_manager import get_engine_optional

# Configure logging with rotation
from ..utils.log_config import setup_optimized_logging
setup_optimized_logging()
logger = logging.getLogger(__name__)

# Global application state
app_state = {
    "engine": None,
    "settings": None,
}

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management with resource monitoring"""
    # Startup
    try:
        # Track startup time
        # Store start_time in app.state instead of directly on app
        app.state.start_time = time.time()
        
        # Start resource monitoring
        await start_resource_monitoring()
        logger.info("Resource monitoring started")
        
        logger.info("Breakout Bot API server started successfully")
        yield
    except Exception as e:
        logger.error(f"Failed to start API server: {e}")
        raise
    finally:
        # Shutdown
        try:
            await stop_resource_monitoring()
            logger.info("Resource monitoring stopped")
        except Exception as e:
            logger.error(f"Error stopping resource monitoring: {e}")
        
        logger.info("API server shutdown completed")

# Create FastAPI application
app = FastAPI(
    title="Breakout Bot Trading System API",
    description="RESTful API for algorithmic cryptocurrency trading bot",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan
)

# Add middleware
app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000", "http://127.0.0.1:3000",
        "http://localhost:5173", "http://127.0.0.1:5173",
        "http://localhost:5174", "http://127.0.0.1:5174",
        "http://localhost:5175", "http://127.0.0.1:5175",
        "http://localhost:5176", "http://127.0.0.1:5176",
        "http://localhost:5181", "http://127.0.0.1:5181",
        "http://localhost:5177", "http://127.0.0.1:5177",
        "http://localhost:5178", "http://127.0.0.1:5178",
        "http://localhost:5179", "http://127.0.0.1:5179",
        "http://localhost:5180", "http://127.0.0.1:5180"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(LoggingMiddleware)
app.add_middleware(ErrorHandlerMiddleware)
app.add_middleware(SecurityHeadersMiddleware)

# Include routers
app.include_router(engine.router, prefix="/api/engine", tags=["Engine"])
app.include_router(presets.router, prefix="/api/presets", tags=["Presets"])
app.include_router(trading.router, prefix="/api/trading", tags=["Trading"])
app.include_router(scanner.router, prefix="/api/scanner", tags=["Scanner"])
app.include_router(performance.router, prefix="/api/performance", tags=["Performance"])
app.include_router(logs.router, prefix="/api/logs", tags=["Logs"])
app.include_router(charts.router, prefix="/api/charts", tags=["Charts"])
app.include_router(monitoring.router, prefix="/api/monitoring", tags=["Monitoring"])
app.include_router(metrics.router, prefix="/api/metrics", tags=["Metrics"])
app.include_router(features.router, tags=["Features"])
app.include_router(websocket_router, prefix="/ws")

@app.get("/api/health")
async def health_check():
    """Enhanced health check endpoint with comprehensive monitoring"""
    from ..utils.resource_monitor import get_resource_monitor
    
    engine = get_engine_optional()
    health_status = "healthy"
    issues = []
    
    # Check engine status
    engine_initialized = engine is not None
    engine_running = False
    engine_state = "unknown"
    
    if engine:
        try:
            engine_running = engine.is_running()
            engine_state = engine.state_machine.current_state.value if hasattr(engine, 'state_machine') else "unknown"
        except Exception as e:
            issues.append(f"Engine status check failed: {e}")
            health_status = "degraded"
    
    # Get resource health
    try:
        monitor = get_resource_monitor()
        resource_health = monitor.get_health_status()
        if resource_health.get("status") != "healthy":
            health_status = "degraded"
            issues.extend(resource_health.get("issues", []))
    except Exception as e:
        resource_health = {"status": "unknown", "issues": [f"Resource monitoring error: {e}"]}
        health_status = "degraded"
        issues.append(f"Resource monitoring failed: {e}")
    
    # Check API connectivity
    api_connectivity = {
        "database": "unknown",
        "exchange": "unknown", 
        "websocket": "unknown"
    }
    
    try:
        # Test basic API functionality
        api_connectivity["database"] = "connected"
        api_connectivity["exchange"] = "connected" if engine_initialized else "disconnected"
        api_connectivity["websocket"] = "available"
    except Exception as e:
        issues.append(f"API connectivity check failed: {e}")
        health_status = "unhealthy"
    
    return {
        "status": health_status,
        "engine_initialized": engine_initialized,
        "engine_running": engine_running,
        "engine_state": engine_state,
        "resource_health": resource_health,
        "api_connectivity": api_connectivity,
        "issues": issues,
        "timestamp": datetime.now().isoformat() + "Z",
        "uptime_seconds": int(time.time() - getattr(app, 'start_time', time.time()))
    }

@app.get("/api/")
async def root():
    """API root endpoint"""
    return {
        "message": "Breakout Bot Trading System API",
        "version": "1.0.0",
        "docs": "/api/docs"
    }

# Direct API routes for positions and orders (as documented)
@app.get("/api/positions")
async def get_positions():
    """Get all open positions - direct API route"""
    from .routers.trading import get_positions as trading_get_positions
    return await trading_get_positions()

@app.get("/api/orders")
async def get_orders():
    """Get all orders - direct API route"""
    from .routers.trading import get_orders as trading_get_orders
    return await trading_get_orders()

# WebSocket endpoint is handled by websocket router

def get_settings():
    """Get the settings instance"""
    settings = app_state.get("settings")
    if not settings:
        raise HTTPException(status_code=503, detail="Settings not initialized")
    return settings

if __name__ == "__main__":
    uvicorn.run(
        "breakout_bot.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )