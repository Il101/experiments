/**
 * State Machine Visualizer Component
 * 
 * Визуализирует текущее состояние торгового движка и историю переходов
 */

import React, { useState, useEffect } from 'react';
import { Card, Badge, ProgressBar, Row, Col, Alert } from 'react-bootstrap';
import { useQuery } from '@tanstack/react-query';
import { monitoringApi } from '../../api/endpoints';

interface StateTransition {
  from_state: string;
  to_state: string;
  reason: string;
  timestamp: number;
  metadata?: Record<string, any>;
}

interface StateMachineStatus {
  current_state: string;
  previous_state?: string;
  is_terminal: boolean;
  is_error: boolean;
  is_trading_active: boolean;
  valid_next_states: string[];
  transition_count: number;
}

interface StateMachineVisualizerProps {
  sessionId?: string;
  autoRefresh?: boolean;
  showHistory?: boolean;
  compact?: boolean;
}

const STATE_COLORS: Record<string, string> = {
  idle: 'secondary',
  initializing: 'info',
  scanning: 'primary',
  level_building: 'warning',
  signal_wait: 'info',
  sizing: 'warning',
  execution: 'success',
  managing: 'success',
  paused: 'secondary',
  error: 'danger',
  emergency: 'danger',
  stopped: 'dark'
};

const STATE_ICONS: Record<string, string> = {
  idle: '⏸️',
  initializing: '🔧',
  scanning: '📊',
  level_building: '📏',
  signal_wait: '⏳',
  sizing: '📐',
  execution: '⚡',
  managing: '🎯',
  paused: '⏸️',
  error: '❌',
  emergency: '🚨',
  stopped: '⏹️'
};

const STATE_DESCRIPTIONS: Record<string, string> = {
  idle: 'Система в режиме ожидания',
  initializing: 'Инициализация компонентов',
  scanning: 'Сканирование рынков на предмет возможностей',
  level_building: 'Построение уровней поддержки/сопротивления',
  signal_wait: 'Ожидание торговых сигналов',
  sizing: 'Расчет размера позиций',
  execution: 'Исполнение торговых ордеров',
  managing: 'Управление открытыми позициями',
  paused: 'Система приостановлена',
  error: 'Обнаружена ошибка в работе',
  emergency: 'Критическая ситуация, требуется вмешательство',
  stopped: 'Система остановлена'
};

export const StateMachineVisualizer: React.FC<StateMachineVisualizerProps> = ({
  sessionId,
  autoRefresh = true,
  showHistory = true,
  compact = false
}) => {
  const [selectedTransition, setSelectedTransition] = useState<StateTransition | null>(null);

  // Query для получения статуса state machine
  const { data: stateStatus, isLoading: statusLoading, error: statusError } = useQuery({
    queryKey: ['state-machine', 'status', sessionId],
    queryFn: () => monitoringApi.getStateMachineStatus(sessionId),
    refetchInterval: autoRefresh ? 2000 : false,
    retry: 3,
    retryDelay: 1000
  });

  // Query для получения истории переходов
  const { data: transitions = [], isLoading: historyLoading } = useQuery({
    queryKey: ['state-machine', 'transitions', sessionId],
    queryFn: () => monitoringApi.getStateTransitions(sessionId, 20),
    enabled: showHistory,
    refetchInterval: autoRefresh ? 2000 : false,
    retry: 3,
    retryDelay: 1000
  });

  const getStateBadge = (state: string) => {
    const color = STATE_COLORS[state] || 'secondary';
    const icon = STATE_ICONS[state] || '❓';
    return (
      <Badge bg={color} className="fs-6 px-3 py-2">
        {icon} {state.toUpperCase()}
      </Badge>
    );
  };

  const formatTimestamp = (timestamp: number) => {
    return new Date(timestamp).toLocaleTimeString('ru-RU');
  };

  const getTransitionDirection = (from: string, to: string) => {
    if (from === to) return '🔄';
    if (['error', 'emergency'].includes(to)) return '❌';
    if (['execution', 'managing'].includes(to)) return '✅';
    if (['scanning', 'level_building', 'signal_wait'].includes(to)) return '🔄';
    return '➡️';
  };

  if (statusLoading) {
    return (
      <Card>
        <Card.Body className="text-center">
          <div className="spinner-border text-primary" role="status">
            <span className="visually-hidden">Загрузка...</span>
          </div>
          <p className="mt-2">Загрузка состояния системы...</p>
        </Card.Body>
      </Card>
    );
  }

  if (statusError) {
    return (
      <Alert variant="danger">
        <Alert.Heading>Ошибка загрузки состояния</Alert.Heading>
        <p>Не удалось получить информацию о состоянии системы.</p>
        <small>Попробуйте обновить страницу или проверить подключение к серверу.</small>
      </Alert>
    );
  }

  if (!stateStatus) {
    return (
      <Alert variant="warning">
        <Alert.Heading>Состояние недоступно</Alert.Heading>
        <p>Информация о состоянии системы временно недоступна.</p>
      </Alert>
    );
  }

  return (
    <div>
      {/* Текущее состояние */}
      <Card className="mb-3">
        <Card.Header>
          <h5 className="mb-0">
            {STATE_ICONS[stateStatus.current_state]} Текущее состояние системы
          </h5>
        </Card.Header>
        <Card.Body>
          <Row className="align-items-center">
            <Col md={compact ? 12 : 6}>
              <div className="d-flex align-items-center mb-2">
                <span className="me-3">Состояние:</span>
                {getStateBadge(stateStatus.current_state)}
              </div>
              
              {stateStatus.previous_state && (
                <div className="d-flex align-items-center mb-2">
                  <span className="me-3">Предыдущее:</span>
                  <Badge bg="outline-secondary" className="fs-6 px-2 py-1">
                    {STATE_ICONS[stateStatus.previous_state]} {stateStatus.previous_state.toUpperCase()}
                  </Badge>
                </div>
              )}

              <div className="text-muted small">
                {STATE_DESCRIPTIONS[stateStatus.current_state]}
              </div>
            </Col>

            {!compact && (
              <Col md={6}>
                <div className="row text-center">
                  <div className="col-4">
                    <div className="h6 mb-0">{stateStatus.transition_count}</div>
                    <small className="text-muted">Переходов</small>
                  </div>
                  <div className="col-4">
                    <div className="h6 mb-0">
                      {stateStatus.is_trading_active ? '✅' : '❌'}
                    </div>
                    <small className="text-muted">Торговля</small>
                  </div>
                  <div className="col-4">
                    <div className="h6 mb-0">
                      {stateStatus.is_error ? '❌' : '✅'}
                    </div>
                    <small className="text-muted">Статус</small>
                  </div>
                </div>
              </Col>
            )}
          </Row>

          {/* Возможные следующие состояния */}
          {stateStatus.valid_next_states.length > 0 && (
            <div className="mt-3">
              <small className="text-muted">Возможные переходы:</small>
              <div className="mt-1">
                {stateStatus.valid_next_states.map((state, index) => (
                  <Badge 
                    key={index} 
                    bg="outline-primary" 
                    className="me-1 mb-1"
                  >
                    {STATE_ICONS[state]} {state}
                  </Badge>
                ))}
              </div>
            </div>
          )}
        </Card.Body>
      </Card>

      {/* История переходов */}
      {showHistory && transitions.length > 0 && (
        <Card>
          <Card.Header>
            <h6 className="mb-0">История переходов состояний</h6>
          </Card.Header>
          <Card.Body className="p-0">
            <div className="list-group list-group-flush">
              {transitions.slice(0, compact ? 5 : 10).map((transition, index) => (
                <div
                  key={index}
                  className={`list-group-item list-group-item-action ${
                    selectedTransition === transition ? 'active' : ''
                  }`}
                  onClick={() => setSelectedTransition(
                    selectedTransition === transition ? null : transition
                  )}
                  style={{ cursor: 'pointer' }}
                >
                  <div className="d-flex justify-content-between align-items-center">
                    <div className="d-flex align-items-center">
                      <span className="me-2">
                        {getTransitionDirection(transition.from_state, transition.to_state)}
                      </span>
                      <Badge bg={STATE_COLORS[transition.from_state]} className="me-2">
                        {transition.from_state}
                      </Badge>
                      <span className="me-2">→</span>
                      <Badge bg={STATE_COLORS[transition.to_state]}>
                        {transition.to_state}
                      </Badge>
                    </div>
                    <small className="text-muted">
                      {formatTimestamp(transition.timestamp)}
                    </small>
                  </div>
                  
                  {selectedTransition === transition && (
                    <div className="mt-2 pt-2 border-top">
                      <div className="small">
                        <strong>Причина:</strong> {transition.reason}
                      </div>
                      {transition.metadata && Object.keys(transition.metadata).length > 0 && (
                        <div className="small mt-1">
                          <strong>Метаданные:</strong>
                          <pre className="mt-1 mb-0 small">
                            {JSON.stringify(transition.metadata, null, 2)}
                          </pre>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </Card.Body>
        </Card>
      )}

      {/* Пустое состояние для истории */}
      {showHistory && transitions.length === 0 && !historyLoading && (
        <Card>
          <Card.Body className="text-center text-muted">
            <div className="mb-2">📝</div>
            <div>История переходов пуста</div>
            <small>Переходы состояний будут отображаться здесь</small>
          </Card.Body>
        </Card>
      )}
    </div>
  );
};

export default StateMachineVisualizer;
