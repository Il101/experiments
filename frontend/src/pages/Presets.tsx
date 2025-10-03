/**
 * Страница управления пресетами
 */

import React, { useState } from 'react';
import { Row, Col, Badge, Modal } from 'react-bootstrap';
import { Card, Table, Button } from '../components/ui';
import { PresetEditForm } from '../components/PresetEditForm';
import { usePresets, usePreset, useUpdatePreset } from '../hooks';

export const Presets: React.FC = () => {
  const [selectedPreset, setSelectedPreset] = useState<string | null>(null);
  const [showConfigModal, setShowConfigModal] = useState(false);

  const { data: presets, isLoading: presetsLoading } = usePresets();
  const { data: presetConfig, isLoading: configLoading } = usePreset(selectedPreset || '');
  const updatePresetMutation = useUpdatePreset();

  const presetColumns = [
    {
      key: 'name',
      title: 'Name',
    },
    {
      key: 'description',
      title: 'Description',
    },
    {
      key: 'strategy_type',
      title: 'Strategy',
      render: (value: string) => (
        <Badge bg="outline-primary">{value}</Badge>
      ),
    },
    {
      key: 'risk_per_trade',
      title: 'Risk per Trade',
      render: (value: number) => `${(value * 100).toFixed(1)}%`,
    },
    {
      key: 'max_positions',
      title: 'Max Positions',
      render: (value: number) => (
        <Badge bg="outline-secondary">{value}</Badge>
      ),
    },
    {
      key: 'actions',
      title: 'Actions',
      render: (_: any, item: any) => (
        <div className="d-flex gap-2">
          <Button
            size="sm"
            variant="outline-primary"
            onClick={() => {
              setSelectedPreset(item.name);
              setShowConfigModal(true);
            }}
          >
            View Config
          </Button>
        </div>
      ),
    },
  ];

  const handleUpdatePreset = (updatedConfig: Record<string, any>) => {
    if (selectedPreset) {
      updatePresetMutation.mutate({
        name: selectedPreset,
        config: updatedConfig,
      }, {
        onSuccess: () => {
          setShowConfigModal(false);
        }
      });
    }
  };

  return (
    <div className="page-content">
      <h1 className="h3 mb-4">Trading Presets</h1>
      
      <Row className="g-4">
        <Col>
          <Card
            title="Available Presets"
            loading={presetsLoading}
            empty={!presets?.length}
            emptyMessage="No presets available"
          >
            <Table
              data={presets || []}
              columns={presetColumns}
              loading={presetsLoading}
            />
          </Card>
        </Col>
      </Row>

      {/* Preset Configuration Modal */}
      <Modal
        show={showConfigModal}
        onHide={() => setShowConfigModal(false)}
        size="xl"
        scrollable
      >
        <Modal.Header closeButton>
          <Modal.Title>
            Preset Configuration: {selectedPreset}
          </Modal.Title>
        </Modal.Header>
        <Modal.Body>
          {configLoading ? (
            <div className="text-center py-4">
              <div className="spinner-border text-primary" role="status">
                <span className="visually-hidden">Loading...</span>
              </div>
              <p className="mt-2 text-muted">Loading configuration...</p>
            </div>
          ) : presetConfig ? (
            <PresetEditForm
              preset={presetConfig}
              onSave={handleUpdatePreset}
              onCancel={() => setShowConfigModal(false)}
              loading={updatePresetMutation.isPending}
            />
          ) : (
            <div className="text-center py-4 text-muted">
              No configuration available
            </div>
          )}
        </Modal.Body>
      </Modal>
    </div>
  );
};


