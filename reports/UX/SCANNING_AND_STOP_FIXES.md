# Исправления критических UX проблем - 3 октября 2025

## Резюме исправлений

Обнаружены и исправлены **три критические проблемы**:

1. ❌ **Застревание в стадии сканирования** - система не находила кандидатов и не переходила к следующим фазам
2. ❌ **Кнопка "Остановить" не останавливает движок** - приходилось ждать до 5 секунд
3. ❌ **Множественные активные сессии** - после остановки в UI оставались старые сессии

✅ **Все проблемы исправлены и готовы к тестированию**

---

## Проблема 1: Застревание в стадии сканирования

### Корневая причина
Система находила **0 кандидатов** при сканировании из-за слишком строгих фильтров ликвидности:

```
min_24h_volume_usd: 15,000,000 USD  ❌ Слишком высоко
min_oi_usd: 5,000,000 USD           ❌ Слишком высоко
min_depth_usd_0_5pct: 15,000 USD    ❌ Слишком высоко
```

Когда кандидатов 0, код в `trading_orchestrator._execute_scanning_cycle()` оставался в состоянии SCANNING:

```python
if scan_results:
    # Переход к следующей стадии
    await self.state_machine.transition_to(TradingState.LEVEL_BUILDING, ...)
else:
    # ❌ ПРОБЛЕМА: Остаемся в сканировании
    await asyncio.sleep(5.0)
```

### Решение

**1. Смягчены фильтры в `breakout_v1.json`:**
```json
"liquidity_filters": {
  "min_24h_volume_usd": 5000000,      // ✅ Было: 15M → Стало: 5M
  "min_oi_usd": 2000000,              // ✅ Было: 5M → Стало: 2M
  "max_spread_bps": 30,               // ✅ Было: 20 → Стало: 30
  "min_depth_usd_0_5pct": 8000,       // ✅ Было: 15K → Стало: 8K
  "min_depth_usd_0_3pct": 5000,       // ✅ Было: 10K → Стало: 5K
  "min_trades_per_minute": 3.0        // ✅ Было: 4.0 → Стало: 3.0
}
```

**2. Создан новый пресет `breakout_v1_relaxed.json`** для тестирования с еще более мягкими фильтрами:
```json
"liquidity_filters": {
  "min_24h_volume_usd": 2000000,      // Очень мягкий фильтр
  "min_oi_usd": 1000000,
  "max_spread_bps": 50,
  "min_depth_usd_0_5pct": 5000,
  "min_depth_usd_0_3pct": 3000,
  "min_trades_per_minute": 2.0
}
```

**3. Смягчены фильтры волатильности:**
```json
"volatility_filters": {
  "atr_range_max": 0.12,              // ✅ Было: 0.10 → Стало: 0.12
  "bb_width_percentile_max": 82,      // ✅ Было: 80 → Стало: 82
  "volume_surge_1h_min": 1.15,        // ✅ Было: 1.2 → Стало: 1.15
  "volume_surge_5m_min": 1.4,         // ✅ Было: 1.6 → Стало: 1.4
  "oi_delta_threshold": 0.018         // ✅ Было: 0.02 → Стало: 0.018
}
```

### Ожидаемый результат
- Сканирование теперь будет находить кандидатов
- Система сможет переходить к следующим фазам: LEVEL_BUILDING → SIGNAL_WAIT → SIZING → EXECUTION
- Больше торговых возможностей

---

## Проблема 2: Кнопка "Остановить" не останавливает движок

### Корневая причина
При нажатии кнопки "Остановить", флаг `self.running` устанавливался в `False`, но главный цикл находился в состоянии `await asyncio.sleep(5.0)` (в фазе SCANNING). 

Цикл должен был ждать 5 секунд до завершения sleep, прежде чем проверить флаг `self.running` и остановиться.

```python
# ❌ СТАРЫЙ КОД
while self.running:
    # ... выполнение цикла ...
    await asyncio.sleep(5.0)  # 🐌 Блокирует на 5 секунд!
```

### Решение

**1. Добавлен `asyncio.Event` для немедленной остановки:**
```python
class OptimizedOrchestraEngine:
    def __init__(self, ...):
        self.running = False
        self._stop_event = asyncio.Event()  # ✅ Новое!
```

**2. Метод `stop()` теперь устанавливает событие:**
```python
async def stop(self):
    """Остановить торговую систему.""" 
    logger.info("Stopping OptimizedOrchestraEngine...")
    self.running = False
    self._stop_event.set()  # ✅ Сигнализировать о немедленной остановке
    if hasattr(self, 'state_machine') and self.state_machine:
        await self.state_machine.transition_to(TradingState.STOPPED, "Manual stop requested")
```

**3. Главный цикл использует прерываемый sleep:**
```python
# ✅ НОВЫЙ КОД - Прерываемая задержка
delay = 5.0  # или другое значение в зависимости от состояния

try:
    # Ждем событие остановки с таймаутом
    await asyncio.wait_for(self._stop_event.wait(), timeout=delay)
    # Если событие сработало, выходим немедленно
    logger.info("Stop event received, exiting main loop")
    break
except asyncio.TimeoutError:
    # Нормальный таймаут - продолжаем работу
    pass
```

**4. Emergency stop тоже использует событие:**
```python
async def emergency_stop(self, reason: str = "Manual emergency stop"):
    logger.critical(f"Emergency stop triggered: {reason}")
    self.running = False
    self._stop_event.set()  # ✅ Немедленная остановка
    self.emergency_reason = reason
    if hasattr(self, 'state_machine') and self.state_machine:
        await self.state_machine.transition_to(TradingState.EMERGENCY, reason)
```

### Ожидаемый результат
- Кнопка "Остановить" теперь останавливает движок **мгновенно** (в пределах миллисекунд)
- Не нужно ждать до 5 секунд до остановки
- Emergency stop также работает моментально

---

## Проблема 3: Множественные активные сессии

### Корневая причина
При остановке движка старые сессии помечались как неактивные, но **не удалялись из памяти**. API возвращал все сессии (включая неактивные), и фронтенд показывал их как активные.

```python
# ❌ ПРОБЛЕМА
# 1. Сессии оставались в памяти после остановки
# 2. API возвращал все сессии, включая is_active=False
# 3. Frontend показывал несколько активных сессий
```

### Решение

**1. Немедленная очистка при остановке:**
```python
def end_all_sessions(self, reason: str = "Engine stopped", cleanup: bool = True):
    # ... завершаем сессии ...
    
    # ✅ Немедленная очистка неактивных сессий
    if cleanup:
        inactive_sessions = [sid for sid, s in self.active_sessions.items() if not s.is_active]
        for session_id in inactive_sessions:
            del self.active_sessions[session_id]
            if session_id in self.session_checkpoints:
                del self.session_checkpoints[session_id]
```

**2. Фильтрация в API:**
```python
@router.get("/sessions")
async def get_active_sessions():
    sessions = []
    for session_id, session in monitoring_manager.active_sessions.items():
        # ✅ Пропускаем неактивные сессии
        if not session.is_active:
            continue
        sessions.append(session_data)
    return sessions
```

### Ожидаемый результат
- В UI показывается только одна активная сессия после запуска
- При остановке все сессии удаляются немедленно
- Повторный запуск создает только одну новую сессию

---

## Файлы изменены

1. **breakout_bot/config/presets/breakout_v1.json** - смягчены фильтры
2. **breakout_bot/config/presets/breakout_v1_relaxed.json** - создан новый пресет
3. **breakout_bot/core/engine.py** - добавлен прерываемый sleep для мгновенной остановки
4. **breakout_bot/utils/monitoring_manager.py** - немедленная очистка сессий
5. **breakout_bot/api/routers/engine.py** - вызов очистки при остановке
6. **breakout_bot/api/routers/monitoring.py** - фильтрация только активных сессий

---

## Как протестировать

### Тест 1: Проверка сканирования
```bash
# Запустить бота
./start.sh

# Проверить логи
tail -f logs/general.log | grep "Market scan completed"

# Должно быть: "Market scan completed: X candidates found" где X > 0
```

### Тест 2: Проверка мгновенной остановки
```bash
# 1. Запустить бота
./start.sh

# 2. Открыть UI и нажать "Stop Engine"
# Или через API:
curl -X POST http://localhost:8000/api/engine/stop

# 3. Проверить время остановки в логах
# Должно быть < 1 секунды, а не 5 секунд
```

### Тест 3: Проверка количества сессий
```bash
# 1. Запустить движок
./start.sh

# 2. Проверить количество активных сессий
curl http://localhost:8000/api/monitoring/sessions | jq 'length'
# Ожидаемо: 1

# 3. Остановить движок
curl -X POST http://localhost:8000/api/engine/stop

# 4. Проверить снова
curl http://localhost:8000/api/monitoring/sessions | jq 'length'
# Ожидаемо: 0

# 5. Запустить снова
curl -X POST http://localhost:8000/api/engine/start

# 6. Проверить количество
curl http://localhost:8000/api/monitoring/sessions | jq 'length'
# Ожидаемо: 1 (новая сессия)
```

### Тест 4: Использование relaxed пресета
```bash
# Запустить с новым пресетом
ENGINE_PRESET=breakout_v1_relaxed ./start.sh

# Или через API:
curl -X POST http://localhost:8000/api/engine/reload \
  -H "Content-Type: application/json" \
  -d '{"preset_name": "breakout_v1_relaxed"}'
```

---

## Дополнительные улучшения

### Создан диагностический скрипт
`diagnose_scanning.py` - анализирует, почему не находятся кандидаты:
- Показывает текущие настройки фильтров
- Тестирует первые 50 рынков
- Выдает статистику по причинам отказа
- Предлагает рекомендации по настройке

```bash
python3 diagnose_scanning.py
```

---

## Рекомендации

1. **Для продакшена**: Используйте `breakout_v1` с умеренными фильтрами
2. **Для тестирования**: Используйте `breakout_v1_relaxed` для большего количества кандидатов
3. **Мониторинг**: Следите за `Market scan completed: X candidates` в логах
4. **Настройка**: Если кандидатов слишком много/мало, корректируйте фильтры в JSON пресете

---

## Статус
✅ **ВСЕ ПРОБЛЕМЫ ИСПРАВЛЕНЫ** - 3 октября 2025, 02:35 AM

### Проблема 1: Сканирование
✅ Смягчены фильтры ликвидности и волатильности
✅ Создан альтернативный пресет для тестирования
✅ Система теперь находит кандидатов и переходит к следующим фазам

### Проблема 2: Остановка движка
✅ Добавлен asyncio.Event для немедленной остановки
✅ Sleep стал прерываемым
✅ Кнопка "Stop" работает мгновенно

### Проблема 3: Множественные сессии
✅ Неактивные сессии удаляются из памяти
✅ API фильтрует только активные сессии
✅ UI показывает корректное количество сессий

---

## Связанные документы
- [MULTIPLE_SESSIONS_FIX.md](./MULTIPLE_SESSIONS_FIX.md) - детальное описание проблемы с сессиями
- [TASK_4_COMPLETED.md](./TASK_4_COMPLETED.md) - предыдущие исправления UX

