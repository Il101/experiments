/**
 * Smart Notifications Component
 * 
 * Умные уведомления о важных событиях в торговой системе
 */

import React, { useState, useEffect } from 'react';
import { Alert, Badge, Button, Card, ListGroup, Modal, Row, Col } from 'react-bootstrap';
import { useQuery } from '@tanstack/react-query';
import { monitoringApi } from '../../api/endpoints';

interface Notification {
  id: string;
  type: 'info' | 'success' | 'warning' | 'danger' | 'error';
  title: string;
  message: string;
  timestamp: number;
  category: 'state_change' | 'trade' | 'error' | 'performance' | 'system';
  priority: 'low' | 'medium' | 'high' | 'critical';
  acknowledged: boolean;
  metadata?: Record<string, any>;
}

interface SmartNotificationsProps {
  sessionId?: string;
  autoRefresh?: boolean;
  maxNotifications?: number;
  showAcknowledged?: boolean;
}

const NOTIFICATION_ICONS: Record<string, string> = {
  state_change: '🔄',
  trade: '💰',
  error: '❌',
  performance: '📊',
  system: '⚙️'
};

const PRIORITY_COLORS: Record<string, string> = {
  low: 'info',
  medium: 'warning',
  high: 'danger',
  critical: 'dark'
};

export const SmartNotifications: React.FC<SmartNotificationsProps> = ({
  sessionId,
  autoRefresh = true,
  maxNotifications = 50,
  showAcknowledged = false
}) => {
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [selectedNotification, setSelectedNotification] = useState<Notification | null>(null);
  const [showModal, setShowModal] = useState(false);

  // Query для получения состояния системы
  const { data: stateStatus } = useQuery({
    queryKey: ['state-machine', 'status', sessionId],
    queryFn: () => monitoringApi.getStateMachineStatus(sessionId),
    refetchInterval: autoRefresh ? 2000 : false,
    retry: 3,
    retryDelay: 1000
  });

  // Query для получения метрик
  const { data: metrics } = useQuery({
    queryKey: ['monitoring', 'metrics'],
    queryFn: monitoringApi.getRealTimeMetrics,
    refetchInterval: autoRefresh ? 3000 : false,
    retry: 3,
    retryDelay: 1000
  });

  // Генерация уведомлений на основе изменений состояния
  useEffect(() => {
    if (!stateStatus) return;

    const newNotification: Notification = {
      id: `state-${Date.now()}`,
      type: stateStatus.is_error ? 'danger' : 
            stateStatus.is_trading_active ? 'success' : 'info',
      title: `Состояние системы изменено`,
      message: `Система перешла в состояние: ${stateStatus.current_state.toUpperCase()}`,
      timestamp: Date.now(),
      category: 'state_change',
      priority: stateStatus.is_error ? 'critical' : 
                stateStatus.is_trading_active ? 'medium' : 'low',
      acknowledged: false,
      metadata: {
        current_state: stateStatus.current_state,
        previous_state: stateStatus.previous_state,
        is_trading_active: stateStatus.is_trading_active,
        is_error: stateStatus.is_error
      }
    };

    setNotifications(prev => {
      // Избегаем дублирования уведомлений о том же состоянии
      const lastNotification = prev[0];
      if (lastNotification && 
          lastNotification.category === 'state_change' &&
          lastNotification.metadata?.current_state === stateStatus.current_state) {
        return prev;
      }

      return [newNotification, ...prev].slice(0, maxNotifications);
    });
  }, [stateStatus?.current_state, stateStatus?.is_error, stateStatus?.is_trading_active]);

  // Генерация уведомлений о производительности
  useEffect(() => {
    if (!metrics) return;

    const criticalMemory = metrics.memory_usage > 90;
    const highCpu = metrics.cpu_usage > 95;
    const highLatency = metrics.latency_ms > 1000;

    if (criticalMemory || highCpu || highLatency) {
      const newNotification: Notification = {
        id: `perf-${Date.now()}`,
        type: 'warning',
        title: 'Предупреждение о производительности',
        message: `Высокая нагрузка: CPU ${metrics.cpu_usage.toFixed(1)}%, Memory ${metrics.memory_usage.toFixed(1)}%, Latency ${metrics.latency_ms.toFixed(0)}ms`,
        timestamp: Date.now(),
        category: 'performance',
        priority: criticalMemory || highCpu ? 'high' : 'medium',
        acknowledged: false,
        metadata: {
          cpu_usage: metrics.cpu_usage,
          memory_usage: metrics.memory_usage,
          latency_ms: metrics.latency_ms
        }
      };

      setNotifications(prev => {
        // Избегаем спама уведомлений о производительности
        const recentPerfNotification = prev.find(n => 
          n.category === 'performance' && 
          Date.now() - n.timestamp < 30000 // 30 секунд
        );
        
        if (recentPerfNotification) return prev;

        return [newNotification, ...prev].slice(0, maxNotifications);
      });
    }
  }, [metrics?.cpu_usage, metrics?.memory_usage, metrics?.latency_ms]);

  const acknowledgeNotification = (id: string) => {
    setNotifications(prev => 
      prev.map(n => n.id === id ? { ...n, acknowledged: true } : n)
    );
  };

  const acknowledgeAll = () => {
    setNotifications(prev => 
      prev.map(n => ({ ...n, acknowledged: true }))
    );
  };

  const clearAcknowledged = () => {
    setNotifications(prev => 
      prev.filter(n => !n.acknowledged)
    );
  };

  const formatTimestamp = (timestamp: number) => {
    const now = Date.now();
    const diff = now - timestamp;
    
    if (diff < 60000) return 'только что';
    if (diff < 3600000) return `${Math.floor(diff / 60000)} мин назад`;
    if (diff < 86400000) return `${Math.floor(diff / 3600000)} ч назад`;
    return new Date(timestamp).toLocaleDateString('ru-RU');
  };

  const filteredNotifications = notifications.filter(n => 
    showAcknowledged || !n.acknowledged
  );

  const unacknowledgedCount = notifications.filter(n => !n.acknowledged).length;
  const criticalCount = notifications.filter(n => 
    !n.acknowledged && n.priority === 'critical'
  ).length;

  return (
    <div>
      {/* Заголовок с кнопками управления */}
      <Card className="mb-3">
        <Card.Header>
          <div className="d-flex justify-content-between align-items-center">
            <h6 className="mb-0">
              🔔 Уведомления
              {unacknowledgedCount > 0 && (
                <Badge bg="danger" className="ms-2">
                  {unacknowledgedCount}
                </Badge>
              )}
              {criticalCount > 0 && (
                <Badge bg="dark" className="ms-1">
                  {criticalCount} критических
                </Badge>
              )}
            </h6>
            <div className="d-flex gap-2">
              <Button
                variant="outline-secondary"
                size="sm"
                onClick={acknowledgeAll}
                disabled={unacknowledgedCount === 0}
              >
                Отметить все
              </Button>
              <Button
                variant="outline-danger"
                size="sm"
                onClick={clearAcknowledged}
                disabled={notifications.length === unacknowledgedCount}
              >
                Очистить
              </Button>
            </div>
          </div>
        </Card.Header>
      </Card>

      {/* Список уведомлений */}
      {filteredNotifications.length === 0 ? (
        <Card>
          <Card.Body className="text-center text-muted">
            <div className="mb-2">🔕</div>
            <div>Нет новых уведомлений</div>
            <small>Важные события будут отображаться здесь</small>
          </Card.Body>
        </Card>
      ) : (
        <div className="list-group">
          {filteredNotifications.map((notification) => (
            <div
              key={notification.id}
              className={`list-group-item list-group-item-action ${
                notification.acknowledged ? 'opacity-50' : ''
              }`}
              onClick={() => {
                setSelectedNotification(notification);
                setShowModal(true);
              }}
              style={{ cursor: 'pointer' }}
            >
              <div className="d-flex justify-content-between align-items-start">
                <div className="flex-grow-1">
                  <div className="d-flex align-items-center mb-1">
                    <span className="me-2 fs-5">
                      {NOTIFICATION_ICONS[notification.category]}
                    </span>
                    <span className="fw-medium">{notification.title}</span>
                    <Badge 
                      bg={PRIORITY_COLORS[notification.priority]} 
                      className="ms-2"
                    >
                      {notification.priority}
                    </Badge>
                    {notification.acknowledged && (
                      <Badge bg="success" className="ms-1">
                        ✓
                      </Badge>
                    )}
                  </div>
                  <p className="mb-1 text-muted small">
                    {notification.message}
                  </p>
                  <small className="text-muted">
                    {formatTimestamp(notification.timestamp)}
                  </small>
                </div>
                {!notification.acknowledged && (
                  <Button
                    variant="outline-primary"
                    size="sm"
                    onClick={(e) => {
                      e.stopPropagation();
                      acknowledgeNotification(notification.id);
                    }}
                  >
                    ✓
                  </Button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Модальное окно с деталями уведомления */}
      <Modal show={showModal} onHide={() => setShowModal(false)} size="lg">
        <Modal.Header closeButton>
          <Modal.Title>
            {selectedNotification && (
              <>
                {NOTIFICATION_ICONS[selectedNotification.category]} 
                {selectedNotification.title}
              </>
            )}
          </Modal.Title>
        </Modal.Header>
        <Modal.Body>
          {selectedNotification && (
            <div>
              <p className="mb-3">{selectedNotification.message}</p>
              
              <Row>
                <Col md={6}>
                  <h6>Детали:</h6>
                  <ul className="list-unstyled">
                    <li><strong>Тип:</strong> {selectedNotification.type}</li>
                    <li><strong>Категория:</strong> {selectedNotification.category}</li>
                    <li><strong>Приоритет:</strong> {selectedNotification.priority}</li>
                    <li><strong>Время:</strong> {new Date(selectedNotification.timestamp).toLocaleString('ru-RU')}</li>
                  </ul>
                </Col>
                <Col md={6}>
                  {selectedNotification.metadata && Object.keys(selectedNotification.metadata).length > 0 && (
                    <>
                      <h6>Метаданные:</h6>
                      <pre className="bg-light p-2 rounded small">
                        {JSON.stringify(selectedNotification.metadata, null, 2)}
                      </pre>
                    </>
                  )}
                </Col>
              </Row>
            </div>
          )}
        </Modal.Body>
        <Modal.Footer>
          <Button
            variant="outline-secondary"
            onClick={() => setShowModal(false)}
          >
            Закрыть
          </Button>
          {selectedNotification && !selectedNotification.acknowledged && (
            <Button
              variant="primary"
              onClick={() => {
                acknowledgeNotification(selectedNotification.id);
                setShowModal(false);
              }}
            >
              Отметить как прочитанное
            </Button>
          )}
        </Modal.Footer>
      </Modal>
    </div>
  );
};

export default SmartNotifications;
