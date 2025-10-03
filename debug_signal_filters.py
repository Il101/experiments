#!/usr/bin/env python3
"""
Debug script to analyze why signals are not being generated
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from breakout_bot.config.settings import load_preset
from breakout_bot.scanner.market_scanner import MarketFilter
from breakout_bot.data.models import MarketData
import logging

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)

def test_market_filters():
    """Test market filters with sample data"""
    
    # Load ultra relaxed preset
    preset = load_preset("breakout_v1_ultra_relaxed")
    print(f"Testing preset: {preset.name}")
    print(f"Liquidity filters: {preset.liquidity_filters}")
    print(f"Volatility filters: {preset.volatility_filters}")
    print()
    
    # Create market filter
    market_filter = MarketFilter("test", preset)
    
    # Test with sample market data
    test_markets = [
        {
            "symbol": "BTC/USDT",
            "price": 50000.0,
            "volume_24h_usd": 2000000000,  # 2B
            "oi_usd": 1000000000,  # 1B
            "spread_bps": 2.0,
            "depth_0_5pct": 100000,
            "depth_0_3pct": 50000,
            "trades_per_minute": 10.0
        },
        {
            "symbol": "ETH/USDT", 
            "price": 3000.0,
            "volume_24h_usd": 1000000000,  # 1B
            "oi_usd": 500000000,  # 500M
            "spread_bps": 3.0,
            "depth_0_5pct": 50000,
            "depth_0_3pct": 25000,
            "trades_per_minute": 5.0
        },
        {
            "symbol": "SMALL/USDT",
            "price": 0.01,
            "volume_24h_usd": 5000000,  # 5M
            "oi_usd": 2000000,  # 2M
            "spread_bps": 10.0,
            "depth_0_5pct": 1000,
            "depth_0_3pct": 500,
            "trades_per_minute": 0.5
        }
    ]
    
    for market_data in test_markets:
        print(f"=== Testing {market_data['symbol']} ===")
        
        # Create MarketData object
        from breakout_bot.data.models import L2Depth
        l2_depth = L2Depth(
            bid_usd_0_5pct=market_data['depth_0_5pct'] / 2,
            ask_usd_0_5pct=market_data['depth_0_5pct'] / 2,
            bid_usd_0_3pct=market_data['depth_0_3pct'] / 2,
            ask_usd_0_3pct=market_data['depth_0_3pct'] / 2,
            spread_bps=market_data['spread_bps'],
            imbalance=0.0
        )
        
        market = MarketData(
            symbol=market_data['symbol'],
            price=market_data['price'],
            volume_24h_usd=market_data['volume_24h_usd'],
            oi_usd=market_data['oi_usd'],
            trades_per_minute=market_data['trades_per_minute'],
            l2_depth=l2_depth,
            timestamp=1234567890
        )
        
        # Test liquidity filters
        print("Liquidity filters:")
        liquidity_results = market_filter.apply_liquidity_filters(market)
        for filter_name, result in liquidity_results.items():
            status = "✅ PASS" if result.passed else "❌ FAIL"
            print(f"  {filter_name}: {status} - {result.reason}")
        
        # Test volatility filters (need to create mock ScanMetrics)
        from breakout_bot.scanner.market_scanner import ScanMetrics
        scan_metrics = ScanMetrics(
            vol_surge_1h=1.5,
            vol_surge_5m=2.0,
            oi_delta_24h=0.1,
            atr_quality=0.05,
            bb_width_pct=25.0,
            btc_correlation=0.8,
            trades_per_minute=10.0,
            liquidity_score=0.9,
            depth_score=0.8,
            spread_score=0.9
        )
        
        print("Volatility filters:")
        volatility_results = market_filter.apply_volatility_filters(market, scan_metrics)
        for filter_name, result in volatility_results.items():
            status = "✅ PASS" if result.passed else "❌ FAIL"
            print(f"  {filter_name}: {status} - {result.reason}")
        
        print()

if __name__ == "__main__":
    test_market_filters()
