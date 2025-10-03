#!/usr/bin/env python3
"""
Диагностический скрипт для анализа проблем с торговой системой.
Анализирует почему система не генерирует сигналы.
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any
import sys
import os

# Добавляем путь к модулю
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from breakout_bot.config.settings import load_preset
from breakout_bot.exchange.exchange_client import ExchangeClient
from breakout_bot.scanner.market_scanner import BreakoutScanner
from breakout_bot.data.models import MarketData
from breakout_bot.diagnostics import DiagnosticsCollector

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TradingDiagnostics:
    """Диагностика торговой системы."""
    
    def __init__(self):
        self.diagnostics = DiagnosticsCollector(enabled=True)
        
    async def analyze_preset_filters(self, preset_name: str = "breakout_v1"):
        """Анализирует фильтры пресета."""
        print(f"\n🔍 Анализ пресета: {preset_name}")
        print("=" * 50)
        
        try:
            preset = load_preset(preset_name)
            print(f"📋 Описание: {preset.description}")
            print(f"🎯 Целевые рынки: {preset.target_markets}")
            print(f"⚡ Приоритет стратегии: {preset.strategy_priority}")
            
            print(f"\n💰 Настройки риска:")
            print(f"  - Риск на сделку: {preset.risk.risk_per_trade:.1%}")
            print(f"  - Макс. позиций: {preset.risk.max_concurrent_positions}")
            print(f"  - Дневной лимит: {preset.risk.daily_risk_limit:.1%}")
            
            print(f"\n💧 Фильтры ликвидности:")
            print(f"  - Мин. объем 24ч: ${preset.liquidity_filters.min_24h_volume_usd:,}")
            print(f"  - Мин. OI: ${preset.liquidity_filters.min_oi_usd:,}")
            print(f"  - Макс. спред: {preset.liquidity_filters.max_spread_bps} bps")
            print(f"  - Мин. глубина 0.5%: ${preset.liquidity_filters.min_depth_usd_0_5pct:,}")
            print(f"  - Мин. глубина 0.3%: ${preset.liquidity_filters.min_depth_usd_0_3pct:,}")
            print(f"  - Мин. сделок/мин: {preset.liquidity_filters.min_trades_per_minute}")
            
            print(f"\n📊 Фильтры волатильности:")
            print(f"  - ATR диапазон: {preset.volatility_filters.atr_range_min:.3f} - {preset.volatility_filters.atr_range_max:.3f}")
            print(f"  - BB ширина макс: {preset.volatility_filters.bb_width_percentile_max}%")
            print(f"  - Всплеск объема 1ч: {preset.volatility_filters.volume_surge_1h_min}x")
            print(f"  - Всплеск объема 5м: {preset.volatility_filters.volume_surge_5m_min}x")
            print(f"  - OI дельта: {preset.volatility_filters.oi_delta_threshold:.3f}")
            
            print(f"\n🎯 Настройки сканера:")
            print(f"  - Макс. кандидатов: {preset.scanner_config.max_candidates}")
            print(f"  - Интервал сканирования: {preset.scanner_config.scan_interval_seconds}с")
            print(f"  - Топ по объему: {preset.scanner_config.top_n_by_volume}")
            
            return preset
            
        except Exception as e:
            print(f"❌ Ошибка загрузки пресета: {e}")
            return None
    
    async def test_market_data(self, preset_name: str = "breakout_v1"):
        """Тестирует получение рыночных данных."""
        print(f"\n📈 Тестирование рыночных данных")
        print("=" * 50)
        
        try:
            # Создаем клиент биржи
            exchange_client = ExchangeClient()
            
            # Получаем список рынков
            markets = await exchange_client.fetch_markets()
            print(f"✅ Найдено {len(markets)} активных рынков")
            
            # Фильтруем только USDT-M фьючерсы
            usdt_markets = [m for m in markets if m['type'] == 'future' and m['quote'] == 'USDT']
            print(f"📊 USDT-M фьючерсы: {len(usdt_markets)}")
            
            # Берем топ-10 по объему для анализа
            top_markets = usdt_markets[:10]
            
            print(f"\n🔍 Анализ топ-10 рынков:")
            for i, market in enumerate(top_markets, 1):
                symbol = market['symbol']
                print(f"  {i}. {symbol}")
                
                try:
                    # Получаем данные рынка
                    market_data = await exchange_client.fetch_market_data(symbol)
                    
                    if market_data:
                        print(f"     💰 Цена: ${market_data.price:,.2f}")
                        print(f"     📊 Объем 24ч: ${market_data.volume_24h_usd:,.0f}")
                        print(f"     🔄 OI: ${market_data.oi_usd:,.0f}" if market_data.oi_usd else "     🔄 OI: N/A")
                        print(f"     📏 Спред: {market_data.l2_depth.spread_bps:.1f} bps")
                        print(f"     📈 ATR 15м: {market_data.atr_15m:.4f}")
                        print(f"     📊 BB ширина: {market_data.bb_width_pct:.1f}%")
                        print(f"     🔗 Корреляция BTC: {market_data.btc_correlation:.2f}")
                        print()
                    
                except Exception as e:
                    print(f"     ❌ Ошибка получения данных: {e}")
                    print()
            
            return True
            
        except Exception as e:
            print(f"❌ Ошибка тестирования данных: {e}")
            return False
    
    async def test_scanner_filters(self, preset_name: str = "breakout_v1"):
        """Тестирует работу фильтров сканера."""
        print(f"\n🔍 Тестирование фильтров сканера")
        print("=" * 50)
        
        try:
            preset = load_preset(preset_name)
            scanner = BreakoutScanner(preset, self.diagnostics)
            exchange_client = ExchangeClient()
            
            # Получаем данные для тестирования
            markets = await exchange_client.fetch_markets()
            usdt_markets = [m for m in markets if m['type'] == 'future' and m['quote'] == 'USDT']
            
            # Берем топ-20 для анализа
            test_markets = usdt_markets[:20]
            print(f"🧪 Тестируем {len(test_markets)} рынков...")
            
            passed_count = 0
            failed_filters = {}
            
            for market in test_markets:
                symbol = market['symbol']
                try:
                    market_data = await exchange_client.fetch_market_data(symbol)
                    if not market_data:
                        continue
                    
                    # Применяем фильтры
                    scan_result = await scanner._scan_single_market(market_data)
                    
                    if scan_result and scan_result.passed_all_filters:
                        passed_count += 1
                        print(f"✅ {symbol}: ПРОШЕЛ все фильтры (оценка: {scan_result.score:.2f})")
                    else:
                        # Анализируем какие фильтры не прошли
                        if scan_result:
                            failed = []
                            for filter_name, result in scan_result.filter_results.items():
                                if not result.passed:
                                    failed.append(f"{filter_name}: {result.reason}")
                            
                            if failed:
                                failed_filters[symbol] = failed
                                print(f"❌ {symbol}: НЕ ПРОШЕЛ - {', '.join(failed[:3])}")
                        else:
                            print(f"❌ {symbol}: Нет данных")
                    
                except Exception as e:
                    print(f"❌ {symbol}: Ошибка - {e}")
            
            print(f"\n📊 Результаты фильтрации:")
            print(f"  ✅ Прошли фильтры: {passed_count}/{len(test_markets)} ({passed_count/len(test_markets)*100:.1f}%)")
            
            if failed_filters:
                print(f"\n🔍 Наиболее частые причины отказа:")
                filter_failures = {}
                for symbol, failures in failed_filters.items():
                    for failure in failures:
                        filter_name = failure.split(':')[0]
                        filter_failures[filter_name] = filter_failures.get(filter_name, 0) + 1
                
                sorted_failures = sorted(filter_failures.items(), key=lambda x: x[1], reverse=True)
                for filter_name, count in sorted_failures[:5]:
                    print(f"  - {filter_name}: {count} раз")
            
            return passed_count > 0
            
        except Exception as e:
            print(f"❌ Ошибка тестирования сканера: {e}")
            return False
    
    async def analyze_signal_conditions(self, preset_name: str = "breakout_v1"):
        """Анализирует условия генерации сигналов."""
        print(f"\n⚡ Анализ условий генерации сигналов")
        print("=" * 50)
        
        try:
            preset = load_preset(preset_name)
            
            print(f"🎯 Стратегия: {preset.strategy_priority}")
            print(f"📋 Конфигурация сигналов:")
            print(f"  - Моментум множитель объема: {preset.signal_config.momentum_volume_multiplier}")
            print(f"  - Мин. соотношение тела: {preset.signal_config.momentum_body_ratio_min}")
            print(f"  - Эпсилон: {preset.signal_config.momentum_epsilon}")
            print(f"  - Толерантность ретеста: {preset.signal_config.retest_pierce_tolerance}")
            print(f"  - Макс. проникновение ATR: {preset.signal_config.retest_max_pierce_atr}")
            print(f"  - Порог L2 дисбаланса: {preset.signal_config.l2_imbalance_threshold}")
            print(f"  - Макс. разрыв VWAP: {preset.signal_config.vwap_gap_max_atr}")
            
            print(f"\n🔍 Требуемые условия для моментум стратегии:")
            print(f"  ✅ price_breakout - прорыв уровня")
            print(f"  ✅ volume_surge - всплеск объема")
            print(f"  ✅ body_ratio - соотношение тела свечи")
            print(f"  ✅ l2_imbalance - дисбаланс L2")
            
            print(f"\n🔍 Требуемые условия для ретест стратегии:")
            print(f"  ✅ level_retest - ретест уровня")
            print(f"  ✅ pierce_tolerance - толерантность проникновения")
            print(f"  ✅ l2_imbalance - дисбаланс L2")
            print(f"  ✅ trading_activity - торговая активность")
            
            return True
            
        except Exception as e:
            print(f"❌ Ошибка анализа сигналов: {e}")
            return False
    
    async def run_full_diagnostics(self):
        """Запускает полную диагностику."""
        print("🚀 ДИАГНОСТИКА ТОРГОВОЙ СИСТЕМЫ")
        print("=" * 60)
        print(f"⏰ Время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Анализ пресетов
        preset = await self.analyze_preset_filters("breakout_v1")
        if not preset:
            return False
        
        # Тестирование данных
        data_ok = await self.test_market_data("breakout_v1")
        if not data_ok:
            print("❌ Проблемы с получением рыночных данных")
            return False
        
        # Тестирование фильтров
        filters_ok = await self.test_scanner_filters("breakout_v1")
        if not filters_ok:
            print("❌ Фильтры слишком строгие - ни один рынок не проходит")
        
        # Анализ сигналов
        signals_ok = await self.analyze_signal_conditions("breakout_v1")
        
        print(f"\n📋 ИТОГОВЫЙ ОТЧЕТ")
        print("=" * 30)
        print(f"✅ Пресет загружен: {'Да' if preset else 'Нет'}")
        print(f"✅ Данные получены: {'Да' if data_ok else 'Нет'}")
        print(f"✅ Фильтры работают: {'Да' if filters_ok else 'Нет'}")
        print(f"✅ Сигналы настроены: {'Да' if signals_ok else 'Нет'}")
        
        if not filters_ok:
            print(f"\n💡 РЕКОМЕНДАЦИИ:")
            print(f"  1. Снизить требования к ликвидности")
            print(f"  2. Увеличить допустимый спред")
            print(f"  3. Снизить требования к объему")
            print(f"  4. Увеличить допустимую волатильность")
        
        return True

async def main():
    """Главная функция."""
    diagnostics = TradingDiagnostics()
    await diagnostics.run_full_diagnostics()

if __name__ == "__main__":
    asyncio.run(main())
