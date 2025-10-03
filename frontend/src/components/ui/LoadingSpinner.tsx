/**
 * Компонент индикатора загрузки
 */

import React from 'react';
import { Spinner } from 'react-bootstrap';

export interface LoadingSpinnerProps {
  size?: 'sm';
  variant?: 'primary' | 'secondary' | 'success' | 'danger' | 'warning' | 'info' | 'light' | 'dark';
  text?: string;
  centered?: boolean;
  className?: string;
}

export const LoadingSpinner: React.FC<LoadingSpinnerProps> = ({
  size = 'sm',
  variant = 'primary',
  text,
  centered = false,
  className = '',
}) => {
  const spinnerElement = (
    <div className={`d-flex align-items-center ${centered ? 'justify-content-center' : ''} ${className}`}>
      <Spinner
        animation="border"
        size={size}
        variant={variant}
        role="status"
        aria-hidden="true"
      />
      {text && (
        <span className={`ms-2 ${centered ? 'text-center' : ''}`}>
          {text}
        </span>
      )}
    </div>
  );

  if (centered) {
    return (
      <div className="d-flex justify-content-center align-items-center min-vh-50">
        {spinnerElement}
      </div>
    );
  }

  return spinnerElement;
};


