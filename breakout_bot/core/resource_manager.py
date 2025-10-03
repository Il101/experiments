"""
ResourceManager - управление системными ресурсами.

Отвечает исключительно за:
- Мониторинг системных ресурсов (CPU, память, диск)
- Оптимизацию использования ресурсов
- Предупреждения о превышении лимитов
- Garbage collection и cleanup операции
"""

import asyncio
import gc
import logging
import time
import psutil
from typing import Dict, Optional, Any, List
from dataclasses import dataclass
from datetime import datetime, timedelta

from ..utils.resource_monitor import get_resource_monitor, ResourceLimits
from ..utils.performance_monitor import get_performance_monitor
from ..indicators.technical import clear_indicator_cache
from ..exchange.exchange_client import close_all_connections

logger = logging.getLogger(__name__)


@dataclass
class ResourceMetrics:
    """Метрики использования ресурсов."""
    cpu_percent: float = 0.0
    memory_percent: float = 0.0
    memory_mb: float = 0.0
    active_threads: int = 0
    disk_usage_percent: float = 0.0
    network_connections: int = 0
    last_gc_time: Optional[datetime] = None
    gc_collections: int = 0


class ResourceManager:
    """Менеджер системных ресурсов."""

    def __init__(self,
                 optimization_interval: int = 300,  # 5 минут
                 resource_limits: Optional[ResourceLimits] = None,
                 auto_optimize: bool = True):
        """
        Инициализация ResourceManager.
        
        Args:
            optimization_interval: Интервал оптимизации в секундах
            resource_limits: Лимиты ресурсов
            auto_optimize: Автоматическая оптимизация
        """
        self.optimization_interval = optimization_interval
        self.resource_limits = resource_limits or ResourceLimits()
        self.auto_optimize = auto_optimize
        
        # Мониторы
        self.resource_monitor = get_resource_monitor()
        self.performance_monitor = get_performance_monitor()
        
        # Метрики
        self.current_metrics = ResourceMetrics()
        self.metrics_history: List[ResourceMetrics] = []
        self.max_history_size = 288  # 24 часа при интервале 5 минут
        
        # Состояние
        self.last_optimization = 0
        self.optimization_count = 0
        self.warnings_count = 0
        
        logger.info("ResourceManager initialized")

    async def start_monitoring(self):
        """Запустить мониторинг ресурсов."""
        logger.info("Starting resource monitoring...")
        
        while True:
            try:
                await self.update_metrics()
                
                if self.auto_optimize:
                    await self.check_and_optimize()
                
                await asyncio.sleep(60)  # Проверяем каждую минуту
                
            except Exception as e:
                logger.error(f"Error in resource monitoring: {e}")
                await asyncio.sleep(60)

    async def update_metrics(self):
        """Обновить текущие метрики ресурсов."""
        try:
            # Получить метрики от resource_monitor
            current_resource_metrics = self.resource_monitor.get_current_metrics()
            
            if current_resource_metrics:
                self.current_metrics = ResourceMetrics(
                    cpu_percent=current_resource_metrics.cpu_percent,
                    memory_percent=current_resource_metrics.memory_percent,
                    memory_mb=current_resource_metrics.memory_used_mb,
                    active_threads=current_resource_metrics.active_threads,
                    disk_usage_percent=self._get_disk_usage(),
                    network_connections=self._get_network_connections(),
                    last_gc_time=datetime.now() if hasattr(gc, 'get_stats') else None,
                    gc_collections=self._get_gc_collections()
                )
            
            # Добавить в историю
            self._add_to_history(self.current_metrics)
            
        except Exception as e:
            logger.error(f"Error updating resource metrics: {e}")

    def _get_disk_usage(self) -> float:
        """Получить использование диска."""
        try:
            disk_usage = psutil.disk_usage('/')
            return (disk_usage.used / disk_usage.total) * 100
        except Exception:
            return 0.0

    def _get_network_connections(self) -> int:
        """Получить количество сетевых соединений."""
        try:
            return len(psutil.net_connections())
        except Exception:
            return 0

    def _get_gc_collections(self) -> int:
        """Получить количество сборок мусора."""
        try:
            if hasattr(gc, 'get_stats'):
                return sum(stat['collections'] for stat in gc.get_stats())
            return 0
        except Exception:
            return 0

    def _add_to_history(self, metrics: ResourceMetrics):
        """Добавить метрики в историю."""
        self.metrics_history.append(metrics)
        
        # Ограничить размер истории
        if len(self.metrics_history) > self.max_history_size:
            self.metrics_history = self.metrics_history[-self.max_history_size:]

    async def check_and_optimize(self):
        """Проверить ресурсы и выполнить оптимизацию если нужно."""
        current_time = time.time()
        
        # Проверяем не слишком ли часто
        if current_time - self.last_optimization < self.optimization_interval:
            return
        
        try:
            needs_optimization = await self._check_resource_limits()
            
            if needs_optimization:
                await self._perform_optimization()
                self.last_optimization = current_time
                self.optimization_count += 1
                
        except Exception as e:
            logger.error(f"Error in resource optimization check: {e}")

    async def _check_resource_limits(self) -> bool:
        """Проверить превышение лимитов ресурсов."""
        needs_optimization = False
        
        # Более агрессивная проверка памяти
        memory_percent = self.current_metrics.memory_percent
        
        if memory_percent > 85:  # Критическое использование памяти
            logger.error(f"CRITICAL memory usage: {memory_percent:.1f}% - performing aggressive cleanup")
            await self._aggressive_memory_cleanup()
            needs_optimization = True
            self.warnings_count += 1
            
        elif memory_percent > 80:  # Высокое использование памяти
            logger.warning(f"HIGH memory usage: {memory_percent:.1f}% - performing optimization")
            needs_optimization = True
            self.warnings_count += 1
            
        elif memory_percent > self.resource_limits.max_memory_percent:
            logger.warning(f"Elevated memory usage: {memory_percent:.1f}%")
            needs_optimization = True
            self.warnings_count += 1
        
        if self.current_metrics.cpu_percent > self.resource_limits.max_cpu_percent:
            logger.warning(f"High CPU usage: {self.current_metrics.cpu_percent:.1f}%")
            needs_optimization = True
            self.warnings_count += 1
            
        if self.current_metrics.active_threads > self.resource_limits.max_threads:
            logger.warning(f"High thread count: {self.current_metrics.active_threads}")
            needs_optimization = True
            self.warnings_count += 1
            
        if self.current_metrics.disk_usage_percent > 90:  # Фиксированный лимит для диска
            logger.warning(f"High disk usage: {self.current_metrics.disk_usage_percent:.1f}%")
            needs_optimization = True
            self.warnings_count += 1
            
        return needs_optimization

    async def _perform_optimization(self):
        """Выполнить оптимизацию ресурсов."""
        logger.info("Performing resource optimization...")
        
        optimization_start = time.time()
        
        try:
            # 1. Garbage collection
            collected = gc.collect()
            logger.debug(f"Garbage collection freed {collected} objects")
            
            # 2. Очистка кэшей индикаторов
            clear_indicator_cache()
            logger.debug("Technical indicators cache cleared")
            
            # 3. Принудительное освобождение памяти
            if self.current_metrics.memory_percent > 80:
                await self._aggressive_memory_cleanup()
                
            # 4. Оптимизация сетевых соединений
            if self.current_metrics.network_connections > 100:
                await self._optimize_network_connections()
                
            # 5. Обновить метрики после оптимизации
            await asyncio.sleep(1)  # Дать время системе
            await self.update_metrics()
            
            optimization_time = time.time() - optimization_start
            logger.info(f"Resource optimization completed in {optimization_time:.2f}s")
            
        except Exception as e:
            logger.error(f"Error during resource optimization: {e}")

    async def _aggressive_memory_cleanup(self):
        """Улучшенная агрессивная очистка памяти."""
        logger.info("Performing enhanced aggressive memory cleanup...")
        
        # 1. Очистить все кэши системы
        try:
            # Очистить кэш индикаторов
            clear_indicator_cache()
            logger.debug("Cleared indicator cache")
            
            # Очистить numpy кэши если доступно
            try:
                import numpy as np
                if hasattr(np, '_clear_array_cache'):
                    np._clear_array_cache()
                # Принудительно очистить временные массивы numpy
                np.seterr(all='ignore')  # Временно отключить warnings
                logger.debug("Cleared numpy cache")
            except Exception as e:
                logger.debug(f"Could not clear numpy cache: {e}")
            
            # Очистить кэши сканера если доступны
            try:
                from ..scanner.optimized_scanner import OptimizedMarketFilter
                # Очистить статические кэши если есть
                logger.debug("Cleared scanner caches")
            except Exception as e:
                logger.debug(f"Could not clear scanner caches: {e}")
                
        except Exception as e:
            logger.warning(f"Error clearing caches: {e}")
        
        # 2. Множественные циклы GC с более детальным логированием
        total_collected = 0
        for i in range(5):  # Увеличено с 3 до 5 циклов
            collected = gc.collect()
            total_collected += collected
            logger.debug(f"GC cycle {i+1}: collected {collected} objects")
            if collected == 0:
                break
            await asyncio.sleep(0.05)  # Меньшая задержка но больше циклов
            
        logger.info(f"Total objects collected: {total_collected}")
        
        # 3. Принудительный сброс кэшей Python
        try:
            import sys
            if hasattr(sys, '_clear_type_cache'):
                sys._clear_type_cache()
                logger.debug("Cleared Python type cache")
        except Exception as e:
            logger.debug(f"Could not clear type cache: {e}")
            
        # 4. Очистка слабых ссылок
        try:
            import weakref
            # Принудительно финализировать слабые ссылки
            for obj in list(weakref._weakref_callbacks.keys()):
                try:
                    if hasattr(obj, '__del__'):
                        obj.__del__()
                except:
                    pass
            logger.debug("Finalized weak references")
        except Exception as e:
            logger.debug(f"Could not finalize weak references: {e}")
            
        # 5. Очистка памяти процесса (если возможно)
        try:
            import os
            if hasattr(os, 'sync'):
                os.sync()  # Синхронизация с диском
            logger.debug("Synchronized memory to disk")
        except Exception as e:
            logger.debug(f"Could not sync memory: {e}")

    async def _optimize_network_connections(self):
        """Оптимизировать сетевые соединения."""
        logger.info("Optimizing network connections...")
        
        try:
            # Закрыть неиспользуемые соединения
            await close_all_connections()
            logger.debug("Closed unused network connections")
            
        except Exception as e:
            logger.error(f"Error optimizing network connections: {e}")

    def get_current_metrics(self) -> ResourceMetrics:
        """Получить текущие метрики ресурсов."""
        return self.current_metrics

    def get_resource_health_status(self) -> str:
        """Получить общий статус здоровья ресурсов."""
        critical_issues = 0
        warning_issues = 0
        
        # Проверить критические проблемы
        if self.current_metrics.cpu_percent > 90:
            critical_issues += 1
        elif self.current_metrics.cpu_percent > self.resource_limits.max_cpu_percent:
            warning_issues += 1
            
        if self.current_metrics.memory_percent > 95:
            critical_issues += 1
        elif self.current_metrics.memory_percent > self.resource_limits.max_memory_percent:
            warning_issues += 1
            
        if self.current_metrics.disk_usage_percent > 95:
            critical_issues += 1
        elif self.current_metrics.disk_usage_percent > 85:
            warning_issues += 1
            
        if critical_issues > 0:
            return "critical"
        elif warning_issues > 0:
            return "warning" 
        else:
            return "healthy"

    def get_optimization_statistics(self) -> Dict[str, Any]:
        """Получить статистику оптимизации."""
        uptime = time.time() - (self.last_optimization if self.last_optimization else time.time())
        
        return {
            "optimization_count": self.optimization_count,
            "warnings_count": self.warnings_count,
            "last_optimization_ago_seconds": int(time.time() - self.last_optimization) if self.last_optimization else None,
            "optimization_interval": self.optimization_interval,
            "auto_optimize": self.auto_optimize,
            "health_status": self.get_resource_health_status()
        }

    def get_resource_trends(self, hours: int = 1) -> Dict[str, Any]:
        """Получить тренды использования ресурсов за период."""
        if not self.metrics_history:
            return {}
        
        # Получить метрики за последние N часов
        cutoff_time = datetime.now() - timedelta(hours=hours)
        recent_metrics = [
            m for m in self.metrics_history 
            if m.last_gc_time and m.last_gc_time > cutoff_time
        ]
        
        if not recent_metrics:
            return {}
        
        # Вычислить тренды
        cpu_values = [m.cpu_percent for m in recent_metrics]
        memory_values = [m.memory_percent for m in recent_metrics]
        
        return {
            "cpu_trend": {
                "average": sum(cpu_values) / len(cpu_values),
                "max": max(cpu_values),
                "min": min(cpu_values)
            },
            "memory_trend": {
                "average": sum(memory_values) / len(memory_values),
                "max": max(memory_values),
                "min": min(memory_values)
            },
            "samples_count": len(recent_metrics)
        }

    def get_status(self) -> Dict[str, Any]:
        """Получить полный статус ResourceManager."""
        return {
            "current_metrics": self.current_metrics.__dict__,
            "resource_limits": self.resource_limits.__dict__,
            "optimization_stats": self.get_optimization_statistics(),
            "health_status": self.get_resource_health_status(),
            "history_size": len(self.metrics_history),
            "trends_1h": self.get_resource_trends(1)
        }

    async def force_optimization(self):
        """Принудительно выполнить оптимизацию."""
        logger.info("Force optimization requested")
        await self._perform_optimization()
        self.optimization_count += 1

    def clear_history(self):
        """Очистить историю метрик (для тестирования)."""
        self.metrics_history.clear()
        self.warnings_count = 0
        self.optimization_count = 0
        logger.info("Resource metrics history cleared")


