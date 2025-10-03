"""
Конфигурация логирования с ротацией для Breakout Bot Trading System.
"""

import logging
import logging.handlers
import os
from pathlib import Path
from typing import Optional


def setup_logging(
    log_level: str = "INFO",
    log_dir: str = "logs",
    max_file_size: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5,
    enable_console: bool = True
) -> None:
    """
    Настроить логирование с ротацией файлов.
    
    Args:
        log_level: Уровень логирования (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_dir: Директория для логов
        max_file_size: Максимальный размер файла в байтах
        backup_count: Количество резервных файлов
        enable_console: Включить вывод в консоль
    """
    # Создать директорию для логов
    log_path = Path(log_dir)
    log_path.mkdir(exist_ok=True)
    
    # Настроить формат логов
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Настроить корневой логгер
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))
    
    # Очистить существующие обработчики
    root_logger.handlers.clear()
    
    # API логи с ротацией
    api_handler = logging.handlers.RotatingFileHandler(
        filename=log_path / "api.log",
        maxBytes=max_file_size,
        backupCount=backup_count,
        encoding='utf-8'
    )
    api_handler.setLevel(logging.INFO)
    api_handler.setFormatter(formatter)
    api_handler.addFilter(lambda record: 'api' in record.name.lower() or 'breakout_bot' in record.name.lower())
    root_logger.addHandler(api_handler)
    
    # Метрики с ротацией
    metrics_handler = logging.handlers.RotatingFileHandler(
        filename=log_path / "metrics.log",
        maxBytes=max_file_size,
        backupCount=backup_count,
        encoding='utf-8'
    )
    metrics_handler.setLevel(logging.DEBUG)
    metrics_handler.setFormatter(formatter)
    metrics_handler.addFilter(lambda record: 'metrics' in record.name.lower() or 'monitor' in record.name.lower())
    root_logger.addHandler(metrics_handler)
    
    # Ошибки с ротацией
    error_handler = logging.handlers.RotatingFileHandler(
        filename=log_path / "errors.log",
        maxBytes=max_file_size,
        backupCount=backup_count,
        encoding='utf-8'
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)
    root_logger.addHandler(error_handler)
    
    # Общие логи с ротацией
    general_handler = logging.handlers.RotatingFileHandler(
        filename=log_path / "general.log",
        maxBytes=max_file_size,
        backupCount=backup_count,
        encoding='utf-8'
    )
    general_handler.setLevel(logging.INFO)
    general_handler.setFormatter(formatter)
    root_logger.addHandler(general_handler)
    
    # Консольный вывод (опционально)
    if enable_console:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.WARNING)  # Только предупреждения и ошибки в консоль
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)
    
    # Настроить логирование для внешних библиотек
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    
    # Логирование успешной настройки
    logger = logging.getLogger(__name__)
    logger.info(f"Logging configured: level={log_level}, dir={log_dir}, max_size={max_file_size}B, backups={backup_count}")


def cleanup_old_logs(log_dir: str = "logs", days_to_keep: int = 7) -> None:
    """
    Очистить старые логи.
    
    Args:
        log_dir: Директория с логами
        days_to_keep: Количество дней для хранения логов
    """
    import time
    from pathlib import Path
    
    log_path = Path(log_dir)
    if not log_path.exists():
        return
    
    cutoff_time = time.time() - (days_to_keep * 24 * 60 * 60)
    
    for log_file in log_path.glob("*.log*"):
        if log_file.stat().st_mtime < cutoff_time:
            try:
                log_file.unlink()
                logging.getLogger(__name__).info(f"Deleted old log file: {log_file}")
            except Exception as e:
                logging.getLogger(__name__).error(f"Failed to delete {log_file}: {e}")


def get_log_stats(log_dir: str = "logs") -> dict:
    """
    Получить статистику логов.
    
    Args:
        log_dir: Директория с логами
        
    Returns:
        Словарь со статистикой логов
    """
    from pathlib import Path
    
    log_path = Path(log_dir)
    if not log_path.exists():
        return {"error": "Log directory does not exist"}
    
    stats = {
        "total_files": 0,
        "total_size_mb": 0,
        "files": {}
    }
    
    for log_file in log_path.glob("*.log*"):
        stats["total_files"] += 1
        file_size = log_file.stat().st_size
        stats["total_size_mb"] += file_size / (1024 * 1024)
        stats["files"][log_file.name] = {
            "size_mb": round(file_size / (1024 * 1024), 2),
            "modified": log_file.stat().st_mtime
        }
    
    stats["total_size_mb"] = round(stats["total_size_mb"], 2)
    return stats


def setup_optimized_logging() -> None:
    """Настроить оптимизированное логирование для продакшена."""
    setup_logging(
        log_level="INFO",
        log_dir="logs",
        max_file_size=5 * 1024 * 1024,  # 5MB
        backup_count=3,
        enable_console=False  # Отключить консоль в продакшене
    )


def setup_development_logging() -> None:
    """Настроить логирование для разработки."""
    setup_logging(
        log_level="DEBUG",
        log_dir="logs",
        max_file_size=10 * 1024 * 1024,  # 10MB
        backup_count=5,
        enable_console=True  # Включить консоль для разработки
    )
