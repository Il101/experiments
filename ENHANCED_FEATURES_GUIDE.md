# Enhanced Breakout Bot - Integration Guide

## 🎯 Overview

This document describes the comprehensive integration of advanced market microstructure features into the Breakout Bot trading system. All components have been implemented and tested.

---

## ✅ Implemented Features

### 1. **Trades WebSocket Aggregator** (`data/streams/trades_ws.py`)

Real-time trade flow analysis:
- **TPM** (Trades Per Minute) - 10s and 60s windows
- **TPS** (Trades Per Second) - 10s window
- **Buy/Sell Ratio** - 60s window
- **Volume Delta** - 10s, 60s, 300s windows
- Automatic reconnection and latency tracking

**Usage:**
```python
from breakout_bot.data.streams.trades_ws import TradesAggregator

# Initialize
agg = TradesAggregator()
await agg.start()
await agg.subscribe('BTC/USDT')

# Get metrics
tpm = agg.get_tpm('BTC/USDT', '60s')
vol_delta = agg.get_vol_delta('BTC/USDT', 60)
metrics = agg.get_metrics('BTC/USDT')
```

---

### 2. **OrderBook WebSocket Manager** (`data/streams/orderbook_ws.py`)

Real-time order book tracking:
- Snapshot + delta updates
- Depth aggregation by price buckets
- Imbalance calculation
- Historical depth tracking

**Usage:**
```python
from breakout_bot.data.streams.orderbook_ws import OrderBookManager

# Initialize
ob_mgr = OrderBookManager()
await ob_mgr.start()
await ob_mgr.subscribe('BTC/USDT')

# Get data
snapshot = ob_mgr.get_snapshot('BTC/USDT')
imbalance = ob_mgr.get_imbalance('BTC/USDT', range_bps=30)
depth = ob_mgr.get_aggregated_depth('BTC/USDT', 'bid', range_bps=50)
```

---

### 3. **Density Detector** (`features/density.py`)

Detects significant liquidity concentrations (walls) and tracks consumption:
- Density threshold: `size ≥ k_density × median_bucket_size`
- Tracks "eaten" densities
- Alerts when `eaten_ratio ≥ enter_on_density_eat_ratio`

**Configuration (in preset):**
```json
"density_config": {
  "k_density": 7.0,
  "bucket_ticks": 3,
  "lookback_window_s": 300
}
```

**Usage:**
```python
from breakout_bot.features.density import DensityDetector

detector = DensityDetector(
    orderbook_manager=ob_mgr,
    k_density=7.0,
    enter_on_density_eat_ratio=0.75
)

# Detect densities
densities = detector.detect_densities('BTC/USDT')

# Track changes
events = detector.update_tracked_densities('BTC/USDT')

# Get density at price
density = detector.get_density_at_price('BTC/USDT', 50000.0, 'bid')
```

---

### 4. **Activity Tracker** (`features/activity.py`)

Monitors trading activity and detects momentum decay:
- **Activity Index**: `Z(tpm_60s) + Z(tps_10s) + Z(|vol_delta_60s|)`
- Drop detection: alerts when activity drops significantly

**Configuration (in preset):**
```json
"position_config": {
  "panic_exit_on_activity_drop": true,
  "activity_drop_threshold": 0.4
}
```

**Usage:**
```python
from breakout_bot.features.activity import ActivityTracker

tracker = ActivityTracker(
    trades_aggregator=agg,
    drop_threshold=0.3
)

# Update activity
metrics = tracker.update_activity('BTC/USDT')

# Check for drop
is_dropping = tracker.is_activity_dropping('BTC/USDT')
activity_index = tracker.get_activity_index('BTC/USDT')
```

---

### 5. **Enhanced Level Detection** (`indicators/levels.py`)

Extended level detection with:
- **Round Numbers**: Bonus scoring for psychological levels
- **Cascades**: Detection of clustered levels
- **Approach Quality**: Filters vertical approaches, requires consolidation

**Configuration (in preset):**
```json
"levels_rules": {
  "min_touches": 2,
  "prefer_round_numbers": true,
  "round_step_candidates": [0.01, 0.05, 0.10, 1.00, 5.00, 10.00],
  "cascade_min_levels": 2,
  "cascade_radius_bps": 15,
  "approach_slope_max_pct_per_bar": 1.5,
  "prebreakout_consolidation_min_bars": 3
}
```

**Usage:**
```python
from breakout_bot.indicators.levels import LevelDetector

detector = LevelDetector(
    prefer_round_numbers=True,
    round_step_candidates=[0.01, 0.05, 0.10, 1.00, 5.00],
    cascade_min_levels=2
)

# Check round number
is_round, bonus = detector.is_round_number(50000.0)

# Detect cascade
cascade_info = detector.detect_cascade(all_levels, target_price)

# Check approach quality
approach = detector.check_approach_quality(candles, level_price)
```

---

### 6. **Enhanced Signal Generation** (`signals/signal_generator.py`)

Improved signal logic:
- **Prelevel Limit Entry**: Enter with limit order before level
- **Retest with TPM**: Require `tpm_on_touch ≥ frac × avg_tpm_1h`
- **Density Entry**: Trigger on density eaten

**Configuration (in preset):**
```json
"signal_config": {
  "prelevel_limit_offset_bps": 2.0,
  "enter_on_density_eat_ratio": 0.75,
  "tpm_on_touch_frac": 0.7
}
```

---

### 7. **Enhanced Position Management** (`position/position_manager.py`)

Added features:
- **Time-stop**: Close position after `time_stop_minutes`
- **Panic Exit**: Close on activity drop
- **TP1 → SL to BE**: Move stop to breakeven after TP1
- **Chandelier Trailing**: ATR-based trailing stop

**Configuration (in preset):**
```json
"position_config": {
  "time_stop_minutes": 180,
  "panic_exit_on_activity_drop": true,
  "activity_drop_threshold": 0.4
}
```

**Usage:**
```python
# Check for close conditions
reason = tracker.should_close_position(
    current_time=current_ts,
    activity_tracker=activity_tracker,
    symbol='BTC/USDT'
)
```

---

### 8. **API Endpoints** (`api/routers/features.py`)

New REST endpoints:

#### `GET /api/features/levels?symbol=BTC/USDT`
Returns:
- Detected levels
- Round number levels
- Cascade information
- Approach metrics

#### `GET /api/features/activity?symbol=BTC/USDT`
Returns:
- TPM, TPS, volume delta
- Activity index and components
- Drop detection status

#### `GET /api/features/density?symbol=BTC/USDT`
Returns:
- Current density levels
- Eaten ratios
- Strength metrics

---

### 9. **WebSocket Events** (`api/websocket.py`)

New real-time events:

#### `DENSITY_UPDATE`
```json
{
  "type": "DENSITY_UPDATE",
  "data": {
    "symbol": "BTC/USDT",
    "price": 50000.0,
    "side": "bid",
    "strength": 8.5,
    "eaten_ratio": 0.75
  }
}
```

#### `ACTIVITY`
```json
{
  "type": "ACTIVITY",
  "data": {
    "symbol": "BTC/USDT",
    "tpm": 45.5,
    "tps": 0.87,
    "vol_delta": 1250.5,
    "activity_index": 2.45,
    "is_dropping": false
  }
}
```

---

## 🧪 Testing

### Unit Tests

Run all tests:
```bash
pytest breakout_bot/tests/unit/ -v
```

Individual test files:
```bash
# Trades aggregator
pytest breakout_bot/tests/unit/test_trades_ws.py -v

# Density detector
pytest breakout_bot/tests/unit/test_density.py -v

# Activity tracker
pytest breakout_bot/tests/unit/test_activity.py -v

# Enhanced levels
pytest breakout_bot/tests/unit/test_levels_enhanced.py -v
```

### CLI Diagnostics

Test L2 features (density + activity):
```bash
python -m breakout_bot.cli diag-l2 \
  --preset high_percent_breakout \
  --symbol BTC/USDT \
  --minutes 120
```

Test level detection:
```bash
python -m breakout_bot.cli diag-levels \
  --preset high_percent_breakout \
  --symbol BTC/USDT
```

---

## 📦 Configuration

### Complete Preset Example (`high_percent_breakout.json`)

The new preset includes all enhanced configurations:
```json
{
  "name": "high_percent_breakout",
  "signal_config": {
    "prelevel_limit_offset_bps": 2.0,
    "enter_on_density_eat_ratio": 0.75,
    "tpm_on_touch_frac": 0.7
  },
  "position_config": {
    "time_stop_minutes": 180,
    "panic_exit_on_activity_drop": true,
    "activity_drop_threshold": 0.4
  },
  "levels_rules": {
    "min_touches": 2,
    "prefer_round_numbers": true,
    "round_step_candidates": [0.01, 0.05, 0.10, 1.00, 5.00, 10.00],
    "cascade_min_levels": 2,
    "cascade_radius_bps": 15,
    "approach_slope_max_pct_per_bar": 1.5,
    "prebreakout_consolidation_min_bars": 3
  },
  "density_config": {
    "k_density": 7.0,
    "bucket_ticks": 3,
    "lookback_window_s": 300
  }
}
```

---

## 🚀 Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Run Tests
```bash
pytest breakout_bot/tests/unit/ -v
```

### 3. Start API Server
```bash
python -m breakout_bot.api.main
```

API will be available at: `http://localhost:8000/api/docs`

### 4. Test Features
```bash
# Test levels
curl http://localhost:8000/api/features/levels?symbol=BTC/USDT

# Test activity
curl http://localhost:8000/api/features/activity?symbol=BTC/USDT

# Test density
curl http://localhost:8000/api/features/density?symbol=BTC/USDT
```

---

## 📊 Monitoring

### DiagnosticsCollector Integration

New metrics are automatically recorded:
- `density_strength`
- `density_eaten_ratio`
- `activity_index`
- `activity_drop`
- `round_number_bonus`
- `cascade_bonus`
- `approach_ok`

---

## 🔧 Production Deployment

### 1. WebSocket Integration

Replace placeholders with real exchange WebSocket:

**trades_ws.py:**
```python
# Replace _process_trades() with actual ccxt.pro trades subscription
import ccxt.pro as ccxtpro

async def _process_trades(self, symbol: str):
    exchange = ccxtpro.binance()  # or bybit
    while self.running:
        trades = await exchange.watch_trades(symbol)
        for trade in trades:
            self.add_trade(symbol, Trade(
                timestamp=trade['timestamp'],
                price=trade['price'],
                amount=trade['amount'],
                side=trade['side']
            ))
```

**orderbook_ws.py:**
```python
# Replace _process_orderbook() with actual order book subscription
async def _process_orderbook(self, symbol: str):
    exchange = ccxtpro.binance()
    while self.running:
        orderbook = await exchange.watch_order_book(symbol)
        # Convert to OrderBookSnapshot and update
```

### 2. Enable Real-Time Events

In `api/websocket.py`, uncomment:
```python
# Density updates
density_events = engine.get_recent_density_events()

# Activity updates
activity_data = engine.get_activity_snapshot()
```

---

## 📝 Notes

### Current Status
- ✅ All core features implemented
- ✅ Unit tests written and passing
- ✅ API endpoints functional
- ✅ CLI diagnostics available
- ✅ Configuration system extended
- ⏳ WebSocket integration (placeholder - needs real exchange connection)

### Next Steps for Production
1. Connect to real exchange WebSocket for trades
2. Connect to real exchange WebSocket for order book
3. Integrate density/activity into main trading engine
4. Add more comprehensive integration tests
5. Performance profiling and optimization

---

## 🆘 Support

For issues or questions:
1. Check unit tests for usage examples
2. Run CLI diagnostics for validation
3. Review API docs at `/api/docs`
4. Check logs in `logs/` directory

---

**Version:** 1.0.0  
**Date:** January 2025  
**Status:** Ready for Integration Testing
