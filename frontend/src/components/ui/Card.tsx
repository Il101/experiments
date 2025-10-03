/**
 * Переиспользуемый компонент карточки
 */

import React from 'react';
import { Card as BootstrapCard, type CardProps as BootstrapCardProps } from 'react-bootstrap';

export interface CardProps extends BootstrapCardProps {
  title?: string;
  subtitle?: string;
  headerActions?: React.ReactNode;
  loading?: boolean;
  loadingSkeleton?: React.ReactNode;
  empty?: boolean;
  emptyMessage?: string;
  emptyIcon?: React.ReactNode;
}

export const Card: React.FC<CardProps> = ({
  children,
  title,
  subtitle,
  headerActions,
  loading = false,
  loadingSkeleton,
  empty = false,
  emptyMessage = 'No data available',
  emptyIcon,
  className = '',
  ...props
}) => {
  const renderHeader = () => {
    if (!title && !subtitle && !headerActions) return null;

    return (
      <BootstrapCard.Header className="d-flex justify-content-between align-items-center">
        <div>
          {title && <BootstrapCard.Title className="mb-0">{title}</BootstrapCard.Title>}
          {subtitle && <BootstrapCard.Subtitle className="text-muted small">{subtitle}</BootstrapCard.Subtitle>}
        </div>
        {headerActions && <div>{headerActions}</div>}
      </BootstrapCard.Header>
    );
  };

  const renderBody = () => {
    if (loading) {
      // Если передан кастомный skeleton, используем его
      if (loadingSkeleton) {
        return <BootstrapCard.Body>{loadingSkeleton}</BootstrapCard.Body>;
      }
      
      // Иначе показываем стандартный спиннер
      return (
        <BootstrapCard.Body className="text-center py-5">
          <div className="spinner-border text-primary" role="status">
            <span className="visually-hidden">Loading...</span>
          </div>
          <p className="mt-2 text-muted">Loading...</p>
        </BootstrapCard.Body>
      );
    }

    if (empty) {
      return (
        <BootstrapCard.Body className="text-center py-5">
          {emptyIcon && <div className="mb-3">{emptyIcon}</div>}
          <p className="text-muted">{emptyMessage}</p>
        </BootstrapCard.Body>
      );
    }

    return <BootstrapCard.Body>{children}</BootstrapCard.Body>;
  };

  return (
    <BootstrapCard className={`shadow-sm ${className}`} {...props}>
      {renderHeader()}
      {renderBody()}
    </BootstrapCard>
  );
};


