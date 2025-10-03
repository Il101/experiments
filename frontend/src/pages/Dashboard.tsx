/**
 * Главная страница Dashboard
 * Оптимизирован с useMemo для предотвращения пересчётов
 */

import React, { useMemo, useEffect } from 'react';
import { Row, Col } from 'react-bootstrap';
import { Card } from '../components/ui';
import { StatusBadge } from '../components/ui/StatusBadge';
import { MetricCard, PnLMetric, LatencyMetric } from '../components/ui/MetricCard';
import { EmptyPositions } from '../components/ui/EmptyState';
import { InfoIcon } from '../components/ui/Tooltip';
import { LiveActivityFeed } from '../components/activity';
import { PositionCard } from '../components/positions';
import { TOOLTIPS } from '../constants/tooltips';
import { useEngineStatus, useEngineMetrics, usePositions, usePerformanceMetrics, useLogs } from '../hooks';
import { useActivityFeed, transformLogToActivity } from '../hooks/useActivityFeed';

export const Dashboard: React.FC = () => {
  const { data: engineStatus, isLoading: engineLoading } = useEngineStatus();
  const { data: engineMetrics, isLoading: metricsLoading } = useEngineMetrics();
  const { data: positions, isLoading: positionsLoading } = usePositions();
  const { data: performance, isLoading: performanceLoading } = usePerformanceMetrics();
  
  // Activity feed для отображения событий в реальном времени
  const { events, addEvent } = useActivityFeed({
    maxEvents: 20,
    autoConnect: false, // Пока без WebSocket, будем добавлять события вручную
  });

  // Получаем последние логи для преобразования в события
  const { data: logs } = useLogs({ limit: 50 });

  // Автоматически добавляем новые события из логов
  useEffect(() => {
    if (logs && logs.length > 0) {
      // Берём только последние 5 логов чтобы не спамить
      const recentLogs = logs.slice(0, 5);
      recentLogs.forEach((log) => {
        const activityEvent = transformLogToActivity(log);
        addEvent(activityEvent);
      });
    }
  }, [logs]); // Обновляем когда приходят новые логи

  // Memoize position calculations to avoid recalculation on each render
  const positionStats = useMemo(() => {
    const openPositions = positions || [];
    const totalPnL = openPositions.reduce((sum, p) => sum + (p.pnlUsd || 0), 0);
    const totalPnLR = openPositions.reduce((sum, p) => sum + (p.pnlR || 0), 0);
    const avgPnLR = openPositions.length > 0 ? totalPnLR / openPositions.length : 0;
    const recentPositions = openPositions.slice(0, 5);

    return {
      openPositions,
      totalPnL,
      avgPnLR,
      recentPositions
    };
  }, [positions]);

  return (
    <div className="page-content">
      <h1 className="h3 mb-4">Dashboard</h1>
      
      <Row className="g-4">
        {/* Live Activity Feed - самое главное! */}
        <Col xs={12}>
          <LiveActivityFeed 
            events={events}
            maxEvents={20}
            autoScroll={true}
            showTimestamp={true}
          />
        </Col>

        {/* Engine Status */}
        <Col md={6} lg={3}>
          <Card
            title="Engine Status"
            loading={engineLoading}
            className="h-100"
          >
            {engineStatus && (
              <div>
                <div className="d-flex justify-content-between align-items-center mb-2">
                  <span>State:</span>
                  <StatusBadge status={engineStatus.state} />
                </div>
                <div className="d-flex justify-content-between align-items-center mb-2">
                  <span>Mode:</span>
                  <StatusBadge status={engineStatus.mode} />
                </div>
                <div className="d-flex justify-content-between align-items-center mb-2">
                  <span>Preset:</span>
                  <span className="text-truncate" title={engineStatus.preset || 'None'}>
                    {engineStatus.preset || 'None'}
                  </span>
                </div>
                <div className="d-flex justify-content-between align-items-center">
                  <span>Latency:</span>
                  <LatencyMetric value={engineStatus.latencyMs} />
                </div>
              </div>
            )}
          </Card>
        </Col>

        {/* Performance Metrics */}
        <Col md={6} lg={3}>
          <Card
            title="Performance"
            loading={metricsLoading}
            className="h-100"
          >
            {engineMetrics && (
              <div>
                <div className="d-flex justify-content-between align-items-center mb-2">
                  <span>
                    Uptime:
                    <InfoIcon tooltip={TOOLTIPS.UPTIME} />
                  </span>
                  <MetricCard
                    title=""
                    value={`${Math.floor(engineMetrics.uptime / 3600)}h`}
                    icon="⏱️"
                    variant="info"
                    size="sm"
                    className="border-0 p-0"
                  />
                </div>
                <div className="d-flex justify-content-between align-items-center mb-2">
                  <span>Total Trades:</span>
                  <MetricCard
                    title=""
                    value={engineMetrics.totalTrades}
                    icon="📊"
                    variant="primary"
                    size="sm"
                    className="border-0 p-0"
                  />
                </div>
                <div className="d-flex justify-content-between align-items-center mb-2">
                  <span>
                    Daily PnL (R):
                    <InfoIcon tooltip={TOOLTIPS.PNL_R} />
                  </span>
                  <PnLMetric value={engineMetrics.dailyPnlR} />
                </div>
                <div className="d-flex justify-content-between align-items-center">
                  <span>
                    Max Drawdown:
                    <InfoIcon tooltip={TOOLTIPS.MAX_DRAWDOWN} />
                  </span>
                  <MetricCard
                    title=""
                    value={`${engineMetrics.maxDrawdownR.toFixed(2)}R`}
                    icon="📉"
                    variant="danger"
                    size="sm"
                    className="border-0 p-0"
                  />
                </div>
              </div>
            )}
          </Card>
        </Col>

        {/* Positions Summary */}
        <Col md={6} lg={3}>
          <Card
            title="Positions"
            loading={positionsLoading}
            className="h-100"
          >
            <div>
              <div className="d-flex justify-content-between align-items-center mb-2">
                <span>Open Positions:</span>
                <span className="badge bg-primary">{positionStats.openPositions.length}</span>
              </div>
              <div className="d-flex justify-content-between align-items-center mb-2">
                <span>
                  Total PnL:
                  <InfoIcon tooltip={TOOLTIPS.PNL_USD} />
                </span>
                <span className={positionStats.totalPnL >= 0 ? 'text-success' : 'text-danger'}>
                  ${positionStats.totalPnL.toFixed(2)}
                </span>
              </div>
              <div className="d-flex justify-content-between align-items-center">
                <span>
                  Avg PnL (R):
                  <InfoIcon tooltip={TOOLTIPS.AVG_R} />
                </span>
                <span>
                  {positionStats.avgPnLR.toFixed(2)}R
                </span>
              </div>
            </div>
          </Card>
        </Col>

        {/* Quick Stats */}
        <Col md={6} lg={3}>
          <Card
            title="Quick Stats"
            loading={performanceLoading}
            className="h-100"
          >
            {performance && (
              <div>
                <div className="d-flex justify-content-between align-items-center mb-2">
                  <span>
                    Win Rate:
                    <InfoIcon tooltip={TOOLTIPS.WIN_RATE} />
                  </span>
                  <span className="text-success">{performance.winRate.toFixed(1)}%</span>
                </div>
                <div className="d-flex justify-content-between align-items-center mb-2">
                  <span>Avg R:</span>
                  <span className={performance.avgR >= 0 ? 'text-success' : 'text-danger'}>
                    {performance.avgR.toFixed(2)}R
                  </span>
                </div>
                <div className="d-flex justify-content-between align-items-center mb-2">
                  <span>
                    Sharpe Ratio:
                    <InfoIcon tooltip={TOOLTIPS.SHARPE_RATIO} />
                  </span>
                  <span>{performance.sharpeRatio.toFixed(2)}</span>
                </div>
                <div className="d-flex justify-content-between align-items-center">
                  <span>
                    Profit Factor:
                    <InfoIcon tooltip={TOOLTIPS.PROFIT_FACTOR} />
                  </span>
                  <span className={performance.profitFactor >= 1 ? 'text-success' : 'text-danger'}>
                    {performance.profitFactor.toFixed(2)}
                  </span>
                </div>
              </div>
            )}
          </Card>
        </Col>
      </Row>

      {/* Recent Positions */}
      <Row className="mt-4">
        <Col>
          <Card
            title="Recent Positions"
            loading={positionsLoading}
            empty={positionStats.openPositions.length === 0}
            emptyMessage="No open positions"
          >
            {positionStats.openPositions.length > 0 ? (
              <div className="positions-compact-list">
                {positionStats.recentPositions.map((position) => (
                  <PositionCard
                    key={position.id}
                    position={position}
                    compact={true}
                  />
                ))}
              </div>
            ) : (
              <EmptyPositions />
            )}
          </Card>
        </Col>
      </Row>
    </div>
  );
};


