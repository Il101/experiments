# 🚀 Quick Start Guide - Enhanced Breakout Bot

## Быстрый запуск за 3 шага

### 1️⃣ Проверка установки

```bash
cd /Users/iliazarikov/Documents/Python_crypto/Barahlo/experiments

# Проверить Python
python3 --version  # Должна быть версия 3.8+

# Установить зависимости (если нужно)
pip3 install -r requirements.txt
```

### 2️⃣ Запуск тестов

Проверим, что все новые компоненты работают:

```bash
# Запустить все unit-тесты
python3 -m pytest breakout_bot/tests/unit/ -v

# Ожидаемый результат: ====== 31 passed in X.XXs ======
```

### 3️⃣ Тестирование функций

#### Вариант A: CLI диагностика

```bash
# Тест L2 фич (density + activity)
python3 -m breakout_bot.cli diag-l2 \
  --preset high_percent_breakout \
  --symbol BTC/USDT \
  --minutes 120

# Тест уровней (round numbers, cascades)
python3 -m breakout_bot.cli diag-levels \
  --preset high_percent_breakout \
  --symbol BTC/USDT
```

#### Вариант B: API сервер

```bash
# Запустить API
python3 -m breakout_bot.api.main

# В другом терминале:
# Тест levels endpoint
curl http://localhost:8000/api/features/levels?symbol=BTC/USDT | jq

# Тест activity endpoint
curl http://localhost:8000/api/features/activity?symbol=BTC/USDT | jq

# Тест density endpoint
curl http://localhost:8000/api/features/density?symbol=BTC/USDT | jq

# Открыть API docs в браузере
open http://localhost:8000/api/docs
```

---

## 📊 Примеры использования в коде

### Пример 1: Trades Aggregator

```python
import asyncio
from breakout_bot.data.streams.trades_ws import TradesAggregator, Trade

async def main():
    # Создать агрегатор
    agg = TradesAggregator()
    await agg.start()
    
    # Подписаться на символ
    await agg.subscribe('BTC/USDT')
    
    # Добавить тестовые сделки
    import time
    current_ts = int(time.time() * 1000)
    
    for i in range(100):
        trade = Trade(
            timestamp=current_ts - (i * 1000),
            price=50000.0 + i,
            amount=1.0,
            side='buy' if i % 2 == 0 else 'sell'
        )
        agg.add_trade('BTC/USDT', trade)
    
    # Получить метрики
    tpm = agg.get_tpm('BTC/USDT', '60s')
    tps = agg.get_tps('BTC/USDT')
    vol_delta = agg.get_vol_delta('BTC/USDT', 60)
    
    print(f"TPM (60s): {tpm:.2f}")
    print(f"TPS (10s): {tps:.2f}")
    print(f"Vol Delta (60s): {vol_delta:.2f}")
    
    await agg.stop()

asyncio.run(main())
```

### Пример 2: Density Detector

```python
import asyncio
from breakout_bot.data.streams.orderbook_ws import (
    OrderBookManager, OrderBookSnapshot, OrderBookLevel
)
from breakout_bot.features.density import DensityDetector

async def main():
    # Создать компоненты
    ob_mgr = OrderBookManager()
    detector = DensityDetector(
        orderbook_manager=ob_mgr,
        k_density=7.0,
        enter_on_density_eat_ratio=0.75
    )
    
    await ob_mgr.start()
    
    # Создать тестовый стакан
    import time
    snapshot = OrderBookSnapshot(
        timestamp=int(time.time() * 1000),
        bids=[
            OrderBookLevel(price=50000.0, size=1.0),
            OrderBookLevel(price=49990.0, size=10.0),  # Большая плотность
            OrderBookLevel(price=49980.0, size=1.5),
        ],
        asks=[
            OrderBookLevel(price=50010.0, size=1.0),
            OrderBookLevel(price=50020.0, size=12.0),  # Большая плотность
            OrderBookLevel(price=50030.0, size=2.0),
        ]
    )
    
    # Обновить стакан
    ob_mgr.update_snapshot('BTC/USDT', snapshot)
    
    # Найти плотности
    densities = detector.detect_densities('BTC/USDT')
    
    for density in densities:
        print(f"{density.side.upper()} density @ {density.price:.2f}")
        print(f"  Size: {density.size:.2f}")
        print(f"  Strength: {density.strength:.2f}x")
    
    # Отслеживать изменения
    events = detector.update_tracked_densities('BTC/USDT')
    
    for event in events:
        print(f"Event: {event.event_type} - {event.density.side} @ {event.density.price:.2f}")
    
    await ob_mgr.stop()

asyncio.run(main())
```

### Пример 3: Activity Tracker

```python
import asyncio
from breakout_bot.data.streams.trades_ws import TradesAggregator, Trade
from breakout_bot.features.activity import ActivityTracker

async def main():
    # Создать компоненты
    agg = TradesAggregator()
    tracker = ActivityTracker(
        trades_aggregator=agg,
        lookback_periods=60,
        drop_threshold=0.3
    )
    
    await agg.start()
    await agg.subscribe('BTC/USDT')
    
    # Добавить сделки
    import time
    current_ts = int(time.time() * 1000)
    
    # Высокая активность
    for i in range(100):
        trade = Trade(
            timestamp=current_ts - (i * 100),
            price=50000.0 + i,
            amount=2.0,
            side='buy' if i % 2 == 0 else 'sell'
        )
        agg.add_trade('BTC/USDT', trade)
    
    # Обновить активность
    metrics = tracker.update_activity('BTC/USDT')
    
    print(f"Activity Index: {metrics.activity_index:.2f}")
    print(f"TPM Z-score: {metrics.tpm_60s_z:.2f}")
    print(f"TPS Z-score: {metrics.tps_10s_z:.2f}")
    print(f"Vol Delta Z-score: {metrics.vol_delta_z:.2f}")
    print(f"Is Dropping: {metrics.is_dropping}")
    
    if metrics.is_dropping:
        print(f"⚠️  Activity drop: {metrics.drop_fraction:.1%}")
    
    await agg.stop()

asyncio.run(main())
```

### Пример 4: Enhanced Level Detection

```python
from breakout_bot.indicators.levels import LevelDetector
from breakout_bot.data.models import Candle, TradingLevel

# Создать detector
detector = LevelDetector(
    prefer_round_numbers=True,
    round_step_candidates=[0.01, 0.05, 0.10, 1.00, 5.00, 10.00],
    cascade_min_levels=2,
    cascade_radius_bps=15.0
)

# Проверить round number
price = 50000.0
is_round, bonus = detector.is_round_number(price)
print(f"Price {price} - Round: {is_round}, Bonus: {bonus:.3f}")

# Создать уровни для cascade теста
levels = [
    TradingLevel(
        price=50000.0,
        level_type='resistance',
        touch_count=3,
        strength=0.8,
        first_touch_ts=1000,
        last_touch_ts=2000
    ),
    TradingLevel(
        price=50005.0,
        level_type='resistance',
        touch_count=2,
        strength=0.75,
        first_touch_ts=1000,
        last_touch_ts=2000
    ),
]

# Найти cascade
cascade_info = detector.detect_cascade(levels, 50000.0)
print(f"\nCascade detected: {cascade_info['has_cascade']}")
print(f"Levels in cascade: {cascade_info['count']}")
print(f"Cascade bonus: {cascade_info['bonus']:.3f}")

# Создать свечи для approach теста
import time
base_ts = int(time.time() * 1000)
candles = []

for i in range(20):
    candle = Candle(
        ts=base_ts + (i * 60000),
        open=49000.0 + (i * 10),
        high=49020.0 + (i * 10),
        low=48980.0 + (i * 10),
        close=49010.0 + (i * 10),
        volume=100.0
    )
    candles.append(candle)

# Проверить approach quality
approach = detector.check_approach_quality(
    candles=candles,
    level_price=49500.0,
    lookback_bars=10
)

print(f"\nApproach valid: {approach['is_valid']}")
print(f"Slope: {approach['slope_pct_per_bar']:.2f}% per bar")
print(f"Consolidation bars: {approach['consolidation_bars']}")
print(f"Reason: {approach['reason']}")
```

### Пример 5: Использование preset

```python
from breakout_bot.config.settings import get_preset

# Загрузить preset
preset = get_preset('high_percent_breakout')

# Конфиг уровней
print("=== Levels Rules ===")
print(f"Min touches: {preset.levels_rules.min_touches}")
print(f"Prefer round: {preset.levels_rules.prefer_round_numbers}")
print(f"Round steps: {preset.levels_rules.round_step_candidates}")
print(f"Cascade min: {preset.levels_rules.cascade_min_levels}")
print(f"Cascade radius: {preset.levels_rules.cascade_radius_bps} bps")

# Конфиг density
print("\n=== Density Config ===")
print(f"k_density: {preset.density_config.k_density}")
print(f"Bucket ticks: {preset.density_config.bucket_ticks}")
print(f"Lookback: {preset.density_config.lookback_window_s}s")

# Конфиг signals
print("\n=== Signal Config ===")
print(f"Prelevel offset: {preset.signal_config.prelevel_limit_offset_bps} bps")
print(f"Density eat ratio: {preset.signal_config.enter_on_density_eat_ratio}")
print(f"TPM touch frac: {preset.signal_config.tpm_on_touch_frac}")

# Конфиг position
print("\n=== Position Config ===")
print(f"Time stop: {preset.position_config.time_stop_minutes} min")
print(f"Panic exit: {preset.position_config.panic_exit_on_activity_drop}")
print(f"Activity drop threshold: {preset.position_config.activity_drop_threshold}")
```

---

## 🐛 Troubleshooting

### Проблема: Тесты не запускаются

```bash
# Установить pytest
pip3 install pytest pytest-asyncio

# Проверить установку
python3 -m pytest --version
```

### Проблема: API не запускается

```bash
# Установить FastAPI и uvicorn
pip3 install fastapi uvicorn[standard]

# Проверить установку
python3 -c "import fastapi; print(fastapi.__version__)"
```

### Проблема: ImportError

```bash
# Установить все зависимости
pip3 install -r requirements.txt

# Или вручную:
pip3 install numpy pandas ccxt pydantic fastapi uvicorn pytest
```

---

## 📚 Документация

- **Полное руководство:** `ENHANCED_FEATURES_GUIDE.md`
- **Сводка реализации:** `IMPLEMENTATION_SUMMARY.md`
- **API документация:** http://localhost:8000/api/docs (после запуска сервера)

---

## ✅ Чеклист готовности

- [x] Все тесты прошли (31/31)
- [x] API endpoints работают
- [x] CLI команды работают
- [x] Preset создан и валидный
- [x] Документация написана
- [x] Примеры кода готовы

---

**Готово к интеграции! 🚀**

Все компоненты реализованы, протестированы и задокументированы.
Следующий шаг — интеграция в основной trading engine.
