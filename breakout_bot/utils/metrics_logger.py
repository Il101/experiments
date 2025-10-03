"""
Enhanced metrics logger for detailed performance tracking
"""

import time
import logging
import json
from typing import Dict, Any, Optional, List
from datetime import datetime
from collections import defaultdict, deque
from dataclasses import dataclass, asdict
import threading
import psutil
import os

@dataclass
class MetricPoint:
    """Single metric data point"""
    timestamp: float
    value: float
    tags: Dict[str, str]
    metadata: Dict[str, Any]

@dataclass
class PerformanceMetrics:
    """Performance metrics summary"""
    cpu_percent: float
    memory_percent: float
    memory_used_mb: float
    disk_usage_percent: float
    active_threads: int
    open_files: int
    network_connections: int
    timestamp: float

class MetricsLogger:
    """Enhanced logger with metrics collection and performance tracking"""
    
    def __init__(self, name: str = "breakout_bot", max_metrics: int = 10000):
        self.logger = logging.getLogger(name)
        self.max_metrics = max_metrics
        self.metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=max_metrics))
        self.performance_history: deque = deque(maxlen=1000)
        self.lock = threading.Lock()
        
        # Setup logging
        self._setup_logging()
        
        # Start performance monitoring
        self._start_performance_monitoring()
    
    def _setup_logging(self):
        """Setup enhanced logging configuration"""
        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
        )
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        
        # File handler for detailed logs
        file_handler = logging.FileHandler('logs/metrics.log')
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        
        # Add handlers
        self.logger.addHandler(console_handler)
        self.logger.addHandler(file_handler)
        self.logger.setLevel(logging.DEBUG)
    
    def _start_performance_monitoring(self):
        """Start background performance monitoring"""
        def monitor_performance():
            while True:
                try:
                    metrics = self._collect_system_metrics()
                    with self.lock:
                        self.performance_history.append(metrics)
                    time.sleep(5)  # Collect every 5 seconds
                except Exception as e:
                    self.logger.error(f"Error in performance monitoring: {e}")
                    time.sleep(10)
        
        monitor_thread = threading.Thread(target=monitor_performance, daemon=True)
        monitor_thread.start()
    
    def _collect_system_metrics(self) -> PerformanceMetrics:
        """Collect current system performance metrics"""
        try:
            process = psutil.Process(os.getpid())
            
            return PerformanceMetrics(
                cpu_percent=process.cpu_percent(),
                memory_percent=process.memory_percent(),
                memory_used_mb=process.memory_info().rss / 1024 / 1024,
                disk_usage_percent=psutil.disk_usage('/').percent,
                active_threads=process.num_threads(),
                open_files=len(process.open_files()),
                network_connections=len(process.connections()),
                timestamp=time.time()
            )
        except Exception as e:
            self.logger.error(f"Error collecting system metrics: {e}")
            return PerformanceMetrics(
                cpu_percent=0.0,
                memory_percent=0.0,
                memory_used_mb=0.0,
                disk_usage_percent=0.0,
                active_threads=0,
                open_files=0,
                network_connections=0,
                timestamp=time.time()
            )
    
    def log_metric(self, name: str, value: float, tags: Optional[Dict[str, str]] = None, 
                   metadata: Optional[Dict[str, Any]] = None):
        """Log a metric value"""
        metric = MetricPoint(
            timestamp=time.time(),
            value=value,
            tags=tags or {},
            metadata=metadata or {}
        )
        
        with self.lock:
            self.metrics[name].append(metric)
        
        self.logger.debug(f"Metric {name}: {value} (tags: {tags})")
    
    def log_trade_event(self, event_type: str, symbol: str, side: str, 
                       quantity: float, price: float, pnl: Optional[float] = None,
                       metadata: Optional[Dict[str, Any]] = None):
        """Log a trade event with detailed metrics"""
        trade_data = {
            'event_type': event_type,
            'symbol': symbol,
            'side': side,
            'quantity': quantity,
            'price': price,
            'pnl': pnl,
            'timestamp': time.time(),
            'metadata': metadata or {}
        }
        
        self.logger.info(f"Trade Event: {json.dumps(trade_data)}")
        
        # Log as metric
        self.log_metric(
            f"trade_{event_type}",
            pnl or 0.0,
            tags={'symbol': symbol, 'side': side},
            metadata=trade_data
        )
    
    def log_engine_cycle(self, cycle_time: float, state: str, positions_count: int,
                        signals_count: int, orders_count: int):
        """Log engine cycle metrics"""
        cycle_data = {
            'cycle_time': cycle_time,
            'state': state,
            'positions_count': positions_count,
            'signals_count': signals_count,
            'orders_count': orders_count,
            'timestamp': time.time()
        }
        
        self.logger.debug(f"Engine Cycle: {json.dumps(cycle_data)}")
        
        # Log metrics
        self.log_metric('engine_cycle_time', cycle_time, {'state': state})
        self.log_metric('engine_positions', positions_count, {'state': state})
        self.log_metric('engine_signals', signals_count, {'state': state})
        self.log_metric('engine_orders', orders_count, {'state': state})
    
    def log_scanner_metrics(self, symbols_scanned: int, candidates_found: int,
                           scan_time: float, filters_applied: Dict[str, int]):
        """Log scanner performance metrics"""
        scanner_data = {
            'symbols_scanned': symbols_scanned,
            'candidates_found': candidates_found,
            'scan_time': scan_time,
            'filters_applied': filters_applied,
            'timestamp': time.time()
        }
        
        self.logger.info(f"Scanner Metrics: {json.dumps(scanner_data)}")
        
        # Log metrics
        self.log_metric('scanner_symbols_scanned', symbols_scanned)
        self.log_metric('scanner_candidates_found', candidates_found)
        self.log_metric('scanner_scan_time', scan_time)
        
        for filter_name, count in filters_applied.items():
            self.log_metric(f'scanner_filter_{filter_name}', count)
    
    def log_risk_metrics(self, current_risk: float, max_risk: float, 
                        position_risk: float, daily_pnl: float):
        """Log risk management metrics"""
        risk_data = {
            'current_risk': current_risk,
            'max_risk': max_risk,
            'position_risk': position_risk,
            'daily_pnl': daily_pnl,
            'timestamp': time.time()
        }
        
        self.logger.info(f"Risk Metrics: {json.dumps(risk_data)}")
        
        # Log metrics
        self.log_metric('risk_current', current_risk)
        self.log_metric('risk_max', max_risk)
        self.log_metric('risk_position', position_risk)
        self.log_metric('risk_daily_pnl', daily_pnl)
    
    def get_metrics_summary(self, metric_name: str, last_n: int = 100) -> Dict[str, Any]:
        """Get summary statistics for a metric"""
        with self.lock:
            if metric_name not in self.metrics:
                return {}
            
            values = [m.value for m in list(self.metrics[metric_name])[-last_n:]]
            
            if not values:
                return {}
            
            return {
                'count': len(values),
                'mean': sum(values) / len(values),
                'min': min(values),
                'max': max(values),
                'latest': values[-1] if values else 0,
                'timestamp': time.time()
            }
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get current performance summary"""
        with self.lock:
            if not self.performance_history:
                return {}
            
            latest = self.performance_history[-1]
            
            return {
                'cpu_percent': latest.cpu_percent,
                'memory_percent': latest.memory_percent,
                'memory_used_mb': latest.memory_used_mb,
                'disk_usage_percent': latest.disk_usage_percent,
                'active_threads': latest.active_threads,
                'open_files': latest.open_files,
                'network_connections': latest.network_connections,
                'timestamp': latest.timestamp
            }
    
    def get_all_metrics(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get all collected metrics"""
        with self.lock:
            return {
                name: [asdict(metric) for metric in list(metrics)[-100:]]
                for name, metrics in self.metrics.items()
            }
    
    def clear_metrics(self):
        """Clear all collected metrics"""
        with self.lock:
            self.metrics.clear()
            self.performance_history.clear()
        
        self.logger.info("All metrics cleared")

# Global metrics logger instance
_metrics_logger: Optional[MetricsLogger] = None

def get_metrics_logger() -> MetricsLogger:
    """Get the global metrics logger instance"""
    global _metrics_logger
    if _metrics_logger is None:
        _metrics_logger = MetricsLogger()
    return _metrics_logger

def log_trade_event(event_type: str, symbol: str, side: str, 
                   quantity: float, price: float, pnl: Optional[float] = None,
                   metadata: Optional[Dict[str, Any]] = None):
    """Convenience function to log trade events"""
    get_metrics_logger().log_trade_event(event_type, symbol, side, quantity, price, pnl, metadata)

def log_engine_cycle(cycle_time: float, state: str, positions_count: int,
                    signals_count: int, orders_count: int):
    """Convenience function to log engine cycles"""
    get_metrics_logger().log_engine_cycle(cycle_time, state, positions_count, signals_count, orders_count)

def log_scanner_metrics(symbols_scanned: int, candidates_found: int,
                       scan_time: float, filters_applied: Dict[str, int]):
    """Convenience function to log scanner metrics"""
    get_metrics_logger().log_scanner_metrics(symbols_scanned, candidates_found, scan_time, filters_applied)

def log_risk_metrics(current_risk: float, max_risk: float, 
                    position_risk: float, daily_pnl: float):
    """Convenience function to log risk metrics"""
    get_metrics_logger().log_risk_metrics(current_risk, max_risk, position_risk, daily_pnl)
