# Breakout Bot API Documentation

## Overview

The Breakout Bot Trading System provides a comprehensive REST API for algorithmic cryptocurrency trading. This document describes all available endpoints, request/response formats, and usage examples.

## Base URL

```
http://localhost:8000/api
```

## Authentication

Currently, the API does not require authentication for development purposes. In production, API keys or JWT tokens should be implemented.

## API Endpoints

### Health Check

#### GET /api/health

Check the overall system health and status.

**Response:**
```json
{
  "status": "healthy",
  "engine_initialized": true,
  "engine_running": false,
  "resource_health": {
    "status": "healthy",
    "issues": [],
    "cpu_percent": 15.2,
    "memory_percent": 45.8
  },
  "timestamp": "2025-01-16T12:00:00Z"
}
```

### Engine Control

#### GET /api/engine/status

Get current engine status and state information.

**Response:**
```json
{
  "state": "IDLE",
  "preset": "breakout_v1",
  "mode": "paper",
  "startedAt": "2025-01-16T12:00:00Z",
  "slots": 3,
  "openPositions": 0,
  "latencyMs": 45,
  "dailyR": 0.0,
  "consecutiveLosses": 0
}
```

#### GET /api/engine/metrics

Get engine performance metrics.

**Response:**
```json
{
  "uptime": 3600,
  "cycleCount": 1200,
  "avgLatencyMs": 47.5,
  "totalSignals": 25,
  "totalTrades": 8,
  "dailyPnlR": 0.15,
  "maxDrawdownR": 0.05
}
```

#### POST /api/engine/start

Start the trading engine with specified preset and mode.

**Request:**
```json
{
  "preset": "breakout_v1",
  "mode": "paper"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Engine started successfully",
  "timestamp": "2025-01-16T12:00:00Z"
}
```

#### POST /api/engine/stop

Stop the trading engine.

**Response:**
```json
{
  "success": true,
  "message": "Engine stopped successfully",
  "timestamp": "2025-01-16T12:00:00Z"
}
```

#### POST /api/engine/command

Execute a system command.

**Request:**
```json
{
  "command": "pause"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Command executed successfully",
  "command": "pause",
  "timestamp": "2025-01-16T12:00:00Z"
}
```

**Available Commands:**
- `pause` - Pause the engine
- `resume` - Resume the engine
- `time_stop` - Time-based stop
- `panic_exit` - Emergency stop
- `kill_switch` - Activate kill switch
- `retry` - Retry after error

### Trading Data

#### GET /api/positions

Get all open positions.

**Response:**
```json
[
  {
    "id": "pos_123",
    "symbol": "BTC/USDT",
    "side": "long",
    "entry": 50000.0,
    "sl": 48000.0,
    "size": 0.1,
    "mode": "momentum",
    "openedAt": "2025-01-16T12:00:00Z",
    "pnlR": 0.5,
    "pnlUsd": 250.0,
    "unrealizedPnlR": 0.5,
    "unrealizedPnlUsd": 250.0
  }
]
```

#### GET /api/orders

Get all orders.

**Response:**
```json
[
  {
    "id": "order_123",
    "symbol": "BTC/USDT",
    "side": "buy",
    "type": "market",
    "qty": 0.1,
    "price": 50000.0,
    "status": "filled",
    "createdAt": "2025-01-16T12:00:00Z",
    "filledAt": "2025-01-16T12:00:01Z",
    "fees": 3.25
  }
]
```

#### DELETE /api/orders/{order_id}

Cancel a specific order.

**Response:**
```json
{
  "success": true,
  "message": "Order canceled successfully",
  "timestamp": "2025-01-16T12:00:00Z"
}
```

### Presets Management

#### GET /api/presets/

Get list of available trading presets.

**Response:**
```json
[
  {
    "name": "breakout_v1",
    "description": "Liquid markets momentum breakout strategy",
    "risk_per_trade": 0.006,
    "max_positions": 3,
    "strategy_type": "momentum"
  }
]
```

#### GET /api/presets/{preset_name}

Get specific preset configuration.

**Response:**
```json
{
  "name": "breakout_v1",
  "config": {
    "description": "Liquid markets momentum breakout strategy",
    "risk": {
      "risk_per_trade": 0.006,
      "max_concurrent_positions": 3
    },
    "scanner_config": {
      "score_weights": {
        "vol_surge": 0.35,
        "oi_delta": 0.2
      }
    }
  }
}
```

#### PUT /api/presets/{preset_name}

Update preset configuration.

**Request:**
```json
{
  "description": "Updated strategy description",
  "risk": {
    "risk_per_trade": 0.007,
    "max_concurrent_positions": 3
  }
}
```

**Response:**
```json
{
  "success": true,
  "message": "Preset updated successfully",
  "timestamp": "2025-01-16T12:00:00Z"
}
```

### Scanner

#### POST /api/scanner/scan

Execute a market scan with specified parameters.

**Request:**
```json
{
  "preset": "breakout_v1",
  "limit": 10,
  "symbols": ["BTC/USDT", "ETH/USDT"]
}
```

**Response:**
```json
{
  "candidates": [
    {
      "symbol": "BTC/USDT",
      "score": 0.85,
      "filters": {
        "liquidity": true,
        "volatility": true,
        "volume_surge": true
      },
      "metrics": {
        "vol_surge_1h": 1.5,
        "atr15m_pct": 0.02
      },
      "levels": {
        "high": 51000.0,
        "low": 49000.0
      }
    }
  ],
  "totalScanned": 50,
  "passedFilters": 3
}
```

#### GET /api/scanner/status

Get current scanner status.

**Response:**
```json
{
  "status": "idle",
  "last_scan": "2025-01-16T12:00:00Z",
  "candidates_found": 3,
  "scan_duration_ms": 1250
}
```

### Performance Analytics

#### GET /api/performance/equity

Get equity curve data.

**Response:**
```json
[
  {
    "timestamp": "2025-01-16T12:00:00Z",
    "value": 10000.0,
    "cumulativeR": 0.15
  }
]
```

#### GET /api/performance/metrics

Get performance metrics summary.

**Response:**
```json
{
  "totalTrades": 25,
  "winRate": 0.68,
  "avgR": 0.45,
  "sharpeRatio": 1.85,
  "maxDrawdownR": 0.12,
  "profitFactor": 2.1,
  "consecutiveWins": 5,
  "consecutiveLosses": 2
}
```

### Metrics and Monitoring

#### GET /api/metrics/summary

Get comprehensive metrics summary.

**Response:**
```json
{
  "performance": {
    "cpu_percent": 15.2,
    "memory_percent": 45.8,
    "memory_used_mb": 256.5,
    "disk_usage_percent": 12.3,
    "active_threads": 8,
    "open_files": 15,
    "network_connections": 3
  },
  "engine": {
    "cycle_time": {
      "count": 100,
      "mean": 0.045,
      "min": 0.020,
      "max": 0.080
    },
    "positions": {
      "count": 100,
      "mean": 2.5,
      "min": 0,
      "max": 5
    }
  },
  "trading": {
    "events": {
      "count": 25,
      "mean": 1.0,
      "min": 0,
      "max": 3
    },
    "pnl": {
      "count": 25,
      "mean": 0.15,
      "min": -0.5,
      "max": 1.2
    }
  }
}
```

#### GET /api/metrics/performance

Get current system performance metrics.

**Response:**
```json
{
  "cpu_percent": 15.2,
  "memory_percent": 45.8,
  "memory_used_mb": 256.5,
  "disk_usage_percent": 12.3,
  "active_threads": 8,
  "open_files": 15,
  "network_connections": 3,
  "timestamp": 1642248000.0
}
```

#### GET /api/metrics/health

Get metrics system health status.

**Response:**
```json
{
  "status": "healthy",
  "issues": [],
  "metrics_count": 1250,
  "performance": {
    "cpu_percent": 15.2,
    "memory_percent": 45.8
  },
  "timestamp": 1642248000000
}
```

### WebSocket Events

#### WebSocket Connection

Connect to `ws://localhost:8000/ws` for real-time updates.

**Event Types:**

- `HEARTBEAT` - Periodic heartbeat with latency info
- `ENGINE_UPDATE` - Engine state changes
- `POSITION_UPDATE` - Position updates
- `ORDER_UPDATE` - Order status changes
- `SIGNAL` - New trading signals
- `SCAN_RESULT` - Scanner results
- `ORDER_PLACED` - Order placement events
- `ORDER_FILLED` - Order fill events
- `ORDER_CANCELLED` - Order cancellation events
- `POSITION_OPENED` - Position opening events
- `POSITION_CLOSED` - Position closing events

**Example WebSocket Message:**
```json
{
  "type": "POSITION_UPDATE",
  "ts": 1642248000000,
  "data": {
    "positions": [
      {
        "id": "pos_123",
        "symbol": "BTC/USDT",
        "side": "long",
        "entry": 50000.0,
        "pnlR": 0.5
      }
    ],
    "timestamp": 1642248000000
  }
}
```

## Error Handling

All API endpoints return appropriate HTTP status codes:

- `200` - Success
- `400` - Bad Request (invalid parameters)
- `404` - Not Found
- `422` - Unprocessable Entity (validation error)
- `500` - Internal Server Error

**Error Response Format:**
```json
{
  "detail": "Error message description",
  "status_code": 400
}
```

## Rate Limiting

Currently, no rate limiting is implemented. In production, consider implementing rate limiting based on:
- Requests per minute per IP
- API key usage limits
- Resource consumption limits

## Examples

### Complete Trading Session

1. **Check system health:**
   ```bash
   curl http://localhost:8000/api/health
   ```

2. **Start engine:**
   ```bash
   curl -X POST http://localhost:8000/api/engine/start \
     -H "Content-Type: application/json" \
     -d '{"preset": "breakout_v1", "mode": "paper"}'
   ```

3. **Monitor positions:**
   ```bash
   curl http://localhost:8000/api/positions
   ```

4. **Check metrics:**
   ```bash
   curl http://localhost:8000/api/metrics/summary
   ```

5. **Stop engine:**
   ```bash
   curl -X POST http://localhost:8000/api/engine/stop
   ```

### WebSocket Monitoring

```javascript
const ws = new WebSocket('ws://localhost:8000/ws');

ws.onmessage = function(event) {
  const message = JSON.parse(event.data);
  console.log('Received:', message.type, message.data);
};

ws.onopen = function() {
  console.log('WebSocket connected');
};
```

## Changelog

### Version 1.0.0 (2025-01-16)

- Initial API release
- Engine control endpoints
- Trading data endpoints
- Preset management
- Scanner functionality
- Performance analytics
- Metrics and monitoring
- WebSocket real-time updates
- Comprehensive error handling
- Detailed logging and metrics collection
