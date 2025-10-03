"""
Enhanced logging system for Breakout Bot Trading System.

This module provides advanced logging capabilities including:
- Structured logging with context
- Performance metrics logging
- Error tracking and analysis
- Automatic log rotation
- Real-time monitoring integration
"""

import logging
import json
import time
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from enum import Enum
import threading
from collections import deque
import psutil
import os

# Register custom log levels
PERFORMANCE_LEVEL = 25  # Between INFO (20) and WARNING (30)
TRADE_LEVEL = 26
RISK_LEVEL = 27

logging.addLevelName(PERFORMANCE_LEVEL, "PERFORMANCE")
logging.addLevelName(TRADE_LEVEL, "TRADE")
logging.addLevelName(RISK_LEVEL, "RISK")


class LogLevel(Enum):
    """Enhanced log levels."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"
    PERFORMANCE = "PERFORMANCE"
    TRADE = "TRADE"
    RISK = "RISK"


@dataclass
class LogContext:
    """Context information for structured logging."""
    session_id: Optional[str] = None
    user_id: Optional[str] = None
    request_id: Optional[str] = None
    component: Optional[str] = None
    state: Optional[str] = None
    symbol: Optional[str] = None
    position_id: Optional[str] = None
    order_id: Optional[str] = None
    error_code: Optional[str] = None
    performance_metrics: Optional[Dict[str, float]] = None


@dataclass
class LogEntry:
    """Structured log entry."""
    timestamp: str
    level: str
    message: str
    context: LogContext
    data: Optional[Dict[str, Any]] = None
    stack_trace: Optional[str] = None


class EnhancedLogger:
    """Enhanced logger with structured logging and performance tracking."""
    
    def __init__(self, name: str, max_entries: int = 10000):
        self.name = name
        self.logger = logging.getLogger(name)
        self.max_entries = max_entries
        self.entries = deque(maxlen=max_entries)
        self.performance_metrics = {}
        self.error_counts = {}
        self.lock = threading.Lock()
        
        # Setup formatter
        self.formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # Setup console handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(self.formatter)
        self.logger.addHandler(console_handler)
        self.logger.setLevel(logging.INFO)
    
    def _create_log_entry(self, level: str, message: str, context: LogContext, 
                         data: Optional[Dict[str, Any]] = None, 
                         stack_trace: Optional[str] = None) -> LogEntry:
        """Create a structured log entry."""
        return LogEntry(
            timestamp=datetime.now().isoformat() + "Z",
            level=level,
            message=message,
            context=context,
            data=data,
            stack_trace=stack_trace
        )
    
    def _log(self, level: str, message: str, context: LogContext, 
             data: Optional[Dict[str, Any]] = None, 
             stack_trace: Optional[str] = None):
        """Internal logging method."""
        with self.lock:
            entry = self._create_log_entry(level, message, context, data, stack_trace)
            self.entries.append(entry)
            
            # Update error counts
            if level in ["ERROR", "CRITICAL"]:
                error_key = f"{context.component}_{context.error_code}" if context.error_code else context.component
                self.error_counts[error_key] = self.error_counts.get(error_key, 0) + 1
            
            # Log to standard logger
            log_message = f"[{context.component}] {message}"
            if context.symbol:
                log_message = f"[{context.symbol}] {log_message}"
            if context.position_id:
                log_message = f"[{context.position_id}] {log_message}"
            
            # Handle custom log levels
            if level == "PERFORMANCE":
                self.logger.log(PERFORMANCE_LEVEL, log_message)
            elif level == "TRADE":
                self.logger.log(TRADE_LEVEL, log_message)
            elif level == "RISK":
                self.logger.log(RISK_LEVEL, log_message)
            else:
                # Use standard logging levels
                getattr(self.logger, level.lower())(log_message)
    
    def debug(self, message: str, context: LogContext, data: Optional[Dict[str, Any]] = None):
        """Log debug message."""
        self._log("DEBUG", message, context, data)
    
    def info(self, message: str, context: LogContext, data: Optional[Dict[str, Any]] = None):
        """Log info message."""
        self._log("INFO", message, context, data)
    
    def warning(self, message: str, context: LogContext, data: Optional[Dict[str, Any]] = None):
        """Log warning message."""
        self._log("WARNING", message, context, data)
    
    def error(self, message: str, context: LogContext, data: Optional[Dict[str, Any]] = None, 
              stack_trace: Optional[str] = None):
        """Log error message."""
        self._log("ERROR", message, context, data, stack_trace)
    
    def critical(self, message: str, context: LogContext, data: Optional[Dict[str, Any]] = None, 
                 stack_trace: Optional[str] = None):
        """Log critical message."""
        self._log("CRITICAL", message, context, data, stack_trace)
    
    def performance(self, message: str, context: LogContext, metrics: Dict[str, float]):
        """Log performance metrics."""
        context.performance_metrics = metrics
        self._log("PERFORMANCE", message, context)
        
        # Update performance tracking
        with self.lock:
            for key, value in metrics.items():
                if key not in self.performance_metrics:
                    self.performance_metrics[key] = []
                self.performance_metrics[key].append(value)
    
    def trade(self, message: str, context: LogContext, trade_data: Dict[str, Any]):
        """Log trade-related message."""
        self._log("TRADE", message, context, trade_data)
    
    def risk(self, message: str, context: LogContext, risk_data: Dict[str, Any]):
        """Log risk-related message."""
        self._log("RISK", message, context, risk_data)
    
    def get_recent_entries(self, count: int = 100) -> List[LogEntry]:
        """Get recent log entries."""
        with self.lock:
            return list(self.entries)[-count:]
    
    def get_entries_by_level(self, level: str) -> List[LogEntry]:
        """Get log entries by level."""
        with self.lock:
            return [entry for entry in self.entries if entry.level == level]
    
    def get_error_summary(self) -> Dict[str, int]:
        """Get error count summary."""
        with self.lock:
            return dict(self.error_counts)
    
    def get_performance_summary(self) -> Dict[str, Dict[str, float]]:
        """Get performance metrics summary."""
        with self.lock:
            summary = {}
            for key, values in self.performance_metrics.items():
                if values:
                    summary[key] = {
                        'min': min(values),
                        'max': max(values),
                        'avg': sum(values) / len(values),
                        'count': len(values)
                    }
            return summary
    
    def clear_old_entries(self, max_age_hours: int = 24):
        """Clear entries older than specified hours."""
        cutoff_time = datetime.now().timestamp() - (max_age_hours * 3600)
        
        with self.lock:
            # Keep only recent entries
            recent_entries = []
            for entry in self.entries:
                entry_time = datetime.fromisoformat(entry.timestamp.replace('Z', '+00:00')).timestamp()
                if entry_time > cutoff_time:
                    recent_entries.append(entry)
            
            self.entries.clear()
            self.entries.extend(recent_entries)


class PerformanceTracker:
    """Track performance metrics for operations."""
    
    def __init__(self, logger: EnhancedLogger, operation_name: str):
        self.logger = logger
        self.operation_name = operation_name
        self.start_time = None
        self.context = LogContext(component=operation_name)
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.start_time:
            duration = time.time() - self.start_time
            
            # Get system metrics
            cpu_percent = psutil.cpu_percent()
            memory_percent = psutil.virtual_memory().percent
            
            metrics = {
                'duration_ms': duration * 1000,
                'cpu_percent': cpu_percent,
                'memory_percent': memory_percent
            }
            
            if hasattr(self.logger, 'performance'):
                self.logger.performance(
                    f"Operation '{self.operation_name}' completed",
                    self.context,
                    metrics
                )
            else:
                # Fallback for regular logger
                self.logger.info(f"Operation '{self.operation_name}' completed in {duration*1000:.2f}ms")


# Global logger instance
_global_logger = None

def get_enhanced_logger(name: str = "breakout_bot") -> EnhancedLogger:
    """Get or create global enhanced logger."""
    global _global_logger
    if _global_logger is None:
        _global_logger = EnhancedLogger(name)
    return _global_logger


def log_performance(operation_name: str):
    """Decorator for logging performance of functions."""
    def decorator(func):
        if asyncio.iscoroutinefunction(func):
            async def async_wrapper(*args, **kwargs):
                # Try to get logger from self.enhanced_logger if available
                if args and hasattr(args[0], 'enhanced_logger'):
                    logger = args[0].enhanced_logger
                else:
                    logger = get_enhanced_logger()
                with PerformanceTracker(logger, operation_name):
                    return await func(*args, **kwargs)
            return async_wrapper
        else:
            def sync_wrapper(*args, **kwargs):
                # Try to get logger from self.enhanced_logger if available
                if args and hasattr(args[0], 'enhanced_logger'):
                    logger = args[0].enhanced_logger
                else:
                    logger = get_enhanced_logger()
                with PerformanceTracker(logger, operation_name):
                    return func(*args, **kwargs)
            return sync_wrapper
    return decorator
