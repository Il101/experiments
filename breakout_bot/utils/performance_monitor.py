"""
Advanced performance monitoring for Breakout Bot Trading System.

This module provides comprehensive performance monitoring including:
- Real-time metrics collection
- Performance alerts
- Resource optimization recommendations
- Historical performance analysis
- Automatic scaling recommendations
"""

import time
import psutil
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, asdict
from collections import deque
import json
import logging

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetrics:
    """Performance metrics data structure."""
    timestamp: str
    cpu_percent: float
    memory_percent: float
    memory_used_mb: float
    memory_available_mb: float
    disk_usage_percent: float
    disk_free_gb: float
    network_io_bytes_sent: int
    network_io_bytes_recv: int
    process_count: int
    thread_count: int
    open_files: int
    load_average: List[float]
    trading_engine_state: Optional[str] = None
    active_positions: int = 0
    scan_candidates: int = 0
    api_requests_per_minute: float = 0.0
    websocket_connections: int = 0


@dataclass
class PerformanceAlert:
    """Performance alert data structure."""
    timestamp: str
    alert_type: str
    severity: str
    message: str
    metrics: PerformanceMetrics
    recommendation: str


class PerformanceMonitor:
    """Advanced performance monitoring system."""
    
    def __init__(self, check_interval: float = 5.0, max_history: int = 1000):
        self.check_interval = check_interval
        self.max_history = max_history
        self.metrics_history = deque(maxlen=max_history)
        self.alerts = deque(maxlen=100)
        self.running = False
        self.monitor_thread = None
        self.lock = threading.Lock()
        
        # Alert thresholds
        self.thresholds = {
            'cpu_percent': 80.0,
            'memory_percent': 85.0,
            'disk_usage_percent': 90.0,
            'load_average': 4.0,
            'api_requests_per_minute': 1000.0,
            'websocket_connections': 50
        }
        
        # Callbacks for external systems
        self.alert_callbacks: List[Callable[[PerformanceAlert], None]] = []
        
        # Performance optimization recommendations
        self.optimization_recommendations = []
    
    def start(self):
        """Start performance monitoring."""
        if self.running:
            return
        
        self.running = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        logger.info("Performance monitoring started")
    
    def stop(self):
        """Stop performance monitoring."""
        self.running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5.0)
        logger.info("Performance monitoring stopped")
    
    def _monitor_loop(self):
        """Main monitoring loop."""
        while self.running:
            try:
                metrics = self._collect_metrics()
                self._process_metrics(metrics)
                time.sleep(self.check_interval)
            except Exception as e:
                logger.error(f"Error in performance monitoring: {e}")
                time.sleep(self.check_interval)
    
    def _collect_metrics(self) -> PerformanceMetrics:
        """Collect current system metrics."""
        # System metrics
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        network = psutil.net_io_counters()
        
        # Process metrics
        process = psutil.Process()
        open_files = len(process.open_files()) if hasattr(process, 'open_files') else 0
        
        # Load average (Unix only)
        try:
            load_avg = list(psutil.getloadavg())
        except AttributeError:
            load_avg = [0.0, 0.0, 0.0]
        
        return PerformanceMetrics(
            timestamp=datetime.now().isoformat() + "Z",
            cpu_percent=cpu_percent,
            memory_percent=memory.percent,
            memory_used_mb=memory.used / (1024 * 1024),
            memory_available_mb=memory.available / (1024 * 1024),
            disk_usage_percent=disk.percent,
            disk_free_gb=disk.free / (1024 * 1024 * 1024),
            network_io_bytes_sent=network.bytes_sent,
            network_io_bytes_recv=network.bytes_recv,
            process_count=len(psutil.pids()),
            thread_count=psutil.thread_count(),
            open_files=open_files,
            load_average=load_avg
        )
    
    def _process_metrics(self, metrics: PerformanceMetrics):
        """Process collected metrics and check for alerts."""
        with self.lock:
            self.metrics_history.append(metrics)
            
            # Check for alerts
            self._check_alerts(metrics)
            
            # Update optimization recommendations
            self._update_optimization_recommendations(metrics)
    
    def _check_alerts(self, metrics: PerformanceMetrics):
        """Check metrics against thresholds and generate alerts."""
        alerts = []
        
        # CPU alert
        if metrics.cpu_percent > self.thresholds['cpu_percent']:
            alerts.append(PerformanceAlert(
                timestamp=metrics.timestamp,
                alert_type="HIGH_CPU",
                severity="WARNING" if metrics.cpu_percent < 90 else "CRITICAL",
                message=f"High CPU usage: {metrics.cpu_percent:.1f}%",
                metrics=metrics,
                recommendation="Consider reducing scan frequency or optimizing algorithms"
            ))
        
        # Memory alert
        if metrics.memory_percent > self.thresholds['memory_percent']:
            alerts.append(PerformanceAlert(
                timestamp=metrics.timestamp,
                alert_type="HIGH_MEMORY",
                severity="WARNING" if metrics.memory_percent < 95 else "CRITICAL",
                message=f"High memory usage: {metrics.memory_percent:.1f}%",
                metrics=metrics,
                recommendation="Consider clearing caches or reducing memory footprint"
            ))
        
        # Disk alert
        if metrics.disk_usage_percent > self.thresholds['disk_usage_percent']:
            alerts.append(PerformanceAlert(
                timestamp=metrics.timestamp,
                alert_type="HIGH_DISK",
                severity="WARNING" if metrics.disk_usage_percent < 95 else "CRITICAL",
                message=f"High disk usage: {metrics.disk_usage_percent:.1f}%",
                metrics=metrics,
                recommendation="Consider cleaning up logs or increasing disk space"
            ))
        
        # Load average alert
        if metrics.load_average and max(metrics.load_average) > self.thresholds['load_average']:
            alerts.append(PerformanceAlert(
                timestamp=metrics.timestamp,
                alert_type="HIGH_LOAD",
                severity="WARNING",
                message=f"High system load: {max(metrics.load_average):.2f}",
                metrics=metrics,
                recommendation="Consider reducing concurrent operations or scaling up"
            ))
        
        # Add alerts to history
        for alert in alerts:
            self.alerts.append(alert)
            logger.warning(f"Performance alert: {alert.message}")
            
            # Notify callbacks
            for callback in self.alert_callbacks:
                try:
                    callback(alert)
                except Exception as e:
                    logger.error(f"Error in alert callback: {e}")
    
    def _update_optimization_recommendations(self, metrics: PerformanceMetrics):
        """Update optimization recommendations based on metrics."""
        recommendations = []
        
        # Memory optimization
        if metrics.memory_percent > 70:
            recommendations.append({
                'type': 'MEMORY_OPTIMIZATION',
                'priority': 'HIGH' if metrics.memory_percent > 80 else 'MEDIUM',
                'message': 'Consider implementing memory optimization strategies',
                'suggestions': [
                    'Reduce cache sizes',
                    'Implement memory pooling',
                    'Use weak references for large objects',
                    'Clear unused data structures'
                ]
            })
        
        # CPU optimization
        if metrics.cpu_percent > 60:
            recommendations.append({
                'type': 'CPU_OPTIMIZATION',
                'priority': 'HIGH' if metrics.cpu_percent > 80 else 'MEDIUM',
                'message': 'Consider optimizing CPU-intensive operations',
                'suggestions': [
                    'Use async/await for I/O operations',
                    'Implement connection pooling',
                    'Cache frequently accessed data',
                    'Optimize algorithms'
                ]
            })
        
        # Network optimization
        if metrics.websocket_connections > 20:
            recommendations.append({
                'type': 'NETWORK_OPTIMIZATION',
                'priority': 'MEDIUM',
                'message': 'Consider optimizing network connections',
                'suggestions': [
                    'Implement connection pooling',
                    'Use keep-alive connections',
                    'Batch API requests',
                    'Implement request queuing'
                ]
            })
        
        self.optimization_recommendations = recommendations
    
    def get_current_metrics(self) -> Optional[PerformanceMetrics]:
        """Get current performance metrics."""
        with self.lock:
            return self.metrics_history[-1] if self.metrics_history else None
    
    def get_metrics_history(self, hours: int = 1) -> List[PerformanceMetrics]:
        """Get metrics history for specified hours."""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        with self.lock:
            return [
                metrics for metrics in self.metrics_history
                if datetime.fromisoformat(metrics.timestamp.replace('Z', '+00:00')) > cutoff_time
            ]
    
    def get_recent_alerts(self, count: int = 10) -> List[PerformanceAlert]:
        """Get recent performance alerts."""
        with self.lock:
            return list(self.alerts)[-count:]
    
    def get_optimization_recommendations(self) -> List[Dict[str, Any]]:
        """Get current optimization recommendations."""
        return self.optimization_recommendations
    
    def add_alert_callback(self, callback: Callable[[PerformanceAlert], None]):
        """Add alert callback function."""
        self.alert_callbacks.append(callback)
    
    def set_threshold(self, metric: str, value: float):
        """Set alert threshold for a metric."""
        if metric in self.thresholds:
            self.thresholds[metric] = value
            logger.info(f"Updated threshold for {metric}: {value}")
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary statistics."""
        with self.lock:
            if not self.metrics_history:
                return {}
            
            recent_metrics = list(self.metrics_history)[-100:]  # Last 100 measurements
            
            summary = {
                'cpu': {
                    'current': recent_metrics[-1].cpu_percent,
                    'average': sum(m.cpu_percent for m in recent_metrics) / len(recent_metrics),
                    'max': max(m.cpu_percent for m in recent_metrics),
                    'min': min(m.cpu_percent for m in recent_metrics)
                },
                'memory': {
                    'current_percent': recent_metrics[-1].memory_percent,
                    'current_mb': recent_metrics[-1].memory_used_mb,
                    'average_percent': sum(m.memory_percent for m in recent_metrics) / len(recent_metrics),
                    'max_percent': max(m.memory_percent for m in recent_metrics)
                },
                'disk': {
                    'current_percent': recent_metrics[-1].disk_usage_percent,
                    'free_gb': recent_metrics[-1].disk_free_gb
                },
                'alerts': {
                    'total': len(self.alerts),
                    'recent': len([a for a in self.alerts if 
                                 datetime.fromisoformat(a.timestamp.replace('Z', '+00:00')) > 
                                 datetime.now() - timedelta(hours=1)])
                },
                'recommendations': len(self.optimization_recommendations)
            }
            
            return summary
    
    def record_cycle(self, cycle_data: Dict[str, Any]):
        """Record trading cycle data for performance analysis."""
        with self.lock:
            # Add cycle-specific metrics to the current metrics
            if self.metrics_history:
                current_metrics = self.metrics_history[-1]
                # Update trading-specific fields
                current_metrics.trading_engine_state = cycle_data.get('state', 'unknown')
                current_metrics.active_positions = cycle_data.get('active_positions', 0)
                current_metrics.scan_candidates = cycle_data.get('scan_candidates', 0)
                current_metrics.api_requests_per_minute = cycle_data.get('api_requests_per_minute', 0.0)
                current_metrics.websocket_connections = cycle_data.get('websocket_connections', 0)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get current performance statistics (alias for get_performance_summary)."""
        return self.get_performance_summary()
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get system health status."""
        with self.lock:
            if not self.metrics_history:
                return {
                    'status': 'UNKNOWN',
                    'message': 'No metrics available',
                    'healthy': False
                }
            
            current_metrics = self.metrics_history[-1]
            recent_alerts = list(self.alerts)[-10:]  # Last 10 alerts
            
            # Determine health status based on current metrics and recent alerts
            health_issues = []
            
            if current_metrics.cpu_percent > self.thresholds['cpu_percent']:
                health_issues.append(f"High CPU usage: {current_metrics.cpu_percent:.1f}%")
            
            if current_metrics.memory_percent > self.thresholds['memory_percent']:
                health_issues.append(f"High memory usage: {current_metrics.memory_percent:.1f}%")
            
            if current_metrics.disk_usage_percent > self.thresholds['disk_usage_percent']:
                health_issues.append(f"High disk usage: {current_metrics.disk_usage_percent:.1f}%")
            
            # Check for recent critical alerts
            critical_alerts = [alert for alert in recent_alerts if alert.severity == 'CRITICAL']
            
            if critical_alerts:
                health_issues.append(f"{len(critical_alerts)} critical alerts in recent history")
            
            # Determine overall health status
            if not health_issues:
                status = 'HEALTHY'
                healthy = True
                message = 'All systems operating normally'
            elif len(health_issues) <= 2:
                status = 'WARNING'
                healthy = True
                message = 'Minor issues detected'
            else:
                status = 'CRITICAL'
                healthy = False
                message = 'Multiple critical issues detected'
            
            return {
                'status': status,
                'healthy': healthy,
                'message': message,
                'issues': health_issues,
                'current_metrics': {
                    'cpu_percent': current_metrics.cpu_percent,
                    'memory_percent': current_metrics.memory_percent,
                    'disk_usage_percent': current_metrics.disk_usage_percent,
                    'load_average': current_metrics.load_average
                },
                'recent_alerts_count': len(recent_alerts),
                'critical_alerts_count': len(critical_alerts)
            }


# Global performance monitor instance
_performance_monitor = None

def get_performance_monitor() -> PerformanceMonitor:
    """Get or create global performance monitor."""
    global _performance_monitor
    if _performance_monitor is None:
        _performance_monitor = PerformanceMonitor()
    return _performance_monitor
