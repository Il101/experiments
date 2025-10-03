#!/bin/bash
# Скрипт для полной очистки и перезапуска бота

echo "🔄 Очистка и перезапуск Breakout Bot..."

# 1. Остановить бот
echo "1️⃣  Останавливаем бот..."
./stop.sh

# 2. Подождать немного
sleep 2

# 3. Очистить старые сессии через API (если сервер еще запущен)
echo "2️⃣  Очистка старых сессий..."
curl -X POST http://localhost:8000/api/monitoring/sessions/cleanup 2>/dev/null || echo "   (Сервер уже остановлен)"

# 4. Принудительно убить все процессы Python, связанные с ботом
echo "3️⃣  Принудительная остановка процессов..."
ps aux | grep -E "python.*breakout|python.*uvicorn" | grep -v grep | awk '{print $2}' | xargs kill -9 2>/dev/null
echo "   ✅ Процессы остановлены"

# 5. Очистить PID файлы
echo "4️⃣  Очистка PID файлов..."
rm -f pids/*.pid 2>/dev/null
echo "   ✅ PID файлы очищены"

# 6. Подождать перед запуском
sleep 1

# 7. Запустить бот
echo "5️⃣  Запуск бота..."
./start.sh

# 8. Подождать загрузки
echo "6️⃣  Ожидание загрузки (5 сек)..."
sleep 5

# 9. Проверить количество активных сессий
echo "7️⃣  Проверка активных сессий..."
SESSIONS=$(curl -s http://localhost:8000/api/monitoring/sessions | jq 'length' 2>/dev/null || echo "?")
echo "   📊 Активных сессий: $SESSIONS"

if [ "$SESSIONS" = "1" ]; then
    echo "   ✅ Отлично! Только одна активная сессия"
elif [ "$SESSIONS" = "0" ]; then
    echo "   ⚠️  Нет активных сессий (движок не запущен?)"
else
    echo "   ⚠️  Обнаружено $SESSIONS сессий (ожидалось 1)"
fi

echo ""
echo "🎉 Готово!"
echo "   UI: http://localhost:3000"
echo "   API: http://localhost:8000"
