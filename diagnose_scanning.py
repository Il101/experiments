#!/usr/bin/env python3
"""
Диагностика проблемы сканирования - почему не находятся кандидаты.
"""

import asyncio
import sys
import os

# Добавить путь к модулям
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from breakout_bot.config import get_preset
from breakout_bot.exchange import ExchangeClient
from breakout_bot.scanner import BreakoutScanner


async def diagnose_scanning():
    """Диагностировать проблему со сканированием."""
    
    print("=" * 80)
    print("ДИАГНОСТИКА СКАНИРОВАНИЯ")
    print("=" * 80)
    
    # Загрузить пресет
    preset = get_preset('breakout_v1')
    
    print("\n1. ТЕКУЩИЕ НАСТРОЙКИ ФИЛЬТРОВ:")
    print("-" * 80)
    lf = preset.liquidity_filters
    print(f"   min_24h_volume_usd:     ${lf.min_24h_volume_usd:,.0f}")
    print(f"   min_oi_usd:             ${lf.min_oi_usd:,.0f}")
    print(f"   max_spread_bps:         {lf.max_spread_bps}")
    print(f"   min_depth_usd_0_5pct:   ${lf.min_depth_usd_0_5pct:,.0f}")
    print(f"   min_depth_usd_0_3pct:   ${lf.min_depth_usd_0_3pct:,.0f}")
    print(f"   min_trades_per_minute:  {lf.min_trades_per_minute}")
    
    vf = preset.volatility_filters
    print(f"\n   Volatility Filters:")
    print(f"   min_atr_pct:            {vf.min_atr_pct}%")
    print(f"   max_atr_pct:            {vf.max_atr_pct}%")
    
    # Создать клиент биржи
    print("\n2. ПОДКЛЮЧЕНИЕ К БИРЖЕ...")
    print("-" * 80)
    client = ExchangeClient(preset=preset, paper_mode=True)
    await client.initialize()
    
    # Получить список рынков
    print("\n3. ПОЛУЧЕНИЕ СПИСКА РЫНКОВ...")
    print("-" * 80)
    all_markets = await client.fetch_markets()
    print(f"   Всего рынков: {len(all_markets)}")
    
    # Ограничить для теста
    test_markets = all_markets[:50]  # Первые 50 для быстрой диагностики
    print(f"   Тестируем первые {len(test_markets)} рынков")
    
    # Получить данные по рынкам
    print("\n4. АНАЛИЗ РЫНКОВ...")
    print("-" * 80)
    
    from breakout_bot.exchange.market_data_provider import MarketDataProvider
    mdp = MarketDataProvider(client)
    
    # Статистика
    stats = {
        'total': len(test_markets),
        'volume_fail': 0,
        'oi_fail': 0,
        'spread_fail': 0,
        'depth_fail': 0,
        'trades_fail': 0,
        'passed_all': 0
    }
    
    passed_symbols = []
    
    for symbol in test_markets:
        try:
            market_data = await mdp.get_market_data(symbol)
            
            # Проверить фильтры
            volume_ok = market_data.volume_24h_usd >= lf.min_24h_volume_usd
            
            # OI - только для фьючерсов
            market_type = getattr(market_data, 'market_type', 'unknown')
            if market_type == 'spot':
                oi_ok = True
            else:
                oi_ok = (market_data.oi_usd is not None and 
                        market_data.oi_usd >= lf.min_oi_usd)
            
            # Spread
            if market_data.l2_depth:
                spread_ok = market_data.l2_depth.spread_bps <= lf.max_spread_bps
                depth_ok = (market_data.l2_depth.total_depth_usd_0_5pct >= 
                           lf.min_depth_usd_0_5pct)
            else:
                spread_ok = True  # Skip if no data
                depth_ok = True
            
            trades_ok = market_data.trades_per_minute >= lf.min_trades_per_minute
            
            # Обновить статистику
            if not volume_ok:
                stats['volume_fail'] += 1
            if not oi_ok:
                stats['oi_fail'] += 1
            if not spread_ok:
                stats['spread_fail'] += 1
            if not depth_ok:
                stats['depth_fail'] += 1
            if not trades_ok:
                stats['trades_fail'] += 1
            
            if volume_ok and oi_ok and spread_ok and depth_ok and trades_ok:
                stats['passed_all'] += 1
                passed_symbols.append({
                    'symbol': symbol,
                    'volume': market_data.volume_24h_usd,
                    'oi': market_data.oi_usd,
                    'spread': market_data.l2_depth.spread_bps if market_data.l2_depth else None,
                    'trades_pm': market_data.trades_per_minute
                })
        
        except Exception as e:
            print(f"   ⚠️  Ошибка для {symbol}: {e}")
            continue
    
    # Вывести результаты
    print("\n5. РЕЗУЛЬТАТЫ АНАЛИЗА:")
    print("=" * 80)
    print(f"   Всего проанализировано:        {stats['total']}")
    print(f"   Прошли все фильтры:            {stats['passed_all']} ({stats['passed_all']/stats['total']*100:.1f}%)")
    print(f"\n   Причины отказа:")
    print(f"   - Недостаточный объем:         {stats['volume_fail']} ({stats['volume_fail']/stats['total']*100:.1f}%)")
    print(f"   - Недостаточный OI:            {stats['oi_fail']} ({stats['oi_fail']/stats['total']*100:.1f}%)")
    print(f"   - Большой спред:               {stats['spread_fail']} ({stats['spread_fail']/stats['total']*100:.1f}%)")
    print(f"   - Недостаточная глубина:       {stats['depth_fail']} ({stats['depth_fail']/stats['total']*100:.1f}%)")
    print(f"   - Мало сделок:                 {stats['trades_fail']} ({stats['trades_fail']/stats['total']*100:.1f}%)")
    
    if passed_symbols:
        print(f"\n6. МОНЕТЫ, ПРОШЕДШИЕ ВСЕ ФИЛЬТРЫ ({len(passed_symbols)}):")
        print("-" * 80)
        for item in passed_symbols[:10]:  # Показать первые 10
            print(f"   {item['symbol']:20s} Vol: ${item['volume']:>12,.0f}  "
                  f"OI: ${item['oi'] if item['oi'] else 0:>12,.0f}  "
                  f"Spread: {item['spread'] if item['spread'] else 0:>5.1f}bps  "
                  f"Trades: {item['trades_pm']:>5.1f}/min")
    else:
        print("\n⚠️  НЕТ МОНЕТ, ПРОШЕДШИХ ВСЕ ФИЛЬТРЫ!")
    
    print("\n7. РЕКОМЕНДАЦИИ:")
    print("=" * 80)
    
    if stats['volume_fail'] > stats['total'] * 0.8:
        print("   ⚠️  КРИТИЧНО: Фильтр по объему слишком строгий!")
        print("   Рекомендуемое значение: min_24h_volume_usd = 1,000,000 - 5,000,000")
    
    if stats['oi_fail'] > stats['total'] * 0.8:
        print("   ⚠️  КРИТИЧНО: Фильтр по открытому интересу слишком строгий!")
        print("   Рекомендуемое значение: min_oi_usd = 500,000 - 2,000,000")
    
    if stats['depth_fail'] > stats['total'] * 0.5:
        print("   ⚠️  Фильтр по глубине стакана слишком строгий!")
        print("   Рекомендуемое значение: min_depth_usd_0_5pct = 5,000 - 10,000")
    
    if stats['passed_all'] == 0:
        print("\n   🔧 РЕШЕНИЕ: Смягчить фильтры в конфигурации пресета")
        print("   Файл: breakout_bot/config/presets/breakout_v1.py")
        print("   Или создать новый пресет с более мягкими фильтрами")
    
    await client.close()
    print("\n" + "=" * 80)


if __name__ == "__main__":
    asyncio.run(diagnose_scanning())
