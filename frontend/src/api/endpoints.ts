/**
 * API эндпоинты
 */

import { apiClient } from './client';
import type {
  EngineStatus,
  EngineMetrics,
  StartEngineRequest,
  Position,
  Order,
  ScannerSnapshot,
  ScanRequest,
  EquityPoint,
  PerformanceMetrics,
  RDistributionPoint,
  LogEntry,
  LogsQuery,
  Candle,
  Level,
  PresetSummary,
  PresetConfig,
  HealthCheck,
} from '../types';

// ===== ENGINE ENDPOINTS =====
export const engineApi = {
  getStatus: (): Promise<EngineStatus> => 
    apiClient.get('/api/engine/status'),
  
  getMetrics: (): Promise<EngineMetrics> => 
    apiClient.get('/api/engine/metrics'),
  
  start: (request: StartEngineRequest): Promise<{ success: boolean; message: string; timestamp: string }> => 
    apiClient.post('/api/engine/start', request),
  
  stop: (): Promise<{ success: boolean; message: string; timestamp: string }> => 
    apiClient.post('/api/engine/stop'),
  
  reload: (): Promise<{ success: boolean; message: string; timestamp: string }> => 
    apiClient.post('/api/engine/reload'),
  
  getCommands: async (): Promise<{ commands: string[]; currentState: string | null }> => {
    const response = await apiClient.get('/api/engine/commands');

    if (Array.isArray(response)) {
      return { commands: response, currentState: null };
    }

    return {
      commands: response?.commands ?? [],
      currentState: response?.current_state ?? null,
    };
  },
  
  executeCommand: (command: string): Promise<{ success: boolean; message: string; timestamp: string }> => 
    apiClient.post('/api/engine/command', { command }),
};

// ===== TRADING ENDPOINTS =====
export const tradingApi = {
  getPositions: (): Promise<Position[]> => 
    apiClient.get('/api/trading/positions'),
  
  getPosition: (id: string): Promise<Position> => 
    apiClient.get(`/api/trading/positions/${id}`),
  
  getOrders: (): Promise<Order[]> => 
    apiClient.get('/api/trading/orders'),
  
  cancelOrder: (id: string): Promise<{ success: boolean; message: string; timestamp: string }> => 
    apiClient.delete(`/api/trading/orders/${id}`),
};

// ===== SCANNER ENDPOINTS =====
export const scannerApi = {
  getLastScan: (): Promise<ScannerSnapshot> => 
    apiClient.get('/api/scanner/last'),
  
  scanMarket: (request: ScanRequest): Promise<{ success: boolean; message: string; timestamp: string }> => 
    apiClient.post('/api/scanner/scan', request),
};

// ===== PERFORMANCE ENDPOINTS =====
export const performanceApi = {
  getEquityHistory: (timeRange?: string): Promise<EquityPoint[]> => 
    apiClient.get('/api/performance/equity', { params: { time_range: timeRange } }),
  
  getMetrics: (): Promise<PerformanceMetrics> => 
    apiClient.get('/api/performance/metrics'),
  
  getRDistribution: (): Promise<RDistributionPoint[]> => 
    apiClient.get('/api/performance/r-distribution'),
};

// ===== LOGS ENDPOINTS =====
export const logsApi = {
  getLogs: (query: LogsQuery = {}): Promise<LogEntry[]> => 
    apiClient.get('/api/logs', { params: query }),
};

// ===== CHARTS ENDPOINTS =====
export const chartsApi = {
  getCandles: (symbol: string, timeframe: string = '15m'): Promise<Candle[]> => 
    apiClient.get(`/api/charts/candles/${symbol}`, { params: { timeframe } }),
  
  getLevels: (symbol: string): Promise<Level[]> => 
    apiClient.get(`/api/charts/levels/${symbol}`),
};

// ===== PRESETS ENDPOINTS =====
export const presetsApi = {
  getPresets: (): Promise<PresetSummary[]> => 
    apiClient.get('/api/presets/'),
  
  getPreset: (name: string): Promise<PresetConfig> => 
    apiClient.get(`/api/presets/${name}`),
  
  updatePreset: (name: string, config: Record<string, any>): Promise<{ success: boolean; message: string; timestamp: string }> => 
    apiClient.put(`/api/presets/${name}`, config),
};

// ===== MONITORING ENDPOINTS =====
export const monitoringApi = {
  getActiveSessions: () => apiClient.get('/api/monitoring/sessions'),
  getCurrentSession: () => apiClient.get('/api/monitoring/current-session'),
  getSessionDetails: (sessionId: string) => apiClient.get(`/api/monitoring/sessions/${sessionId}`),
  getSessionVisualization: (sessionId: string) => apiClient.get(`/api/monitoring/sessions/${sessionId}/visualization`),
  getSessionCheckpoints: (sessionId: string, limit: number = 100) => 
    apiClient.get(`/api/monitoring/checkpoints/${sessionId}?limit=${limit}`),
  getRealTimeMetrics: () => apiClient.get('/api/monitoring/metrics'),
  getSessionSummary: (sessionId: string) => apiClient.get(`/api/monitoring/sessions/${sessionId}/summary`),
  
  // State Machine endpoints
  getStateMachineStatus: (sessionId?: string) => 
    apiClient.get(`/api/monitoring/state-machine/status${sessionId ? `?session_id=${sessionId}` : ''}`),
  getStateTransitions: (sessionId?: string, limit: number = 20) => 
    apiClient.get(`/api/monitoring/state-machine/transitions?limit=${limit}${sessionId ? `&session_id=${sessionId}` : ''}`),
  getStateMachinePerformance: (sessionId?: string) => 
    apiClient.get(`/api/monitoring/state-machine/performance${sessionId ? `?session_id=${sessionId}` : ''}`),
  endSession: (sessionId: string, status: string = 'completed') => 
    apiClient.post(`/api/monitoring/sessions/${sessionId}/end`, { status }),
};

// ===== SYSTEM ENDPOINTS =====
export const systemApi = {
  healthCheck: (): Promise<HealthCheck> => 
    apiClient.get('/api/health'),
  
  getRoot: (): Promise<{ message: string; version: string; docs: string }> => 
    apiClient.get('/api/'),
};
