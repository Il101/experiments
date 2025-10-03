#!/usr/bin/env python3
"""
Глубокий анализ пайплайна торгового бота.
Отслеживает прохождение данных через все этапы: SCANNING -> LEVEL_BUILDING -> SIGNAL_WAIT -> SIZING
"""

import asyncio
import sys
import time
import logging
from pathlib import Path

# Настроить путь для импортов
sys.path.insert(0, str(Path(__file__).parent))

from breakout_bot.core.engine import OptimizedOrchestraEngine
from breakout_bot.core.state_machine import TradingState


# Настроить логирование
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class PipelineAnalyzer:
    """Анализатор пайплайна торгового бота."""
    
    def __init__(self, preset_name: str = "breakout_v1"):
        self.preset_name = preset_name
        self.engine = None
        self.checkpoints = {}
        
    async def analyze(self):
        """Провести глубокий анализ пайплайна."""
        print("\n" + "="*80)
        print("🔍 ГЛУБОКИЙ АНАЛИЗ ПАЙПЛАЙНА")
        print("="*80 + "\n")
        
        try:
            # 1. Инициализация движка
            await self._test_engine_initialization()
            
            # 2. Анализ сканирования
            await self._test_scanning_phase()
            
            # 3. Анализ построения уровней
            await self._test_level_building_phase()
            
            # 4. Анализ генерации сигналов
            await self._test_signal_generation_phase()
            
            # 5. Анализ размерения
            await self._test_sizing_phase()
            
            # 6. Итоговый отчет
            self._print_summary()
            
        except Exception as e:
            logger.error(f"Ошибка анализа: {e}", exc_info=True)
            print(f"\n❌ КРИТИЧЕСКАЯ ОШИБКА: {e}\n")
            
        finally:
            if self.engine:
                await self.engine.stop()
                
    async def _test_engine_initialization(self):
        """Тест инициализации движка."""
        print("\n📦 ШАГ 1: Инициализация движка")
        print("-" * 80)
        
        start_time = time.time()
        try:
            self.engine = OptimizedOrchestraEngine(self.preset_name)
            await self.engine.initialize()
            
            duration = time.time() - start_time
            print(f"✅ Движок инициализирован за {duration:.2f}s")
            
            # Проверка компонентов
            components = {
                "exchange_client": self.engine.exchange_client,
                "scanning_manager": self.engine.scanning_manager,
                "signal_manager": self.engine.signal_manager,
                "risk_manager": self.engine.risk_manager,
                "position_manager": self.engine.position_manager,
                "execution_manager": self.engine.execution_manager,
            }
            
            print("\nКомпоненты движка:")
            for name, component in components.items():
                status = "✅" if component is not None else "❌"
                print(f"  {status} {name}: {type(component).__name__ if component else 'None'}")
                
            self.checkpoints['initialization'] = {
                'status': 'success',
                'duration': duration
            }
            
        except Exception as e:
            print(f"❌ Ошибка инициализации: {e}")
            self.checkpoints['initialization'] = {
                'status': 'failed',
                'error': str(e)
            }
            raise
            
    async def _test_scanning_phase(self):
        """Тест фазы сканирования."""
        print("\n\n🔍 ШАГ 2: Фаза сканирования")
        print("-" * 80)
        
        start_time = time.time()
        try:
            # Запустить сканирование через оркестратор
            print("Запуск сканирования...")
            
            # Переключить на состояние SCANNING
            await self.engine.state_machine.transition_to(
                TradingState.SCANNING,
                "Manual scan test"
            )
            
            # Запустить цикл сканирования с таймаутом
            async with asyncio.timeout(120.0):  # 2 минуты таймаут
                scan_results = await self.engine.scanning_manager.scan_markets(
                    self.engine.exchange_client,
                    "test_session"
                )
                
            duration = time.time() - start_time
            
            print(f"\n✅ Сканирование завершено за {duration:.2f}s")
            print(f"   Найдено кандидатов: {len(scan_results)}")
            
            # Анализ результатов сканирования
            if scan_results:
                print("\n📊 Топ-5 кандидатов:")
                for i, result in enumerate(scan_results[:5], 1):
                    print(f"   {i}. {result.symbol}")
                    print(f"      - Общий балл: {result.total_score:.3f}")
                    print(f"      - Уровней найдено: {len(result.levels)}")
                    print(f"      - Market data: {'✅' if result.market_data else '❌'}")
                    
                # Проверка данных первого кандидата
                first_result = scan_results[0]
                print(f"\n🔬 Детальная проверка {first_result.symbol}:")
                print(f"   - Candles: {len(first_result.market_data.candles) if first_result.market_data else 0}")
                print(f"   - L2 Depth: {'✅' if first_result.market_data and first_result.market_data.l2_depth else '❌'}")
                print(f"   - Trade Data: {'✅' if first_result.market_data and first_result.market_data.trades else '❌'}")
                
            else:
                print("⚠️  Кандидаты не найдены")
                
            self.checkpoints['scanning'] = {
                'status': 'success',
                'duration': duration,
                'candidates_found': len(scan_results),
                'scan_results': scan_results
            }
            
        except asyncio.TimeoutError:
            duration = time.time() - start_time
            print(f"\n❌ ТАЙМАУТ сканирования после {duration:.2f}s")
            print("   Возможные причины:")
            print("   1. Слишком много символов для сканирования")
            print("   2. Медленные API запросы к бирже")
            print("   3. Проблемы с сетью")
            
            self.checkpoints['scanning'] = {
                'status': 'timeout',
                'duration': duration
            }
            raise
            
        except Exception as e:
            duration = time.time() - start_time
            print(f"\n❌ Ошибка сканирования: {e}")
            self.checkpoints['scanning'] = {
                'status': 'failed',
                'error': str(e),
                'duration': duration
            }
            raise
            
    async def _test_level_building_phase(self):
        """Тест фазы построения уровней."""
        print("\n\n📐 ШАГ 3: Построение уровней")
        print("-" * 80)
        
        scan_results = self.checkpoints.get('scanning', {}).get('scan_results', [])
        
        if not scan_results:
            print("⚠️  Пропуск: нет результатов сканирования")
            self.checkpoints['level_building'] = {
                'status': 'skipped',
                'reason': 'no_scan_results'
            }
            return
            
        try:
            # Проверить уровни в результатах сканирования
            total_levels = sum(len(sr.levels) for sr in scan_results)
            print(f"✅ Всего уровней найдено: {total_levels}")
            
            if total_levels > 0:
                # Анализ качества уровней
                print("\n📊 Анализ уровней:")
                for result in scan_results[:3]:
                    if result.levels:
                        print(f"\n   {result.symbol}:")
                        for level in result.levels[:2]:
                            print(f"      - Цена: ${level.price:.4f}")
                            print(f"        Сила: {level.strength:.3f}")
                            print(f"        Тип: {level.level_type}")
                            print(f"        Касаний: {level.touches}")
            else:
                print("⚠️  Уровни не найдены")
                
            self.checkpoints['level_building'] = {
                'status': 'success',
                'total_levels': total_levels
            }
            
        except Exception as e:
            print(f"❌ Ошибка построения уровней: {e}")
            self.checkpoints['level_building'] = {
                'status': 'failed',
                'error': str(e)
            }
            raise
            
    async def _test_signal_generation_phase(self):
        """Тест фазы генерации сигналов."""
        print("\n\n⚡ ШАГ 4: Генерация сигналов")
        print("-" * 80)
        
        scan_results = self.checkpoints.get('scanning', {}).get('scan_results', [])
        
        if not scan_results:
            print("⚠️  Пропуск: нет результатов сканирования")
            self.checkpoints['signal_generation'] = {
                'status': 'skipped',
                'reason': 'no_scan_results'
            }
            return
            
        start_time = time.time()
        try:
            # Генерация сигналов
            print("Генерация сигналов из результатов сканирования...")
            
            signals = await self.engine.signal_manager.generate_signals_from_scan(
                scan_results,
                "test_session"
            )
            
            duration = time.time() - start_time
            
            print(f"\n✅ Генерация сигналов завершена за {duration:.2f}s")
            print(f"   Сигналов сгенерировано: {len(signals)}")
            
            if signals:
                print("\n📊 Сгенерированные сигналы:")
                for i, signal in enumerate(signals[:5], 1):
                    print(f"\n   {i}. {signal.symbol} - {signal.side}")
                    print(f"      Entry: ${signal.entry:.4f}")
                    print(f"      Stop Loss: ${signal.sl:.4f}")
                    print(f"      Take Profit: ${signal.tp:.4f}")
                    print(f"      Strategy: {signal.strategy}")
                    print(f"      Confidence: {signal.confidence:.2%}")
            else:
                print("\n⚠️  Сигналы не сгенерированы")
                print("   Возможные причины:")
                print("   1. Условия стратегии не выполнены")
                print("   2. Отфильтрованы риск-менеджером")
                print("   3. Не хватает рыночных данных")
                
            self.checkpoints['signal_generation'] = {
                'status': 'success',
                'duration': duration,
                'signals_generated': len(signals),
                'signals': signals
            }
            
        except Exception as e:
            duration = time.time() - start_time
            print(f"\n❌ Ошибка генерации сигналов: {e}")
            self.checkpoints['signal_generation'] = {
                'status': 'failed',
                'error': str(e),
                'duration': duration
            }
            raise
            
    async def _test_sizing_phase(self):
        """Тест фазы размерения позиций."""
        print("\n\n💰 ШАГ 5: Размерение позиций")
        print("-" * 80)
        
        signals = self.checkpoints.get('signal_generation', {}).get('signals', [])
        
        if not signals:
            print("⚠️  Пропуск: нет сигналов")
            self.checkpoints['sizing'] = {
                'status': 'skipped',
                'reason': 'no_signals'
            }
            return
            
        start_time = time.time()
        try:
            print("Оценка рисков и размерение позиций...")
            
            equity = 10000.0  # Тестовый капитал
            sized_signals = []
            
            for signal in signals:
                # Получить market data
                market_data = self.engine.signal_manager.signal_market_data.get(signal.symbol)
                
                if not market_data:
                    print(f"   ⚠️  {signal.symbol}: нет market data")
                    continue
                    
                # Оценить риск
                risk_evaluation = self.engine.risk_manager.evaluate_signal_risk(
                    signal,
                    equity,
                    [],  # Нет открытых позиций
                    market_data
                )
                
                print(f"\n   {signal.symbol}:")
                print(f"      Одобрено: {'✅' if risk_evaluation.get('approved') else '❌'}")
                print(f"      Размер: {risk_evaluation.get('position_size', 0):.4f}")
                print(f"      Риск: {risk_evaluation.get('risk_amount', 0):.2f} USDT")
                
                if risk_evaluation.get('rejection_reasons'):
                    print(f"      Причины отклонения:")
                    for reason in risk_evaluation['rejection_reasons']:
                        print(f"        - {reason}")
                        
                if risk_evaluation.get('approved'):
                    sized_signals.append(signal)
                    
            duration = time.time() - start_time
            
            print(f"\n✅ Размерение завершено за {duration:.2f}s")
            print(f"   Одобрено сигналов: {len(sized_signals)} / {len(signals)}")
            
            self.checkpoints['sizing'] = {
                'status': 'success',
                'duration': duration,
                'signals_approved': len(sized_signals),
                'signals_rejected': len(signals) - len(sized_signals)
            }
            
        except Exception as e:
            duration = time.time() - start_time
            print(f"\n❌ Ошибка размерения: {e}")
            self.checkpoints['sizing'] = {
                'status': 'failed',
                'error': str(e),
                'duration': duration
            }
            raise
            
    def _print_summary(self):
        """Вывести итоговый отчет."""
        print("\n\n" + "="*80)
        print("📋 ИТОГОВЫЙ ОТЧЕТ АНАЛИЗА ПАЙПЛАЙНА")
        print("="*80 + "\n")
        
        total_duration = sum(
            cp.get('duration', 0) 
            for cp in self.checkpoints.values()
        )
        
        print(f"Общее время: {total_duration:.2f}s\n")
        
        # Статус каждой фазы
        phases = [
            ('Инициализация', 'initialization'),
            ('Сканирование', 'scanning'),
            ('Построение уровней', 'level_building'),
            ('Генерация сигналов', 'signal_generation'),
            ('Размерение', 'sizing')
        ]
        
        for phase_name, phase_key in phases:
            checkpoint = self.checkpoints.get(phase_key, {})
            status = checkpoint.get('status', 'not_run')
            
            status_emoji = {
                'success': '✅',
                'failed': '❌',
                'timeout': '⏱️',
                'skipped': '⏭️',
                'not_run': '❓'
            }.get(status, '❓')
            
            print(f"{status_emoji} {phase_name}: {status.upper()}")
            
            if status == 'success':
                if 'duration' in checkpoint:
                    print(f"   Время: {checkpoint['duration']:.2f}s")
                if 'candidates_found' in checkpoint:
                    print(f"   Кандидатов: {checkpoint['candidates_found']}")
                if 'total_levels' in checkpoint:
                    print(f"   Уровней: {checkpoint['total_levels']}")
                if 'signals_generated' in checkpoint:
                    print(f"   Сигналов: {checkpoint['signals_generated']}")
                if 'signals_approved' in checkpoint:
                    print(f"   Одобрено: {checkpoint['signals_approved']}")
                    
            elif status == 'failed':
                print(f"   Ошибка: {checkpoint.get('error', 'Unknown')}")
                
            elif status == 'timeout':
                print(f"   Превышен таймаут после {checkpoint.get('duration', 0):.2f}s")
                
            elif status == 'skipped':
                print(f"   Причина: {checkpoint.get('reason', 'Unknown')}")
                
            print()
            
        # Диагностика проблем
        print("\n" + "="*80)
        print("🔧 ДИАГНОСТИКА ПРОБЛЕМ")
        print("="*80 + "\n")
        
        # Проверка, где застрял пайплайн
        last_success = None
        first_failure = None
        
        for phase_name, phase_key in phases:
            checkpoint = self.checkpoints.get(phase_key, {})
            status = checkpoint.get('status')
            
            if status == 'success':
                last_success = phase_name
            elif status in ['failed', 'timeout'] and first_failure is None:
                first_failure = phase_name
                
        if first_failure:
            print(f"❌ Пайплайн остановился на этапе: {first_failure}")
        elif last_success:
            print(f"✅ Последний успешный этап: {last_success}")
            
            # Следующий этап
            phase_index = next(
                (i for i, (n, _) in enumerate(phases) if n == last_success), 
                -1
            )
            if phase_index >= 0 and phase_index < len(phases) - 1:
                next_phase = phases[phase_index + 1][0]
                print(f"⏭️  Следующий этап: {next_phase}")
                
                next_checkpoint = self.checkpoints.get(phases[phase_index + 1][1], {})
                if next_checkpoint.get('status') == 'skipped':
                    print(f"   Пропущен из-за: {next_checkpoint.get('reason', 'Unknown')}")
                    
        print()


async def main():
    """Главная функция."""
    analyzer = PipelineAnalyzer()
    await analyzer.analyze()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  Анализ прерван пользователем")
    except Exception as e:
        print(f"\n\n❌ Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()
