"""
Tests for Trades WebSocket Aggregator.
"""

import pytest
import asyncio
import time
from breakout_bot.data.streams.trades_ws import (
    TradesAggregator,
    Trade,
    TradeWindow,
    TradeMetrics
)


@pytest.fixture
def trades_aggregator():
    """Create trades aggregator fixture."""
    return TradesAggregator()


@pytest.fixture
def trade_window():
    """Create trade window fixture."""
    return TradeWindow(window_seconds=60)


class TestTradeWindow:
    """Tests for TradeWindow class."""
    
    def test_add_trade(self, trade_window):
        """Test adding trades to window."""
        current_ts = int(time.time() * 1000)
        
        trade = Trade(
            timestamp=current_ts,
            price=50000.0,
            amount=1.5,
            side='buy'
        )
        
        trade_window.add_trade(trade)
        assert len(trade_window.trades) == 1
    
    def test_cleanup_old_trades(self, trade_window):
        """Test automatic cleanup of old trades."""
        current_ts = int(time.time() * 1000)
        
        # Add old trade (65 seconds ago)
        old_trade = Trade(
            timestamp=current_ts - 65000,
            price=50000.0,
            amount=1.0,
            side='buy'
        )
        trade_window.add_trade(old_trade)
        
        # Add current trade
        new_trade = Trade(
            timestamp=current_ts,
            price=50100.0,
            amount=1.0,
            side='buy'
        )
        trade_window.add_trade(new_trade)
        
        # Old trade should be removed
        assert len(trade_window.trades) == 1
        assert trade_window.trades[0].timestamp == current_ts
    
    def test_get_tpm(self, trade_window):
        """Test trades per minute calculation."""
        current_ts = int(time.time() * 1000)
        
        # Add 10 trades
        for i in range(10):
            trade = Trade(
                timestamp=current_ts - (i * 1000),  # 1 second apart
                price=50000.0 + i,
                amount=1.0,
                side='buy'
            )
            trade_window.add_trade(trade)
        
        tpm = trade_window.get_tpm(current_ts)
        # 10 trades in 60 second window = 10 TPM
        assert tpm == pytest.approx(10.0, rel=0.1)
    
    def test_get_buy_sell_ratio(self, trade_window):
        """Test buy/sell ratio calculation."""
        current_ts = int(time.time() * 1000)
        
        # Add 6 buy trades
        for i in range(6):
            trade = Trade(
                timestamp=current_ts - (i * 1000),
                price=50000.0,
                amount=1.0,
                side='buy'
            )
            trade_window.add_trade(trade)
        
        # Add 3 sell trades
        for i in range(3):
            trade = Trade(
                timestamp=current_ts - (i * 1000),
                price=50000.0,
                amount=1.0,
                side='sell'
            )
            trade_window.add_trade(trade)
        
        ratio = trade_window.get_buy_sell_ratio(current_ts)
        # 6 buys / 3 sells = 2.0
        assert ratio == pytest.approx(2.0, rel=0.01)
    
    def test_get_volume_delta(self, trade_window):
        """Test volume delta calculation."""
        current_ts = int(time.time() * 1000)
        
        # Add buy trades: 10 BTC
        for i in range(5):
            trade = Trade(
                timestamp=current_ts - (i * 1000),
                price=50000.0,
                amount=2.0,
                side='buy'
            )
            trade_window.add_trade(trade)
        
        # Add sell trades: 6 BTC
        for i in range(3):
            trade = Trade(
                timestamp=current_ts - (i * 1000),
                price=50000.0,
                amount=2.0,
                side='sell'
            )
            trade_window.add_trade(trade)
        
        vol_delta = trade_window.get_volume_delta(current_ts)
        # 10 - 6 = 4 BTC
        assert vol_delta == pytest.approx(4.0, rel=0.01)


class TestTradesAggregator:
    """Tests for TradesAggregator class."""
    
    @pytest.mark.asyncio
    async def test_start_stop(self, trades_aggregator):
        """Test starting and stopping aggregator."""
        assert not trades_aggregator.running
        
        await trades_aggregator.start()
        assert trades_aggregator.running
        
        await trades_aggregator.stop()
        assert not trades_aggregator.running
    
    @pytest.mark.asyncio
    async def test_subscribe_unsubscribe(self, trades_aggregator):
        """Test subscribing and unsubscribing to symbols."""
        await trades_aggregator.start()
        
        symbol = 'BTC/USDT'
        await trades_aggregator.subscribe(symbol)
        
        assert symbol in trades_aggregator.active_symbols
        assert trades_aggregator.is_subscribed(symbol)
        
        await trades_aggregator.unsubscribe(symbol)
        assert not trades_aggregator.is_subscribed(symbol)
        
        await trades_aggregator.stop()
    
    @pytest.mark.asyncio
    async def test_add_trade_and_metrics(self, trades_aggregator):
        """Test adding trades and retrieving metrics."""
        await trades_aggregator.start()
        
        symbol = 'BTC/USDT'
        await trades_aggregator.subscribe(symbol)
        
        current_ts = int(time.time() * 1000)
        
        # Add some trades
        for i in range(10):
            trade = Trade(
                timestamp=current_ts - (i * 1000),
                price=50000.0 + i * 10,
                amount=1.0,
                side='buy' if i % 2 == 0 else 'sell'
            )
            trades_aggregator.add_trade(symbol, trade)
        
        # Get metrics
        tpm = trades_aggregator.get_tpm(symbol, '60s')
        assert tpm > 0
        
        tps = trades_aggregator.get_tps(symbol)
        assert tps > 0
        
        vol_delta = trades_aggregator.get_vol_delta(symbol, 60)
        # Volume delta might be 0 initially, just check it's a number
        assert isinstance(vol_delta, (int, float))
        
        metrics = trades_aggregator.get_metrics(symbol)
        assert metrics is not None
        assert metrics.symbol == symbol
        
        await trades_aggregator.stop()
    
    def test_get_metrics_unsubscribed_symbol(self, trades_aggregator):
        """Test getting metrics for unsubscribed symbol."""
        tpm = trades_aggregator.get_tpm('UNKNOWN/SYMBOL')
        assert tpm == 0.0
        
        metrics = trades_aggregator.get_metrics('UNKNOWN/SYMBOL')
        assert metrics is None
