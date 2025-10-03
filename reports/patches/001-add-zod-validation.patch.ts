// ============================================
// PATCH 001: Add Zod Runtime Validation
// ============================================
// Priority: P0 - Critical
// Impact: Prevents runtime type errors
// Files: frontend/src/types/websocket.ts (new), frontend/src/store/useWebSocketStore.ts

// File: frontend/src/types/websocket.ts (NEW)
import { z } from 'zod';

// Base schemas
const BaseMessageSchema = z.object({
  ts: z.number(),
});

// Individual message schemas
export const HeartbeatMessageSchema = BaseMessageSchema.extend({
  type: z.literal('HEARTBEAT'),
  data: z.object({
    latencyMs: z.number(),
  }),
});

export const EngineUpdateMessageSchema = BaseMessageSchema.extend({
  type: z.literal('ENGINE_UPDATE'),
  data: z.object({
    state: z.string(),
    running: z.boolean(),
    timestamp: z.number(),
  }),
});

export const SignalMessageSchema = BaseMessageSchema.extend({
  type: z.literal('SIGNAL'),
  data: z.object({
    signals: z.array(z.record(z.any())),
    timestamp: z.number(),
  }),
});

export const ScanResultMessageSchema = BaseMessageSchema.extend({
  type: z.literal('SCAN_RESULT'),
  data: z.object({
    results: z.array(z.record(z.any())),
    timestamp: z.number(),
  }),
});

export const OrderPlacedMessageSchema = BaseMessageSchema.extend({
  type: z.literal('ORDER_PLACED'),
  data: z.object({
    order: z.record(z.any()),
    timestamp: z.number(),
  }),
});

export const OrderUpdatedMessageSchema = BaseMessageSchema.extend({
  type: z.literal('ORDER_UPDATED'),
  data: z.object({
    order: z.record(z.any()),
    timestamp: z.number(),
  }),
});

export const OrderCanceledMessageSchema = BaseMessageSchema.extend({
  type: z.literal('ORDER_CANCELED'),
  data: z.object({
    order: z.record(z.any()),
    timestamp: z.number(),
  }),
});

export const PositionOpenMessageSchema = BaseMessageSchema.extend({
  type: z.literal('POSITION_OPEN'),
  data: z.object({
    position: z.record(z.any()),
    timestamp: z.number(),
  }),
});

export const PositionUpdateMessageSchema = BaseMessageSchema.extend({
  type: z.literal('POSITION_UPDATE'),
  data: z.object({
    position: z.record(z.any()),
    timestamp: z.number(),
  }),
});

export const PositionCloseMessageSchema = BaseMessageSchema.extend({
  type: z.literal('POSITION_CLOSE'),
  data: z.object({
    position: z.record(z.any()),
    timestamp: z.number(),
  }),
});

export const KillSwitchMessageSchema = BaseMessageSchema.extend({
  type: z.literal('KILL_SWITCH'),
  data: z.object({
    reason: z.string().optional(),
  }),
});

export const StopMovedMessageSchema = BaseMessageSchema.extend({
  type: z.literal('STOP_MOVED'),
  data: z.object({
    position_id: z.string(),
  }),
});

export const TakeProfitMessageSchema = BaseMessageSchema.extend({
  type: z.literal('TAKE_PROFIT'),
  data: z.object({
    position_id: z.string(),
    pnl: z.number().optional(),
  }),
});

// Discriminated union
export const WebSocketMessageSchema = z.discriminatedUnion('type', [
  HeartbeatMessageSchema,
  EngineUpdateMessageSchema,
  SignalMessageSchema,
  ScanResultMessageSchema,
  OrderPlacedMessageSchema,
  OrderUpdatedMessageSchema,
  OrderCanceledMessageSchema,
  PositionOpenMessageSchema,
  PositionUpdateMessageSchema,
  PositionCloseMessageSchema,
  KillSwitchMessageSchema,
  StopMovedMessageSchema,
  TakeProfitMessageSchema,
]);

// TypeScript types inferred from schemas
export type WebSocketMessage = z.infer<typeof WebSocketMessageSchema>;
export type HeartbeatMessage = z.infer<typeof HeartbeatMessageSchema>;
export type EngineUpdateMessage = z.infer<typeof EngineUpdateMessageSchema>;
export type SignalMessage = z.infer<typeof SignalMessageSchema>;
export type ScanResultMessage = z.infer<typeof ScanResultMessageSchema>;
export type OrderPlacedMessage = z.infer<typeof OrderPlacedMessageSchema>;
export type OrderUpdatedMessage = z.infer<typeof OrderUpdatedMessageSchema>;
export type OrderCanceledMessage = z.infer<typeof OrderCanceledMessageSchema>;
export type PositionOpenMessage = z.infer<typeof PositionOpenMessageSchema>;
export type PositionUpdateMessage = z.infer<typeof PositionUpdateMessageSchema>;
export type PositionCloseMessage = z.infer<typeof PositionCloseMessageSchema>;
export type KillSwitchMessage = z.infer<typeof KillSwitchMessageSchema>;
export type StopMovedMessage = z.infer<typeof StopMovedMessageSchema>;
export type TakeProfitMessage = z.infer<typeof TakeProfitMessageSchema>;

// ============================================
// File: frontend/src/store/useWebSocketStore.ts (MODIFIED)

import { create } from 'zustand';
import { devtools } from 'zustand/middleware';
import { useAppStore } from './useAppStore';
import { WebSocketMessageSchema, type WebSocketMessage } from '../types/websocket';
import type { OrderEvent, PositionEvent } from '../types';

// ... existing interface ...

export const useWebSocketStore = create<WebSocketState>()(
  devtools(
    (set, get) => ({
      // ... existing state ...

      connect: () => {
        // ... existing connection logic ...

        socket.onmessage = (event) => {
          try {
            const raw = JSON.parse(event.data);
            
            // ✅ ADDED: Runtime validation with Zod
            const result = WebSocketMessageSchema.safeParse(raw);
            
            if (!result.success) {
              console.error('Invalid WebSocket message:', {
                raw,
                errors: result.error.errors
              });
              
              // Send to error tracking
              if (window.Sentry) {
                window.Sentry.captureException(new Error('Invalid WS message'), {
                  extra: { raw, zodErrors: result.error.errors }
                });
              }
              
              return;
            }
            
            const message = result.data;
            get().addMessage(message);
            
            // ✅ Type-safe message handling
            switch (message.type) {
              case 'HEARTBEAT':
                useAppStore.getState().setLastHeartbeat(message.ts);
                break;
                
              case 'ENGINE_UPDATE':
                if (message.data) {
                  useAppStore.getState().setEngineStatus({
                    state: message.data.state || 'IDLE',
                    running: message.data.running || false,
                    preset: null,
                    mode: 'paper',
                    startedAt: null,
                    slots: 0,
                    openPositions: 0,
                    latencyMs: 50,
                    dailyR: 0.0,
                    consecutiveLosses: 0
                  });
                }
                break;
                
              case 'ORDER_PLACED':
              case 'ORDER_UPDATED':
              case 'ORDER_CANCELED':
                if (message.data?.order) {
                  get().addOrderEvent(message.data.order as OrderEvent);
                }
                break;
                
              case 'POSITION_OPEN':
              case 'POSITION_UPDATE':
              case 'POSITION_CLOSE':
                if (message.data?.position) {
                  get().addPositionEvent(message.data.position as PositionEvent);
                }
                break;
                
              case 'KILL_SWITCH':
                if (message.data) {
                  useAppStore.getState().addNotification({
                    type: 'error',
                    title: 'Kill Switch Activated',
                    message: message.data.reason || 'Kill switch has been activated',
                    duration: 10000
                  });
                }
                break;
                
              case 'STOP_MOVED':
                if (message.data) {
                  useAppStore.getState().addNotification({
                    type: 'info',
                    title: 'Stop Loss Updated',
                    message: `Stop moved for position ${message.data.position_id}`,
                    duration: 5000
                  });
                }
                break;
                
              case 'TAKE_PROFIT':
                if (message.data) {
                  useAppStore.getState().addNotification({
                    type: 'success',
                    title: 'Take Profit Executed',
                    message: `Take profit for position ${message.data.position_id}: ${message.data.pnl?.toFixed(2) || '?'} USD`,
                    duration: 5000
                  });
                }
                break;
                
              default:
                // Exhaustive check - TypeScript will error if we miss a case
                const _exhaustiveCheck: never = message;
                return _exhaustiveCheck;
            }
          } catch (error) {
            console.error('Failed to parse WebSocket message:', error);
          }
        };

        // ... rest of socket setup ...
      },

      // ... rest of store implementation ...
    }),
    {
      name: 'websocket-store',
    }
  )
);

// ============================================
// Installation:
// 1. Install zod if not already: npm install zod
// 2. Create new file: frontend/src/types/websocket.ts
// 3. Update frontend/src/store/useWebSocketStore.ts with new validation
// 4. Test WebSocket connection and verify validation works
// 5. Add Sentry integration for error tracking

// Testing:
// - Send invalid message from backend and verify error is caught
// - Send valid messages and verify they're processed correctly
// - Check console for validation errors
