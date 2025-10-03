"""
Resource monitoring and optimization utilities for Breakout Bot Trading System.

This module provides real-time monitoring of CPU, memory, and disk usage
with automatic optimization and alerting capabilities.
"""

import asyncio
import psutil
import time
import logging
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import threading
import gc
import os
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class ResourceMetrics:
    """Resource usage metrics."""
    timestamp: float
    cpu_percent: float
    memory_percent: float
    memory_used_mb: float
    memory_available_mb: float
    disk_usage_percent: float
    disk_free_gb: float
    active_threads: int
    open_files: int
    network_connections: int


@dataclass
class ResourceLimits:
    """Resource usage limits and thresholds."""
    max_cpu_percent: float = 80.0
    max_memory_percent: float = 85.0
    max_memory_mb: float = 2048.0  # 2GB
    max_disk_percent: float = 90.0
    max_threads: int = 100
    max_open_files: int = 1000
    warning_cpu_percent: float = 70.0
    warning_memory_percent: float = 75.0
    warning_disk_percent: float = 80.0


@dataclass
class OptimizationAction:
    """Resource optimization action."""
    action_type: str  # 'gc', 'cache_clear', 'thread_cleanup', 'log_cleanup', 'alert'
    description: str
    priority: int  # 1=critical, 2=high, 3=medium, 4=low
    executed: bool = False
    timestamp: float = field(default_factory=time.time)


class ResourceMonitor:
    """Real-time resource monitoring and optimization system."""
    
    def __init__(self, 
                 limits: Optional[ResourceLimits] = None,
                 check_interval: float = 5.0,
                 enable_auto_optimization: bool = True,
                 max_history: int = 1000):
        self.limits = limits or ResourceLimits()
        self.check_interval = check_interval
        self.enable_auto_optimization = enable_auto_optimization
        
        # Monitoring state
        self.running = False
        self.monitor_task: Optional[asyncio.Task] = None
        self.metrics_history: List[ResourceMetrics] = []
        self.max_history = max_history  # Keep last N measurements
        
        # Optimization callbacks
        self.optimization_callbacks: List[Callable[[OptimizationAction], None]] = []
        
        # Alert thresholds
        self.alert_cooldown = 300  # 5 minutes between same alerts
        self.last_alerts: Dict[str, float] = {}
        
        # Performance tracking
        self.optimization_count = 0
        self.last_optimization = 0.0
        self._network_warning_logged = False
        
        logger.info("Resource monitor initialized")
    
    def add_optimization_callback(self, callback: Callable[[OptimizationAction], None]):
        """Add callback for optimization actions."""
        self.optimization_callbacks.append(callback)
    
    async def start(self):
        """Start resource monitoring."""
        if self.running:
            logger.warning("Resource monitor already running")
            return
        
        self.running = True
        self.monitor_task = asyncio.create_task(self._monitor_loop())
        logger.info("Resource monitoring started")
    
    async def stop(self):
        """Stop resource monitoring."""
        if not self.running:
            return
        
        self.running = False
        if self.monitor_task:
            self.monitor_task.cancel()
            try:
                await self.monitor_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Resource monitoring stopped")
    
    async def _monitor_loop(self):
        """Main monitoring loop."""
        while self.running:
            try:
                # Collect current metrics
                metrics = self._collect_metrics()
                self._add_metrics(metrics)
                
                # Check for optimization needs
                if self.enable_auto_optimization:
                    await self._check_and_optimize(metrics)
                
                # Wait for next check
                await asyncio.sleep(self.check_interval)
                
            except Exception as e:
                logger.error(f"Error in resource monitoring loop: {e}")
                await asyncio.sleep(self.check_interval)
    
    def _add_metrics(self, metrics: ResourceMetrics):
        """Add metrics to history with automatic trimming."""
        self.metrics_history.append(metrics)
        if len(self.metrics_history) > self.max_history:
            self.metrics_history = self.metrics_history[-self.max_history:]

    def _collect_metrics(self) -> ResourceMetrics:
        """Collect current resource metrics."""
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=0.1)
            
            # Memory usage
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            memory_used_mb = memory.used / (1024 * 1024)
            memory_available_mb = memory.available / (1024 * 1024)
            
            # Disk usage
            disk = psutil.disk_usage('/')
            disk_usage_percent = (disk.used / disk.total) * 100
            disk_free_gb = disk.free / (1024 * 1024 * 1024)
            
            # Process info
            process = psutil.Process()
            active_threads = process.num_threads()
            open_files = len(process.open_files())
            
            network_connections = 0
            try:
                network_connections = len(psutil.net_connections())
            except Exception as net_err:
                if not self._network_warning_logged:
                    logger.debug(f"Unable to collect network connections: {net_err}")
                    self._network_warning_logged = True

            return ResourceMetrics(
                timestamp=time.time(),
                cpu_percent=cpu_percent,
                memory_percent=memory_percent,
                memory_used_mb=memory_used_mb,
                memory_available_mb=memory_available_mb,
                disk_usage_percent=disk_usage_percent,
                disk_free_gb=disk_free_gb,
                active_threads=active_threads,
                open_files=open_files,
                network_connections=network_connections
            )
            
        except Exception as e:
            logger.error(f"Error collecting resource metrics: {e}")
            # Return default metrics on error
            return ResourceMetrics(
                timestamp=time.time(),
                cpu_percent=0.0,
                memory_percent=0.0,
                memory_used_mb=0.0,
                memory_available_mb=0.0,
                disk_usage_percent=0.0,
                disk_free_gb=0.0,
                active_threads=0,
                open_files=0,
                network_connections=0
            )
    
    async def _check_and_optimize(self, metrics: ResourceMetrics):
        """Check metrics and perform optimizations if needed."""
        actions = []
        
        # Check CPU usage
        if metrics.cpu_percent > self.limits.max_cpu_percent:
            actions.append(OptimizationAction(
                action_type='cpu_alert',
                description=f"High CPU usage: {metrics.cpu_percent:.1f}%",
                priority=1
            ))
        elif metrics.cpu_percent > self.limits.warning_cpu_percent:
            actions.append(OptimizationAction(
                action_type='cpu_warning',
                description=f"Elevated CPU usage: {metrics.cpu_percent:.1f}%",
                priority=3
            ))
        
        # Check memory usage
        if metrics.memory_percent > self.limits.max_memory_percent:
            actions.append(OptimizationAction(
                action_type='memory_alert',
                description=f"High memory usage: {metrics.memory_percent:.1f}% ({metrics.memory_used_mb:.0f}MB)",
                priority=1
            ))
            # Trigger garbage collection
            actions.append(OptimizationAction(
                action_type='gc',
                description="Triggering garbage collection due to high memory usage",
                priority=1
            ))
        elif metrics.memory_percent > self.limits.warning_memory_percent:
            actions.append(OptimizationAction(
                action_type='memory_warning',
                description=f"Elevated memory usage: {metrics.memory_percent:.1f}%",
                priority=3
            ))
        
        # Check disk usage
        if metrics.disk_usage_percent > self.limits.max_disk_percent:
            actions.append(OptimizationAction(
                action_type='disk_alert',
                description=f"High disk usage: {metrics.disk_usage_percent:.1f}%",
                priority=1
            ))
            # Trigger log cleanup
            actions.append(OptimizationAction(
                action_type='log_cleanup',
                description="Triggering log cleanup due to high disk usage",
                priority=1
            ))
        elif metrics.disk_usage_percent > self.limits.warning_disk_percent:
            actions.append(OptimizationAction(
                action_type='disk_warning',
                description=f"Elevated disk usage: {metrics.disk_usage_percent:.1f}%",
                priority=3
            ))
        
        # Check thread count
        if metrics.active_threads > self.limits.max_threads:
            actions.append(OptimizationAction(
                action_type='thread_alert',
                description=f"High thread count: {metrics.active_threads}",
                priority=2
            ))
        
        # Check open files
        if metrics.open_files > self.limits.max_open_files:
            actions.append(OptimizationAction(
                action_type='files_alert',
                description=f"High open file count: {metrics.open_files}",
                priority=2
            ))
        
        # Execute optimization actions
        for action in actions:
            await self._execute_optimization(action)
    
    async def _execute_optimization(self, action: OptimizationAction):
        """Execute an optimization action."""
        try:
            # Check cooldown for alerts
            if action.action_type.endswith('_alert') or action.action_type.endswith('_warning'):
                if action.action_type in self.last_alerts:
                    if time.time() - self.last_alerts[action.action_type] < self.alert_cooldown:
                        return
                self.last_alerts[action.action_type] = time.time()
            
            # Execute action based on type
            if action.action_type == 'gc':
                await self._trigger_garbage_collection()
                action.executed = True
                
            elif action.action_type == 'cache_clear':
                await self._clear_caches()
                action.executed = True
                
            elif action.action_type == 'log_cleanup':
                await self._cleanup_logs()
                action.executed = True
                
            elif action.action_type == 'thread_cleanup':
                await self._cleanup_threads()
                action.executed = True
            
            # Log the action
            if action.priority <= 2:  # Critical or high priority
                logger.warning(f"Resource optimization: {action.description}")
            else:
                logger.info(f"Resource optimization: {action.description}")
            
            # Notify callbacks
            for callback in self.optimization_callbacks:
                try:
                    callback(action)
                except Exception as e:
                    logger.error(f"Error in optimization callback: {e}")
            
            self.optimization_count += 1
            self.last_optimization = time.time()
            
        except Exception as e:
            logger.error(f"Error executing optimization action {action.action_type}: {e}")
    
    async def _trigger_garbage_collection(self):
        """Trigger garbage collection."""
        try:
            # Force garbage collection
            collected = gc.collect()
            logger.debug(f"Garbage collection freed {collected} objects")
        except Exception as e:
            logger.error(f"Error during garbage collection: {e}")
    
    async def _clear_caches(self):
        """Clear various caches."""
        try:
            # Clear indicator cache if available
            from ..indicators.technical import clear_indicator_cache
            clear_indicator_cache()
            logger.debug("Indicator cache cleared")
        except Exception as e:
            logger.error(f"Error clearing caches: {e}")
    
    async def _cleanup_logs(self):
        """Cleanup old log files."""
        try:
            # This would be implemented based on your logging setup
            # For now, just log the action
            logger.info("Log cleanup triggered")
        except Exception as e:
            logger.error(f"Error during log cleanup: {e}")
    
    async def _cleanup_threads(self):
        """Cleanup idle threads."""
        try:
            # This would be implemented based on your thread pool setup
            logger.info("Thread cleanup triggered")
        except Exception as e:
            logger.error(f"Error during thread cleanup: {e}")
    
    def get_current_metrics(self) -> Optional[ResourceMetrics]:
        """Get the most recent resource metrics."""
        if not self.metrics_history:
            return None
        return self.metrics_history[-1]
    
    def get_metrics_summary(self, minutes: int = 5) -> Dict[str, Any]:
        """Get resource metrics summary for the last N minutes."""
        if not self.metrics_history:
            return {}
        
        cutoff_time = time.time() - (minutes * 60)
        recent_metrics = [m for m in self.metrics_history if m.timestamp >= cutoff_time]
        
        if not recent_metrics:
            return {}
        
        # Calculate averages and peaks
        cpu_values = [m.cpu_percent for m in recent_metrics]
        memory_values = [m.memory_percent for m in recent_metrics]
        disk_values = [m.disk_usage_percent for m in recent_metrics]
        
        return {
            'period_minutes': minutes,
            'sample_count': len(recent_metrics),
            'cpu': {
                'avg': sum(cpu_values) / len(cpu_values),
                'max': max(cpu_values),
                'min': min(cpu_values)
            },
            'memory': {
                'avg_percent': sum(memory_values) / len(memory_values),
                'max_percent': max(memory_values),
                'min_percent': min(memory_values),
                'current_mb': recent_metrics[-1].memory_used_mb
            },
            'disk': {
                'avg_percent': sum(disk_values) / len(disk_values),
                'max_percent': max(disk_values),
                'min_percent': min(disk_values),
                'free_gb': recent_metrics[-1].disk_free_gb
            },
            'threads': {
                'current': recent_metrics[-1].active_threads,
                'max': max(m.active_threads for m in recent_metrics)
            },
            'optimization_count': self.optimization_count,
            'last_optimization': self.last_optimization
        }
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get overall system health status."""
        current = self.get_current_metrics()
        if not current:
            return {'status': 'unknown', 'message': 'No metrics available'}
        
        issues = []
        status = 'healthy'
        
        # Check for critical issues
        if current.cpu_percent > self.limits.max_cpu_percent:
            issues.append(f"High CPU usage: {current.cpu_percent:.1f}%")
            status = 'critical'
        
        if current.memory_percent > self.limits.max_memory_percent:
            issues.append(f"High memory usage: {current.memory_percent:.1f}%")
            status = 'critical'
        
        if current.disk_usage_percent > self.limits.max_disk_percent:
            issues.append(f"High disk usage: {current.disk_usage_percent:.1f}%")
            status = 'critical'
        
        # Check for warnings
        if current.cpu_percent > self.limits.warning_cpu_percent:
            issues.append(f"Elevated CPU usage: {current.cpu_percent:.1f}%")
            if status == 'healthy':
                status = 'warning'
        
        if current.memory_percent > self.limits.warning_memory_percent:
            issues.append(f"Elevated memory usage: {current.memory_percent:.1f}%")
            if status == 'healthy':
                status = 'warning'
        
        return {
            'status': status,
            'issues': issues,
            'metrics': current,
            'optimization_count': self.optimization_count,
            'uptime_seconds': time.time() - (self.metrics_history[0].timestamp if self.metrics_history else time.time())
        }


# Global resource monitor instance
_resource_monitor: Optional[ResourceMonitor] = None


def get_resource_monitor() -> ResourceMonitor:
    """Get the global resource monitor instance."""
    global _resource_monitor
    if _resource_monitor is None:
        _resource_monitor = ResourceMonitor()
    return _resource_monitor


async def start_resource_monitoring():
    """Start global resource monitoring."""
    monitor = get_resource_monitor()
    await monitor.start()


async def stop_resource_monitoring():
    """Stop global resource monitoring."""
    monitor = get_resource_monitor()
    await monitor.stop()


def get_system_health() -> Dict[str, Any]:
    """Get current system health status."""
    monitor = get_resource_monitor()
    return monitor.get_health_status()
