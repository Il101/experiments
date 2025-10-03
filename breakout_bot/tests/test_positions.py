"""
Тесты для PositionManager - управления позициями.

Покрывает:
- PositionTracker - отслеживание отдельных позиций
- PositionManager - основной менеджер позиций
- Обновление стоп-лоссов
- Тейк-профиты
- Трейлинг-стопы
- Add-on позиции
- Метрики позиций
"""

import pytest
import numpy as np
import asyncio
from unittest.mock import Mock, patch
from datetime import datetime, timedelta

from breakout_bot.position.position_manager import (
    PositionTracker, PositionManager, PositionUpdate
)
from breakout_bot.data.models import Position, Candle, MarketData
from breakout_bot.config.settings import TradingPreset, PositionConfig


class TestPositionTracker:
    """Тесты для PositionTracker."""
    
    @pytest.fixture
    def mock_position(self):
        """Создает мок-позицию."""
        return Position(
            id="pos_123",
            symbol="BTC/USDT",
            side="long",
            strategy="momentum",
            qty=1.0,
            entry=100.0,
            sl=99.0,
            status="open",
            timestamps={"opened_at": int(datetime.now().timestamp() * 1000)}
        )
    
    @pytest.fixture
    def mock_config(self):
        """Создает мок-конфигурацию позиций."""
        config = Mock(spec=PositionConfig)
        config.tp1_r = 1.0
        config.tp2_r = 2.0
        config.tp1_size_pct = 0.5
        config.tp2_size_pct = 0.5
        config.chandelier_atr_mult = 3.0
        config.max_hold_time_hours = 24.0
        config.add_on_enabled = True
        config.add_on_max_size_pct = 0.3
        return config
    
    @pytest.fixture
    def mock_candles(self):
        """Создает мок-свечи."""
        base_time = int(datetime.now().timestamp() * 1000)
        candles = []
        
        for i in range(25):
            candle = Candle(
                ts=base_time - (25 - i) * 300000,  # 5-минутные свечи
                open=100.0 + i * 0.1,
                high=101.0 + i * 0.1,
                low=99.0 + i * 0.1,
                close=100.5 + i * 0.1,
                volume=1000.0 + i * 50
            )
            candles.append(candle)
        
        return candles
    
    @pytest.fixture
    def tracker(self, mock_position, mock_config):
        """Создает экземпляр трекера."""
        return PositionTracker(mock_position, mock_config)
    
    def test_initialization(self, tracker, mock_position, mock_config):
        """Тест инициализации трекера."""
        assert tracker.position == mock_position
        assert tracker.config == mock_config
        assert tracker.tp1_executed is False
        assert tracker.tp2_executed is False
        assert tracker.breakeven_moved is False
        assert tracker.trailing_active is False
        assert tracker.add_on_executed is False
    
    def test_should_update_stop_breakeven_after_tp1_long(self, tracker, mock_candles):
        """Тест обновления стопа - безубыток после TP1 для лонга."""
        tracker.tp1_executed = True
        tracker.breakeven_moved = False
        tracker.position.side = "long"
        tracker.position.entry = 100.0
        tracker.position.sl = 99.0
        
        new_stop = tracker.should_update_stop(102.0, mock_candles)
        
        assert new_stop is not None
        assert new_stop == 100.1  # 100.0 * 1.001
        assert tracker.breakeven_moved is True
    
    def test_should_update_stop_breakeven_after_tp1_short(self, tracker, mock_candles):
        """Тест обновления стопа - безубыток после TP1 для шорта."""
        tracker.tp1_executed = True
        tracker.breakeven_moved = False
        tracker.position.side = "short"
        tracker.position.entry = 100.0
        tracker.position.sl = 101.0
        
        new_stop = tracker.should_update_stop(98.0, mock_candles)
        
        assert new_stop is not None
        assert new_stop == 99.9  # 100.0 * 0.999
        assert tracker.breakeven_moved is True
    
    def test_should_update_stop_chandelier_exit_long(self, tracker, mock_candles):
        """Тест обновления стопа - Chandelier Exit для лонга."""
        tracker.breakeven_moved = True
        tracker.position.side = "long"
        tracker.position.sl = 100.0
        
        with patch('breakout_bot.position.position_manager.chandelier_exit') as mock_chandelier:
            mock_chandelier.return_value = np.array([101.0] * 25)
            
            new_stop = tracker.should_update_stop(102.0, mock_candles)
            
            assert new_stop is not None
            assert new_stop == 101.0
    
    def test_should_update_stop_chandelier_exit_short(self, tracker, mock_candles):
        """Тест обновления стопа - Chandelier Exit для шорта."""
        tracker.breakeven_moved = True
        tracker.position.side = "short"
        tracker.position.sl = 100.0
        
        with patch('breakout_bot.position.position_manager.chandelier_exit') as mock_chandelier:
            mock_chandelier.return_value = np.array([99.0] * 25)
            
            new_stop = tracker.should_update_stop(98.0, mock_candles)
            
            assert new_stop is not None
            assert new_stop == 99.0
    
    def test_should_update_stop_no_update(self, tracker, mock_candles):
        """Тест обновления стопа - нет обновления."""
        tracker.tp1_executed = False
        tracker.breakeven_moved = False
        
        new_stop = tracker.should_update_stop(102.0, mock_candles)
        
        assert new_stop is None
    
    def test_should_take_profit_tp1_long(self, tracker):
        """Тест тейк-профита - TP1 для лонга."""
        tracker.position.side = "long"
        tracker.position.entry = 100.0
        tracker.position.sl = 99.0
        tracker.tp1_executed = False
        
        result = tracker.should_take_profit(101.0)  # 1R прибыль
        
        assert result is not None
        tp_type, tp_price, tp_qty = result
        assert tp_type == "tp1"
        assert tp_price == 101.0  # entry + 1R
        assert tp_qty == 0.5  # 50% от позиции
    
    def test_should_take_profit_tp2_long(self, tracker):
        """Тест тейк-профита - TP2 для лонга."""
        tracker.position.side = "long"
        tracker.position.entry = 100.0
        tracker.position.sl = 99.0
        tracker.tp1_executed = True
        tracker.tp2_executed = False
        
        result = tracker.should_take_profit(102.0)  # 2R прибыль
        
        assert result is not None
        tp_type, tp_price, tp_qty = result
        assert tp_type == "tp2"
        assert tp_price == 102.0  # entry + 2R
        assert tp_qty == 0.5  # 50% от позиции
    
    def test_should_take_profit_tp1_short(self, tracker):
        """Тест тейк-профита - TP1 для шорта."""
        tracker.position.side = "short"
        tracker.position.entry = 100.0
        tracker.position.sl = 101.0
        tracker.tp1_executed = False
        
        result = tracker.should_take_profit(99.0)  # 1R прибыль
        
        assert result is not None
        tp_type, tp_price, tp_qty = result
        assert tp_type == "tp1"
        assert tp_price == 99.0  # entry - 1R
        assert tp_qty == 0.5  # 50% от позиции
    
    def test_should_take_profit_no_tp(self, tracker):
        """Тест тейк-профита - нет TP."""
        tracker.position.side = "long"
        tracker.position.entry = 100.0
        tracker.position.sl = 99.0
        tracker.tp1_executed = False
        
        result = tracker.should_take_profit(100.5)  # Недостаточно прибыли
        
        assert result is None
    
    def test_should_close_position_max_hold_time(self, tracker):
        """Тест закрытия позиции - превышено время удержания."""
        # Устанавливаем время открытия 25 часов назад
        old_time = int((datetime.now() - timedelta(hours=25)).timestamp() * 1000)
        tracker.position.timestamps["opened_at"] = old_time
        tracker.config.max_hold_time_hours = 24.0
        
        current_time = int(datetime.now().timestamp() * 1000)
        reason = tracker.should_close_position(current_time)
        
        assert reason is not None
        assert "Maximum hold time exceeded" in reason
    
    def test_should_close_position_no_progress(self, tracker):
        """Тест закрытия позиции - нет прогресса."""
        # Устанавливаем время открытия 9 часов назад
        old_time = int((datetime.now() - timedelta(hours=9)).timestamp() * 1000)
        tracker.position.timestamps["opened_at"] = old_time
        tracker.tp1_executed = False
        tracker.position.pnl_r = 0.2  # Меньше 0.3R
        
        current_time = int(datetime.now().timestamp() * 1000)
        reason = tracker.should_close_position(current_time)
        
        assert reason is not None
        assert "No progress after" in reason
    
    def test_should_close_position_no_close(self, tracker):
        """Тест закрытия позиции - не нужно закрывать."""
        # Устанавливаем время открытия 1 час назад
        old_time = int((datetime.now() - timedelta(hours=1)).timestamp() * 1000)
        tracker.position.timestamps["opened_at"] = old_time
        tracker.tp1_executed = True
        
        current_time = int(datetime.now().timestamp() * 1000)
        reason = tracker.should_close_position(current_time)
        
        assert reason is None
    
    def test_should_add_on_long(self, tracker, mock_candles):
        """Тест add-on позиции - лонг."""
        tracker.position.side = "long"
        tracker.position.pnl_r = 0.6  # Достаточно прибыли
        tracker.add_on_executed = False
        tracker.config.add_on_enabled = True
        
        with patch('breakout_bot.position.position_manager.ema') as mock_ema:
            mock_ema.return_value = np.array([100.0] * 25)
            
            add_on_price = tracker.should_add_on(100.0, mock_candles)
            
            assert add_on_price is not None
            assert add_on_price == 100.0
    
    def test_should_add_on_short(self, tracker, mock_candles):
        """Тест add-on позиции - шорт."""
        tracker.position.side = "short"
        tracker.position.pnl_r = 0.6  # Достаточно прибыли
        tracker.add_on_executed = False
        tracker.config.add_on_enabled = True
        
        with patch('breakout_bot.position.position_manager.ema') as mock_ema:
            mock_ema.return_value = np.array([100.0] * 25)
            
            add_on_price = tracker.should_add_on(100.0, mock_candles)
            
            assert add_on_price is not None
            assert add_on_price == 100.0
    
    def test_should_add_on_disabled(self, tracker, mock_candles):
        """Тест add-on позиции - отключено."""
        tracker.config.add_on_enabled = False
        
        add_on_price = tracker.should_add_on(100.0, mock_candles)
        
        assert add_on_price is None
    
    def test_should_add_on_already_executed(self, tracker, mock_candles):
        """Тест add-on позиции - уже выполнено."""
        tracker.add_on_executed = True
        
        add_on_price = tracker.should_add_on(100.0, mock_candles)
        
        assert add_on_price is None
    
    def test_should_add_on_insufficient_profit(self, tracker, mock_candles):
        """Тест add-on позиции - недостаточно прибыли."""
        tracker.position.pnl_r = 0.3  # Меньше 0.5R
        
        add_on_price = tracker.should_add_on(100.0, mock_candles)
        
        assert add_on_price is None


class TestPositionManager:
    """Тесты для PositionManager."""
    
    @pytest.fixture
    def mock_preset(self):
        """Создает мок-пресет."""
        preset = Mock(spec=TradingPreset)
        preset.name = "test_preset"
        preset.position_config = Mock(spec=PositionConfig)
        preset.position_config.tp1_r = 1.0
        preset.position_config.tp2_r = 2.0
        preset.position_config.tp1_size_pct = 0.5
        preset.position_config.tp2_size_pct = 0.5
        preset.position_config.chandelier_atr_mult = 3.0
        preset.position_config.max_hold_time_hours = 24.0
        preset.position_config.add_on_enabled = True
        preset.position_config.add_on_max_size_pct = 0.3
        return preset
    
    @pytest.fixture
    def mock_position(self):
        """Создает мок-позицию."""
        return Position(
            id="pos_123",
            symbol="BTC/USDT",
            side="long",
            strategy="momentum",
            qty=1.0,
            entry=100.0,
            sl=99.0,
            status="open",
            timestamps={"opened_at": int(datetime.now().timestamp() * 1000)}
        )
    
    @pytest.fixture
    def mock_market_data(self):
        """Создает мок-рыночные данные."""
        candles = [
            Candle(
                ts=int((datetime.now() - timedelta(minutes=i*5)).timestamp() * 1000),
                open=100.0 + i * 0.1,
                high=101.0 + i * 0.1,
                low=99.0 + i * 0.1,
                close=100.5 + i * 0.1,
                volume=1000.0 + i * 50
            )
            for i in range(25, 0, -1)
        ]
        
        return MarketData(
            symbol="BTC/USDT",
            price=102.0,
            volume_24h_usd=1000000.0,
            oi_usd=500000.0,
            oi_change_24h=0.05,
            trades_per_minute=10.0,
            atr_5m=1.0,
            atr_15m=1.5,
            bb_width_pct=2.0,
            btc_correlation=0.8,
            l2_depth=None,
            candles_5m=candles,
            timestamp=int(datetime.now().timestamp() * 1000)
        )
    
    @pytest.fixture
    def manager(self, mock_preset):
        """Создает экземпляр менеджера."""
        return PositionManager(mock_preset)
    
    @pytest.mark.asyncio
    async def test_initialization(self, manager, mock_preset):
        """Тест инициализации менеджера."""
        assert manager.preset == mock_preset
        assert manager.config == mock_preset.position_config
        assert len(manager.position_trackers) == 0
    
    @pytest.mark.asyncio
    async def test_add_position(self, manager, mock_position):
        """Тест добавления позиции."""
        await manager.add_position(mock_position)
        
        assert mock_position.id in manager.position_trackers
        tracker = manager.position_trackers[mock_position.id]
        assert tracker.position == mock_position
    
    @pytest.mark.asyncio
    async def test_remove_position(self, manager, mock_position):
        """Тест удаления позиции."""
        await manager.add_position(mock_position)
        assert mock_position.id in manager.position_trackers
        
        await manager.remove_position(mock_position.id)
        assert mock_position.id not in manager.position_trackers
    
    @pytest.mark.asyncio
    async def test_update_position(self, manager, mock_position):
        """Тест обновления позиции."""
        await manager.add_position(mock_position)
        
        # Обновляем позицию
        updated_position = Position(
            id="pos_123",
            symbol="BTC/USDT",
            side="long",
            strategy="momentum",
            qty=2.0,  # Изменили количество
            entry=100.0,
            sl=99.0,
            status="open"
        )
        
        await manager.update_position(updated_position)
        
        tracker = manager.position_trackers[mock_position.id]
        assert tracker.position.qty == 2.0
    
    @pytest.mark.asyncio

    
    async def test_process_position_updates_stop_update(self, manager, mock_position, mock_market_data):
        """Тест обработки обновлений позиций - обновление стопа."""
        await manager.add_position(mock_position)
        
        # Мокаем трекер для возврата обновления стопа
        tracker = manager.position_trackers[mock_position.id]
        tracker.should_update_stop = Mock(return_value=100.5)
        tracker.should_take_profit = Mock(return_value=None)
        tracker.should_close_position = Mock(return_value=None)
        tracker.should_add_on = Mock(return_value=None)
        
        positions = [mock_position]
        market_data_dict = {"BTC/USDT": mock_market_data}
        
        # Use asyncio.run for async method
        updates = asyncio.run(manager.process_position_updates(positions, market_data_dict))
        
        assert len(updates) == 1
        update = updates[0]
        assert update.position_id == "pos_123"
        assert update.action == "update_stop"
        assert update.price == 100.5
        assert "Stop update" in update.reason
    
    @pytest.mark.asyncio

    
    async def test_process_position_updates_take_profit(self, manager, mock_position, mock_market_data):
        """Тест обработки обновлений позиций - тейк-профит."""
        await manager.add_position(mock_position)
        
        # Мокаем трекер для возврата тейк-профита
        tracker = manager.position_trackers[mock_position.id]
        tracker.should_update_stop = Mock(return_value=None)
        tracker.should_take_profit = Mock(return_value=("tp1", 101.0, 0.5))
        tracker.should_close_position = Mock(return_value=None)
        tracker.should_add_on = Mock(return_value=None)
        
        positions = [mock_position]
        market_data_dict = {"BTC/USDT": mock_market_data}
        
        updates = asyncio.run(manager.process_position_updates(positions, market_data_dict))
        
        assert len(updates) == 1
        update = updates[0]
        assert update.position_id == "pos_123"
        assert update.action == "take_profit"
        assert update.price == 101.0
        assert update.quantity == 0.5
        assert "TP1 execution" in update.reason
        
        # Проверяем, что TP1 отмечен как выполненный
        assert tracker.tp1_executed is True
    
    @pytest.mark.asyncio

    
    async def test_process_position_updates_close_position(self, manager, mock_position, mock_market_data):
        """Тест обработки обновлений позиций - закрытие позиции."""
        await manager.add_position(mock_position)
        
        # Мокаем трекер для возврата закрытия позиции
        tracker = manager.position_trackers[mock_position.id]
        tracker.should_update_stop = Mock(return_value=None)
        tracker.should_take_profit = Mock(return_value=None)
        tracker.should_close_position = Mock(return_value="Maximum hold time exceeded")
        tracker.should_add_on = Mock(return_value=None)
        
        positions = [mock_position]
        market_data_dict = {"BTC/USDT": mock_market_data}
        
        updates = asyncio.run(manager.process_position_updates(positions, market_data_dict))
        
        assert len(updates) == 1
        update = updates[0]
        assert update.position_id == "pos_123"
        assert update.action == "close"
        assert update.price == 102.0  # Текущая цена
        assert update.quantity == 1.0  # Полное количество
        assert "Maximum hold time exceeded" in update.reason
    
    @pytest.mark.asyncio

    
    async def test_process_position_updates_add_on(self, manager, mock_position, mock_market_data):
        """Тест обработки обновлений позиций - add-on позиция."""
        await manager.add_position(mock_position)
        
        # Мокаем трекер для возврата add-on
        tracker = manager.position_trackers[mock_position.id]
        tracker.should_update_stop = Mock(return_value=None)
        tracker.should_take_profit = Mock(return_value=None)
        tracker.should_close_position = Mock(return_value=None)
        tracker.should_add_on = Mock(return_value=100.0)
        tracker.position.pnl_r = 0.6  # Достаточно прибыли
        
        positions = [mock_position]
        market_data_dict = {"BTC/USDT": mock_market_data}
        
        updates = asyncio.run(manager.process_position_updates(positions, market_data_dict))
        
        assert len(updates) == 1
        update = updates[0]
        assert update.position_id == "pos_123"
        assert update.action == "add_on"
        assert update.price == 100.0
        assert update.quantity == 0.3  # 30% от позиции
        assert "Add-on at EMA pullback" in update.reason
        
        # Проверяем, что add-on отмечен как выполненный
        assert tracker.add_on_executed is True
    
    def test_process_position_updates_closed_position(self, manager, mock_position, mock_market_data):
        """Тест обработки обновлений позиций - закрытая позиция."""
        # Создаем закрытую позицию
        closed_position = Position(
            id="pos_456",
            symbol="ETH/USDT",
            side="short",
            strategy="retest",
            qty=2.0,
            entry=2000.0,
            sl=2100.0,
            status="closed"
        )
        
        positions = [closed_position]
        market_data_dict = {"ETH/USDT": mock_market_data}
        
        updates = asyncio.run(manager.process_position_updates(positions, market_data_dict))
        
        # Закрытые позиции не должны обрабатываться
        assert len(updates) == 0
    
    @pytest.mark.asyncio

    
    async def test_process_position_updates_no_market_data(self, manager, mock_position):
        """Тест обработки обновлений позиций - нет рыночных данных."""
        await manager.add_position(mock_position)
        
        positions = [mock_position]
        market_data_dict = {}  # Пустой словарь
        
        updates = asyncio.run(manager.process_position_updates(positions, market_data_dict))
        
        # Без рыночных данных не должно быть обновлений
        assert len(updates) == 0
    
    @pytest.mark.asyncio
    async def test_calculate_position_metrics(self, manager):
        """Тест расчета метрик позиций."""
        # Создаем позиции
        open_position = Position(
            id="pos_1",
            symbol="BTC/USDT",
            side="long",
            strategy="momentum",
            qty=1.0,
            entry=100.0,
            sl=99.0,
            status="open",
            pnl_r=0.5
        )
        
        closed_position = Position(
            id="pos_2",
            symbol="ETH/USDT",
            side="short",
            strategy="retest",
            qty=2.0,
            entry=2000.0,
            sl=2100.0,
            status="closed",
            pnl_r=2.5,  # Changed to 2.5 to hit both tp1 and tp2
            timestamps={
                "opened_at": int((datetime.now() - timedelta(hours=2)).timestamp() * 1000),
                "closed_at": int(datetime.now().timestamp() * 1000)
            }
        )
        
        positions = [open_position, closed_position]
        
        # Добавляем трекеры для открытых позиций
        await manager.add_position(open_position)
        
        metrics = manager.calculate_position_metrics(positions)
        
        assert metrics["total_positions"] == 2
        assert metrics["open_positions"] == 1
        assert metrics["closed_positions"] == 1
        assert metrics["avg_hold_time_hours"] == 2.0
        assert metrics["tp1_hit_rate"] == 1.0  # 1 из 1 закрытых позиций >= 1R
        assert metrics["tp2_hit_rate"] == 1.0  # 1 из 1 закрытых позиций >= 2R
        assert metrics["avg_r_realized"] == 2.5
    
    @pytest.mark.asyncio

    
    async def test_get_position_status(self, manager, mock_position):
        """Тест получения статуса позиции."""
        await manager.add_position(mock_position)
        
        status = manager.get_position_status("pos_123")
        
        assert status is not None
        assert status["position_id"] == "pos_123"
        assert status["symbol"] == "BTC/USDT"
        assert status["side"] == "long"
        assert status["qty"] == 1.0
        assert status["entry"] == 100.0
        assert status["current_sl"] == 99.0
        assert status["tp1_executed"] is False
        assert status["tp2_executed"] is False
        assert status["breakeven_moved"] is False
        assert status["trailing_active"] is False
        assert status["add_on_executed"] is False
        assert status["status"] == "open"
    
    def test_get_position_status_not_found(self, manager):
        """Тест получения статуса несуществующей позиции."""
        status = manager.get_position_status("pos_999")
        
        assert status is None
    
    @pytest.mark.asyncio
    async def test_cleanup_closed_positions(self, manager):
        """Тест очистки закрытых позиций."""
        # Создаем трекеры для разных статусов
        open_position = Position(
            id="pos_1",
            symbol="BTC/USDT",
            side="long",
            strategy="momentum",
            qty=1.0,
            entry=100.0,
            sl=99.0,
            status="open"
        )
        
        closed_position = Position(
            id="pos_2",
            symbol="ETH/USDT",
            side="short",
            strategy="retest",
            qty=2.0,
            entry=2000.0,
            sl=2100.0,
            status="closed"
        )
        
        partially_closed_position = Position(
            id="pos_3",
            symbol="ADA/USDT",
            side="long",
            strategy="momentum",
            qty=1.0,
            entry=0.5,
            sl=0.49,
            status="partially_closed"
        )
        
        await manager.add_position(open_position)
        await manager.add_position(closed_position)
        await manager.add_position(partially_closed_position)
        
        # Очищаем закрытые позиции
        await manager.cleanup_closed_positions()
        
        # Должны остаться только открытые позиции
        assert "pos_1" in manager.position_trackers
        assert "pos_2" not in manager.position_trackers
        assert "pos_3" not in manager.position_trackers
    
    @pytest.mark.asyncio

    
    async def test_process_position_updates_error_handling(self, manager, mock_position, mock_market_data):
        """Тест обработки ошибок при обновлении позиций."""
        await manager.add_position(mock_position)
        
        # Мокаем трекер для вызова исключения
        tracker = manager.position_trackers[mock_position.id]
        tracker.should_update_stop = Mock(side_effect=Exception("Test error"))
        
        positions = [mock_position]
        market_data_dict = {"BTC/USDT": mock_market_data}
        
        updates = asyncio.run(manager.process_position_updates(positions, market_data_dict))
        
        # Должен обработать ошибку и продолжить
        assert len(updates) == 0
