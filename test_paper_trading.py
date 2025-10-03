import asyncio

import pytest

from breakout_bot.core.engine import OptimizedOrchestraEngine
from breakout_bot.config.settings import SystemConfig
from breakout_bot.data.models import Signal


@pytest.mark.asyncio
async def test_paper_open_close_position():
    config = SystemConfig()
    config.trading_mode = 'paper'
    config.paper_starting_balance = 10_000

    engine = OptimizedOrchestraEngine('breakout_v1', config)

    signal = Signal(
        symbol='BTC/USDT:USDT',
        side='long',
        strategy='momentum',
        reason='test-signal',
        entry=50_000,
        level=49_800,
        sl=49_500,
        confidence=0.8,
        timestamp=0,
    )
    signal.meta['position_size'] = {
        'quantity': 0.01,
        'notional_usd': 500,
        'risk_usd': 5,
        'risk_r': 0.01,
        'stop_distance': 500,
    }
    signal.meta['tp1'] = 50_500
    signal.meta['tp2'] = 51_000
    signal.meta['market_snapshot'] = {}

    position = await engine._open_position(signal)
    assert position is not None
    assert position.status == 'open'
    assert engine.exchange_client._paper_exchange.balance['USDT'] < config.paper_starting_balance

    await engine._close_position(position, 50_600, 'tp1')
    assert position.status == 'closed'
    assert engine.exchange_client._paper_exchange.balance['USDT'] > config.paper_starting_balance - 100

    await engine.stop()


@pytest.mark.asyncio
async def test_kill_switch_triggers_on_large_loss():
    config = SystemConfig()
    config.trading_mode = 'paper'
    config.paper_starting_balance = 20_000

    engine = OptimizedOrchestraEngine('breakout_v1', config)
    engine.daily_pnl = -config.paper_starting_balance * (engine.preset.risk.kill_switch_loss_limit + 0.01)

    triggered = await engine._check_kill_switch()

    assert triggered is True
    assert engine.kill_switch_active is True
    assert 'Kill switch' in engine.kill_switch_reason

    await engine.stop()
