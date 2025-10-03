#!/usr/bin/env python3
"""
Debug script to test engine status
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'breakout_bot'))

from breakout_bot.core.engine import OptimizedOrchestraEngine
from breakout_bot.config.settings import SystemConfig

def test_engine_status():
    """Test engine status method"""
    try:
        # Create system config
        system_config = SystemConfig(
            trading_mode="paper",
            exchange="bybit"
        )
        
        # Create engine
        engine = OptimizedOrchestraEngine("breakout_v1", system_config)
        
        print("Engine created successfully")
        
        # Try to get system status
        try:
            status = engine.get_system_status()
            print("System status retrieved successfully")
            print(f"Status keys: {list(status.keys())}")
            
            # Check for coroutines
            for key, value in status.items():
                if hasattr(value, '__await__'):
                    print(f"WARNING: {key} is a coroutine: {type(value)}")
                elif hasattr(value, '__len__'):
                    try:
                        length = len(value)
                        print(f"{key}: {type(value)} with length {length}")
                    except Exception as e:
                        print(f"ERROR getting length of {key}: {e}")
                        print(f"Value type: {type(value)}")
                        print(f"Value: {value}")
        except Exception as e:
            print(f"Error getting system status: {type(e).__name__}: {str(e)}")
            
    except Exception as e:
        print(f"Error creating engine: {type(e).__name__}: {str(e)}")

if __name__ == "__main__":
    test_engine_status()
