"""
Engine manager for API
"""

from fastapi import HTTPException
from typing import Optional

def get_engine():
    """Get the trading engine instance from the engine router"""
    # Import here to avoid circular imports
    from .routers.engine import _engine_instance
    
    if not _engine_instance:
        raise HTTPException(status_code=503, detail="Trading engine not initialized. Please start the engine first.")
    return _engine_instance

def get_engine_optional():
    """Get the trading engine instance if available, otherwise return None"""
    # Import here to avoid circular imports
    from .routers.engine import _engine_instance
    return _engine_instance