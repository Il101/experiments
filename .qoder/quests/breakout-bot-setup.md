# Breakout Trading Bot Design Document

## Overview

This document outlines the design for a sophisticated breakout trading bot system built in Python 3.11+. The bot implements range breakout strategies after volatility compression on cryptocurrency exchanges using CCXT. The system supports both paper trading and live trading modes with four distinct trading presets targeting different market segments.

### Core Objectives
- Detect and trade range breakouts after volatility compression
- Support multiple trading strategies through configurable presets
- Provide robust risk management and position sizing
- Enable both paper trading and live trading capabilities
- Implement comprehensive monitoring and logging

### Trading Presets
1. **breakout_v1**: Base strategy for liquid pairs
2. **smallcap_top_gainers**: Target high-growth small-cap tokens (long)
3. **smallcap_top_losers**: Target declining small-cap tokens (short)
4. **high_liquidity_top30**: Focus on top 30 pairs by volume/OI

## Technology Stack & Dependencies

```mermaid
graph TD
    A[Python 3.11+] --> B[CCXT 4.3.0+]
    A --> C[Pandas/Numpy]
    A --> D[Pydantic v2]
    A --> E[AsyncIO/Websockets]
    A --> F[Typer CLI]
    A --> G[Loguru]
    A --> H[Pytest]
    
    B --> I[Exchange Integration]
    C --> J[Data Processing]
    D --> K[Data Models]
    E --> L[Real-time Data]
    F --> M[Command Interface]
    G --> N[Logging System]
    H --> O[Testing Framework]
```

### Key Dependencies
- **ccxt>=4.3.0**: Exchange connectivity and trading
- **pandas, numpy**: Data manipulation and calculations
- **pydantic>=2**: Data validation and models
- **aiohttp, asyncio, websockets**: Async operations
- **python-dotenv, typer[all], rich, loguru**: Configuration and CLI
- **pandas_ta**: Technical analysis indicators
- **pytest, pytest-asyncio**: Testing framework

## Architecture

### System Components Overview

```mermaid
graph TB
    subgraph "Data Layer"
        A[Exchange Client] --> B[Market Data]
        A --> C[Order Book]
        A --> D[Trade History]
    end
    
    subgraph "Analysis Layer"
        E[Indicators] --> F[Technical Analysis]
        G[Correlations] --> H[Market Relations]
        I[Scanner] --> J[Candidate Selection]
    end
    
    subgraph "Signal Layer"
        K[Breakout Signal] --> L[Entry Conditions]
        M[Risk Manager] --> N[Position Sizing]
    end
    
    subgraph "Execution Layer"
        O[Executor] --> P[Order Management]
        Q[Position Manager] --> R[Exit Strategies]
    end
    
    subgraph "Orchestration"
        S[Engine] --> T[State Machine]
        U[CLI] --> V[User Interface]
    end
    
    B --> F
    C --> F
    D --> F
    F --> J
    H --> J
    J --> L
    L --> N
    N --> P
    P --> R
    T --> A
    T --> I
    T --> K
    T --> O
```

### Core Models (Pydantic)

```mermaid
classDiagram
    class Candle {
        +int ts
        +float open
        +float high
        +float low
        +float close
        +float volume
    }
    
    class L2Depth {
        +float bid_usd_0_5pct
        +float ask_usd_0_5pct
        +float bid_usd_0_3pct
        +float ask_usd_0_3pct
        +float spread_bps
        +float imbalance
    }
    
    class Signal {
        +str symbol
        +str side
        +str reason
        +float entry
        +float level
        +float sl
        +dict meta
    }
    
    class Position {
        +str id
        +str symbol
        +str side
        +float qty
        +float entry
        +float sl
        +float tp
        +str status
        +dict timestamps
    }
    
    class Preset {
        +str name
        +dict timeframes
        +float risk_per_trade
        +int max_positions
        +dict scanner
        +dict levels
        +dict entry
        +dict sizing
        +dict stops
        +dict takes
        +dict management
        +dict execution
        +float fees_bps
    }
```

## Data Layer Architecture

### Exchange Client (data/exchange_ccxt.py)

```mermaid
sequenceDiagram
    participant C as Client
    participant E as ExchangeClient
    participant X as CCXT Exchange
    participant M as Market Data
    
    C->>E: fetch_ohlcv(symbol, timeframe)
    E->>X: load_markets()
    E->>X: fetch_ohlcv()
    X->>M: Raw OHLCV data
    M->>E: Formatted candles
    E->>C: Candle objects
    
    C->>E: fetch_order_book(symbol)
    E->>X: fetch_order_book()
    X->>E: Raw order book
    E->>E: calculate_l2_depth()
    E->>C: L2Depth object
```

#### Key Responsibilities
- **Market Data Fetching**: OHLCV data with configurable timeframes
- **Order Book Analysis**: Calculate depth metrics and spread analysis
- **Trade Flow Monitoring**: Recent trades for volume surge detection
- **Order Management**: Create limit, market, and stop-limit orders
- **Paper Trading Simulation**: Fill simulation with slippage modeling

#### L2Depth Calculation
- Extract bid/ask depths at 0.3% and 0.5% price levels
- Calculate spread in basis points
- Compute order book imbalance ratio
- Validate minimum depth requirements per preset

## Features Layer

### Technical Indicators (features/indicators.py)

```mermaid
graph LR
    A[Price Data] --> B[ATR Calculation]
    A --> C[Donchian Channels]
    A --> D[Bollinger Band Width]
    A --> E[VWAP]
    A --> F[Chandelier Exit]
    
    B --> G[Volatility Metrics]
    C --> H[Support/Resistance]
    D --> I[Compression Detection]
    E --> J[Volume-Weighted Price]
    F --> K[Trailing Stops]
```

#### Core Indicators Implementation
- **ATR (Average True Range)**: EMA-based volatility measurement
- **Donchian Channels**: Highest high and lowest low over N periods
- **Bollinger Band Width**: Volatility compression indicator
- **VWAP**: Volume-weighted average price from candle data
- **Chandelier Exit**: ATR-based trailing stop mechanism

### Correlation Analysis (features/correlations.py)

```mermaid
graph TD
    A[Symbol Returns 15m] --> C[Correlation Engine]
    B[BTC Returns 15m] --> C
    C --> D[Rolling Window 3d]
    D --> E[Correlation Coefficient]
    E --> F[Filter: |r| ≤ threshold]
```

## Scanner Architecture

### Breakout Scanner (scanner/breakout_scanner.py)

```mermaid
flowchart TD
    A[Market Universe] --> B[Liquidity Filters]
    B --> C[Activity Filters]
    C --> D[Volatility Quality]
    D --> E[Correlation Filter]
    E --> F[Scoring Algorithm]
    F --> G[Top N Candidates]
    G --> H[Donchian Levels]
    H --> I[Base Quality Check]
    
    subgraph "Filters"
        B1[24h Volume ≥ min]
        B2[OI ≥ min]
        B3[Spread ≤ max bps]
        B4[Depth ≥ min USD]
        B5[Trades/min ≥ min]
    end
    
    subgraph "Scoring Weights"
        F1[Vol Surge: 35%]
        F2[OI Change: 20%]
        F3[ATR Quality: 15%]
        F4[Low Correlation: 20%]
        F5[Trade Activity: 10%]
    end
    
    B --> B1
    B1 --> B2
    B2 --> B3
    B3 --> B4
    B4 --> B5
    
    F --> F1
    F1 --> F2
    F2 --> F3
    F3 --> F4
    F4 --> F5
```

#### Filtering Logic
1. **Liquidity Filters**: Volume, open interest, spread, depth, trade frequency
2. **Activity Filters**: Volume surge (1h, 5m), OI delta
3. **Volatility Quality**: ATR percentage bounds, Bollinger Band width percentile
4. **Correlation Filter**: Absolute correlation with BTC within limits

#### Scoring Formula
```
Score = 0.35 × z(vol_surge) + 0.20 × z(oi_change) + 0.15 × z(atr_quality) 
        + 0.20 × z(-abs(correlation)) + 0.10 × z(trades_per_min)
```

## Signal Generation

### Breakout Signal Logic (signals/breakout_signal.py)

```mermaid
stateDiagram-v2
    [*] --> Scanning
    Scanning --> LevelIdentified: Donchian levels found
    LevelIdentified --> MomentumWatch: Priority = momentum
    LevelIdentified --> RetestWatch: Priority = retest
    
    MomentumWatch --> MomentumTriggered: Price breaks level + conditions
    RetestWatch --> RetestTriggered: Pullback to level + conditions
    
    MomentumTriggered --> SignalGenerated: Create Signal object
    RetestTriggered --> SignalGenerated: Create Signal object
    
    SignalGenerated --> [*]
```

#### Momentum Entry (Primary for Liquid Markets)
- **Trigger**: Close > Level × (1 + ε)
- **Volume**: ≥ k × median_5m
- **Body Size**: ≥ 50% of candle range
- **L2 Imbalance**: ≥ minimum threshold
- **VWAP Gap**: ≤ maximum percentage
- **Order Type**: Stop-limit with offset

#### Retest Entry (Priority for Small-cap)
- **Setup**: Previous breakout occurred
- **Trigger**: First pullback to level
- **Entry**: Limit order at level with pierce tolerance
- **Validation**: L2 imbalance ≥ 0.60 and trade activity maintained
- **Window**: Time-limited opportunity

## Risk Management

### Position Sizing (risk/risk_manager.py)

```mermaid
graph TD
    A[Account Equity] --> B[Risk per Trade %]
    B --> C[R Dollar Amount]
    D[Entry Price] --> E[Stop Distance]
    F[Stop Level] --> E
    C --> G[Position Quantity]
    E --> G
    G --> H[Exchange Precision]
    H --> I[Final Position Size]
    
    J[Market Depth] --> K[Depth Constraint]
    K --> L[Max Share of 5bps Depth]
    L --> M[TWAP Requirement]
    I --> N[Validate Constraints]
    M --> N
    N --> O[Approved Size]
```

#### Sizing Algorithm
1. **R-Model**: R_dollar = equity × risk_per_trade
2. **Quantity**: position_qty = R_dollar / stop_distance
3. **Precision**: Round to exchange amount steps
4. **Depth Limit**: Maximum percentage of available depth
5. **TWAP**: Split large orders across time

### Stop Loss Strategy (management/position_manager.py)

```mermaid
graph LR
    A[Entry Type] --> B{Momentum or Retest?}
    B -->|Momentum| C[SL = max(swing_low, entry - 1.2×ATR)]
    B -->|Retest| D[SL = level - 1.0×ATR]
    
    E[Time-based Stops] --> F[20-30 min limit]
    G[Panic Exit] --> H[ATR(1m) multiplier trigger]
    
    C --> I[Active Stop Management]
    D --> I
    F --> I
    H --> I
```

### Take Profit Strategy

```mermaid
sequenceDiagram
    participant P as Position
    participant M as Manager
    participant E as Exchange
    
    P->>M: Position reaches +1R
    M->>E: Close 30-40% at TP1
    M->>M: Move stop to breakeven
    
    P->>M: Position reaches +2R
    M->>E: Close 30% at TP2
    M->>M: Activate Chandelier trailing
    
    P->>M: Base projection level hit
    M->>E: Partial profit taking
    M->>M: Continue trailing
```

#### Multi-level Exit Strategy
- **TP1**: +1R (30-40% position), move stop to breakeven
- **TP2**: +2R (30% position), activate Chandelier trailing
- **Projection**: Base height projection for additional exits
- **Trailing**: Chandelier exit with 2.5-2.8 × ATR(5m)

## Execution Layer

### Order Execution (execution/executor.py)

```mermaid
flowchart TD
    A[Signal Generated] --> B{Order Type}
    B -->|Stop-Limit| C[Monitor Stop Condition]
    B -->|Limit| D[Place Limit Order]
    B -->|TWAP| E[Split Order Over Time]
    
    C --> F{Stop Triggered?}
    F -->|Yes| G[Place Limit at Stop + Offset]
    F -->|No| C
    
    G --> H{Fill within Window?}
    H -->|Yes| I[Position Opened]
    H -->|No| J[Cancel - Anti-squeeze]
    
    D --> K{Fill Received?}
    K -->|Yes| I
    K -->|No| L[Monitor/Cancel]
    
    E --> M[Sequential TWAP Slices]
    M --> I
```

#### Paper Trading Simulation
- **Fill Logic**: Simulate fills based on bid/ask spread
- **Slippage Model**: a + b × |qty|/depth
- **Latency Simulation**: Add realistic execution delays
- **Market Impact**: Adjust fill prices based on order size

## Orchestration Engine

### State Machine (orchestra/engine.py)

```mermaid
stateDiagram-v2
    [*] --> Initialize
    Initialize --> Scan: Start cycle
    Scan --> BuildLevels: Candidates found
    BuildLevels --> SignalWatch: Levels established
    SignalWatch --> Sizing: Signal triggered
    Sizing --> Execute: Size calculated
    Execute --> Manage: Position opened
    Manage --> Manage: Active management
    Manage --> Scan: Position closed
    
    SignalWatch --> Scan: No signal/timeout
    Sizing --> Scan: Risk rejected
    Execute --> Scan: Execution failed
```

#### Engine Responsibilities
- **Cycle Management**: Coordinate scan → signal → execute workflow
- **Position Slots**: Limit concurrent positions per preset
- **Collision Avoidance**: Prevent scanning of symbols with open positions
- **State Persistence**: Maintain state across restarts
- **Error Handling**: Graceful degradation and recovery

## Preset Configuration

### Configuration Hierarchy

```mermaid
graph TD
    A[Base Config] --> B[Preset Override]
    B --> C[CLI Arguments]
    C --> D[Environment Variables]
    
    E[breakout_v1.json] --> F[Liquid Markets]
    G[smallcap_top_gainers.json] --> H[Growth Focused]
    I[smallcap_top_losers.json] --> J[Short Bias]
    K[high_liquidity_top30.json] --> L[Volume Leaders]
```

### Preset Specifications

| Parameter | breakout_v1 | smallcap_gainers | smallcap_losers | high_liquidity |
|-----------|-------------|------------------|-----------------|----------------|
| Risk per Trade | 0.6% | 0.3% | 0.3% | 0.5% |
| Max Positions | 3 | 2 | 2 | 4 |
| Min Volume 24h | $200M | $100M | $100M | Top 30 |
| Max Spread (bps) | 2 | 6 | 6 | 2 |
| Entry Priority | momentum | retest | retest | momentum |
| Stop Multiplier | 1.2× ATR | 1.3× ATR | 1.3× ATR | 1.2× ATR |

## CLI Interface

### Command Structure

```mermaid
graph TD
    A[breakout_bot] --> B[scan]
    A --> C[trade]
    A --> D[backtest]
    
    B --> E[--preset name]
    B --> F[--exchange bybit]
    B --> G[--universe USDT]
    B --> H[--tf 5m]
    
    C --> I[--preset name]
    C --> J[--live/--paper]
    C --> K[--exchange bybit]
    
    D --> L[--preset name]
    D --> M[--start date]
    D --> N[--end date]
```

#### Usage Examples
```bash
# Scan candidates
python -m breakout_bot.cli scan --preset smallcap_top_gainers --exchange bybit --tf 5m

# Paper trading
python -m breakout_bot.cli trade --preset breakout_v1 --exchange bybit --paper

# Live trading (requires API keys)
python -m breakout_bot.cli trade --preset smallcap_top_losers --exchange bybit --live

# Backtesting
python -m breakout_bot.cli backtest --preset breakout_v1 --start 2024-01-01 --end 2024-06-01
```

## Testing Strategy

### Test Coverage Matrix

| Component | Unit Tests | Integration Tests | Mock Requirements |
|-----------|------------|-------------------|-------------------|
| Indicators | ✓ | - | Price data |
| Scanner | ✓ | ✓ | Market data, exchange |
| Signals | ✓ | ✓ | OHLCV, L2 data |
| Risk Manager | ✓ | - | Account data |
| Executor | - | ✓ | Exchange API |
| Position Manager | ✓ | ✓ | Position state |

### Key Test Scenarios

```mermaid
graph TD
    A[Test Indicators] --> B[ATR Calculation]
    A --> C[Donchian Levels]
    A --> D[VWAP Accuracy]
    
    E[Test Scanner] --> F[Filter Logic]
    E --> G[Scoring Algorithm]
    E --> H[Symbol Selection]
    
    I[Test Signals] --> J[Momentum Triggers]
    I --> K[Retest Logic]
    I --> L[Anti-squeeze]
    
    M[Test Risk] --> N[Position Sizing]
    M --> O[Stop Calculation]
    M --> P[Depth Validation]
```

## Storage & Persistence

### Data Repository (storage/repository.py)

```mermaid
erDiagram
    TRADES {
        string id PK
        string symbol
        string side
        float entry_price
        float exit_price
        float quantity
        datetime entry_time
        datetime exit_time
        float pnl
        string preset
    }
    
    ORDERS {
        string id PK
        string trade_id FK
        string symbol
        string side
        string type
        float price
        float quantity
        string status
        datetime created_at
        datetime filled_at
    }
    
    POSITIONS {
        string id PK
        string symbol
        string side
        float quantity
        float entry_price
        float stop_loss
        float take_profit
        string status
        datetime opened_at
        datetime closed_at
    }
    
    DECISIONS {
        string id PK
        datetime timestamp
        string event_type
        string symbol
        dict metadata
        string reasoning
    }
```

## Backtesting Framework

### Backtesting Architecture (backtest/backtester.py)

```mermaid
sequenceDiagram
    participant B as Backtester
    participant D as Data Source
    participant E as Engine
    participant R as Results
    
    B->>D: Load historical data
    D->>B: OHLCV + Order book snapshots
    B->>E: Initialize with historical mode
    
    loop For each time step
        B->>E: Process market data
        E->>E: Run strategy logic
        E->>B: Generate orders
        B->>B: Simulate execution
        B->>R: Record trade results
    end
    
    B->>R: Calculate performance metrics
    R->>B: Final report
```

#### Performance Metrics
- **Returns**: CAGR, total return, Sharpe ratio
- **Risk**: Maximum drawdown, volatility, VaR
- **Trade Stats**: Win rate, profit factor, average R
- **Efficiency**: Trade frequency, holding periods

### Walk-Forward Analysis
- **Window Size**: 3-month training periods
- **Validation**: 1-month out-of-sample testing
- **Reoptimization**: Quarterly parameter updates
- **Robustness**: Performance consistency across periods

## Logging & Monitoring

### Logging Strategy (loguru)

```mermaid
graph TD
    A[Decision Events] --> B[Scanner Logs]
    A --> C[Signal Logs]
    A --> D[Execution Logs]
    A --> E[Risk Logs]
    
    B --> F[Candidate Filtering]
    B --> G[Score Calculations]
    
    C --> H[Entry Conditions]
    C --> I[Signal Generation]
    
    D --> J[Order Placement]
    D --> K[Fill Confirmations]
    
    E --> L[Position Sizing]
    E --> M[Risk Violations]
    
    F --> N[Structured Logs]
    G --> N
    H --> N
    I --> N
    J --> N
    K --> N
    L --> N
    M --> N
    
    N --> O[Log Analysis]
    N --> P[Performance Review]
```

#### Log Categories
- **Decision Logs**: Every filter pass/fail with metrics
- **Execution Logs**: Order flow and latency tracking
- **Risk Logs**: Position sizing and stop adjustments
- **Performance Logs**: Trade outcomes and attribution
- **System Logs**: Errors, warnings, and health checks

## Kill Switch & Safety

### Risk Controls

```mermaid
stateDiagram-v2
    [*] --> Normal
    Normal --> Warning: Daily R < -1.5
    Normal --> Critical: Daily R < -2.5
    Normal --> Critical: 3 consecutive losses
    
    Warning --> Normal: Positive trade
    Warning --> Critical: Additional loss
    
    Critical --> Shutdown: Stop all new entries
    Shutdown --> Normal: Next trading session
```

#### Safety Mechanisms
- **Daily R Limit**: Stop entries when daily loss exceeds threshold
- **Consecutive Loss Limit**: Halt after N losing trades in sequence
- **Latency Cutoff**: Reject orders with excessive execution delay
- **Spread Protection**: No market orders when spread too wide
- **Depth Validation**: Ensure sufficient liquidity before entry

This design provides a comprehensive framework for a sophisticated breakout trading bot with robust risk management, multiple trading strategies, and extensive monitoring capabilities.