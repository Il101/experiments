/**
 * Компонент для отображения событий в реальном времени
 * Оптимизирован с React.memo для предотвращения unnecessary re-renders
 */

import React, { useMemo } from 'react';
import { useWebSocketStore } from '../store/useWebSocketStore';
import type { OrderEvent, PositionEvent } from '../types/api';
import { formatDistanceToNow } from 'date-fns';
import { ru } from 'date-fns/locale';

interface EventFeedProps {
  maxEvents?: number;
  showOrders?: boolean;
  showPositions?: boolean;
}

interface OrderEventItemProps {
  event: OrderEvent;
}

interface PositionEventItemProps {
  event: PositionEvent;
}

// Memoized sub-component for order events
const OrderEventItem = React.memo<OrderEventItemProps>(({ event }) => {
  const statusColors = {
    pending: 'text-yellow-600',
    open: 'text-blue-600',
    filled: 'text-green-600',
    cancelled: 'text-red-600',
    rejected: 'text-red-600'
  };

  return (
    <div className="flex items-center space-x-3 p-2 bg-gray-50 rounded">
      <div className="flex-shrink-0">
        <div className={`w-2 h-2 rounded-full ${statusColors[event.status] || 'bg-gray-400'}`} />
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center space-x-2">
          <span className="text-sm font-medium text-gray-900">
            {event.side.toUpperCase()} {event.qty} {event.symbol}
          </span>
          <span className={`text-xs px-2 py-1 rounded ${statusColors[event.status] || 'bg-gray-100'}`}>
            {event.status.toUpperCase()}
          </span>
        </div>
        <div className="text-xs text-gray-500">
          {event.price && `@ ${event.price}`}
          {event.fees && ` • Fee: ${event.fees.toFixed(4)}`}
          {event.reason && ` • ${event.reason}`}
        </div>
        <div className="text-xs text-gray-400">
          {formatDistanceToNow(new Date(event.createdAt), { addSuffix: true, locale: ru })}
        </div>
      </div>
    </div>
  );
});

OrderEventItem.displayName = 'OrderEventItem';

// Memoized sub-component for position events
const PositionEventItem = React.memo<PositionEventItemProps>(({ event }) => {
  const sideColors = {
    long: 'text-green-600',
    short: 'text-red-600'
  };

  const pnlColor = event.pnlR && event.pnlR > 0 ? 'text-green-600' : 'text-red-600';

  return (
    <div className="flex items-center space-x-3 p-2 bg-gray-50 rounded">
      <div className="flex-shrink-0">
        <div className={`w-2 h-2 rounded-full ${sideColors[event.side] || 'bg-gray-400'}`} />
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center space-x-2">
          <span className="text-sm font-medium text-gray-900">
            {event.side.toUpperCase()} {event.size} {event.symbol}
          </span>
          <span className="text-xs text-gray-500">
            @ {event.entry}
          </span>
          {event.pnlR && (
            <span className={`text-xs font-medium ${pnlColor}`}>
              {event.pnlR > 0 ? '+' : ''}{event.pnlR.toFixed(2)}R
            </span>
          )}
        </div>
        <div className="text-xs text-gray-500">
          SL: {event.sl} {event.tp && `• TP: ${event.tp}`}
          {event.reason && ` • ${event.reason}`}
        </div>
        <div className="text-xs text-gray-400">
          {formatDistanceToNow(new Date(event.openedAt), { addSuffix: true, locale: ru })}
        </div>
      </div>
    </div>
  );
});

PositionEventItem.displayName = 'PositionEventItem';

type EventWithMetadata = 
  | { kind: 'order'; event: OrderEvent; timestamp: number }
  | { kind: 'position'; event: PositionEvent; timestamp: number };

export const EventFeed: React.FC<EventFeedProps> = ({
  maxEvents = 50,
  showOrders = true,
  showPositions = true
}) => {
  const { orderEvents, positionEvents } = useWebSocketStore();

  // Memoize expensive event merging and sorting operation
  const allEvents = useMemo(() => {
    const events: EventWithMetadata[] = [];
    
    if (showOrders) {
      orderEvents.forEach(event => {
        events.push({
          kind: 'order',
          event,
          timestamp: new Date(event.createdAt).getTime()
        });
      });
    }
    
    if (showPositions) {
      positionEvents.forEach(event => {
        events.push({
          kind: 'position',
          event,
          timestamp: new Date(event.openedAt).getTime()
        });
      });
    }
    
    return events
      .sort((a, b) => b.timestamp - a.timestamp)
      .slice(0, maxEvents);
  }, [orderEvents, positionEvents, showOrders, showPositions, maxEvents]);

  if (allEvents.length === 0) {
    return (
      <div className="text-center py-8 text-gray-500">
        <div className="text-4xl mb-2">📊</div>
        <div>Нет событий для отображения</div>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      <div className="text-sm font-medium text-gray-700 mb-3">
        События в реальном времени ({allEvents.length})
      </div>
      <div className="space-y-1 max-h-96 overflow-y-auto">
        {allEvents.map((item, index) => (
          <div key={`${item.kind}-${item.event.id}-${index}`}>
            {item.kind === 'order' ? (
              <OrderEventItem event={item.event} />
            ) : (
              <PositionEventItem event={item.event} />
            )}
          </div>
        ))}
      </div>
    </div>
  );
};
