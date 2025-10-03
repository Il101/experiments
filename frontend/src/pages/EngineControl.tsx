/**
 * Страница управления движком
 */

import React, { useState, useEffect } from 'react';
import { Row, Col, Form, Alert } from 'react-bootstrap';
import { Card, Button, CommandButton, ToastNotifications } from '../components/ui';
import { StatusBadge } from '../components/ui/StatusBadge';
import { MetricCard, LatencyMetric, PnLMetric } from '../components/ui/MetricCard';
import { useEngineStatus, useEngineMetrics, useStartEngine, usePresets, useEngineCommands, useExecuteCommand, useToast } from '../hooks';
import { useAppStore } from '../store';
import { ENGINE_COMMANDS } from '../constants/engineCommands';

export const EngineControl: React.FC = () => {
  const { selectedPreset, setSelectedPreset } = useAppStore();
  const [tradingMode, setTradingMode] = useState<'paper' | 'live'>('paper');
  const { notifications, showSuccess, showError, removeToast } = useToast();
  
  const { data: engineStatus, isLoading: statusLoading } = useEngineStatus();
  const { data: engineMetrics, isLoading: metricsLoading } = useEngineMetrics();
  const { data: presets } = usePresets();
  const { data: availableCommands } = useEngineCommands();
  
  const startEngineMutation = useStartEngine();
  const executeCommandMutation = useExecuteCommand();

  const engineState = engineStatus?.state ? engineStatus.state.toLowerCase() : undefined;
  const remoteState = availableCommands?.currentState ? availableCommands.currentState.toLowerCase() : undefined;
  const effectiveState = remoteState ?? engineState;
  const isRunning = effectiveState ? !['idle', 'stopped'].includes(effectiveState) : false;
  const isLoading = startEngineMutation.isPending || executeCommandMutation.isPending;
  
  // Use commands from server or fallback to local logic
  const getAvailableCommands = () => {
    if (availableCommands?.commands) {
      return availableCommands.commands.map((cmd) => cmd.toLowerCase());
    }
    
    // Fallback to local logic
    const state = effectiveState;
    switch (state) {
      case 'idle':
        return ['start', 'reload'];
      case 'paused':
        return ['resume', 'stop', 'reload'];
      case 'error':
        return ['retry', 'stop', 'reload'];
      case 'scanning':
      case 'level_building':
      case 'signal_wait':
      case 'sizing':
      case 'execution':
      case 'managing':
        return ['stop', 'pause', 'time_stop', 'panic_exit', 'kill_switch'];
      case 'emergency':
        return ['stop'];
      default:
        return ['start', 'stop'];
    }
  };

  const commands = getAvailableCommands();

  // Helper functions for status display
  const getStatusColor = (state: string) => {
    const stateLower = state?.toLowerCase();
    switch (stateLower) {
      case 'idle':
        return 'secondary';
      case 'initializing':
        return 'info';
      case 'scanning':
      case 'level_building':
      case 'signal_wait':
      case 'sizing':
      case 'execution':
      case 'managing':
        return 'success';
      case 'paused':
        return 'warning';
      case 'error':
        return 'danger';
      case 'emergency':
        return 'danger';
      case 'stopped':
        return 'secondary';
      default:
        return 'secondary';
    }
  };

  const handleStart = () => {
    if (selectedPreset) {
      startEngineMutation.mutate({
        preset: selectedPreset,
        mode: tradingMode,
      });
    }
  };

  const handlePresetChange = (preset: string) => {
    setSelectedPreset(preset);
  };

  // Command handlers using the new API
  const handleCommand = (command: string) => {
    executeCommandMutation.mutate(command.toLowerCase());
  };

  // Show success notifications
  useEffect(() => {
    if (startEngineMutation.isSuccess) {
      showSuccess('Engine Started', `Engine started successfully with ${selectedPreset} preset in ${tradingMode} mode`);
    }
  }, [startEngineMutation.isSuccess, selectedPreset, tradingMode, showSuccess]);

  useEffect(() => {
    if (executeCommandMutation.isSuccess) {
      showSuccess('Command Executed', 'Command executed successfully');
    }
  }, [executeCommandMutation.isSuccess, showSuccess]);

  useEffect(() => {
    if (startEngineMutation.isError) {
      showError('Engine Start Failed', (startEngineMutation.error as any)?.detail || startEngineMutation.error?.message || 'Unknown error');
    }
  }, [startEngineMutation.isError, startEngineMutation.error, showError]);

  useEffect(() => {
    if (executeCommandMutation.isError) {
      showError('Command Failed', (executeCommandMutation.error as any)?.detail || executeCommandMutation.error?.message || 'Unknown error');
    }
  }, [executeCommandMutation.isError, executeCommandMutation.error, showError]);

  return (
    <div className="page-content">
      <ToastNotifications 
        notifications={notifications} 
        onClose={removeToast}
      />
      
      <h1 className="h3 mb-4">Engine Control</h1>
      
      <Row className="g-4">
        {/* Engine Controls */}
        <Col lg={6}>
          <Card title="Engine Controls" className="h-100">
            <div className="mb-4">
              <Form.Group className="mb-3">
                <Form.Label>Select Preset</Form.Label>
                <Form.Select
                  value={selectedPreset || ''}
                  onChange={(e) => handlePresetChange(e.target.value)}
                  disabled={isRunning || isLoading}
                >
                  <option value="">Choose a preset...</option>
                  {presets?.map((preset) => (
                    <option key={preset.name} value={preset.name}>
                      {preset.name} - {preset.description}
                    </option>
                  ))}
                </Form.Select>
              </Form.Group>

              <Form.Group className="mb-3">
                <Form.Label>Trading Mode</Form.Label>
                <Form.Select
                  value={tradingMode}
                  onChange={(e) => setTradingMode(e.target.value as 'paper' | 'live')}
                  disabled={isRunning || isLoading}
                >
                  <option value="paper">Paper Trading</option>
                  <option value="live">Live Trading</option>
                </Form.Select>
              </Form.Group>

              <div className="d-grid gap-2">
                {/* Primary Commands */}
                <div className="d-grid gap-2">
                  {commands.includes('start') && (
                    <Button
                      onClick={handleStart}
                      disabled={!selectedPreset || isLoading}
                      loading={isLoading}
                      loadingText="Starting Engine..."
                      variant="success"
                      size="lg"
                    >
                      🚀 Start Engine
                    </Button>
                  )}
                  
                  {commands.includes('stop') && (
                    <CommandButton
                      config={ENGINE_COMMANDS.stop}
                      onClick={handleCommand}
                      loading={isLoading}
                      size="lg"
                    />
                  )}
                </div>

                {/* Secondary Commands */}
                {(commands.includes('pause') || commands.includes('resume') || 
                  commands.includes('retry') || commands.includes('reload')) && (
                  <div className="mt-3">
                    <h6 className="text-muted mb-2">Control Commands</h6>
                    <div className="d-grid gap-2">
                      {commands.includes('pause') && (
                        <CommandButton
                          config={ENGINE_COMMANDS.pause}
                          onClick={handleCommand}
                          loading={isLoading}
                          size="sm"
                        />
                      )}
                      
                      {commands.includes('resume') && (
                        <CommandButton
                          config={ENGINE_COMMANDS.resume}
                          onClick={handleCommand}
                          loading={isLoading}
                          size="sm"
                        />
                      )}
                      
                      {commands.includes('retry') && (
                        <CommandButton
                          config={ENGINE_COMMANDS.retry}
                          onClick={handleCommand}
                          loading={isLoading}
                          size="sm"
                        />
                      )}
                      
                      {commands.includes('reload') && (
                        <CommandButton
                          config={ENGINE_COMMANDS.reload}
                          onClick={handleCommand}
                          loading={isLoading}
                          size="sm"
                        />
                      )}
                    </div>
                  </div>
                )}

                {/* Emergency Commands */}
                {(commands.includes('time_stop') || commands.includes('panic_exit') || 
                  commands.includes('kill_switch')) && (
                  <div className="mt-3">
                    <h6 className="text-danger mb-2">⚠️ Emergency Commands</h6>
                    <div className="d-grid gap-2">
                      {commands.includes('time_stop') && (
                        <CommandButton
                          config={ENGINE_COMMANDS.time_stop}
                          onClick={handleCommand}
                          loading={isLoading}
                          size="sm"
                        />
                      )}
                      
                      {commands.includes('panic_exit') && (
                        <CommandButton
                          config={ENGINE_COMMANDS.panic_exit}
                          onClick={handleCommand}
                          loading={isLoading}
                          size="sm"
                        />
                      )}
                      
                      {commands.includes('kill_switch') && (
                        <CommandButton
                          config={ENGINE_COMMANDS.kill_switch}
                          onClick={handleCommand}
                          loading={isLoading}
                          size="sm"
                        />
                      )}
                    </div>
                  </div>
                )}
              </div>
            </div>
          </Card>
        </Col>

        {/* Engine Status */}
        <Col lg={6}>
          <Card title="Engine Status" loading={statusLoading} className="h-100">
            {engineStatus && (
              <div>
                <div className="d-flex justify-content-between align-items-center mb-3">
                  <span className="fw-bold">Status:</span>
                  <StatusBadge 
                    status={engineStatus.state} 
                    variant={getStatusColor(engineStatus.state) as any}
                    size="lg"
                  />
                </div>
                
                {/* Available Commands Display */}
                <div className="mb-3">
                  <span className="fw-bold">Available Commands:</span>
                  <div className="mt-1">
                    {commands.map((cmd) => (
                      <span key={cmd} className="badge bg-light text-dark me-1 mb-1">
                        {cmd}
                      </span>
                    ))}
                  </div>
                </div>
                
                <div className="row g-3">
                  <div className="col-6">
                    <MetricCard
                      title="Slots"
                      value={engineStatus.slots}
                      icon="📊"
                      variant="primary"
                      size="sm"
                    />
                  </div>
                  <div className="col-6">
                    <MetricCard
                      title="Open Positions"
                      value={engineStatus.openPositions}
                      icon="📈"
                      variant="info"
                      size="sm"
                    />
                  </div>
                  <div className="col-6">
                    <LatencyMetric value={engineStatus.latencyMs} />
                  </div>
                  <div className="col-6">
                    <PnLMetric value={engineStatus.dailyR} />
                  </div>
                </div>

                {engineStatus.consecutiveLosses > 0 && (
                  <Alert variant="warning" className="mt-3">
                    <strong>Warning:</strong> {engineStatus.consecutiveLosses} consecutive losses
                  </Alert>
                )}
              </div>
            )}
          </Card>
        </Col>
      </Row>

      {/* Engine Metrics */}
      <Row className="mt-4">
        <Col>
          <Card title="Engine Metrics" loading={metricsLoading}>
            {engineMetrics && (
              <Row>
                <Col md={3}>
                  <div className="text-center p-3">
                    <div className="h5 mb-1">{Math.floor(engineMetrics.uptime / 3600)}h</div>
                    <div className="small text-muted">Uptime</div>
                  </div>
                </Col>
                <Col md={3}>
                  <div className="text-center p-3">
                    <div className="h5 mb-1">{engineMetrics.cycleCount}</div>
                    <div className="small text-muted">Cycles</div>
                  </div>
                </Col>
                <Col md={3}>
                  <div className="text-center p-3">
                    <div className="h5 mb-1">{engineMetrics.avgLatencyMs.toFixed(1)}ms</div>
                    <div className="small text-muted">Avg Latency</div>
                  </div>
                </Col>
                <Col md={3}>
                  <div className="text-center p-3">
                    <div className="h5 mb-1">{engineMetrics.totalSignals}</div>
                    <div className="small text-muted">Total Signals</div>
                  </div>
                </Col>
              </Row>
            )}
          </Card>
        </Col>
      </Row>
    </div>
  );
};
