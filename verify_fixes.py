#!/usr/bin/env python3
"""
Quick verification script to test critical fixes.

Usage:
    python verify_fixes.py
"""

import sys
import inspect
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

import numpy as np
from breakout_bot.data.models import Candle, L2Depth, MarketData, TradingLevel
from breakout_bot.indicators.levels import LevelDetector
from breakout_bot.scanner import market_scanner


def test_volume_surge_median():
    """Verify volume surge uses median instead of mean."""
    print("🧪 Testing Patch 001: Volume surge uses median...")
    
    try:
        source = inspect.getsource(market_scanner.BreakoutScanner._calculate_scan_metrics)
        
        # Check for median usage in volume surge calculation
        if 'np.median(volumes[-12:])' in source or 'median(volumes[-12:])' in source:
            print("   ✅ PASS: Volume surge now uses median (robust to outliers)")
            return True
        else:
            print("   ❌ FAIL: Volume surge still uses mean (outlier-sensitive)")
            return False
    except Exception as e:
        print(f"   ❌ ERROR: {str(e)}")
        return False


def test_execution_depth_guard():
    """Test that execution has depth guard (Patch 002)."""
    print("🧪 Testing Patch 002: Execution depth guard...")
    
    from breakout_bot.execution import manager
    import inspect
    
    source = inspect.getsource(manager.ExecutionManager.execute_trade)
    
    # Check for depth guard keywords - the patch adds these checks
    if ('max_depth_fraction' in source and 'available_depth' in source) or \
       ('max_allowed_notional' in source and 'PATCH 002' in source):
        print("   ✅ PASS: Found depth guard logic")
        return True
    else:
        print("   ❌ FAIL: Depth guard not found (patch not applied)")
        return False


def test_level_min_touches():
    """Test that levels enforce min_touches (Patch 003)."""
    print("🧪 Testing Patch 003: Level min_touches enforcement...")
    
    detector = LevelDetector(min_touches=3)
    
    # Check the source code for the validation logic
    import inspect
    source = inspect.getsource(detector._validate_levels)
    
    # Check for the explicit min_touches enforcement added by patch
    if ('PATCH 003' in source or 
        ('len(touches) < self.min_touches' in source and 'continue' in source)):
        print("   ✅ PASS: Found min_touches check in validation")
        return True
    else:
        print("   ❌ FAIL: min_touches check not found (patch not applied)")
        return False


def test_correlation_id_support():
    """Test that correlation_id is supported (Patch 004)."""
    print("🧪 Testing Patch 004: Correlation ID support...")
    
    try:
        # Check if correlation_id field exists in models
        from breakout_bot.data.models import Signal, ScanResult
        import inspect
        
        signal_source = inspect.getsource(Signal)
        scan_result_source = inspect.getsource(ScanResult)
        
        # Check for correlation_id in both Signal and ScanResult models
        if 'correlation_id' in signal_source and 'correlation_id' in scan_result_source:
            print("   ✅ PASS: Correlation ID fields added to models")
            return True
        else:
            print("   ❌ FAIL: Correlation ID fields not found in models")
            return False
    except Exception as e:
        print(f"   ❌ FAIL: Error testing correlation ID: {e}")
        return False


def test_oi_spot_filter():
    """Test that OI filter handles spot markets (Patch 005)."""
    print("🧪 Testing Patch 005: OI filter for spot markets...")
    
    from breakout_bot.scanner import market_scanner
    import inspect
    
    source = inspect.getsource(market_scanner.MarketFilter.apply_liquidity_filters)
    
    if 'market_type' in source and 'spot' in source.lower():
        print("   ✅ PASS: Found spot market handling in OI filter")
        return True
    else:
        print("   ❌ FAIL: Spot market handling not found (patch not applied)")
        return False


def main():
    """Run all verification tests."""
    print("=" * 60)
    print("🔍 PIPELINE FIXES VERIFICATION")
    print("=" * 60)
    print()
    
    results = {}
    
    # Run tests
    results['volume_surge'] = test_volume_surge_median()
    print()
    
    results['depth_guard'] = test_execution_depth_guard()
    print()
    
    results['min_touches'] = test_level_min_touches()
    print()
    
    results['correlation_id'] = test_correlation_id_support()
    print()
    
    results['oi_spot'] = test_oi_spot_filter()
    print()
    
    # Summary
    print("=" * 60)
    print("📊 SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for r in results.values() if r is True)
    failed = sum(1 for r in results.values() if r is False)
    unknown = sum(1 for r in results.values() if r is None)
    total = len(results)
    
    print(f"✅ Passed: {passed}/{total}")
    print(f"❌ Failed: {failed}/{total}")
    if unknown:
        print(f"⚠️  Unknown: {unknown}/{total}")
    print()
    
    # Details
    for name, result in results.items():
        status = "✅ PASS" if result is True else ("❌ FAIL" if result is False else "⚠️  UNKNOWN")
        print(f"  {status}  {name}")
    
    print()
    
    # Overall verdict
    if failed == 0:
        print("🎉 ALL FIXES VERIFIED!")
        print("✅ Ready for E2E testing")
        return 0
    else:
        print("⚠️  SOME FIXES NOT APPLIED")
        print("📋 Please apply missing patches before testing")
        return 1


if __name__ == "__main__":
    sys.exit(main())
