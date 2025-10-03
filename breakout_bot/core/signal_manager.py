"""
SignalManager - управление торговыми сигналами.

Отвечает исключительно за:
- Генерацию торговых сигналов
- Управление активными сигналами
- Фильтрацию сигналов по критериям
- Мониторинг жизненного цикла сигналов
"""

import asyncio
import logging
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime, timedelta

from ..data.models import Signal, ScanResult, MarketData
from ..signals import SignalGenerator
from ..risk import RiskManager
from ..utils.enhanced_logger import LogContext

logger = logging.getLogger(__name__)


@dataclass
class SignalMetrics:
    """Метрики сигналов для мониторинга."""
    total_generated: int = 0
    active_signals: int = 0
    filtered_out: int = 0
    expired_signals: int = 0
    successful_signals: int = 0
    failed_signals: int = 0
    generation_time_ms: int = 0


class SignalManager:
    """Менеджер для управления торговыми сигналами."""

    def __init__(self,
                 signal_generator: SignalGenerator,
                 risk_manager: RiskManager,
                 enhanced_logger,
                 signal_timeout_minutes: int = 15,
                 max_active_signals: int = 50,
                 trades_aggregator=None,
                 density_detector=None,
                 activity_tracker=None):
        """
        Инициализация SignalManager.
        
        Args:
            signal_generator: Генератор торговых сигналов
            risk_manager: Менеджер рисков
            enhanced_logger: Расширенный логгер
            signal_timeout_minutes: Время жизни сигнала в минутах
            max_active_signals: Максимальное количество активных сигналов
            trades_aggregator: Агрегатор сделок для TPM/TPS (опционально)
            density_detector: Детектор плотности ликвидности (опционально)
            activity_tracker: Трекер активности (опционально)
        """
        self.signal_generator = signal_generator
        self.risk_manager = risk_manager
        self.enhanced_logger = enhanced_logger
        self.signal_timeout_minutes = signal_timeout_minutes
        self.max_active_signals = max_active_signals
        
        # Enhanced microstructure components
        self.trades_aggregator = trades_aggregator
        self.density_detector = density_detector
        self.activity_tracker = activity_tracker
        
        # Активные сигналы
        self.active_signals: List[Signal] = []
        self.signal_market_data: Dict[str, MarketData] = {}
        
        # История сигналов (ограниченная)
        self.signal_history: List[Signal] = []
        self.max_history_size = 1000
        
        # Метрики
        self.metrics = SignalMetrics()
        
        logger.info("SignalManager initialized")

    async def generate_signals_from_scan(self, 
                                       scan_results: List[ScanResult],
                                       session_id: str) -> List[Signal]:
        """
        Сгенерировать торговые сигналы из результатов сканирования.
        
        Args:
            scan_results: Результаты сканирования рынков
            session_id: ID текущей сессии
            
        Returns:
            Список валидных торговых сигналов
        """
        generation_start = time.time()
        
        try:
            context = LogContext(
                component="signal_manager",
                state="SIGNAL_GENERATION",
                session_id=session_id
            )
            
            self.enhanced_logger.debug(
                f"Generating signals from {len(scan_results)} scan results", 
                context
            )
            
            # Очистить устаревшие сигналы
            await self._cleanup_expired_signals()
            
            # Генерировать сигналы
            raw_signals = []
            for scan_result in scan_results:
                # PATCH 004: Propagate correlation_id from scan to signal
                # Note: correlation_id is already in scan_result model, no need to set it again
                correlation_id = getattr(scan_result, 'correlation_id', None)
            
            raw_signals = self.signal_generator.generate_signals(scan_results)
            self.enhanced_logger.debug(f"Generated {len(raw_signals)} raw signals", context)
            
            # Фильтровать сигналы
            filtered_signals = await self._filter_signals(raw_signals)
            self.enhanced_logger.debug(f"Filtered to {len(filtered_signals)} signals", context)
            
            # Привязать market data к сигналам по символу для последующих фаз
            try:
                scan_by_symbol = {sr.symbol: sr for sr in scan_results}
                for signal in filtered_signals:
                    sr = scan_by_symbol.get(signal.symbol)
                    if sr and sr.market_data:
                        self.signal_market_data[signal.symbol] = sr.market_data
            except Exception as e:
                logger.debug(f"Failed to attach market data to signals: {e}")
            
            # Добавить в активные
            for signal in filtered_signals:
                await self._add_active_signal(signal)
            
            # Обновить метрики
            generation_time = int((time.time() - generation_start) * 1000)
            self.metrics.total_generated += len(raw_signals)
            self.metrics.active_signals = len(self.active_signals)
            self.metrics.filtered_out += len(raw_signals) - len(filtered_signals)
            self.metrics.generation_time_ms = generation_time
            
            self.enhanced_logger.info(
                f"Signal generation completed: {len(filtered_signals)} signals added", 
                context
            )
            
            return filtered_signals
            
        except Exception as e:
            logger.error(f"Signal generation failed: {e}")
            raise

    async def _filter_signals(self, signals: List[Signal]) -> List[Signal]:
        """Фильтровать сигналы по различным критериям."""
        filtered = []
        
        for signal in signals:
            try:
                # Проверка дублирования
                if self._is_duplicate_signal(signal):
                    continue
                
                # Проверка лимитов
                if len(self.active_signals) >= self.max_active_signals:
                    logger.warning("Maximum active signals limit reached")
                    break
                
                # Enhanced filters using microstructure data
                if not await self._check_microstructure_filters(signal):
                    continue
                
                filtered.append(signal)
                
            except Exception as e:
                logger.error(f"Error filtering signal {signal.symbol}: {e}")
                continue
        
        return filtered
    
    async def _check_microstructure_filters(self, signal: Signal) -> bool:
        """
        Проверить сигнал против фильтров микроструктуры.
        
        Returns:
            True если сигнал проходит фильтры
        """
        try:
            symbol = signal.symbol
            
            # 1. Check TPM on retest signals
            if signal.strategy == 'retest' and self.trades_aggregator:
                tpm_60s = self.trades_aggregator.get_tpm(symbol, '60s')
                
                # Get historical average (simplified - could use more sophisticated calculation)
                # For now, just check that there IS some activity
                if tpm_60s is not None and tpm_60s == 0:
                    logger.debug(f"Signal {symbol} rejected: no trading activity (TPM=0)")
                    return False
            
            # 2. Check density for momentum signals
            if signal.strategy == 'momentum' and self.density_detector:
                densities = self.density_detector.get_densities(symbol)
                
                # Check if there's a density that's been eaten in the breakout direction
                direction = signal.side  # 'long' or 'short'
                density_side = 'ask' if direction == 'long' else 'bid'
                
                has_eaten_density = any(
                    d.side == density_side and d.eaten_ratio >= 0.75
                    for d in densities
                )
                
                # If no eaten density, reduce confidence or skip
                if not has_eaten_density:
                    logger.debug(f"Signal {symbol} has no eaten density in direction {direction}")
                    # Don't reject, but could lower priority
            
            # 3. Check activity for all signals
            if self.activity_tracker:
                activity = self.activity_tracker.get_metrics(symbol)
                
                if activity and activity.is_dropping:
                    logger.debug(f"Signal {symbol} rejected: activity is dropping")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking microstructure filters for {signal.symbol}: {e}")
            # On error, don't reject the signal
            return True

    def _is_duplicate_signal(self, signal: Signal) -> bool:
        """Проверить, не является ли сигнал дублирующим."""
        for active_signal in self.active_signals:
            if (active_signal.symbol == signal.symbol and 
                active_signal.side == signal.side and
                abs(active_signal.entry - signal.entry) < 0.001):  # Близкие цены входа
                return True
        return False

    async def _add_active_signal(self, signal: Signal):
        """Добавить сигнал в список активных."""
        signal.timestamps['created_at'] = int(time.time() * 1000)
        signal.status = 'active'
        
        self.active_signals.append(signal)
        
        # Сохранить маркет дату если есть
        if hasattr(signal, 'market_data') and signal.market_data:
            self.signal_market_data[signal.symbol] = signal.market_data

    async def _cleanup_expired_signals(self):
        """Удалить устаревшие сигналы."""
        current_time = time.time() * 1000
        timeout_ms = self.signal_timeout_minutes * 60 * 1000
        
        expired_signals = []
        active_signals = []
        
        for signal in self.active_signals:
            created_at = signal.timestamps.get('created_at', current_time)
            if current_time - created_at > timeout_ms:
                expired_signals.append(signal)
            else:
                active_signals.append(signal)
        
        # Переместить устаревшие в историю
        for expired_signal in expired_signals:
            expired_signal.status = 'expired'
            self._add_to_history(expired_signal)
        
        self.active_signals = active_signals
        self.metrics.expired_signals += len(expired_signals)
        
        if expired_signals:
            logger.debug(f"Cleaned up {len(expired_signals)} expired signals")

    def get_active_signals(self) -> List[Signal]:
        """Получить список активных сигналов."""
        return self.active_signals.copy()

    def get_signal_by_symbol(self, symbol: str) -> Optional[Signal]:
        """Найти активный сигнал по символу."""
        for signal in self.active_signals:
            if signal.symbol == symbol:
                return signal
        return None

    async def mark_signal_executed(self, signal: Signal, success: bool = True):
        """Отметить сигнал как исполненный."""
        if signal in self.active_signals:
            self.active_signals.remove(signal)
            
            signal.status = 'executed' if success else 'failed'
            signal.timestamps['executed_at'] = int(time.time() * 1000)
            
            self._add_to_history(signal)
            
            if success:
                self.metrics.successful_signals += 1
            else:
                self.metrics.failed_signals += 1
                
            logger.debug(f"Signal {signal.symbol} marked as {'executed' if success else 'failed'}")

    async def remove_signal(self, signal: Signal, reason: str = "Removed"):
        """Удалить сигнал из активных."""
        if signal in self.active_signals:
            self.active_signals.remove(signal)
            
            signal.status = 'removed'
            signal.meta['removal_reason'] = reason
            
            self._add_to_history(signal)
            logger.debug(f"Signal {signal.symbol} removed: {reason}")

    def _add_to_history(self, signal: Signal):
        """Добавить сигнал в историю с ограничением размера."""
        self.signal_history.append(signal)
        
        # Ограничить размер истории
        if len(self.signal_history) > self.max_history_size:
            self.signal_history = self.signal_history[-self.max_history_size:]

    def get_signal_statistics(self) -> Dict[str, Any]:
        """Получить статистику сигналов."""
        total_processed = (self.metrics.successful_signals + 
                          self.metrics.failed_signals + 
                          self.metrics.expired_signals)
        
        success_rate = 0
        if total_processed > 0:
            success_rate = (self.metrics.successful_signals / total_processed) * 100
        
        return {
            "metrics": self.metrics.__dict__,
            "success_rate_percent": round(success_rate, 2),
            "total_processed": total_processed,
            "history_size": len(self.signal_history)
        }

    def get_recent_signals(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Получить список недавних сигналов."""
        recent = self.signal_history[-limit:] if limit > 0 else self.signal_history
        
        return [
            {
                "symbol": signal.symbol,
                "side": signal.side,
                "entry": signal.entry,
                "sl": signal.sl,
                "tp1": signal.tp1,
                "tp2": signal.tp2,
                "status": signal.status,
                "confidence": signal.confidence,
                "created_at": signal.timestamps.get('created_at'),
                "executed_at": signal.timestamps.get('executed_at'),
                "removal_reason": signal.meta.get('removal_reason')
            }
            for signal in recent
        ]

    def get_signals_by_status(self, status: str) -> List[Signal]:
        """Получить сигналы по статусу."""
        if status == 'active':
            return self.active_signals.copy()
        else:
            return [s for s in self.signal_history if s.status == status]

    def clear_history(self):
        """Очистить историю сигналов (для тестирования)."""
        self.signal_history.clear()
        self.metrics = SignalMetrics()
        logger.info("Signal history cleared")

    def get_status(self) -> Dict[str, Any]:
        """Получить статус SignalManager."""
        return {
            "active_signals_count": len(self.active_signals),
            "max_active_signals": self.max_active_signals,
            "signal_timeout_minutes": self.signal_timeout_minutes,
            "history_size": len(self.signal_history),
            "market_data_cache_size": len(self.signal_market_data),
            "statistics": self.get_signal_statistics()
        }



