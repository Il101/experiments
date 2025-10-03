"""
Report generation for Breakout Bot Trading System.

Provides comprehensive reporting capabilities for trading performance,
backtesting results, and system analytics with multiple output formats.
"""

import json
import csv
from typing import Dict, List, Optional, Any
from ..data.models import Position
from datetime import datetime, timedelta
from pathlib import Path
import logging

from .analytics import get_analytics_engine
from .database import get_database_manager

logger = logging.getLogger(__name__)


class ReportGenerator:
    """Report generator for trading performance and analytics."""
    
    def __init__(self, output_dir: str = "reports"):
        """Initialize report generator."""
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.analytics = get_analytics_engine()
        self.db = get_database_manager()
    
    def generate_daily_report(self, session_id: str, date: Optional[datetime] = None) -> Dict[str, Any]:
        """Generate daily performance report."""
        if date is None:
            date = datetime.now()
        
        # Get positions for the day
        positions = self.db.get_positions(limit=1000)
        day_positions = []
        
        for pos_data in positions:
            pos = Position(**pos_data)
            if 'closed_at' in pos.timestamps:
                close_date = datetime.fromtimestamp(pos.timestamps['closed_at'] / 1000)
                if close_date.date() == date.date():
                    day_positions.append(pos)
        
        # Calculate metrics
        performance = self.analytics.calculate_position_metrics(day_positions)
        risk_metrics = self.analytics.calculate_risk_metrics(day_positions)
        
        report = {
            'date': date.isoformat(),
            'session_id': session_id,
            'trading_day': date.strftime('%Y-%m-%d'),
            'performance': performance,
            'risk_metrics': risk_metrics,
            'positions': len(day_positions),
            'generated_at': datetime.now().isoformat()
        }
        
        # Save to file
        filename = f"daily_report_{date.strftime('%Y%m%d')}.json"
        self._save_json_report(report, filename)
        
        return report
    
    def generate_weekly_report(self, session_id: str, week_start: Optional[datetime] = None) -> Dict[str, Any]:
        """Generate weekly performance report."""
        if week_start is None:
            week_start = datetime.now() - timedelta(days=7)
        
        week_end = week_start + timedelta(days=7)
        
        # Get positions for the week
        positions = self.db.get_positions(limit=1000)
        week_positions = []
        
        for pos_data in positions:
            pos = Position(**pos_data)
            if 'closed_at' in pos.timestamps:
                close_date = datetime.fromtimestamp(pos.timestamps['closed_at'] / 1000)
                if week_start.date() <= close_date.date() < week_end.date():
                    week_positions.append(pos)
        
        # Calculate metrics
        performance = self.analytics.calculate_position_metrics(week_positions)
        risk_metrics = self.analytics.calculate_risk_metrics(week_positions)
        daily_pnl = self.analytics.calculate_daily_pnl(7)
        
        report = {
            'week_start': week_start.isoformat(),
            'week_end': week_end.isoformat(),
            'session_id': session_id,
            'performance': performance,
            'risk_metrics': risk_metrics,
            'daily_pnl': daily_pnl,
            'positions': len(week_positions),
            'generated_at': datetime.now().isoformat()
        }
        
        # Save to file
        filename = f"weekly_report_{week_start.strftime('%Y%m%d')}.json"
        self._save_json_report(report, filename)
        
        return report
    
    def generate_monthly_report(self, session_id: str, month: Optional[datetime] = None) -> Dict[str, Any]:
        """Generate monthly performance report."""
        if month is None:
            month = datetime.now()
        
        # Get positions for the month
        positions = self.db.get_positions(limit=1000)
        month_positions = []
        
        for pos_data in positions:
            pos = Position(**pos_data)
            if 'closed_at' in pos.timestamps:
                close_date = datetime.fromtimestamp(pos.timestamps['closed_at'] / 1000)
                if close_date.month == month.month and close_date.year == month.year:
                    month_positions.append(pos)
        
        # Calculate comprehensive metrics
        performance = self.analytics.calculate_position_metrics(month_positions)
        risk_metrics = self.analytics.calculate_risk_metrics(month_positions)
        daily_pnl = self.analytics.calculate_daily_pnl(30)
        
        # Strategy breakdown
        strategy_performance = {}
        strategies = set(pos.strategy for pos in month_positions)
        for strategy in strategies:
            strategy_positions = [p for p in month_positions if p.strategy == strategy]
            strategy_performance[strategy] = self.analytics.calculate_position_metrics(strategy_positions)
        
        report = {
            'month': month.strftime('%Y-%m'),
            'session_id': session_id,
            'performance': performance,
            'risk_metrics': risk_metrics,
            'daily_pnl': daily_pnl,
            'strategy_breakdown': strategy_performance,
            'positions': len(month_positions),
            'generated_at': datetime.now().isoformat()
        }
        
        # Save to file
        filename = f"monthly_report_{month.strftime('%Y%m')}.json"
        self._save_json_report(report, filename)
        
        return report
    
    def generate_backtest_report(self, backtest_results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate backtest performance report."""
        report = {
            'backtest_id': backtest_results.get('id', 'unknown'),
            'strategy': backtest_results.get('strategy', 'unknown'),
            'start_date': backtest_results.get('start_date'),
            'end_date': backtest_results.get('end_date'),
            'initial_capital': backtest_results.get('initial_capital', 0),
            'final_capital': backtest_results.get('final_capital', 0),
            'total_return': backtest_results.get('total_return', 0),
            'performance': backtest_results.get('performance', {}),
            'risk_metrics': backtest_results.get('risk_metrics', {}),
            'trades': backtest_results.get('trades', []),
            'generated_at': datetime.now().isoformat()
        }
        
        # Save to file
        filename = f"backtest_report_{report['backtest_id']}.json"
        self._save_json_report(report, filename)
        
        return report
    
    def export_positions_csv(self, filename: Optional[str] = None) -> str:
        """Export positions to CSV file."""
        if filename is None:
            filename = f"positions_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        filepath = self.output_dir / filename
        
        positions = self.db.get_positions(limit=10000)
        
        with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
            if not positions:
                csvfile.write("No positions found\n")
                return str(filepath)
            
            # Get fieldnames from first position
            fieldnames = list(positions[0].keys())
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            writer.writeheader()
            for position in positions:
                # Convert timestamps and meta to strings for CSV
                row = position.copy()
                if 'timestamps' in row and isinstance(row['timestamps'], str):
                    row['timestamps'] = json.loads(row['timestamps'])
                if 'meta' in row and isinstance(row['meta'], str):
                    row['meta'] = json.loads(row['meta'])
                
                # Convert complex fields to strings
                for key, value in row.items():
                    if isinstance(value, (dict, list)):
                        row[key] = json.dumps(value)
                
                writer.writerow(row)
        
        logger.info(f"Positions exported to {filepath}")
        return str(filepath)
    
    def export_performance_csv(self, session_id: str, days: int = 30) -> str:
        """Export performance metrics to CSV file."""
        filename = f"performance_export_{session_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        filepath = self.output_dir / filename
        
        # Get performance data
        daily_pnl = self.analytics.calculate_daily_pnl(days)
        
        with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['date', 'pnl_r', 'trades']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            writer.writeheader()
            for day_data in daily_pnl:
                writer.writerow(day_data)
        
        logger.info(f"Performance data exported to {filepath}")
        return str(filepath)
    
    def generate_summary_report(self, session_id: str) -> str:
        """Generate human-readable summary report."""
        report = self.analytics.generate_performance_report(session_id)
        
        summary = f"""
# Breakout Bot Trading Report
## Session: {session_id}
## Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Performance Summary
- **Total Trades**: {report['performance']['total_trades']}
- **Win Rate**: {report['performance']['win_rate']:.1%}
- **Average R**: {report['performance']['avg_r']:.2f}
- **Max Drawdown**: {report['performance']['max_drawdown_r']:.2f}R
- **Profit Factor**: {report['performance']['profit_factor']:.2f}
- **Sharpe Ratio**: {report['performance']['sharpe_ratio']:.2f}

## Risk Metrics
- **VaR (95%)**: {report['risk_metrics'].get('var_95', 0):.2f}R
- **Max Consecutive Losses**: {report['risk_metrics'].get('max_consecutive_losses', 0)}
- **Recovery Time**: {report['risk_metrics'].get('recovery_time_days', 0)} days

## Strategy Breakdown
"""
        
        for strategy, perf in report['strategy_breakdown'].items():
            summary += f"""
### {strategy}
- Trades: {perf['total_trades']}
- Win Rate: {perf['win_rate']:.1%}
- Avg R: {perf['avg_r']:.2f}
"""
        
        summary += f"""
## Summary
{report['summary']}
"""
        
        # Save to file
        filename = f"summary_report_{session_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        filepath = self.output_dir / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(summary)
        
        logger.info(f"Summary report saved to {filepath}")
        return str(filepath)
    
    def _save_json_report(self, report: Dict[str, Any], filename: str) -> str:
        """Save report as JSON file."""
        filepath = self.output_dir / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, default=str)
        
        logger.info(f"Report saved to {filepath}")
        return str(filepath)


# Global report generator instance
_report_generator: Optional[ReportGenerator] = None

def get_report_generator() -> ReportGenerator:
    """Get global report generator instance."""
    global _report_generator
    if _report_generator is None:
        _report_generator = ReportGenerator()
    return _report_generator
