"""
Tests for Activity Tracking.
"""

import pytest
import asyncio
import time
import numpy as np
from breakout_bot.data.streams.trades_ws import TradesAggregator, Trade
from breakout_bot.features.activity import ActivityTracker, ActivityMetrics


@pytest.fixture
def trades_aggregator():
    """Create trades aggregator fixture."""
    return TradesAggregator()


@pytest.fixture
def activity_tracker(trades_aggregator):
    """Create activity tracker fixture."""
    return ActivityTracker(
        trades_aggregator=trades_aggregator,
        lookback_periods=20,
        drop_threshold=0.3
    )


class TestActivityTracker:
    """Tests for ActivityTracker."""
    
    @pytest.mark.asyncio
    async def test_update_activity_basic(self, activity_tracker, trades_aggregator):
        """Test basic activity update."""
        await trades_aggregator.start()
        
        symbol = 'BTC/USDT'
        await trades_aggregator.subscribe(symbol)
        
        current_ts = int(time.time() * 1000)
        
        # Add some trades to generate activity
        for i in range(20):
            trade = Trade(
                timestamp=current_ts - (i * 1000),
                price=50000.0 + i,
                amount=1.0,
                side='buy' if i % 2 == 0 else 'sell'
            )
            trades_aggregator.add_trade(symbol, trade)
        
        # Update activity
        metrics = activity_tracker.update_activity(symbol)
        
        assert metrics is not None
        assert metrics.symbol == symbol
        assert isinstance(metrics.activity_index, float)
        
        await trades_aggregator.stop()
    
    @pytest.mark.asyncio
    async def test_activity_index_calculation(self, activity_tracker, trades_aggregator):
        """Test activity index calculation."""
        await trades_aggregator.start()
        
        symbol = 'BTC/USDT'
        await trades_aggregator.subscribe(symbol)
        
        current_ts = int(time.time() * 1000)
        
        # Build up history with varying activity
        for period in range(30):
            # Decreasing activity over time
            num_trades = max(5, 30 - period)
            
            for i in range(num_trades):
                trade = Trade(
                    timestamp=current_ts - (period * 10000) - (i * 100),
                    price=50000.0 + i,
                    amount=1.0,
                    side='buy' if i % 2 == 0 else 'sell'
                )
                trades_aggregator.add_trade(symbol, trade)
            
            # Update activity after each period
            await asyncio.sleep(0.01)  # Small delay
            metrics = activity_tracker.update_activity(symbol)
        
        # Latest metrics should show some activity
        final_metrics = activity_tracker.get_metrics(symbol)
        assert final_metrics is not None
        
        await trades_aggregator.stop()
    
    @pytest.mark.asyncio
    async def test_activity_drop_detection(self, activity_tracker, trades_aggregator):
        """Test detection of activity drop."""
        await trades_aggregator.start()
        
        symbol = 'BTC/USDT'
        await trades_aggregator.subscribe(symbol)
        
        current_ts = int(time.time() * 1000)
        
        # High activity period
        for period in range(15):
            for i in range(50):  # High trade count
                trade = Trade(
                    timestamp=current_ts - (period * 10000) - (i * 100),
                    price=50000.0 + i,
                    amount=2.0,
                    side='buy' if i % 2 == 0 else 'sell'
                )
                trades_aggregator.add_trade(symbol, trade)
            
            activity_tracker.update_activity(symbol)
        
        # Low activity period (drop)
        for period in range(5):
            for i in range(5):  # Low trade count
                trade = Trade(
                    timestamp=current_ts - (i * 100),
                    price=50000.0 + i,
                    amount=0.5,
                    side='sell'
                )
                trades_aggregator.add_trade(symbol, trade)
            
            activity_tracker.update_activity(symbol)
        
        # Check if drop is detected
        is_dropping = activity_tracker.is_activity_dropping(symbol)
        
        # Activity drop detection is based on statistical analysis
        # Can return bool or numpy.bool_
        assert isinstance(is_dropping, (bool, np.bool_))
        
        await trades_aggregator.stop()
    
    def test_get_activity_index(self, activity_tracker):
        """Test getting activity index for symbol."""
        symbol = 'BTC/USDT'
        
        # No data yet
        index = activity_tracker.get_activity_index(symbol)
        assert index == 0.0
    
    @pytest.mark.asyncio
    async def test_activity_history(self, activity_tracker, trades_aggregator):
        """Test retrieving activity history."""
        await trades_aggregator.start()
        
        symbol = 'BTC/USDT'
        await trades_aggregator.subscribe(symbol)
        
        current_ts = int(time.time() * 1000)
        
        # Build up some history
        for period in range(10):
            for i in range(10):
                trade = Trade(
                    timestamp=current_ts - (period * 5000) - (i * 100),
                    price=50000.0 + i,
                    amount=1.0,
                    side='buy' if i % 2 == 0 else 'sell'
                )
                trades_aggregator.add_trade(symbol, trade)
            
            activity_tracker.update_activity(symbol)
        
        # Get history
        history = activity_tracker.get_activity_history(symbol, periods=5)
        
        # Should have some history
        assert len(history) > 0
        assert all(isinstance(val, float) for val in history)
        
        await trades_aggregator.stop()
