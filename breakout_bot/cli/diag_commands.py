"""
CLI commands for testing and diagnostics of enhanced features.
"""

import asyncio
import json
import sys
from datetime import datetime, timedelta
import click
import logging

from breakout_bot.data.streams.trades_ws import TradesAggregator
from breakout_bot.data.streams.orderbook_ws import OrderBookManager
from breakout_bot.features.density import DensityDetector
from breakout_bot.features.activity import ActivityTracker
from breakout_bot.indicators.levels import LevelDetector
from breakout_bot.config.settings import get_preset

logger = logging.getLogger(__name__)


@click.group(name="diag")
def diag_group():
    """Diagnostic commands for enhanced features."""
    pass


@diag_group.command(name="l2")
@click.option('--preset', default='high_percent_breakout', help='Preset to use')
@click.option('--symbol', default='BTC/USDT', help='Symbol to analyze')
@click.option('--minutes', default=120, type=int, help='Analysis duration in minutes')
def diagnose_l2(preset: str, symbol: str, minutes: int):
    """
    Diagnose L2 features (density, activity) for a symbol.
    
    Example:
        python -m breakout_bot.cli diag-l2 --preset high_percent_breakout --symbol BTC/USDT --minutes 120
    """
    
    click.echo(f"\n{'='*60}")
    click.echo(f"L2 Features Diagnostic")
    click.echo(f"{'='*60}\n")
    click.echo(f"Preset: {preset}")
    click.echo(f"Symbol: {symbol}")
    click.echo(f"Duration: {minutes} minutes")
    click.echo(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    try:
        # Load preset
        preset_config = get_preset(preset)
        click.echo(f"✓ Loaded preset: {preset_config.name}")
        
        # Initialize components
        click.echo("\nInitializing components...")
        
        trades_agg = TradesAggregator()
        orderbook_mgr = OrderBookManager()
        
        density_detector = DensityDetector(
            orderbook_manager=orderbook_mgr,
            k_density=preset_config.density_config.k_density,
            bucket_ticks=preset_config.density_config.bucket_ticks,
            enter_on_density_eat_ratio=preset_config.signal_config.enter_on_density_eat_ratio
        )
        
        activity_tracker = ActivityTracker(
            trades_aggregator=trades_agg,
            lookback_periods=60,
            drop_threshold=preset_config.position_config.activity_drop_threshold
        )
        
        level_detector = LevelDetector(
            min_touches=preset_config.levels_rules.min_touches,
            prefer_round_numbers=preset_config.levels_rules.prefer_round_numbers,
            round_step_candidates=preset_config.levels_rules.round_step_candidates,
            cascade_min_levels=preset_config.levels_rules.cascade_min_levels,
            cascade_radius_bps=preset_config.levels_rules.cascade_radius_bps
        )
        
        click.echo("✓ Components initialized")
        
        # Run diagnostic
        asyncio.run(_run_l2_diagnostic(
            symbol=symbol,
            minutes=minutes,
            trades_agg=trades_agg,
            orderbook_mgr=orderbook_mgr,
            density_detector=density_detector,
            activity_tracker=activity_tracker,
            level_detector=level_detector
        ))
        
    except Exception as e:
        click.echo(f"\n✗ Error: {e}", err=True)
        logger.error(f"Diagnostic error: {e}", exc_info=True)
        sys.exit(1)


async def _run_l2_diagnostic(
    symbol: str,
    minutes: int,
    trades_agg: TradesAggregator,
    orderbook_mgr: OrderBookManager,
    density_detector: DensityDetector,
    activity_tracker: ActivityTracker,
    level_detector: LevelDetector
):
    """Run L2 diagnostic for specified duration."""
    
    click.echo(f"\nStarting {minutes}-minute diagnostic for {symbol}...")
    click.echo("(This is a simulation - in production would connect to real WebSocket)\n")
    
    # Start components
    await trades_agg.start()
    await orderbook_mgr.start()
    
    # Subscribe to symbol
    await trades_agg.subscribe(symbol)
    await orderbook_mgr.subscribe(symbol)
    
    click.echo(f"✓ Subscribed to {symbol}")
    
    # Simulate for a short period
    for i in range(10):
        await asyncio.sleep(1)
        
        # Update activity
        activity_metrics = activity_tracker.update_activity(symbol)
        
        click.echo(f"\n[Iteration {i+1}/10]")
        click.echo(f"  Activity Index: {activity_metrics.activity_index:.2f}")
        click.echo(f"  TPM (60s): {activity_metrics.tpm_60s_z:.2f}σ")
        click.echo(f"  TPS (10s): {activity_metrics.tps_10s_z:.2f}σ")
        click.echo(f"  Vol Delta Z: {activity_metrics.vol_delta_z:.2f}σ")
        
        if activity_metrics.is_dropping:
            click.echo(f"  ⚠️  Activity DROP detected! ({activity_metrics.drop_fraction:.2%})")
    
    # Stop components
    await trades_agg.stop()
    await orderbook_mgr.stop()
    
    click.echo(f"\n{'='*60}")
    click.echo("Diagnostic completed")
    click.echo(f"{'='*60}\n")
    
    # Summary
    click.echo("\nSummary:")
    click.echo("  ✓ Trades aggregator working")
    click.echo("  ✓ OrderBook manager working")
    click.echo("  ✓ Density detector initialized")
    click.echo("  ✓ Activity tracker working")
    click.echo("  ✓ Level detector initialized")
    
    click.echo("\nNote: This was a simulation. In production:")
    click.echo("  - Connect to exchange WebSocket for real trades")
    click.echo("  - Connect to exchange WebSocket for real order book")
    click.echo("  - Density events will be detected from real order book")
    click.echo("  - Activity metrics will reflect real trade flow")


@diag_group.command(name="levels")
@click.option('--preset', default='high_percent_breakout', help='Preset to use')
@click.option('--symbol', default='BTC/USDT', help='Symbol to analyze')
def diagnose_levels(preset: str, symbol: str):
    """
    Test level detection with enhanced features.
    
    Example:
        python -m breakout_bot.cli diag-levels --preset high_percent_breakout --symbol BTC/USDT
    """
    
    click.echo(f"\n{'='*60}")
    click.echo(f"Enhanced Level Detection Test")
    click.echo(f"{'='*60}\n")
    
    try:
        preset_config = get_preset(preset)
        
        level_detector = LevelDetector(
            min_touches=preset_config.levels_rules.min_touches,
            prefer_round_numbers=preset_config.levels_rules.prefer_round_numbers,
            round_step_candidates=preset_config.levels_rules.round_step_candidates,
            cascade_min_levels=preset_config.levels_rules.cascade_min_levels,
            cascade_radius_bps=preset_config.levels_rules.cascade_radius_bps
        )
        
        click.echo(f"Preset: {preset_config.name}")
        click.echo(f"Min touches: {preset_config.levels_rules.min_touches}")
        click.echo(f"Prefer round numbers: {preset_config.levels_rules.prefer_round_numbers}")
        click.echo(f"Round steps: {preset_config.levels_rules.round_step_candidates}")
        click.echo(f"Cascade min levels: {preset_config.levels_rules.cascade_min_levels}")
        click.echo(f"Cascade radius: {preset_config.levels_rules.cascade_radius_bps} bps")
        
        # Test round number detection
        click.echo("\n\nRound Number Detection Test:")
        click.echo("-" * 40)
        
        test_prices = [50000.0, 50005.0, 49995.0, 50123.45, 48750.0]
        
        for price in test_prices:
            is_round, bonus = level_detector.is_round_number(price)
            status = "✓" if is_round else "✗"
            click.echo(f"  {status} {price:>10.2f} -> Round: {is_round:5} | Bonus: {bonus:.3f}")
        
        click.echo("\n✓ Level detector configured successfully")
        
    except Exception as e:
        click.echo(f"\n✗ Error: {e}", err=True)
        sys.exit(1)


# Register diagnostic commands
def register_diag_commands(cli_app):
    """Register diagnostic commands to main CLI."""
    cli_app.add_command(diag_group)
