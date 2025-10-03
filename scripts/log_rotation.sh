#!/bin/bash
# Скрипт для автоматической ротации логов Breakout Bot Trading System

# Настройки
LOG_DIR="/Users/iliazarikov/Documents/Python_crypto/Barahlo/experiments/logs"
PROJECT_DIR="/Users/iliazarikov/Documents/Python_crypto/Barahlo/experiments"
DAYS_TO_KEEP=7
MAX_SIZE_MB=50

# Перейти в директорию проекта
cd "$PROJECT_DIR"

# Проверить размер логов
TOTAL_SIZE=$(du -sm "$LOG_DIR" | cut -f1)

echo "📊 Текущий размер логов: ${TOTAL_SIZE}MB"

# Если размер превышает лимит, очистить старые логи
if [ "$TOTAL_SIZE" -gt "$MAX_SIZE_MB" ]; then
    echo "⚠️  Размер логов превышает ${MAX_SIZE_MB}MB, очищаем старые логи..."
    
    # Очистить старые логи
    python3 cleanup_logs.py --cleanup --days "$DAYS_TO_KEEP" --log-dir "$LOG_DIR"
    
    # Проверить размер после очистки
    NEW_SIZE=$(du -sm "$LOG_DIR" | cut -f1)
    echo "✅ Размер после очистки: ${NEW_SIZE}MB"
else
    echo "✅ Размер логов в норме"
fi

# Показать статистику
echo "📈 Статистика логов:"
python3 cleanup_logs.py --stats --log-dir "$LOG_DIR"
