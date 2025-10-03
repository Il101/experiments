/**
 * Страница логов
 */

import React, { useState } from 'react';
import { Row, Col, Form, Badge } from 'react-bootstrap';
import { Card, Table } from '../components/ui';
import { useLogs } from '../hooks';

export const Logs: React.FC = () => {
  const [levelFilter, setLevelFilter] = useState<string>('');
  const [componentFilter, setComponentFilter] = useState<string>('');
  const [limit, setLimit] = useState<number>(100);

  const { data: logs, isLoading } = useLogs({
    level: levelFilter || undefined,
    component: componentFilter || undefined,
    limit,
  });

  const logColumns = [
    {
      key: 'timestamp',
      title: 'Timestamp',
      render: (value: string) => new Date(value).toLocaleString(),
    },
    {
      key: 'level',
      title: 'Level',
      render: (value: string) => (
        <Badge 
          bg={
            value === 'ERROR' ? 'danger' :
            value === 'WARNING' ? 'warning' :
            value === 'INFO' ? 'info' :
            'secondary'
          }
        >
          {value}
        </Badge>
      ),
    },
    {
      key: 'component',
      title: 'Component',
      render: (value: string) => (
        <Badge bg="outline-primary">{value}</Badge>
      ),
    },
    {
      key: 'message',
      title: 'Message',
    },
  ];

  const uniqueLevels = Array.from(new Set(logs?.map(log => log.level) || []));
  const uniqueComponents = Array.from(new Set(logs?.map(log => log.component) || []));

  return (
    <div className="page-content">
      <h1 className="h3 mb-4">System Logs</h1>
      
      <Row className="g-4">
        {/* Filters */}
        <Col lg={3}>
          <Card title="Filters" className="h-100">
            <div className="mb-3">
              <Form.Group>
                <Form.Label>Log Level</Form.Label>
                <Form.Select
                  value={levelFilter}
                  onChange={(e) => setLevelFilter(e.target.value)}
                >
                  <option value="">All Levels</option>
                  {uniqueLevels.map(level => (
                    <option key={level} value={level}>{level}</option>
                  ))}
                </Form.Select>
              </Form.Group>
            </div>

            <div className="mb-3">
              <Form.Group>
                <Form.Label>Component</Form.Label>
                <Form.Select
                  value={componentFilter}
                  onChange={(e) => setComponentFilter(e.target.value)}
                >
                  <option value="">All Components</option>
                  {uniqueComponents.map(component => (
                    <option key={component} value={component}>{component}</option>
                  ))}
                </Form.Select>
              </Form.Group>
            </div>

            <div className="mb-3">
              <Form.Group>
                <Form.Label>Limit</Form.Label>
                <Form.Control
                  type="number"
                  value={limit}
                  onChange={(e) => setLimit(Number(e.target.value))}
                  min={10}
                  max={1000}
                />
              </Form.Group>
            </div>

            <div className="d-grid">
              <button
                className="btn btn-outline-secondary"
                onClick={() => {
                  setLevelFilter('');
                  setComponentFilter('');
                  setLimit(100);
                }}
              >
                Clear Filters
              </button>
            </div>
          </Card>
        </Col>

        {/* Logs Table */}
        <Col lg={9}>
          <Card
            title="Logs"
            loading={isLoading}
            empty={!logs?.length}
            emptyMessage="No logs found"
          >
            <Table
              data={logs || []}
              columns={logColumns}
              loading={isLoading}
            />
          </Card>
        </Col>
      </Row>
    </div>
  );
};
