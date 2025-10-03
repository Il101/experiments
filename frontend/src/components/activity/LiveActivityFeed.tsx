/**
 * Live Activity Feed - отображает события в реальном времени
 * Показывает что бот делает прямо сейчас
 */

import React, { useMemo } from 'react';
import { Card } from '../ui';
import { Badge } from 'react-bootstrap';
import './LiveActivityFeed.css';

export interface ActivityEvent {
  id: string;
  timestamp: string;
  type: 'scan' | 'candidate' | 'signal' | 'entry' | 'exit' | 'reject' | 'error' | 'info' | 'level_building' | 'sizing';
  message: string;
  details?: Record<string, any>;
  severity: 'info' | 'success' | 'warning' | 'error';
  symbol?: string;
}

export interface LiveActivityFeedProps {
  events: ActivityEvent[];
  maxEvents?: number;
  autoScroll?: boolean;
  showTimestamp?: boolean;
  className?: string;
}

const EVENT_ICONS: Record<ActivityEvent['type'], string> = {
  scan: '🔍',
  candidate: '⭐',
  signal: '📊',
  entry: '📈',
  exit: '✅',
  reject: '❌',
  error: '🔴',
  info: 'ℹ️',
  level_building: '📏',
  sizing: '📐',
};

const EVENT_COLORS: Record<ActivityEvent['severity'], string> = {
  info: 'info',
  success: 'success',
  warning: 'warning',
  error: 'danger',
};

const EVENT_LABELS: Record<ActivityEvent['type'], string> = {
  scan: 'Сканирование',
  candidate: 'Кандидат найден',
  signal: 'Торговый сигнал',
  entry: 'Вход в позицию',
  exit: 'Выход из позиции',
  reject: 'Отклонено',
  error: 'Ошибка',
  info: 'Информация',
  level_building: 'Построение уровней',
  sizing: 'Расчёт размера',
};

export const LiveActivityFeed: React.FC<LiveActivityFeedProps> = ({
  events,
  maxEvents = 20,
  autoScroll = true,
  showTimestamp = true,
  className = '',
}) => {
  // Ограничиваем количество событий
  const displayEvents = useMemo(() => {
    return events.slice(0, maxEvents);
  }, [events, maxEvents]);

  const formatTime = (timestamp: string) => {
    const date = new Date(timestamp);
    return date.toLocaleTimeString('ru-RU', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });
  };

  const formatTimestamp = (timestamp: string) => {
    const date = new Date(timestamp);
    const now = new Date();
    const diff = Math.floor((now.getTime() - date.getTime()) / 1000);

    if (diff < 60) return `${diff}с назад`;
    if (diff < 3600) return `${Math.floor(diff / 60)}м назад`;
    if (diff < 86400) return `${Math.floor(diff / 3600)}ч назад`;
    return formatTime(timestamp);
  };

  const renderEventDetails = (event: ActivityEvent) => {
    if (!event.details || Object.keys(event.details).length === 0) {
      return null;
    }

    return (
      <div className="event-details">
        {Object.entries(event.details).map(([key, value]) => (
          <span key={key} className="detail-item">
            <strong>{key}:</strong> {String(value)}
          </span>
        ))}
      </div>
    );
  };

  if (displayEvents.length === 0) {
    return (
      <Card title="🔴 Сейчас происходит" className={className}>
        <div className="text-center text-muted py-4">
          <div className="mb-2" style={{ fontSize: '2rem' }}>⏸️</div>
          <p>Нет активности</p>
          <small>События появятся здесь, когда бот начнёт работу</small>
        </div>
      </Card>
    );
  }

  return (
    <Card 
      title="🔴 Сейчас происходит" 
      className={className}
      subtitle={`Последние ${displayEvents.length} событий`}
    >
      <div className={`activity-feed ${autoScroll ? 'auto-scroll' : ''}`}>
        {displayEvents.map((event) => (
          <div
            key={event.id}
            className={`activity-event activity-event-${event.severity}`}
          >
            {/* Header */}
            <div className="event-header">
              <div className="event-icon-type">
                <span className="event-icon">
                  {EVENT_ICONS[event.type]}
                </span>
                <Badge bg={EVENT_COLORS[event.severity]} className="event-badge">
                  {EVENT_LABELS[event.type]}
                </Badge>
                {event.symbol && (
                  <Badge bg="secondary" className="symbol-badge">
                    {event.symbol}
                  </Badge>
                )}
              </div>
              
              {showTimestamp && (
                <span className="event-time" title={formatTime(event.timestamp)}>
                  {formatTimestamp(event.timestamp)}
                </span>
              )}
            </div>

            {/* Message */}
            <div className="event-message">
              {event.message}
            </div>

            {/* Details */}
            {renderEventDetails(event)}
          </div>
        ))}
      </div>
    </Card>
  );
};

/**
 * Компактная версия для Dashboard
 */
export const CompactActivityFeed: React.FC<LiveActivityFeedProps> = ({
  events,
  maxEvents = 5,
  className = '',
}) => {
  const recentEvents = useMemo(() => {
    return events.slice(0, maxEvents);
  }, [events, maxEvents]);

  const formatTime = (timestamp: string) => {
    const date = new Date(timestamp);
    return date.toLocaleTimeString('ru-RU', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });
  };

  if (recentEvents.length === 0) {
    return null;
  }

  return (
    <div className={`compact-activity-feed ${className}`}>
      {recentEvents.map((event) => (
        <div key={event.id} className="compact-event">
          <span className="compact-icon">{EVENT_ICONS[event.type]}</span>
          <span className="compact-time">{formatTime(event.timestamp)}</span>
          <span className="compact-message">{event.message}</span>
        </div>
      ))}
    </div>
  );
};

export default LiveActivityFeed;
