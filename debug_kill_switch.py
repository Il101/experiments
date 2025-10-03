#!/usr/bin/env python3
"""
Debug script to test kill switch logic
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from breakout_bot.config.settings import load_preset
from breakout_bot.risk.risk_manager import RiskManager
from breakout_bot.data.models import Position, MarketData

def test_kill_switch():
    """Test kill switch logic"""
    
    # Load preset
    preset = load_preset("breakout_v1_relaxed")
    print(f"Preset: {preset.name}")
    print(f"Kill switch limit: {preset.risk.kill_switch_loss_limit:.2%}")
    print(f"Daily risk limit: {preset.risk.daily_risk_limit:.2%}")
    print()
    
    # Create risk manager
    risk_manager = RiskManager(preset)
    
    # Test with no positions
    positions = []
    account_equity = 10000.0
    
    print("=== Testing with no positions ===")
    print(f"Account equity: ${account_equity:,.2f}")
    
    # Check risk limits
    risk_status = risk_manager.risk_monitor.check_risk_limits(positions, account_equity)
    
    print(f"Kill switch triggered: {risk_status['kill_switch_triggered']}")
    print(f"Overall status: {risk_status['overall_status']}")
    print(f"Violations: {risk_status['violations']}")
    
    if risk_status['metrics']:
        metrics = risk_status['metrics']
        print(f"Max drawdown: {metrics.max_drawdown:.4f}")
        print(f"Daily PnL: ${metrics.daily_pnl:.2f}")
        print(f"Total equity: ${metrics.total_equity:.2f}")
        print(f"High water mark: {risk_manager.risk_monitor.portfolio_high_water_mark:.2f}")
    
    print()
    
    # Test signal evaluation
    print("=== Testing signal evaluation ===")
    
    # Create a mock signal
    from breakout_bot.data.models import Signal
    signal = Signal(
        symbol="TEST/USDT",
        side="long",
        entry=100.0,
        sl=95.0,
        level=100.0,
        strategy="momentum",
        reason="test",
        confidence=0.8,
        timestamp=1234567890
    )
    
    # Create mock market data
    market_data = MarketData(
        symbol="TEST/USDT",
        price=100.0,
        volume_24h_usd=1000000,
        oi_usd=500000,
        trades_per_minute=5.0,
        timestamp=1234567890
    )
    
    # Evaluate signal
    result = risk_manager.evaluate_signal_risk(signal, account_equity, positions, market_data)
    
    print(f"Signal approved: {result['approved']}")
    print(f"Reason: {result.get('reason', 'N/A')}")
    
    if result.get('risk_status'):
        risk_status = result['risk_status']
        print(f"Risk status kill switch: {risk_status['kill_switch_triggered']}")
        print(f"Risk status overall: {risk_status['overall_status']}")

if __name__ == "__main__":
    test_kill_switch()
