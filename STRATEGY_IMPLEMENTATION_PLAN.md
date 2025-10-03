# 🛠️ План имплементации профессиональной торговой стратегии

## 📅 Timeline: 4-6 недель

---

## 🔴 Week 1: Критические улучшения Exit Logic

### Task 1.1: Расширить TP до 4 уровней (2 дня)

#### Файл: `breakout_bot/config/settings.py`

```python
class PositionConfig(BaseModel):
    """Position management configuration."""
    
    # ===== РАСШИРИТЬ ДО 4 УРОВНЕЙ TP =====
    tp1_r: float = Field(..., description="First take profit in R multiples")
    tp1_size_pct: float = Field(..., description="First TP size percentage (e.g., 0.25 = 25%)")
    
    tp2_r: float = Field(..., description="Second take profit in R multiples")
    tp2_size_pct: float = Field(..., description="Second TP size percentage")
    
    tp3_r: float = Field(default=3.0, description="Third take profit in R multiples")
    tp3_size_pct: float = Field(default=0.25, description="Third TP size percentage")
    
    tp4_r: float = Field(default=4.0, description="Fourth take profit in R multiples")
    tp4_size_pct: float = Field(default=0.25, description="Fourth TP size percentage")
    
    # ===== УМНЫЕ ТП =====
    tp_before_round_numbers: bool = Field(
        default=True, 
        description="Place TP before round numbers (0.050, 1.000, etc)"
    )
    tp_before_densities: bool = Field(
        default=True,
        description="Place TP before large order book densities"
    )
    tp_density_offset_bps: float = Field(
        default=5.0,
        description="Offset in bps before density to place TP"
    )
    
    # ===== QUICK EXIT LOGIC =====
    failed_breakout_timeout_s: int = Field(
        default=60,
        description="Seconds to wait for impulse after entry"
    )
    failed_breakout_exit_enabled: bool = Field(
        default=True,
        description="Enable quick exit on failed breakout"
    )
    min_favorable_move_bps: float = Field(
        default=5.0,
        description="Minimum favorable price move required in timeout period"
    )
    
    # ===== EXIT ON ACTIVITY DROP (уже есть) =====
    panic_exit_on_activity_drop: bool = Field(default=True)
    activity_drop_threshold: float = Field(default=0.4)
    
    @field_validator('tp1_size_pct', 'tp2_size_pct', 'tp3_size_pct', 'tp4_size_pct')
    @classmethod
    def validate_tp_sum(cls, v: float, info) -> float:
        """Validate that TP percentages sum to ~1.0"""
        # Note: будет вызван для каждого поля отдельно
        return v
```

#### Файл: `config/presets/breakout_v1.json`

```json
{
  "position_config": {
    "tp1_r": 1.0,
    "tp1_size_pct": 0.25,
    "tp2_r": 2.0,
    "tp2_size_pct": 0.25,
    "tp3_r": 3.0,
    "tp3_size_pct": 0.25,
    "tp4_r": 4.0,
    "tp4_size_pct": 0.25,
    
    "tp_before_round_numbers": true,
    "tp_before_densities": true,
    "tp_density_offset_bps": 5.0,
    
    "failed_breakout_timeout_s": 60,
    "failed_breakout_exit_enabled": true,
    "min_favorable_move_bps": 5.0,
    
    "chandelier_atr_mult": 2.0,
    "max_hold_time_hours": 8,
    "panic_exit_on_activity_drop": true,
    "activity_drop_threshold": 0.4
  }
}
```

---

### Task 1.2: Умное размещение TP (3 дня)

#### Новый файл: `breakout_bot/position/tp_optimizer.py`

```python
"""
Smart Take Profit Optimizer.

Динамически корректирует TP уровни на основе:
- Круглых чисел
- Плотностей в стакане
- Swing levels
"""

import logging
from typing import List, Tuple, Optional
from dataclasses import dataclass

from ..data.models import Position
from ..features.density import DensityDetector, DensityLevel
from ..indicators.levels import LevelDetector, TradingLevel

logger = logging.getLogger(__name__)


@dataclass
class TakeProfitLevel:
    """Take profit level with metadata."""
    price: float
    size_pct: float
    r_multiple: float
    reason: str  # "fixed_r", "round_number", "density", "level"
    priority: int  # Higher = more important


class TakeProfitOptimizer:
    """
    Оптимизирует размещение TP на основе микроструктуры рынка.
    """
    
    def __init__(
        self,
        density_detector: Optional[DensityDetector] = None,
        level_detector: Optional[LevelDetector] = None,
        round_numbers_enabled: bool = True,
        densities_enabled: bool = True,
        density_offset_bps: float = 5.0
    ):
        self.density_detector = density_detector
        self.level_detector = level_detector
        self.round_numbers_enabled = round_numbers_enabled
        self.densities_enabled = densities_enabled
        self.density_offset_bps = density_offset_bps
    
    def optimize_tp_levels(
        self,
        position: Position,
        base_tps: List[Tuple[float, float, float]]  # [(r_mult, size_pct, base_price)]
    ) -> List[TakeProfitLevel]:
        """
        Оптимизировать TP уровни для позиции.
        
        Args:
            position: Текущая позиция
            base_tps: Базовые TP [(r_multiple, size_pct, price)]
        
        Returns:
            List[TakeProfitLevel] - оптимизированные TP
        """
        optimized = []
        
        for r_mult, size_pct, base_price in base_tps:
            # 1. Начинаем с базового уровня
            best_price = base_price
            best_reason = "fixed_r"
            best_priority = 1
            
            # 2. Проверяем круглые числа
            if self.round_numbers_enabled:
                round_price = self._find_nearest_round_number(
                    base_price, 
                    position.side,
                    max_distance_bps=10.0
                )
                if round_price:
                    best_price = round_price
                    best_reason = "round_number"
                    best_priority = 3
            
            # 3. Проверяем плотности в стакане
            if self.densities_enabled and self.density_detector:
                density_price = self._find_tp_before_density(
                    position.symbol,
                    base_price,
                    position.side
                )
                if density_price:
                    # Плотность имеет наивысший приоритет
                    best_price = density_price
                    best_reason = "density"
                    best_priority = 5
            
            optimized.append(TakeProfitLevel(
                price=best_price,
                size_pct=size_pct,
                r_multiple=r_mult,
                reason=best_reason,
                priority=best_priority
            ))
            
            logger.info(
                f"TP{len(optimized)}: {r_mult}R @ {best_price:.6f} "
                f"({size_pct*100:.0f}%) - reason: {best_reason}"
            )
        
        return optimized
    
    def _find_nearest_round_number(
        self,
        price: float,
        side: str,
        max_distance_bps: float = 10.0
    ) -> Optional[float]:
        """
        Найти ближайшее круглое число для TP.
        
        Примеры круглых чисел:
        - 0.050, 0.100, 0.500
        - 1.00, 2.00, 5.00, 10.00
        - 100, 500, 1000
        """
        # Определить масштаб цены
        if price < 0.01:
            steps = [0.001, 0.005, 0.01]
        elif price < 0.1:
            steps = [0.01, 0.05, 0.1]
        elif price < 1.0:
            steps = [0.1, 0.5, 1.0]
        elif price < 10:
            steps = [1.0, 5.0, 10.0]
        elif price < 100:
            steps = [10, 50, 100]
        else:
            steps = [100, 500, 1000]
        
        best_round = None
        min_distance_bps = float('inf')
        
        for step in steps:
            # Найти ближайшее кратное
            if side == 'long':
                # Для long ищем выше текущей цены
                round_candidate = (int(price / step) + 1) * step
            else:
                # Для short ищем ниже
                round_candidate = int(price / step) * step
            
            # Проверить расстояние
            distance_bps = abs((round_candidate - price) / price) * 10000
            
            if distance_bps <= max_distance_bps and distance_bps < min_distance_bps:
                best_round = round_candidate
                min_distance_bps = distance_bps
        
        return best_round
    
    def _find_tp_before_density(
        self,
        symbol: str,
        target_price: float,
        side: str
    ) -> Optional[float]:
        """
        Найти TP перед крупной плотностью в стакане.
        """
        if not self.density_detector:
            return None
        
        densities = self.density_detector.get_densities(symbol)
        if not densities:
            return None
        
        # Фильтровать densities в направлении выхода
        relevant_densities = [
            d for d in densities
            if (side == 'long' and d.side == 'ask' and d.price > target_price * 0.99) or
               (side == 'short' and d.side == 'bid' and d.price < target_price * 1.01)
        ]
        
        if not relevant_densities:
            return None
        
        # Найти ближайшую крупную плотность
        if side == 'long':
            relevant_densities.sort(key=lambda d: d.price)
            nearest = relevant_densities[0]
            # TP чуть ниже плотности
            tp_price = nearest.price * (1 - self.density_offset_bps / 10000)
        else:
            relevant_densities.sort(key=lambda d: d.price, reverse=True)
            nearest = relevant_densities[0]
            # TP чуть выше плотности
            tp_price = nearest.price * (1 + self.density_offset_bps / 10000)
        
        logger.info(
            f"Found density at {nearest.price:.6f} (strength={nearest.strength:.1f}), "
            f"placing TP at {tp_price:.6f}"
        )
        
        return tp_price
    
    def update_tps_on_new_density(
        self,
        position: Position,
        current_tps: List[TakeProfitLevel]
    ) -> List[TakeProfitLevel]:
        """
        Пересчитать TP при появлении новых плотностей.
        
        Вызывается при DensityEvent.NEW или изменении стакана.
        """
        # TODO: Реализовать динамическое обновление
        # Пока возвращаем без изменений
        return current_tps
```

---

### Task 1.3: Интеграция в PositionManager (2 дня)

#### Файл: `breakout_bot/position/manager.py` (модификация)

```python
# Добавить в импорты:
from .tp_optimizer import TakeProfitOptimizer, TakeProfitLevel

class PositionManager:
    def __init__(
        self,
        preset: TradingPreset,
        risk_manager: RiskManager,
        execution_manager: ExecutionManager,
        activity_tracker: Optional[ActivityTracker] = None,
        density_detector: Optional[DensityDetector] = None  # НОВОЕ
    ):
        # ... существующий код ...
        
        # НОВОЕ: Инициализировать TP optimizer
        self.tp_optimizer = TakeProfitOptimizer(
            density_detector=density_detector,
            level_detector=None,  # TODO: передать если есть
            round_numbers_enabled=preset.position_config.tp_before_round_numbers,
            densities_enabled=preset.position_config.tp_before_densities,
            density_offset_bps=preset.position_config.tp_density_offset_bps
        )
    
    async def open_position(
        self,
        signal: Signal,
        market_data: MarketData
    ) -> Position:
        """Открыть позицию (существующий метод - модифицировать)."""
        
        # ... существующий код до расчёта TP ...
        
        # НОВОЕ: Оптимизировать TP уровни
        base_tps = [
            (self.preset.position_config.tp1_r, 
             self.preset.position_config.tp1_size_pct,
             self._calculate_tp_price(entry_price, stop_loss, self.preset.position_config.tp1_r, side)),
            (self.preset.position_config.tp2_r,
             self.preset.position_config.tp2_size_pct,
             self._calculate_tp_price(entry_price, stop_loss, self.preset.position_config.tp2_r, side)),
            (self.preset.position_config.tp3_r,
             self.preset.position_config.tp3_size_pct,
             self._calculate_tp_price(entry_price, stop_loss, self.preset.position_config.tp3_r, side)),
            (self.preset.position_config.tp4_r,
             self.preset.position_config.tp4_size_pct,
             self._calculate_tp_price(entry_price, stop_loss, self.preset.position_config.tp4_r, side)),
        ]
        
        # Создать временную позицию для optimizer
        temp_position = Position(
            id=str(uuid.uuid4()),
            symbol=signal.symbol,
            side=side,
            entry_price=entry_price,
            quantity=quantity,
            stop_loss=stop_loss,
            # ... etc
        )
        
        optimized_tps = self.tp_optimizer.optimize_tp_levels(
            temp_position,
            base_tps
        )
        
        # Использовать оптимизированные TP
        position.meta['tp_levels'] = [
            {
                'price': tp.price,
                'size_pct': tp.size_pct,
                'r_multiple': tp.r_multiple,
                'reason': tp.reason,
                'filled': False
            }
            for tp in optimized_tps
        ]
        
        # ... остальной код ...
    
    def _calculate_tp_price(
        self,
        entry: float,
        stop_loss: float,
        r_multiple: float,
        side: str
    ) -> float:
        """Рассчитать базовую цену TP."""
        risk = abs(entry - stop_loss)
        
        if side == 'long':
            return entry + (risk * r_multiple)
        else:
            return entry - (risk * r_multiple)
```

---

## 🟡 Week 2: Quick Exit Logic

### Task 2.1: Failed Breakout Detector (3 дня)

#### Новый файл: `breakout_bot/position/exit_rules.py`

```python
"""
Exit rules for position management.

Implements:
- Failed breakout detection
- Activity drop exit
- Time-based exit
- Emergency exit scenarios
"""

import time
import logging
from typing import Optional, Tuple
from enum import Enum

from ..data.models import Position, MarketData
from ..features.activity import ActivityTracker


logger = logging.getLogger(__name__)


class ExitReason(str, Enum):
    """Reasons for position exit."""
    STOP_LOSS = "stop_loss"
    TAKE_PROFIT = "take_profit"
    FAILED_BREAKOUT = "failed_breakout"
    ACTIVITY_DROP = "activity_drop"
    TIME_STOP = "time_stop"
    TRAILING_STOP = "trailing_stop"
    EMERGENCY = "emergency"


class ExitRules:
    """
    Правила для различных сценариев выхода.
    """
    
    def __init__(
        self,
        failed_breakout_timeout_s: int = 60,
        min_favorable_move_bps: float = 5.0,
        activity_drop_threshold: float = 0.4,
        time_stop_minutes: Optional[int] = None,
        activity_tracker: Optional[ActivityTracker] = None
    ):
        self.failed_breakout_timeout_s = failed_breakout_timeout_s
        self.min_favorable_move_bps = min_favorable_move_bps
        self.activity_drop_threshold = activity_drop_threshold
        self.time_stop_minutes = time_stop_minutes
        self.activity_tracker = activity_tracker
    
    def check_failed_breakout(
        self,
        position: Position,
        current_price: float
    ) -> Tuple[bool, Optional[str]]:
        """
        Проверить сценарий "failed breakout" (S3).
        
        Логика:
        - Прошло ≥ timeout с момента входа
        - Цена не сдвинулась в нашу сторону на min_favorable_move_bps
        - → Выход с минимальным убытком/нулём
        
        Returns:
            (should_exit, reason)
        """
        entry_time = position.opened_at
        current_time = time.time()
        elapsed = current_time - entry_time
        
        # Проверка только после timeout
        if elapsed < self.failed_breakout_timeout_s:
            return False, None
        
        # Рассчитать движение цены в нашу сторону
        if position.side == 'long':
            favorable_move = (current_price - position.entry_price) / position.entry_price
        else:
            favorable_move = (position.entry_price - current_price) / position.entry_price
        
        favorable_move_bps = favorable_move * 10000
        
        # Если не достигли минимального движения → failed breakout
        if favorable_move_bps < self.min_favorable_move_bps:
            reason = (
                f"Failed breakout: {elapsed:.0f}s elapsed, "
                f"only {favorable_move_bps:.1f} bps favorable move "
                f"(required: {self.min_favorable_move_bps:.1f})"
            )
            logger.warning(f"Position {position.id}: {reason}")
            return True, reason
        
        return False, None
    
    def check_activity_drop(
        self,
        position: Position
    ) -> Tuple[bool, Optional[str]]:
        """
        Проверить сценарий "activity drop" (S4).
        
        Логика:
        - Активность резко упала (>40% от пика)
        - Импульс "закончился"
        - → Выход, не дожидаясь SL
        """
        if not self.activity_tracker:
            return False, None
        
        is_dropping = self.activity_tracker.is_activity_dropping(
            position.symbol,
            drop_frac=self.activity_drop_threshold
        )
        
        if is_dropping:
            activity_metrics = self.activity_tracker.get_metrics(position.symbol)
            reason = (
                f"Activity drop: index={activity_metrics.activity_index:.2f}, "
                f"drop_fraction={activity_metrics.drop_fraction:.2f}"
            )
            logger.warning(f"Position {position.id}: {reason}")
            return True, reason
        
        return False, None
    
    def check_time_stop(
        self,
        position: Position
    ) -> Tuple[bool, Optional[str]]:
        """
        Проверить time-based stop.
        
        Если позиция держится слишком долго без движения.
        """
        if not self.time_stop_minutes:
            return False, None
        
        entry_time = position.opened_at
        current_time = time.time()
        elapsed_minutes = (current_time - entry_time) / 60
        
        if elapsed_minutes >= self.time_stop_minutes:
            reason = f"Time stop: {elapsed_minutes:.0f} minutes elapsed"
            logger.info(f"Position {position.id}: {reason}")
            return True, reason
        
        return False, None
    
    def check_all_exit_conditions(
        self,
        position: Position,
        current_price: float
    ) -> Tuple[bool, Optional[ExitReason], Optional[str]]:
        """
        Проверить все условия выхода (кроме SL/TP).
        
        Returns:
            (should_exit, exit_reason, message)
        """
        # Приоритет 1: Failed breakout (S3)
        should_exit, msg = self.check_failed_breakout(position, current_price)
        if should_exit:
            return True, ExitReason.FAILED_BREAKOUT, msg
        
        # Приоритет 2: Activity drop (S4)
        should_exit, msg = self.check_activity_drop(position)
        if should_exit:
            return True, ExitReason.ACTIVITY_DROP, msg
        
        # Приоритет 3: Time stop
        should_exit, msg = self.check_time_stop(position)
        if should_exit:
            return True, ExitReason.TIME_STOP, msg
        
        return False, None, None
```

#### Интеграция в PositionManager:

```python
# В PositionManager.__init__:
self.exit_rules = ExitRules(
    failed_breakout_timeout_s=preset.position_config.failed_breakout_timeout_s,
    min_favorable_move_bps=preset.position_config.min_favorable_move_bps,
    activity_drop_threshold=preset.position_config.activity_drop_threshold,
    time_stop_minutes=preset.position_config.time_stop_minutes,
    activity_tracker=activity_tracker
)

# В update_position():
async def update_position(self, position: Position, market_data: MarketData):
    """Обновить позицию."""
    
    current_price = market_data.last_price
    
    # 1. НОВОЕ: Проверить quick exit conditions
    should_exit, exit_reason, message = self.exit_rules.check_all_exit_conditions(
        position,
        current_price
    )
    
    if should_exit:
        logger.warning(f"Quick exit triggered: {message}")
        return await self._execute_exit(
            position, 
            current_price, 
            exit_reason,
            urgent=True  # Используем market order для быстрого выхода
        )
    
    # 2. Обычные проверки (SL, TP, trailing)
    # ... существующий код ...
```

---

## 🟡 Week 3: Entry Safety

### Task 3.1: Flat Market Filter (2 дня)

#### Файл: `breakout_bot/config/settings.py` (добавить)

```python
class SignalConfig(BaseModel):
    # ... существующие поля ...
    
    # ===== FLAT MARKET FILTERS =====
    min_atr_pct: float = Field(
        default=0.015,
        description="Minimum ATR/Price ratio to avoid flat markets (1.5%)"
    )
    min_bb_width_pct: float = Field(
        default=0.02,
        description="Minimum Bollinger Bands width to avoid flat markets (2%)"
    )
    require_impulse_confirmation: bool = Field(
        default=True,
        description="Require clear impulse candle before entry"
    )
```

#### Файл: `breakout_bot/signals/strategies.py` (модификация)

```python
def _is_flat_market(
    self,
    candles: List[Candle],
    current_atr: float
) -> bool:
    """
    Детектор flat/ranging market.
    
    Не входим в проторговку!
    """
    if len(candles) < 20:
        return False
    
    current_price = candles[-1].close
    
    # 1. Проверка ATR
    atr_pct = current_atr / current_price
    if atr_pct < self.preset.signal_config.min_atr_pct:
        logger.info(f"Flat market detected: ATR={atr_pct*100:.2f}% < min={self.preset.signal_config.min_atr_pct*100:.2f}%")
        return True
    
    # 2. Проверка Bollinger Bands width
    prices = [c.close for c in candles[-20:]]
    bb_middle = np.mean(prices)
    bb_std = np.std(prices)
    bb_width = (4 * bb_std) / bb_middle  # Upper - Lower normalized
    
    if bb_width < self.preset.signal_config.min_bb_width_pct:
        logger.info(f"Flat market detected: BB width={bb_width*100:.2f}% < min={self.preset.signal_config.min_bb_width_pct*100:.2f}%")
        return True
    
    return False

# В методе _generate_momentum_signal:
def _generate_momentum_signal(...):
    # ... существующий код ...
    
    # НОВОЕ: Проверить flat market
    if self._is_flat_market(candles, current_atr):
        logger.info(f"Skipping {symbol}: flat market detected")
        return None
    
    # ... остальной код ...
```

---

### Task 3.2: Density Safety Check (2 дня)

#### Новый файл: `breakout_bot/signals/entry_safety.py`

```python
"""
Entry safety checks.

Prevents entering into dangerous positions:
- Inside large order book density
- Against strong opposite flow
- In unstable market conditions
"""

import logging
from typing import Optional, Tuple

from ..data.models import Signal, MarketData
from ..features.density import DensityDetector

logger = logging.getLogger(__name__)


class EntrySafetyChecker:
    """
    Проверки безопасности перед входом.
    """
    
    def __init__(
        self,
        density_detector: Optional[DensityDetector] = None,
        avoid_entry_into_density: bool = True,
        density_safety_margin_bps: float = 5.0
    ):
        self.density_detector = density_detector
        self.avoid_entry_into_density = avoid_entry_into_density
        self.density_safety_margin_bps = density_safety_margin_bps
    
    def check_entry_safety(
        self,
        signal: Signal,
        market_data: MarketData
    ) -> Tuple[bool, Optional[str]]:
        """
        Проверить безопасность входа.
        
        Returns:
            (is_safe, rejection_reason)
        """
        # 1. Проверка плотности
        if self.avoid_entry_into_density and self.density_detector:
            is_safe, reason = self._check_density_safety(signal)
            if not is_safe:
                return False, reason
        
        # 2. Можно добавить другие проверки
        # - Spread не слишком широк
        # - Volatility не аномальна
        # - etc.
        
        return True, None
    
    def _check_density_safety(
        self,
        signal: Signal
    ) -> Tuple[bool, Optional[str]]:
        """
        Проверить: не входим ли мы прямо В крупную плотность.
        
        Правило: не входить, если entry price находится внутри
        или очень близко к крупной density.
        """
        densities = self.density_detector.get_densities(signal.symbol)
        if not densities:
            return True, None
        
        entry_price = signal.entry
        
        for density in densities:
            # Проверить только densities на противоположной стороне
            if signal.side == 'long' and density.side == 'bid':
                continue
            if signal.side == 'short' and density.side == 'ask':
                continue
            
            # Рассчитать расстояние до density
            distance_bps = abs((density.price - entry_price) / entry_price) * 10000
            
            if distance_bps < self.density_safety_margin_bps:
                reason = (
                    f"Entry {entry_price:.6f} too close to {density.side} density "
                    f"at {density.price:.6f} (distance={distance_bps:.1f} bps, "
                    f"strength={density.strength:.1f})"
                )
                logger.warning(f"Entry rejected: {reason}")
                return False, reason
        
        return True, None
```

#### Интеграция в SignalManager:

```python
# В SignalManager.__init__:
from ..signals.entry_safety import EntrySafetyChecker

self.entry_safety = EntrySafetyChecker(
    density_detector=density_detector,
    avoid_entry_into_density=True,
    density_safety_margin_bps=5.0
)

# В validate_signal_for_entry():
async def validate_signal_for_entry(self, signal: Signal, market_data: MarketData) -> bool:
    # ... существующие проверки ...
    
    # НОВОЕ: Проверка entry safety
    is_safe, rejection_reason = self.entry_safety.check_entry_safety(signal, market_data)
    if not is_safe:
        logger.warning(f"Signal {signal.id} rejected: {rejection_reason}")
        return False
    
    return True
```

---

## 🟢 Week 4: Position State Machine

### Task 4.1: Реализовать FSM (5 дней)

#### Новый файл: `breakout_bot/position/state_machine.py`

```python
"""
Position State Machine.

Управляет жизненным циклом каждой позиции через чёткие состояния.

Сценарии:
- S1: Успешный пробой → импульс → BE → TP1 → TP2 → TP3 → TP4
- S2: Слабый импульс → BE → выход
- S3: Немедленно против → SL или quick exit
- S4: Активность пропала → выход
"""

import time
import logging
from enum import Enum
from typing import Optional, Callable
from dataclasses import dataclass, field

from ..data.models import Position, MarketData
from ..features.activity import ActivityTracker

logger = logging.getLogger(__name__)


class PositionState(str, Enum):
    """Состояния позиции."""
    WAITING_ENTRY = "waiting_entry"
    ENTERED = "entered"
    IMPULSE_CONFIRMED = "impulse_confirmed"
    BREAKEVEN = "breakeven"
    PARTIAL_TP_1 = "partial_tp_1"
    PARTIAL_TP_2 = "partial_tp_2"
    PARTIAL_TP_3 = "partial_tp_3"
    TRAILING = "trailing"
    FAILING = "failing"
    EXITED = "exited"


@dataclass
class StateTransition:
    """Переход между состояниями."""
    from_state: PositionState
    to_state: PositionState
    timestamp: float
    reason: str
    price: float


class PositionStateMachine:
    """
    FSM для управления состоянием позиции.
    """
    
    def __init__(
        self,
        position: Position,
        activity_tracker: Optional[ActivityTracker] = None,
        impulse_confirmation_bps: float = 10.0,
        impulse_timeout_s: int = 120
    ):
        self.position = position
        self.activity_tracker = activity_tracker
        self.impulse_confirmation_bps = impulse_confirmation_bps
        self.impulse_timeout_s = impulse_timeout_s
        
        # Текущее состояние
        self.state = PositionState.ENTERED
        self.state_entered_at = time.time()
        
        # История переходов
        self.transitions: list[StateTransition] = []
        
        # Метрики для принятия решений
        self.max_favorable_price = position.entry_price
        self.min_favorable_price = position.entry_price
    
    def update(self, market_data: MarketData) -> Optional[str]:
        """
        Обновить состояние на основе рыночных данных.
        
        Returns:
            Optional[str] - action to take ("exit", "move_sl_to_be", etc)
        """
        current_price = market_data.last_price
        
        # Обновить метрики
        if self.position.side == 'long':
            self.max_favorable_price = max(self.max_favorable_price, current_price)
        else:
            self.min_favorable_price = min(self.min_favorable_price, current_price)
        
        # Обработка в зависимости от текущего состояния
        if self.state == PositionState.ENTERED:
            return self._handle_entered_state(current_price)
        
        elif self.state == PositionState.IMPULSE_CONFIRMED:
            return self._handle_impulse_confirmed_state(current_price)
        
        elif self.state == PositionState.BREAKEVEN:
            return self._handle_breakeven_state(current_price)
        
        # ... другие состояния ...
        
        return None
    
    def _handle_entered_state(self, current_price: float) -> Optional[str]:
        """
        Состояние ENTERED: ждём подтверждения импульса.
        
        Сценарии:
        - Цена пошла в нашу сторону >10bps → переход в IMPULSE_CONFIRMED
        - Прошло >2мин без импульса → переход в FAILING (S3)
        - Активность упала → переход в FAILING (S4)
        """
        elapsed = time.time() - self.state_entered_at
        
        # Проверка импульса
        if self.position.side == 'long':
            favorable_move = (current_price - self.position.entry_price) / self.position.entry_price
        else:
            favorable_move = (self.position.entry_price - current_price) / self.position.entry_price
        
        favorable_move_bps = favorable_move * 10000
        
        # Импульс подтверждён!
        if favorable_move_bps >= self.impulse_confirmation_bps:
            self._transition_to(
                PositionState.IMPULSE_CONFIRMED,
                f"Impulse confirmed: {favorable_move_bps:.1f} bps",
                current_price
            )
            return "move_sl_to_be_scheduled"  # Планируем перенос в BE
        
        # Таймаут: нет импульса
        if elapsed > self.impulse_timeout_s:
            self._transition_to(
                PositionState.FAILING,
                f"No impulse after {elapsed:.0f}s",
                current_price
            )
            return "exit_failed_breakout"
        
        # Проверка активности
        if self.activity_tracker:
            is_dropping = self.activity_tracker.is_activity_dropping(
                self.position.symbol,
                drop_frac=0.4
            )
            if is_dropping:
                self._transition_to(
                    PositionState.FAILING,
                    "Activity dropped before impulse",
                    current_price
                )
                return "exit_activity_drop"
        
        return None
    
    def _handle_impulse_confirmed_state(self, current_price: float) -> Optional[str]:
        """
        Состояние IMPULSE_CONFIRMED: импульс есть, переносим в BE.
        
        Сценарий S1: продолжаем движение
        Сценарий S2: если импульс не продолжился, выходим из BE
        """
        # Проверить: достигли ли мы цены для BE
        if self.position.side == 'long':
            move_since_entry = current_price - self.position.entry_price
            if move_since_entry >= self.position.entry_price * 0.0015:  # 0.15% = 15bps
                self._transition_to(
                    PositionState.BREAKEVEN,
                    "Moved to breakeven",
                    current_price
                )
                return "move_sl_to_be_now"
        else:
            move_since_entry = self.position.entry_price - current_price
            if move_since_entry >= self.position.entry_price * 0.0015:
                self._transition_to(
                    PositionState.BREAKEVEN,
                    "Moved to breakeven",
                    current_price
                )
                return "move_sl_to_be_now"
        
        # Проверка активности (S2 или S4)
        if self.activity_tracker:
            is_dropping = self.activity_tracker.is_activity_dropping(
                self.position.symbol,
                drop_frac=0.3
            )
            if is_dropping:
                self._transition_to(
                    PositionState.FAILING,
                    "Activity dropped after impulse (S2)",
                    current_price
                )
                # Выход из BE или с минимальной прибылью
                return "exit_activity_drop_from_be"
        
        return None
    
    def _handle_breakeven_state(self, current_price: float) -> Optional[str]:
        """
        Состояние BREAKEVEN: SL на входе, ждём TP или trailing.
        """
        # В этом состоянии обычная логика TP/trailing
        # FSM просто отслеживает, какой TP был достигнут
        return None
    
    def _transition_to(
        self,
        new_state: PositionState,
        reason: str,
        price: float
    ):
        """Выполнить переход в новое состояние."""
        transition = StateTransition(
            from_state=self.state,
            to_state=new_state,
            timestamp=time.time(),
            reason=reason,
            price=price
        )
        self.transitions.append(transition)
        
        logger.info(
            f"Position {self.position.id}: {self.state} → {new_state} | {reason}"
        )
        
        self.state = new_state
        self.state_entered_at = time.time()
    
    def get_scenario(self) -> str:
        """Определить, какой сценарий (S1-S4) реализовался."""
        if self.state in [PositionState.PARTIAL_TP_1, PositionState.PARTIAL_TP_2, 
                          PositionState.PARTIAL_TP_3, PositionState.TRAILING]:
            return "S1"  # Успешный пробой
        
        if self.state == PositionState.BREAKEVEN and len(self.transitions) > 2:
            # Перешли в BE, но вышли без TP
            return "S2"  # Слабый импульс
        
        if any(t.reason.startswith("No impulse") for t in self.transitions):
            return "S3"  # Сразу против
        
        if any("Activity dropped" in t.reason for t in self.transitions):
            return "S4"  # Активность пропала
        
        return "Unknown"
```

---

## 📊 Testing & Validation (Week 5-6)

### Task 5.1: Unit Tests

```python
# tests/unit/test_tp_optimizer.py
# tests/unit/test_exit_rules.py
# tests/unit/test_entry_safety.py
# tests/unit/test_position_state_machine.py
```

### Task 5.2: Integration Tests

```python
# tests/integration/test_full_trade_cycle_advanced.py

async def test_scenario_s1_successful_breakout():
    """Test S1: Успешный пробой с 4 TP."""
    pass

async def test_scenario_s2_weak_impulse():
    """Test S2: Слабый импульс, выход из BE."""
    pass

async def test_scenario_s3_failed_breakout():
    """Test S3: Сразу против, quick exit."""
    pass

async def test_scenario_s4_activity_drop():
    """Test S4: Активность пропала, panic exit."""
    pass
```

### Task 5.3: Backtesting

```python
# Запустить backtesting на исторических данных
# - Период: последние 3 месяца
# - Инструменты: топ-30 по ликвидности
# - Метрики: win rate, profit factor, max DD, Sharpe ratio

python -m breakout_bot.backtesting.runner \
    --preset advanced_strategy_v1 \
    --start-date 2024-07-01 \
    --end-date 2024-10-01 \
    --symbols BTC/USDT,ETH/USDT,SOL/USDT,... \
    --report-path reports/advanced_strategy_backtest.json
```

---

## 📝 Configuration Example

### Новый пресет: `advanced_scalping_v1.json`

```json
{
  "name": "advanced_scalping_v1",
  "description": "Advanced scalping strategy based on professional trader insights",
  
  "risk_config": {
    "risk_per_trade": 0.005,
    "max_concurrent_positions": 3,
    "daily_risk_limit": 0.02,
    "kill_switch_loss_limit": 0.05,
    "correlation_limit": 0.7,
    "max_consecutive_losses": 5
  },
  
  "liquidity_filters": {
    "min_24h_volume_usd": 200000000.0,
    "max_spread_bps": 5.0,
    "min_depth_usd_0_5pct": 100000.0,
    "min_depth_usd_0_3pct": 50000.0,
    "min_trades_per_minute": 30.0
  },
  
  "volatility_filters": {
    "atr_range_min": 0.015,
    "atr_range_max": 0.08,
    "bb_width_percentile_max": 0.8,
    "volume_surge_1h_min": 1.5,
    "volume_surge_5m_min": 1.3
  },
  
  "signal_config": {
    "momentum_volume_multiplier": 1.5,
    "momentum_body_ratio_min": 0.6,
    "momentum_epsilon": 0.001,
    "retest_pierce_tolerance": 0.0015,
    "retest_max_pierce_atr": 0.3,
    "l2_imbalance_threshold": 1.5,
    "vwap_gap_max_atr": 0.5,
    
    "prelevel_limit_offset_bps": 2.0,
    "enter_on_density_eat_ratio": 0.75,
    "tpm_on_touch_frac": 0.7,
    
    "min_atr_pct": 0.015,
    "min_bb_width_pct": 0.02,
    "require_impulse_confirmation": true
  },
  
  "position_config": {
    "tp1_r": 1.0,
    "tp1_size_pct": 0.25,
    "tp2_r": 2.0,
    "tp2_size_pct": 0.25,
    "tp3_r": 3.0,
    "tp3_size_pct": 0.25,
    "tp4_r": 4.0,
    "tp4_size_pct": 0.25,
    
    "tp_before_round_numbers": true,
    "tp_before_densities": true,
    "tp_density_offset_bps": 5.0,
    
    "failed_breakout_timeout_s": 60,
    "failed_breakout_exit_enabled": true,
    "min_favorable_move_bps": 5.0,
    
    "chandelier_atr_mult": 2.0,
    "max_hold_time_hours": 6,
    "time_stop_minutes": 120,
    
    "panic_exit_on_activity_drop": true,
    "activity_drop_threshold": 0.4,
    
    "add_on_enabled": false,
    "add_on_max_size_pct": 0.0
  },
  
  "scanner_config": {
    "max_candidates": 20,
    "scan_interval_seconds": 60,
    "top_n_by_volume": 100,
    "score_weights": {
      "volume_surge": 0.3,
      "volatility": 0.2,
      "liquidity": 0.2,
      "proximity_to_level": 0.3
    }
  }
}
```

---

## 🎯 Success Metrics

### После Week 1-2:
- [ ] 4 уровня TP работают
- [ ] TP размещаются перед плотностями и круглыми числами
- [ ] Failed breakout detection срабатывает корректно
- [ ] Activity drop exit работает

### После Week 3-4:
- [ ] Flat market filter отсеивает проторговки
- [ ] Entry safety не пускает в плотности
- [ ] Position FSM корректно отслеживает сценарии S1-S4
- [ ] Все unit tests проходят

### После Week 5-6:
- [ ] Backtesting показывает positive expectancy
- [ ] Win rate ≥ 45%
- [ ] Profit factor ≥ 1.5
- [ ] Max drawdown ≤ 15%
- [ ] Paper trading 2 недели успешно

---

## ⚠️ Риски и mitigation

| Риск | Вероятность | Impact | Mitigation |
|------|-------------|--------|------------|
| Overfitting на backtest | Высокая | Высокий | Walk-forward analysis, out-of-sample testing |
| Latency проблемы | Средняя | Высокий | VPS рядом с биржей, WebSocket |
| Slippage больше ожидаемого | Средняя | Средний | Строгие liquidity filters |
| Комиссии съедают прибыль | Средняя | Высокий | Приоритет maker orders, мин. trades |
| Market regime change | Высокая | Высокий | Adaptive parameters, kill switch |

---

## 📚 Next Steps После имплементации

1. **Адаптивные параметры**
   - Автоматическая корректировка на основе market regime
   - Machine learning для классификации паттернов

2. **Multi-timeframe анализ**
   - Подтверждение сигналов на старших TF
   - Фильтрация против главного тренда

3. **Portfolio управление**
   - Корреляция между позициями
   - Sector exposure limits
   - Dynamic position sizing

4. **Мониторинг и алерты**
   - Telegram/Discord уведомления
   - Dashboard в реальном времени
   - Аномалия детекция

---

**Good luck! 🚀**
