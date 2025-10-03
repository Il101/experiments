/**
 * Страница мониторинга торгового процесса
 */

import React, { useState, useEffect } from 'react';
import { Row, Col, Card, ProgressBar, Badge, Table, Button, Alert, Tab, Tabs } from 'react-bootstrap';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { monitoringApi } from '../api/endpoints';
import { StateMachineVisualizer } from '../components/ui/StateMachineVisualizer';
import { ProcessProgress } from '../components/ui/ProcessProgress';
import { SmartNotifications } from '../components/ui/SmartNotifications';
import { EventFeed } from '../components/EventFeed';

interface Checkpoint {
  id: string;
  type: string;
  status: string;
  timestamp: string;
  duration_ms?: number;
  symbol?: string;
  message: string;
  metrics: Record<string, any>;
  data: Record<string, any>;
  error?: string;
}

interface Session {
  session_id: string;
  preset: string;
  start_time: string;
  end_time?: string;
  status: string;
  current_state: string;
  is_active: boolean;
  success_rate: number;
  total_duration_ms?: number;
  symbols_scanned: number;
  candidates_found: number;
  signals_generated: number;
  positions_opened: number;
  orders_executed: number;
}

interface ProcessStep {
  name: string;
  key: string;
  status: string;
}

interface Visualization {
  session_id: string;
  current_step: number;
  total_steps: number;
  steps: ProcessStep[];
  progress_percentage: number;
  estimated_completion?: string;
  current_activity: string;
  current_symbol?: string;
  avg_step_duration_ms: number;
  remaining_steps: number;
}

interface RealTimeMetrics {
  timestamp: string;
  engine_state: string;
  is_running: boolean;
  cpu_usage: number;
  memory_usage: number;
  latency_ms: number;
  active_sessions: number;
  positions_open: number;
  orders_pending: number;
  markets_scanned: number;
  candidates_found: number;
  signals_generated: number;
  daily_pnl: number;
  max_drawdown: number;
  risk_utilization: number;
}

export const Monitoring: React.FC = () => {
  const [selectedSessionId, setSelectedSessionId] = useState<string>('');
  const [autoRefresh, setAutoRefresh] = useState(true);
  const queryClient = useQueryClient();

  // Queries
  const { data: sessions = [] } = useQuery({
    queryKey: ['monitoring', 'sessions'],
    queryFn: monitoringApi.getActiveSessions,
    refetchInterval: autoRefresh ? 2000 : false,
  });

  const { data: currentSession } = useQuery({
    queryKey: ['monitoring', 'current-session'],
    queryFn: monitoringApi.getCurrentSession,
    refetchInterval: autoRefresh ? 1000 : false,
  });

  const { data: visualization } = useQuery({
    queryKey: ['monitoring', 'visualization', selectedSessionId],
    queryFn: () => monitoringApi.getSessionVisualization(selectedSessionId),
    enabled: !!selectedSessionId,
    refetchInterval: autoRefresh ? 1000 : false,
  });

  const { data: checkpoints = [] } = useQuery({
    queryKey: ['monitoring', 'checkpoints', selectedSessionId],
    queryFn: () => monitoringApi.getSessionCheckpoints(selectedSessionId, 50),
    enabled: !!selectedSessionId,
    refetchInterval: autoRefresh ? 1000 : false,
  });

  const { data: metrics } = useQuery({
    queryKey: ['monitoring', 'metrics'],
    queryFn: monitoringApi.getRealTimeMetrics,
    refetchInterval: autoRefresh ? 2000 : false,
  });

  // Auto-select current session
  useEffect(() => {
    if (currentSession?.session_id && !selectedSessionId) {
      setSelectedSessionId(currentSession.session_id);
    }
  }, [currentSession, selectedSessionId]);

  const getStatusBadge = (status: string) => {
    const variants: Record<string, string> = {
      completed: 'success',
      in_progress: 'warning',
      failed: 'danger',
      pending: 'secondary',
      error: 'danger',
    };
    return <Badge bg={variants[status] || 'secondary'}>{status}</Badge>;
  };

  const getStepStatusBadge = (status: string) => {
    const variants: Record<string, string> = {
      completed: 'success',
      in_progress: 'warning',
      pending: 'secondary',
    };
    return <Badge bg={variants[status] || 'secondary'}>{status}</Badge>;
  };

  const formatDuration = (ms?: number) => {
    if (!ms) return '-';
    if (ms < 1000) return `${ms}ms`;
    return `${(ms / 1000).toFixed(1)}s`;
  };

  const formatTimestamp = (timestamp: string) => {
    return new Date(timestamp).toLocaleString();
  };

  const checkpointColumns = [
    {
      key: 'timestamp',
      title: 'Time',
      render: (value: string) => formatTimestamp(value),
    },
    {
      key: 'type',
      title: 'Type',
      render: (value: string) => (
        <Badge bg="info" className="text-uppercase">
          {value.replace('_', ' ')}
        </Badge>
      ),
    },
    {
      key: 'status',
      title: 'Status',
      render: (value: string) => getStatusBadge(value),
    },
    {
      key: 'message',
      title: 'Message',
    },
    {
      key: 'symbol',
      title: 'Symbol',
      render: (value: string) => value || '-',
    },
    {
      key: 'duration_ms',
      title: 'Duration',
      render: (value: number) => formatDuration(value),
    },
  ];

  return (
    <div className="page-content">
      <div className="d-flex justify-content-between align-items-center mb-4">
        <h1 className="h3 mb-0">Trading Process Monitoring</h1>
        <div className="d-flex gap-2">
          <Button
            variant={autoRefresh ? 'success' : 'outline-secondary'}
            size="sm"
            onClick={() => setAutoRefresh(!autoRefresh)}
          >
            {autoRefresh ? 'Auto Refresh ON' : 'Auto Refresh OFF'}
          </Button>
        </div>
      </div>

      <Tabs defaultActiveKey="overview" className="mb-4">
        <Tab eventKey="overview" title="📊 Обзор">
          <div className="mt-3">
            <Row className="g-4">
        {/* Current Session Status */}
        <Col lg={12}>
          <Card>
            <Card.Header>
              <h5 className="mb-0">Current Session Status</h5>
            </Card.Header>
            <Card.Body>
              {currentSession ? (
                <div className="d-flex justify-content-between align-items-center">
                  <div>
                    <h6 className="mb-1">
                      Session: {currentSession.session_id?.slice(0, 8)}...
                    </h6>
                    <p className="mb-0 text-muted">
                      Preset: {currentSession.preset} | 
                      State: <Badge bg="primary">{currentSession.current_state}</Badge> | 
                      Started: {formatTimestamp(currentSession.start_time)}
                    </p>
                  </div>
                  <div className="text-end">
                    <Badge bg={currentSession.is_active ? 'success' : 'secondary'}>
                      {currentSession.is_active ? 'ACTIVE' : 'INACTIVE'}
                    </Badge>
                  </div>
                </div>
              ) : (
                <Alert variant="info">No active session</Alert>
              )}
            </Card.Body>
          </Card>
        </Col>

        {/* Process Visualization */}
        {visualization && (
          <Col lg={8}>
            <Card>
              <Card.Header>
                <h5 className="mb-0">Process Flow</h5>
              </Card.Header>
              <Card.Body>
                <div className="mb-3">
                  <div className="d-flex justify-content-between mb-2">
                    <span>Progress</span>
                    <span>{visualization.progress_percentage.toFixed(1)}%</span>
                  </div>
                  <ProgressBar 
                    now={visualization.progress_percentage} 
                    variant="success"
                    animated
                  />
                </div>

                <div className="mb-3">
                  <h6>Current Activity: {visualization.current_activity}</h6>
                  {visualization.current_symbol && (
                    <p className="text-muted mb-0">Symbol: {visualization.current_symbol}</p>
                  )}
                </div>

                <div className="row">
                  {visualization.steps.map((step, index) => (
                    <div key={step.key} className="col-md-2 mb-2">
                      <div className="text-center">
                        <div className="mb-1">
                          {getStepStatusBadge(step.status)}
                        </div>
                        <small className="text-muted">{step.name}</small>
                      </div>
                    </div>
                  ))}
                </div>

                <div className="mt-3 text-muted small">
                  <div className="row">
                    <div className="col-6">
                      Step {visualization.current_step} of {visualization.total_steps}
                    </div>
                    <div className="col-6 text-end">
                      Avg Duration: {formatDuration(visualization.avg_step_duration_ms)}
                    </div>
                  </div>
                </div>
              </Card.Body>
            </Card>
          </Col>
        )}

        {/* Real-time Metrics */}
        {metrics && (
          <Col lg={4}>
            <Card>
              <Card.Header>
                <h5 className="mb-0">Real-time Metrics</h5>
              </Card.Header>
              <Card.Body>
                <div className="mb-3">
                  <div className="d-flex justify-content-between">
                    <span>CPU Usage</span>
                    <span>{metrics.cpu_usage.toFixed(1)}%</span>
                  </div>
                  <ProgressBar now={metrics.cpu_usage} variant="info" />
                </div>

                <div className="mb-3">
                  <div className="d-flex justify-content-between">
                    <span>Memory Usage</span>
                    <span>{metrics.memory_usage.toFixed(1)}%</span>
                  </div>
                  <ProgressBar now={metrics.memory_usage} variant="warning" />
                </div>

                <div className="row text-center">
                  <div className="col-6 mb-2">
                    <div className="h5 mb-0">{metrics.latency_ms.toFixed(0)}ms</div>
                    <small className="text-muted">Latency</small>
                  </div>
                  <div className="col-6 mb-2">
                    <div className="h5 mb-0">{metrics.active_sessions}</div>
                    <small className="text-muted">Sessions</small>
                  </div>
                  <div className="col-6 mb-2">
                    <div className="h5 mb-0">{metrics.markets_scanned}</div>
                    <small className="text-muted">Markets</small>
                  </div>
                  <div className="col-6 mb-2">
                    <div className="h5 mb-0">{metrics.candidates_found}</div>
                    <small className="text-muted">Candidates</small>
                  </div>
                </div>
              </Card.Body>
            </Card>
          </Col>
        )}

        {/* Real-time Events */}
        <Col lg={12}>
          <Card>
            <Card.Header>
              <h5 className="mb-0">Real-time Events</h5>
            </Card.Header>
            <Card.Body>
              <EventFeed maxEvents={20} showOrders={true} showPositions={true} />
            </Card.Body>
          </Card>
        </Col>

        {/* Session Selection */}
        <Col lg={12}>
          <Card>
            <Card.Header>
              <h5 className="mb-0">Session Selection</h5>
            </Card.Header>
            <Card.Body>
              <div className="row">
                {sessions.map((session: Session) => (
                  <div key={session.session_id} className="col-md-4 mb-3">
                    <Card 
                      className={`h-100 ${selectedSessionId === session.session_id ? 'border-primary' : ''}`}
                      style={{ cursor: 'pointer' }}
                      onClick={() => setSelectedSessionId(session.session_id)}
                    >
                      <Card.Body>
                        <div className="d-flex justify-content-between align-items-start mb-2">
                        <h6 className="mb-0">
                          {session.session_id?.slice(0, 8)}...
                        </h6>
                          <Badge bg={session.is_active ? 'success' : 'secondary'}>
                            {session.is_active ? 'ACTIVE' : 'INACTIVE'}
                          </Badge>
                        </div>
                        <p className="text-muted small mb-2">
                          Preset: {session.preset}<br />
                          State: {session.current_state}
                        </p>
                        <div className="row text-center">
                          <div className="col-6">
                            <div className="h6 mb-0">{session.candidates_found}</div>
                            <small className="text-muted">Candidates</small>
                          </div>
                          <div className="col-6">
                            <div className="h6 mb-0">{(session.success_rate * 100).toFixed(0)}%</div>
                            <small className="text-muted">Success</small>
                          </div>
                        </div>
                      </Card.Body>
                    </Card>
                  </div>
                ))}
              </div>
            </Card.Body>
          </Card>
        </Col>

        {/* Checkpoints Table */}
        {selectedSessionId && (
          <Col lg={12}>
            <Card>
              <Card.Header>
                <h5 className="mb-0">Process Checkpoints</h5>
              </Card.Header>
              <Card.Body>
                <Table responsive striped hover>
                  <thead>
                    <tr>
                      {checkpointColumns.map((col) => (
                        <th key={col.key}>{col.title}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {checkpoints.map((checkpoint: Checkpoint) => (
                      <tr key={checkpoint.id}>
                        {checkpointColumns.map((col) => (
                          <td key={col.key}>
                            {col.render 
                              ? col.render(checkpoint[col.key as keyof Checkpoint] as any)
                              : checkpoint[col.key as keyof Checkpoint]
                            }
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </Table>
              </Card.Body>
            </Card>
          </Col>
        )}
            </Row>
          </div>
        </Tab>

        <Tab eventKey="state-machine" title="🔄 State Machine">
          <div className="mt-3">
            <StateMachineVisualizer 
              sessionId={selectedSessionId}
              autoRefresh={autoRefresh}
              showHistory={true}
              compact={false}
            />
          </div>
        </Tab>

        <Tab eventKey="progress" title="📈 Прогресс">
          <div className="mt-3">
            <ProcessProgress 
              sessionId={selectedSessionId}
              autoRefresh={autoRefresh}
              compact={false}
            />
          </div>
        </Tab>

        <Tab eventKey="notifications" title="🔔 Уведомления">
          <div className="mt-3">
            <SmartNotifications 
              sessionId={selectedSessionId}
              autoRefresh={autoRefresh}
              maxNotifications={100}
              showAcknowledged={false}
            />
          </div>
        </Tab>

        <Tab eventKey="events" title="📝 События">
          <div className="mt-3">
            <EventFeed sessionId={selectedSessionId} />
          </div>
        </Tab>
      </Tabs>
    </div>
  );
};
