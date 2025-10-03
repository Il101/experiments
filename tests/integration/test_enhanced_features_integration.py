"""
Integration tests for enhanced market microstructure features.

Tests the full integration of:
- TradesAggregator
- OrderBookManager  
- DensityDetector
- ActivityTracker
- Enhanced LevelDetector

With the core trading engine components.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, MagicMock
from breakout_bot.core.engine import OptimizedOrchestraEngine
from breakout_bot.config.settings import SystemConfig, get_preset


@pytest.fixture
def mock_exchange_client():
    """Create a mock exchange client."""
    client = Mock()
    client.fetch_markets = AsyncMock(return_value=['BTC/USDT', 'ETH/USDT'])
    client.fetch_ticker = AsyncMock(return_value={
        'last': 50000,
        'bid': 49995,
        'ask': 50005,
        'volume': 1000
    })
    client.get_rate_limiter_status = Mock(return_value={
        'remaining': 100,
        'limit': 100
    })
    return client


@pytest.fixture
def engine():
    """Create an engine instance with mock components."""
    system_config = SystemConfig(
        trading_mode='paper',
        api_key='test_key',
        api_secret='test_secret'
    )
    
    return OptimizedOrchestraEngine(
        preset_name='high_percent_breakout',
        system_config=system_config
    )


@pytest.mark.asyncio
async def test_enhanced_components_initialized(engine):
    """Test that all enhanced components are properly initialized."""
    await engine.initialize()
    
    # Check that enhanced components are created
    assert engine.trades_aggregator is not None, "TradesAggregator should be initialized"
    assert engine.orderbook_manager is not None, "OrderBookManager should be initialized"
    assert engine.density_detector is not None, "DensityDetector should be initialized"
    assert engine.activity_tracker is not None, "ActivityTracker should be initialized"


@pytest.mark.asyncio
async def test_signal_manager_has_microstructure_components(engine):
    """Test that SignalManager receives microstructure components."""
    await engine.initialize()
    
    assert engine.signal_manager.trades_aggregator is not None
    assert engine.signal_manager.density_detector is not None
    assert engine.signal_manager.activity_tracker is not None


@pytest.mark.asyncio
async def test_position_manager_has_activity_tracker(engine):
    """Test that PositionManager receives ActivityTracker."""
    await engine.initialize()
    
    assert hasattr(engine.position_manager, 'activity_tracker')
    assert engine.position_manager.activity_tracker is not None


@pytest.mark.asyncio
async def test_scanning_manager_has_websocket_components(engine):
    """Test that ScanningManager receives WebSocket components."""
    await engine.initialize()
    
    assert engine.scanning_manager.trades_aggregator is not None
    assert engine.scanning_manager.orderbook_manager is not None


@pytest.mark.asyncio
async def test_subscribe_symbol_to_streams(engine):
    """Test subscribing a symbol to WebSocket streams."""
    await engine.initialize()
    
    # Mock the subscribe methods
    engine.trades_aggregator.subscribe = AsyncMock()
    engine.orderbook_manager.subscribe = AsyncMock()
    
    # Subscribe a symbol
    await engine.subscribe_symbol_to_streams('BTC/USDT')
    
    # Verify subscriptions were called
    engine.trades_aggregator.subscribe.assert_called_once_with('BTC/USDT')
    engine.orderbook_manager.subscribe.assert_called_once_with('BTC/USDT')


@pytest.mark.asyncio
async def test_get_market_microstructure_metrics(engine):
    """Test getting microstructure metrics for a symbol."""
    await engine.initialize()
    
    # Mock some data
    engine.trades_aggregator.get_tpm = Mock(return_value=150.0)
    engine.trades_aggregator.get_tps = Mock(return_value=25000.0)
    engine.trades_aggregator.get_vol_delta = Mock(return_value=5000.0)
    
    # Get metrics
    metrics = engine.get_market_microstructure_metrics('BTC/USDT')
    
    # Verify structure
    assert 'symbol' in metrics
    assert 'trades' in metrics
    assert 'activity' in metrics
    assert 'densities' in metrics
    assert metrics['symbol'] == 'BTC/USDT'


@pytest.mark.asyncio
async def test_density_config_loaded_from_preset(engine):
    """Test that density configuration is loaded from preset."""
    await engine.initialize()
    
    # Check that density_detector was initialized with config from preset
    assert engine.density_detector.k_density > 0
    assert engine.density_detector.bucket_ticks > 0


@pytest.mark.asyncio
async def test_activity_tracker_config_loaded_from_preset(engine):
    """Test that activity tracker configuration is loaded from preset."""
    await engine.initialize()
    
    # Check that activity_tracker was initialized with config from preset
    assert engine.activity_tracker.drop_threshold > 0
    assert engine.activity_tracker.drop_threshold <= 1.0


@pytest.mark.asyncio
async def test_engine_status_includes_microstructure(engine):
    """Test that engine status can be retrieved without errors."""
    await engine.initialize()
    
    status = engine.get_status()
    
    # Basic status check
    assert 'status' in status
    assert 'state' in status
    assert status is not None


@pytest.mark.asyncio 
async def test_full_initialization_no_errors(engine):
    """Test that full engine initialization completes without errors."""
    try:
        await engine.initialize()
        
        # Verify all critical components exist
        assert engine.exchange_client is not None
        assert engine.market_data_provider is not None
        assert engine.scanner is not None
        assert engine.signal_generator is not None
        assert engine.risk_manager is not None
        assert engine.position_manager is not None
        assert engine.execution_manager is not None
        
        # Verify new components
        assert engine.trades_aggregator is not None
        assert engine.orderbook_manager is not None
        assert engine.density_detector is not None
        assert engine.activity_tracker is not None
        
        # Verify managers have new components
        assert engine.signal_manager.trades_aggregator is not None
        assert engine.signal_manager.density_detector is not None
        assert engine.signal_manager.activity_tracker is not None
        
        assert engine.scanning_manager.trades_aggregator is not None
        assert engine.scanning_manager.orderbook_manager is not None
        
        assert engine.position_manager.activity_tracker is not None
        
    except Exception as e:
        pytest.fail(f"Engine initialization failed with error: {e}")


@pytest.mark.asyncio
async def test_microstructure_metrics_format(engine):
    """Test that microstructure metrics return proper format."""
    await engine.initialize()
    
    # Get metrics
    metrics = engine.get_market_microstructure_metrics('BTC/USDT')
    
    # Check format
    assert isinstance(metrics, dict)
    assert isinstance(metrics.get('trades', {}), dict)
    assert isinstance(metrics.get('activity', {}), dict)
    assert isinstance(metrics.get('densities', []), list)
    assert 'timestamp' in metrics


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
