#!/usr/bin/env python3
"""
Quick visual comparison of all 4 strategy presets.
Shows key differences at a glance.
"""

from breakout_bot.config.settings import load_preset


def print_separator(char='=', length=80):
    """Print a separator line."""
    print(char * length)


def print_header(text, char='='):
    """Print a centered header."""
    print_separator(char)
    print(f' {text} '.center(80, char))
    print_separator(char)


def compare_presets():
    """Compare all video strategy presets."""
    
    presets = ['scalping', 'conservative', 'aggressive', 'swing']
    preset_data = {}
    
    print_header('🎯 STRATEGY PRESETS COMPARISON', '=')
    print()
    
    # Load all presets
    for name in presets:
        preset_data[name] = load_preset(f'video_strategy_{name}')
    
    # Compare Risk Management
    print_header('💰 RISK MANAGEMENT', '-')
    print(f"{'Metric':<25} {'Scalping':<15} {'Conservative':<15} {'Aggressive':<15} {'Swing':<15}")
    print_separator('-')
    
    for name in presets:
        p = preset_data[name]
        if name == 'scalping':
            print(f"{'Risk per Trade':<25} ", end='')
        print(f"{p.risk.risk_per_trade*100:>13.1f}%  ", end='')
    print()
    
    for name in presets:
        p = preset_data[name]
        if name == 'scalping':
            print(f"{'Max Positions':<25} ", end='')
        print(f"{p.risk.max_concurrent_positions:>14d}   ", end='')
    print()
    
    for name in presets:
        p = preset_data[name]
        if name == 'scalping':
            print(f"{'Daily Risk Limit':<25} ", end='')
        print(f"{p.risk.daily_risk_limit*100:>13.1f}%  ", end='')
    print()
    
    for name in presets:
        p = preset_data[name]
        if name == 'scalping':
            print(f"{'Kill Switch':<25} ", end='')
        print(f"{p.risk.kill_switch_loss_limit*100:>13.1f}%  ", end='')
    print()
    
    for name in presets:
        p = preset_data[name]
        if name == 'scalping':
            print(f"{'Max Position Size':<25} ", end='')
        print(f"${p.risk.max_position_size_usd:>12,}  ", end='')
    print()
    print()
    
    # Compare TP Configuration
    print_header('📈 TAKE PROFIT CONFIGURATION', '-')
    print(f"{'Metric':<25} {'Scalping':<15} {'Conservative':<15} {'Aggressive':<15} {'Swing':<15}")
    print_separator('-')
    
    for name in presets:
        p = preset_data[name]
        if name == 'scalping':
            print(f"{'Number of TP Levels':<25} ", end='')
        print(f"{len(p.position_config.tp_levels):>14d}   ", end='')
    print()
    
    for name in presets:
        p = preset_data[name]
        if name == 'scalping':
            print(f"{'First TP':<25} ", end='')
        first_tp = p.position_config.tp_levels[0]
        print(f"{first_tp.reward_multiple:>13.1f}R  ", end='')
    print()
    
    for name in presets:
        p = preset_data[name]
        if name == 'scalping':
            print(f"{'Last TP':<25} ", end='')
        last_tp = p.position_config.tp_levels[-1]
        print(f"{last_tp.reward_multiple:>13.1f}R  ", end='')
    print()
    
    for name in presets:
        p = preset_data[name]
        if name == 'scalping':
            print(f"{'Total TP Size':<25} ", end='')
        total = sum(tp.size_pct for tp in p.position_config.tp_levels)
        print(f"{total*100:>13.0f}%  ", end='')
    print()
    print()
    
    # Compare Position Management
    print_header('🛡️  POSITION MANAGEMENT', '-')
    print(f"{'Metric':<25} {'Scalping':<15} {'Conservative':<15} {'Aggressive':<15} {'Swing':<15}")
    print_separator('-')
    
    for name in presets:
        p = preset_data[name]
        if name == 'scalping':
            print(f"{'SL Mode':<25} ", end='')
        print(f"{p.position_config.sl_mode:>14}   ", end='')
    print()
    
    for name in presets:
        p = preset_data[name]
        if name == 'scalping':
            print(f"{'Breakeven Trigger':<25} ", end='')
        print(f"{p.position_config.breakeven_trigger_r:>13.1f}R  ", end='')
    print()
    
    for name in presets:
        p = preset_data[name]
        if name == 'scalping':
            print(f"{'Trailing Activation':<25} ", end='')
        print(f"{p.position_config.trailing_activation_r:>13.1f}R  ", end='')
    print()
    
    for name in presets:
        p = preset_data[name]
        if name == 'scalping':
            print(f"{'Trailing Step':<25} ", end='')
        print(f"{p.position_config.trailing_step_bps:>12.0f}bps ", end='')
    print()
    
    for name in presets:
        p = preset_data[name]
        if name == 'scalping':
            print(f"{'Max Hold Time':<25} ", end='')
        print(f"{p.position_config.max_hold_time_hours:>13.0f}h  ", end='')
    print()
    print()
    
    # Compare Scanner
    print_header('🔍 SCANNER CONFIGURATION', '-')
    print(f"{'Metric':<25} {'Scalping':<15} {'Conservative':<15} {'Aggressive':<15} {'Swing':<15}")
    print_separator('-')
    
    for name in presets:
        p = preset_data[name]
        if name == 'scalping':
            print(f"{'Max Candidates':<25} ", end='')
        print(f"{p.scanner_config.max_candidates:>14d}   ", end='')
    print()
    
    for name in presets:
        p = preset_data[name]
        if name == 'scalping':
            print(f"{'Scan Interval':<25} ", end='')
        print(f"{p.scanner_config.scan_interval_seconds:>13d}s  ", end='')
    print()
    print()
    
    # Compare Entry Rules
    print_header('✨ ENTRY RULES', '-')
    print(f"{'Metric':<25} {'Scalping':<15} {'Conservative':<15} {'Aggressive':<15} {'Swing':<15}")
    print_separator('-')
    
    for name in presets:
        p = preset_data[name]
        entry = p.signal_config.entry_rules
        if name == 'scalping':
            print(f"{'Volume Confirm':<25} ", end='')
        if entry:
            print(f"{entry.volume_confirmation_multiplier:>13.1f}x  ", end='')
        else:
            print(f"{'N/A':>14}   ", end='')
    print()
    
    for name in presets:
        p = preset_data[name]
        entry = p.signal_config.entry_rules
        if name == 'scalping':
            print(f"{'Density Confirm':<25} ", end='')
        if entry:
            print(f"{entry.density_confirmation_threshold:>13.1f}x  ", end='')
        else:
            print(f"{'N/A':>14}   ", end='')
    print()
    
    for name in presets:
        p = preset_data[name]
        entry = p.signal_config.entry_rules
        if name == 'scalping':
            print(f"{'Momentum Min Slope':<25} ", end='')
        if entry:
            print(f"{entry.momentum_min_slope_pct:>13.1f}%  ", end='')
        else:
            print(f"{'N/A':>14}   ", end='')
    print()
    print()
    
    # Summary
    print_header('🎯 STRATEGY SUMMARY', '=')
    
    summaries = {
        'scalping': '🚀 High-frequency, quick profits (1-5min)',
        'conservative': '🛡️  Balanced, quality trades (15min-1h)',
        'aggressive': '⚡ High risk/reward, momentum (5min-4h)',
        'swing': '🎯 Patient, maximum R:R (4h-1d)'
    }
    
    for name in presets:
        print(f"  {summaries[name]}")
    
    print()
    print_header('✅ ALL 4 PRESETS READY FOR DEPLOYMENT', '=')
    print()


if __name__ == '__main__':
    compare_presets()
