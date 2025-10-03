"""
Quick test for OrderBookManager with Bybit WebSocket integration.
"""

import asyncio
import pytest
from breakout_bot.data.streams.orderbook_ws import OrderBookManager, OrderBookSnapshot, OrderBookLevel


@pytest.mark.asyncio
async def test_orderbook_manager_initialization():
    """Test OrderBookManager initializes correctly."""
    manager = OrderBookManager(use_real_ws=False)
    
    assert manager is not None
    assert manager.running is False
    assert len(manager.active_symbols) == 0
    assert len(manager.snapshots) == 0


@pytest.mark.asyncio
async def test_orderbook_manager_start_stop():
    """Test OrderBookManager start/stop."""
    manager = OrderBookManager(use_real_ws=False)
    
    await manager.start()
    assert manager.running is True
    
    await manager.stop()
    assert manager.running is False


@pytest.mark.asyncio
async def test_orderbook_manager_subscribe_unsubscribe():
    """Test subscribing/unsubscribing to symbols."""
    manager = OrderBookManager(use_real_ws=False)
    await manager.start()
    
    # Subscribe
    await manager.subscribe('BTCUSDT')
    assert manager.is_subscribed('BTCUSDT')
    assert 'BTCUSDT' in manager.active_symbols
    
    # Unsubscribe
    await manager.unsubscribe('BTCUSDT')
    assert not manager.is_subscribed('BTCUSDT')
    
    await manager.stop()


@pytest.mark.asyncio
async def test_orderbook_snapshot_operations():
    """Test order book snapshot operations."""
    manager = OrderBookManager(use_real_ws=False)
    
    # Create test snapshot
    bids = [
        OrderBookLevel(price=50000.0, size=1.0),
        OrderBookLevel(price=49950.0, size=2.0),
        OrderBookLevel(price=49900.0, size=1.5),
    ]
    
    asks = [
        OrderBookLevel(price=50050.0, size=1.0),
        OrderBookLevel(price=50100.0, size=2.0),
        OrderBookLevel(price=50150.0, size=1.5),
    ]
    
    snapshot = OrderBookSnapshot(
        timestamp=1000,
        bids=bids,
        asks=asks
    )
    
    # Update snapshot
    manager.update_snapshot('BTCUSDT', snapshot)
    
    # Retrieve snapshot
    retrieved = manager.get_snapshot('BTCUSDT')
    assert retrieved is not None
    assert retrieved.best_bid == 50000.0
    assert retrieved.best_ask == 50050.0
    assert retrieved.mid_price == 50025.0
    assert retrieved.spread_bps > 0


@pytest.mark.asyncio
async def test_orderbook_imbalance_calculation():
    """Test order book imbalance calculation."""
    manager = OrderBookManager(use_real_ws=False)
    
    # Create test snapshot with bid-heavy book
    bids = [
        OrderBookLevel(price=50000.0, size=10.0),  # Large bid
        OrderBookLevel(price=49950.0, size=8.0),
        OrderBookLevel(price=49900.0, size=5.0),
    ]
    
    asks = [
        OrderBookLevel(price=50050.0, size=2.0),  # Small ask
        OrderBookLevel(price=50100.0, size=3.0),
        OrderBookLevel(price=50150.0, size=2.0),
    ]
    
    snapshot = OrderBookSnapshot(
        timestamp=1000,
        bids=bids,
        asks=asks
    )
    
    manager.update_snapshot('BTCUSDT', snapshot)
    
    # Calculate imbalance
    imbalance = manager.get_imbalance('BTCUSDT', range_bps=30)
    
    # Should be positive (more bids than asks)
    assert imbalance > 0
    assert -1 <= imbalance <= 1


@pytest.mark.asyncio
async def test_orderbook_aggregated_depth():
    """Test aggregated depth calculation."""
    manager = OrderBookManager(use_real_ws=False)
    
    # Create test snapshot
    bids = [
        OrderBookLevel(price=50000.0, size=1.0),
        OrderBookLevel(price=49950.0, size=2.0),
        OrderBookLevel(price=49900.0, size=1.5),
    ]
    
    asks = [
        OrderBookLevel(price=50050.0, size=1.0),
        OrderBookLevel(price=50100.0, size=2.0),
        OrderBookLevel(price=50150.0, size=1.5),
    ]
    
    snapshot = OrderBookSnapshot(
        timestamp=1000,
        bids=bids,
        asks=asks
    )
    
    manager.update_snapshot('BTCUSDT', snapshot)
    
    # Get aggregated bid depth
    bid_depth = manager.get_aggregated_depth('BTCUSDT', side='bid', range_bps=50)
    assert len(bid_depth) > 0
    
    # Check cumulative size increases
    prev_size = 0
    for price, cum_size in bid_depth:
        assert cum_size > prev_size
        prev_size = cum_size
    
    # Get aggregated ask depth
    ask_depth = manager.get_aggregated_depth('BTCUSDT', side='ask', range_bps=50)
    assert len(ask_depth) > 0


@pytest.mark.asyncio
async def test_orderbook_callback_integration():
    """Test Bybit orderbook callback processing."""
    manager = OrderBookManager(use_real_ws=False)
    await manager.start()
    await manager.subscribe('BTCUSDT')
    
    # Simulate Bybit orderbook update
    bybit_orderbook_data = {
        'symbol': 'BTCUSDT',
        'bids': [
            ['50000.0', '1.5'],
            ['49950.0', '2.0'],
            ['49900.0', '1.0'],
        ],
        'asks': [
            ['50050.0', '1.2'],
            ['50100.0', '1.8'],
            ['50150.0', '1.5'],
        ],
        'timestamp': 1672304484978,
        'update_id': 177400507,
        'type': 'snapshot'
    }
    
    # Process update via callback
    await manager._on_orderbook_update('BTCUSDT', bybit_orderbook_data)
    
    # Verify snapshot was created
    snapshot = manager.get_snapshot('BTCUSDT')
    assert snapshot is not None
    assert snapshot.best_bid == 50000.0
    assert snapshot.best_ask == 50050.0
    assert len(snapshot.bids) == 3
    assert len(snapshot.asks) == 3
    
    await manager.stop()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
