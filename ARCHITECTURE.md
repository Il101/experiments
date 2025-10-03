# 🏗️ Architecture Overview - Enhanced Features Integration

## Диаграмма компонентов

```
┌─────────────────────────────────────────────────────────────────┐
│                      Trading Engine (Core)                       │
│                                                                   │
│  ┌────────────────┐  ┌────────────────┐  ┌─────────────────┐   │
│  │  Scanner       │  │ Signal Gen     │  │ Position Mgr    │   │
│  │  (existing)    │  │ (enhanced)     │  │ (enhanced)      │   │
│  └───────┬────────┘  └────────┬───────┘  └────────┬────────┘   │
│          │                     │                    │            │
└──────────┼─────────────────────┼────────────────────┼────────────┘
           │                     │                    │
           └─────────┬───────────┴──────────┬─────────┘
                     │                      │
          ┌──────────▼──────────┐  ┌────────▼─────────┐
          │  Market Data Layer  │  │  Feature Layer   │
          │  (NEW)              │  │  (NEW)           │
          │                     │  │                  │
          │ ┌─────────────────┐ │  │ ┌──────────────┐│
          │ │ TradesAggregator│ │  │ │DensityDetector││
          │ │  - TPM/TPS      │ │  │ │  - Walls     ││
          │ │  - Vol Delta    │ │  │ │  - Eaten     ││
          │ └────────┬────────┘ │  │ └──────┬───────┘│
          │          │          │  │        │        │
          │ ┌────────▼────────┐ │  │ ┌──────▼───────┐│
          │ │OrderBookManager │ │  │ │ActivityTracker│
          │ │  - Snapshots    │ │  │ │  - Index     ││
          │ │  - Imbalance    │ │  │ │  - Drop      ││
          │ └─────────────────┘ │  │ └──────────────┘│
          └─────────────────────┘  └──────────────────┘
                     │                      │
          ┌──────────▼──────────────────────▼─────────┐
          │         Exchange WebSocket                 │
          │  (ccxt.pro или нативный WS)               │
          └────────────────────────────────────────────┘
                           │
                ┌──────────▼──────────┐
                │   Exchange API      │
                │  (Bybit/Binance)    │
                └─────────────────────┘
```

---

## Поток данных

### 1. Инициализация (Engine Startup)

```python
# В engine.__init__ или startup()

# 1. Создать market data компоненты
self.trades_agg = TradesAggregator(exchange_client=self.exchange_client)
self.orderbook_mgr = OrderBookManager(exchange_client=self.exchange_client)

# 2. Создать feature компоненты
self.density_detector = DensityDetector(
    orderbook_manager=self.orderbook_mgr,
    k_density=self.preset.density_config.k_density,
    bucket_ticks=self.preset.density_config.bucket_ticks
)

self.activity_tracker = ActivityTracker(
    trades_aggregator=self.trades_agg,
    drop_threshold=self.preset.position_config.activity_drop_threshold
)

# 3. Создать enhanced level detector
self.level_detector = LevelDetector(
    min_touches=self.preset.levels_rules.min_touches,
    prefer_round_numbers=self.preset.levels_rules.prefer_round_numbers,
    round_step_candidates=self.preset.levels_rules.round_step_candidates,
    cascade_min_levels=self.preset.levels_rules.cascade_min_levels,
    cascade_radius_bps=self.preset.levels_rules.cascade_radius_bps
)

# 4. Запустить WS streams
await self.trades_agg.start()
await self.orderbook_mgr.start()
```

---

### 2. Symbol Subscription (При сканировании)

```python
# Когда символ добавляется в активное отслеживание

async def add_symbol_to_tracking(self, symbol: str):
    # Подписаться на trades
    await self.trades_agg.subscribe(symbol)
    
    # Подписаться на orderbook
    await self.orderbook_mgr.subscribe(symbol)
    
    logger.info(f"Started tracking {symbol} on WS")
```

---

### 3. Real-time Updates (Основной цикл)

```python
# В основном цикле engine (каждые N секунд)

async def update_market_features(self):
    for symbol in self.active_symbols:
        # 1. Обновить activity
        activity_metrics = self.activity_tracker.update_activity(symbol)
        
        # 2. Обновить densities
        density_events = self.density_detector.update_tracked_densities(symbol)
        
        # 3. Обработать density события
        for event in density_events:
            if event.event_type == 'eaten':
                # Возможно, сгенерировать сигнал на вход
                await self._handle_density_eaten(symbol, event)
        
        # 4. Проверить activity drop для открытых позиций
        if activity_metrics.is_dropping:
            await self._check_panic_exit(symbol, activity_metrics)
```

---

### 4. Signal Generation (Генерация сигналов)

```python
# В signal_generator.py

async def generate_signals(
    self,
    symbol: str,
    candles: List[Candle],
    levels: List[TradingLevel],
    market_data: MarketData
) -> List[Signal]:
    
    signals = []
    
    # 1. Получить текущие метрики
    activity = self.activity_tracker.get_metrics(symbol)
    densities = self.density_detector.get_densities(symbol)
    
    # 2. Улучшенная оценка уровней
    for level in levels:
        enhanced_strength = self.level_detector.enhance_level_scoring(
            level=level,
            all_levels=levels,
            candles=candles
        )
        
        # 3. Проверить approach quality
        approach = self.level_detector.check_approach_quality(
            candles=candles,
            level_price=level.price
        )
        
        if not approach['is_valid']:
            continue  # Skip vertical approaches
        
        # 4. Momentum signal с density
        if self._is_momentum_breakout(candles, level):
            # Проверить есть ли density в направлении пробоя
            density = self._find_density_at_level(densities, level)
            
            if density and density.eaten_ratio >= 0.75:
                # Density eaten → strong momentum signal
                signal = self._create_signal(
                    symbol=symbol,
                    level=level,
                    strategy='momentum',
                    confidence=enhanced_strength,
                    meta={
                        'density_eaten': True,
                        'eaten_ratio': density.eaten_ratio,
                        'activity_index': activity.activity_index if activity else 0
                    }
                )
                signals.append(signal)
        
        # 5. Retest signal с TPM requirement
        if self._is_retest_setup(candles, level):
            # Проверить TPM
            tpm = self.trades_agg.get_tpm(symbol, '60s')
            avg_tpm_1h = self._get_avg_tpm_1h(symbol)  # Historical
            
            if tpm >= avg_tpm_1h * 0.7:  # tpm_on_touch_frac
                signal = self._create_signal(
                    symbol=symbol,
                    level=level,
                    strategy='retest',
                    confidence=enhanced_strength * 0.9,
                    meta={
                        'tpm': tpm,
                        'tpm_threshold': avg_tpm_1h * 0.7
                    }
                )
                signals.append(signal)
    
    return signals
```

---

### 5. Position Management (Управление позициями)

```python
# В position_manager.py

async def update_position(
    self,
    position: Position,
    current_price: float,
    candles: List[Candle]
):
    tracker = self.position_trackers[position.id]
    current_ts = int(time.time() * 1000)
    
    # 1. Проверить time-stop
    close_reason = tracker.should_close_position(
        current_time=current_ts,
        activity_tracker=self.activity_tracker,
        symbol=position.symbol
    )
    
    if close_reason:
        if "activity drop" in close_reason.lower():
            # Panic exit
            await self._execute_panic_exit(position, close_reason)
        else:
            # Normal time-based exit
            await self._close_position(position, close_reason)
        return
    
    # 2. Проверить TP1 → move SL to BE
    tp_result = tracker.should_take_profit(current_price)
    if tp_result:
        tp_level, tp_price, tp_qty = tp_result
        
        if tp_level == 'tp1' and not tracker.tp1_executed:
            # Исполнить TP1
            await self._execute_take_profit(position, tp_qty, tp_price)
            tracker.tp1_executed = True
            
            # Move SL to breakeven
            new_sl = tracker.should_update_stop(current_price, candles)
            if new_sl:
                await self._update_stop_loss(position, new_sl)
                tracker.breakeven_moved = True
    
    # 3. Chandelier trailing (after breakeven)
    if tracker.breakeven_moved:
        new_sl = tracker.should_update_stop(current_price, candles)
        if new_sl and new_sl != position.sl:
            await self._update_stop_loss(position, new_sl)
```

---

### 6. API/WebSocket Broadcasting

```python
# В api/websocket.py

async def broadcast_market_updates(engine):
    # 1. Density updates
    for symbol in engine.active_symbols:
        events = engine.density_detector.get_recent_events(symbol)
        
        for event in events:
            await manager.broadcast(
                create_websocket_message("DENSITY_UPDATE", {
                    "symbol": symbol,
                    "price": event.density.price,
                    "side": event.density.side,
                    "strength": event.density.strength,
                    "eaten_ratio": event.density.eaten_ratio,
                    "event_type": event.event_type
                })
            )
    
    # 2. Activity updates
    for symbol in engine.active_symbols:
        metrics = engine.activity_tracker.get_metrics(symbol)
        
        if metrics:
            await manager.broadcast(
                create_websocket_message("ACTIVITY", {
                    "symbol": symbol,
                    "tpm_60s": metrics.tpm_60s_z,
                    "tps_10s": metrics.tps_10s_z,
                    "activity_index": metrics.activity_index,
                    "is_dropping": metrics.is_dropping,
                    "drop_fraction": metrics.drop_fraction
                })
            )
```

---

## Integration Points

### 1. Scanner Integration

```python
# В market_scanner.py

# Добавить enhanced level detection
levels = self.level_detector.detect_levels(candles)

# Для каждого level:
for level in levels:
    # Check round number
    is_round, bonus = self.level_detector.is_round_number(level.price)
    
    # Check cascade
    cascade_info = self.level_detector.detect_cascade(levels, level.price)
    
    # Enhance score
    enhanced_strength = self.level_detector.enhance_level_scoring(
        level=level,
        all_levels=levels,
        candles=candles
    )
    
    # Update metrics
    scan_result.meta['round_number'] = is_round
    scan_result.meta['cascade'] = cascade_info['has_cascade']
    scan_result.meta['enhanced_strength'] = enhanced_strength
```

---

### 2. DiagnosticsCollector Integration

```python
# Записывать новые метрики

# Density
self.diagnostics.record_custom_metric(
    'density_strength',
    density.strength,
    {'symbol': symbol, 'side': density.side}
)

# Activity
self.diagnostics.record_custom_metric(
    'activity_index',
    metrics.activity_index,
    {'symbol': symbol}
)

# Level enhancements
self.diagnostics.record_custom_metric(
    'round_number_bonus',
    bonus,
    {'symbol': symbol, 'price': level.price}
)
```

---

## Configuration Examples

### Preset Loading

```python
from breakout_bot.config.settings import get_preset

preset = get_preset('high_percent_breakout')

# Use in components:
trades_agg = TradesAggregator()
density_detector = DensityDetector(
    orderbook_manager=ob_mgr,
    k_density=preset.density_config.k_density,
    bucket_ticks=preset.density_config.bucket_ticks,
    enter_on_density_eat_ratio=preset.signal_config.enter_on_density_eat_ratio
)
```

---

## Testing Integration

### Integration Test Template

```python
# tests/integration/test_enhanced_features_integration.py

import pytest
from breakout_bot.core.engine import TradingEngine
from breakout_bot.config.settings import get_preset

@pytest.mark.asyncio
async def test_full_cycle_with_density():
    """Test full trading cycle with density detection."""
    
    # 1. Setup
    preset = get_preset('high_percent_breakout')
    engine = TradingEngine(preset, mode='paper')
    
    await engine.start()
    
    # 2. Add symbol
    await engine.add_symbol('BTC/USDT')
    
    # 3. Wait for data accumulation
    await asyncio.sleep(10)
    
    # 4. Check components are working
    trades_metrics = engine.trades_agg.get_metrics('BTC/USDT')
    assert trades_metrics is not None
    
    densities = engine.density_detector.get_densities('BTC/USDT')
    # Should have some densities detected
    
    activity = engine.activity_tracker.get_metrics('BTC/USDT')
    assert activity is not None
    
    # 5. Cleanup
    await engine.stop()
```

---

## Performance Considerations

### Memory Management

- **TradesAggregator**: Автоматически чистит старые сделки
- **OrderBookManager**: Хранит только последний snapshot
- **DensityDetector**: Ограничивает историю bucket_history (deque с maxlen)
- **ActivityTracker**: Ограничивает историю (deque с maxlen)

### Latency Optimization

- Async везде где возможно
- Batch updates вместо individual
- Caching для часто используемых вычислений
- ThreadPoolExecutor для CPU-bound операций

---

## Next Steps

1. ✅ **Реализовано:** Все компоненты
2. ⏳ **TODO:** WebSocket integration с реальной биржей
3. ⏳ **TODO:** Integration tests
4. ⏳ **TODO:** Performance profiling
5. ⏳ **TODO:** Production deployment

---

**Architecture Status:** ✅ Designed and Ready for Integration

Все компоненты спроектированы для seamless интеграции в существующий engine.
