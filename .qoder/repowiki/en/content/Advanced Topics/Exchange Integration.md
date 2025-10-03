# Exchange Integration

<cite>
**Referenced Files in This Document**   
- [exchange_client.py](file://breakout_bot/exchange/exchange_client.py)
- [bybit_rate_limiter.py](file://breakout_bot/exchange/bybit_rate_limiter.py)
- [rate_limiter.py](file://breakout_bot/exchange/rate_limiter.py)
- [test_bybit_rate_limiter.py](file://test_bybit_rate_limiter.py)
- [market_stream.py](file://breakout_bot/exchange/market_stream.py)
</cite>

## Table of Contents
1. [Introduction](#introduction)
2. [Adapter Pattern Implementation](#adapter-pattern-implementation)
3. [Core Exchange Client Architecture](#core-exchange-client-architecture)
4. [Market Data Retrieval](#market-data-retrieval)
5. [Order Execution and Account Management](#order-execution-and-account-management)
6. [Rate Limiting Strategy](#rate-limiting-strategy)
7. [WebSocket Stream Handling](#websocket-stream-handling)
8. [Authentication Mechanisms](#authentication-mechanisms)
9. [Integration Testing Framework](#integration-testing-framework)
10. [Step-by-Step Exchange Integration Guide](#step-by-step-exchange-integration-guide)

## Introduction
This document provides comprehensive guidance for integrating new cryptocurrency exchanges into the Breakout Bot trading system. The integration framework uses an adapter pattern to abstract exchange-specific APIs through a unified interface, enabling seamless connectivity with multiple exchanges while maintaining consistent behavior across market data retrieval, order execution, and account management operations. The system supports both live trading and paper trading modes, with sophisticated rate limiting, WebSocket streaming, and connection resilience features.

The core implementation is centered around the `ExchangeClient` class, which serves as the primary interface for all exchange interactions. This client abstracts away the complexities of individual exchange APIs by leveraging the CCXT library while adding critical enhancements such as connection pooling, rate limiting enforcement, and real-time market data streaming. The architecture enables traders to switch between exchanges with minimal configuration changes, promoting flexibility and reducing vendor lock-in.

**Section sources**
- [exchange_client.py](file://breakout_bot/exchange/exchange_client.py#L0-L50)

## Adapter Pattern Implementation

```mermaid
classDiagram
class ExchangeClient {
+fetch_ohlcv(symbol, timeframe, limit)
+fetch_order_book(symbol, limit)
+fetch_ticker(symbol)
+create_order(symbol, type, side, amount, price)
+cancel_order(order_id, symbol)
+fetch_balance()
}
class PaperTradingExchange {
+create_order(symbol, type, side, amount, price)
+fetch_balance()
+fetch_order(order_id, symbol)
+cancel_order(order_id, symbol)
}
class ExchangeConnectionPool {
+get_connection(exchange_class, config)
+release_connection(conn)
+close_all()
}
ExchangeClient --> ExchangeConnectionPool : "uses"
ExchangeClient --> PaperTradingExchange : "delegates in paper mode"
ExchangeClient --> ccxt_async : "adapts via"
```

**Diagram sources **
- [exchange_client.py](file://breakout_bot/exchange/exchange_client.py#L327-L352)
- [exchange_client.py](file://breakout_bot/exchange/exchange_client.py#L87-L139)

**Section sources**
- [exchange_client.py](file://breakout_bot/exchange/exchange_client.py#L327-L352)

## Core Exchange Client Architecture

```mermaid
graph TB
subgraph "ExchangeClient Components"
A[ExchangeClient]
B[Connection Pool]
C[Rate Limiter]
D[Market Streamer]
E[Paper Trading Mode]
end
A --> B
A --> C
A --> D
A --> E
A --> |Adapts| F[(CCXT Library)]
G[SystemConfig] --> A
H[RealTimeMarketDataStreamer] --> I[WebSocket Connections]
```

**Diagram sources **
- [exchange_client.py](file://breakout_bot/exchange/exchange_client.py#L327-L352)
- [market_stream.py](file://breakout_bot/exchange/market_stream.py#L51-L78)

**Section sources**
- [exchange_client.py](file://breakout_bot/exchange/exchange_client.py#L327-L352)

## Market Data Retrieval

```mermaid
sequenceDiagram
participant Client as "Trading Engine"
participant ExchangeClient as "ExchangeClient"
participant RateLimiter as "BybitRateLimiter"
participant CCXT as "ccxt.async_support"
participant Exchange as "Cryptocurrency Exchange"
Client->>ExchangeClient : fetch_ohlcv(symbol, timeframe, limit)
activate ExchangeClient
ExchangeClient->>RateLimiter : wait_if_needed(MARKET_DATA)
activate RateLimiter
RateLimiter-->>ExchangeClient : Permission granted
deactivate RateLimiter
ExchangeClient->>CCXT : fetch_ohlcv() with endpoint /v5/market/kline
activate CCXT
CCXT->>Exchange : HTTP GET Request
activate Exchange
Exchange-->>CCXT : OHLCV Data
deactivate Exchange
CCXT-->>ExchangeClient : Raw OHLCV Data
deactivate CCXT
ExchangeClient->>ExchangeClient : Convert to Candle objects
ExchangeClient-->>Client : List[Candle]
deactivate ExchangeClient
```

**Diagram sources **
- [exchange_client.py](file://breakout_bot/exchange/exchange_client.py#L523-L559)
- [bybit_rate_limiter.py](file://breakout_bot/exchange/bybit_rate_limiter.py#L100-L130)

**Section sources**
- [exchange_client.py](file://breakout_bot/exchange/exchange_client.py#L523-L559)

## Order Execution and Account Management

```mermaid
flowchart TD
Start([Create Order]) --> ValidateInput["Validate Parameters"]
ValidateInput --> InputValid{"Required Fields Present?"}
InputValid --> |No| ReturnError["Return Validation Error"]
InputValid --> |Yes| CheckMode["Check Trading Mode"]
CheckMode --> |Paper Mode| SimulateExecution["Simulate Order Execution"]
CheckMode --> |Live Mode| ApplyRateLimit["Apply Rate Limiting"]
ApplyRateLimit --> ExecuteOrder["Execute via CCXT"]
ExecuteOrder --> HandleResponse["Process Response"]
HandleResponse --> ConvertModel["Convert to Order Model"]
ConvertModel --> UpdateBalance["Update Paper Balance if Applicable"]
UpdateBalance --> ReturnSuccess["Return Order Object"]
ReturnError --> End([Function Exit])
ReturnSuccess --> End
```

**Diagram sources **
- [exchange_client.py](file://breakout_bot/exchange/exchange_client.py#L779-L839)
- [exchange_client.py](file://breakout_bot/exchange/exchange_client.py#L172-L196)

**Section sources**
- [exchange_client.py](file://breakout_bot/exchange/exchange_client.py#L779-L839)

## Rate Limiting Strategy

```mermaid
classDiagram
class BybitRateLimiter {
+request_times : Dict[EndpointCategory, List[float]]
+rate_limit_info : Dict[str, RateLimitInfo]
+min_delay : float
+wait_if_needed(category, endpoint)
+update_from_headers(headers, endpoint)
+execute_with_retry(func, category, endpoint, max_retries)
+get_status()
+reset_limits()
}
class EndpointCategory {
MARKET_DATA
TRADING
ACCOUNT
PUBLIC
}
class RateLimitInfo {
limit : int
remaining : int
reset_timestamp : int
last_updated : float
}
BybitRateLimiter --> EndpointCategory : "uses"
BybitRateLimiter --> RateLimitInfo : "contains"
```

**Diagram sources **
- [bybit_rate_limiter.py](file://breakout_bot/exchange/bybit_rate_limiter.py#L70-L100)
- [rate_limiter.py](file://breakout_bot/exchange/rate_limiter.py#L39-L68)

**Section sources**
- [bybit_rate_limiter.py](file://breakout_bot/exchange/bybit_rate_limiter.py#L70-L100)

## WebSocket Stream Handling

```mermaid
sequenceDiagram
participant Client as "Trading Engine"
participant Streamer as "RealTimeMarketDataStreamer"
participant WS as "WebSocket Connection"
participant Exchange as "Cryptocurrency Exchange"
Client->>Streamer : ensure_symbol(BTCUSDT)
activate Streamer
Streamer->>Streamer : Create depth_task and trade_task
Streamer->>WS : Connect to wss : //stream.bybit.com/v5/public/linear
activate WS
WS->>Exchange : Subscribe to orderbook.50.BTCUSDT
activate Exchange
loop Every 100ms
Exchange-->>WS : Order book delta/snapshot
WS-->>Streamer : Process message
Streamer->>Streamer : Update local_book
Streamer->>Streamer : Build DepthSnapshot
Streamer->>Streamer : Store in _depth_cache
end
loop On Trade
Exchange-->>WS : Public trade message
WS-->>Streamer : Process trade
Streamer->>Streamer : Update trade window
Streamer->>Streamer : Calculate trades_per_minute
Streamer->>Streamer : Store in _trade_cache
end
Client->>Streamer : get_depth_snapshot(BTCUSDT)
Streamer-->>Client : DepthSnapshot object
Client->>Streamer : get_trade_stats(BTCUSDT)
Streamer-->>Client : TradeStats object
deactivate Exchange
deactivate WS
deactivate Streamer
```

**Diagram sources **
- [market_stream.py](file://breakout_bot/exchange/market_stream.py#L80-L110)
- [market_stream.py](file://breakout_bot/exchange/market_stream.py#L51-L78)

**Section sources**
- [market_stream.py](file://breakout_bot/exchange/market_stream.py#L51-L78)

## Authentication Mechanisms
The system implements secure authentication mechanisms for accessing exchange APIs. Authentication credentials are managed through environment variables rather than hard-coded values, ensuring sensitive information remains protected. The `ExchangeClient` retrieves API keys, secrets, and passphrases from environment variables (`EXCHANGE_API_KEY`, `EXCHANGE_SECRET`, `EXCHANGE_PASSPHRASE`) during initialization. These credentials are only included in the exchange configuration when they exist, allowing public market data access without authentication while requiring proper credentials for trading operations.

For enhanced security, the system uses asynchronous CCXT instances that support modern authentication protocols including HMAC-SHA256 signatures for REST API requests and secure WebSocket connections. The configuration includes specific parameters like `recvWindow` (5 seconds) to accommodate network latency while maintaining security against replay attacks. All API communications occur over HTTPS/TLS encrypted channels, and sensitive operations are subject to rate limiting to prevent abuse.

**Section sources**
- [exchange_client.py](file://breakout_bot/exchange/exchange_client.py#L418-L447)

## Integration Testing Framework

```mermaid
sequenceDiagram
participant Tester as "BybitRateLimiterTester"
participant Client as "ExchangeClient"
participant Limiter as "BybitRateLimiter"
participant Exchange as "Bybit API"
Tester->>Tester : Initialize test environment
Tester->>Client : Configure SystemConfig for Bybit
Tester->>Client : Create ExchangeClient instance
Tester->>Client : Verify rate_limiter exists
Tester->>Client : get_rate_limiter_status()
Client->>Limiter : get_status()
Limiter-->>Client : Status dictionary
Client-->>Tester : Return status
Tester->>Client : fetch_ticker(BTCUSDT) x 15
loop Burst Requests
Client->>Limiter : wait_if_needed(MARKET_DATA)
alt Within Limits
Limiter-->>Client : Proceed
Client->>Exchange : HTTP Request
Exchange-->>Client : Ticker Data
else Exceed Limits
Limiter->>Limiter : Sleep 2-3 seconds
Limiter-->>Client : Retry allowed
end
end
Tester->>Tester : Analyze results and generate report
```

**Diagram sources **
- [test_bybit_rate_limiter.py](file://test_bybit_rate_limiter.py#L48-L69)
- [test_bybit_rate_limiter.py](file://test_bybit_rate_limiter.py#L285-L311)

**Section sources**
- [test_bybit_rate_limiter.py](file://test_bybit_rate_limiter.py#L48-L69)

## Step-by-Step Exchange Integration Guide

```mermaid
flowchart TD
A[Identify Target Exchange] --> B[Verify CCXT Support]
B --> C{Supported?}
C --> |Yes| D[Create Configuration Profile]
C --> |No| E[Implement Custom CCXT Extension]
E --> D
D --> F[Configure Rate Limiting Rules]
F --> G[Implement WebSocket Handlers]
G --> H[Develop Mock Testing Suite]
H --> I[Conduct Sandbox Validation]
I --> J[Perform Load Testing]
J --> K[Deploy to Production]
K --> L[Monitor Performance Metrics]
L --> M{Stable Operation?}
M --> |Yes| N[Complete Integration]
M --> |No| O[Debug and Optimize]
O --> J
```

**Diagram sources **
- [exchange_client.py](file://breakout_bot/exchange/exchange_client.py#L327-L352)
- [bybit_rate_limiter.py](file://breakout_bot/exchange/bybit_rate_limiter.py#L70-L100)
- [market_stream.py](file://breakout_bot/exchange/market_stream.py#L51-L78)
- [test_bybit_rate_limiter.py](file://test_bybit_rate_limiter.py#L48-L69)

**Section sources**
- [exchange_client.py](file://breakout_bot/exchange/exchange_client.py#L327-L352)