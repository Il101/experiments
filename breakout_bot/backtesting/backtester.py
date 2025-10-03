"""Simple walk-forward backtester with depth-aware slippage."""

from __future__ import annotations

import asyncio
import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from ..config.settings import TradingPreset
from ..data.models import MarketData
from ..scanner import BreakoutScanner
from ..signals import SignalGenerator
from ..risk import RiskManager


@dataclass
class BacktestConfig:
    slippage_intercept_bps: float = 4.0
    slippage_depth_factor: float = 40.0
    walk_forward_splits: int = 3
    starting_equity: float = 100_000.0
    max_positions: int = 5


@dataclass
class BacktestTrade:
    symbol: str
    side: str
    entry_ts: int
    exit_ts: int
    entry_price: float
    exit_price: float
    qty: float
    pnl_usd: float
    pnl_r: float
    reason: str


@dataclass
class BacktestResult:
    equity_curve: List[Tuple[int, float]] = field(default_factory=list)
    trades: List[BacktestTrade] = field(default_factory=list)
    profit_factor: float = 0.0
    win_rate: float = 0.0
    average_r: float = 0.0
    max_drawdown: float = 0.0


@dataclass
class SimulatedPosition:
    symbol: str
    side: str
    entry_price: float
    stop_loss: float
    take_profit: Optional[float]
    qty: float
    entry_ts: int
    stop_distance: float


class Backtester:
    def __init__(self, preset: TradingPreset, config: Optional[BacktestConfig] = None):
        self.preset = preset
        self.config = config or BacktestConfig()
        self.scanner = BreakoutScanner(preset)
        self.signal_generator = SignalGenerator(preset)
        self.risk_manager = RiskManager(preset)

    async def run(self, dataset: Dict[int, List[MarketData]]) -> BacktestResult:
        timestamps = sorted(dataset.keys())
        if not timestamps:
            return BacktestResult()

        split_size = max(1, len(timestamps) // self.config.walk_forward_splits)
        equity = self.config.starting_equity
        equity_curve: List[Tuple[int, float]] = []
        trades: List[BacktestTrade] = []
        open_positions: Dict[str, SimulatedPosition] = {}
        realized_pnl: Dict[str, float] = {}

        for idx, ts in enumerate(timestamps):
            slice_data = dataset[ts]
            btc_data = next((md for md in slice_data if md.symbol.upper().startswith('BTC')), None)
            scan_results = await self.scanner.scan_markets(slice_data, btc_data)

            for result in scan_results:
                if len(open_positions) >= self.config.max_positions:
                    break
                signal = await self.signal_generator.generate_signal(result)
                if not signal:
                    continue
                market_data = result.market_data
                evaluation = self.risk_manager.evaluate_signal_risk(
                    signal,
                    equity,
                    [],
                    market_data,
                )
                if not evaluation.get('approved'):
                    continue
                position_size = evaluation['position_size']
                if position_size.quantity <= 0:
                    continue
                entry_price = self._apply_slippage(
                    'long' if signal.side == 'long' else 'short',
                    market_data,
                    position_size.notional_usd
                )
                take_profit = signal.meta.get('tp2') or signal.meta.get('tp1')
                open_positions[signal.symbol] = SimulatedPosition(
                    symbol=signal.symbol,
                    side=signal.side,
                    entry_price=entry_price,
                    stop_loss=signal.sl,
                    take_profit=take_profit,
                    qty=position_size.quantity,
                    entry_ts=ts,
                    stop_distance=position_size.stop_distance,
                )
                equity -= position_size.notional_usd

            # Update open positions
            for md in slice_data:
                position = open_positions.get(md.symbol)
                if not position:
                    continue
                exit_info = self._check_exit(position, md)
                if exit_info:
                    exit_price, reason = exit_info
                    exit_price = self._apply_slippage(
                        'sell' if position.side == 'long' else 'buy',
                        md,
                        position.qty * exit_price
                    )
                    direction = 1 if position.side == 'long' else -1
                    pnl = (exit_price - position.entry_price) * position.qty * direction
                    risk = position.stop_distance * position.qty if position.stop_distance else 1.0
                    pnl_r = pnl / risk
                    equity += position.qty * exit_price
                    realized_pnl[position.symbol] = realized_pnl.get(position.symbol, 0.0) + pnl
                    trades.append(
                        BacktestTrade(
                            symbol=position.symbol,
                            side=position.side,
                            entry_ts=position.entry_ts,
                            exit_ts=ts,
                            entry_price=position.entry_price,
                            exit_price=exit_price,
                            qty=position.qty,
                            pnl_usd=pnl,
                            pnl_r=pnl_r,
                            reason=reason,
                        )
                    )
                    open_positions.pop(position.symbol, None)

            equity_curve.append((ts, equity))

            if (idx + 1) % split_size == 0:
                self.risk_manager = RiskManager(self.preset)

        # Force close any remaining positions at the last available price
        if open_positions:
            final_ts = timestamps[-1]
            final_slice = dataset[final_ts]
            for symbol, position in list(open_positions.items()):
                md = next((item for item in final_slice if item.symbol == symbol), None)
                if not md:
                    continue
                exit_price = self._apply_slippage(
                    'sell' if position.side == 'long' else 'buy',
                    md,
                    position.qty * md.price
                )
                direction = 1 if position.side == 'long' else -1
                pnl = (exit_price - position.entry_price) * position.qty * direction
                risk = position.stop_distance * position.qty if position.stop_distance else 1.0
                pnl_r = pnl / risk
                equity += position.qty * exit_price
                trades.append(
                    BacktestTrade(
                        symbol=position.symbol,
                        side=position.side,
                        entry_ts=position.entry_ts,
                        exit_ts=final_ts,
                        entry_price=position.entry_price,
                        exit_price=exit_price,
                        qty=position.qty,
                        pnl_usd=pnl,
                        pnl_r=pnl_r,
                        reason='forced_close',
                    )
                )
                open_positions.pop(symbol, None)

            if not equity_curve or equity_curve[-1][0] != final_ts:
                equity_curve.append((final_ts, equity))

        return self._build_result(equity_curve, trades)

    def _apply_slippage(self, side: str, market_data: MarketData, notional: float) -> float:
        price = market_data.price
        depth = market_data.l2_depth
        depth_reference = 0.0
        if depth:
            if side in ('long', 'buy'):
                depth_reference = depth.ask_usd_0_3pct
            else:
                depth_reference = depth.bid_usd_0_3pct
        slip_bps = self.config.slippage_intercept_bps
        if depth_reference > 0:
            slip_bps += self.config.slippage_depth_factor * (notional / depth_reference)
        factor = slip_bps / 10000.0
        if side in ('long', 'buy'):
            return price * (1 + factor)
        return price * (1 - factor)

    def _check_exit(self, position: SimulatedPosition, market_data: MarketData) -> Optional[Tuple[float, str]]:
        price = market_data.price
        if position.side == 'long':
            if price <= position.stop_loss:
                return position.stop_loss, 'stop_loss'
            if position.take_profit and price >= position.take_profit:
                return position.take_profit, 'take_profit'
        else:
            if price >= position.stop_loss:
                return position.stop_loss, 'stop_loss'
            if position.take_profit and price <= position.take_profit:
                return position.take_profit, 'take_profit'
        return None

    def _build_result(self, equity_curve: List[Tuple[int, float]], trades: List[BacktestTrade]) -> BacktestResult:
        result = BacktestResult(equity_curve=equity_curve, trades=trades)
        if not trades:
            return result
        wins = [t for t in trades if t.pnl_usd > 0]
        losses = [t for t in trades if t.pnl_usd < 0]
        gross_profit = sum(t.pnl_usd for t in wins)
        gross_loss = abs(sum(t.pnl_usd for t in losses))
        result.profit_factor = gross_profit / gross_loss if gross_loss else math.inf
        result.win_rate = len(wins) / len(trades)
        result.average_r = sum(t.pnl_r for t in trades) / len(trades)
        result.max_drawdown = self._max_drawdown(equity_curve)
        return result

    def _max_drawdown(self, equity_curve: List[Tuple[int, float]]) -> float:
        peak = -math.inf
        max_dd = 0.0
        for _, value in equity_curve:
            if value > peak:
                peak = value
            drawdown = (peak - value) / peak if peak > 0 else 0.0
            if drawdown > max_dd:
                max_dd = drawdown
        return max_dd


def load_dataset(path: str) -> Dict[int, List[MarketData]]:
    dataset: Dict[int, List[MarketData]] = {}
    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"Dataset not found: {path}")

    with file_path.open('r') as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            payload = json.loads(line)
            timestamp = int(payload['timestamp'])
            md = MarketData.model_validate(payload['market_data'])
            dataset.setdefault(timestamp, []).append(md)
    return dataset


async def run_backtest(preset: TradingPreset, dataset_path: str, config: Optional[BacktestConfig] = None) -> BacktestResult:
    dataset = load_dataset(dataset_path)
    tester = Backtester(preset, config)
    return await tester.run(dataset)


def run_backtest_sync(preset: TradingPreset, dataset_path: str, config: Optional[BacktestConfig] = None) -> BacktestResult:
    return asyncio.run(run_backtest(preset, dataset_path, config))
