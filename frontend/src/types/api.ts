/**
 * TypeScript типы для API на основе Pydantic моделей бэкенда
 */

// ===== ENGINE TYPES =====
export interface EngineStatus {
  state:
    | 'IDLE'
    | 'RUNNING'
    | 'STOPPED'
    | 'running'
    | 'stopped'
    | 'initializing'
    | 'idle'
    | 'scanning'
    | 'level_building'
    | 'signal_wait'
    | 'sizing'
    | 'execution'
    | 'managing'
    | 'paused'
    | 'error'
    | 'emergency';
  preset?: string;
  mode: 'paper' | 'live';
  startedAt?: string;
  slots: number;
  openPositions: number;
  latencyMs: number;
  dailyR: number;
  consecutiveLosses: number;
}

export interface EngineMetrics {
  uptime: number;
  cycleCount: number;
  avgLatencyMs: number;
  totalSignals: number;
  totalTrades: number;
  dailyPnlR: number;
  maxDrawdownR: number;
}

export interface StartEngineRequest {
  preset: string;
  mode: 'paper' | 'live';
}

// ===== TRADING TYPES =====
export interface Position {
  id: string;
  symbol: string;
  side: 'long' | 'short';
  entry: number;
  sl: number;
  tp?: number; // Take profit level
  size: number;
  mode: string;
  openedAt: string;
  openTime?: string; // Alias for openedAt
  currentPrice?: number; // Current market price
  riskR?: number; // Risk in R
  pnlR?: number;
  pnlUsd?: number;
  unrealizedPnlR?: number;
  unrealizedPnlUsd?: number;
}

export interface Order {
  id: string;
  symbol: string;
  side: 'buy' | 'sell';
  type: 'market' | 'limit' | 'stop' | 'stop_limit';
  qty: number;
  price?: number;
  status: 'pending' | 'open' | 'filled' | 'cancelled' | 'rejected';
  createdAt: string;
  filledAt?: string;
  fees?: number;
}

// ===== SCANNER TYPES =====
export interface Candidate {
  symbol: string;
  score: number;
  filters: {
    liquidity: boolean;
    volatility: boolean;
    volume_surge: boolean;
    correlation: boolean;
    spread: boolean;
  };
  metrics: {
    vol_surge_1h: number;
    vol_surge_5m: number;
    oi_usd: number;
    atr15m_pct: number;
    bbwidth_pctile: number;
    corr_btc_15m: number;
    trades_per_min: number;
    spread_bps: number;
    depth_usd_0_5pct: number;
  };
  levels: {
    high: number;
    low: number;
  };
}

export interface ScannerSnapshot {
  timestamp: string;
  candidates: Candidate[];
  totalScanned: number;
  passedFilters: number;
  summary?: Record<string, any>;
}

export interface ScanRequest {
  preset: string;
  limit?: number;
  symbols?: string[];
}

// ===== PERFORMANCE TYPES =====
export interface EquityPoint {
  timestamp: string;
  value: number;
  cumulativeR: number;
}

export interface PerformanceMetrics {
  totalTrades: number;
  winRate: number;
  avgR: number;
  sharpeRatio: number;
  maxDrawdownR: number;
  profitFactor: number;
  consecutiveWins: number;
  consecutiveLosses: number;
}

export interface RDistributionPoint {
  r: number;
  count: number;
}

// ===== LOGS TYPES =====
export interface LogEntry {
  id: string;
  timestamp: string;
  level: 'DEBUG' | 'INFO' | 'WARNING' | 'ERROR';
  component: string;
  message: string;
  data?: Record<string, any>;
}

export interface LogsQuery {
  level?: string;
  component?: string;
  limit?: number;
}

// ===== CHARTS TYPES =====
export interface Candle {
  time: number;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface Level {
  price: number;
  type: 'support' | 'resistance';
  strength: number;
  timestamp: string;
}

// ===== PRESETS TYPES =====
export interface PresetSummary {
  name: string;
  description: string;
  risk_per_trade: number;
  max_positions: number;
  strategy_type: string;
}

export interface PresetConfig {
  name: string;
  config: Record<string, any>;
}

// ===== API RESPONSE TYPES =====
export interface ApiResponse<T = any> {
  success: boolean;
  message: string;
  data?: T;
  timestamp: string;
}

export interface ApiError {
  detail: string;
  status_code: number;
}

// ===== WEBSOCKET TYPES =====
export interface WebSocketMessage {
  type: 'HEARTBEAT' | 'ENGINE_UPDATE' | 'SIGNAL' | 'SCAN_RESULT' | 'ORDER_UPDATE' | 'ORDER_PLACED' | 'ORDER_UPDATED' | 'ORDER_CANCELED' | 'POSITION_OPEN' | 'POSITION_UPDATE' | 'POSITION_CLOSE' | 'KILL_SWITCH' | 'STOP_MOVED' | 'TAKE_PROFIT' | 'PRICE_UPDATE';
  ts: number;
  data: any;
}

// ===== UNIFIED EVENT TYPES =====
export interface OrderEvent {
  id: string;
  symbol: string;
  side: 'buy' | 'sell';
  type: 'market' | 'limit' | 'stop' | 'stop_limit';
  qty: number;
  price?: number;
  status: 'pending' | 'open' | 'filled' | 'cancelled' | 'rejected';
  createdAt: string;
  updatedAt?: string;
  filledAt?: string;
  fees?: number;
  reason?: string;
}

export interface PositionEvent {
  id: string;
  symbol: string;
  side: 'long' | 'short';
  entry: number;
  sl: number;
  tp?: number;
  size: number;
  mode: string;
  openedAt: string;
  updatedAt?: string;
  closedAt?: string;
  pnlR?: number;
  pnlUsd?: number;
  unrealizedPnlR?: number;
  unrealizedPnlUsd?: number;
  reason?: string;
}

// ===== HEALTH CHECK =====
export interface HealthCheck {
  status: 'healthy' | 'unhealthy';
  engine_initialized: boolean;
  engine_running: boolean;
  timestamp: string;
}
