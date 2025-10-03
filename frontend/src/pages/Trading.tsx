/**
 * Страница торговли
 * Оптимизирован с useMemo для предотвращения пересоздания columns и вычислений
 */

import React, { useMemo, useState } from 'react';
import { Row, Col, Badge, ButtonGroup, Button } from 'react-bootstrap';
import { Card, Table } from '../components/ui';
import { StatusBadge } from '../components/ui/StatusBadge';
import { EmptyPositions, EmptyOrders } from '../components/ui/EmptyState';
import { PositionCard } from '../components/positions';
import { usePositions, useOrders } from '../hooks';
import './Trading.css';

export const Trading: React.FC = () => {
  const { data: positions, isLoading: positionsLoading } = usePositions();
  const { data: orders, isLoading: ordersLoading } = useOrders();
  
  // View toggle: 'cards' or 'table'
  const [positionsView, setPositionsView] = useState<'cards' | 'table'>('cards');

  // Memoize column definitions to prevent recreation on each render
  const positionColumns = useMemo(() => [
    {
      key: 'symbol',
      title: 'Symbol',
    },
    {
      key: 'side',
      title: 'Side',
      render: (value: string) => (
        <StatusBadge 
          status={value.toUpperCase()} 
          variant={value === 'long' ? 'success' : 'danger'}
        />
      ),
    },
    {
      key: 'entry',
      title: 'Entry',
      render: (value: number) => `$${value.toFixed(2)}`,
    },
    {
      key: 'sl',
      title: 'Stop Loss',
      render: (value: number) => `$${value.toFixed(2)}`,
    },
    {
      key: 'size',
      title: 'Size',
      render: (value: number) => value.toFixed(4),
    },
    {
      key: 'pnlR',
      title: 'PnL (R)',
      render: (value: number) => (
        <span className={value >= 0 ? 'text-success' : 'text-danger'}>
          {value?.toFixed(2) || '0.00'}R
        </span>
      ),
    },
    {
      key: 'pnlUsd',
      title: 'PnL (USD)',
      render: (value: number) => (
        <span className={value >= 0 ? 'text-success' : 'text-danger'}>
          ${value?.toFixed(2) || '0.00'}
        </span>
      ),
    },
    {
      key: 'openedAt',
      title: 'Opened',
      render: (value: string) => new Date(value).toLocaleString(),
    },
  ], []);

  // Memoize order columns
  const orderColumns = useMemo(() => [
    {
      key: 'symbol',
      title: 'Symbol',
    },
    {
      key: 'side',
      title: 'Side',
      render: (value: string) => (
        <StatusBadge 
          status={value.toUpperCase()} 
          variant={value === 'buy' ? 'success' : 'danger'}
        />
      ),
    },
    {
      key: 'type',
      title: 'Type',
      render: (value: string) => (
        <Badge bg="secondary">{value.toUpperCase()}</Badge>
      ),
    },
    {
      key: 'qty',
      title: 'Quantity',
      render: (value: number) => value.toFixed(4),
    },
    {
      key: 'price',
      title: 'Price',
      render: (value: number) => value ? `$${value.toFixed(2)}` : 'Market',
    },
    {
      key: 'status',
      title: 'Status',
      render: (value: string) => {
        const variant = value === 'filled' ? 'success' : 
                       value === 'pending' || value === 'open' ? 'warning' :
                       value === 'cancelled' ? 'secondary' : 'danger';
        return (
          <StatusBadge 
            status={value.toUpperCase()} 
            variant={variant}
          />
        );
      },
    },
    {
      key: 'createdAt',
      title: 'Created',
      render: (value: string) => new Date(value).toLocaleString(),
    },
  ], []);

  // Memoize position statistics to avoid recalculation on each render
  const positionStats = useMemo(() => {
    if (!positions || positions.length === 0) {
      return {
        total: 0,
        long: 0,
        short: 0,
        totalPnlR: 0,
        totalPnlUsd: 0
      };
    }

    return {
      total: positions.length,
      long: positions.filter(p => p.side === 'long').length,
      short: positions.filter(p => p.side === 'short').length,
      totalPnlR: positions.reduce((sum, p) => sum + (p.pnlR || 0), 0),
      totalPnlUsd: positions.reduce((sum, p) => sum + (p.pnlUsd || 0), 0)
    };
  }, [positions]);

  return (
    <div className="page-content">
      <h1 className="h3 mb-4">Trading</h1>
      
      <Row className="g-4">
        {/* Positions */}
        <Col lg={8}>
          <Card
            title="Open Positions"
            loading={positionsLoading}
            empty={!positions?.length}
            emptyMessage="No open positions"
            headerActions={
              <ButtonGroup size="sm">
                <Button
                  variant={positionsView === 'cards' ? 'primary' : 'outline-primary'}
                  onClick={() => setPositionsView('cards')}
                >
                  📇 Cards
                </Button>
                <Button
                  variant={positionsView === 'table' ? 'primary' : 'outline-primary'}
                  onClick={() => setPositionsView('table')}
                >
                  📊 Table
                </Button>
              </ButtonGroup>
            }
          >
            {positions && positions.length > 0 ? (
              positionsView === 'cards' ? (
                <div className="positions-grid">
                  {positions.map((position) => (
                    <PositionCard
                      key={position.id}
                      position={position}
                      onClose={(id, percentage) => {
                        console.log(`Close position ${id} - ${percentage}%`);
                        // TODO: Implement close position API call
                      }}
                      onMoveSL={(id, toBreakeven) => {
                        console.log(`Move SL for ${id} to BE: ${toBreakeven}`);
                        // TODO: Implement move SL API call
                      }}
                    />
                  ))}
                </div>
              ) : (
                <Table
                  data={positions}
                  columns={positionColumns}
                  loading={positionsLoading}
                />
              )
            ) : (
              <EmptyPositions />
            )}
          </Card>
        </Col>

        {/* Quick Stats */}
        <Col lg={4}>
          <Card title="Position Summary" loading={positionsLoading}>
            {positions && (
              <div>
                <div className="d-flex justify-content-between align-items-center mb-3">
                  <span>Total Positions:</span>
                  <span className="badge bg-primary">{positionStats.total}</span>
                </div>
                
                <div className="d-flex justify-content-between align-items-center mb-3">
                  <span>Long Positions:</span>
                  <span className="badge bg-success">{positionStats.long}</span>
                </div>
                
                <div className="d-flex justify-content-between align-items-center mb-3">
                  <span>Short Positions:</span>
                  <span className="badge bg-danger">{positionStats.short}</span>
                </div>
                
                <div className="d-flex justify-content-between align-items-center mb-3">
                  <span>Total PnL (R):</span>
                  <span className={positionStats.totalPnlR >= 0 ? 'text-success' : 'text-danger'}>
                    {positionStats.totalPnlR.toFixed(2)}R
                  </span>
                </div>
                
                <div className="d-flex justify-content-between align-items-center">
                  <span>Total PnL (USD):</span>
                  <span className={positionStats.totalPnlUsd >= 0 ? 'text-success' : 'text-danger'}>
                    ${positionStats.totalPnlUsd.toFixed(2)}
                  </span>
                </div>
              </div>
            )}
          </Card>
        </Col>
      </Row>

      {/* Orders */}
      <Row className="mt-4">
        <Col>
          <Card
            title="Recent Orders"
            loading={ordersLoading}
            empty={!orders?.length}
            emptyMessage="No orders found"
          >
            {orders && orders.length > 0 ? (
              <Table
                data={orders}
                columns={orderColumns}
                loading={ordersLoading}
              />
            ) : (
              <EmptyOrders />
            )}
          </Card>
        </Col>
      </Row>
    </div>
  );
};


