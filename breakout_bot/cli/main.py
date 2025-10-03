"""
CLI interface for Breakout Bot Trading System.

This module provides command-line interface using Typer for easy interaction
with the trading system.
"""

import asyncio
import os
import typer
from typing import Optional, Dict
from datetime import datetime
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich import print as rprint
import json

from ..core.engine import OptimizedOrchestraEngine
from ..config.settings import SystemConfig, get_available_presets, get_preset
from ..exchange import ExchangeClient, MarketDataProvider
from ..exchange.exchange_client import close_all_connections
from ..diagnostics.runner import DiagnosticsRunner, DiagnosticsProfileResult
from ..diagnostics.reporting import DiagnosticsReportBuilder

# Import diagnostic commands
from .diag_commands import diag

app = typer.Typer(name="breakout-bot", help="Breakout Bot Trading System")
console = Console()

# Add diagnostic commands
app.add_typer(diag, name="diag")


@app.command()
def trade(
    preset: str = typer.Argument(..., help="Trading preset name"),
    paper: bool = typer.Option(False, "--paper", help="Use paper trading mode"),
    live: bool = typer.Option(False, "--live", help="Use live trading mode"),
    log_level: str = typer.Option("INFO", help="Logging level"),
    symbols: Optional[str] = typer.Option(
        None,
        "--symbols",
        help="Comma-separated symbol whitelist for the engine",
    ),
):
    """Start trading with specified preset."""
    
    if paper and live:
        typer.echo("Cannot specify both --paper and --live", err=True)
        raise typer.Exit(1)
    
    # Set trading mode
    trading_mode = "live" if live else "paper"
    
    rprint(f"[bold green]Starting Breakout Bot[/bold green]")
    rprint(f"Preset: [yellow]{preset}[/yellow]")
    rprint(f"Mode: [cyan]{trading_mode.upper()}[/cyan]")
    
    # Create system config
    system_config = SystemConfig.from_env()
    system_config.trading_mode = trading_mode
    system_config.log_level = log_level
    
    # Run trading engine
    manual_symbols = (
        [sym.strip().upper() for sym in symbols.split(',') if sym.strip()]
        if symbols
        else None
    )

    async def run_trading():
        engine = OptimizedOrchestraEngine(
            preset_name=preset,
            system_config=system_config,
            symbols_whitelist=manual_symbols
        )
        await engine.start()
    
    try:
        asyncio.run(run_trading())
    except KeyboardInterrupt:
        rprint("\n[yellow]Shutting down gracefully...[/yellow]")


@app.command()
def scan(
    preset: str = typer.Argument(..., help="Scanning preset name"),
    exchange: str = typer.Option("bybit", help="Exchange to scan"),
    limit: int = typer.Option(10, help="Maximum results to show"),
    output: Optional[str] = typer.Option(None, help="Output file for results"),
    symbols: Optional[str] = typer.Option(
        None,
        "--symbols",
        help="Comma-separated list of symbols to scan (overrides automatic universe)",
    ),
):
    """Scan markets for breakout opportunities."""
    
    rprint(f"[bold blue]Scanning Markets[/bold blue]")
    rprint(f"Preset: [yellow]{preset}[/yellow]")
    rprint(f"Exchange: [cyan]{exchange}[/cyan]")
    
    async def run_scan():
        # This would be a scan-only version
        from ..config import get_preset
        from ..scanner import BreakoutScanner
        
        # Parse symbol overrides
        manual_symbols = (
            [sym.strip().upper() for sym in symbols.split(',') if sym.strip()]
            if symbols
            else None
        )

        # Load preset
        trading_preset = get_preset(preset)
        
        # Create exchange client in live mode for real data, but with paper trading
        system_config = SystemConfig.from_env()
        system_config.trading_mode = "live"  # Use live data
        system_config.exchange = exchange  # Use specified exchange (Bybit supports public data)
        system_config.paper_starting_balance = 10000  # Set paper balance
        
        async with ExchangeClient(system_config) as exchange_client:
            market_data_provider = MarketDataProvider(exchange_client)
            scanner = BreakoutScanner(trading_preset)
            
            # Get markets
            if manual_symbols:
                symbols_list = manual_symbols
                rprint(f"Fetching data for custom list: {', '.join(symbols_list)}")
            else:
                symbols_list = await exchange_client.fetch_markets()
                symbol_limit = int(os.getenv('CLI_LIVE_SYMBOL_LIMIT', '40')) if exchange.lower() == 'bybit' else None
                if symbol_limit and symbol_limit > 0:
                    original_count = len(symbols_list)
                    symbols_list = symbols_list[:symbol_limit]
                    rprint(f"Fetching data for {len(symbols_list)} из {original_count} символов (ограничение Bybit)")
                else:
                    rprint(f"Fetching data for {len(symbols_list)} symbols...")
            
            # Get market data
            market_data = await market_data_provider.get_multiple_market_data(symbols_list)
            market_data_list = list(market_data.values())
            
            # Get BTC data
            btc_data = market_data.get('BTC/USDT')
            
            # Run scan
            results = await scanner.scan_markets(market_data_list, btc_data)
            
            # Display results
            display_scan_results(results[:limit])
            
            # Save to file if requested
            if output:
                save_scan_results(results, output)
                rprint(f"Results saved to: [green]{output}[/green]")

        await close_all_connections()
    
    try:
        asyncio.run(run_scan())
    except KeyboardInterrupt:
        rprint("\n[yellow]Scan interrupted[/yellow]")


@app.command()
def presets():
    """List available trading presets."""
    
    available_presets = get_available_presets()
    
    table = Table(title="Available Trading Presets")
    table.add_column("Name", style="cyan")
    table.add_column("Description", style="green")
    table.add_column("Target Markets", style="yellow")
    
    for preset_name in available_presets:
        try:
            preset = get_preset(preset_name)
            table.add_row(
                preset.name,
                preset.description,
                preset.target_markets
            )
        except Exception as e:
            table.add_row(preset_name, f"Error loading: {e}", "")
    
    console.print(table)


@app.command()
def status(
    preset: str = typer.Argument(..., help="Preset name for status check")
):
    """Show system status and metrics."""
    
    # This would connect to a running instance or show saved state
    rprint("[yellow]Status command not yet implemented[/yellow]")
    rprint("This would show:")
    rprint("- Current system state")
    rprint("- Open positions")
    rprint("- Risk metrics")
    rprint("- Recent performance")


@app.command()
def diag(
    preset: str = typer.Argument(..., help="Base preset name"),
    start: datetime = typer.Option(..., help="Start datetime (ISO 8601)"),
    end: datetime = typer.Option(..., help="End datetime (ISO 8601)"),
    symbol: str = typer.Option("BTC/USDT", help="Symbol to diagnose"),
    diag_preset: Optional[str] = typer.Option(None, help="Optional override for diagnostic preset (defaults to preset+'_diag')"),
):
    """Run diagnostics over a historical window with baseline vs relaxed thresholds."""

    os.environ['DEBUG_DIAG'] = '1'

    system_config = SystemConfig.from_env()
    system_config.debug_diag = True

    base_preset = get_preset(preset)
    diag_preset_name = diag_preset or f"{preset}_diag"
    try:
        relaxed_preset = get_preset(diag_preset_name)
    except Exception:
        relaxed_preset = base_preset

    async def _run() -> Dict[str, DiagnosticsProfileResult]:
        runner = DiagnosticsRunner(system_config, symbol, start, end)
        profiles = {'A': base_preset, 'B': relaxed_preset}
        try:
            return await runner.run_profiles(profiles)
        finally:
            await runner.close()

    results = asyncio.run(_run())

    report_dir = Path('reports')
    report_dir.mkdir(parents=True, exist_ok=True)

    log_paths = [res.diagnostics_log for res in results.values()]
    aggregate_report = DiagnosticsReportBuilder(log_paths).build()

    summary_path = report_dir / 'diag_summary.md'
    with summary_path.open('w', encoding='utf-8') as fp:
        fp.write(f"# Diagnostics Summary for {symbol}\n\n")
        fp.write(f"Window: {start.isoformat()} → {end.isoformat()}\n\n")
        for profile_name, res in results.items():
            fp.write(f"## Profile {profile_name}\n")
            fp.write(f"Bars analysed: {res.bars}\n\n")
            candidates_per_bar = res.candidates / res.bars if res.bars else 0.0
            fp.write(
                f"- Candidates/bar: {candidates_per_bar:.2f}\n"
                f"- Passed filters: {res.passed_filters}/{res.candidates} ({res.pass_rate*100:.1f}% )\n"
                f"- Momentum signals: {res.momentum_signals}\n"
                f"- Retest signals: {res.retest_signals}\n"
                f"- Diagnostics log: {res.diagnostics_log}\n"
            )
            fp.write("- Top reasons:\n")
            for reason, count in res.reasons[:5]:
                fp.write(f"  - {reason}: {count}\n")
            fp.write("\n")

        fp.write("## Aggregate Reasons\n")
        for reason, count in aggregate_report.get('reasons', [])[:10]:
            fp.write(f"- {reason}: {count}\n")
        fp.write("\n")

        recommendations = aggregate_report.get('recommendations', [])
        if recommendations:
            fp.write("## Threshold Suggestions\n")
            for item in recommendations:
                fp.write(f"- {item}\n")

    console.print(f"Diagnostics summary written to [green]{summary_path}[/green]")
    console.print("Profile breakdown:")
    for name, res in results.items():
        console.print(
            f"[cyan]{name}[/cyan] candidates/bar={res.candidates / res.bars if res.bars else 0:.2f} "
            f"pass_rate={res.pass_rate*100:.1f}% signals={res.total_signals}"
        )


@app.command()
def backtest(
    preset: str = typer.Argument(..., help="Preset for backtesting"),
    start: str = typer.Option("2024-01-01", help="Start date (YYYY-MM-DD)"),
    end: str = typer.Option("2024-06-01", help="End date (YYYY-MM-DD)"),
    output: Optional[str] = typer.Option(None, help="Output file for results")
):
    """Run backtest on historical data."""
    
    rprint(f"[bold magenta]Backtesting[/bold magenta]")
    rprint(f"Preset: [yellow]{preset}[/yellow]")
    rprint(f"Period: [cyan]{start}[/cyan] to [cyan]{end}[/cyan]")
    
    # This would implement backtesting logic
    rprint("[yellow]Backtest functionality not yet implemented[/yellow]")
    rprint("This would:")
    rprint("- Load historical data")
    rprint("- Simulate trading with preset")
    rprint("- Calculate performance metrics")
    rprint("- Generate reports")


def display_scan_results(results):
    """Display scan results in a nice table."""
    
    if not results:
        rprint("[red]No scan results found[/red]")
        return
    
    table = Table(title="Market Scan Results")
    table.add_column("Rank", style="dim")
    table.add_column("Symbol", style="cyan")
    table.add_column("Score", style="green")
    table.add_column("Price", style="yellow")
    table.add_column("24h Vol", style="blue")
    table.add_column("Levels", style="magenta")
    table.add_column("Filters", style="white")
    
    for result in results:
        # Format volume
        vol_str = f"${result.market_data.volume_24h_usd/1e6:.1f}M"
        
        # Count levels
        levels_str = str(len(result.levels))
        
        # Filter status
        passed_filters = sum(1 for passed in result.filter_results.values() if passed)
        total_filters = len(result.filter_results)
        filter_str = f"{passed_filters}/{total_filters}"
        
        table.add_row(
            str(result.rank),
            result.symbol,
            f"{result.score:.3f}",
            f"{result.market_data.price:.6f}",
            vol_str,
            levels_str,
            filter_str
        )
    
    console.print(table)


def save_scan_results(results, filename: str):
    """Save scan results to JSON file."""
    
    # Convert results to serializable format
    serializable_results = []
    
    for result in results:
        serializable_results.append({
            'rank': result.rank,
            'symbol': result.symbol,
            'score': result.score,
            'price': result.market_data.price,
            'volume_24h_usd': result.market_data.volume_24h_usd,
            'levels_count': len(result.levels),
            'filter_results': result.filter_results,
            'score_components': result.score_components,
            'timestamp': result.timestamp
        })
    
    with open(filename, 'w') as f:
        json.dump(serializable_results, f, indent=2)


if __name__ == "__main__":
    app()
