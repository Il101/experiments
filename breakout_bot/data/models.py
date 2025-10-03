"""
Core data models for the Breakout Bot Trading System.

This module defines the fundamental data structures used throughout the system
for market data, trading signals, positions, and order management.
"""

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional, Union
from pydantic import BaseModel, Field, field_validator, computed_field
from decimal import Decimal


class Candle(BaseModel):
    """OHLCV candlestick data model."""
    
    ts: int = Field(..., description="Timestamp in milliseconds")
    open: float = Field(..., description="Opening price")
    high: float = Field(..., description="Highest price")
    low: float = Field(..., description="Lowest price")
    close: float = Field(..., description="Closing price")
    volume: float = Field(..., description="Volume in base currency")
    
    @field_validator('high', 'low', 'open', 'close')
    @classmethod
    def validate_prices(cls, v: float) -> float:
        """Validate that prices are positive."""
        if v <= 0:
            raise ValueError("Prices must be positive")
        return v
    
    @field_validator('volume')
    @classmethod
    def validate_volume(cls, v: float) -> float:
        """Validate that volume is non-negative."""
        if v < 0:
            raise ValueError("Volume cannot be negative")
        return v
    
    @field_validator('low')
    @classmethod
    def validate_low_vs_high(cls, v: float, info) -> float:
        """Validate that low <= high."""
        if info.data and 'high' in info.data and v > info.data['high']:
            raise ValueError("Low price cannot be higher than high price")
        return v
    
    @property
    def datetime(self) -> datetime:
        """Convert timestamp to datetime object."""
        return datetime.fromtimestamp(self.ts / 1000)
    
    @property
    def typical_price(self) -> float:
        """Calculate typical price (HLC/3)."""
        return (self.high + self.low + self.close) / 3
    
    @property
    def hl2(self) -> float:
        """Calculate median price (HL/2)."""
        return (self.high + self.low) / 2
    
    @property
    def ohlc4(self) -> float:
        """Calculate OHLC average."""
        return (self.open + self.high + self.low + self.close) / 4


class L2Depth(BaseModel):
    """Level 2 order book depth analysis."""
    
    bid_usd_0_5pct: float = Field(..., description="Bid liquidity within 0.5% in USD")
    ask_usd_0_5pct: float = Field(..., description="Ask liquidity within 0.5% in USD")
    bid_usd_0_3pct: float = Field(..., description="Bid liquidity within 0.3% in USD")
    ask_usd_0_3pct: float = Field(..., description="Ask liquidity within 0.3% in USD")
    spread_bps: float = Field(..., description="Bid-ask spread in basis points")
    imbalance: float = Field(..., description="Order book imbalance ratio")
    
    @field_validator('spread_bps')
    @classmethod
    def validate_spread(cls, v: float) -> float:
        """Validate spread is non-negative."""
        if v < 0:
            raise ValueError("Spread cannot be negative")
        return v
    
    @field_validator('imbalance')
    @classmethod
    def validate_imbalance(cls, v: float) -> float:
        """Validate imbalance is between -1 and 1."""
        if not -1 <= v <= 1:
            raise ValueError("Imbalance must be between -1 and 1")
        return v
    
    @property
    def total_depth_usd_0_5pct(self) -> float:
        """Total depth within 0.5%."""
        return self.bid_usd_0_5pct + self.ask_usd_0_5pct
    
    @property
    def total_depth_usd_0_3pct(self) -> float:
        """Total depth within 0.3%."""
        return self.bid_usd_0_3pct + self.ask_usd_0_3pct


class TradingLevel(BaseModel):
    """Support/resistance level definition."""
    
    price: float = Field(..., description="Level price")
    level_type: Literal["support", "resistance"] = Field(..., description="Level type")
    touch_count: int = Field(..., description="Number of times price touched this level")
    strength: float = Field(..., description="Level strength score 0-1")
    first_touch_ts: int = Field(..., description="First touch timestamp")
    last_touch_ts: int = Field(..., description="Last touch timestamp")
    base_height: Optional[float] = Field(None, description="Height of base pattern")
    
    @field_validator('touch_count')
    @classmethod
    def validate_touch_count(cls, v: int) -> int:
        """Validate touch count is positive."""
        if v < 1:
            raise ValueError("Touch count must be at least 1")
        return v
    
    @field_validator('strength')
    @classmethod
    def validate_strength(cls, v: float) -> float:
        """Validate strength is between 0 and 1."""
        if not 0 <= v <= 1:
            raise ValueError("Strength must be between 0 and 1")
        return v


class Signal(BaseModel):
    """Trading signal model."""
    
    symbol: str = Field(..., description="Trading pair symbol")
    side: Literal["long", "short"] = Field(..., description="Signal direction")
    strategy: Literal["momentum", "retest"] = Field(..., description="Signal strategy type")
    reason: str = Field(..., description="Signal generation reason")
    entry: float = Field(..., description="Suggested entry price")
    level: float = Field(..., description="Key level price")
    sl: float = Field(..., description="Stop loss price")
    confidence: float = Field(..., description="Signal confidence 0-1")
    timestamp: int = Field(..., description="Signal generation timestamp")
    
    # Добавляем недостающие поля для управления жизненным циклом
    status: Literal["pending", "active", "executed", "failed", "expired", "removed"] = Field(
        default="pending", description="Signal status"
    )
    correlation_id: Optional[str] = Field(None, description="Correlation ID for end-to-end tracing")
    timestamps: Dict[str, int] = Field(
        default_factory=dict, description="Key timestamps (created_at, executed_at, etc.)"
    )
    tp1: Optional[float] = Field(None, description="Take profit 1 price")
    tp2: Optional[float] = Field(None, description="Take profit 2 price") 
    meta: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    
    @field_validator('confidence')
    @classmethod
    def validate_confidence(cls, v: float) -> float:
        """Validate confidence is between 0 and 1."""
        if not 0 <= v <= 1:
            raise ValueError("Confidence must be between 0 and 1")
        return v
    
    @field_validator('entry', 'level', 'sl')
    @classmethod
    def validate_prices(cls, v: float) -> float:
        """Validate prices are positive."""
        if v <= 0:
            raise ValueError("Prices must be positive")
        return v
    
    @property
    def risk_reward_ratio(self) -> float:
        """Calculate risk-reward ratio using tp1 as primary target."""
        tp_target = self.tp1 or self.meta.get("tp")  # Fallback to meta for compatibility
        if not tp_target:
            return 0
            
        if self.side == "long":
            risk = self.entry - self.sl
            reward = tp_target - self.entry
            return reward / risk if risk > 0 else 0
        elif self.side == "short":
            risk = self.sl - self.entry
            reward = self.entry - tp_target
            return reward / risk if risk > 0 else 0
        return 0


class Position(BaseModel):
    """Trading position model."""
    
    id: str = Field(..., description="Unique position identifier")
    symbol: str = Field(..., description="Trading pair symbol")
    side: Literal["long", "short"] = Field(..., description="Position direction")
    strategy: str = Field(..., description="Strategy used")
    qty: float = Field(..., description="Position quantity")
    entry: float = Field(..., description="Average entry price")
    sl: float = Field(..., description="Stop loss price")
    tp: Optional[float] = Field(None, description="Take profit price")
    status: Literal["open", "closed", "partially_closed"] = Field(..., description="Position status")
    pnl_usd: float = Field(default=0.0, description="Unrealized PnL in USD")
    pnl_r: float = Field(default=0.0, description="PnL in R multiples")
    fees_usd: float = Field(default=0.0, description="Total fees paid")
    timestamps: Dict[str, int] = Field(default_factory=dict, description="Key timestamps")
    meta: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    
    @field_validator('qty')
    @classmethod
    def validate_quantity(cls, v: float) -> float:
        """Validate quantity is positive."""
        if v <= 0:
            raise ValueError("Quantity must be positive")
        return v
    
    @field_validator('entry', 'sl')
    @classmethod
    def validate_prices(cls, v: float) -> float:
        """Validate prices are positive."""
        if v <= 0:
            raise ValueError("Prices must be positive")
        return v
    
    @property
    def is_profitable(self) -> bool:
        """Check if position is currently profitable."""
        return self.pnl_usd > 0
    
    @property
    def duration_hours(self) -> float:
        """Calculate position duration in hours."""
        if "opened_at" in self.timestamps:
            end_time = self.timestamps.get("closed_at", int(datetime.now().timestamp() * 1000))
            duration_ms = end_time - self.timestamps["opened_at"]
            return duration_ms / (1000 * 60 * 60)
        return 0


class Order(BaseModel):
    """Order model for tracking trade executions."""
    
    id: str = Field(..., description="Unique order identifier")
    position_id: Optional[str] = Field(None, description="Associated position ID")
    symbol: str = Field(..., description="Trading pair symbol")
    side: Literal["buy", "sell"] = Field(..., description="Order side")
    order_type: Literal["market", "limit", "stop", "stop_limit"] = Field(..., description="Order type")
    qty: float = Field(..., description="Order quantity")
    price: Optional[float] = Field(None, description="Order price (for limit orders)")
    stop_price: Optional[float] = Field(None, description="Stop price (for stop orders)")
    status: Literal["pending", "open", "filled", "cancelled", "rejected"] = Field(..., description="Order status")
    filled_qty: float = Field(default=0.0, description="Filled quantity")
    avg_fill_price: Optional[float] = Field(None, description="Average fill price")
    fees_usd: float = Field(default=0.0, description="Order fees in USD")
    timestamps: Dict[str, int] = Field(default_factory=dict, description="Order timestamps")
    exchange_id: Optional[str] = Field(None, description="Exchange order ID")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional execution metadata")
    
    @field_validator('qty', 'filled_qty')
    @classmethod
    def validate_quantities(cls, v: float) -> float:
        """Validate quantities are non-negative."""
        if v < 0:
            raise ValueError("Quantities cannot be negative")
        return v
    
    @property
    def is_filled(self) -> bool:
        """Check if order is completely filled."""
        return self.status == "filled"
    
    @property
    def remaining_qty(self) -> float:
        """Calculate remaining unfilled quantity."""
        return max(0, self.qty - self.filled_qty)


class MarketData(BaseModel):
    """Aggregated market data for a symbol."""
    
    symbol: str = Field(..., description="Trading pair symbol")
    price: float = Field(..., description="Current price")
    volume_24h_usd: float = Field(..., description="24h volume in USD")
    oi_usd: Optional[float] = Field(None, description="Open interest in USD")
    oi_change_24h: Optional[float] = Field(None, description="24h OI change")
    trades_per_minute: float = Field(default=0.0, description="Recent trades per minute")
    atr_5m: float = Field(default=0.0, description="5-minute ATR")
    atr_15m: float = Field(default=0.0, description="15-minute ATR")
    bb_width_pct: float = Field(default=0.0, description="Bollinger Band width percentage")
    btc_correlation: float = Field(default=0.0, description="Correlation with BTC")
    l2_depth: Optional[L2Depth] = Field(None, description="Order book depth analysis")
    candles_5m: List[Candle] = Field(default_factory=list, description="Recent 5m candles")
    timestamp: int = Field(..., description="Data timestamp")
    market_type: str = Field(default="unknown", description="Market type: spot or futures")
    
    @field_validator('volume_24h_usd', 'trades_per_minute', 'atr_5m', 'atr_15m')
    @classmethod
    def validate_positive_metrics(cls, v: float) -> float:
        """Validate metrics are non-negative."""
        if v < 0:
            raise ValueError("Metrics cannot be negative")
        return v
    
    @field_validator('btc_correlation')
    @classmethod
    def validate_correlation(cls, v: float) -> float:
        """Validate correlation is between -1 and 1."""
        if not -1 <= v <= 1:
            raise ValueError("Correlation must be between -1 and 1")
        return v
    
    @property
    def atr_ratio(self) -> float:
        """Calculate ATR ratio (15m/5m)."""
        return self.atr_15m / self.atr_5m if self.atr_5m > 0 else 0
    
    @property
    def liquidity_score(self) -> float:
        """Calculate overall liquidity score."""
        if self.l2_depth is None:
            # Fallback to volume-only score if no L2 data
            volume_score = min(1.0, self.volume_24h_usd / 100000000)  # Normalize to 100M USD
            return volume_score
        
        depth_score = min(1.0, self.l2_depth.total_depth_usd_0_5pct / 1000000)  # Normalize to 1M USD
        spread_score = max(0.0, 1.0 - self.l2_depth.spread_bps / 50)  # Penalty for spreads > 50 bps
        volume_score = min(1.0, self.volume_24h_usd / 100000000)  # Normalize to 100M USD
        
        return (depth_score + spread_score + volume_score) / 3


class ScanResult(BaseModel):
    """Market scan result with scoring."""
    
    symbol: str = Field(..., description="Trading pair symbol")
    score: float = Field(..., description="Overall scan score")
    rank: int = Field(..., description="Ranking position")
    market_data: MarketData = Field(..., description="Market data snapshot")
    filter_results: Dict[str, bool] = Field(..., description="Filter pass/fail results")
    filter_details: Dict[str, Dict[str, Any]] = Field(default_factory=dict, description="Detailed filter diagnostics")
    score_components: Dict[str, float] = Field(..., description="Individual score components")
    levels: List[TradingLevel] = Field(default_factory=list, description="Detected levels")
    timestamp: int = Field(..., description="Scan timestamp")
    correlation_id: Optional[str] = Field(None, description="Correlation ID for end-to-end tracing")
    
    @field_validator('score')
    @classmethod
    def validate_score(cls, v: float) -> float:
        """Validate score is reasonable."""
        if v < -10 or v > 10:
            raise ValueError("Score should be between -10 and 10")
        return v
    
    @computed_field
    @property
    def passed_all_filters(self) -> bool:
        """Check if all filters passed."""
        return all(self.filter_results.values())
    
    @property
    def strongest_level(self) -> Optional[TradingLevel]:
        """Get the strongest detected level."""
        if not self.levels:
            return None
        return max(self.levels, key=lambda x: x.strength)


class OrderBookEntry(BaseModel):
    """Order book entry."""
    
    price: float = Field(..., description="Price level")
    size: float = Field(..., description="Size at this price level")
    
    @field_validator('price', 'size')
    @classmethod
    def validate_positive(cls, v: float) -> float:
        """Validate that values are positive."""
        if v <= 0:
            raise ValueError("Price and size must be positive")
        return v


class OrderBook(BaseModel):
    """Order book data model."""
    
    symbol: str = Field(..., description="Trading symbol")
    timestamp: int = Field(..., description="Timestamp in milliseconds")
    bids: List[OrderBookEntry] = Field(default_factory=list, description="Bid orders")
    asks: List[OrderBookEntry] = Field(default_factory=list, description="Ask orders")
    
    @field_validator('bids', 'asks')
    @classmethod
    def validate_entries(cls, v: List[OrderBookEntry]) -> List[OrderBookEntry]:
        """Validate order book entries."""
        if not v:
            return v
        
        # Check that bids are sorted by price (descending)
        if v == cls.model_fields['bids'].default_factory():
            for i in range(len(v) - 1):
                if v[i].price < v[i + 1].price:
                    raise ValueError("Bids must be sorted by price (descending)")
        
        # Check that asks are sorted by price (ascending)
        if v == cls.model_fields['asks'].default_factory():
            for i in range(len(v) - 1):
                if v[i].price > v[i + 1].price:
                    raise ValueError("Asks must be sorted by price (ascending)")
        
        return v
    
    @property
    def best_bid(self) -> Optional[OrderBookEntry]:
        """Get best bid price."""
        return self.bids[0] if self.bids else None
    
    @property
    def best_ask(self) -> Optional[OrderBookEntry]:
        """Get best ask price."""
        return self.asks[0] if self.asks else None
    
    @property
    def spread(self) -> Optional[float]:
        """Get bid-ask spread."""
        if self.best_bid and self.best_ask:
            return self.best_ask.price - self.best_bid.price
        return None


class TradeTick(BaseModel):
    """Trade tick data model."""
    
    symbol: str = Field(..., description="Trading symbol")
    timestamp: int = Field(..., description="Timestamp in milliseconds")
    price: float = Field(..., description="Trade price")
    size: float = Field(..., description="Trade size")
    side: Literal['buy', 'sell'] = Field(..., description="Trade side")
    trade_id: Optional[str] = Field(None, description="Unique trade identifier")
    
    @field_validator('price', 'size')
    @classmethod
    def validate_positive(cls, v: float) -> float:
        """Validate that values are positive."""
        if v <= 0:
            raise ValueError("Price and size must be positive")
        return v
    
    @field_validator('side')
    @classmethod
    def validate_side(cls, v: str) -> str:
        """Validate trade side."""
        if v not in ['buy', 'sell']:
            raise ValueError("Side must be 'buy' or 'sell'")
        return v
