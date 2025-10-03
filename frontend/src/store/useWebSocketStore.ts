/**
 * WebSocket store для real-time обновлений
 */

import { create } from 'zustand';
import { devtools } from 'zustand/middleware';
import type { WebSocketMessage, OrderEvent, PositionEvent } from '../types';
import { useAppStore } from './useAppStore';
import { QueryClient } from '@tanstack/react-query';
import { validateWebSocketMessage } from '../schemas/websocket';

// Create a singleton QueryClient instance to avoid memory leaks
let queryClientInstance: QueryClient | null = null;

export const getQueryClient = (): QueryClient => {
  if (!queryClientInstance) {
    queryClientInstance = new QueryClient();
  }
  return queryClientInstance;
};

interface WebSocketState {
  socket: WebSocket | null;
  isConnected: boolean;
  isConnecting: boolean;
  lastMessage: WebSocketMessage | null;
  messageHistory: WebSocketMessage[];
  reconnectAttempts: number;
  
  // Event stores
  orderEvents: OrderEvent[];
  positionEvents: PositionEvent[];
  
  // Actions
  connect: () => void;
  disconnect: () => void;
  sendMessage: (message: any) => void;
  addMessage: (message: WebSocketMessage) => void;
  clearHistory: () => void;
  
  // Event actions
  addOrderEvent: (event: OrderEvent) => void;
  addPositionEvent: (event: PositionEvent) => void;
  clearEvents: () => void;
}

export const useWebSocketStore = create<WebSocketState>()(
  devtools(
    (set, get) => ({
      socket: null,
      isConnected: false,
      isConnecting: false,
      lastMessage: null,
      messageHistory: [],
      reconnectAttempts: 0,
      orderEvents: [],
      positionEvents: [],

      connect: () => {
        const state = get();
        if (state.socket?.readyState === WebSocket.OPEN) {
          return;
        }

        set({ isConnecting: true });

        const wsUrl = import.meta.env.VITE_WS_URL || 'ws://localhost:8000/ws/';
        const socket = new WebSocket(wsUrl);

        socket.onopen = () => {
          set({ 
            socket, 
            isConnected: true, 
            isConnecting: false,
            reconnectAttempts: 0  // Reset counter on successful connection
          });
        };

        socket.onmessage = (event) => {
          try {
            const rawMessage = JSON.parse(event.data);
            
            // Validate message with Zod schema
            const validatedMessage = validateWebSocketMessage(rawMessage);
            
            if (!validatedMessage) {
              console.error('Invalid WebSocket message received:', rawMessage);
              return;
            }
            
            // Type-safe message processing
            const message = validatedMessage as WebSocketMessage;
            get().addMessage(message);
            
            // Handle real-time updates based on message type
            switch (message.type) {
              case 'ENGINE_UPDATE':
                // Update engine status in real-time
                if (message.data) {
                  useAppStore.getState().setEngineStatus({
                    state: message.data.state || 'IDLE',
                    preset: undefined,
                    mode: message.data.mode || 'paper',
                    startedAt: undefined,
                    slots: message.data.slots || 0,
                    openPositions: message.data.openPositions || 0,
                    latencyMs: message.data.latencyMs || 50,
                    dailyR: message.data.dailyR || 0.0,
                    consecutiveLosses: message.data.consecutiveLosses || 0
                  });
                }
                break;
              case 'ORDER_UPDATE':
                // Update orders in real-time - invalidate React Query cache
                const queryClient = getQueryClient();
                queryClient.invalidateQueries({ queryKey: ['trading', 'orders'] });
                break;
              case 'SIGNAL':
                // Update signals in real-time - invalidate React Query cache
                getQueryClient().invalidateQueries({ queryKey: ['scanner', 'signals'] });
                break;
              case 'SCAN_RESULT':
                // Update scanner results in real-time - invalidate React Query cache
                getQueryClient().invalidateQueries({ queryKey: ['scanner', 'results'] });
                break;
              case 'ORDER_PLACED':
              case 'ORDER_UPDATED':
              case 'ORDER_CANCELED':
                // Handle order events - store in local state and invalidate cache
                if (message.data?.order) {
                  get().addOrderEvent(message.data.order);
                }
                getQueryClient().invalidateQueries({ queryKey: ['trading', 'orders'] });
                break;
              case 'POSITION_OPEN':
              case 'POSITION_UPDATE':
              case 'POSITION_CLOSE':
                // Handle position events - store in local state and invalidate cache
                if (message.data?.position) {
                  get().addPositionEvent(message.data.position);
                }
                getQueryClient().invalidateQueries({ queryKey: ['trading', 'positions'] });
                break;
              case 'KILL_SWITCH':
                // Handle kill switch events
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
                // Handle stop loss movement
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
                // Handle take profit events
                if (message.data) {
                  useAppStore.getState().addNotification({
                    type: 'success',
                    title: 'Take Profit Executed',
                    message: `Take profit for position ${message.data.position_id}: ${message.data.pnl?.toFixed(2)} USD`,
                    duration: 5000
                  });
                }
                break;
              case 'HEARTBEAT':
                // Update heartbeat timestamp
                useAppStore.getState().setLastHeartbeat(message.ts);
                break;
              default:
                // Handle other message types
                break;
            }
          } catch (error) {
            console.error('Failed to parse WebSocket message:', error);
          }
        };

        socket.onclose = () => {
          const attempts = get().reconnectAttempts;
          
          set({ 
            socket: null, 
            isConnected: false, 
            isConnecting: false,
            reconnectAttempts: attempts + 1
          });
          
          // Exponential backoff: 1s, 2s, 4s, 8s, 16s, max 30s
          const delay = Math.min(1000 * Math.pow(2, attempts), 30000);
          
          console.log(`WebSocket closed. Reconnecting in ${delay}ms (attempt ${attempts + 1})`);
          
          setTimeout(() => {
            if (!get().isConnected) {
              get().connect();
            }
          }, delay);
        };

        socket.onerror = (error) => {
          console.error('WebSocket error:', error);
          set({ isConnecting: false });
        };
      },

      disconnect: () => {
        const { socket } = get();
        if (socket) {
          socket.close();
          set({ 
            socket: null, 
            isConnected: false, 
            isConnecting: false,
            reconnectAttempts: 0  // Reset reconnect counter on manual disconnect
          });
        }
      },

      sendMessage: (message: any) => {
        const { socket, isConnected } = get();
        if (socket && isConnected) {
          socket.send(JSON.stringify(message));
        }
      },

      addMessage: (message: WebSocketMessage) => {
        set((state) => ({
          lastMessage: message,
          messageHistory: [...state.messageHistory.slice(-99), message], // Keep last 100 messages
        }));
      },

      clearHistory: () => {
        set({ messageHistory: [] });
      },

      addOrderEvent: (event: OrderEvent) => {
        set((state) => ({
          orderEvents: [...state.orderEvents.slice(-99), event], // Keep last 100 events
        }));
      },

      addPositionEvent: (event: PositionEvent) => {
        set((state) => ({
          positionEvents: [...state.positionEvents.slice(-99), event], // Keep last 100 events
        }));
      },

      clearEvents: () => {
        set({ orderEvents: [], positionEvents: [] });
      },
    }),
    {
      name: 'websocket-store',
    }
  )
);


