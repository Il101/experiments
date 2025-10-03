#!/usr/bin/env python3
"""
Скрипт для очистки и ротации логов Breakout Bot Trading System.
"""

import argparse
import sys
from pathlib import Path

# Добавить путь к модулям
sys.path.append('.')

from breakout_bot.utils.log_config import cleanup_old_logs, get_log_stats, setup_logging


def main():
    parser = argparse.ArgumentParser(description='Управление логами Breakout Bot')
    parser.add_argument('--cleanup', action='store_true', help='Очистить старые логи')
    parser.add_argument('--stats', action='store_true', help='Показать статистику логов')
    parser.add_argument('--setup', action='store_true', help='Настроить логирование')
    parser.add_argument('--days', type=int, default=7, help='Количество дней для хранения логов')
    parser.add_argument('--log-dir', default='logs', help='Директория с логами')
    
    args = parser.parse_args()
    
    if args.setup:
        print("Настройка логирования...")
        setup_logging(log_dir=args.log_dir)
        print("✅ Логирование настроено")
    
    if args.stats:
        print("Статистика логов:")
        stats = get_log_stats(args.log_dir)
        if "error" in stats:
            print(f"❌ {stats['error']}")
        else:
            print(f"📊 Всего файлов: {stats['total_files']}")
            print(f"📊 Общий размер: {stats['total_size_mb']} MB")
            print("\n📁 Файлы:")
            for filename, info in stats['files'].items():
                print(f"   {filename}: {info['size_mb']} MB")
    
    if args.cleanup:
        print(f"Очистка логов старше {args.days} дней...")
        cleanup_old_logs(args.log_dir, args.days)
        print("✅ Старые логи очищены")
    
    if not any([args.setup, args.stats, args.cleanup]):
        parser.print_help()


if __name__ == "__main__":
    main()
