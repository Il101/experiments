# 🎛️ Configuration-Driven Implementation Plan

## 🎯 Философия: ВСЁ через пресеты, НЕТ хардкода!

```
┌──────────────────────────────────────────────────────────────┐
│                    DESIGN PRINCIPLES                          │
├──────────────────────────────────────────────────────────────┤
│                                                               │
│  ✅ Каждый параметр → в preset JSON                          │
│  ✅ Код → универсальный, без магических чисел                │
│  ✅ A/B тестирование → просто создать 2 пресета              │
│  ✅ Оптимизация → изменить JSON, не трогая код               │
│  ✅ Production-ready → validate схемой Pydantic              │
│                                                               │
└──────────────────────────────────────────────────────────────┘
```

---

## 📋 PHASE 1: Расширение конфигурационных моделей

### 1.1 Обновить `PositionConfig` (расширенные TP)

**Файл:** `breakout_bot/config/settings.py`

```python
class PositionConfig(BaseModel):
    """Position management configuration."""
    
    # ==================== TAKE PROFIT CONFIGURATION ====================
    
    # Базовые уровни TP
    tp_levels: List[TakeProfitLevel] = Field(
        default_factory=lambda: [
            {"r_multiple": 1.0, "size_pct": 0.25, "enabled": True},
            {"r_multiple": 2.0, "size_pct": 0.25, "enabled": True},
            {"r_multiple": 3.0, "size_pct": 0.25, "enabled": True},
            {"r_multiple": 4.0, "size_pct": 0.25, "enabled": True},
        ],
        description="Take profit levels with R-multiples and position sizes"
    )
    
    # Умное размещение TP
    tp_smart_placement: TakeProfitSmartPlacement = Field(
        default_factory=lambda: TakeProfitSmartPlacement(),
        description="Smart TP placement configuration"
    )
    
    # ==================== STOP LOSS CONFIGURATION ====================
    
    sl_type: Literal["atr", "swing", "fixed_pct"] = Field(
        default="atr",
        description="Stop loss calculation method"
    )
    sl_atr_multiplier: float = Field(
        default=1.5,
        description="ATR multiplier for SL (if sl_type='atr')"
    )
    sl_fixed_pct: float = Field(
        default=0.003,
        description="Fixed percentage for SL (if sl_type='fixed_pct')"
    )
    
    # ==================== BREAKEVEN CONFIGURATION ====================
    
    breakeven_enabled: bool = Field(default=True, description="Enable breakeven move")
    breakeven_trigger_r: float = Field(
        default=0.5,
        description="R-multiple to trigger breakeven move (0.5 = half-way to TP1)"
    )
    breakeven_offset_bps: float = Field(
        default=5.0,
        description="Offset above/below entry in bps for BE stop"
    )
    
    # ==================== TRAILING STOP CONFIGURATION ====================
    
    trailing_enabled: bool = Field(default=True, description="Enable trailing stop")
    trailing_activation_r: float = Field(
        default=1.5,
        description="R-multiple to activate trailing stop"
    )
    trailing_type: Literal["chandelier", "percent", "atr"] = Field(
        default="chandelier",
        description="Trailing stop calculation method"
    )
    chandelier_atr_mult: float = Field(
        default=2.0,
        description="ATR multiplier for Chandelier trailing"
    )
    trailing_percent: float = Field(
        default=0.02,
        description="Percentage for percent-based trailing"
    )
    
    # ==================== EXIT RULES CONFIGURATION ====================
    
    exit_rules: ExitRulesConfig = Field(
        default_factory=lambda: ExitRulesConfig(),
        description="Exit rules configuration"
    )
    
    # ==================== POSITION LIMITS ====================
    
    max_hold_time_hours: int = Field(
        default=8,
        description="Maximum hold time in hours"
    )
    time_stop_enabled: bool = Field(
        default=False,
        description="Enable time-based stop"
    )
    time_stop_minutes: Optional[int] = Field(
        default=None,
        description="Time-based stop in minutes (if enabled)"
    )
    
    # ==================== ADD-ON CONFIGURATION ====================
    
    add_on_enabled: bool = Field(default=False, description="Enable add-on positions")
    add_on_max_size_pct: float = Field(
        default=0.0,
        description="Maximum add-on size as percentage of initial"
    )
    add_on_trigger_r: float = Field(
        default=0.5,
        description="R-multiple to trigger add-on consideration"
    )
    
    @field_validator('tp_levels')
    @classmethod
    def validate_tp_levels_sum(cls, v: List[dict]) -> List[dict]:
        """Validate that enabled TP levels sum to ~1.0"""
        total = sum(tp['size_pct'] for tp in v if tp.get('enabled', True))
        if not 0.95 <= total <= 1.05:
            raise ValueError(f"TP size percentages must sum to ~1.0, got {total}")
        return v


class TakeProfitLevel(BaseModel):
    """Single take profit level configuration."""
    r_multiple: float = Field(..., description="R-multiple for this TP")
    size_pct: float = Field(..., description="Position size to close (0.0-1.0)")
    enabled: bool = Field(default=True, description="Whether this TP is enabled")


class TakeProfitSmartPlacement(BaseModel):
    """Smart TP placement configuration."""
    
    # Round numbers
    round_numbers_enabled: bool = Field(
        default=True,
        description="Adjust TP to round numbers"
    )
    round_numbers_max_distance_bps: float = Field(
        default=10.0,
        description="Maximum distance to round number in bps"
    )
    round_numbers_priority: int = Field(
        default=3,
        description="Priority (1-5, higher = more important)"
    )
    
    # Densities
    densities_enabled: bool = Field(
        default=True,
        description="Adjust TP based on order book densities"
    )
    densities_offset_bps: float = Field(
        default=5.0,
        description="Offset before density in bps"
    )
    densities_min_strength: float = Field(
        default=3.0,
        description="Minimum density strength to consider"
    )
    densities_priority: int = Field(
        default=5,
        description="Priority (1-5, higher = more important)"
    )
    
    # Levels
    levels_enabled: bool = Field(
        default=True,
        description="Adjust TP based on swing levels"
    )
    levels_offset_bps: float = Field(
        default=3.0,
        description="Offset before level in bps"
    )
    levels_priority: int = Field(
        default=4,
        description="Priority (1-5, higher = more important)"
    )
    
    # Dynamic adjustment
    dynamic_adjustment_enabled: bool = Field(
        default=True,
        description="Allow dynamic TP adjustment during position lifetime"
    )
    dynamic_update_interval_s: int = Field(
        default=30,
        description="How often to check for TP adjustments (seconds)"
    )


class ExitRulesConfig(BaseModel):
    """Configuration for exit rules."""
    
    # Failed breakout
    failed_breakout_enabled: bool = Field(
        default=True,
        description="Enable failed breakout detection"
    )
    failed_breakout_timeout_s: int = Field(
        default=60,
        description="Seconds to wait for favorable move"
    )
    failed_breakout_min_move_bps: float = Field(
        default=5.0,
        description="Minimum favorable move required in bps"
    )
    failed_breakout_exit_type: Literal["market", "limit"] = Field(
        default="market",
        description="Order type for failed breakout exit"
    )
    
    # Activity drop
    activity_drop_enabled: bool = Field(
        default=True,
        description="Enable activity drop detection"
    )
    activity_drop_threshold: float = Field(
        default=0.4,
        description="Activity drop threshold (0.4 = 40% drop)"
    )
    activity_drop_lookback_s: int = Field(
        default=120,
        description="Lookback period for activity comparison"
    )
    activity_drop_exit_type: Literal["market", "limit"] = Field(
        default="limit",
        description="Order type for activity drop exit"
    )
    
    # Panic exit conditions
    panic_exit_on_spike_enabled: bool = Field(
        default=False,
        description="Exit on sudden adverse spike"
    )
    panic_spike_threshold_bps: float = Field(
        default=50.0,
        description="Spike size to trigger panic exit in bps"
    )
    
    # Weak impulse
    weak_impulse_enabled: bool = Field(
        default=True,
        description="Exit on weak impulse after breakeven"
    )
    weak_impulse_min_r: float = Field(
        default=1.0,
        description="Minimum R to avoid weak impulse classification"
    )
    weak_impulse_timeout_s: int = Field(
        default=300,
        description="Time in BE before declaring weak impulse"
    )
```

---

### 1.2 Добавить `EntryRulesConfig`

**Файл:** `breakout_bot/config/settings.py` (продолжение)

```python
class SignalConfig(BaseModel):
    """Signal generation configuration."""
    
    # ==================== EXISTING FIELDS (оставить как есть) ====================
    momentum_volume_multiplier: float = Field(...)
    momentum_body_ratio_min: float = Field(...)
    # ... etc
    
    # ==================== ENTRY RULES CONFIGURATION ====================
    
    entry_rules: EntryRulesConfig = Field(
        default_factory=lambda: EntryRulesConfig(),
        description="Entry validation rules"
    )
    
    # ==================== MARKET QUALITY FILTERS ====================
    
    market_quality: MarketQualityConfig = Field(
        default_factory=lambda: MarketQualityConfig(),
        description="Market quality filters"
    )


class EntryRulesConfig(BaseModel):
    """Configuration for entry validation rules."""
    
    # Density safety
    avoid_entry_into_density: bool = Field(
        default=True,
        description="Avoid entering into large order book density"
    )
    density_safety_margin_bps: float = Field(
        default=5.0,
        description="Minimum distance from density in bps"
    )
    density_safety_min_strength: float = Field(
        default=3.0,
        description="Minimum density strength to avoid"
    )
    
    # Entry timing
    entry_on_density_eaten_enabled: bool = Field(
        default=True,
        description="Enter when density is being eaten"
    )
    entry_density_eaten_ratio: float = Field(
        default=0.75,
        description="Density eaten ratio to trigger entry (0.75 = 75%)"
    )
    entry_density_eaten_speed_min: float = Field(
        default=0.1,
        description="Minimum eating speed (fraction per second)"
    )
    
    # Pre-level entry
    prelevel_entry_enabled: bool = Field(
        default=True,
        description="Enter before level with limit order"
    )
    prelevel_offset_bps: float = Field(
        default=2.0,
        description="Offset before level in bps"
    )
    prelevel_max_distance_bps: float = Field(
        default=10.0,
        description="Maximum distance from level to consider pre-level entry"
    )
    
    # Confirmation requirements
    require_volume_confirmation: bool = Field(
        default=True,
        description="Require volume surge before entry"
    )
    volume_confirmation_multiplier: float = Field(
        default=1.5,
        description="Volume must be X times average"
    )
    
    require_momentum_candle: bool = Field(
        default=True,
        description="Require clear momentum candle"
    )
    momentum_body_ratio_min: float = Field(
        default=0.6,
        description="Minimum candle body ratio"
    )


class MarketQualityConfig(BaseModel):
    """Configuration for market quality filters."""
    
    # Flat market detection
    flat_market_filter_enabled: bool = Field(
        default=True,
        description="Filter out flat/ranging markets"
    )
    flat_market_atr_min_pct: float = Field(
        default=0.015,
        description="Minimum ATR/Price ratio (1.5%)"
    )
    flat_market_bb_width_min_pct: float = Field(
        default=0.02,
        description="Minimum Bollinger Bands width (2%)"
    )
    flat_market_lookback_candles: int = Field(
        default=20,
        description="Candles to analyze for flat market"
    )
    
    # Consolidation detection
    consolidation_filter_enabled: bool = Field(
        default=True,
        description="Filter entries during consolidation"
    )
    consolidation_range_threshold_pct: float = Field(
        default=0.02,
        description="Max price range for consolidation (2%)"
    )
    consolidation_min_candles: int = Field(
        default=5,
        description="Minimum candles to declare consolidation"
    )
    
    # Spread quality
    max_spread_for_entry_bps: float = Field(
        default=10.0,
        description="Maximum spread to allow entry in bps"
    )
    
    # Activity requirements
    min_activity_index: float = Field(
        default=1.0,
        description="Minimum activity index for entry"
    )
    activity_increasing_required: bool = Field(
        default=False,
        description="Require increasing activity for entry"
    )
```

---

### 1.3 Добавить `FSMConfig`

**Файл:** `breakout_bot/config/settings.py` (продолжение)

```python
class PositionConfig(BaseModel):
    # ... existing fields ...
    
    # ==================== FSM CONFIGURATION ====================
    
    fsm_enabled: bool = Field(
        default=True,
        description="Enable per-position state machine"
    )
    fsm_config: FSMConfig = Field(
        default_factory=lambda: FSMConfig(),
        description="FSM behavior configuration"
    )


class FSMConfig(BaseModel):
    """Configuration for Position State Machine."""
    
    # State: ENTERED → IMPULSE_CONFIRMED
    impulse_confirmation_bps: float = Field(
        default=10.0,
        description="Favorable move required to confirm impulse (bps)"
    )
    impulse_timeout_s: int = Field(
        default=120,
        description="Time to wait for impulse before declaring failure"
    )
    
    # State: IMPULSE_CONFIRMED → BREAKEVEN
    breakeven_trigger_r: float = Field(
        default=0.5,
        description="R-multiple to trigger breakeven move"
    )
    breakeven_immediate: bool = Field(
        default=False,
        description="Move to BE immediately after impulse confirmation"
    )
    
    # State: BREAKEVEN → TRAILING
    trailing_activation_r: float = Field(
        default=1.5,
        description="R-multiple to activate trailing stop"
    )
    
    # Scenario detection
    scenario_s2_enabled: bool = Field(
        default=True,
        description="Enable S2 scenario (weak impulse exit from BE)"
    )
    scenario_s2_timeout_s: int = Field(
        default=300,
        description="Time in BE before S2 exit consideration"
    )
    scenario_s2_min_activity_index: float = Field(
        default=1.5,
        description="Minimum activity to avoid S2 exit"
    )
    
    scenario_s3_enabled: bool = Field(
        default=True,
        description="Enable S3 scenario (immediate failure)"
    )
    
    scenario_s4_enabled: bool = Field(
        default=True,
        description="Enable S4 scenario (activity drop)"
    )
    
    # Logging
    log_state_transitions: bool = Field(
        default=True,
        description="Log all FSM state transitions"
    )
    log_scenario_detection: bool = Field(
        default=True,
        description="Log detected scenarios (S1-S4)"
    )
```

---

## 📋 PHASE 2: Реализация универсальных компонентов

### 2.1 Универсальный TakeProfitOptimizer

**Файл:** `breakout_bot/position/tp_optimizer.py`

```python
"""
Universal Take Profit Optimizer.

Размещает TP на основе конфигурации, БЕЗ хардкода параметров.
"""

import logging
from typing import List, Tuple, Optional
from dataclasses import dataclass

from ..config.settings import (
    TakeProfitSmartPlacement,
    TakeProfitLevel as TPLevelConfig
)
from ..data.models import Position
from ..features.density import DensityDetector, DensityLevel
from ..indicators.levels import LevelDetector, TradingLevel

logger = logging.getLogger(__name__)


@dataclass
class OptimizedTPLevel:
    """Optimized TP level with metadata."""
    price: float
    size_pct: float
    r_multiple: float
    reason: str
    priority: int
    original_price: float


class TakeProfitOptimizer:
    """
    Универсальный оптимизатор TP.
    
    Все параметры берутся из конфигурации, НЕТ магических чисел.
    """
    
    def __init__(
        self,
        config: TakeProfitSmartPlacement,
        density_detector: Optional[DensityDetector] = None,
        level_detector: Optional[LevelDetector] = None
    ):
        """
        Initialize optimizer with configuration.
        
        Args:
            config: Smart placement configuration from preset
            density_detector: Optional density detector
            level_detector: Optional level detector
        """
        self.config = config
        self.density_detector = density_detector
        self.level_detector = level_detector
        
        logger.info(
            f"TakeProfitOptimizer initialized: "
            f"round_numbers={config.round_numbers_enabled}, "
            f"densities={config.densities_enabled}, "
            f"levels={config.levels_enabled}"
        )
    
    def optimize_tp_levels(
        self,
        position: Position,
        base_tps: List[TPLevelConfig]
    ) -> List[OptimizedTPLevel]:
        """
        Оптимизировать TP уровни для позиции.
        
        Args:
            position: Текущая позиция
            base_tps: Базовые TP из конфигурации
        
        Returns:
            List оптимизированных TP
        """
        optimized = []
        
        for tp_config in base_tps:
            if not tp_config.enabled:
                continue
            
            # Рассчитать базовую цену TP
            base_price = self._calculate_base_tp_price(
                position,
                tp_config.r_multiple
            )
            
            # Применить smart placement
            optimized_price, reason, priority = self._apply_smart_placement(
                position.symbol,
                base_price,
                position.side,
                tp_config.r_multiple
            )
            
            optimized.append(OptimizedTPLevel(
                price=optimized_price,
                size_pct=tp_config.size_pct,
                r_multiple=tp_config.r_multiple,
                reason=reason,
                priority=priority,
                original_price=base_price
            ))
            
            logger.info(
                f"TP{len(optimized)}: {tp_config.r_multiple}R @ "
                f"{optimized_price:.6f} ({tp_config.size_pct*100:.0f}%) "
                f"[{reason}] (was {base_price:.6f})"
            )
        
        return optimized
    
    def _calculate_base_tp_price(
        self,
        position: Position,
        r_multiple: float
    ) -> float:
        """Рассчитать базовую цену TP без оптимизации."""
        risk = abs(position.entry_price - position.stop_loss)
        
        if position.side == 'long':
            return position.entry_price + (risk * r_multiple)
        else:
            return position.entry_price - (risk * r_multiple)
    
    def _apply_smart_placement(
        self,
        symbol: str,
        base_price: float,
        side: str,
        r_multiple: float
    ) -> Tuple[float, str, int]:
        """
        Применить smart placement на основе конфигурации.
        
        Returns:
            (optimized_price, reason, priority)
        """
        candidates = [
            (base_price, "fixed_r", 1)  # Baseline
        ]
        
        # 1. Check round numbers (если включено)
        if self.config.round_numbers_enabled:
            round_price = self._find_nearest_round_number(
                base_price,
                side,
                self.config.round_numbers_max_distance_bps
            )
            if round_price:
                candidates.append((
                    round_price,
                    "round_number",
                    self.config.round_numbers_priority
                ))
        
        # 2. Check densities (если включено)
        if self.config.densities_enabled and self.density_detector:
            density_price = self._find_tp_before_density(
                symbol,
                base_price,
                side
            )
            if density_price:
                candidates.append((
                    density_price,
                    "density",
                    self.config.densities_priority
                ))
        
        # 3. Check levels (если включено)
        if self.config.levels_enabled and self.level_detector:
            level_price = self._find_tp_before_level(
                symbol,
                base_price,
                side
            )
            if level_price:
                candidates.append((
                    level_price,
                    "swing_level",
                    self.config.levels_priority
                ))
        
        # Выбрать кандидата с максимальным приоритетом
        best = max(candidates, key=lambda x: x[2])
        return best
    
    def _find_nearest_round_number(
        self,
        price: float,
        side: str,
        max_distance_bps: float
    ) -> Optional[float]:
        """Найти ближайшее круглое число (из конфигурации)."""
        # Определить масштаб
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
            if side == 'long':
                round_candidate = (int(price / step) + 1) * step
            else:
                round_candidate = int(price / step) * step
            
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
        """Найти TP перед плотностью (параметры из конфигурации)."""
        if not self.density_detector:
            return None
        
        densities = self.density_detector.get_densities(symbol)
        if not densities:
            return None
        
        # Фильтровать по strength из конфигурации
        relevant_densities = [
            d for d in densities
            if d.strength >= self.config.densities_min_strength and
            ((side == 'long' and d.side == 'ask' and d.price > target_price * 0.99) or
             (side == 'short' and d.side == 'bid' and d.price < target_price * 1.01))
        ]
        
        if not relevant_densities:
            return None
        
        # Найти ближайшую
        if side == 'long':
            relevant_densities.sort(key=lambda d: d.price)
            nearest = relevant_densities[0]
            # Offset из конфигурации
            tp_price = nearest.price * (1 - self.config.densities_offset_bps / 10000)
        else:
            relevant_densities.sort(key=lambda d: d.price, reverse=True)
            nearest = relevant_densities[0]
            tp_price = nearest.price * (1 + self.config.densities_offset_bps / 10000)
        
        logger.info(
            f"Found density at {nearest.price:.6f} (strength={nearest.strength:.1f}), "
            f"placing TP at {tp_price:.6f} (offset={self.config.densities_offset_bps}bps)"
        )
        
        return tp_price
    
    def _find_tp_before_level(
        self,
        symbol: str,
        target_price: float,
        side: str
    ) -> Optional[float]:
        """Найти TP перед swing level (параметры из конфигурации)."""
        # TODO: Реализовать при наличии level_detector
        return None
    
    def update_tps_dynamically(
        self,
        position: Position,
        current_tps: List[OptimizedTPLevel]
    ) -> Optional[List[OptimizedTPLevel]]:
        """
        Динамически обновить TP при изменении рынка.
        
        Вызывается периодически, если dynamic_adjustment_enabled=True.
        """
        if not self.config.dynamic_adjustment_enabled:
            return None
        
        # TODO: Реализовать логику обновления
        # - Проверить новые densities
        # - Сдвинуть TP если появились лучшие уровни
        
        return None
```

---

### 2.2 Универсальный ExitRulesChecker

**Файл:** `breakout_bot/position/exit_rules.py`

```python
"""
Universal Exit Rules Checker.

Проверяет условия выхода на основе конфигурации.
"""

import time
import logging
from typing import Optional, Tuple
from enum import Enum

from ..config.settings import ExitRulesConfig
from ..data.models import Position, MarketData
from ..features.activity import ActivityTracker


logger = logging.getLogger(__name__)


class ExitReason(str, Enum):
    """Exit reasons."""
    STOP_LOSS = "stop_loss"
    TAKE_PROFIT = "take_profit"
    FAILED_BREAKOUT = "failed_breakout"
    ACTIVITY_DROP = "activity_drop"
    WEAK_IMPULSE = "weak_impulse"
    TIME_STOP = "time_stop"
    TRAILING_STOP = "trailing_stop"
    PANIC_SPIKE = "panic_spike"
    EMERGENCY = "emergency"


class ExitRulesChecker:
    """
    Универсальный checker для exit rules.
    
    ВСЕ параметры из конфигурации!
    """
    
    def __init__(
        self,
        config: ExitRulesConfig,
        activity_tracker: Optional[ActivityTracker] = None
    ):
        """
        Initialize with configuration.
        
        Args:
            config: Exit rules configuration from preset
            activity_tracker: Optional activity tracker
        """
        self.config = config
        self.activity_tracker = activity_tracker
        
        logger.info(
            f"ExitRulesChecker initialized: "
            f"failed_breakout={config.failed_breakout_enabled}, "
            f"activity_drop={config.activity_drop_enabled}, "
            f"weak_impulse={config.weak_impulse_enabled}"
        )
    
    def check_all_exit_conditions(
        self,
        position: Position,
        current_price: float
    ) -> Tuple[bool, Optional[ExitReason], Optional[str]]:
        """
        Проверить все условия выхода (параметры из config).
        
        Returns:
            (should_exit, exit_reason, message)
        """
        # Priority 1: Failed breakout
        if self.config.failed_breakout_enabled:
            should_exit, msg = self._check_failed_breakout(position, current_price)
            if should_exit:
                return True, ExitReason.FAILED_BREAKOUT, msg
        
        # Priority 2: Activity drop
        if self.config.activity_drop_enabled:
            should_exit, msg = self._check_activity_drop(position)
            if should_exit:
                return True, ExitReason.ACTIVITY_DROP, msg
        
        # Priority 3: Panic spike
        if self.config.panic_exit_on_spike_enabled:
            should_exit, msg = self._check_panic_spike(position, current_price)
            if should_exit:
                return True, ExitReason.PANIC_SPIKE, msg
        
        # Priority 4: Weak impulse
        if self.config.weak_impulse_enabled:
            should_exit, msg = self._check_weak_impulse(position, current_price)
            if should_exit:
                return True, ExitReason.WEAK_IMPULSE, msg
        
        return False, None, None
    
    def _check_failed_breakout(
        self,
        position: Position,
        current_price: float
    ) -> Tuple[bool, Optional[str]]:
        """Check failed breakout (параметры из config)."""
        entry_time = position.opened_at
        current_time = time.time()
        elapsed = current_time - entry_time
        
        # Timeout из конфигурации
        if elapsed < self.config.failed_breakout_timeout_s:
            return False, None
        
        # Рассчитать движение
        if position.side == 'long':
            favorable_move = (current_price - position.entry_price) / position.entry_price
        else:
            favorable_move = (position.entry_price - current_price) / position.entry_price
        
        favorable_move_bps = favorable_move * 10000
        
        # Min move из конфигурации
        if favorable_move_bps < self.config.failed_breakout_min_move_bps:
            reason = (
                f"Failed breakout: {elapsed:.0f}s elapsed, "
                f"only {favorable_move_bps:.1f} bps favorable move "
                f"(required: {self.config.failed_breakout_min_move_bps:.1f})"
            )
            logger.warning(f"Position {position.id}: {reason}")
            return True, reason
        
        return False, None
    
    def _check_activity_drop(
        self,
        position: Position
    ) -> Tuple[bool, Optional[str]]:
        """Check activity drop (параметры из config)."""
        if not self.activity_tracker:
            return False, None
        
        is_dropping = self.activity_tracker.is_activity_dropping(
            position.symbol,
            drop_frac=self.config.activity_drop_threshold,  # Из конфигурации!
            lookback_s=self.config.activity_drop_lookback_s  # Из конфигурации!
        )
        
        if is_dropping:
            activity_metrics = self.activity_tracker.get_metrics(position.symbol)
            reason = (
                f"Activity drop: index={activity_metrics.activity_index:.2f}, "
                f"drop_fraction={activity_metrics.drop_fraction:.2f} "
                f"(threshold={self.config.activity_drop_threshold:.2f})"
            )
            logger.warning(f"Position {position.id}: {reason}")
            return True, reason
        
        return False, None
    
    def _check_panic_spike(
        self,
        position: Position,
        current_price: float
    ) -> Tuple[bool, Optional[str]]:
        """Check panic spike (параметры из config)."""
        if position.side == 'long':
            adverse_move = (position.entry_price - current_price) / position.entry_price
        else:
            adverse_move = (current_price - position.entry_price) / position.entry_price
        
        adverse_move_bps = adverse_move * 10000
        
        # Threshold из конфигурации
        if adverse_move_bps > self.config.panic_spike_threshold_bps:
            reason = (
                f"Panic spike: {adverse_move_bps:.1f} bps adverse move "
                f"(threshold={self.config.panic_spike_threshold_bps:.1f})"
            )
            logger.error(f"Position {position.id}: {reason}")
            return True, reason
        
        return False, None
    
    def _check_weak_impulse(
        self,
        position: Position,
        current_price: float
    ) -> Tuple[bool, Optional[str]]:
        """Check weak impulse after BE (параметры из config)."""
        # Проверяем только если позиция в BE
        if position.stop_loss != position.entry_price:
            return False, None
        
        entry_time = position.opened_at
        current_time = time.time()
        elapsed = current_time - entry_time
        
        # Timeout из конфигурации
        if elapsed < self.config.weak_impulse_timeout_s:
            return False, None
        
        # Рассчитать текущий R
        risk = abs(position.entry_price - position.meta.get('original_stop_loss', position.stop_loss))
        if position.side == 'long':
            current_r = (current_price - position.entry_price) / risk if risk > 0 else 0
        else:
            current_r = (position.entry_price - current_price) / risk if risk > 0 else 0
        
        # Min R из конфигурации
        if current_r < self.config.weak_impulse_min_r:
            reason = (
                f"Weak impulse: {elapsed:.0f}s in BE, only {current_r:.2f}R "
                f"(required: {self.config.weak_impulse_min_r:.2f}R)"
            )
            logger.info(f"Position {position.id}: {reason}")
            return True, reason
        
        return False, None
    
    def get_exit_order_type(self, exit_reason: ExitReason) -> str:
        """Получить тип ордера для выхода (из конфигурации)."""
        if exit_reason == ExitReason.FAILED_BREAKOUT:
            return self.config.failed_breakout_exit_type
        elif exit_reason == ExitReason.ACTIVITY_DROP:
            return self.config.activity_drop_exit_type
        elif exit_reason == ExitReason.PANIC_SPIKE:
            return "market"  # Всегда market для panic
        else:
            return "market"  # Default
```

---

## 📋 PHASE 3: Примеры пресетов

### 3.1 Консервативный пресет

**Файл:** `config/presets/video_strategy_conservative.json`

```json
{
  "name": "video_strategy_conservative",
  "description": "Conservative implementation of video strategy - strict filters",
  
  "risk_config": {
    "risk_per_trade": 0.003,
    "max_concurrent_positions": 1,
    "daily_risk_limit": 0.01,
    "kill_switch_loss_limit": 0.03,
    "correlation_limit": 0.7,
    "max_consecutive_losses": 3
  },
  
  "liquidity_filters": {
    "min_24h_volume_usd": 250000000.0,
    "max_spread_bps": 3.0,
    "min_depth_usd_0_5pct": 150000.0,
    "min_depth_usd_0_3pct": 75000.0,
    "min_trades_per_minute": 40.0
  },
  
  "signal_config": {
    "entry_rules": {
      "avoid_entry_into_density": true,
      "density_safety_margin_bps": 8.0,
      "density_safety_min_strength": 4.0,
      "entry_on_density_eaten_enabled": true,
      "entry_density_eaten_ratio": 0.8,
      "prelevel_entry_enabled": true,
      "prelevel_offset_bps": 3.0,
      "require_volume_confirmation": true,
      "volume_confirmation_multiplier": 2.0,
      "require_momentum_candle": true
    },
    "market_quality": {
      "flat_market_filter_enabled": true,
      "flat_market_atr_min_pct": 0.02,
      "flat_market_bb_width_min_pct": 0.025,
      "consolidation_filter_enabled": true,
      "max_spread_for_entry_bps": 5.0,
      "min_activity_index": 1.5,
      "activity_increasing_required": true
    }
  },
  
  "position_config": {
    "tp_levels": [
      {"r_multiple": 1.0, "size_pct": 0.25, "enabled": true},
      {"r_multiple": 2.0, "size_pct": 0.25, "enabled": true},
      {"r_multiple": 3.0, "size_pct": 0.25, "enabled": true},
      {"r_multiple": 4.0, "size_pct": 0.25, "enabled": true}
    ],
    "tp_smart_placement": {
      "round_numbers_enabled": true,
      "round_numbers_max_distance_bps": 8.0,
      "round_numbers_priority": 3,
      "densities_enabled": true,
      "densities_offset_bps": 6.0,
      "densities_min_strength": 4.0,
      "densities_priority": 5,
      "levels_enabled": true,
      "levels_offset_bps": 4.0,
      "levels_priority": 4,
      "dynamic_adjustment_enabled": true,
      "dynamic_update_interval_s": 30
    },
    "sl_type": "atr",
    "sl_atr_multiplier": 1.8,
    "breakeven_enabled": true,
    "breakeven_trigger_r": 0.4,
    "breakeven_offset_bps": 8.0,
    "trailing_enabled": true,
    "trailing_activation_r": 2.0,
    "trailing_type": "chandelier",
    "chandelier_atr_mult": 2.5,
    "exit_rules": {
      "failed_breakout_enabled": true,
      "failed_breakout_timeout_s": 90,
      "failed_breakout_min_move_bps": 8.0,
      "failed_breakout_exit_type": "limit",
      "activity_drop_enabled": true,
      "activity_drop_threshold": 0.35,
      "activity_drop_lookback_s": 180,
      "activity_drop_exit_type": "limit",
      "panic_exit_on_spike_enabled": true,
      "panic_spike_threshold_bps": 40.0,
      "weak_impulse_enabled": true,
      "weak_impulse_min_r": 1.2,
      "weak_impulse_timeout_s": 400
    },
    "max_hold_time_hours": 6,
    "fsm_enabled": true,
    "fsm_config": {
      "impulse_confirmation_bps": 12.0,
      "impulse_timeout_s": 150,
      "breakeven_trigger_r": 0.4,
      "trailing_activation_r": 2.0,
      "scenario_s2_enabled": true,
      "scenario_s2_timeout_s": 400,
      "scenario_s3_enabled": true,
      "scenario_s4_enabled": true,
      "log_state_transitions": true
    }
  }
}
```

---

### 3.2 Агрессивный пресет

**Файл:** `config/presets/video_strategy_aggressive.json`

```json
{
  "name": "video_strategy_aggressive",
  "description": "Aggressive implementation - more entries, faster exits",
  
  "risk_config": {
    "risk_per_trade": 0.006,
    "max_concurrent_positions": 3,
    "daily_risk_limit": 0.025,
    "kill_switch_loss_limit": 0.05,
    "correlation_limit": 0.8
  },
  
  "liquidity_filters": {
    "min_24h_volume_usd": 200000000.0,
    "max_spread_bps": 5.0,
    "min_depth_usd_0_3pct": 50000.0,
    "min_trades_per_minute": 25.0
  },
  
  "signal_config": {
    "entry_rules": {
      "avoid_entry_into_density": true,
      "density_safety_margin_bps": 3.0,
      "entry_on_density_eaten_enabled": true,
      "entry_density_eaten_ratio": 0.65,
      "require_volume_confirmation": true,
      "volume_confirmation_multiplier": 1.3
    },
    "market_quality": {
      "flat_market_filter_enabled": true,
      "flat_market_atr_min_pct": 0.012,
      "flat_market_bb_width_min_pct": 0.015,
      "min_activity_index": 0.8
    }
  },
  
  "position_config": {
    "tp_levels": [
      {"r_multiple": 0.8, "size_pct": 0.3, "enabled": true},
      {"r_multiple": 1.5, "size_pct": 0.3, "enabled": true},
      {"r_multiple": 2.5, "size_pct": 0.2, "enabled": true},
      {"r_multiple": 4.0, "size_pct": 0.2, "enabled": true}
    ],
    "tp_smart_placement": {
      "round_numbers_enabled": true,
      "round_numbers_max_distance_bps": 15.0,
      "densities_enabled": true,
      "densities_offset_bps": 3.0,
      "densities_min_strength": 2.5,
      "densities_priority": 5
    },
    "sl_atr_multiplier": 1.2,
    "breakeven_trigger_r": 0.3,
    "trailing_activation_r": 1.0,
    "chandelier_atr_mult": 1.5,
    "exit_rules": {
      "failed_breakout_enabled": true,
      "failed_breakout_timeout_s": 45,
      "failed_breakout_min_move_bps": 3.0,
      "failed_breakout_exit_type": "market",
      "activity_drop_enabled": true,
      "activity_drop_threshold": 0.45,
      "activity_drop_exit_type": "market"
    },
    "fsm_config": {
      "impulse_confirmation_bps": 6.0,
      "impulse_timeout_s": 90,
      "breakeven_trigger_r": 0.3
    }
  }
}
```

---

### 3.3 Scalping пресет (быстрые сделки)

**Файл:** `config/presets/video_strategy_scalping.json`

```json
{
  "name": "video_strategy_scalping",
  "description": "Fast scalping - many small wins",
  
  "position_config": {
    "tp_levels": [
      {"r_multiple": 0.5, "size_pct": 0.4, "enabled": true},
      {"r_multiple": 1.0, "size_pct": 0.3, "enabled": true},
      {"r_multiple": 1.5, "size_pct": 0.2, "enabled": true},
      {"r_multiple": 2.5, "size_pct": 0.1, "enabled": true}
    ],
    "tp_smart_placement": {
      "densities_enabled": true,
      "densities_offset_bps": 2.0,
      "densities_priority": 5
    },
    "breakeven_trigger_r": 0.2,
    "breakeven_immediate": true,
    "exit_rules": {
      "failed_breakout_timeout_s": 30,
      "failed_breakout_min_move_bps": 2.0,
      "activity_drop_threshold": 0.5
    },
    "max_hold_time_hours": 2
  }
}
```

---

### 3.4 Swing пресет (длинные сделки)

**Файл:** `config/presets/video_strategy_swing.json`

```json
{
  "name": "video_strategy_swing",
  "description": "Swing trading - ride the trend",
  
  "position_config": {
    "tp_levels": [
      {"r_multiple": 2.0, "size_pct": 0.2, "enabled": true},
      {"r_multiple": 4.0, "size_pct": 0.3, "enabled": true},
      {"r_multiple": 6.0, "size_pct": 0.3, "enabled": true},
      {"r_multiple": 8.0, "size_pct": 0.2, "enabled": true}
    ],
    "tp_smart_placement": {
      "round_numbers_enabled": true,
      "round_numbers_priority": 5,
      "levels_enabled": true
    },
    "sl_atr_multiplier": 2.5,
    "breakeven_trigger_r": 1.0,
    "trailing_activation_r": 3.0,
    "chandelier_atr_mult": 3.0,
    "exit_rules": {
      "failed_breakout_timeout_s": 300,
      "failed_breakout_min_move_bps": 15.0,
      "activity_drop_enabled": false,
      "weak_impulse_timeout_s": 1800
    },
    "max_hold_time_hours": 24
  }
}
```

---

## 📋 PHASE 4: Интеграция в PositionManager

**Файл:** `breakout_bot/position/manager.py` (модификации)

```python
from ..config.settings import PositionConfig
from .tp_optimizer import TakeProfitOptimizer
from .exit_rules import ExitRulesChecker
from .state_machine import PositionStateMachine  # Новый компонент

class PositionManager:
    """Position manager with configuration-driven behavior."""
    
    def __init__(
        self,
        preset: TradingPreset,
        risk_manager: RiskManager,
        execution_manager: ExecutionManager,
        activity_tracker: Optional[ActivityTracker] = None,
        density_detector: Optional[DensityDetector] = None,
        level_detector: Optional[LevelDetector] = None
    ):
        self.preset = preset
        self.config = preset.position_config  # PositionConfig
        
        # Initialize TP optimizer with config
        self.tp_optimizer = TakeProfitOptimizer(
            config=self.config.tp_smart_placement,
            density_detector=density_detector,
            level_detector=level_detector
        )
        
        # Initialize exit rules checker with config
        self.exit_rules = ExitRulesChecker(
            config=self.config.exit_rules,
            activity_tracker=activity_tracker
        )
        
        # FSM per position
        self.position_fsms: Dict[str, PositionStateMachine] = {}
        
        logger.info(
            f"PositionManager initialized with config-driven components: "
            f"fsm_enabled={self.config.fsm_enabled}"
        )
    
    async def open_position(
        self,
        signal: Signal,
        market_data: MarketData
    ) -> Position:
        """Open position using configuration."""
        
        # ... расчёт entry, SL, quantity ...
        
        # Оптимизировать TP через optimizer (параметры из конфига!)
        optimized_tps = self.tp_optimizer.optimize_tp_levels(
            temp_position,
            self.config.tp_levels  # Из конфигурации!
        )
        
        # Сохранить в position.meta
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
        
        # Инициализировать FSM (если включено)
        if self.config.fsm_enabled:
            self.position_fsms[position.id] = PositionStateMachine(
                position=position,
                config=self.config.fsm_config,  # Из конфигурации!
                activity_tracker=self.activity_tracker
            )
        
        return position
    
    async def update_position(
        self,
        position: Position,
        market_data: MarketData
    ) -> Optional[PositionUpdate]:
        """Update position using configuration."""
        
        current_price = market_data.last_price
        
        # 1. Update FSM (если включено)
        if self.config.fsm_enabled and position.id in self.position_fsms:
            fsm = self.position_fsms[position.id]
            action = fsm.update(market_data)
            
            if action:
                logger.info(f"FSM action for {position.id}: {action}")
                # Handle FSM action...
        
        # 2. Check exit rules (параметры из конфига!)
        should_exit, exit_reason, message = self.exit_rules.check_all_exit_conditions(
            position,
            current_price
        )
        
        if should_exit:
            # Тип ордера из конфигурации!
            order_type = self.exit_rules.get_exit_order_type(exit_reason)
            
            return await self._execute_exit(
                position,
                current_price,
                exit_reason,
                order_type=order_type
            )
        
        # 3. Check TP/SL/trailing (как обычно)
        # ...
        
        # 4. Dynamic TP adjustment (если включено)
        if self.config.tp_smart_placement.dynamic_adjustment_enabled:
            updated_tps = self.tp_optimizer.update_tps_dynamically(
                position,
                current_tps
            )
            if updated_tps:
                # Update position TPs
                pass
        
        return None
```

---

## 🎯 Ключевые преимущества этого подхода

```
┌─────────────────────────────────────────────────────────────┐
│                   WHY THIS IS BETTER                         │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ✅ A/B Testing за 5 минут                                  │
│     → Создать 2 пресета, запустить параллельно             │
│                                                              │
│  ✅ Оптимизация БЕЗ изменения кода                          │
│     → Изменить JSON → перезапустить → готово               │
│                                                              │
│  ✅ Backtesting разных стратегий                            │
│     → Один backtest runner, N пресетов                     │
│                                                              │
│  ✅ Production-ready validation                             │
│     → Pydantic схемы валидируют ВСЁ                        │
│                                                              │
│  ✅ Self-documenting                                        │
│     → JSON пресет = документация стратегии                 │
│                                                              │
│  ✅ Easy debugging                                          │
│     → Лог показывает: "using config.exit_rules.timeout=60" │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 📊 Следующие шаги

### Week 1: Configuration Models (2 дня)
- [ ] Расширить `PositionConfig` с новыми полями
- [ ] Добавить `EntryRulesConfig`
- [ ] Добавить `ExitRulesConfig`
- [ ] Добавить `FSMConfig`
- [ ] Создать 4 тестовых пресета

### Week 2: Universal Components (5 дней)
- [ ] Реализовать `TakeProfitOptimizer` (config-driven)
- [ ] Реализовать `ExitRulesChecker` (config-driven)
- [ ] Реализовать `EntrySafetyChecker` (config-driven)
- [ ] Интегрировать в `PositionManager`
- [ ] Unit tests для каждого компонента

### Week 3: FSM Implementation (5 дней)
- [ ] Реализовать `PositionStateMachine` (config-driven)
- [ ] Интегрировать в `PositionManager`
- [ ] Тесты для всех сценариев S1-S4

### Week 4: Testing & Validation (5 дней)
- [ ] Integration tests с разными пресетами
- [ ] Backtesting на 4 пресетах
- [ ] Paper trading на 4 пресетах
- [ ] Сравнительный анализ результатов

---

## 🎓 Примеры использования

### A/B Testing

```bash
# Terminal 1: Conservative strategy
python -m breakout_bot.cli.main start \
  --preset video_strategy_conservative \
  --paper

# Terminal 2: Aggressive strategy  
python -m breakout_bot.cli.main start \
  --preset video_strategy_aggressive \
  --paper \
  --port 8001

# Через неделю сравнить:
python scripts/compare_strategies.py \
  --preset1 video_strategy_conservative \
  --preset2 video_strategy_aggressive \
  --period 7d
```

### Parameter Optimization

```python
# scripts/optimize_parameters.py

import json
from itertools import product

# Grid search по параметрам
failed_breakout_timeouts = [30, 60, 90, 120]
activity_drop_thresholds = [0.3, 0.35, 0.4, 0.45]

best_sharpe = -999
best_config = None

for timeout, threshold in product(failed_breakout_timeouts, activity_drop_thresholds):
    # Создать пресет с этими параметрами
    config = load_base_preset("video_strategy_conservative")
    config["position_config"]["exit_rules"]["failed_breakout_timeout_s"] = timeout
    config["position_config"]["exit_rules"]["activity_drop_threshold"] = threshold
    
    # Запустить backtest
    results = run_backtest(config, start_date, end_date)
    
    if results.sharpe_ratio > best_sharpe:
        best_sharpe = results.sharpe_ratio
        best_config = config

# Сохранить оптимальную конфигурацию
save_preset("video_strategy_optimized", best_config)
```

---

**Это правильная архитектура! 🎯**

**Суть:** Код = универсальный движок, JSON = бизнес-логика
