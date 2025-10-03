#!/usr/bin/env python3
"""
Проверка пайплайна работающего бота.

Анализирует логи и показывает:
1. Прогресс сканирования
2. Генерацию сигналов
3. Исполнение сделок
4. Узкие места в пайплайне
"""

import re
import os
from collections import defaultdict, Counter
from datetime import datetime, timedelta
from typing import Dict, List, Tuple


class PipelineChecker:
    """Анализатор пайплайна бота."""
    
    def __init__(self, log_file: str = 'logs/general.log'):
        self.log_file = log_file
        self.pipeline_stages = {
            'SCANNING': 0,
            'LEVEL_BUILDING': 0,
            'SIGNAL_WAIT': 0,
            'SIZING': 0,
            'EXECUTION': 0,
            'MANAGING': 0
        }
        self.scan_results = []
        self.signal_results = []
        self.trade_results = []
        self.errors = []
        self.rate_limit_errors = []
        self.timeouts = []
        
    def parse_logs(self, last_n_lines: int = 5000):
        """Парсинг логов."""
        print(f"📖 Читаю последние {last_n_lines} строк из {self.log_file}...")
        
        if not os.path.exists(self.log_file):
            print(f"❌ Лог-файл {self.log_file} не найден!")
            return
            
        # Читаем последние N строк
        with open(self.log_file, 'r') as f:
            lines = f.readlines()
            
        recent_lines = lines[-last_n_lines:] if len(lines) > last_n_lines else lines
        
        print(f"✅ Прочитано {len(recent_lines)} строк\n")
        
        # Паттерны для поиска
        patterns = {
            'scan_complete': re.compile(r'Market scan completed: (\d+) candidates found'),
            'scan_start': re.compile(r'Starting market scan'),
            'scan_symbols': re.compile(r'Fetching comprehensive market data for (\d+) symbols'),
            'scan_timeout': re.compile(r'Market data fetch timeout after (\d+)s'),
            'scan_fetched': re.compile(r'Comprehensive data fetch completed: (\d+) symbols'),
            'state_transition': re.compile(r'State transition: (\w+) -> (\w+)'),
            'current_state': re.compile(r'state: (\w+)'),
            'signal_generated': re.compile(r'Signal generated|Found (\d+) signals'),
            'trade_executed': re.compile(r'Order created|Order executed|Trade executed'),
            'error': re.compile(r'ERROR|Exception|Failed|failed'),
            'rate_limit': re.compile(r'429|rate limit|RateLimitExceeded', re.IGNORECASE),
            'timeout': re.compile(r'timeout|timed out', re.IGNORECASE),
            'cycle_count': re.compile(r'Completed (\d+) cycles'),
        }
        
        # Анализ строк
        for line in recent_lines:
            # Сканирование
            if match := patterns['scan_complete'].search(line):
                candidates = int(match.group(1))
                timestamp = self._extract_timestamp(line)
                self.scan_results.append({
                    'timestamp': timestamp,
                    'candidates': candidates
                })
                
            if match := patterns['scan_symbols'].search(line):
                symbols_count = int(match.group(1))
                timestamp = self._extract_timestamp(line)
                print(f"   🔍 {timestamp}: Начало сканирования {symbols_count} символов")
                
            if match := patterns['scan_timeout'].search(line):
                timeout_sec = int(match.group(1))
                self.timeouts.append({
                    'timestamp': self._extract_timestamp(line),
                    'timeout': timeout_sec
                })
                
            if match := patterns['scan_fetched'].search(line):
                fetched_count = int(match.group(1))
                timestamp = self._extract_timestamp(line)
                print(f"   ✅ {timestamp}: Получено данных по {fetched_count} символам")
                
            # Переходы состояний
            if match := patterns['state_transition'].search(line):
                from_state = match.group(1)
                to_state = match.group(2)
                timestamp = self._extract_timestamp(line)
                print(f"   🔄 {timestamp}: {from_state} → {to_state}")
                self.pipeline_stages[to_state] = self.pipeline_stages.get(to_state, 0) + 1
                
            # Текущее состояние
            if match := patterns['current_state'].search(line):
                state = match.group(1)
                self.pipeline_stages[state] = self.pipeline_stages.get(state, 0) + 1
                
            # Сигналы
            if patterns['signal_generated'].search(line):
                timestamp = self._extract_timestamp(line)
                self.signal_results.append({
                    'timestamp': timestamp
                })
                
            # Сделки
            if patterns['trade_executed'].search(line):
                timestamp = self._extract_timestamp(line)
                self.trade_results.append({
                    'timestamp': timestamp
                })
                
            # Ошибки
            if patterns['error'].search(line):
                self.errors.append({
                    'timestamp': self._extract_timestamp(line),
                    'line': line.strip()
                })
                
            # Rate limit
            if patterns['rate_limit'].search(line):
                self.rate_limit_errors.append({
                    'timestamp': self._extract_timestamp(line),
                    'line': line.strip()
                })
                
    def _extract_timestamp(self, line: str) -> str:
        """Извлечение timestamp из строки лога."""
        match = re.match(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', line)
        if match:
            return match.group(1)
        return 'N/A'
        
    def analyze_scanning(self):
        """Анализ сканирования."""
        print("\n" + "="*80)
        print("🔍 АНАЛИЗ СКАНИРОВАНИЯ")
        print("="*80 + "\n")
        
        if not self.scan_results:
            print("⚠️  Результаты сканирования не найдены в логах")
            print("   Возможные причины:")
            print("   - Бот еще не начал сканирование")
            print("   - Логи слишком старые")
            return
            
        print(f"Всего циклов сканирования: {len(self.scan_results)}")
        
        # Статистика по кандидатам
        candidates_counts = [r['candidates'] for r in self.scan_results]
        
        if candidates_counts:
            avg_candidates = sum(candidates_counts) / len(candidates_counts)
            max_candidates = max(candidates_counts)
            min_candidates = min(candidates_counts)
            zero_candidates = candidates_counts.count(0)
            
            print(f"\n📊 Статистика по кандидатам:")
            print(f"   Среднее: {avg_candidates:.1f}")
            print(f"   Максимум: {max_candidates}")
            print(f"   Минимум: {min_candidates}")
            print(f"   Циклов с 0 кандидатами: {zero_candidates}/{len(candidates_counts)}")
            
            if zero_candidates == len(candidates_counts):
                print("\n❌ ПРОБЛЕМА: Всегда находится 0 кандидатов!")
                print("   Возможные причины:")
                print("   - Фильтры слишком строгие")
                print("   - Не получаются данные от биржи")
                print("   - Timeout при получении данных")
                print("   - ENGINE_MARKET_FETCH_LIMIT слишком мал")
            elif zero_candidates > len(candidates_counts) * 0.8:
                print("\n⚠️  ВНИМАНИЕ: Более 80% циклов без кандидатов")
            else:
                print("\n✅ Сканирование работает нормально")
                
        # Последние результаты
        print(f"\n🕐 Последние 10 сканирований:")
        for result in self.scan_results[-10:]:
            status = "✅" if result['candidates'] > 0 else "❌"
            print(f"   {status} {result['timestamp']}: {result['candidates']} кандидатов")
            
    def analyze_timeouts(self):
        """Анализ таймаутов."""
        print("\n" + "="*80)
        print("⏱️  АНАЛИЗ ТАЙМАУТОВ")
        print("="*80 + "\n")
        
        if not self.timeouts:
            print("✅ Таймаутов не обнаружено")
            return
            
        print(f"❌ Обнаружено таймаутов: {len(self.timeouts)}")
        print(f"\n🕐 Последние 5 таймаутов:")
        for timeout in self.timeouts[-5:]:
            print(f"   ⏱️  {timeout['timestamp']}: Timeout после {timeout['timeout']}s")
            
        print("\n💡 Рекомендации:")
        print("   - Увеличьте MARKET_DATA_TIMEOUT в .env")
        print("   - Уменьшите ENGINE_MARKET_FETCH_LIMIT")
        print("   - Увеличьте LIVE_SCAN_CONCURRENCY")
        
    def analyze_pipeline_flow(self):
        """Анализ потока через пайплайн."""
        print("\n" + "="*80)
        print("🔄 АНАЛИЗ ПОТОКА ПАЙПЛАЙНА")
        print("="*80 + "\n")
        
        if not self.pipeline_stages or all(v == 0 for v in self.pipeline_stages.values()):
            print("⚠️  Данные о переходах между стадиями не найдены")
            print("   Возможно, бот еще не начал полноценную работу")
            return
        
        print("Количество прохождений через каждую стадию:")
        
        max_count = max(self.pipeline_stages.values()) if self.pipeline_stages.values() else 1
        max_count = max(1, max_count)  # Ensure at least 1 to avoid division by zero
        
        for stage, count in sorted(self.pipeline_stages.items(), key=lambda x: x[1], reverse=True):
            bar_length = int((count / max_count) * 40)
            bar = "█" * bar_length
            print(f"   {stage:20s} {bar} {count}")
            
        # Анализ узких мест
        print("\n🔍 Анализ узких мест:")
        
        scanning_count = self.pipeline_stages.get('SCANNING', 0)
        signal_wait_count = self.pipeline_stages.get('SIGNAL_WAIT', 0)
        execution_count = self.pipeline_stages.get('EXECUTION', 0)
        
        if scanning_count > signal_wait_count * 2:
            print("   ⚠️  Бот застревает в SCANNING - не находит кандидатов")
        elif signal_wait_count > execution_count * 2:
            print("   ⚠️  Бот застревает в SIGNAL_WAIT - не генерирует сигналы")
        else:
            print("   ✅ Поток через пайплайн сбалансирован")
            
    def analyze_signals_and_trades(self):
        """Анализ сигналов и сделок."""
        print("\n" + "="*80)
        print("📡 АНАЛИЗ СИГНАЛОВ И СДЕЛОК")
        print("="*80 + "\n")
        
        print(f"Сгенерировано сигналов: {len(self.signal_results)}")
        print(f"Выполнено сделок: {len(self.trade_results)}")
        
        if len(self.signal_results) == 0:
            print("\n❌ ПРОБЛЕМА: Сигналы не генерируются!")
            print("   Возможные причины:")
            print("   - Нет кандидатов из сканирования")
            print("   - Фильтры сигналов слишком строгие")
            print("   - Ошибки в генераторе сигналов")
        elif len(self.trade_results) == 0 and len(self.signal_results) > 0:
            print("\n⚠️  ВНИМАНИЕ: Сигналы есть, но сделок нет!")
            print("   Возможные причины:")
            print("   - Риск-менеджмент блокирует сделки")
            print("   - Недостаточно баланса")
            print("   - Ошибки в execution manager")
        else:
            conversion = (len(self.trade_results) / len(self.signal_results) * 100) if len(self.signal_results) > 0 else 0
            print(f"\n✅ Конверсия сигналов в сделки: {conversion:.1f}%")
            
    def analyze_errors(self):
        """Анализ ошибок."""
        print("\n" + "="*80)
        print("🐛 АНАЛИЗ ОШИБОК")
        print("="*80 + "\n")
        
        if not self.errors:
            print("✅ Критических ошибок не обнаружено")
        else:
            print(f"⚠️  Обнаружено ошибок: {len(self.errors)}")
            print(f"\n🕐 Последние 5 ошибок:")
            for error in self.errors[-5:]:
                print(f"   ❌ {error['timestamp']}")
                print(f"      {error['line'][:120]}...")
                
        if self.rate_limit_errors:
            print(f"\n⚠️  Rate limit ошибок: {len(self.rate_limit_errors)}")
            print("   Рекомендации:")
            print("   - Уменьшите LIVE_SCAN_CONCURRENCY")
            print("   - Проверьте, что rate limiter активен")
            
    def print_summary(self):
        """Печать финальной сводки."""
        print("\n" + "="*80)
        print("📋 СВОДКА")
        print("="*80 + "\n")
        
        # Определение текущего статуса
        if not self.scan_results:
            status = "🔴 НЕ РАБОТАЕТ"
            print(f"Статус: {status}")
            print("\nПроблема: Бот не выполняет сканирование")
            print("\n🔧 Рекомендации:")
            print("   1. Проверьте, что бот запущен: ps aux | grep breakout")
            print("   2. Проверьте логи на ошибки: tail -50 logs/general.log")
            print("   3. Перезапустите бот: ./stop.sh && ./start.sh")
            return
            
        zero_candidates_pct = (
            self.scan_results[-10:].count({'timestamp': r['timestamp'], 'candidates': 0} 
            for r in self.scan_results[-10:]) / len(self.scan_results[-10:]) * 100
            if len(self.scan_results) >= 10 else 0
        )
        
        if all(r['candidates'] == 0 for r in self.scan_results[-10:]):
            status = "🟡 РАБОТАЕТ, НО ЗАСТРЯЛ"
            print(f"Статус: {status}")
            print("\nПроблема: Бот работает, но застревает на сканировании (0 кандидатов)")
            print("\n🔧 Рекомендации:")
            print("   1. Увеличьте ENGINE_MARKET_FETCH_LIMIT в .env (текущее значение может быть слишком мало)")
            print("   2. Увеличьте MARKET_DATA_TIMEOUT (возможно, данные не успевают получиться)")
            print("   3. Проверьте фильтры в пресете - они могут быть слишком строгие")
            print("   4. Запустите: python3 test_bybit_data_fetching.py")
        elif len(self.signal_results) == 0:
            status = "🟡 СКАНИРУЕТ, НО НЕТ СИГНАЛОВ"
            print(f"Статус: {status}")
            print("\nПроблема: Сканирование работает, но сигналы не генерируются")
            print("\n🔧 Рекомендации:")
            print("   1. Проверьте фильтры сигналов в пресете")
            print("   2. Проверьте логи signal_manager")
            print("   3. Используйте более мягкий пресет (например, breakout_v1_relaxed)")
        else:
            status = "🟢 РАБОТАЕТ НОРМАЛЬНО"
            print(f"Статус: {status}")
            print("\n✅ Бот работает корректно:")
            print(f"   - Сканирование: {len(self.scan_results)} циклов")
            print(f"   - Сигналы: {len(self.signal_results)}")
            print(f"   - Сделки: {len(self.trade_results)}")
            
    def run(self):
        """Запуск полного анализа."""
        print("="*80)
        print("🔍 ПРОВЕРКА ПАЙПЛАЙНА БОТА")
        print("="*80)
        
        self.parse_logs()
        self.analyze_scanning()
        self.analyze_timeouts()
        self.analyze_pipeline_flow()
        self.analyze_signals_and_trades()
        self.analyze_errors()
        self.print_summary()
        
        print("\n✅ Анализ завершен!\n")


def main():
    """Главная функция."""
    checker = PipelineChecker()
    
    try:
        checker.run()
    except KeyboardInterrupt:
        print("\n\n⚠️  Анализ прерван")
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
