/**
 * Переиспользуемый компонент модального окна
 */

import React from 'react';
import { Modal as BootstrapModal, type ModalProps as BootstrapModalProps } from 'react-bootstrap';
import { Button } from './Button';

export interface ModalProps extends Omit<BootstrapModalProps, 'onHide'> {
  title?: string;
  subtitle?: string;
  onClose: () => void;
  onConfirm?: () => void;
  confirmText?: string;
  cancelText?: string;
  confirmVariant?: 'primary' | 'secondary' | 'success' | 'danger' | 'warning' | 'info';
  loading?: boolean;
  size?: 'sm' | 'lg' | 'xl';
  centered?: boolean;
  scrollable?: boolean;
}

export const Modal: React.FC<ModalProps> = ({
  children,
  title,
  subtitle,
  onClose,
  onConfirm,
  confirmText = 'Confirm',
  cancelText = 'Cancel',
  confirmVariant = 'primary',
  loading = false,
  size,
  centered = true,
  scrollable = false,
  show,
  className = '',
  ...props
}) => {
  const handleConfirm = () => {
    if (onConfirm && !loading) {
      onConfirm();
    }
  };

  const renderHeader = () => {
    if (!title && !subtitle) return null;

    return (
      <BootstrapModal.Header closeButton onHide={onClose}>
        <BootstrapModal.Title>{title}</BootstrapModal.Title>
        {subtitle && (
          <p className="text-muted small mb-0 mt-1">{subtitle}</p>
        )}
      </BootstrapModal.Header>
    );
  };

  const renderFooter = () => {
    if (!onConfirm) return null;

    return (
      <BootstrapModal.Footer>
        <Button
          variant="outline-secondary"
          onClick={onClose}
          disabled={loading}
        >
          {cancelText}
        </Button>
        <Button
          variant={confirmVariant}
          onClick={handleConfirm}
          loading={loading}
        >
          {confirmText}
        </Button>
      </BootstrapModal.Footer>
    );
  };

  return (
    <BootstrapModal
      show={show}
      onHide={onClose}
      size={size}
      centered={centered}
      scrollable={scrollable}
      className={className}
      {...props}
    >
      {renderHeader()}
      <BootstrapModal.Body>{children}</BootstrapModal.Body>
      {renderFooter()}
    </BootstrapModal>
  );
};


