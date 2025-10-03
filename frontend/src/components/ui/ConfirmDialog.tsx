/**
 * Компонент диалога подтверждения действий
 */

import React from 'react';
import { Modal, Button } from 'react-bootstrap';

export interface ConfirmDialogProps {
  show: boolean;
  title: string;
  message: string;
  confirmText?: string;
  cancelText?: string;
  danger?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
  loading?: boolean;
}

export const ConfirmDialog: React.FC<ConfirmDialogProps> = ({
  show,
  title,
  message,
  confirmText = 'Подтвердить',
  cancelText = 'Отмена',
  danger = false,
  onConfirm,
  onCancel,
  loading = false,
}) => {
  return (
    <Modal show={show} onHide={onCancel} centered>
      <Modal.Header closeButton>
        <Modal.Title>{title}</Modal.Title>
      </Modal.Header>
      
      <Modal.Body>
        <div style={{ whiteSpace: 'pre-line' }}>
          {message}
        </div>
      </Modal.Body>
      
      <Modal.Footer>
        <Button 
          variant="secondary" 
          onClick={onCancel}
          disabled={loading}
        >
          {cancelText}
        </Button>
        <Button 
          variant={danger ? 'danger' : 'primary'} 
          onClick={onConfirm}
          disabled={loading}
        >
          {loading ? (
            <>
              <span className="spinner-border spinner-border-sm me-2" />
              Выполняется...
            </>
          ) : (
            confirmText
          )}
        </Button>
      </Modal.Footer>
    </Modal>
  );
};

export default ConfirmDialog;
