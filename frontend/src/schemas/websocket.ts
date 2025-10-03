/**
 * Zod schemas for WebSocket message validation
 * Provides runtime type safety for all WebSocket messages
 */

import { z } from 'zod';

// Base message schema
const BaseMessageSchema = z.object({
  ts: z.number(),
  data: z.unknown().optional(),
});

// Engine Update Schema
const EngineUpdateDataSchema = z.object({
  state: z.string(),
  mode: z.enum(['paper', 'live']).optional(),
  preset: z.string().optional(),
  startedAt: z.string().optional(),
  slots: z.number().optional(),
  openPositions: z.number().optional(),
  latencyMs: z.number().optional(),
  dailyR: z.number().optional(),
  consecutiveLosses: z.number().optional(),
});

export const EngineUpdateMessageSchema = BaseMessageSchema.extend({
  type: z.literal('ENGINE_UPDATE'),
  data: EngineUpdateDataSchema.optional(),
});

// Order Event Schemas
const OrderDataSchema = z.object({
  id: z.string(),
  symbol: z.string(),
  side: z.enum(['buy', 'sell']),
  type: z.enum(['market', 'limit', 'stop', 'stop_limit']),
  qty: z.number(),
  price: z.number().optional(),
  status: z.enum(['pending', 'open', 'filled', 'cancelled', 'rejected']),
  createdAt: z.string(),
  updatedAt: z.string().optional(),
  filledAt: z.string().optional(),
  fees: z.number().optional(),
  reason: z.string().optional(),
});

export const OrderUpdateMessageSchema = BaseMessageSchema.extend({
  type: z.literal('ORDER_UPDATE'),
  data: z.object({
    order: OrderDataSchema.optional(),
  }).optional(),
});

export const OrderPlacedMessageSchema = BaseMessageSchema.extend({
  type: z.literal('ORDER_PLACED'),
  data: z.object({
    order: OrderDataSchema.optional(),
  }).optional(),
});

export const OrderUpdatedMessageSchema = BaseMessageSchema.extend({
  type: z.literal('ORDER_UPDATED'),
  data: z.object({
    order: OrderDataSchema.optional(),
  }).optional(),
});

export const OrderCanceledMessageSchema = BaseMessageSchema.extend({
  type: z.literal('ORDER_CANCELED'),
  data: z.object({
    order: OrderDataSchema.optional(),
  }).optional(),
});

// Position Event Schemas
const PositionDataSchema = z.object({
  id: z.string(),
  symbol: z.string(),
  side: z.enum(['long', 'short']),
  entry: z.number(),
  sl: z.number(),
  tp: z.number().optional(),
  size: z.number(),
  mode: z.string(),
  openedAt: z.string(),
  updatedAt: z.string().optional(),
  closedAt: z.string().optional(),
  pnlR: z.number().optional(),
  pnlUsd: z.number().optional(),
  unrealizedPnlR: z.number().optional(),
  unrealizedPnlUsd: z.number().optional(),
  reason: z.string().optional(),
});

export const PositionOpenMessageSchema = BaseMessageSchema.extend({
  type: z.literal('POSITION_OPEN'),
  data: z.object({
    position: PositionDataSchema.optional(),
  }).optional(),
});

export const PositionUpdateMessageSchema = BaseMessageSchema.extend({
  type: z.literal('POSITION_UPDATE'),
  data: z.object({
    position: PositionDataSchema.optional(),
  }).optional(),
});

export const PositionCloseMessageSchema = BaseMessageSchema.extend({
  type: z.literal('POSITION_CLOSE'),
  data: z.object({
    position: PositionDataSchema.optional(),
  }).optional(),
});

// Signal Schema
export const SignalMessageSchema = BaseMessageSchema.extend({
  type: z.literal('SIGNAL'),
  data: z.unknown().optional(),
});

// Scan Result Schema
export const ScanResultMessageSchema = BaseMessageSchema.extend({
  type: z.literal('SCAN_RESULT'),
  data: z.unknown().optional(),
});

// Kill Switch Schema
export const KillSwitchMessageSchema = BaseMessageSchema.extend({
  type: z.literal('KILL_SWITCH'),
  data: z.object({
    reason: z.string().optional(),
    triggered_at: z.string().optional(),
  }).optional(),
});

// Stop Moved Schema
export const StopMovedMessageSchema = BaseMessageSchema.extend({
  type: z.literal('STOP_MOVED'),
  data: z.object({
    position_id: z.string().optional(),
    old_sl: z.number().optional(),
    new_sl: z.number().optional(),
  }).optional(),
});

// Take Profit Schema
export const TakeProfitMessageSchema = BaseMessageSchema.extend({
  type: z.literal('TAKE_PROFIT'),
  data: z.object({
    position_id: z.string().optional(),
    pnl: z.number().optional(),
    pnlR: z.number().optional(),
  }).optional(),
});

// Heartbeat Schema
export const HeartbeatMessageSchema = BaseMessageSchema.extend({
  type: z.literal('HEARTBEAT'),
});

// Discriminated union of all message types
export const WebSocketMessageSchema = z.discriminatedUnion('type', [
  EngineUpdateMessageSchema,
  OrderUpdateMessageSchema,
  OrderPlacedMessageSchema,
  OrderUpdatedMessageSchema,
  OrderCanceledMessageSchema,
  PositionOpenMessageSchema,
  PositionUpdateMessageSchema,
  PositionCloseMessageSchema,
  SignalMessageSchema,
  ScanResultMessageSchema,
  KillSwitchMessageSchema,
  StopMovedMessageSchema,
  TakeProfitMessageSchema,
  HeartbeatMessageSchema,
]);

// Type inference from schemas
export type WebSocketMessageValidated = z.infer<typeof WebSocketMessageSchema>;
export type EngineUpdateMessage = z.infer<typeof EngineUpdateMessageSchema>;
export type OrderUpdateMessage = z.infer<typeof OrderUpdateMessageSchema>;
export type PositionUpdateMessage = z.infer<typeof PositionUpdateMessageSchema>;

/**
 * Validates a WebSocket message using Zod schema
 * @param rawMessage - Raw message object from WebSocket
 * @returns Validated message or null if validation fails
 */
export function validateWebSocketMessage(rawMessage: unknown): WebSocketMessageValidated | null {
  try {
    return WebSocketMessageSchema.parse(rawMessage);
  } catch (error) {
    console.error('WebSocket message validation failed:', error);
    if (error instanceof z.ZodError) {
      console.error('Validation errors:', error.issues);
    }
    return null;
  }
}

/**
 * Safe parse that returns result with success flag
 * @param rawMessage - Raw message object from WebSocket
 * @returns SafeParseReturnType with success flag and data/error
 */
export function safeParseWebSocketMessage(rawMessage: unknown) {
  return WebSocketMessageSchema.safeParse(rawMessage);
}
