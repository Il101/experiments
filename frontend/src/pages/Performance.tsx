/**
 * Страница производительности
 */

import React from 'react';
import { Row, Col } from 'react-bootstrap';
import { Card } from '../components/ui';
import { InfoIcon } from '../components/ui/Tooltip';
import { TOOLTIPS } from '../constants/tooltips';
import { useEquityHistory, usePerformanceMetrics, useRDistribution } from '../hooks';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, BarChart, Bar } from 'recharts';

export const Performance: React.FC = () => {
  const { data: equityData, isLoading: equityLoading } = useEquityHistory();
  const { data: performance, isLoading: performanceLoading } = usePerformanceMetrics();
  const { data: rDistribution, isLoading: rDistributionLoading } = useRDistribution();

  // Format equity data for chart
  const chartData = equityData?.map(point => ({
    time: new Date(point.timestamp).toLocaleTimeString(),
    value: point.value,
    cumulativeR: point.cumulativeR,
  })) || [];

  // Format R distribution data for chart
  const rDistributionData = rDistribution?.map(point => ({
    r: point.r,
    count: point.count,
  })) || [];

  return (
    <div className="page-content">
      <h1 className="h3 mb-4">Performance</h1>
      
      <Row className="g-4">
        {/* Performance Metrics */}
        <Col lg={6}>
          <Card title="Performance Metrics" loading={performanceLoading}>
            {performance && (
              <div className="row g-3">
                <div className="col-6">
                  <div className="text-center p-3 bg-light rounded">
                    <div className="h4 mb-1">{performance.totalTrades}</div>
                    <div className="small text-muted">Total Trades</div>
                  </div>
                </div>
                <div className="col-6">
                  <div className="text-center p-3 bg-light rounded">
                    <div className={`h4 mb-1 ${performance.winRate >= 50 ? 'text-success' : 'text-danger'}`}>
                      {performance.winRate.toFixed(1)}%
                    </div>
                    <div className="small text-muted">
                      Win Rate
                      <InfoIcon tooltip={TOOLTIPS.WIN_RATE} />
                    </div>
                  </div>
                </div>
                <div className="col-6">
                  <div className="text-center p-3 bg-light rounded">
                    <div className={`h4 mb-1 ${performance.avgR >= 0 ? 'text-success' : 'text-danger'}`}>
                      {performance.avgR.toFixed(2)}R
                    </div>
                    <div className="small text-muted">
                      Avg R
                      <InfoIcon tooltip={TOOLTIPS.AVG_R} />
                    </div>
                  </div>
                </div>
                <div className="col-6">
                  <div className="text-center p-3 bg-light rounded">
                    <div className="h4 mb-1">{performance.sharpeRatio.toFixed(2)}</div>
                    <div className="small text-muted">
                      Sharpe Ratio
                      <InfoIcon tooltip={TOOLTIPS.SHARPE_RATIO} />
                    </div>
                  </div>
                </div>
                <div className="col-6">
                  <div className="text-center p-3 bg-light rounded">
                    <div className="text-danger h4 mb-1">{performance.maxDrawdownR.toFixed(2)}R</div>
                    <div className="small text-muted">
                      Max Drawdown
                      <InfoIcon tooltip={TOOLTIPS.MAX_DRAWDOWN} />
                    </div>
                  </div>
                </div>
                <div className="col-6">
                  <div className="text-center p-3 bg-light rounded">
                    <div className={`h4 mb-1 ${performance.profitFactor >= 1 ? 'text-success' : 'text-danger'}`}>
                      {performance.profitFactor.toFixed(2)}
                    </div>
                    <div className="small text-muted">
                      Profit Factor
                      <InfoIcon tooltip={TOOLTIPS.PROFIT_FACTOR} />
                    </div>
                  </div>
                </div>
              </div>
            )}
          </Card>
        </Col>

        {/* Consecutive Stats */}
        <Col lg={6}>
          <Card title="Consecutive Stats" loading={performanceLoading}>
            {performance && (
              <div className="row g-3">
                <div className="col-6">
                  <div className="text-center p-3 bg-success bg-opacity-10 rounded">
                    <div className="h4 mb-1 text-success">{performance.consecutiveWins}</div>
                    <div className="small text-muted">
                      Consecutive Wins
                      <InfoIcon tooltip={TOOLTIPS.CONSECUTIVE_WINS} />
                    </div>
                  </div>
                </div>
                <div className="col-6">
                  <div className="text-center p-3 bg-danger bg-opacity-10 rounded">
                    <div className="h4 mb-1 text-danger">{performance.consecutiveLosses}</div>
                    <div className="small text-muted">
                      Consecutive Losses
                      <InfoIcon tooltip={TOOLTIPS.CONSECUTIVE_LOSSES} />
                    </div>
                  </div>
                </div>
              </div>
            )}
          </Card>
        </Col>
      </Row>

      {/* Equity Curve */}
      <Row className="mt-4">
        <Col>
          <Card title="Equity Curve" loading={equityLoading}>
            <div style={{ height: '400px' }}>
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis 
                    dataKey="time" 
                    tick={{ fontSize: 12 }}
                    interval="preserveStartEnd"
                  />
                  <YAxis 
                    tick={{ fontSize: 12 }}
                    tickFormatter={(value) => `$${value.toLocaleString()}`}
                  />
                  <Tooltip 
                    formatter={(value: any, name: string) => [
                      name === 'value' ? `$${value.toLocaleString()}` : `${value.toFixed(2)}R`,
                      name === 'value' ? 'Equity' : 'Cumulative R'
                    ]}
                    labelFormatter={(label) => `Time: ${label}`}
                  />
                  <Line 
                    type="monotone" 
                    dataKey="value" 
                    stroke="#0d6efd" 
                    strokeWidth={2}
                    dot={false}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </Card>
        </Col>
      </Row>

      {/* R Distribution */}
      <Row className="mt-4">
        <Col>
          <Card title="R-Multiple Distribution" loading={rDistributionLoading}>
            <div style={{ height: '300px' }}>
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={rDistributionData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis 
                    dataKey="r" 
                    tick={{ fontSize: 12 }}
                    tickFormatter={(value) => `${value}R`}
                  />
                  <YAxis 
                    tick={{ fontSize: 12 }}
                  />
                  <Tooltip 
                    formatter={(value: any) => [value, 'Count']}
                    labelFormatter={(label) => `R-Multiple: ${label}`}
                  />
                  <Bar 
                    dataKey="count" 
                    fill="#198754"
                    radius={[2, 2, 0, 0]}
                  />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </Card>
        </Col>
      </Row>
    </div>
  );
};


