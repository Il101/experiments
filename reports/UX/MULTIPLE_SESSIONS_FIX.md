# Исправление проблемы множественных активных сессий - 3 октября 2025

## Проблема
При остановке движка в UI продолжали отображаться **множественные активные сессии**, даже после нажатия кнопки "Stop Engine".

На скриншоте видно:
- Сессия `d84c7e3f...` - ACTIVE
- Сессия `b4ca34b6...` - ACTIVE

Обе сессии показаны как активные, хотя первая должна была быть остановлена.

---

## Корневая причина

### 1. Сессии не удалялись из памяти
При остановке движка метод `end_all_sessions()` помечал сессии как `is_active = False`, но **НЕ удалял их из словаря** `active_sessions`:

```python
# ❌ СТАРЫЙ КОД
def end_all_sessions(self, reason: str = "Engine stopped"):
    for session_id in sessions_to_end:
        self.end_session(session_id, "stopped")
        # session остается в active_sessions!
```

### 2. API возвращал ВСЕ сессии
Endpoint `/api/monitoring/sessions` возвращал все сессии из словаря, включая неактивные:

```python
# ❌ СТАРЫЙ КОД
for session_id, session in monitoring_manager.active_sessions.items():
    sessions.append(session_data)  # Включая is_active=False!
```

### 3. Frontend показывал все полученные сессии
Frontend получал список со старыми сессиями и отображал их как активные.

---

## Решение

### Изменение 1: Немедленная очистка неактивных сессий
**Файл:** `breakout_bot/utils/monitoring_manager.py`

```python
def end_all_sessions(self, reason: str = "Engine stopped", cleanup: bool = True):
    """End all active sessions.
    
    Args:
        reason: Reason for ending sessions
        cleanup: If True, immediately remove inactive sessions from memory
    """
    sessions_to_end = list(self.active_sessions.keys())
    
    for session_id in sessions_to_end:
        self.end_session(session_id, "stopped")
        logger.info(f"Ended session {session_id} due to: {reason}")
    
    # Clear current session
    self.current_session_id = None
    
    # ✅ НОВОЕ: Немедленная очистка неактивных сессий
    if cleanup:
        inactive_sessions = [sid for sid, s in self.active_sessions.items() if not s.is_active]
        for session_id in inactive_sessions:
            del self.active_sessions[session_id]
            if session_id in self.session_checkpoints:
                del self.session_checkpoints[session_id]
        logger.info(f"Cleaned up {len(inactive_sessions)} inactive sessions")
    
    logger.info(f"Ended {len(sessions_to_end)} active sessions")
```

### Изменение 2: Вызов очистки при остановке движка
**Файл:** `breakout_bot/api/routers/engine.py`

```python
# ✅ IMPROVED: End all monitoring sessions with immediate cleanup
try:
    monitoring_manager = get_monitoring_manager()
    monitoring_manager.end_all_sessions("Engine stopped by user request", cleanup=True)
    logger.info("Ended and cleaned up all monitoring sessions")
except Exception as e:
    logger.warning(f"Failed to end monitoring sessions: {e}")
```

### Изменение 3: Фильтрация активных сессий в API
**Файл:** `breakout_bot/api/routers/monitoring.py`

```python
@router.get("/sessions", response_model=List[Dict[str, Any]])
async def get_active_sessions():
    """Get all active trading sessions."""
    try:
        monitoring_manager = get_monitoring_manager()
        
        sessions = []
        # ✅ FIX: Фильтруем только активные сессии
        for session_id, session in monitoring_manager.active_sessions.items():
            # Пропускаем неактивные сессии
            if not session.is_active:
                continue
                
            session_data = {
                "session_id": session_id,
                "preset": session.preset,
                ...
            }
            sessions.append(session_data)
        
        return sessions
```

---

## Результат

После этих исправлений:

1. ✅ При нажатии "Stop Engine" все сессии **немедленно удаляются из памяти**
2. ✅ API `/api/monitoring/sessions` возвращает **только активные сессии**
3. ✅ Frontend показывает **только одну активную сессию** после запуска
4. ✅ Старые сессии не мешают новым

---

## Как протестировать

### Шаг 1: Запустить движок
```bash
./start.sh
```

### Шаг 2: Проверить количество сессий
Открыть UI (http://localhost:3000) → вкладка "Analytics" → "Session Selection"

**Ожидаемо:** Должна быть видна **ТОЛЬКО ОДНА активная сессия**

### Шаг 3: Остановить движок
Нажать кнопку "Stop Engine" в UI

### Шаг 4: Проверить очистку
```bash
# Проверить API
curl http://localhost:8000/api/monitoring/sessions

# Ожидаемо: пустой массив []
```

### Шаг 5: Запустить снова
Нажать "Start Engine"

**Ожидаемо:** Снова видна **ТОЛЬКО ОДНА новая активная сессия**

---

## Дополнительные улучшения

### Автоматическая очистка старых сессий
Уже существует метод `cleanup_old_sessions()`, который удаляет сессии старше 1 часа:

```python
def cleanup_old_sessions(self):
    """Clean up old completed sessions."""
    now = datetime.now()
    sessions_to_remove = []
    
    for session_id, session in self.active_sessions.items():
        if not session.is_active and session.end_time:
            # Remove sessions older than 1 hour
            if (now - session.end_time).total_seconds() > 3600:
                sessions_to_remove.append(session_id)
    
    for session_id in sessions_to_remove:
        del self.active_sessions[session_id]
        if session_id in self.session_checkpoints:
            del self.session_checkpoints[session_id]
```

Можно вызывать его периодически для предотвращения утечек памяти.

---

## Файлы изменены

1. **breakout_bot/utils/monitoring_manager.py** - добавлена немедленная очистка
2. **breakout_bot/api/routers/engine.py** - вызов очистки при остановке
3. **breakout_bot/api/routers/monitoring.py** - фильтрация только активных сессий

---

## Статус
✅ **ИСПРАВЛЕНО** - 3 октября 2025, 02:35 AM
- Множественные активные сессии больше не появляются
- При остановке движка сессии удаляются немедленно
- API возвращает только действительно активные сессии
