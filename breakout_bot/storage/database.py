"""
Database management for Breakout Bot Trading System.

Provides SQLite-based data persistence for trading data, performance metrics,
and system logs with support for both development and production environments.
"""

import sqlite3
import json
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from pathlib import Path
import asyncio
from contextlib import asynccontextmanager

from ..data.models import Position, Signal, ScanResult, MarketData, Order

logger = logging.getLogger(__name__)


class DatabaseManager:
    """SQLite database manager for trading data persistence."""
    
    def __init__(self, db_path: str = "breakout_bot.db"):
        """Initialize database manager."""
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._connection_pool = []
        self._max_connections = 10
        
    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection from pool or create new one."""
        if self._connection_pool:
            return self._connection_pool.pop()
        
        conn = sqlite3.connect(
            str(self.db_path),
            check_same_thread=False,
            timeout=30.0
        )
        conn.row_factory = sqlite3.Row
        return conn
    
    def _return_connection(self, conn: sqlite3.Connection):
        """Return connection to pool."""
        if len(self._connection_pool) < self._max_connections:
            self._connection_pool.append(conn)
        else:
            conn.close()
    
    def initialize(self):
        """Initialize database schema."""
        conn = self._get_connection()
        try:
            conn.executescript("""
                -- Positions table
                CREATE TABLE IF NOT EXISTS positions (
                    id TEXT PRIMARY KEY,
                    symbol TEXT NOT NULL,
                    side TEXT NOT NULL,
                    strategy TEXT NOT NULL,
                    qty REAL NOT NULL,
                    entry_price REAL NOT NULL,
                    stop_loss REAL,
                    take_profit REAL,
                    status TEXT NOT NULL,
                    pnl_usd REAL DEFAULT 0.0,
                    pnl_r REAL DEFAULT 0.0,
                    fees_usd REAL DEFAULT 0.0,
                    timestamps TEXT NOT NULL,
                    meta TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                
                -- Signals table
                CREATE TABLE IF NOT EXISTS signals (
                    id TEXT PRIMARY KEY,
                    symbol TEXT NOT NULL,
                    strategy TEXT NOT NULL,
                    side TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    entry_price REAL NOT NULL,
                    stop_loss REAL,
                    take_profit REAL,
                    risk_reward_ratio REAL,
                    level_id TEXT,
                    market_data TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                
                -- Scan results table
                CREATE TABLE IF NOT EXISTS scan_results (
                    id TEXT PRIMARY KEY,
                    symbol TEXT NOT NULL,
                    score REAL NOT NULL,
                    rank INTEGER NOT NULL,
                    market_data TEXT NOT NULL,
                    filter_results TEXT NOT NULL,
                    score_components TEXT NOT NULL,
                    levels TEXT NOT NULL,
                    timestamp INTEGER NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                
                -- Orders table
                CREATE TABLE IF NOT EXISTS orders (
                    id TEXT PRIMARY KEY,
                    exchange_id TEXT,
                    symbol TEXT NOT NULL,
                    side TEXT NOT NULL,
                    type TEXT NOT NULL,
                    qty REAL NOT NULL,
                    price REAL,
                    status TEXT NOT NULL,
                    filled_qty REAL DEFAULT 0.0,
                    remaining_qty REAL NOT NULL,
                    fees_usd REAL DEFAULT 0.0,
                    timestamps TEXT NOT NULL,
                    meta TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                
                -- Performance metrics table
                CREATE TABLE IF NOT EXISTS performance_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    timestamp INTEGER NOT NULL,
                    total_trades INTEGER DEFAULT 0,
                    win_rate REAL DEFAULT 0.0,
                    avg_r REAL DEFAULT 0.0,
                    sharpe_ratio REAL DEFAULT 0.0,
                    max_drawdown_r REAL DEFAULT 0.0,
                    daily_pnl_r REAL DEFAULT 0.0,
                    consecutive_losses INTEGER DEFAULT 0,
                    active_positions INTEGER DEFAULT 0,
                    total_equity REAL DEFAULT 0.0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                
                -- System logs table
                CREATE TABLE IF NOT EXISTS system_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    level TEXT NOT NULL,
                    message TEXT NOT NULL,
                    module TEXT,
                    timestamp INTEGER NOT NULL,
                    meta TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                
                -- Create indexes for better performance
                CREATE INDEX IF NOT EXISTS idx_positions_symbol ON positions(symbol);
                CREATE INDEX IF NOT EXISTS idx_positions_status ON positions(status);
                CREATE INDEX IF NOT EXISTS idx_positions_created_at ON positions(created_at);
                CREATE INDEX IF NOT EXISTS idx_signals_symbol ON signals(symbol);
                CREATE INDEX IF NOT EXISTS idx_signals_created_at ON signals(created_at);
                CREATE INDEX IF NOT EXISTS idx_scan_results_symbol ON scan_results(symbol);
                CREATE INDEX IF NOT EXISTS idx_scan_results_timestamp ON scan_results(timestamp);
                CREATE INDEX IF NOT EXISTS idx_orders_symbol ON orders(symbol);
                CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);
                CREATE INDEX IF NOT EXISTS idx_performance_session ON performance_metrics(session_id);
                CREATE INDEX IF NOT EXISTS idx_performance_timestamp ON performance_metrics(timestamp);
                CREATE INDEX IF NOT EXISTS idx_logs_level ON system_logs(level);
                CREATE INDEX IF NOT EXISTS idx_logs_timestamp ON system_logs(timestamp);
            """)
            conn.commit()
            logger.info("Database schema initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize database schema: {e}")
            raise
        finally:
            self._return_connection(conn)
    
    def save_position(self, position: Position) -> bool:
        """Save position to database."""
        conn = self._get_connection()
        try:
            conn.execute("""
                INSERT OR REPLACE INTO positions 
                (id, symbol, side, strategy, qty, entry_price, stop_loss, take_profit, 
                 status, pnl_usd, pnl_r, fees_usd, timestamps, meta)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                position.id,
                position.symbol,
                position.side,
                position.strategy,
                position.qty,
                position.entry,
                position.sl,
                position.tp,
                position.status,
                position.pnl_usd,
                position.pnl_r,
                position.fees_usd,
                json.dumps(position.timestamps),
                json.dumps(position.meta) if position.meta else None
            ))
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to save position {position.id}: {e}")
            return False
        finally:
            self._return_connection(conn)
    
    def save_signal(self, signal: Signal) -> bool:
        """Save signal to database."""
        conn = self._get_connection()
        try:
            conn.execute("""
                INSERT OR REPLACE INTO signals 
                (id, symbol, strategy, side, confidence, entry_price, stop_loss, 
                 take_profit, risk_reward_ratio, level_id, market_data)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                signal.id,
                signal.symbol,
                signal.strategy,
                signal.side,
                signal.confidence,
                signal.entry_price,
                signal.stop_loss,
                signal.take_profit,
                signal.risk_reward_ratio,
                signal.level_id,
                json.dumps(signal.market_data.dict() if signal.market_data else {})
            ))
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to save signal {signal.id}: {e}")
            return False
        finally:
            self._return_connection(conn)
    
    def save_scan_result(self, scan_result: ScanResult) -> bool:
        """Save scan result to database."""
        conn = self._get_connection()
        try:
            conn.execute("""
                INSERT OR REPLACE INTO scan_results 
                (id, symbol, score, rank, market_data, filter_results, 
                 score_components, levels, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                scan_result.symbol,  # Using symbol as ID for scan results
                scan_result.symbol,
                scan_result.score,
                scan_result.rank,
                json.dumps(scan_result.market_data.dict() if scan_result.market_data else {}),
                json.dumps(scan_result.filter_results),
                json.dumps(scan_result.score_components),
                json.dumps([level.dict() for level in scan_result.levels]),
                scan_result.timestamp
            ))
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to save scan result for {scan_result.symbol}: {e}")
            return False
        finally:
            self._return_connection(conn)
    
    def save_performance_metrics(self, session_id: str, metrics: Dict[str, Any]) -> bool:
        """Save performance metrics to database."""
        conn = self._get_connection()
        try:
            conn.execute("""
                INSERT INTO performance_metrics 
                (session_id, timestamp, total_trades, win_rate, avg_r, sharpe_ratio,
                 max_drawdown_r, daily_pnl_r, consecutive_losses, active_positions, total_equity)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                session_id,
                int(datetime.now().timestamp() * 1000),
                metrics.get('total_trades', 0),
                metrics.get('win_rate', 0.0),
                metrics.get('avg_r', 0.0),
                metrics.get('sharpe_ratio', 0.0),
                metrics.get('max_drawdown_r', 0.0),
                metrics.get('daily_pnl_r', 0.0),
                metrics.get('consecutive_losses', 0),
                metrics.get('active_positions', 0),
                metrics.get('total_equity', 0.0)
            ))
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to save performance metrics: {e}")
            return False
        finally:
            self._return_connection(conn)
    
    def get_positions(self, status: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        """Get positions from database."""
        conn = self._get_connection()
        try:
            if status:
                cursor = conn.execute(
                    "SELECT * FROM positions WHERE status = ? ORDER BY created_at DESC LIMIT ?",
                    (status, limit)
                )
            else:
                cursor = conn.execute(
                    "SELECT * FROM positions ORDER BY created_at DESC LIMIT ?",
                    (limit,)
                )
            
            rows = cursor.fetchall()
            positions = []
            for row in rows:
                position = dict(row)
                position['timestamps'] = json.loads(position['timestamps'])
                position['meta'] = json.loads(position['meta']) if position['meta'] else {}
                positions.append(position)
            
            return positions
        except Exception as e:
            logger.error(f"Failed to get positions: {e}")
            return []
        finally:
            self._return_connection(conn)
    
    def get_performance_summary(self, session_id: str, days: int = 30) -> Dict[str, Any]:
        """Get performance summary for a session."""
        conn = self._get_connection()
        try:
            since_timestamp = int((datetime.now() - timedelta(days=days)).timestamp() * 1000)
            
            cursor = conn.execute("""
                SELECT 
                    COUNT(*) as total_entries,
                    AVG(win_rate) as avg_win_rate,
                    AVG(avg_r) as avg_r,
                    AVG(sharpe_ratio) as avg_sharpe,
                    MAX(max_drawdown_r) as max_drawdown,
                    AVG(daily_pnl_r) as avg_daily_pnl,
                    MAX(consecutive_losses) as max_consecutive_losses,
                    AVG(active_positions) as avg_active_positions,
                    AVG(total_equity) as avg_equity
                FROM performance_metrics 
                WHERE session_id = ? AND timestamp >= ?
            """, (session_id, since_timestamp))
            
            row = cursor.fetchone()
            if row:
                return dict(row)
            return {}
        except Exception as e:
            logger.error(f"Failed to get performance summary: {e}")
            return {}
        finally:
            self._return_connection(conn)
    
    def cleanup_old_data(self, days: int = 90):
        """Clean up old data to prevent database bloat."""
        conn = self._get_connection()
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            cutoff_timestamp = int(cutoff_date.timestamp() * 1000)
            
            # Clean up old scan results and logs
            conn.execute("DELETE FROM scan_results WHERE timestamp < ?", (cutoff_timestamp,))
            conn.execute("DELETE FROM system_logs WHERE timestamp < ?", (cutoff_timestamp,))
            
            # Clean up old performance metrics (keep only daily summaries)
            conn.execute("""
                DELETE FROM performance_metrics 
                WHERE created_at < ? AND id NOT IN (
                    SELECT id FROM performance_metrics 
                    WHERE created_at < ? 
                    ORDER BY created_at DESC 
                    LIMIT 1
                )
            """, (cutoff_date, cutoff_date))
            
            conn.commit()
            logger.info(f"Cleaned up data older than {days} days")
        except Exception as e:
            logger.error(f"Failed to cleanup old data: {e}")
        finally:
            self._return_connection(conn)
    
    def close(self):
        """Close all database connections."""
        for conn in self._connection_pool:
            conn.close()
        self._connection_pool.clear()
        logger.info("Database connections closed")


# Global database manager instance
_db_manager: Optional[DatabaseManager] = None

def get_database_manager() -> DatabaseManager:
    """Get global database manager instance."""
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager()
        _db_manager.initialize()
    return _db_manager
