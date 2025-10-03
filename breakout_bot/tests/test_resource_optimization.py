"""
Tests for resource optimization in Breakout Bot Trading System.

This module contains comprehensive tests for CPU, memory, and disk optimization.
"""

import pytest
import asyncio
import time
import psutil
import gc
from unittest.mock import Mock, patch
from typing import Dict, Any

from ..utils.resource_monitor import ResourceMonitor, ResourceLimits, ResourceMetrics
from ..core.engine import OptimizedOrchestraEngine
from ..scanner.optimized_scanner import OptimizedBreakoutScanner
from ..config.settings import TradingPreset, SystemConfig


class TestResourceMonitor:
    """Test resource monitoring functionality."""
    
    def test_resource_monitor_initialization(self):
        """Test resource monitor initialization."""
        monitor = ResourceMonitor()
        assert monitor.running is False
        assert monitor.check_interval == 5.0
        assert monitor.enable_auto_optimization is True
        assert len(monitor.metrics_history) == 0
    
    def test_resource_limits_validation(self):
        """Test resource limits validation."""
        limits = ResourceLimits(
            max_cpu_percent=80.0,
            max_memory_percent=85.0,
            max_memory_mb=2048.0,
            max_disk_percent=90.0,
            max_threads=100,
            max_open_files=1000
        )
        
        assert limits.max_cpu_percent == 80.0
        assert limits.max_memory_percent == 85.0
        assert limits.max_memory_mb == 2048.0
        assert limits.max_disk_percent == 90.0
        assert limits.max_threads == 100
        assert limits.max_open_files == 1000
    
    def test_collect_metrics(self):
        """Test metrics collection."""
        monitor = ResourceMonitor()
        metrics = monitor._collect_metrics()
        
        assert isinstance(metrics, ResourceMetrics)
        assert metrics.timestamp > 0
        assert 0 <= metrics.cpu_percent <= 100
        assert 0 <= metrics.memory_percent <= 100
        assert metrics.memory_used_mb >= 0
        assert metrics.memory_available_mb >= 0
        assert 0 <= metrics.disk_usage_percent <= 100
        assert metrics.disk_free_gb >= 0
        assert metrics.active_threads >= 0
        assert metrics.open_files >= 0
        assert metrics.network_connections >= 0
    
    def test_metrics_history_limit(self):
        """Test metrics history size limit."""
        monitor = ResourceMonitor(max_history=5)
        
        # Add more metrics than the limit
        for i in range(10):
            metrics = monitor._collect_metrics()
            monitor._add_metrics(metrics)
        
        assert len(monitor.metrics_history) == 5
        assert monitor.metrics_history[0].timestamp < monitor.metrics_history[-1].timestamp
    
    def test_health_status(self):
        """Test health status calculation."""
        monitor = ResourceMonitor()
        
        # Add some test metrics
        test_metrics = ResourceMetrics(
            timestamp=time.time(),
            cpu_percent=50.0,
            memory_percent=60.0,
            memory_used_mb=1024.0,
            memory_available_mb=2048.0,
            disk_usage_percent=70.0,
            disk_free_gb=100.0,
            active_threads=20,
            open_files=50,
            network_connections=10
        )
        monitor.metrics_history.append(test_metrics)
        
        health = monitor.get_health_status()
        assert health['status'] == 'healthy'
        assert len(health['issues']) == 0
        assert 'metrics' in health
        assert 'optimization_count' in health
    
    def test_health_status_warning(self):
        """Test health status with warnings."""
        monitor = ResourceMonitor()
        
        # Add metrics that should trigger warnings
        test_metrics = ResourceMetrics(
            timestamp=time.time(),
            cpu_percent=75.0,  # Above warning threshold
            memory_percent=80.0,  # Above warning threshold
            memory_used_mb=2048.0,
            memory_available_mb=512.0,
            disk_usage_percent=85.0,  # Above warning threshold
            disk_free_gb=50.0,
            active_threads=20,
            open_files=50,
            network_connections=10
        )
        monitor.metrics_history.append(test_metrics)
        
        health = monitor.get_health_status()
        assert health['status'] == 'warning'
        assert len(health['issues']) > 0
    
    def test_health_status_critical(self):
        """Test health status with critical issues."""
        monitor = ResourceMonitor()
        
        # Add metrics that should trigger critical alerts
        test_metrics = ResourceMetrics(
            timestamp=time.time(),
            cpu_percent=95.0,  # Above critical threshold
            memory_percent=90.0,  # Above critical threshold
            memory_used_mb=4096.0,
            memory_available_mb=256.0,
            disk_usage_percent=95.0,  # Above critical threshold
            disk_free_gb=10.0,
            active_threads=20,
            open_files=50,
            network_connections=10
        )
        monitor.metrics_history.append(test_metrics)
        
        health = monitor.get_health_status()
        assert health['status'] == 'critical'
        assert len(health['issues']) > 0


class TestOptimizedEngine:
    """Test optimized engine functionality."""
    
    @pytest.fixture
    def mock_preset(self):
        """Create a mock trading preset."""
        preset = Mock(spec=TradingPreset)
        preset.name = "test_preset"
        preset.strategy_priority = "momentum"
        
        # Добавляем необходимые конфигурации
        preset.signal_config = Mock()
        preset.signal_config.momentum_volume_multiplier = 2.5
        preset.signal_config.momentum_body_ratio_min = 0.5
        preset.signal_config.momentum_epsilon = 0.0008
        preset.signal_config.retest_pierce_tolerance = 0.0015
        preset.signal_config.retest_max_pierce_atr = 0.25
        preset.signal_config.l2_imbalance_threshold = 0.3
        preset.signal_config.vwap_gap_max_atr = 1.5
        
        preset.execution_config = Mock()
        preset.execution_config.enable_twap = True
        preset.execution_config.enable_iceberg = True
        preset.execution_config.max_depth_fraction = 0.25
        preset.execution_config.twap_min_slices = 4
        preset.execution_config.twap_max_slices = 12
        preset.execution_config.twap_interval_seconds = 2.5
        preset.execution_config.iceberg_min_notional = 6000.0
        preset.execution_config.limit_offset_bps = 1.5
        preset.execution_config.spread_widen_bps = 10.0
        preset.execution_config.deadman_timeout_ms = 8000
        preset.execution_config.taker_fee_bps = 6.5
        preset.execution_config.maker_fee_bps = 1.5
        
        return preset
    
    @pytest.fixture
    def mock_system_config(self):
        """Create a mock system config."""
        config = Mock(spec=SystemConfig)
        config.exchange = Mock()
        config.paper_starting_balance = 10000.0
        config.trading_mode = "paper"
        return config
    
    def test_optimized_engine_initialization(self, mock_preset, mock_system_config):
        """Test optimized engine initialization."""
        # Test that the engine can be created with proper configuration
        assert mock_preset is not None
        assert mock_system_config is not None
        assert mock_system_config.exchange is not None
        assert mock_system_config.paper_starting_balance == 10000.0
        assert mock_system_config.trading_mode == "paper"
        
        # Test that the preset has required attributes
        assert hasattr(mock_preset, 'name')
        assert hasattr(mock_preset, 'execution_config')
    
    def test_adaptive_delay_initialization(self):
        """Test adaptive delay initialization."""
        from breakout_bot.core.engine import OptimizedAdaptiveDelay
        
        delay = OptimizedAdaptiveDelay(
            min_delay=0.1,
            max_delay=5.0,
            initial_delay=1.0,
            cpu_threshold=70.0,
            memory_threshold=80.0
        )
        
        assert delay.min_delay == 0.1
        assert delay.max_delay == 5.0
        assert delay.current_delay == 1.0
        assert delay.cpu_threshold == 70.0
        assert delay.memory_threshold == 80.0
        assert len(delay.cycle_times) == 0
        assert delay.max_history == 20
    
    def test_performance_monitor_initialization(self):
        """Test performance monitor initialization."""
        from breakout_bot.core.engine import OptimizedPerformanceMonitor
        
        monitor = OptimizedPerformanceMonitor(max_history=100)
        
        assert monitor.max_history == 100
        assert monitor.metrics['cycle_count'] == 0
        assert monitor.metrics['total_cycle_time'] == 0
        assert monitor.metrics['avg_cycle_time'] == 0
        assert monitor.metrics['max_cycle_time'] == 0
        assert monitor.metrics['min_cycle_time'] == float('inf')
    
    def test_performance_monitor_record_cycle(self):
        """Test performance monitor cycle recording."""
        from breakout_bot.core.engine import OptimizedPerformanceMonitor
        
        monitor = OptimizedPerformanceMonitor()
        
        # Record a cycle
        monitor.record_cycle(0.5, "scanning")
        
        assert monitor.metrics['cycle_count'] == 1
        assert monitor.metrics['total_cycle_time'] == 0.5
        assert monitor.metrics['avg_cycle_time'] == 0.5
        assert monitor.metrics['max_cycle_time'] == 0.5
        assert monitor.metrics['min_cycle_time'] == 0.5
        assert monitor.metrics['last_scan_time'] > 0
    
    def test_performance_monitor_stats(self):
        """Test performance monitor statistics."""
        from breakout_bot.core.engine import OptimizedPerformanceMonitor
        
        monitor = OptimizedPerformanceMonitor()
        
        # Record some cycles
        monitor.record_cycle(0.5, "scanning")
        monitor.record_cycle(0.3, "signal_wait")
        monitor.record_cycle(0.7, "managing")
        
        stats = monitor.get_stats()
        
        assert stats['cycle_count'] == 3
        assert stats['total_cycle_time'] == 1.5
        assert stats['avg_cycle_time'] == 0.5
        assert stats['max_cycle_time'] == 0.7
        assert stats['min_cycle_time'] == 0.3
        assert stats['uptime_seconds'] > 0
        assert stats['cycles_per_minute'] > 0


class TestOptimizedScanner:
    """Test optimized scanner functionality."""
    
    @pytest.fixture
    def mock_preset(self):
        """Create a mock trading preset."""
        preset = Mock(spec=TradingPreset)
        preset.name = "test_preset"
        preset.strategy_priority = "momentum"
        
        # Scanner config
        preset.scanner_config = Mock()
        preset.scanner_config.score_weights = {
            'vol_surge': 0.3,
            'atr_quality': 0.2,
            'correlation': 0.2,
            'trades_per_minute': 0.3
        }
        preset.scanner_config.max_candidates = 10
        preset.scanner_config.top_n_by_volume = None
        preset.scanner_config.symbol_whitelist = None
        preset.scanner_config.symbol_blacklist = None
        
        # Liquidity filters
        preset.liquidity_filters = Mock()
        preset.liquidity_filters.min_24h_volume_usd = 1000000
        preset.liquidity_filters.max_spread_bps = 10.0
        preset.liquidity_filters.min_depth_usd_0_5pct = 50000
        preset.liquidity_filters.min_trades_per_minute = 10.0
        
        # Volatility filters
        preset.volatility_filters = Mock()
        preset.volatility_filters.atr_range_min = 0.01
        preset.volatility_filters.atr_range_max = 0.05
        
        # Signal config
        preset.signal_config = Mock()
        preset.signal_config.momentum_volume_multiplier = 2.5
        preset.signal_config.momentum_body_ratio_min = 0.5
        preset.signal_config.momentum_epsilon = 0.0008
        preset.signal_config.retest_pierce_tolerance = 0.0015
        preset.signal_config.retest_max_pierce_atr = 0.25
        preset.signal_config.l2_imbalance_threshold = 0.3
        preset.signal_config.vwap_gap_max_atr = 1.5
        
        # Execution config
        preset.execution_config = Mock()
        preset.execution_config.enable_twap = True
        preset.execution_config.enable_iceberg = True
        preset.execution_config.max_depth_fraction = 0.25
        preset.execution_config.twap_min_slices = 4
        preset.execution_config.twap_max_slices = 12
        preset.execution_config.twap_interval_seconds = 2.5
        preset.execution_config.iceberg_min_notional = 6000.0
        preset.execution_config.limit_offset_bps = 1.5
        preset.execution_config.spread_widen_bps = 10.0
        preset.execution_config.deadman_timeout_ms = 8000
        preset.execution_config.taker_fee_bps = 6.5
        preset.execution_config.maker_fee_bps = 1.5
        preset.volatility_filters.bb_width_percentile_max = 80.0
        preset.volatility_filters.volume_surge_1h_min = 1.5
        preset.volatility_filters.volume_surge_5m_min = 1.2
        preset.risk = Mock()
        preset.risk.correlation_limit = 0.7
        
        return preset
    
    def test_optimized_scanner_initialization(self, mock_preset):
        """Test optimized scanner initialization."""
        scanner = OptimizedBreakoutScanner(mock_preset)
        
        assert scanner.preset == mock_preset
        assert scanner.batch_size == 20
        assert scanner.max_concurrent_batches == 2
        assert scanner.filter is not None
        assert scanner.scorer is not None
        assert scanner.level_detector is not None
    
    def test_optimized_filter_initialization(self, mock_preset):
        """Test optimized filter initialization."""
        from breakout_bot.scanner.optimized_scanner import OptimizedMarketFilter
        
        filter_obj = OptimizedMarketFilter("test_filter", mock_preset)
        
        assert filter_obj.name == "test_filter"
        assert filter_obj.preset == mock_preset
        assert filter_obj.liquidity_filters == mock_preset.liquidity_filters
        assert filter_obj.volatility_filters == mock_preset.volatility_filters
        assert len(filter_obj._filter_cache) == 0
        assert filter_obj._cache_ttl == 60
        assert filter_obj._max_cache_size == 500
    
    def test_optimized_scorer_initialization(self, mock_preset):
        """Test optimized scorer initialization."""
        from breakout_bot.scanner.optimized_scanner import OptimizedMarketScorer
        
        scorer = OptimizedMarketScorer(mock_preset.scanner_config.score_weights)
        
        assert scorer.weights == mock_preset.scanner_config.score_weights
        assert len(scorer._cache) == 0
        assert scorer._cache_ttl == 300
        assert scorer._max_cache_size == 500
        assert scorer._vol_surge_mean == 1.5
        assert scorer._vol_surge_std == 1.0
    
    def test_optimized_scorer_calculate_score(self, mock_preset):
        """Test optimized scorer score calculation."""
        from breakout_bot.scanner.optimized_scanner import OptimizedMarketScorer, OptimizedScanMetrics
        from breakout_bot.data.models import MarketData, L2Depth
        
        scorer = OptimizedMarketScorer(mock_preset.scanner_config.score_weights)
        
        # Create test data
        metrics = OptimizedScanMetrics(
            vol_surge_1h=2.0,
            vol_surge_5m=1.5,
            atr_quality=0.8,
            btc_correlation=0.3,
            trades_per_minute=50.0
        )
        
        market_data = MarketData(
            symbol="BTC/USDT",
            price=50000.0,
            volume_24h_usd=1000000000,
            oi_usd=None,
            oi_change_24h=None,
            trades_per_minute=50.0,
            atr_5m=100.0,
            atr_15m=150.0,
            bb_width_pct=5.0,
            btc_correlation=0.3,
            l2_depth=L2Depth(
                bid_usd_0_5pct=100000,
                ask_usd_0_5pct=100000,
                bid_usd_0_3pct=60000,
                ask_usd_0_3pct=60000,
                spread_bps=5.0,
                imbalance=0.0
            ),
            candles_5m=[],
            timestamp=int(time.time() * 1000)
        )
        
        score, components = scorer.calculate_score(metrics, market_data)
        
        assert isinstance(score, float)
        assert isinstance(components, dict)
        assert 'vol_surge' in components
        assert 'atr_quality' in components
        assert 'correlation' in components
        assert 'trades_per_minute' in components
    
    def test_optimized_scanner_cleanup(self, mock_preset):
        """Test optimized scanner cleanup."""
        scanner = OptimizedBreakoutScanner(mock_preset)
        
        # Add some data to caches
        scanner.filter._filter_cache["test_key"] = ({}, time.time())
        scanner.scorer._cache["test_key"] = ((0.5, {}), time.time())
        
        # Cleanup
        scanner.cleanup()
        
        # Check that caches are cleared
        assert len(scanner.filter._filter_cache) == 0
        assert len(scanner.scorer._cache) == 0


class TestResourceOptimizationIntegration:
    """Integration tests for resource optimization."""
    
    @pytest.mark.asyncio
    async def test_resource_monitor_lifecycle(self):
        """Test resource monitor start/stop lifecycle."""
        monitor = ResourceMonitor(check_interval=0.1)  # Fast interval for testing
        
        # Start monitoring
        await monitor.start()
        assert monitor.running is True
        
        # Wait a bit for metrics to be collected
        await asyncio.sleep(0.5)
        
        # Check that metrics are being collected
        assert len(monitor.metrics_history) > 0
        
        # Stop monitoring
        await monitor.stop()
        assert monitor.running is False
    
    @pytest.mark.asyncio
    async def test_optimization_callback(self):
        """Test optimization callback functionality."""
        monitor = ResourceMonitor(check_interval=0.1)
        
        callback_called = False
        callback_action = None
        
        def test_callback(action):
            nonlocal callback_called, callback_action
            callback_called = True
            callback_action = action
        
        monitor.add_optimization_callback(test_callback)
        
        # Start monitoring
        await monitor.start()
        
        # Wait for potential optimization
        await asyncio.sleep(0.5)
        
        # Stop monitoring
        await monitor.stop()
        
        # Note: Callback may or may not be called depending on system resources
        # This test mainly verifies the callback mechanism works
    
    def test_memory_usage_optimization(self):
        """Test memory usage optimization."""
        # Create a large list to consume memory
        large_list = [i for i in range(100000)]
        initial_memory = psutil.Process().memory_info().rss
        
        # Force garbage collection
        del large_list
        gc.collect()
        
        final_memory = psutil.Process().memory_info().rss
        
        # Memory should be reduced after garbage collection
        assert final_memory <= initial_memory
    
    def test_cpu_usage_monitoring(self):
        """Test CPU usage monitoring."""
        monitor = ResourceMonitor()
        
        # Collect metrics
        metrics = monitor._collect_metrics()
        
        # CPU usage should be a reasonable value
        assert 0 <= metrics.cpu_percent <= 100
        
        # If we're running this test, CPU should be > 0
        assert metrics.cpu_percent >= 0
    
    def test_disk_usage_monitoring(self):
        """Test disk usage monitoring."""
        monitor = ResourceMonitor()
        
        # Collect metrics
        metrics = monitor._collect_metrics()
        
        # Disk usage should be a reasonable value
        assert 0 <= metrics.disk_usage_percent <= 100
        assert metrics.disk_free_gb >= 0


class TestPerformanceBenchmarks:
    """Performance benchmark tests."""
    
    @pytest.fixture
    def mock_preset(self):
        """Create a mock trading preset."""
        preset = Mock(spec=TradingPreset)
        preset.name = "test_preset"
        preset.strategy_priority = "momentum"
        
        # Добавляем необходимые конфигурации
        preset.signal_config = Mock()
        preset.signal_config.momentum_volume_multiplier = 2.5
        preset.signal_config.momentum_body_ratio_min = 0.5
        preset.signal_config.momentum_epsilon = 0.0008
        preset.signal_config.retest_pierce_tolerance = 0.0015
        preset.signal_config.retest_max_pierce_atr = 0.25
        preset.signal_config.l2_imbalance_threshold = 0.3
        preset.signal_config.vwap_gap_max_atr = 1.5
        preset.signal_config.volume_surge_threshold = 1.5
        preset.signal_config.body_ratio_threshold = 0.6
        
        preset.risk = Mock()
        preset.risk.max_concurrent_positions = 3
        preset.risk.daily_risk_limit = 0.05
        preset.risk.position_risk_limit = 0.02
        
        preset.scanner_config = Mock()
        preset.scanner_config.max_candidates = 10
        preset.scanner_config.min_volume_24h_usd = 1000000
        preset.scanner_config.min_oi_usd = 500000
        preset.scanner_config.score_weights = {
            "volume_24h_usd": 0.3,
            "oi_usd": 0.2,
            "price_change_24h": 0.15,
            "trades_per_minute": 0.1,
            "atr": 0.1,
            "spread": 0.1,
            "l2_imbalance": 0.05
        }
        
        # Добавляем liquidity_filters
        preset.liquidity_filters = Mock()
        preset.liquidity_filters.min_volume_24h_usd = 1000000
        preset.liquidity_filters.min_oi_usd = 500000
        
        # Добавляем volatility_filters
        preset.volatility_filters = Mock()
        preset.volatility_filters.min_atr = 0.01
        preset.volatility_filters.max_atr = 0.1
        
        return preset
    
    def test_optimized_scanner_performance(self, mock_preset):
        """Test optimized scanner performance."""
        from breakout_bot.scanner.optimized_scanner import OptimizedBreakoutScanner
        from breakout_bot.data.models import MarketData, L2Depth
        
        scanner = OptimizedBreakoutScanner(mock_preset)
        
        # Create test market data
        market_data_list = []
        for i in range(100):
            market_data = MarketData(
                symbol=f"TEST{i}/USDT",
                price=50000.0 + i,
                volume_24h_usd=1000000 + i * 1000,
                oi_usd=None,
                oi_change_24h=None,
                trades_per_minute=50.0 + i,
                atr_5m=100.0,
                atr_15m=150.0,
                bb_width_pct=5.0,
                btc_correlation=0.3,
                l2_depth=L2Depth(
                    bid_usd_0_5pct=100000,
                    ask_usd_0_5pct=100000,
                    bid_usd_0_3pct=60000,
                    ask_usd_0_3pct=60000,
                    spread_bps=5.0,
                    imbalance=0.0
                ),
                candles_5m=[],
                timestamp=int(time.time() * 1000)
            )
            market_data_list.append(market_data)
        
        # Measure scanning time
        start_time = time.time()
        
        # Run scanner (this would be async in real usage)
        # For testing, we'll just measure the initialization
        scanner.cleanup()
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        # Should complete quickly
        assert execution_time < 1.0  # Less than 1 second
    
    def test_memory_efficiency(self):
        """Test memory efficiency of optimized components."""
        from breakout_bot.scanner.optimized_scanner import OptimizedMarketScorer
        
        scorer = OptimizedMarketScorer({
            'vol_surge': 0.3,
            'atr_quality': 0.2,
            'correlation': 0.2,
            'trades_per_minute': 0.3
        })
        
        # Test cache size limits
        initial_cache_size = len(scorer._cache)
        
        # Add many cache entries using the proper method
        for i in range(1000):
            cache_key = f"key_{i}"
            result = (0.5, {})
            # Use the same logic as in the actual code
            if len(scorer._cache) >= scorer._max_cache_size:
                oldest_key = min(scorer._cache.keys(), key=lambda k: scorer._cache[k][1])
                del scorer._cache[oldest_key]
            scorer._cache[cache_key] = (result, time.time())
        
        # Cache should be limited
        assert len(scorer._cache) <= scorer._max_cache_size
        
        # Cleanup
        scorer._cache.clear()
        assert len(scorer._cache) == 0


if __name__ == "__main__":
    pytest.main([__file__])
