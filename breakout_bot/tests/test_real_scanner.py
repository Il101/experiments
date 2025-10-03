#!/usr/bin/env python3
"""
Test script for real scanner functionality with test data
"""

import asyncio
import logging
import pytest
from breakout_bot.scanner.market_scanner import BreakoutScanner
from breakout_bot.config.settings import load_preset
from breakout_bot.data.models import MarketData, Candle, L2Depth
from datetime import datetime, timedelta
import numpy as np

# Enable detailed logging
logging.basicConfig(level=logging.INFO)

@pytest.mark.asyncio
async def test_real_scanner():
    """Test scanner with realistic test data"""
    try:
        # Load preset
        preset = load_preset('breakout_v1')
        print(f'✅ Preset loaded: {preset.name}')
        
        # Create realistic test data
        test_markets = []
        
        # BTC/USDT - excellent candidate
        btc_candles = []
        base_price = 50000
        for i in range(100):
            price = base_price + np.random.normal(0, 100)
            candle = Candle(
                ts=int((datetime.now() - timedelta(minutes=5*i)).timestamp() * 1000),
                open=price,
                high=price + np.random.uniform(0, 200),
                low=price - np.random.uniform(0, 200),
                close=price + np.random.normal(0, 50),
                volume=np.random.uniform(1000, 5000)
            )
            btc_candles.append(candle)
        
        btc_data = MarketData(
            symbol='BTC/USDT',
            price=base_price,
            volume_24h_usd=50000000000,  # 50B volume
            oi_usd=1000000000,  # 1B OI
            oi_change_24h=0.05,
            trades_per_minute=150.0,
            atr_5m=200.0,
            atr_15m=300.0,
            bb_width_pct=2.5,
            btc_correlation=1.0,
            l2_depth=L2Depth(
                bid_usd_0_5pct=500000,
                ask_usd_0_5pct=500000,
                bid_usd_0_3pct=300000,
                ask_usd_0_3pct=300000,
                spread_bps=1.0,
                imbalance=0.1
            ),
            candles_5m=btc_candles,
            timestamp=int(datetime.now().timestamp() * 1000)
        )
        test_markets.append(btc_data)
        
        # ETH/USDT - good candidate
        eth_candles = []
        base_price = 3000
        for i in range(100):
            price = base_price + np.random.normal(0, 50)
            candle = Candle(
                ts=int((datetime.now() - timedelta(minutes=5*i)).timestamp() * 1000),
                open=price,
                high=price + np.random.uniform(0, 100),
                low=price - np.random.uniform(0, 100),
                close=price + np.random.normal(0, 25),
                volume=np.random.uniform(500, 2500)
            )
            eth_candles.append(candle)
        
        eth_data = MarketData(
            symbol='ETH/USDT',
            price=base_price,
            volume_24h_usd=20000000000,  # 20B volume
            oi_usd=500000000,  # 500M OI
            oi_change_24h=0.03,
            trades_per_minute=100.0,
            atr_5m=50.0,
            atr_15m=75.0,
            bb_width_pct=3.0,
            btc_correlation=0.8,
            l2_depth=L2Depth(
                bid_usd_0_5pct=200000,
                ask_usd_0_5pct=200000,
                bid_usd_0_3pct=120000,
                ask_usd_0_3pct=120000,
                spread_bps=1.5,
                imbalance=0.05
            ),
            candles_5m=eth_candles,
            timestamp=int(datetime.now().timestamp() * 1000)
        )
        test_markets.append(eth_data)
        
        # SOL/USDT - poor candidate (low volume)
        sol_candles = []
        base_price = 100
        for i in range(100):
            price = base_price + np.random.normal(0, 5)
            candle = Candle(
                ts=int((datetime.now() - timedelta(minutes=5*i)).timestamp() * 1000),
                open=price,
                high=price + np.random.uniform(0, 10),
                low=price - np.random.uniform(0, 10),
                close=price + np.random.normal(0, 2),
                volume=np.random.uniform(100, 500)
            )
            sol_candles.append(candle)
        
        sol_data = MarketData(
            symbol='SOL/USDT',
            price=base_price,
            volume_24h_usd=1000000000,  # 1B volume (low)
            oi_usd=50000000,  # 50M OI (low)
            oi_change_24h=0.01,
            trades_per_minute=20.0,  # Low activity
            atr_5m=5.0,
            atr_15m=7.5,
            bb_width_pct=1.0,
            btc_correlation=0.6,
            l2_depth=L2Depth(
                bid_usd_0_5pct=50000,
                ask_usd_0_5pct=50000,
                bid_usd_0_3pct=30000,
                ask_usd_0_3pct=30000,
                spread_bps=3.0,  # High spread
                imbalance=0.3
            ),
            candles_5m=sol_candles,
            timestamp=int(datetime.now().timestamp() * 1000)
        )
        test_markets.append(sol_data)
        
        print(f'✅ Created {len(test_markets)} test markets')
        
        # Create scanner
        scanner = BreakoutScanner(preset)
        print(f'✅ Scanner created')
        
        # Run scan
        print('🔍 Starting scan with realistic test data...')
        results = await scanner.scan_markets(test_markets, btc_data)
        print(f'✅ Scan results: {len(results)} candidates')
        
        # Display results
        if results:
            print("\n📊 SCAN RESULTS:")
            print("=" * 80)
            for i, result in enumerate(results, 1):
                print(f"{i}. {result.symbol}")
                print(f"   Score: {result.score:.3f}")
                print(f"   Price: ${result.market_data.price:,.2f}")
                print(f"   Volume: ${result.market_data.volume_24h_usd/1e9:.1f}B")
                print(f"   OI: ${result.market_data.oi_usd/1e6:.0f}M")
                print(f"   Trades/min: {result.market_data.trades_per_minute:.0f}")
                print(f"   Spread: {result.market_data.l2_depth.spread_bps:.1f} bps")
                print(f"   Filters passed: {sum(result.filter_results.values())}/{len(result.filter_results)}")
                print(f"   Failed filters: {[k for k, v in result.filter_results.items() if not v]}")
                print(f"   Levels: {len(result.levels)}")
                print()
        else:
            print("❌ No candidates found")
        
        print("✅ Real scanner test completed successfully!")
        
    except Exception as e:
        print(f'❌ Error: {type(e).__name__}: {str(e)}')

if __name__ == "__main__":
    asyncio.run(test_real_scanner())
