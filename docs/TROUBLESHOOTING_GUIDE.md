# 🔧 Breakout Bot Trading System - Руководство по устранению неполадок

## 📋 Содержание
1. [Диагностика проблем](#диагностика-проблем)
2. [Частые проблемы](#частые-проблемы)
3. [Ошибки API](#ошибки-api)
4. [Проблемы с производительностью](#проблемы-с-производительностью)
5. [Проблемы с данными](#проблемы-с-данными)
6. [Проблемы с сетью](#проблемы-с-сетью)
7. [Восстановление системы](#восстановление-системы)

---

## 🔍 Диагностика проблем

### Шаг 1: Проверка статуса системы
```bash
# Общий статус
./status.sh

# Детальная проверка
curl http://localhost:8000/api/health | jq .

# Статус движка
curl http://localhost:8000/api/engine/status | jq .
```

### Шаг 2: Анализ логов
```bash
# API логи
tail -f logs/api.log

# Frontend логи
tail -f logs/frontend.log

# Поиск ошибок
grep -i "error" logs/api.log
grep -i "exception" logs/api.log
grep -i "failed" logs/api.log
```

### Шаг 3: Проверка ресурсов
```bash
# Использование памяти и CPU
curl http://localhost:8000/api/health | jq '.resource_health.metrics'

# Процессы
ps aux | grep breakout_bot
ps aux | grep vite
```

---

## ⚠️ Частые проблемы

### Проблема: Система не запускается
**Симптомы:**
- Ошибки при выполнении `./start.sh`
- Порт 8000 или 5173 занят
- Процессы не запускаются

**Решение:**
```bash
# Проверить занятые порты
lsof -i :8000
lsof -i :5173

# Остановить конфликтующие процессы
pkill -f "breakout_bot"
pkill -f "vite"

# Очистить PID файлы
rm -f pids/api.pid pids/frontend.pid

# Перезапустить
./start.sh
```

### Проблема: API не отвечает
**Симптомы:**
- HTTP 500 ошибки
- Таймауты запросов
- Пустые ответы

**Решение:**
```bash
# Проверить статус API
curl -v http://localhost:8000/api/health

# Перезапустить API
curl -X POST http://localhost:8000/api/engine/stop
sleep 5
curl -X POST http://localhost:8000/api/engine/start \
  -H "Content-Type: application/json" \
  -d '{"preset": "breakout_v1", "mode": "paper"}'
```

### Проблема: Frontend не загружается
**Симптомы:**
- Белая страница
- Ошибки JavaScript
- Нет соединения с API

**Решение:**
```bash
# Проверить статус frontend
curl http://localhost:5173

# Перезапустить frontend
pkill -f "vite"
cd frontend && npm run dev &

# Проверить соединение с API
curl http://localhost:8000/api/health
```

---

## 🚨 Ошибки API

### HTTP 500 - Internal Server Error
**Причина:** Внутренняя ошибка сервера
**Решение:**
```bash
# Проверить логи
tail -f logs/api.log

# Перезапустить API
./stop.sh && ./start.sh

# Проверить конфигурацию
cat breakout_bot/config/settings.py
```

### HTTP 404 - Not Found
**Причина:** Неверный URL или эндпоинт недоступен
**Решение:**
```bash
# Проверить доступные эндпоинты
curl http://localhost:8000/docs

# Проверить правильность URL
curl http://localhost:8000/api/health
```

### HTTP 422 - Validation Error
**Причина:** Неверные параметры запроса
**Решение:**
```bash
# Проверить формат запроса
curl -X POST http://localhost:8000/api/engine/start \
  -H "Content-Type: application/json" \
  -d '{"preset": "breakout_v1", "mode": "paper"}'

# Проверить доступные пресеты
curl http://localhost:8000/api/presets
```

---

## ⚡ Проблемы с производительностью

### Высокое использование CPU
**Симптомы:**
- CPU > 80%
- Медленные ответы API
- Зависание системы

**Решение:**
```bash
# Проверить метрики
curl http://localhost:8000/api/health | jq '.resource_health.metrics.cpu_percent'

# Остановить движок
curl -X POST http://localhost:8000/api/engine/stop

# Перезапустить с оптимизацией
curl -X POST http://localhost:8000/api/engine/start \
  -H "Content-Type: application/json" \
  -d '{"preset": "high_liquidity_top30", "mode": "paper"}'
```

### Высокое использование памяти
**Симптомы:**
- Memory > 85%
- Медленная работа
- Ошибки выделения памяти

**Решение:**
```bash
# Проверить использование памяти
curl http://localhost:8000/api/health | jq '.resource_health.metrics.memory_percent'

# Перезапустить систему
./stop.sh && sleep 10 && ./start.sh

# Проверить утечки памяти
ps aux | grep breakout_bot
```

### Медленные ответы API
**Симптомы:**
- Latency > 100ms
- Таймауты запросов
- Нестабильная работа

**Решение:**
```bash
# Проверить latency
curl http://localhost:8000/api/engine/status | jq '.latencyMs'

# Оптимизировать конфигурацию
# Уменьшить лимиты сканирования
curl -X POST http://localhost:8000/api/scanner/scan \
  -H "Content-Type: application/json" \
  -d '{"preset": "breakout_v1", "limit": 5}'
```

---

## 📊 Проблемы с данными

### Сканер не находит кандидатов
**Симптомы:**
- 0 кандидатов в результатах
- Пустые результаты сканирования
- Ошибки фильтрации

**Решение:**
```bash
# Проверить результаты сканирования
curl http://localhost:8000/api/scanner/last | jq '.candidates | length'

# Запустить новое сканирование
curl -X POST http://localhost:8000/api/scanner/scan \
  -H "Content-Type: application/json" \
  -d '{"preset": "breakout_v1", "limit": 10}'

# Проверить фильтры
curl http://localhost:8000/api/scanner/last | jq '.candidates[0].filters'
```

### Неточные данные рынка
**Симптомы:**
- Устаревшие цены
- Некорректные объемы
- Ошибки в метриках

**Решение:**
```bash
# Проверить соединение с биржей
curl http://localhost:8000/api/health | jq '.engine_initialized'

# Перезапустить движок
curl -X POST http://localhost:8000/api/engine/stop
curl -X POST http://localhost:8000/api/engine/start \
  -H "Content-Type: application/json" \
  -d '{"preset": "breakout_v1", "mode": "paper"}'
```

### Проблемы с позициями
**Симптомы:**
- Некорректные PnL
- Ошибки в расчетах
- Проблемы с закрытием позиций

**Решение:**
```bash
# Проверить позиции
curl http://localhost:8000/api/trading/positions | jq .

# Проверить ордера
curl http://localhost:8000/api/trading/orders | jq .

# Перезапустить движок
curl -X POST http://localhost:8000/api/engine/stop
```

---

## 🌐 Проблемы с сетью

### WebSocket не работает
**Симптомы:**
- Нет real-time обновлений
- Ошибки соединения
- Потеря данных

**Решение:**
```bash
# Проверить WebSocket
curl -N -H "Connection: Upgrade" -H "Upgrade: websocket" \
  -H "Sec-WebSocket-Key: test" -H "Sec-WebSocket-Version: 13" \
  http://localhost:8000/ws

# Перезапустить API
curl -X POST http://localhost:8000/api/engine/stop
curl -X POST http://localhost:8000/api/engine/start \
  -H "Content-Type: application/json" \
  -d '{"preset": "breakout_v1", "mode": "paper"}'
```

### Проблемы с API ключами
**Симптомы:**
- Ошибки аутентификации
- Ограничения API
- Блокировка запросов

**Решение:**
```bash
# Проверить логи на ошибки API
grep -i "api" logs/api.log
grep -i "key" logs/api.log

# Проверить конфигурацию
cat .env

# Перезапустить с новыми ключами
./stop.sh && ./start.sh
```

---

## 🔄 Восстановление системы

### Полное восстановление
```bash
# 1. Остановить все процессы
./stop.sh
pkill -f "breakout_bot"
pkill -f "vite"

# 2. Очистить временные файлы
rm -f pids/*.pid
rm -f logs/*.log

# 3. Перезапустить систему
./start.sh

# 4. Проверить статус
./status.sh
```

### Восстановление из резервной копии
```bash
# 1. Остановить систему
./stop.sh

# 2. Восстановить конфигурацию
cp backup/config/* breakout_bot/config/

# 3. Восстановить данные
cp backup/data/* breakout_bot/data/

# 4. Перезапустить
./start.sh
```

### Аварийное восстановление
```bash
# 1. Принудительная остановка
pkill -9 -f "breakout_bot"
pkill -9 -f "vite"

# 2. Очистка портов
sudo lsof -ti:8000 | xargs kill -9
sudo lsof -ti:5173 | xargs kill -9

# 3. Перезапуск
./start.sh
```

---

## 📞 Эскалация проблем

### Уровень 1: Операционная команда
- Перезапуск системы
- Проверка логов
- Базовое устранение неполадок

### Уровень 2: Команда разработки
- Анализ кода
- Исправление багов
- Обновление конфигурации

### Уровень 3: Архитектор системы
- Критические проблемы
- Изменения архитектуры
- Планирование улучшений

---

## 📚 Дополнительные ресурсы

### Полезные команды
```bash
# Мониторинг в реальном времени
watch -n 1 'curl -s http://localhost:8000/api/health | jq .'

# Анализ логов
tail -f logs/api.log | grep -E "(ERROR|WARN|INFO)"

# Проверка процессов
ps aux | grep -E "(breakout_bot|vite)" | grep -v grep
```

### Конфигурационные файлы
- `breakout_bot/config/settings.py` - Основные настройки
- `breakout_bot/config/presets/` - Торговые пресеты
- `.env` - Переменные окружения
- `requirements.txt` - Зависимости Python

---

*Последнее обновление: $(date)*
*Версия документации: 1.0*
