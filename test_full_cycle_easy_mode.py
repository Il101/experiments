#!/usr/bin/env python3
"""
Тест полного цикла с ОЧЕНЬ МЯГКИМИ критериями для гарантированного прохождения всех состояний.

Цель: Увидеть полный пайплайн на реальных данных Bybit:
    SCANNING → LEVEL_BUILDING → SIGNAL_WAIT → SIZING → EXECUTION → MANAGING → IDLE

Используем экстремально низкие требования чтобы:
    1. Сгенерировать сигналы на любом токене
    2. Открыть позицию
    3. Подержать её
    4. Закрыть с профитом/лоссом
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

# Добавляем путь к проекту
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from breakout_bot.config.settings import Settings
from breakout_bot.core.engine import OptimizedOrchestraEngine
from breakout_bot.core.state_machine import TradingState


class EasyModeConfig:
    """Конфигурация с очень мягкими критериями для тестирования"""
    
    @staticmethod
    def get_easy_preset() -> Dict[str, Any]:
        """Создаем пресет с минимальными требованиями"""
        return {
            # === СКАНИРОВАНИЕ: Принимаем почти всё ===
            "scanning": {
                "min_24h_volume": 100,  # $100 (вместо $100k+)
                "min_oi": 10,  # $10 OI (вместо $50k+)
                "max_spread_pct": 5.0,  # 5% spread (вместо 0.2%)
                "min_depth_0_3pct": 10,  # $10 глубина (вместо $5k+)
                "min_depth_0_5pct": 10,  # $10 глубина
                "min_depth_1pct": 10,  # $10 глубина
                "min_trades_per_minute": 0.1,  # 0.1 сделок/мин (вместо 5)
                "atr_range": [0.0001, 100.0],  # Любая волатильность
                "volume_surge_1h": 0.1,  # 10% surge (вместо 150%)
                "volume_surge_5m": 0.1,  # 10% surge
                "max_candidates": 50,
            },
            
            # === УРОВНИ: Упрощенные требования ===
            "levels": {
                "lookback_candles": 50,  # Меньше свечей
                "min_touches": 2,  # 2 касания (вместо 3)
                "touch_threshold_atr": 0.5,
                "merge_threshold_atr": 0.3,
                "strength_threshold": 0.3,  # Низкий порог силы
                "volume_threshold": 0.5,  # Низкий порог объема
            },
            
            # === СИГНАЛЫ: Принимаем почти любое движение ===
            "signals": {
                "min_breakout_strength": 0.5,  # 50% силы (вместо 70%)
                "min_volume_ratio": 1.0,  # 1x объем (вместо 1.5x)
                "max_distance_from_level_atr": 1.0,  # Далеко от уровня OK
                "min_momentum_score": 0.3,  # 30% моментум (вместо 60%)
                "min_trend_alignment": 0.3,  # 30% тренд (вместо 60%)
                "require_volume_confirmation": False,  # Не требуем объем
                "allow_against_trend": True,  # Разрешаем против тренда
            },
            
            # === РИСК: Агрессивный (для быстрого тестирования) ===
            "risk": {
                "max_portfolio_risk": 0.5,  # 50% капитала (!)
                "max_position_risk": 0.1,  # 10% на позицию
                "max_open_positions": 3,
                "min_reward_risk_ratio": 1.0,  # 1:1 RR (вместо 2:1)
                "default_stop_loss_atr": 1.0,  # 1 ATR стоп
                "default_take_profit_atr": 2.0,  # 2 ATR профит
            },
            
            # === РАЗМЕР ПОЗИЦИИ: Минимальный ===
            "sizing": {
                "default_size_usd": 10,  # $10 позиция
                "min_size_usd": 5,  # Минимум $5
                "max_size_usd": 100,  # Максимум $100
                "use_dynamic_sizing": False,  # Фиксированный размер
            },
            
            # === УПРАВЛЕНИЕ: Быстрое закрытие ===
            "management": {
                "use_trailing_stop": True,
                "trailing_stop_activation_pct": 0.5,  # Активация при 0.5% профита
                "trailing_stop_distance_atr": 0.5,  # 0.5 ATR trailing
                "breakeven_trigger_pct": 0.3,  # В безубыток при 0.3%
                "partial_take_profit_levels": [
                    {"pct_profit": 0.5, "pct_close": 0.3},  # 30% при 0.5% профита
                    {"pct_profit": 1.0, "pct_close": 0.3},  # 30% при 1% профита
                ],
                "max_hold_time_minutes": 5,  # Максимум 5 минут держим
                "force_close_on_timeout": True,  # Принудительно закрываем
            },
        }


class FullCycleTestEasyMode:
    """Тест полного цикла торговли с мягкими критериями"""
    
    def __init__(self):
        self.engine = None
        self.start_time = None
        self.test_duration_minutes = 10  # 10 минут теста
        self.state_history = []
        self.signals_generated = []
        self.positions_opened = []
        self.positions_closed = []
        
    async def setup_engine(self):
        """Настройка движка с мягкими критериями"""
        print("=" * 80)
        print("🚀 FULL CYCLE TEST - EASY MODE (Real Data)")
        print("=" * 80)
        print()
        print("📋 Конфигурация теста:")
        print("   • Режим: Paper Trading + Real Bybit Data")
        print("   • Критерии: ОЧЕНЬ МЯГКИЕ (для гарантии сигналов)")
        print("   • Продолжительность: 10 минут")
        print("   • Размер позиций: $10-$100")
        print("   • Макс. время удержания: 5 минут")
        print()
        
        # Создаем конфиг с мягкими критериями
        easy_config = EasyModeConfig.get_easy_preset()
        
        # Создаем настройки
        settings = Settings()
        settings.mode = "paper"
        settings.exchange = "bybit"
        
        # Создаем движок
        print("⚙️  Инициализация движка...")
        self.engine = OptimizedOrchestraEngine(
            preset_name="breakout_v1_working"
        )
        
        # Инициализируем
        await self.engine.initialize()
        
        # Переопределяем конфиг на мягкий
        print("🔧 Применяем мягкие критерии...")
        self._apply_easy_config(easy_config)
        
        print("✅ Движок готов!")
        print()
        
    def _apply_easy_config(self, config: Dict[str, Any]):
        """Применяем мягкую конфигурацию к движку"""
        # Обновляем конфиг сканера
        if hasattr(self.engine, 'scanning_manager') and self.engine.scanning_manager:
            scanner = self.engine.scanning_manager.scanner
            if scanner and hasattr(scanner, 'config'):
                for key, value in config['scanning'].items():
                    setattr(scanner.config, key, value)
                print(f"   ✓ Сканер: мин. объем ${config['scanning']['min_24h_volume']}")
        
        # Обновляем конфиг сигналов
        if hasattr(self.engine, 'signal_manager') and self.engine.signal_manager:
            sig_gen = self.engine.signal_manager.signal_generator
            if sig_gen and hasattr(sig_gen, 'config'):
                for key, value in config['signals'].items():
                    if hasattr(sig_gen.config, key):
                        setattr(sig_gen.config, key, value)
                print(f"   ✓ Сигналы: мин. сила {config['signals']['min_breakout_strength']*100}%")
        
        # Обновляем риск-менеджер
        if hasattr(self.engine, 'risk_manager') and self.engine.risk_manager:
            for key, value in config['risk'].items():
                if hasattr(self.engine.risk_manager, key):
                    setattr(self.engine.risk_manager, key, value)
            print(f"   ✓ Риск: макс. {config['risk']['max_portfolio_risk']*100}% капитала")
        
    async def monitor_state_changes(self):
        """Мониторинг изменений состояний"""
        prev_state = None
        
        while True:
            await asyncio.sleep(0.5)  # Проверяем каждые 0.5 сек
            
            if not self.engine:
                continue
                
            current_state = self.engine.state_machine.current_state
            
            if current_state != prev_state:
                timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
                self.state_history.append({
                    'timestamp': timestamp,
                    'state': current_state,
                    'prev_state': prev_state
                })
                
                print(f"\n{'='*80}")
                print(f"[{timestamp}] 🔄 STATE CHANGE: {prev_state} → {current_state}")
                print(f"{'='*80}")
                
                # Выводим специфичную инфу по состоянию
                await self._print_state_details(current_state)
                
                prev_state = current_state
                
    async def _print_state_details(self, state: TradingState):
        """Выводим детали текущего состояния"""
        if state == TradingState.SCANNING:
            print("📡 Сканируем рынок...")
            
        elif state == TradingState.LEVEL_BUILDING:
            print("📊 Строим уровни поддержки/сопротивления...")
            
        elif state == TradingState.SIGNAL_WAIT:
            candidates = len(self.engine.scanning_manager.scan_results) if self.engine.scanning_manager else 0
            print(f"🎯 Ожидаем сигналы на {candidates} кандидатах...")
            
        elif state == TradingState.SIZING:
            signals = len(self.engine.signal_manager.pending_signals) if self.engine.signal_manager else 0
            print(f"📏 Рассчитываем размеры для {signals} сигналов...")
            
        elif state == TradingState.EXECUTION:
            print("💰 Открываем позиции!")
            
        elif state == TradingState.MANAGING:
            positions = len(self.engine.position_manager.active_positions) if self.engine.position_manager else 0
            print(f"📈 Управляем {positions} активными позициями...")
            await self._print_positions_status()
            
        elif state == TradingState.IDLE:
            print("🏁 Позиции закрыты, система в режиме ожидания...")
            await self._print_final_position_stats()
            
    async def _print_positions_status(self):
        """Выводим статус активных позиций"""
        if not self.engine or not self.engine.position_manager:
            return
            
        positions = self.engine.position_manager.active_positions
        if not positions:
            return
            
        print("\n📊 Активные позиции:")
        for pos in positions.values():
            pnl = pos.unrealized_pnl if hasattr(pos, 'unrealized_pnl') else 0
            pnl_pct = (pnl / pos.entry_price / pos.size * 100) if pos.size > 0 else 0
            
            print(f"   • {pos.symbol}:")
            print(f"      Entry: ${pos.entry_price:.6f}")
            print(f"      Size: {pos.size}")
            print(f"      PnL: ${pnl:.2f} ({pnl_pct:+.2f}%)")
            print(f"      Stop: ${pos.stop_loss:.6f}")
            print(f"      Target: ${pos.take_profit:.6f}")
        print()
        
    async def _print_final_position_stats(self):
        """Выводим финальную статистику закрытых позиций"""
        if not self.engine or not self.engine.position_manager:
            return
            
        closed = self.engine.position_manager.closed_positions
        if not closed:
            return
            
        print("\n💼 Закрытые позиции:")
        total_pnl = 0
        for pos in closed:
            pnl = pos.realized_pnl if hasattr(pos, 'realized_pnl') else 0
            total_pnl += pnl
            
            print(f"   • {pos.symbol}:")
            print(f"      Entry: ${pos.entry_price:.6f}")
            print(f"      Exit: ${pos.exit_price:.6f}")
            print(f"      PnL: ${pnl:.2f}")
            print(f"      Reason: {pos.close_reason if hasattr(pos, 'close_reason') else 'Unknown'}")
            
        print(f"\n   💰 Total PnL: ${total_pnl:.2f}")
        print()
        
    async def monitor_signals(self):
        """Мониторинг генерации сигналов"""
        prev_signal_count = 0
        
        while True:
            await asyncio.sleep(2)
            
            if not self.engine or not self.engine.signal_manager:
                continue
                
            current_signals = len(self.engine.signal_manager.pending_signals)
            
            if current_signals > prev_signal_count:
                new_signals = current_signals - prev_signal_count
                timestamp = datetime.now().strftime("%H:%M:%S")
                
                print(f"\n⚡ [{timestamp}] Сгенерировано {new_signals} новых сигналов!")
                print(f"   Всего в очереди: {current_signals}")
                
                # Выводим детали новых сигналов
                for signal in list(self.engine.signal_manager.pending_signals)[-new_signals:]:
                    print(f"\n   📊 {signal.symbol}:")
                    print(f"      Тип: {signal.signal_type}")
                    print(f"      Сила: {signal.strength:.2%}")
                    print(f"      Цена: ${signal.price:.6f}")
                    print(f"      Стоп: ${signal.stop_loss:.6f}")
                    print(f"      Цель: ${signal.take_profit:.6f}")
                    
                    self.signals_generated.append({
                        'timestamp': timestamp,
                        'symbol': signal.symbol,
                        'type': signal.signal_type,
                        'strength': signal.strength,
                        'price': signal.price
                    })
                
                prev_signal_count = current_signals
                
    async def run_test(self):
        """Запуск теста"""
        try:
            # Настройка движка
            await self.setup_engine()
            
            # Запуск движка
            print("🚀 Запуск движка...")
            self.start_time = datetime.now()
            
            # Запускаем мониторинг в фоне
            monitor_task = asyncio.create_task(self.monitor_state_changes())
            signal_task = asyncio.create_task(self.monitor_signals())
            
            # Запускаем движок
            engine_task = asyncio.create_task(self.engine.start())
            
            print(f"⏱️  Тест будет работать {self.test_duration_minutes} минут...")
            print(f"   Начало: {self.start_time.strftime('%H:%M:%S')}")
            print()
            
            # Ждем завершения теста или движка
            try:
                await asyncio.wait_for(
                    engine_task,
                    timeout=self.test_duration_minutes * 60
                )
            except asyncio.TimeoutError:
                print("\n⏰ Время теста истекло, останавливаем движок...")
                await self.engine.stop()
                
            # Останавливаем мониторинг
            monitor_task.cancel()
            signal_task.cancel()
            
            # Выводим итоги
            await self.print_summary()
            
        except Exception as e:
            print(f"\n❌ Ошибка: {e}")
            import traceback
            traceback.print_exc()
            
        finally:
            if self.engine:
                await self.engine.stop()
                
    async def print_summary(self):
        """Выводим итоговую сводку"""
        print("\n" + "="*80)
        print("📊 ИТОГИ ТЕСТА")
        print("="*80)
        
        runtime = datetime.now() - self.start_time
        print(f"\n⏱️  Время работы: {runtime}")
        
        print(f"\n🔄 История состояний ({len(self.state_history)} переходов):")
        for i, record in enumerate(self.state_history, 1):
            print(f"   {i}. [{record['timestamp']}] {record['prev_state']} → {record['state']}")
            
        print(f"\n⚡ Сигналы: {len(self.signals_generated)}")
        for sig in self.signals_generated:
            print(f"   • [{sig['timestamp']}] {sig['symbol']} - {sig['type']} (сила: {sig['strength']:.2%})")
            
        if self.engine and self.engine.position_manager:
            active = len(self.engine.position_manager.active_positions)
            closed = len(self.engine.position_manager.closed_positions)
            
            print(f"\n💼 Позиции:")
            print(f"   • Активных: {active}")
            print(f"   • Закрытых: {closed}")
            
            if closed > 0:
                total_pnl = sum(
                    pos.realized_pnl for pos in self.engine.position_manager.closed_positions
                    if hasattr(pos, 'realized_pnl')
                )
                print(f"   • Итоговый PnL: ${total_pnl:.2f}")
                
        print("\n" + "="*80)
        print("✅ ТЕСТ ЗАВЕРШЕН")
        print("="*80)


async def main():
    """Главная функция"""
    test = FullCycleTestEasyMode()
    await test.run_test()


if __name__ == "__main__":
    asyncio.run(main())
