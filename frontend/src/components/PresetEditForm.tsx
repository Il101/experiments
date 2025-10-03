/**
 * Компонент для редактирования preset конфигурации
 */

import React, { useState, useEffect } from 'react';
import { Form, Row, Col, Button, Alert } from 'react-bootstrap';

interface PresetConfig {
  name: string;
  config: Record<string, any>;
}

interface PresetEditFormProps {
  preset: PresetConfig | null;
  onSave: (config: Record<string, any>) => void;
  onCancel: () => void;
  loading?: boolean;
}

export const PresetEditForm: React.FC<PresetEditFormProps> = ({
  preset,
  onSave,
  onCancel,
  loading = false
}) => {
  const [config, setConfig] = useState<Record<string, any>>({});
  const [errors, setErrors] = useState<Record<string, string>>({});

  useEffect(() => {
    if (preset) {
      setConfig(preset.config);
    }
  }, [preset]);

  const handleInputChange = (path: string[], value: any) => {
    setConfig(prev => {
      const newConfig = { ...prev };
      let current = newConfig;
      
      // Navigate to the nested property
      for (let i = 0; i < path.length - 1; i++) {
        if (!current[path[i]]) {
          current[path[i]] = {};
        }
        current = current[path[i]];
      }
      
      // Set the final value
      current[path[path.length - 1]] = value;
      return newConfig;
    });
  };

  const validateConfig = (): boolean => {
    const newErrors: Record<string, string> = {};

    // Validate risk settings
    const riskPerTrade = config.risk?.risk_per_trade;
    if (riskPerTrade && (riskPerTrade < 0 || riskPerTrade > 1)) {
      newErrors['risk.risk_per_trade'] = 'Risk per trade must be between 0 and 1';
    }

    const maxPositions = config.risk?.max_concurrent_positions;
    if (maxPositions && (maxPositions < 1 || maxPositions > 10)) {
      newErrors['risk.max_concurrent_positions'] = 'Max positions must be between 1 and 10';
    }

    // Validate scanner weights sum to 1.0
    const weights = config.scanner_config?.score_weights;
    if (weights) {
      const sum = Object.values(weights).reduce((acc: number, val: any) => acc + (val || 0), 0);
      if (Math.abs(sum - 1.0) > 0.001) {
        newErrors['scanner_config.score_weights'] = 'Score weights must sum to 1.0';
      }
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSave = () => {
    if (validateConfig()) {
      onSave(config);
    }
  };

  const renderNestedForm = (obj: any, path: string[] = []): React.ReactNode => {
    return Object.entries(obj).map(([key, value]) => {
      const currentPath = [...path, key];
      const fieldName = currentPath.join('.');

      if (typeof value === 'object' && value !== null && !Array.isArray(value)) {
        return (
          <div key={fieldName} className="mb-4">
            <h6 className="text-capitalize">{key.replace(/_/g, ' ')}</h6>
            <div className="ps-3 border-start">
              {renderNestedForm(value, currentPath)}
            </div>
          </div>
        );
      }

      if (Array.isArray(value)) {
        return (
          <div key={fieldName} className="mb-3">
            <Form.Label className="text-capitalize">
              {key.replace(/_/g, ' ')}
            </Form.Label>
            <Form.Control
              as="textarea"
              value={JSON.stringify(value, null, 2)}
              onChange={(e) => {
                try {
                  const parsed = JSON.parse(e.target.value);
                  handleInputChange(currentPath, parsed);
                } catch {
                  // Invalid JSON, keep the text as is
                }
              }}
              isInvalid={!!errors[fieldName]}
            />
            <Form.Control.Feedback type="invalid">
              {errors[fieldName]}
            </Form.Control.Feedback>
          </div>
        );
      }

      return (
        <Form.Group key={fieldName} className="mb-3">
          <Form.Label className="text-capitalize">
            {key.replace(/_/g, ' ')}
          </Form.Label>
          <Form.Control
            type={typeof value === 'number' ? 'number' : 'text'}
            value={value || ''}
            onChange={(e) => {
              const newValue = typeof value === 'number' ? parseFloat(e.target.value) || 0 : e.target.value;
              handleInputChange(currentPath, newValue);
            }}
            isInvalid={!!errors[fieldName]}
            step={typeof value === 'number' ? '0.01' : undefined}
          />
          <Form.Control.Feedback type="invalid">
            {errors[fieldName]}
          </Form.Control.Feedback>
        </Form.Group>
      );
    });
  };

  if (!preset) {
    return (
      <div className="text-center py-4 text-muted">
        No preset selected
      </div>
    );
  }

  return (
    <div>
      <Alert variant="info" className="mb-4">
        <strong>Editing:</strong> {preset.name}
        <br />
        <small>Make your changes and click Save to update the preset configuration.</small>
      </Alert>

      <Form>
        {renderNestedForm(config)}
      </Form>

      <div className="d-flex justify-content-end gap-2 mt-4">
        <Button
          variant="outline-secondary"
          onClick={onCancel}
          disabled={loading}
        >
          Cancel
        </Button>
        <Button
          variant="primary"
          onClick={handleSave}
          disabled={loading}
        >
          {loading ? 'Saving...' : 'Save Changes'}
        </Button>
      </div>
    </div>
  );
};
