/**
 * Process Progress Component
 * 
 * Отображает прогресс выполнения торговых процессов в реальном времени
 */

import React, { useState, useEffect } from 'react';
import { Card, ProgressBar, Badge, Row, Col, Alert, Spinner } from 'react-bootstrap';
import { useQuery } from '@tanstack/react-query';
import { monitoringApi } from '../../api/endpoints';

interface ProcessStep {
  name: string;
  status: 'pending' | 'in_progress' | 'completed' | 'failed' | 'skipped';
  progress: number; // 0-100
  startTime?: number;
  endTime?: number;
  duration?: number;
  details?: string;
  metadata?: Record<string, any>;
}

interface ProcessProgressProps {
  sessionId?: string;
  autoRefresh?: boolean;
  compact?: boolean;
}

const STEP_ICONS: Record<string, string> = {
  scanning: '📊',
  level_building: '📏',
  signal_wait: '⏳',
  sizing: '📐',
  execution: '⚡',
  managing: '🎯',
  error: '❌',
  completed: '✅'
};

const STEP_COLORS: Record<string, string> = {
  pending: 'secondary',
  in_progress: 'primary',
  completed: 'success',
  failed: 'danger',
  skipped: 'warning'
};

export const ProcessProgress: React.FC<ProcessProgressProps> = ({
  sessionId,
  autoRefresh = true,
  compact = false
}) => {
  const [currentStep, setCurrentStep] = useState<string>('idle');
  const [stepProgress, setStepProgress] = useState<number>(0);

  // Query для получения текущего состояния
  const { data: stateStatus, isLoading: stateLoading } = useQuery({
    queryKey: ['state-machine', 'status', sessionId],
    queryFn: () => monitoringApi.getStateMachineStatus(sessionId),
    refetchInterval: autoRefresh ? 1000 : false,
    retry: 3,
    retryDelay: 1000
  });

  // Query для получения метрик производительности
  const { data: performance, isLoading: perfLoading } = useQuery({
    queryKey: ['state-machine', 'performance', sessionId],
    queryFn: () => monitoringApi.getStateMachinePerformance(sessionId),
    refetchInterval: autoRefresh ? 2000 : false,
    retry: 3,
    retryDelay: 1000
  });

  // Симуляция прогресса для текущего шага
  useEffect(() => {
    if (!stateStatus?.current_state) return;

    const state = stateStatus.current_state;
    setCurrentStep(state);

    // Симуляция прогресса в зависимости от состояния
    const progressMap: Record<string, number> = {
      idle: 0,
      initializing: 25,
      scanning: 50,
      level_building: 70,
      signal_wait: 85,
      sizing: 90,
      execution: 95,
      managing: 100,
      error: 0,
      emergency: 0,
      stopped: 100
    };

    setStepProgress(progressMap[state] || 0);
  }, [stateStatus?.current_state]);

  const getStepStatus = (stepName: string): ProcessStep['status'] => {
    if (!stateStatus) return 'pending';
    
    const currentState = stateStatus.current_state;
    
    if (stepName === currentState) {
      return stateStatus.is_error ? 'failed' : 'in_progress';
    }
    
    // Определить статус на основе текущего состояния
    const stepOrder = ['idle', 'initializing', 'scanning', 'level_building', 'signal_wait', 'sizing', 'execution', 'managing'];
    const currentIndex = stepOrder.indexOf(currentState);
    const stepIndex = stepOrder.indexOf(stepName);
    
    if (stepIndex < currentIndex) return 'completed';
    if (stepIndex > currentIndex) return 'pending';
    
    return 'pending';
  };

  const getStepDuration = (stepName: string): number | undefined => {
    if (!performance?.metrics?.state_durations_ms) return undefined;
    return performance.metrics.state_durations_ms[stepName] || 0;
  };

  const formatDuration = (ms: number): string => {
    if (ms < 1000) return `${ms}ms`;
    if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
    return `${(ms / 60000).toFixed(1)}m`;
  };

  const processSteps: ProcessStep[] = [
    {
      name: 'scanning',
      status: getStepStatus('scanning'),
      progress: currentStep === 'scanning' ? stepProgress : (getStepStatus('scanning') === 'completed' ? 100 : 0),
      details: 'Сканирование рынков на предмет торговых возможностей',
      duration: getStepDuration('scanning')
    },
    {
      name: 'level_building',
      status: getStepStatus('level_building'),
      progress: currentStep === 'level_building' ? stepProgress : (getStepStatus('level_building') === 'completed' ? 100 : 0),
      details: 'Построение уровней поддержки и сопротивления',
      duration: getStepDuration('level_building')
    },
    {
      name: 'signal_wait',
      status: getStepStatus('signal_wait'),
      progress: currentStep === 'signal_wait' ? stepProgress : (getStepStatus('signal_wait') === 'completed' ? 100 : 0),
      details: 'Ожидание торговых сигналов (breakout + volume + L2)',
      duration: getStepDuration('signal_wait')
    },
    {
      name: 'sizing',
      status: getStepStatus('sizing'),
      progress: currentStep === 'sizing' ? stepProgress : (getStepStatus('sizing') === 'completed' ? 100 : 0),
      details: 'Расчет размера позиций (R-based сайзинг)',
      duration: getStepDuration('sizing')
    },
    {
      name: 'execution',
      status: getStepStatus('execution'),
      progress: currentStep === 'execution' ? stepProgress : (getStepStatus('execution') === 'completed' ? 100 : 0),
      details: 'Исполнение торговых ордеров (TWAP slicing)',
      duration: getStepDuration('execution')
    },
    {
      name: 'managing',
      status: getStepStatus('managing'),
      progress: currentStep === 'managing' ? stepProgress : (getStepStatus('managing') === 'completed' ? 100 : 0),
      details: 'Управление открытыми позициями',
      duration: getStepDuration('managing')
    }
  ];

  if (stateLoading) {
    return (
      <Card>
        <Card.Body className="text-center">
          <Spinner animation="border" variant="primary" />
          <p className="mt-2">Загрузка прогресса процессов...</p>
        </Card.Body>
      </Card>
    );
  }

  if (!stateStatus) {
    return (
      <Alert variant="warning">
        <Alert.Heading>Прогресс недоступен</Alert.Heading>
        <p>Информация о прогрессе процессов временно недоступна.</p>
      </Alert>
    );
  }

  return (
    <div>
      {/* Общий прогресс */}
      <Card className="mb-3">
        <Card.Header>
          <h6 className="mb-0">
            {STEP_ICONS[currentStep]} Текущий процесс: {currentStep.toUpperCase()}
          </h6>
        </Card.Header>
        <Card.Body>
          <div className="mb-2">
            <div className="d-flex justify-content-between mb-1">
              <span>Общий прогресс</span>
              <span>{stepProgress}%</span>
            </div>
            <ProgressBar 
              now={stepProgress} 
              variant={stateStatus.is_error ? 'danger' : 'primary'}
              animated={currentStep !== 'idle' && currentStep !== 'stopped'}
            />
          </div>
          
          {stateStatus.is_error && (
            <Alert variant="danger" className="mb-0">
              <small>⚠️ Обнаружена ошибка в процессе</small>
            </Alert>
          )}
        </Card.Body>
      </Card>

      {/* Детальный прогресс по шагам */}
      <Card>
        <Card.Header>
          <h6 className="mb-0">Детальный прогресс по шагам</h6>
        </Card.Header>
        <Card.Body className="p-0">
          <div className="list-group list-group-flush">
            {processSteps.map((step, index) => (
              <div key={step.name} className="list-group-item">
                <Row className="align-items-center">
                  <Col xs={compact ? 12 : 8}>
                    <div className="d-flex align-items-center mb-2">
                      <span className="me-2 fs-5">
                        {STEP_ICONS[step.name] || '📋'}
                      </span>
                      <div className="flex-grow-1">
                        <div className="d-flex justify-content-between align-items-center">
                          <span className="fw-medium text-capitalize">
                            {step.name.replace('_', ' ')}
                          </span>
                          <Badge bg={STEP_COLORS[step.status]} className="ms-2">
                            {step.status === 'in_progress' ? 'В процессе' :
                             step.status === 'completed' ? 'Завершено' :
                             step.status === 'failed' ? 'Ошибка' :
                             step.status === 'skipped' ? 'Пропущено' : 'Ожидание'}
                          </Badge>
                        </div>
                        
                        {!compact && (
                          <small className="text-muted d-block mt-1">
                            {step.details}
                          </small>
                        )}
                      </div>
                    </div>
                    
                    {step.status === 'in_progress' && (
                      <ProgressBar 
                        now={step.progress} 
                        variant="primary"
                        animated
                        className="mb-1"
                      />
                    )}
                    
                    {step.duration !== undefined && (
                      <small className="text-muted">
                        Время выполнения: {formatDuration(step.duration)}
                      </small>
                    )}
                  </Col>
                  
                  {!compact && (
                    <Col xs={4} className="text-end">
                      <div className="text-muted small">
                        {step.progress}%
                      </div>
                    </Col>
                  )}
                </Row>
              </div>
            ))}
          </div>
        </Card.Body>
      </Card>

      {/* Статистика производительности */}
      {performance?.metrics && (
        <Card className="mt-3">
          <Card.Header>
            <h6 className="mb-0">📊 Статистика производительности</h6>
          </Card.Header>
          <Card.Body>
            <Row>
              <Col md={4}>
                <div className="text-center">
                  <div className="h5 mb-0">{performance.metrics.total_transitions}</div>
                  <small className="text-muted">Всего переходов</small>
                </div>
              </Col>
              <Col md={4}>
                <div className="text-center">
                  <div className="h5 mb-0">
                    {stateStatus.is_trading_active ? '✅' : '❌'}
                  </div>
                  <small className="text-muted">Торговля активна</small>
                </div>
              </Col>
              <Col md={4}>
                <div className="text-center">
                  <div className="h5 mb-0">
                    {stateStatus.is_error ? '❌' : '✅'}
                  </div>
                  <small className="text-muted">Статус системы</small>
                </div>
              </Col>
            </Row>
          </Card.Body>
        </Card>
      )}
    </div>
  );
};

export default ProcessProgress;
