/**
 * Страница сканера рынка
 * Оптимизирован с useCallback и useMemo для предотвращения пересозданий
 */

import React, { useState, useMemo, useCallback } from 'react';
import { Row, Col, Badge, Form } from 'react-bootstrap';
import { Card, Table, Button } from '../components/ui';
import { StatusBadge } from '../components/ui/StatusBadge';
import { EmptyScanResults } from '../components/ui/EmptyState';
import { TOOLTIPS } from '../constants/tooltips';
import { useLastScan, useScanMarket, usePresets } from '../hooks';

export const Scanner: React.FC = () => {
  const [selectedPreset, setSelectedPreset] = useState<string>('');
  const [scanLimit, setScanLimit] = useState<number>(10);
  
  const { data: lastScan, isLoading: scanLoading } = useLastScan();
  const { data: presets } = usePresets();
  const scanMarketMutation = useScanMarket();

  // Memoize column definitions to prevent recreation on each render
  const candidateColumns = useMemo(() => [
    {
      key: 'symbol',
      title: 'Symbol',
    },
    {
      key: 'score',
      title: 'Score',
      render: (value: number) => {
        const variant = value >= 0.8 ? 'success' : value >= 0.6 ? 'warning' : 'secondary';
        return (
          <span title={TOOLTIPS.SCAN_SCORE}>
            <StatusBadge 
              status={value.toFixed(1)} 
              variant={variant}
              showIcon={false}
            />
          </span>
        );
      },
    },
    {
      key: 'metrics.vol_surge',
      title: 'Vol Surge',
      render: (value: number) => (
        <span title={TOOLTIPS.VOLUME_SURGE}>
          {`${(value || 0).toFixed(1)}x`}
        </span>
      ),
    },
    {
      key: 'metrics.atr_quality',
      title: 'ATR Quality',
      render: (value: number) => (
        <span title={TOOLTIPS.ATR_QUALITY}>
          {`${(value || 0).toFixed(2)}`}
        </span>
      ),
    },
    {
      key: 'metrics.correlation',
      title: 'Correlation',
      render: (value: number) => (
        <span title={TOOLTIPS.CORRELATION}>
          {`${(value || 0).toFixed(2)}`}
        </span>
      ),
    },
    {
      key: 'metrics.trades_per_minute',
      title: 'Trades/min',
      render: (value: number) => (
        <span title={TOOLTIPS.TRADES_PER_MINUTE}>
          {`${(value || 0).toFixed(1)}`}
        </span>
      ),
    },
    {
      key: 'filters',
      title: 'Filters',
      render: (filters: any) => (
        <div className="d-flex gap-1">
          {Object.entries(filters).map(([key, value]) => (
            <Badge 
              key={key} 
              bg={value ? 'success' : 'danger'}
              className="small"
            >
              {key}
            </Badge>
          ))}
        </div>
      ),
    },
  ], []);

  // Memoize handleScan callback to prevent recreation
  const handleScan = useCallback(() => {
    if (selectedPreset) {
      scanMarketMutation.mutate({
        preset: selectedPreset,
        limit: scanLimit,
      });
    }
  }, [selectedPreset, scanLimit, scanMarketMutation]);

  return (
    <div className="page-content">
      <h1 className="h3 mb-4">Market Scanner</h1>
      
      <Row className="g-4">
        {/* Scanner Controls */}
        <Col lg={4}>
          <Card title="Scanner Controls" className="h-100">
            <div className="mb-3">
              <Form.Group>
                <Form.Label>Select Preset</Form.Label>
                <Form.Select
                  value={selectedPreset}
                  onChange={(e) => setSelectedPreset(e.target.value)}
                  disabled={scanMarketMutation.isPending}
                >
                  <option value="">Choose a preset...</option>
                  {presets?.map((preset) => (
                    <option key={preset.name} value={preset.name}>
                      {preset.name}
                    </option>
                  ))}
                </Form.Select>
              </Form.Group>
            </div>

            <div className="mb-3">
              <Form.Group>
                <Form.Label>Scan Limit</Form.Label>
                <Form.Control
                  type="number"
                  value={scanLimit}
                  onChange={(e) => setScanLimit(Number(e.target.value))}
                  min={1}
                  max={50}
                  disabled={scanMarketMutation.isPending}
                />
              </Form.Group>
            </div>

            <div className="d-grid">
              <Button
                onClick={handleScan}
                disabled={!selectedPreset || scanMarketMutation.isPending}
                loading={scanMarketMutation.isPending}
                loadingText="Scanning..."
                variant="primary"
                size="lg"
              >
                Scan Market
              </Button>
            </div>

            {scanMarketMutation.isSuccess && (
              <div className="alert alert-success mt-3 mb-0">
                Scan completed successfully!
              </div>
            )}

            {scanMarketMutation.isError && (
              <div className="alert alert-danger mt-3 mb-0">
                Scan failed: {(scanMarketMutation.error as any)?.detail || scanMarketMutation.error?.message}
              </div>
            )}

            {scanMarketMutation.isPending && (
              <div className="alert alert-info mt-3 mb-0">
                Scanning market... Please wait.
              </div>
            )}
          </Card>
        </Col>

        {/* Scan Results */}
        <Col lg={8}>
          <Card
            title="Scan Results"
            loading={scanLoading}
            empty={!lastScan?.candidates?.length}
            emptyMessage="No scan results available"
          >
            {lastScan && lastScan.candidates && lastScan.candidates.length > 0 ? (
              <div>
                <div className="d-flex justify-content-between align-items-center mb-3">
                  <div>
                    <span className="text-muted">Last scan: </span>
                    <span>{new Date(lastScan.timestamp).toLocaleString()}</span>
                  </div>
                  <div>
                    <StatusBadge 
                      status={`${lastScan.passedFilters} passed`} 
                      variant="info"
                      className="me-2"
                    />
                    <StatusBadge 
                      status={`${lastScan.totalScanned} total`} 
                      variant="secondary"
                    />
                  </div>
                </div>

                <div className="fixed-height-table">
                  <Table
                    data={lastScan.candidates}
                    columns={candidateColumns}
                    loading={scanLoading}
                  />
                </div>
              </div>
            ) : (
              <EmptyScanResults onStartScan={handleScan} />
            )}
          </Card>
        </Col>
      </Row>
    </div>
  );
};
