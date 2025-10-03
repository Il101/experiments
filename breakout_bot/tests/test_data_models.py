"""
Тесты для моделей данных.

Покрывает:
- Candle - свечи OHLCV
- L2Depth - данные L2
- TradingLevel - торговые уровни
- Signal - торговые сигналы
- Position - позиции
- Order - ордера
- MarketData - рыночные данные
- ScanResult - результаты сканирования
"""

import pytest
from datetime import datetime, timedelta
from pydantic import ValidationError

from breakout_bot.data.models import (
    Candle, L2Depth, TradingLevel, Signal, Position, Order, MarketData, ScanResult
)


class TestCandle:
    """Тесты для модели Candle."""
    
    def test_candle_creation(self):
        """Тест создания свечи."""
        candle = Candle(
            ts=1640995200000,  # 2022-01-01 00:00:00
            open=100.0,
            high=105.0,
            low=95.0,
            close=102.0,
            volume=1000.0
        )
        
        assert candle.ts == 1640995200000
        assert candle.open == 100.0
        assert candle.high == 105.0
        assert candle.low == 95.0
        assert candle.close == 102.0
        assert candle.volume == 1000.0
    
    def test_candle_validation_positive_prices(self):
        """Тест валидации - положительные цены."""
        # Все цены должны быть положительными
        with pytest.raises(ValidationError):
            Candle(
                ts=1640995200000,
                open=-100.0,  # Отрицательная цена
                high=105.0,
                low=95.0,
                close=102.0,
                volume=1000.0
            )
    
    def test_candle_validation_positive_volume(self):
        """Тест валидации - неотрицательный объем."""
        with pytest.raises(ValidationError):
            Candle(
                ts=1640995200000,
                open=100.0,
                high=105.0,
                low=95.0,
                close=102.0,
                volume=-1000.0  # Отрицательный объем
            )
    
    def test_candle_validation_low_vs_high(self):
        """Тест валидации - low <= high."""
        with pytest.raises(ValidationError):
            Candle(
                ts=1640995200000,
                open=100.0,
                high=95.0,  # high < low
                low=105.0,
                close=102.0,
                volume=1000.0
            )
    
    def test_candle_properties(self):
        """Тест свойств свечи."""
        candle = Candle(
            ts=1640995200000,
            open=100.0,
            high=105.0,
            low=95.0,
            close=102.0,
            volume=1000.0
        )
        
        # Тест datetime
        expected_dt = datetime.fromtimestamp(1640995200)
        assert candle.datetime == expected_dt
        
        # Тест typical_price
        expected_typical = (105.0 + 95.0 + 102.0) / 3
        assert candle.typical_price == expected_typical
        
        # Тест hl2
        expected_hl2 = (105.0 + 95.0) / 2
        assert candle.hl2 == expected_hl2
        
        # Тест ohlc4
        expected_ohlc4 = (100.0 + 105.0 + 95.0 + 102.0) / 4
        assert candle.ohlc4 == expected_ohlc4


class TestL2Depth:
    """Тесты для модели L2Depth."""
    
    def test_l2_depth_creation(self):
        """Тест создания L2 данных."""
        l2_depth = L2Depth(
            bid_usd_0_5pct=50000.0,
            ask_usd_0_5pct=50000.0,
            bid_usd_0_3pct=30000.0,
            ask_usd_0_3pct=30000.0,
            spread_bps=5.0,
            imbalance=0.1
        )
        
        assert l2_depth.bid_usd_0_5pct == 50000.0
        assert l2_depth.ask_usd_0_5pct == 50000.0
        assert l2_depth.bid_usd_0_3pct == 30000.0
        assert l2_depth.ask_usd_0_3pct == 30000.0
        assert l2_depth.spread_bps == 5.0
        assert l2_depth.imbalance == 0.1
    
    def test_l2_depth_validation_spread(self):
        """Тест валидации - неотрицательный спред."""
        with pytest.raises(ValidationError):
            L2Depth(
                bid_usd_0_5pct=50000.0,
                ask_usd_0_5pct=50000.0,
                bid_usd_0_3pct=30000.0,
                ask_usd_0_3pct=30000.0,
                spread_bps=-5.0,  # Отрицательный спред
                imbalance=0.1
            )
    
    def test_l2_depth_validation_imbalance(self):
        """Тест валидации - imbalance между -1 и 1."""
        with pytest.raises(ValidationError):
            L2Depth(
                bid_usd_0_5pct=50000.0,
                ask_usd_0_5pct=50000.0,
                bid_usd_0_3pct=30000.0,
                ask_usd_0_3pct=30000.0,
                spread_bps=5.0,
                imbalance=1.5  # Вне диапазона [-1, 1]
            )
    
    def test_l2_depth_properties(self):
        """Тест свойств L2 данных."""
        l2_depth = L2Depth(
            bid_usd_0_5pct=50000.0,
            ask_usd_0_5pct=50000.0,
            bid_usd_0_3pct=30000.0,
            ask_usd_0_3pct=30000.0,
            spread_bps=5.0,
            imbalance=0.1
        )
        
        # Тест total_depth_usd_0_5pct
        expected_total_0_5 = 50000.0 + 50000.0
        assert l2_depth.total_depth_usd_0_5pct == expected_total_0_5
        
        # Тест total_depth_usd_0_3pct
        expected_total_0_3 = 30000.0 + 30000.0
        assert l2_depth.total_depth_usd_0_3pct == expected_total_0_3


class TestTradingLevel:
    """Тесты для модели TradingLevel."""
    
    def test_trading_level_creation(self):
        """Тест создания торгового уровня."""
        level = TradingLevel(
            price=100.0,
            level_type="resistance",
            touch_count=3,
            strength=0.8,
            first_touch_ts=1640995200000,
            last_touch_ts=1640995200000
        )
        
        assert level.price == 100.0
        assert level.level_type == "resistance"
        assert level.touch_count == 3
        assert level.strength == 0.8
        assert level.first_touch_ts == 1640995200000
        assert level.last_touch_ts == 1640995200000
        assert level.base_height is None
    
    def test_trading_level_validation_touch_count(self):
        """Тест валидации - положительное количество касаний."""
        with pytest.raises(ValidationError):
            TradingLevel(
                price=100.0,
                level_type="resistance",
                touch_count=0,  # Должно быть >= 1
                strength=0.8,
                first_touch_ts=1640995200000,
                last_touch_ts=1640995200000
            )
    
    def test_trading_level_validation_strength(self):
        """Тест валидации - strength между 0 и 1."""
        with pytest.raises(ValidationError):
            TradingLevel(
                price=100.0,
                level_type="resistance",
                touch_count=3,
                strength=1.5,  # Вне диапазона [0, 1]
                first_touch_ts=1640995200000,
                last_touch_ts=1640995200000
            )
    
    def test_trading_level_with_base_height(self):
        """Тест торгового уровня с base_height."""
        level = TradingLevel(
            price=100.0,
            level_type="support",
            touch_count=5,
            strength=0.9,
            first_touch_ts=1640995200000,
            last_touch_ts=1640995200000,
            base_height=10.0
        )
        
        assert level.base_height == 10.0


class TestSignal:
    """Тесты для модели Signal."""
    
    def test_signal_creation(self):
        """Тест создания торгового сигнала."""
        signal = Signal(
            symbol="BTC/USDT",
            side="long",
            strategy="momentum",
            reason="Test signal",
            entry=100.0,
            level=99.0,
            sl=98.0,
            confidence=0.8,
            timestamp=1640995200000,
            meta={"test": "value"}
        )
        
        assert signal.symbol == "BTC/USDT"
        assert signal.side == "long"
        assert signal.strategy == "momentum"
        assert signal.reason == "Test signal"
        assert signal.entry == 100.0
        assert signal.level == 99.0
        assert signal.sl == 98.0
        assert signal.confidence == 0.8
        assert signal.timestamp == 1640995200000
        assert signal.meta == {"test": "value"}
    
    def test_signal_validation_confidence(self):
        """Тест валидации - confidence между 0 и 1."""
        with pytest.raises(ValidationError):
            Signal(
                symbol="BTC/USDT",
                side="long",
                strategy="momentum",
                reason="Test signal",
                entry=100.0,
                level=99.0,
                sl=98.0,
                confidence=1.5,  # Вне диапазона [0, 1]
                timestamp=1640995200000
            )
    
    def test_signal_validation_prices(self):
        """Тест валидации - положительные цены."""
        with pytest.raises(ValidationError):
            Signal(
                symbol="BTC/USDT",
                side="long",
                strategy="momentum",
                reason="Test signal",
                entry=-100.0,  # Отрицательная цена
                level=99.0,
                sl=98.0,
                confidence=0.8,
                timestamp=1640995200000
            )
    
    def test_signal_risk_reward_ratio_long(self):
        """Тест расчета risk-reward ratio для лонга."""
        signal = Signal(
            symbol="BTC/USDT",
            side="long",
            strategy="momentum",
            reason="Test signal",
            entry=100.0,
            level=99.0,
            sl=98.0,
            confidence=0.8,
            timestamp=1640995200000,
            meta={"tp": 102.0}  # Take profit
        )
        
        # Risk = 100 - 98 = 2
        # Reward = 102 - 100 = 2
        # Ratio = 2 / 2 = 1
        assert signal.risk_reward_ratio == 1.0
    
    def test_signal_risk_reward_ratio_short(self):
        """Тест расчета risk-reward ratio для шорта."""
        signal = Signal(
            symbol="BTC/USDT",
            side="short",
            strategy="momentum",
            reason="Test signal",
            entry=100.0,
            level=101.0,
            sl=102.0,
            confidence=0.8,
            timestamp=1640995200000,
            meta={"tp": 98.0}  # Take profit
        )
        
        # Risk = 102 - 100 = 2
        # Reward = 100 - 98 = 2
        # Ratio = 2 / 2 = 1
        assert signal.risk_reward_ratio == 1.0
    
    def test_signal_risk_reward_ratio_no_tp(self):
        """Тест расчета risk-reward ratio без TP."""
        signal = Signal(
            symbol="BTC/USDT",
            side="long",
            strategy="momentum",
            reason="Test signal",
            entry=100.0,
            level=99.0,
            sl=98.0,
            confidence=0.8,
            timestamp=1640995200000
        )
        
        assert signal.risk_reward_ratio == 0


class TestPosition:
    """Тесты для модели Position."""
    
    def test_position_creation(self):
        """Тест создания позиции."""
        position = Position(
            id="pos_123",
            symbol="BTC/USDT",
            side="long",
            strategy="momentum",
            qty=1.0,
            entry=100.0,
            sl=99.0,
            tp=102.0,
            status="open",
            pnl_usd=50.0,
            pnl_r=1.0,
            fees_usd=5.0,
            timestamps={"opened_at": 1640995200000},
            meta={"test": "value"}
        )
        
        assert position.id == "pos_123"
        assert position.symbol == "BTC/USDT"
        assert position.side == "long"
        assert position.strategy == "momentum"
        assert position.qty == 1.0
        assert position.entry == 100.0
        assert position.sl == 99.0
        assert position.tp == 102.0
        assert position.status == "open"
        assert position.pnl_usd == 50.0
        assert position.pnl_r == 1.0
        assert position.fees_usd == 5.0
        assert position.timestamps == {"opened_at": 1640995200000}
        assert position.meta == {"test": "value"}
    
    def test_position_validation_quantity(self):
        """Тест валидации - положительное количество."""
        with pytest.raises(ValidationError):
            Position(
                id="pos_123",
                symbol="BTC/USDT",
                side="long",
                strategy="momentum",
                qty=-1.0,  # Отрицательное количество
                entry=100.0,
                sl=99.0,
                status="open"
            )
    
    def test_position_validation_prices(self):
        """Тест валидации - положительные цены."""
        with pytest.raises(ValidationError):
            Position(
                id="pos_123",
                symbol="BTC/USDT",
                side="long",
                strategy="momentum",
                qty=1.0,
                entry=-100.0,  # Отрицательная цена
                sl=99.0,
                status="open"
            )
    
    def test_position_properties(self):
        """Тест свойств позиции."""
        position = Position(
            id="pos_123",
            symbol="BTC/USDT",
            side="long",
            strategy="momentum",
            qty=1.0,
            entry=100.0,
            sl=99.0,
            status="open",
            pnl_usd=50.0,
            timestamps={"opened_at": 1640995200000}
        )
        
        # Тест is_profitable
        assert position.is_profitable is True
        
        # Тест duration_hours
        expected_duration = (datetime.now().timestamp() * 1000 - 1640995200000) / (1000 * 60 * 60)
        assert abs(position.duration_hours - expected_duration) < 1.0  # В пределах 1 часа
    
    def test_position_duration_with_closed(self):
        """Тест длительности позиции с закрытием."""
        position = Position(
            id="pos_123",
            symbol="BTC/USDT",
            side="long",
            strategy="momentum",
            qty=1.0,
            entry=100.0,
            sl=99.0,
            status="closed",
            timestamps={
                "opened_at": 1640995200000,
                "closed_at": 1640998800000  # +1 час
            }
        )
        
        # Длительность должна быть 1 час
        assert abs(position.duration_hours - 1.0) < 0.1


class TestOrder:
    """Тесты для модели Order."""
    
    def test_order_creation(self):
        """Тест создания ордера."""
        order = Order(
            id="order_123",
            position_id="pos_123",
            symbol="BTC/USDT",
            side="buy",
            order_type="limit",
            qty=1.0,
            price=100.0,
            stop_price=99.0,
            status="open",
            filled_qty=0.5,
            avg_fill_price=100.5,
            fees_usd=2.5,
            timestamps={"created_at": 1640995200000},
            exchange_id="ex_123"
        )
        
        assert order.id == "order_123"
        assert order.position_id == "pos_123"
        assert order.symbol == "BTC/USDT"
        assert order.side == "buy"
        assert order.order_type == "limit"
        assert order.qty == 1.0
        assert order.price == 100.0
        assert order.stop_price == 99.0
        assert order.status == "open"
        assert order.filled_qty == 0.5
        assert order.avg_fill_price == 100.5
        assert order.fees_usd == 2.5
        assert order.timestamps == {"created_at": 1640995200000}
        assert order.exchange_id == "ex_123"
    
    def test_order_validation_quantities(self):
        """Тест валидации - неотрицательные количества."""
        with pytest.raises(ValidationError):
            Order(
                id="order_123",
                symbol="BTC/USDT",
                side="buy",
                order_type="limit",
                qty=-1.0,  # Отрицательное количество
                status="open"
            )
    
    def test_order_properties(self):
        """Тест свойств ордера."""
        order = Order(
            id="order_123",
            symbol="BTC/USDT",
            side="buy",
            order_type="limit",
            qty=1.0,
            status="filled",
            filled_qty=1.0
        )
        
        # Тест is_filled
        assert order.is_filled is True
        
        # Тест remaining_qty
        assert order.remaining_qty == 0.0
    
    def test_order_remaining_qty_partial_fill(self):
        """Тест оставшегося количества при частичном исполнении."""
        order = Order(
            id="order_123",
            symbol="BTC/USDT",
            side="buy",
            order_type="limit",
            qty=1.0,
            status="open",
            filled_qty=0.3
        )
        
        assert order.remaining_qty == 0.7


class TestMarketData:
    """Тесты для модели MarketData."""
    
    def test_market_data_creation(self):
        """Тест создания рыночных данных."""
        l2_depth = L2Depth(
            bid_usd_0_5pct=50000.0,
            ask_usd_0_5pct=50000.0,
            bid_usd_0_3pct=30000.0,
            ask_usd_0_3pct=30000.0,
            spread_bps=5.0,
            imbalance=0.1
        )
        
        market_data = MarketData(
            symbol="BTC/USDT",
            price=50000.0,
            volume_24h_usd=1000000.0,
            oi_usd=500000.0,
            oi_change_24h=0.05,
            trades_per_minute=10.0,
            atr_5m=100.0,
            atr_15m=150.0,
            bb_width_pct=2.0,
            btc_correlation=0.8,
            l2_depth=l2_depth,
            candles_5m=[],
            timestamp=1640995200000
        )
        
        assert market_data.symbol == "BTC/USDT"
        assert market_data.price == 50000.0
        assert market_data.volume_24h_usd == 1000000.0
        assert market_data.oi_usd == 500000.0
        assert market_data.oi_change_24h == 0.05
        assert market_data.trades_per_minute == 10.0
        assert market_data.atr_5m == 100.0
        assert market_data.atr_15m == 150.0
        assert market_data.bb_width_pct == 2.0
        assert market_data.btc_correlation == 0.8
        assert market_data.l2_depth == l2_depth
        assert market_data.candles_5m == []
        assert market_data.timestamp == 1640995200000
    
    def test_market_data_validation_positive_metrics(self):
        """Тест валидации - неотрицательные метрики."""
        with pytest.raises(ValidationError):
            MarketData(
                symbol="BTC/USDT",
                price=50000.0,
                volume_24h_usd=-1000000.0,  # Отрицательный объем
                trades_per_minute=10.0,
                atr_5m=100.0,
                atr_15m=150.0,
                timestamp=1640995200000
            )
    
    def test_market_data_validation_correlation(self):
        """Тест валидации - корреляция между -1 и 1."""
        with pytest.raises(ValidationError):
            MarketData(
                symbol="BTC/USDT",
                price=50000.0,
                volume_24h_usd=1000000.0,
                trades_per_minute=10.0,
                atr_5m=100.0,
                atr_15m=150.0,
                btc_correlation=1.5,  # Вне диапазона [-1, 1]
                timestamp=1640995200000
            )
    
    def test_market_data_properties(self):
        """Тест свойств рыночных данных."""
        market_data = MarketData(
            symbol="BTC/USDT",
            price=50000.0,
            volume_24h_usd=1000000.0,
            trades_per_minute=10.0,
            atr_5m=100.0,
            atr_15m=150.0,
            timestamp=1640995200000
        )
        
        # Тест atr_ratio
        expected_ratio = 150.0 / 100.0
        assert market_data.atr_ratio == expected_ratio
        
        # Тест liquidity_score без L2 данных
        expected_score = min(1.0, 1000000.0 / 100000000)  # volume / 100M
        assert market_data.liquidity_score == expected_score
    
    def test_market_data_liquidity_score_with_l2(self):
        """Тест liquidity_score с L2 данными."""
        l2_depth = L2Depth(
            bid_usd_0_5pct=50000.0,
            ask_usd_0_5pct=50000.0,
            bid_usd_0_3pct=30000.0,
            ask_usd_0_3pct=30000.0,
            spread_bps=5.0,
            imbalance=0.1
        )
        
        market_data = MarketData(
            symbol="BTC/USDT",
            price=50000.0,
            volume_24h_usd=1000000.0,
            trades_per_minute=10.0,
            atr_5m=100.0,
            atr_15m=150.0,
            l2_depth=l2_depth,
            timestamp=1640995200000
        )
        
        # Должен использовать L2 данные для расчета
        assert 0 <= market_data.liquidity_score <= 1


class TestScanResult:
    """Тесты для модели ScanResult."""
    
    def test_scan_result_creation(self):
        """Тест создания результата сканирования."""
        market_data = MarketData(
            symbol="BTC/USDT",
            price=50000.0,
            volume_24h_usd=1000000.0,
            trades_per_minute=10.0,
            atr_5m=100.0,
            atr_15m=150.0,
            timestamp=1640995200000
        )
        
        level = TradingLevel(
            price=50000.0,
            level_type="resistance",
            touch_count=3,
            strength=0.8,
            first_touch_ts=1640995200000,
            last_touch_ts=1640995200000
        )
        
        scan_result = ScanResult(
            symbol="BTC/USDT",
            score=0.8,
            rank=1,
            market_data=market_data,
            filter_results={"min_24h_volume": True, "max_spread": True},
            score_components={"vol_surge": 0.5, "atr_quality": 0.3},
            levels=[level],
            timestamp=1640995200000
        )
        
        assert scan_result.symbol == "BTC/USDT"
        assert scan_result.score == 0.8
        assert scan_result.rank == 1
        assert scan_result.market_data == market_data
        assert scan_result.filter_results == {"min_24h_volume": True, "max_spread": True}
        assert scan_result.score_components == {"vol_surge": 0.5, "atr_quality": 0.3}
        assert scan_result.levels == [level]
        assert scan_result.timestamp == 1640995200000
    
    def test_scan_result_validation_score(self):
        """Тест валидации - разумный скор."""
        market_data = MarketData(
            symbol="BTC/USDT",
            price=50000.0,
            volume_24h_usd=1000000.0,
            trades_per_minute=10.0,
            atr_5m=100.0,
            atr_15m=150.0,
            timestamp=1640995200000
        )
        
        with pytest.raises(ValidationError):
            ScanResult(
                symbol="BTC/USDT",
                score=15.0,  # Вне разумного диапазона
                rank=1,
                market_data=market_data,
                filter_results={},
                score_components={},
                timestamp=1640995200000
            )
    
    def test_scan_result_properties(self):
        """Тест свойств результата сканирования."""
        market_data = MarketData(
            symbol="BTC/USDT",
            price=50000.0,
            volume_24h_usd=1000000.0,
            trades_per_minute=10.0,
            atr_5m=100.0,
            atr_15m=150.0,
            timestamp=1640995200000
        )
        
        # Тест passed_all_filters
        scan_result_passed = ScanResult(
            symbol="BTC/USDT",
            score=0.8,
            rank=1,
            market_data=market_data,
            filter_results={"min_24h_volume": True, "max_spread": True},
            score_components={},
            levels=[],
            timestamp=1640995200000
        )
        assert scan_result_passed.passed_all_filters
        
        scan_result_failed = ScanResult(
            symbol="BTC/USDT",
            score=0.8,
            rank=1,
            market_data=market_data,
            filter_results={"min_24h_volume": True, "max_spread": False},
            score_components={},
            levels=[],
            timestamp=1640995200000
        )
        assert not scan_result_failed.passed_all_filters
    
    def test_scan_result_strongest_level(self):
        """Тест strongest_level."""
        market_data = MarketData(
            symbol="BTC/USDT",
            price=50000.0,
            volume_24h_usd=1000000.0,
            trades_per_minute=10.0,
            atr_5m=100.0,
            atr_15m=150.0,
            timestamp=1640995200000
        )
        
        level1 = TradingLevel(
            price=50000.0,
            level_type="resistance",
            touch_count=3,
            strength=0.6,
            first_touch_ts=1640995200000,
            last_touch_ts=1640995200000
        )
        
        level2 = TradingLevel(
            price=51000.0,
            level_type="support",
            touch_count=5,
            strength=0.9,
            first_touch_ts=1640995200000,
            last_touch_ts=1640995200000
        )
        
        scan_result = ScanResult(
            symbol="BTC/USDT",
            score=0.8,
            rank=1,
            market_data=market_data,
            filter_results={},
            score_components={},
            levels=[level1, level2],
            timestamp=1640995200000
        )
        
        # Должен вернуть уровень с наибольшей силой
        assert scan_result.strongest_level == level2
    
    def test_scan_result_no_levels(self):
        """Тест strongest_level без уровней."""
        market_data = MarketData(
            symbol="BTC/USDT",
            price=50000.0,
            volume_24h_usd=1000000.0,
            trades_per_minute=10.0,
            atr_5m=100.0,
            atr_15m=150.0,
            timestamp=1640995200000
        )
        
        scan_result = ScanResult(
            symbol="BTC/USDT",
            score=0.8,
            rank=1,
            market_data=market_data,
            filter_results={},
            score_components={},
            levels=[],
            timestamp=1640995200000
        )
        
        assert scan_result.strongest_level is None
