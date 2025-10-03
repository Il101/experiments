/**
 * Command Button Component
 * Button with integrated confirmation dialog for engine commands
 */

import React, { useState } from 'react';
import { Button, type ButtonProps } from 'react-bootstrap';
import { ConfirmDialog } from './ConfirmDialog';

export interface CommandConfig {
  command: string;
  label: string;
  icon: string;
  variant: ButtonProps['variant'];
  requiresConfirmation: boolean;
  confirmTitle?: string;
  confirmMessage?: string;
  confirmDetails?: string[];
  confirmVariant?: 'danger' | 'warning' | 'info';
}

export interface CommandButtonProps {
  config: CommandConfig;
  onClick: (command: string) => void;
  loading?: boolean;
  disabled?: boolean;
  size?: 'sm' | 'lg';
  className?: string;
}

export const CommandButton: React.FC<CommandButtonProps> = ({
  config,
  onClick,
  loading = false,
  disabled = false,
  size,
  className = '',
}) => {
  const [showConfirm, setShowConfirm] = useState(false);

  const handleClick = () => {
    if (config.requiresConfirmation) {
      setShowConfirm(true);
    } else {
      onClick(config.command);
    }
  };

  const handleConfirm = () => {
    onClick(config.command);
    setShowConfirm(false);
  };

  const handleCancel = () => {
    setShowConfirm(false);
  };

  return (
    <>
      <Button
        variant={config.variant}
        size={size}
        onClick={handleClick}
        disabled={disabled || loading}
        className={className}
      >
        {loading ? (
          <>
            <span className="spinner-border spinner-border-sm me-2" />
            Processing...
          </>
        ) : (
          <>
            <span className="me-2">{config.icon}</span>
            {config.label}
          </>
        )}
      </Button>

      {config.requiresConfirmation && (
        <ConfirmDialog
          show={showConfirm}
          title={config.confirmTitle || `Confirm ${config.label}`}
          message={config.confirmMessage || `Are you sure you want to ${config.label.toLowerCase()}?`}
          confirmText={config.label}
          cancelText="Cancel"
          danger={config.confirmVariant === 'danger'}
          onConfirm={handleConfirm}
          onCancel={handleCancel}
          loading={loading}
        />
      )}
    </>
  );
};

export default CommandButton;
