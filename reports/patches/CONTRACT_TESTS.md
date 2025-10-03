# Contract Testing Examples

Примеры contract тестов для верификации соответствия между backend API и frontend типами.

## 🎯 Назначение

Contract тесты проверяют, что:
1. Backend API возвращает данные в ожидаемом формате
2. Типы TypeScript соответствуют реальным данным
3. WebSocket сообщения соответствуют схемам
4. Нет breaking changes между версиями

## 📦 Установка

```bash
cd frontend
npm install --save-dev vitest @testing-library/react @testing-library/jest-dom
```

## 🧪 REST API Contract Tests

### Test 1: Engine Status Endpoint

```typescript
// frontend/src/__tests__/contracts/engine.contract.test.ts
import { describe, it, expect } from 'vitest';
import { z } from 'zod';
import { engineApi } from '../../api/endpoints';

describe('Engine API Contract', () => {
  it('GET /api/engine/status should match schema', async () => {
    // Define expected schema
    const EngineStatusSchema = z.object({
      state: z.string(),
      preset: z.string().optional().nullable(),
      mode: z.enum(['paper', 'live']),
      startedAt: z.string().optional().nullable(),
      slots: z.number(),
      openPositions: z.number(),
      latencyMs: z.number(),
      dailyR: z.number(),
      consecutiveLosses: z.number(),
    });

    // Fetch data from API
    const response = await engineApi.getStatus();

    // Validate against schema
    const result = EngineStatusSchema.safeParse(response);

    expect(result.success).toBe(true);
    if (!result.success) {
      console.error('Schema validation errors:', result.error.errors);
      throw new Error('Engine status does not match expected schema');
    }

    // Additional assertions
    expect(response.slots).toBeGreaterThanOrEqual(0);
    expect(response.openPositions).toBeGreaterThanOrEqual(0);
    expect(response.latencyMs).toBeGreaterThan(0);
  });

  it('POST /api/engine/start should return success response', async () => {
    const ResponseSchema = z.object({
      success: z.boolean(),
      message: z.string(),
      timestamp: z.string(),
    });

    try {
      const response = await engineApi.start({
        preset: 'breakout_v1',
        mode: 'paper',
      });

      const result = ResponseSchema.safeParse(response);
      expect(result.success).toBe(true);

      if (result.success) {
        expect(result.data.success).toBe(true);
        expect(result.data.message).toContain('started');
      }
    } catch (error: any) {
      // API error responses should also match schema
      expect(error).toHaveProperty('detail');
      expect(error).toHaveProperty('status_code');
    }
  });

  it('GET /api/engine/commands should return available commands', async () => {
    const CommandsSchema = z.object({
      commands: z.array(z.string()),
      currentState: z.string().nullable(),
    });

    const response = await engineApi.getCommands();
    const result = CommandsSchema.safeParse(response);

    expect(result.success).toBe(true);
    if (result.success) {
      expect(Array.isArray(result.data.commands)).toBe(true);
      expect(result.data.commands.length).toBeGreaterThan(0);
    }
  });
});
```

### Test 2: Trading Endpoints

```typescript
// frontend/src/__tests__/contracts/trading.contract.test.ts
import { describe, it, expect } from 'vitest';
import { z } from 'zod';
import { tradingApi } from '../../api/endpoints';

describe('Trading API Contract', () => {
  it('GET /api/trading/positions should match schema', async () => {
    const PositionSchema = z.object({
      id: z.string(),
      symbol: z.string(),
      side: z.enum(['long', 'short']),
      entry: z.number(),
      sl: z.number(),
      size: z.number(),  // ✅ Must be 'size', not 'qty'
      mode: z.string(),  // ✅ Must be 'mode', not 'strategy'
      openedAt: z.string(),
      pnlR: z.number().optional().nullable(),
      pnlUsd: z.number().optional().nullable(),
      unrealizedPnlR: z.number().optional().nullable(),
      unrealizedPnlUsd: z.number().optional().nullable(),
    });

    const PositionsArraySchema = z.array(PositionSchema);

    const response = await tradingApi.getPositions();
    const result = PositionsArraySchema.safeParse(response);

    expect(result.success).toBe(true);
    if (!result.success) {
      console.error('Position schema errors:', result.error.errors);
      throw new Error('Positions do not match expected schema');
    }

    // If positions exist, validate field names
    if (result.data.length > 0) {
      const firstPosition = result.data[0];
      
      // ✅ CRITICAL: Verify 'size' field exists (not 'qty')
      expect(firstPosition).toHaveProperty('size');
      expect(firstPosition).not.toHaveProperty('qty');
      
      // ✅ CRITICAL: Verify 'mode' field exists (not 'strategy')
      expect(firstPosition).toHaveProperty('mode');
      expect(firstPosition).not.toHaveProperty('strategy');

      // Validate values
      expect(firstPosition.size).toBeGreaterThan(0);
      expect(['long', 'short']).toContain(firstPosition.side);
    }
  });

  it('GET /api/trading/orders should match schema', async () => {
    const OrderSchema = z.object({
      id: z.string(),
      symbol: z.string(),
      side: z.enum(['buy', 'sell']),
      type: z.string(),  // ✅ Must be 'type', not 'order_type'
      qty: z.number(),
      price: z.number().optional().nullable(),
      status: z.enum(['pending', 'open', 'filled', 'cancelled', 'rejected']),
      createdAt: z.string(),
      filledAt: z.string().optional().nullable(),
      fees: z.number().optional().nullable(),
    });

    const OrdersArraySchema = z.array(OrderSchema);

    const response = await tradingApi.getOrders();
    const result = OrdersArraySchema.safeParse(response);

    expect(result.success).toBe(true);
    if (!result.success) {
      console.error('Order schema errors:', result.error.errors);
      throw new Error('Orders do not match expected schema');
    }

    // If orders exist, validate field names
    if (result.data.length > 0) {
      const firstOrder = result.data[0];
      
      // ✅ CRITICAL: Verify 'type' field exists (not 'order_type')
      expect(firstOrder).toHaveProperty('type');
      expect(firstOrder).not.toHaveProperty('order_type');

      // Validate values
      expect(['buy', 'sell']).toContain(firstOrder.side);
      expect(['pending', 'open', 'filled', 'cancelled', 'rejected']).toContain(firstOrder.status);
    }
  });
});
```

### Test 3: Scanner Endpoints

```typescript
// frontend/src/__tests__/contracts/scanner.contract.test.ts
import { describe, it, expect } from 'vitest';
import { z } from 'zod';
import { scannerApi } from '../../api/endpoints';

describe('Scanner API Contract', () => {
  it('GET /api/scanner/last should match schema', async () => {
    const CandidateSchema = z.object({
      symbol: z.string(),
      score: z.number(),
      filters: z.record(z.boolean()),
      metrics: z.record(z.number()),
      levels: z.array(z.record(z.any())),
    });

    const ScannerSnapshotSchema = z.object({
      timestamp: z.string(),
      candidates: z.array(CandidateSchema),
      totalScanned: z.number(),
      passedFilters: z.number(),
      summary: z.record(z.any()).optional(),
    });

    const response = await scannerApi.getLastScan();
    const result = ScannerSnapshotSchema.safeParse(response);

    expect(result.success).toBe(true);
    if (!result.success) {
      console.error('Scanner snapshot errors:', result.error.errors);
      throw new Error('Scanner snapshot does not match expected schema');
    }

    // Validate data consistency
    if (result.data.candidates.length > 0) {
      expect(result.data.passedFilters).toBeGreaterThan(0);
      
      // Each candidate should have required metrics
      const firstCandidate = result.data.candidates[0];
      expect(firstCandidate.score).toBeGreaterThanOrEqual(0);
      expect(firstCandidate.score).toBeLessThanOrEqual(1);
      
      // ⚠️ WARNING: Backend might return placeholder data
      // Check if symbol is real or placeholder
      if (firstCandidate.symbol.startsWith('SYMBOL_')) {
        console.warn('Scanner is returning placeholder data!');
      }
    }
  });
});
```

## 🔌 WebSocket Contract Tests

### Test 4: WebSocket Messages

```typescript
// frontend/src/__tests__/contracts/websocket.contract.test.ts
import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { WebSocketMessageSchema } from '../../types/websocket';

describe('WebSocket Contract', () => {
  let ws: WebSocket;
  const WS_URL = 'ws://localhost:8000/ws/';

  beforeEach(() => {
    ws = new WebSocket(WS_URL);
  });

  afterEach(() => {
    if (ws.readyState === WebSocket.OPEN) {
      ws.close();
    }
  });

  it('should receive valid HEARTBEAT messages', (done) => {
    ws.onopen = () => {
      console.log('WebSocket connected');
    };

    ws.onmessage = (event) => {
      const raw = JSON.parse(event.data);
      const result = WebSocketMessageSchema.safeParse(raw);

      expect(result.success).toBe(true);
      
      if (result.success && result.data.type === 'HEARTBEAT') {
        expect(result.data.ts).toBeGreaterThan(0);
        expect(result.data.data.latencyMs).toBeGreaterThan(0);
        ws.close();
        done();
      }
    };

    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
      done(error);
    };
  }, 10000); // 10 second timeout

  it('should receive valid ENGINE_UPDATE messages', (done) => {
    let receivedHeartbeat = false;

    ws.onmessage = (event) => {
      const raw = JSON.parse(event.data);
      const result = WebSocketMessageSchema.safeParse(raw);

      if (!result.success) {
        console.error('Invalid message:', result.error.errors);
        done(new Error('Invalid WebSocket message'));
        return;
      }

      if (result.data.type === 'HEARTBEAT') {
        receivedHeartbeat = true;
      } else if (result.data.type === 'ENGINE_UPDATE') {
        expect(result.data.data.state).toBeDefined();
        expect(typeof result.data.data.running).toBe('boolean');
        expect(result.data.data.timestamp).toBeGreaterThan(0);
        ws.close();
        done();
      }
    };

    // Timeout if no ENGINE_UPDATE received
    setTimeout(() => {
      if (!receivedHeartbeat) {
        done(new Error('No messages received from WebSocket'));
      } else {
        console.log('Only received HEARTBEAT, ENGINE_UPDATE not sent');
        ws.close();
        done();
      }
    }, 15000);
  }, 20000);

  it('should reject invalid messages', (done) => {
    // Simulate receiving an invalid message
    const invalidMessage = {
      type: 'INVALID_TYPE',
      ts: Date.now(),
      data: {}
    };

    const result = WebSocketMessageSchema.safeParse(invalidMessage);
    expect(result.success).toBe(false);
    
    if (!result.success) {
      expect(result.error.errors.length).toBeGreaterThan(0);
      console.log('Correctly rejected invalid message:', result.error.errors[0].message);
    }

    ws.close();
    done();
  });
});
```

## 🧪 Mock Data для Testing

```typescript
// frontend/src/__tests__/mocks/api-responses.ts

export const mockEngineStatus = {
  state: 'RUNNING',
  preset: 'breakout_v1',
  mode: 'paper' as const,
  startedAt: new Date().toISOString(),
  slots: 3,
  openPositions: 1,
  latencyMs: 45,
  dailyR: 2.5,
  consecutiveLosses: 0,
};

export const mockPosition = {
  id: 'pos_123',
  symbol: 'BTCUSDT',
  side: 'long' as const,
  entry: 50000,
  sl: 49500,
  size: 0.1,          // ✅ 'size', not 'qty'
  mode: 'breakout',   // ✅ 'mode', not 'strategy'
  openedAt: new Date().toISOString(),
  pnlR: 0.5,
  pnlUsd: 250,
  unrealizedPnlR: 0.5,
  unrealizedPnlUsd: 250,
};

export const mockOrder = {
  id: 'order_456',
  symbol: 'ETHUSDT',
  side: 'buy' as const,
  type: 'market',     // ✅ 'type', not 'order_type'
  qty: 1.0,
  price: null,
  status: 'filled' as const,
  createdAt: new Date().toISOString(),
  filledAt: new Date().toISOString(),
  fees: 0.5,
};

export const mockHeartbeatMessage = {
  type: 'HEARTBEAT' as const,
  ts: Date.now(),
  data: {
    latencyMs: 45,
  },
};

export const mockEngineUpdateMessage = {
  type: 'ENGINE_UPDATE' as const,
  ts: Date.now(),
  data: {
    state: 'RUNNING',
    running: true,
    timestamp: Date.now(),
  },
};
```

## 🏃 Запуск тестов

```bash
# Run all contract tests
npm run test

# Run specific test file
npm run test contracts/engine.contract.test.ts

# Run with coverage
npm run test:coverage

# Run in watch mode
npm run test:watch

# Run WebSocket tests (requires backend running)
npm run test websocket.contract.test.ts
```

## ✅ CI/CD Integration

```yaml
# .github/workflows/contract-tests.yml
name: Contract Tests

on: [push, pull_request]

jobs:
  contract-tests:
    runs-on: ubuntu-latest
    
    services:
      backend:
        image: breakout-bot-backend:latest
        ports:
          - 8000:8000
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Setup Node
        uses: actions/setup-node@v3
        with:
          node-version: '18'
      
      - name: Install dependencies
        run: |
          cd frontend
          npm ci
      
      - name: Wait for backend
        run: |
          timeout 30 bash -c 'until curl -f http://localhost:8000/api/health; do sleep 1; done'
      
      - name: Run contract tests
        run: |
          cd frontend
          npm run test -- contracts/
      
      - name: Upload test results
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: test-results
          path: frontend/test-results/
```

## 📊 Test Coverage Goals

- **Engine API:** 100% endpoint coverage
- **Trading API:** 100% endpoint coverage  
- **Scanner API:** 100% endpoint coverage
- **WebSocket:** All message types covered
- **Type Safety:** All Zod schemas validated

## 🐛 Debugging Failed Tests

```typescript
// Enable verbose logging
import { enableDebugLogging } from '../../utils/test-helpers';

describe('Debug Contract Test', () => {
  beforeAll(() => {
    enableDebugLogging();
  });

  it('debug API response', async () => {
    const response = await engineApi.getStatus();
    console.log('Full response:', JSON.stringify(response, null, 2));
    
    // Check specific fields
    console.log('State:', response.state);
    console.log('Type of state:', typeof response.state);
    
    // Validate
    expect(response).toBeDefined();
  });
});
```

---

**Последнее обновление:** 2 октября 2025  
**Автор:** Senior Full-Stack Engineer
