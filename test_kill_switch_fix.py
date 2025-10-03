#!/usr/bin/env python3
"""
Test script to verify kill switch fix
"""

import sys
import os
import asyncio
import time
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from breakout_bot.config.settings import load_preset
from breakout_bot.data.models import MarketData, L2Depth, Signal, ScanResult, TradingLevel, Candle, Position
from breakout_bot.scanner.market_scanner import MarketFilter, ScanMetrics
from breakout_bot.signals.signal_generator import SignalGenerator
from breakout_bot.risk.risk_manager import RiskManager, RiskMonitor
import logging

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)

def create_test_market_data(symbol: str, price: float) -> MarketData:
    """Create test market data that passes all filters"""
    
    l2_depth = L2Depth(
        bid_usd_0_5pct=50000,  # $50k
        ask_usd_0_5pct=50000,  # $50k
        bid_usd_0_3pct=25000,  # $25k
        ask_usd_0_3pct=25000,  # $25k
        spread_bps=2.0,  # 2 bps spread
        imbalance=0.1  # 10% imbalance
    )
    
    return MarketData(
        symbol=symbol,
        price=price,
        volume_24h_usd=100000000,  # $100M volume
        oi_usd=50000000,  # $50M OI
        trades_per_minute=10.0,
        l2_depth=l2_depth,
        timestamp=int(time.time())
    )

def create_test_candles(price: float, count: int = 100) -> list[Candle]:
    """Create test candles for signal generation"""
    
    candles = []
    current_time = int(time.time() * 1000)
    base_price = price
    
    for i in range(count):
        # Create some price movement
        price_change = (i % 10 - 5) * 0.001  # Small price changes
        candle_price = base_price * (1 + price_change)
        
        candle = Candle(
            ts=current_time - (count - i) * 300000,  # 5-minute intervals
            open=candle_price * 0.999,
            high=candle_price * 1.002,
            low=candle_price * 0.998,
            close=candle_price,
            volume=1000000 + i * 1000  # Increasing volume
        )
        candles.append(candle)
    
    return candles

def create_test_scan_metrics() -> ScanMetrics:
    """Create test scan metrics that pass volatility filters"""
    
    return ScanMetrics(
        vol_surge_1h=2.0,  # 2x volume surge
        vol_surge_5m=3.0,  # 3x volume surge
        oi_delta_24h=0.1,  # 10% OI change
        atr_quality=0.05,  # 5% ATR (within 0.001-0.50 range)
        bb_width_pct=30.0,  # 30% BB width
        btc_correlation=0.7,  # 70% correlation
        trades_per_minute=10.0,
        liquidity_score=0.9,
        depth_score=0.8,
        spread_score=0.9
    )

def create_test_level(price: float) -> TradingLevel:
    """Create test trading level"""
    
    current_time = int(time.time() * 1000)
    
    return TradingLevel(
        price=price,
        level_type="resistance",
        touch_count=3,
        strength=0.8,
        first_touch_ts=current_time - 7200000,  # 2 hours ago
        last_touch_ts=current_time - 3600000   # 1 hour ago
    )

async def test_kill_switch_fix():
    """Test kill switch fix with different scenarios"""
    
    print("🔧 Testing Kill Switch Fix")
    print("=" * 50)
    
    # Load preset
    preset = load_preset("breakout_v1_ultra_relaxed")
    print(f"📋 Using preset: {preset.name}")
    print()
    
    # Create test market data
    market_data = create_test_market_data("TEST/USDT", 100.0)
    test_candles = create_test_candles(100.0, 100)
    market_data.candles_5m = test_candles
    
    # Create test scan result
    test_level = create_test_level(100.0)
    scan_result = ScanResult(
        symbol="TEST/USDT",
        score=8.5,
        rank=1,
        market_data=market_data,
        filter_results={
            "min_24h_volume": True,
            "min_oi": True,
            "max_spread": True,
            "min_depth_0_5pct": True,
            "min_depth_0_3pct": True,
            "min_trades_per_minute": True,
            "atr_range": True,
            "bb_width": True,
            "volume_surge_1h": True,
            "volume_surge_5m": True
        },
        score_components={
            "volume_score": 0.9,
            "volatility_score": 0.8,
            "momentum_score": 0.85,
            "liquidity_score": 0.9
        },
        levels=[test_level],
        timestamp=int(time.time())
    )
    
    # Test signal generation
    signal_generator = SignalGenerator(preset)
    signal = await signal_generator.generate_signal(scan_result)
    
    if not signal:
        print("❌ No signal generated")
        return
    
    print(f"✅ Signal generated: {signal.symbol} {signal.side} at ${signal.entry}")
    print()
    
    # Test scenario 1: Fresh start (portfolio_high_water_mark = 0.0)
    print("🧪 Test 1: Fresh start (portfolio_high_water_mark = 0.0)")
    risk_manager1 = RiskManager(preset)
    positions = []
    account_equity = 10000.0
    
    risk_result1 = risk_manager1.evaluate_signal_risk(signal, account_equity, positions, market_data)
    print(f"   Approved: {risk_result1['approved']}")
    if not risk_result1['approved']:
        print(f"   Reason: {risk_result1.get('reason', 'Unknown')}")
    else:
        print("   ✅ Signal approved!")
    print()
    
    # Test scenario 2: High water mark from previous session
    print("🧪 Test 2: High water mark from previous session (portfolio_high_water_mark = 15000)")
    risk_manager2 = RiskManager(preset)
    # Simulate previous session with higher equity
    risk_manager2.risk_monitor.portfolio_high_water_mark = 15000.0
    
    risk_result2 = risk_manager2.evaluate_signal_risk(signal, account_equity, positions, market_data)
    print(f"   Approved: {risk_result2['approved']}")
    if not risk_result2['approved']:
        print(f"   Reason: {risk_result2.get('reason', 'Unknown')}")
        
        # Debug metrics
        if 'risk_status' in risk_result2 and 'metrics' in risk_result2['risk_status']:
            metrics = risk_result2['risk_status']['metrics']
            print(f"   Max drawdown: {metrics.max_drawdown:.2%}")
            print(f"   High water mark: ${risk_manager2.risk_monitor.portfolio_high_water_mark:,.2f}")
            print(f"   Current equity: ${account_equity:,.2f}")
    else:
        print("   ✅ Signal approved!")
    print()
    
    # Test scenario 3: Current equity higher than high water mark
    print("🧪 Test 3: Current equity higher than high water mark")
    risk_manager3 = RiskManager(preset)
    risk_manager3.risk_monitor.portfolio_high_water_mark = 8000.0  # Lower than current
    account_equity_high = 12000.0
    
    risk_result3 = risk_manager3.evaluate_signal_risk(signal, account_equity_high, positions, market_data)
    print(f"   Approved: {risk_result3['approved']}")
    if not risk_result3['approved']:
        print(f"   Reason: {risk_result3.get('reason', 'Unknown')}")
    else:
        print("   ✅ Signal approved!")
    print()
    
    print("🎯 Kill switch fix test complete!")

if __name__ == "__main__":
    asyncio.run(test_kill_switch_fix())

