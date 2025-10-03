# 🚀 Integration Usage Examples

Практические примеры использования интегрированных компонентов микроструктуры рынка.

---

## 1. Базовое использование в Engine

### Запуск с интеграцией

```python
from breakout_bot.core.engine import OptimizedOrchestraEngine
from breakout_bot.config.settings import SystemConfig

# Создание engine
system_config = SystemConfig(
    trading_mode='paper',
    api_key='your_api_key',
    api_secret='your_api_secret'
)

engine = OptimizedOrchestraEngine(
    preset_name='high_percent_breakout',  # Preset с новыми фичами
    system_config=system_config
)

# Инициализация (создает все компоненты)
await engine.initialize()

# Все компоненты микроструктуры теперь доступны:
print(f"TradesAggregator: {engine.trades_aggregator}")
print(f"DensityDetector: {engine.density_detector}")
print(f"ActivityTracker: {engine.activity_tracker}")

# Запуск
await engine.start()
```

---

## 2. Подписка символов на WebSocket

### Автоматическая подписка после сканирования

```python
# Автоматически: топ-20 кандидатов подписываются при scan_markets()
await engine.scanning_manager.scan_markets(exchange_client, session_id)
# → Автоматически вызывается _subscribe_candidates_to_streams()
# → Топ-20 символов подписаны на trades + orderbook
```

### Ручная подписка символа

```python
# Подписать конкретный символ
await engine.subscribe_symbol_to_streams('BTC/USDT')

# Теперь данные для BTC/USDT начнут поступать:
# - trades → TradesAggregator
# - orderbook → OrderBookManager → DensityDetector
```

### Отписка от символа

```python
# Отписаться когда символ больше не нужен
await engine.unsubscribe_symbol_from_streams('BTC/USDT')
```

---

## 3. Получение метрик микроструктуры

### Полные метрики для символа

```python
# Получить все метрики микроструктуры
metrics = engine.get_market_microstructure_metrics('BTC/USDT')

print(f"Symbol: {metrics['symbol']}")
print(f"Timestamp: {metrics['timestamp']}")

# Trades metrics
trades = metrics['trades']
print(f"TPM 60s: {trades['tpm_60s']}")  # Trades per minute
print(f"TPS 10s: {trades['tps_10s']}")  # Trades per second (10s window)
print(f"Vol Delta: {trades['vol_delta']}")  # Buy - Sell volume

# Activity metrics
activity = metrics['activity']
print(f"Activity Index: {activity['index']}")  # Z-score композит
print(f"Is Dropping: {activity['is_dropping']}")  # True если резкое падение
print(f"Drop Fraction: {activity['drop_fraction']}")  # На сколько упало

# Density metrics
for density in metrics['densities']:
    print(f"Price: {density['price']}, Side: {density['side']}, Strength: {density['strength']}")
    print(f"  Eaten: {density['eaten_ratio'] * 100:.1f}%")
```

### Отдельные метрики

```python
# Только trades
tpm_60s = engine.trades_aggregator.get_tpm('BTC/USDT', '60s')
tps_10s = engine.trades_aggregator.get_tps('BTC/USDT', '10s')
vol_delta = engine.trades_aggregator.get_vol_delta('BTC/USDT')

# Только activity
activity_metrics = engine.activity_tracker.get_metrics('BTC/USDT')
if activity_metrics:
    print(f"Activity: {activity_metrics.activity_index}")
    print(f"Dropping: {activity_metrics.is_dropping}")

# Только densities
densities = engine.density_detector.get_densities('BTC/USDT')
for d in densities:
    print(f"{d.side} density at {d.price}: strength={d.strength}, eaten={d.eaten_ratio}")
```

---

## 4. Использование в торговой логике

### Фильтрация сигналов на основе микроструктуры

```python
# SignalManager автоматически применяет фильтры
signals = await engine.signal_manager.generate_signals_from_scan(scan_results)

# Внутри SignalManager._check_microstructure_filters():
# 1. Retest сигналы: отклоняет если TPM = 0 (нет активности)
# 2. Momentum сигналы: проверяет eaten density >= 75%
# 3. Все сигналы: отклоняет если activity_dropping = True

# Результат: только качественные сигналы с подтверждением микроструктуры
```

### Проверка условий для входа

```python
async def should_enter_trade(symbol: str, signal: Signal) -> bool:
    """Пример дополнительной проверки перед входом."""
    
    # 1. Проверить активность
    activity = engine.activity_tracker.get_metrics(symbol)
    if activity and activity.is_dropping:
        print(f"Skip {symbol}: activity dropping")
        return False
    
    # 2. Для momentum: проверить eaten density
    if signal.strategy == 'momentum':
        densities = engine.density_detector.get_densities(symbol)
        direction_side = 'ask' if signal.side == 'long' else 'bid'
        
        eaten_densities = [d for d in densities 
                          if d.side == direction_side and d.eaten_ratio >= 0.75]
        
        if not eaten_densities:
            print(f"Skip {symbol}: no eaten density in direction")
            return False
    
    # 3. Для retest: проверить TPM
    if signal.strategy == 'retest':
        tpm = engine.trades_aggregator.get_tpm(symbol, '60s')
        avg_tpm = 100  # Получить из истории
        
        if tpm < avg_tpm * 0.7:
            print(f"Skip {symbol}: low TPM ({tpm} < {avg_tpm * 0.7})")
            return False
    
    return True
```

### Управление позицией с panic exit

```python
# PositionManager автоматически проверяет activity_drop
# В методе should_close_position():

position = Position(...)  # Открытая позиция

# Автоматическая проверка
close_reason = position_manager.should_close_position(
    current_time=int(time.time() * 1000),
    activity_tracker=engine.activity_tracker,  # Передается автоматически
    symbol=position.symbol
)

if close_reason:
    if "activity drop" in close_reason.lower():
        # Panic exit! Активность резко упала
        print(f"PANIC EXIT: {close_reason}")
        await engine.close_position(position, reason=close_reason)
    elif "time stop" in close_reason.lower():
        # Time-based exit
        print(f"TIME STOP: {close_reason}")
        await engine.close_position(position, reason=close_reason)
```

---

## 5. Работа с enhanced уровнями

### Детектор улучшенных уровней

```python
from breakout_bot.indicators.levels import LevelDetector

# В Scanner создается автоматически, но можно использовать отдельно
detector = LevelDetector(
    min_touches=2,
    prefer_round_numbers=True,
    round_step_candidates=[0.01, 0.05, 0.10, 1.0, 5.0, 10.0],
    cascade_min_levels=3,
    cascade_radius_bps=15
)

# Проверить круглое число
price = 50000.0
is_round, bonus = detector.is_round_number(price)
print(f"Price {price}: round={is_round}, bonus={bonus}")
# Output: Price 50000.0: round=True, bonus=0.15 (бонус 15%)

# Проверить каскад
levels = [
    TradingLevel(price=50000, strength=0.8),
    TradingLevel(price=50050, strength=0.7),
    TradingLevel(price=50100, strength=0.9),
]
cascade = detector.detect_cascade(levels, target_price=50050)
print(f"Cascade detected: {cascade['has_cascade']}")
print(f"Levels in cascade: {cascade['cascade_levels']}")

# Проверить качество подхода
approach = detector.check_approach_quality(candles, level_price=50000)
if not approach['is_valid']:
    print(f"Bad approach: {approach['reason']}")
    # Слишком вертикальный подход или нет консолидации
```

### Улучшенное скоринг уровня

```python
# Автоматически применяется в Scanner, но можно использовать вручную
enhanced_strength = detector.enhance_level_scoring(
    level=level,
    all_levels=all_levels,
    candles=candles
)

# enhanced_strength = base_strength * round_bonus * cascade_bonus
# Пример: 0.8 * 1.15 (round) * 1.25 (cascade) = 1.15 (макс 1.0 после clamp)
```

---

## 6. API эндпоинты

### REST API для микроструктуры

```python
# GET /api/features/microstructure/{symbol}
import requests

response = requests.get('http://localhost:8000/api/features/microstructure/BTCUSDT')
data = response.json()

print(f"TPM: {data['trades']['tpm_60s']}")
print(f"Activity Index: {data['activity']['index']}")
print(f"Densities: {len(data['densities'])}")
```

### WebSocket events

```python
# В api/websocket.py автоматически broadcast'ятся события:

# DENSITY_UPDATE event
{
    "type": "DENSITY_UPDATE",
    "data": {
        "symbol": "BTC/USDT",
        "price": 50000,
        "side": "ask",
        "strength": 2.8,
        "eaten_ratio": 0.85,
        "event_type": "eaten"
    }
}

# ACTIVITY event
{
    "type": "ACTIVITY",
    "data": {
        "symbol": "BTC/USDT",
        "tpm_60s": 145.5,
        "tps_10s": 28.3,
        "activity_index": 1.25,
        "is_dropping": true,
        "drop_fraction": 0.35
    }
}
```

---

## 7. Диагностика и мониторинг

### CLI команды

```bash
# Диагностика L2 данных (orderbook + density)
python3 -m breakout_bot.cli diag-l2 \
    --preset high_percent_breakout \
    --symbol BTC/USDT \
    --minutes 120

# Диагностика уровней (enhanced detection)
python3 -m breakout_bot.cli diag-levels \
    --preset high_percent_breakout \
    --symbol BTC/USDT
```

### Программная диагностика

```python
# Проверить состояние компонентов
print("=== Components Status ===")
print(f"TradesAggregator running: {engine.trades_aggregator.running}")
print(f"Subscribed symbols: {list(engine.trades_aggregator.subscribed_symbols)}")

print(f"OrderBookManager running: {engine.orderbook_manager.running}")
print(f"Tracked symbols: {list(engine.orderbook_manager.subscribed_symbols)}")

print(f"DensityDetector tracked: {list(engine.density_detector.tracked_densities.keys())}")

# Проверить доступность данных
for symbol in engine.trades_aggregator.subscribed_symbols:
    metrics = engine.get_market_microstructure_metrics(symbol)
    print(f"\n{symbol}:")
    print(f"  TPM 60s: {metrics['trades'].get('tpm_60s', 'N/A')}")
    print(f"  Activity: {metrics['activity'].get('index', 'N/A')}")
    print(f"  Densities: {len(metrics['densities'])}")
```

---

## 8. Тестирование интеграции

### Unit тесты компонентов

```bash
# Все unit тесты новых компонентов
pytest breakout_bot/tests/unit/test_trades_ws.py -v
pytest breakout_bot/tests/unit/test_density.py -v
pytest breakout_bot/tests/unit/test_activity.py -v
pytest breakout_bot/tests/unit/test_levels_enhanced.py -v
```

### Integration тесты

```bash
# Тесты интеграции с engine
pytest tests/integration/test_enhanced_features_integration.py -v
```

### Пример integration теста

```python
@pytest.mark.asyncio
async def test_full_trading_cycle_with_microstructure():
    """Test full cycle: scan → signal → filter → execute → manage."""
    
    # 1. Initialize
    engine = OptimizedOrchestraEngine(preset_name='high_percent_breakout')
    await engine.initialize()
    
    # 2. Scan markets (auto-subscribes top candidates)
    scan_results = await engine.scanning_manager.scan_markets(
        exchange_client=engine.exchange_client,
        session_id='test_session'
    )
    assert len(scan_results) > 0
    
    # 3. Generate signals (auto-filters by microstructure)
    signals = await engine.signal_manager.generate_signals_from_scan(
        scan_results,
        session_id='test_session'
    )
    # Signals are already filtered by TPM, density, activity
    
    # 4. Open position
    if signals:
        position = await engine.trading_orchestrator._open_position_from_signal(signals[0])
        assert position is not None
        
        # 5. Monitor position (auto-checks activity drop)
        await asyncio.sleep(1)
        close_reason = engine.position_manager.should_close_position(
            current_time=int(time.time() * 1000),
            activity_tracker=engine.activity_tracker,
            symbol=position.symbol
        )
        
        if close_reason:
            print(f"Position would close: {close_reason}")
```

---

## 9. Production Checklist

### Перед запуском:

```python
# 1. Проверить preset загружен
preset = engine.preset
assert hasattr(preset, 'density_config'), "density_config missing"
assert hasattr(preset, 'levels_rules'), "levels_rules missing"

# 2. Проверить компоненты инициализированы
assert engine.trades_aggregator is not None
assert engine.orderbook_manager is not None
assert engine.density_detector is not None
assert engine.activity_tracker is not None

# 3. Проверить интеграцию
assert engine.signal_manager.trades_aggregator is not None
assert engine.signal_manager.density_detector is not None
assert engine.signal_manager.activity_tracker is not None

assert engine.scanning_manager.trades_aggregator is not None
assert engine.scanning_manager.orderbook_manager is not None

assert engine.position_manager.activity_tracker is not None

# 4. Запустить
await engine.start()
```

### Мониторинг в production:

```python
# Периодически проверять метрики
async def monitor_microstructure():
    while True:
        for symbol in engine.trades_aggregator.subscribed_symbols:
            metrics = engine.get_market_microstructure_metrics(symbol)
            
            # Alert если нет данных
            if metrics['trades']['tpm_60s'] == 0:
                logger.warning(f"{symbol}: No trade activity!")
            
            # Alert при резком падении
            if metrics['activity'].get('is_dropping'):
                logger.warning(f"{symbol}: Activity dropping!")
            
            # Log densities
            if metrics['densities']:
                logger.info(f"{symbol}: {len(metrics['densities'])} densities detected")
        
        await asyncio.sleep(10)
```

---

## 10. Troubleshooting

### Нет данных микроструктуры

```python
# Проверка 1: Символ подписан?
if symbol not in engine.trades_aggregator.subscribed_symbols:
    await engine.subscribe_symbol_to_streams(symbol)

# Проверка 2: WebSocket запущен?
assert engine.trades_aggregator.running
assert engine.orderbook_manager.running

# Проверка 3: Есть ли данные в windows?
trade_window = engine.trades_aggregator.trade_windows.get(symbol)
if trade_window:
    print(f"Trades in window: {len(trade_window.window_10s)}")
```

### Фильтры отклоняют все сигналы

```python
# Временно отключить фильтры для дебага
engine.signal_manager.trades_aggregator = None
engine.signal_manager.density_detector = None
engine.signal_manager.activity_tracker = None

# Сгенерировать сигналы без фильтров
signals = await engine.signal_manager.generate_signals_from_scan(scan_results)
print(f"Signals without filters: {len(signals)}")

# Вернуть фильтры
engine.signal_manager.trades_aggregator = engine.trades_aggregator
# ...
```

### Performance issues

```python
# Проверить размер rolling windows
for symbol, window in engine.trades_aggregator.trade_windows.items():
    print(f"{symbol}: 10s={len(window.window_10s)}, 60s={len(window.window_60s)}")
    # Должно быть разумное количество (< 1000 trades)

# Ограничить количество подписанных символов
max_subscriptions = 20
current = len(engine.trades_aggregator.subscribed_symbols)
if current > max_subscriptions:
    print(f"Too many subscriptions: {current} > {max_subscriptions}")
```

---

**Готово к использованию!** 🚀

Все примеры работают с интегрированными компонентами. Для production осталось только подключить реальные WebSocket streams через `ccxt.pro`.
