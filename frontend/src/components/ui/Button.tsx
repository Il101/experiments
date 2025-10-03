/**
 * Переиспользуемый компонент кнопки
 */

import React from 'react';
import { Button as BootstrapButton, Spinner } from 'react-bootstrap';
import type { ButtonProps as BootstrapButtonProps } from 'react-bootstrap/Button';

export interface ButtonProps extends Omit<BootstrapButtonProps, 'variant' | 'size'> {
  variant?: 'primary' | 'secondary' | 'success' | 'danger' | 'warning' | 'info' | 'light' | 'dark' | 'outline-primary' | 'outline-secondary' | 'outline-success' | 'outline-danger' | 'outline-warning' | 'outline-info' | 'outline-light' | 'outline-dark';
  size?: 'sm' | 'lg';
  loading?: boolean;
  loadingText?: string;
  icon?: React.ReactNode;
  iconPosition?: 'left' | 'right';
  fullWidth?: boolean;
}

export const Button: React.FC<ButtonProps> = ({
  children,
  variant = 'primary',
  size,
  loading = false,
  loadingText = 'Loading...',
  icon,
  iconPosition = 'left',
  fullWidth = false,
  disabled,
  className = '',
  ...props
}) => {
  const isDisabled = disabled || loading;
  const buttonContent = loading ? loadingText : children;

  const iconElement = icon && !loading ? (
    <span className={iconPosition === 'left' ? 'me-2' : 'ms-2'}>
      {icon}
    </span>
  ) : null;

  const loadingElement = loading ? (
    <Spinner
      as="span"
      animation="border"
      size="sm"
      role="status"
      aria-hidden="true"
      className={iconPosition === 'left' ? 'me-2' : 'ms-2'}
    />
  ) : null;

  return (
    <BootstrapButton
      variant={variant}
      size={size}
      disabled={isDisabled}
      className={`${fullWidth ? 'w-100' : ''} ${className}`}
      {...props}
    >
      {iconPosition === 'left' && (iconElement || loadingElement)}
      {buttonContent}
      {iconPosition === 'right' && (iconElement || loadingElement)}
    </BootstrapButton>
  );
};


