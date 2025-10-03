"""
Breakout Bot Trading System

A sophisticated algorithmic trading system for cryptocurrency range breakout trading.
"""

__version__ = "0.1.0"
__author__ = "Trading Team"
__email__ = "info@example.com"

# Core exports
from .data.models import Candle, L2Depth, Position, Signal
from .config.settings import get_preset

__all__ = [
    "Candle",
    "L2Depth", 
    "Position",
    "Signal",
    "get_preset",
]