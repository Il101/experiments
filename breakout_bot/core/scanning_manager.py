"""
ScanningManager - управление сканированием рынков.

Отвечает исключительно за:
- Получение рыночных данных
- Координацию со сканером брейкаутов
- Кэширование рыночных данных
- Мониторинг процесса сканирования
"""

import asyncio
import logging
import time
import os
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from ..data.models import MarketData, ScanResult
from ..scanner import BreakoutScanner
from ..exchange import MarketDataProvider
from ..utils.enhanced_logger import LogContext
from ..data.monitoring import CheckpointType, CheckpointStatus

logger = logging.getLogger(__name__)


@dataclass
class ScanningMetrics:
    """Метрики сканирования для мониторинга."""
    total_symbols: int = 0
    scanned_symbols: int = 0
    scan_duration_ms: int = 0
    candidates_found: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    errors_count: int = 0


class ScanningManager:
    """Менеджер для координации сканирования рынков."""

    def __init__(self,
                 scanner: BreakoutScanner,
                 market_data_provider: MarketDataProvider,
                 monitoring_manager,
                 enhanced_logger,
                 max_cache_size: int = 1000,
                 symbols_whitelist: Optional[List[str]] = None,
                 trades_aggregator=None,
                 orderbook_manager=None):
        """
        Инициализация ScanningManager.
        
        Args:
            scanner: Сканер брейкаутов  
            market_data_provider: Провайдер рыночных данных
            monitoring_manager: Менеджер мониторинга
            enhanced_logger: Расширенный логгер
            max_cache_size: Максимальный размер кэша
            symbols_whitelist: Белый список символов для сканирования
            trades_aggregator: Агрегатор сделок (опционально)
            orderbook_manager: Менеджер стакана (опционально)
        """
        self.scanner = scanner
        self.market_data_provider = market_data_provider
        self.monitoring_manager = monitoring_manager
        self.enhanced_logger = enhanced_logger
        self.max_cache_size = max_cache_size
        self.symbols_whitelist = symbols_whitelist
        
        # Enhanced components for WebSocket subscriptions
        self.trades_aggregator = trades_aggregator
        self.orderbook_manager = orderbook_manager
        
        # Кэш рыночных данных
        self.market_data_cache: Dict[str, MarketData] = {}
        
        # Сохранение результатов последнего сканирования для оркестратора
        self.last_scan_results: List[ScanResult] = []
        
        # Метрики сканирования
        self.metrics = ScanningMetrics()
        self.last_scan_time = 0
        
        logger.info("ScanningManager initialized")

    async def scan_markets(self, 
                          exchange_client,
                          session_id: str) -> List[ScanResult]:
        """
        Выполнить полное сканирование рынков.
        
        Args:
            exchange_client: Клиент биржи для получения списка символов
            session_id: ID текущей сессии для мониторинга
            
        Returns:
            Список результатов сканирования
        """
        scan_start_time = time.time()
        
        try:
            # Логирование начала сканирования
            context = LogContext(
                component="scanning",
                state="SCANNING",
                session_id=session_id
            )
            self.enhanced_logger.info("Starting market scan...", context)
            
            # Checkpoint начала сканирования
            self.monitoring_manager.add_checkpoint(
                CheckpointType.SCAN_START,
                "Starting market scan",
                CheckpointStatus.IN_PROGRESS,
                session_id
            )
            
            # Получить список символов
            all_symbols = await exchange_client.fetch_markets()
            symbols_to_scan = self._filter_symbols(all_symbols)
            
            # Получить рыночные данные с оптимизацией
            market_data = await self._fetch_market_data_optimized(symbols_to_scan, exchange_client)
            
            # Checkpoint получения данных
            self.monitoring_manager.add_checkpoint(
                CheckpointType.SCAN_START,
                f"Fetched data for {len(symbols_to_scan)} markets",
                CheckpointStatus.COMPLETED,
                session_id,
                metrics={
                    "markets_count": len(symbols_to_scan), 
                    "data_points": len(market_data)
                }
            )
            
            # Выполнить сканирование
            scan_results = await self._execute_scan(market_data)
            
            # Обновить метрики
            scan_duration = int((time.time() - scan_start_time) * 1000)
            self.metrics = ScanningMetrics(
                total_symbols=len(all_symbols),
                scanned_symbols=len(symbols_to_scan),
                scan_duration_ms=scan_duration,
                candidates_found=len(scan_results),
                cache_hits=self._get_cache_hits(),
                cache_misses=self._get_cache_misses(),
                errors_count=0
            )
            
            # Checkpoint завершения сканирования
            self.monitoring_manager.add_checkpoint(
                CheckpointType.SCAN_COMPLETE,
                f"Scan completed, found {len(scan_results)} candidates",
                CheckpointStatus.COMPLETED,
                session_id,
                metrics=self.metrics.__dict__
            )
            
            self.enhanced_logger.info(
                f"Market scan completed: {len(scan_results)} candidates found", 
                context
            )
            
            # Subscribe found candidates to WebSocket streams
            await self._subscribe_candidates_to_streams(scan_results)
            
            self.last_scan_time = time.time()
            # Сохраняем результаты для последующих фаз (уровни/сигналы)
            self.last_scan_results = scan_results
            return scan_results
            
        except Exception as e:
            # Обновить метрики ошибок
            self.metrics.errors_count += 1
            
            # Checkpoint ошибки
            self.monitoring_manager.add_checkpoint(
                CheckpointType.SCAN_START,
                f"Scan failed: {str(e)}",
                CheckpointStatus.FAILED,
                session_id
            )
            
            logger.error(f"Market scanning failed: {e}")
            raise

    def _filter_symbols(self, all_symbols: List[str]) -> List[str]:
        """Отфильтровать символы для сканирования."""
        symbols = all_symbols
        
        # Применить whitelist если есть
        if self.symbols_whitelist:
            symbols = [s for s in symbols if s in self.symbols_whitelist]
            
        # Применить лимит из environment
        fetch_limit = int(os.getenv('ENGINE_MARKET_FETCH_LIMIT', '0'))
        if fetch_limit > 0:
            symbols = symbols[:fetch_limit]
            
        logger.debug(f"Filtered {len(all_symbols)} symbols to {len(symbols)} for scanning")
        return symbols

    async def _fetch_market_data(self, symbols: List[str]) -> Dict[str, MarketData]:
        """Получить рыночные данные с кэшированием."""
        # Получить свежие данные через провайдер
        market_data = await self.market_data_provider.get_multiple_market_data(symbols)
        
        # Обновить кэш с контролем размера
        for symbol, data in market_data.items():
            self._update_cache(symbol, data)
            
        return market_data

    def _update_cache(self, symbol: str, data: MarketData):
        """Обновить кэш рыночных данных с контролем размера."""
        self.market_data_cache[symbol] = data
        
        # Контроль размера кэша
        if len(self.market_data_cache) > self.max_cache_size:
            # Удалить самый старый элемент
            oldest_key = next(iter(self.market_data_cache))
            if oldest_key in self.market_data_cache:
                self.market_data_cache.pop(oldest_key)

    async def _execute_scan(self, market_data: Dict[str, MarketData]) -> List[ScanResult]:
        """Выполнить сканирование с помощью BreakoutScanner."""
        # Получить BTC данные для корреляции
        btc_data = (market_data.get('BTC/USDT') or 
                   market_data.get('BTC/USDT:USDT') or 
                   market_data.get('BTCUSDT'))
        
        # Выполнить сканирование
        scan_results = await self.scanner.scan_markets(
            list(market_data.values()),
            btc_data
        )
        
        logger.debug(f"Scanner found {len(scan_results)} candidates")
        return scan_results

    def get_cached_data(self, symbol: str) -> Optional[MarketData]:
        """Получить данные из кэша."""
        return self.market_data_cache.get(symbol)

    def get_scanning_metrics(self) -> ScanningMetrics:
        """Получить метрики сканирования."""
        return self.metrics

    def _get_cache_hits(self) -> int:
        """Получить количество попаданий в кэш (заглушка)."""
        return 0  # TODO: Implement cache hit tracking

    def _get_cache_misses(self) -> int:
        """Получить количество промахов кэша (заглушка)."""
        return 0  # TODO: Implement cache miss tracking

    def get_status(self) -> Dict[str, Any]:
        """Получить статус ScanningManager."""
        return {
            "cache_size": len(self.market_data_cache),
            "max_cache_size": self.max_cache_size,
            "last_scan_time": self.last_scan_time,
            "whitelist_size": len(self.symbols_whitelist) if self.symbols_whitelist else 0,
            "last_scan_candidates": len(self.last_scan_results),
            "metrics": self.metrics.__dict__
        }

    def clear_cache(self):
        """Очистить кэш рыночных данных."""
        self.market_data_cache.clear()
        logger.info("Market data cache cleared")

    def update_whitelist(self, new_whitelist: Optional[List[str]]):
        """Обновить whitelist символов."""
        self.symbols_whitelist = new_whitelist
        if new_whitelist:
            logger.info(f"Updated symbols whitelist: {len(new_whitelist)} symbols")
        else:
            logger.info("Symbols whitelist cleared - scanning all symbols")

    async def _fetch_market_data_optimized(self, symbols: List[str], exchange_client) -> Dict[str, MarketData]:
        """Получение полных рыночных данных через MarketDataProvider вместо упрощенной версии."""
        logger.info(f"Fetching comprehensive market data for {len(symbols)} symbols")
        
        # Используем полноценный MarketDataProvider для получения всех данных
        # вместо упрощенной версии с обнуленными метриками
        # Add timeout to prevent hanging - увеличен до 120 секунд
        timeout_seconds = int(os.getenv('MARKET_DATA_TIMEOUT', '120'))
        try:
            market_data = await asyncio.wait_for(
                self.market_data_provider.get_multiple_market_data(symbols),
                timeout=float(timeout_seconds)
            )
        except asyncio.TimeoutError:
            logger.warning(f"Market data fetch timeout after {timeout_seconds}s - got partial results")
            market_data = {}
        
        # Обновить кэш с контролем размера
        for symbol, data in market_data.items():
            self._update_cache(symbol, data)
            
        logger.info(f"Comprehensive data fetch completed: {len(market_data)} symbols")
        return market_data
    
    # Удалил _fetch_single_market_data так как он создавал данные с обнуленными полями
    # Теперь используем только полноценный MarketDataProvider
    
    async def _subscribe_candidates_to_streams(self, scan_results: List[ScanResult]):
        """
        Подписать найденные кандидаты на WebSocket потоки.
        
        Args:
            scan_results: Результаты сканирования с кандидатами
        """
        if not self.trades_aggregator and not self.orderbook_manager:
            # If no WebSocket components available, skip
            return
        
        try:
            # Subscribe top candidates to streams
            top_candidates = sorted(scan_results, key=lambda x: x.score, reverse=True)[:20]
            
            for result in top_candidates:
                try:
                    if self.trades_aggregator:
                        await self.trades_aggregator.subscribe(result.symbol)
                    
                    if self.orderbook_manager:
                        await self.orderbook_manager.subscribe(result.symbol)
                    
                    logger.debug(f"Subscribed {result.symbol} to WebSocket streams")
                
                except Exception as e:
                    logger.warning(f"Failed to subscribe {result.symbol} to streams: {e}")
            
            logger.info(f"Subscribed {len(top_candidates)} candidates to WebSocket streams")
        
        except Exception as e:
            logger.error(f"Error subscribing candidates to streams: {e}")



