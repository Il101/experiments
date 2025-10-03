"""
Analytics engine for Breakout Bot Trading System.

Provides comprehensive analytics and performance calculations
for trading strategies, risk management, and system optimization.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
import logging
from dataclasses import dataclass

from .database import get_database_manager
from ..data.models import Position

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetrics:
    """Performance metrics container."""
    total_trades: int
    win_rate: float
    avg_r: float
    sharpe_ratio: float
    max_drawdown_r: float
    daily_pnl_r: float
    consecutive_losses: int
    active_positions: int
    total_equity: float
    profit_factor: float
    recovery_factor: float
    calmar_ratio: float


class AnalyticsEngine:
    """Analytics engine for trading performance analysis."""
    
    def __init__(self):
        """Initialize analytics engine."""
        self.db = get_database_manager()
    
    def calculate_position_metrics(self, positions: List[Position]) -> Dict[str, Any]:
        """Calculate comprehensive position metrics."""
        if not positions:
            return self._empty_metrics()
        
        # Separate open and closed positions
        open_positions = [p for p in positions if p.status == 'open']
        closed_positions = [p for p in positions if p.status == 'closed']
        
        if not closed_positions:
            return self._empty_metrics()
        
        # Basic metrics
        total_trades = len(closed_positions)
        winning_trades = [p for p in closed_positions if p.pnl_r > 0]
        losing_trades = [p for p in closed_positions if p.pnl_r < 0]
        
        win_rate = len(winning_trades) / total_trades if total_trades > 0 else 0.0
        
        # R-multiple calculations
        r_multiples = [p.pnl_r for p in closed_positions]
        avg_r = np.mean(r_multiples) if r_multiples else 0.0
        
        # Risk metrics
        max_drawdown_r = self._calculate_max_drawdown(r_multiples)
        
        # Profit factor
        gross_profit = sum(p.pnl_r for p in winning_trades)
        gross_loss = abs(sum(p.pnl_r for p in losing_trades))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
        
        # Sharpe ratio (simplified)
        sharpe_ratio = self._calculate_sharpe_ratio(r_multiples)
        
        # Recovery factor
        recovery_factor = gross_profit / max_drawdown_r if max_drawdown_r > 0 else 0.0
        
        # Calmar ratio
        calmar_ratio = avg_r / max_drawdown_r if max_drawdown_r > 0 else 0.0
        
        return {
            'total_trades': total_trades,
            'win_rate': win_rate,
            'avg_r': avg_r,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown_r': max_drawdown_r,
            'profit_factor': profit_factor,
            'recovery_factor': recovery_factor,
            'calmar_ratio': calmar_ratio,
            'active_positions': len(open_positions),
            'gross_profit': gross_profit,
            'gross_loss': gross_loss,
            'net_profit': gross_profit - gross_loss,
            'avg_win': np.mean([p.pnl_r for p in winning_trades]) if winning_trades else 0.0,
            'avg_loss': np.mean([p.pnl_r for p in losing_trades]) if losing_trades else 0.0,
            'max_win': max([p.pnl_r for p in winning_trades]) if winning_trades else 0.0,
            'max_loss': min([p.pnl_r for p in losing_trades]) if losing_trades else 0.0,
            'consecutive_wins': self._calculate_max_consecutive_wins(r_multiples),
            'consecutive_losses': self._calculate_max_consecutive_losses(r_multiples)
        }
    
    def calculate_strategy_performance(self, strategy: str, days: int = 30) -> Dict[str, Any]:
        """Calculate performance metrics for a specific strategy."""
        positions = self.db.get_positions(limit=1000)
        strategy_positions = [
            Position(**pos) for pos in positions 
            if pos.get('strategy') == strategy
        ]
        
        return self.calculate_position_metrics(strategy_positions)
    
    def calculate_daily_pnl(self, days: int = 30) -> List[Dict[str, Any]]:
        """Calculate daily P&L for the last N days."""
        positions = self.db.get_positions(limit=1000)
        closed_positions = [
            Position(**pos) for pos in positions 
            if pos.get('status') == 'closed'
        ]
        
        if not closed_positions:
            return []
        
        # Group by date
        daily_pnl = {}
        for pos in closed_positions:
            if 'closed_at' in pos.timestamps:
                close_date = datetime.fromtimestamp(pos.timestamps['closed_at'] / 1000).date()
                if close_date not in daily_pnl:
                    daily_pnl[close_date] = {'pnl_r': 0.0, 'trades': 0}
                daily_pnl[close_date]['pnl_r'] += pos.pnl_r
                daily_pnl[close_date]['trades'] += 1
        
        # Convert to list and sort by date
        result = []
        for date in sorted(daily_pnl.keys()):
            result.append({
                'date': date.isoformat(),
                'pnl_r': daily_pnl[date]['pnl_r'],
                'trades': daily_pnl[date]['trades']
            })
        
        return result[-days:]  # Last N days
    
    def calculate_risk_metrics(self, positions: List[Position]) -> Dict[str, Any]:
        """Calculate risk management metrics."""
        if not positions:
            return {}
        
        closed_positions = [p for p in positions if p.status == 'closed']
        if not closed_positions:
            return {}
        
        r_multiples = [p.pnl_r for p in closed_positions]
        
        # Value at Risk (VaR) - 95% confidence
        var_95 = np.percentile(r_multiples, 5) if len(r_multiples) > 0 else 0.0
        
        # Expected Shortfall (Conditional VaR)
        es_95 = np.mean([r for r in r_multiples if r <= var_95]) if var_95 < 0 else 0.0
        
        # Maximum consecutive losses
        max_consecutive_losses = self._calculate_max_consecutive_losses(r_multiples)
        
        # Drawdown analysis
        cumulative_returns = np.cumsum(r_multiples)
        running_max = np.maximum.accumulate(cumulative_returns)
        drawdowns = cumulative_returns - running_max
        max_drawdown = np.min(drawdowns)
        
        # Recovery time analysis
        recovery_time = self._calculate_recovery_time(cumulative_returns)
        
        return {
            'var_95': var_95,
            'expected_shortfall_95': es_95,
            'max_consecutive_losses': max_consecutive_losses,
            'max_drawdown': max_drawdown,
            'avg_drawdown': np.mean(drawdowns[drawdowns < 0]) if np.any(drawdowns < 0) else 0.0,
            'recovery_time_days': recovery_time,
            'downside_deviation': np.std([r for r in r_multiples if r < 0]) if any(r < 0 for r in r_multiples) else 0.0
        }
    
    def generate_performance_report(self, session_id: str, days: int = 30) -> Dict[str, Any]:
        """Generate comprehensive performance report."""
        positions = self.db.get_positions(limit=1000)
        position_objects = [Position(**pos) for pos in positions]
        
        # Basic performance metrics
        performance = self.calculate_position_metrics(position_objects)
        
        # Risk metrics
        risk_metrics = self.calculate_risk_metrics(position_objects)
        
        # Daily P&L
        daily_pnl = self.calculate_daily_pnl(days)
        
        # Strategy breakdown
        strategy_performance = {}
        strategies = set(pos.strategy for pos in position_objects)
        for strategy in strategies:
            strategy_positions = [p for p in position_objects if p.strategy == strategy]
            strategy_performance[strategy] = self.calculate_position_metrics(strategy_positions)
        
        return {
            'session_id': session_id,
            'report_date': datetime.now().isoformat(),
            'period_days': days,
            'performance': performance,
            'risk_metrics': risk_metrics,
            'daily_pnl': daily_pnl,
            'strategy_breakdown': strategy_performance,
            'summary': self._generate_summary(performance, risk_metrics)
        }
    
    def _empty_metrics(self) -> Dict[str, Any]:
        """Return empty metrics structure."""
        return {
            'total_trades': 0,
            'win_rate': 0.0,
            'avg_r': 0.0,
            'sharpe_ratio': 0.0,
            'max_drawdown_r': 0.0,
            'profit_factor': 0.0,
            'recovery_factor': 0.0,
            'calmar_ratio': 0.0,
            'active_positions': 0,
            'gross_profit': 0.0,
            'gross_loss': 0.0,
            'net_profit': 0.0,
            'avg_win': 0.0,
            'avg_loss': 0.0,
            'max_win': 0.0,
            'max_loss': 0.0,
            'consecutive_wins': 0,
            'consecutive_losses': 0
        }
    
    def _calculate_max_drawdown(self, returns: List[float]) -> float:
        """Calculate maximum drawdown from returns."""
        if not returns:
            return 0.0
        
        cumulative = np.cumsum(returns)
        running_max = np.maximum.accumulate(cumulative)
        drawdowns = cumulative - running_max
        return float(np.min(drawdowns))
    
    def _calculate_sharpe_ratio(self, returns: List[float]) -> float:
        """Calculate Sharpe ratio (simplified)."""
        if not returns or len(returns) < 2:
            return 0.0
        
        mean_return = np.mean(returns)
        std_return = np.std(returns)
        
        if std_return == 0:
            return 0.0
        
        # Assuming risk-free rate of 0 for simplicity
        return float(mean_return / std_return)
    
    def _calculate_max_consecutive_wins(self, returns: List[float]) -> int:
        """Calculate maximum consecutive wins."""
        if not returns:
            return 0
        
        max_consecutive = 0
        current_consecutive = 0
        
        for ret in returns:
            if ret > 0:
                current_consecutive += 1
                max_consecutive = max(max_consecutive, current_consecutive)
            else:
                current_consecutive = 0
        
        return max_consecutive
    
    def _calculate_max_consecutive_losses(self, returns: List[float]) -> int:
        """Calculate maximum consecutive losses."""
        if not returns:
            return 0
        
        max_consecutive = 0
        current_consecutive = 0
        
        for ret in returns:
            if ret < 0:
                current_consecutive += 1
                max_consecutive = max(max_consecutive, current_consecutive)
            else:
                current_consecutive = 0
        
        return max_consecutive
    
    def _calculate_recovery_time(self, cumulative_returns: np.ndarray) -> int:
        """Calculate average recovery time from drawdowns."""
        if len(cumulative_returns) < 2:
            return 0
        
        recovery_times = []
        in_drawdown = False
        drawdown_start = 0
        
        for i, ret in enumerate(cumulative_returns):
            if ret < 0 and not in_drawdown:
                in_drawdown = True
                drawdown_start = i
            elif ret >= 0 and in_drawdown:
                in_drawdown = False
                recovery_times.append(i - drawdown_start)
        
        return int(np.mean(recovery_times)) if recovery_times else 0
    
    def _generate_summary(self, performance: Dict[str, Any], risk_metrics: Dict[str, Any]) -> str:
        """Generate human-readable performance summary."""
        total_trades = performance.get('total_trades', 0)
        win_rate = performance.get('win_rate', 0.0)
        avg_r = performance.get('avg_r', 0.0)
        max_drawdown = performance.get('max_drawdown_r', 0.0)
        
        if total_trades == 0:
            return "No trading data available"
        
        summary = f"Performance Summary ({total_trades} trades):\n"
        summary += f"• Win Rate: {win_rate:.1%}\n"
        summary += f"• Average R: {avg_r:.2f}\n"
        summary += f"• Max Drawdown: {max_drawdown:.2f}R\n"
        
        if risk_metrics:
            var_95 = risk_metrics.get('var_95', 0.0)
            summary += f"• VaR (95%): {var_95:.2f}R\n"
        
        return summary


# Global analytics engine instance
_analytics_engine: Optional[AnalyticsEngine] = None

def get_analytics_engine() -> AnalyticsEngine:
    """Get global analytics engine instance."""
    global _analytics_engine
    if _analytics_engine is None:
        _analytics_engine = AnalyticsEngine()
    return _analytics_engine
