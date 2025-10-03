/**
 * Hook for managing activity feed events
 * Handles event storage, updates, and real-time subscriptions
 */

import { useState, useCallback, useRef, useEffect } from 'react';
import type { ActivityEvent } from '../components/activity/LiveActivityFeed';

interface UseActivityFeedOptions {
  maxEvents?: number;
  autoConnect?: boolean;
  wsUrl?: string;
}

interface UseActivityFeedReturn {
  events: ActivityEvent[];
  addEvent: (event: Omit<ActivityEvent, 'id' | 'timestamp'>) => void;
  clearEvents: () => void;
  isConnected: boolean;
  error: Error | null;
}

const generateEventId = (): string => {
  return `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
};

export const useActivityFeed = (
  options: UseActivityFeedOptions = {}
): UseActivityFeedReturn => {
  const {
    maxEvents = 100,
    autoConnect = false,
    wsUrl = undefined,
  } = options;

  const [events, setEvents] = useState<ActivityEvent[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const reconnectAttemptsRef = useRef(0);

  // Add new event
  const addEvent = useCallback((
    event: Omit<ActivityEvent, 'id' | 'timestamp'>
  ) => {
    const newEvent: ActivityEvent = {
      ...event,
      id: generateEventId(),
      timestamp: new Date().toISOString(),
    };

    setEvents((prev) => {
      const updated = [newEvent, ...prev];
      // Keep only maxEvents
      return updated.slice(0, maxEvents);
    });
  }, [maxEvents]);

  // Clear all events
  const clearEvents = useCallback(() => {
    setEvents([]);
  }, []);

  // WebSocket connection
  const connect = useCallback(() => {
    if (!wsUrl || wsRef.current?.readyState === WebSocket.OPEN) {
      return;
    }

    try {
      const ws = new WebSocket(wsUrl);

      ws.onopen = () => {
        console.log('[ActivityFeed] WebSocket connected');
        setIsConnected(true);
        setError(null);
        reconnectAttemptsRef.current = 0;
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          
          // Handle different message types
          if (data.type === 'activity_event') {
            addEvent(data.payload);
          } else if (data.type === 'batch_events') {
            // Handle batch updates
            data.payload.forEach((evt: Omit<ActivityEvent, 'id' | 'timestamp'>) => {
              addEvent(evt);
            });
          }
        } catch (err) {
          console.error('[ActivityFeed] Error parsing message:', err);
        }
      };

      ws.onerror = (event) => {
        console.error('[ActivityFeed] WebSocket error:', event);
        setError(new Error('WebSocket connection error'));
      };

      ws.onclose = () => {
        console.log('[ActivityFeed] WebSocket disconnected');
        setIsConnected(false);
        wsRef.current = null;

        // Auto-reconnect with exponential backoff
        if (autoConnect && reconnectAttemptsRef.current < 5) {
          const delay = Math.min(1000 * Math.pow(2, reconnectAttemptsRef.current), 30000);
          console.log(`[ActivityFeed] Reconnecting in ${delay}ms...`);
          
          reconnectTimeoutRef.current = setTimeout(() => {
            reconnectAttemptsRef.current += 1;
            connect();
          }, delay);
        }
      };

      wsRef.current = ws;
    } catch (err) {
      console.error('[ActivityFeed] Error creating WebSocket:', err);
      setError(err instanceof Error ? err : new Error('Unknown error'));
    }
  }, [wsUrl, autoConnect, addEvent]);

  // Disconnect WebSocket
  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }

    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }

    setIsConnected(false);
  }, []);

  // Auto-connect on mount
  useEffect(() => {
    if (autoConnect && wsUrl) {
      connect();
    }

    return () => {
      disconnect();
    };
  }, [autoConnect, wsUrl, connect, disconnect]);

  return {
    events,
    addEvent,
    clearEvents,
    isConnected,
    error,
  };
};

/**
 * Transform backend log entries to activity events
 */
export const transformLogToActivity = (log: any): Omit<ActivityEvent, 'id' | 'timestamp'> => {
  const message = log.message || log.msg || '';
  
  // Determine event type from message
  let type: ActivityEvent['type'] = 'info';
  let severity: ActivityEvent['severity'] = 'info';
  
  if (message.includes('Scanning') || message.includes('сканирование')) {
    type = 'scan';
  } else if (message.includes('Candidate found') || message.includes('кандидат найден')) {
    type = 'candidate';
    severity = 'success';
  } else if (message.includes('Signal generated') || message.includes('сигнал')) {
    type = 'signal';
    severity = 'warning';
  } else if (message.includes('Entry') || message.includes('вход')) {
    type = 'entry';
    severity = 'success';
  } else if (message.includes('Exit') || message.includes('выход')) {
    type = 'exit';
    severity = 'success';
  } else if (message.includes('Rejected') || message.includes('отклонено')) {
    type = 'reject';
    severity = 'warning';
  } else if (message.includes('Error') || message.includes('ошибка')) {
    type = 'error';
    severity = 'error';
  } else if (message.includes('Level building') || message.includes('уровни')) {
    type = 'level_building';
  } else if (message.includes('Sizing') || message.includes('размер')) {
    type = 'sizing';
  }

  return {
    type,
    severity,
    message,
    symbol: log.symbol || undefined,
    details: log.details || undefined,
  };
};

export default useActivityFeed;
