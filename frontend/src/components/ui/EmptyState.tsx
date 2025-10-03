/**
 * Компонент для пустых состояний с контекстом и действиями
 */

import React from 'react';
import { Card, Button } from 'react-bootstrap';

export interface EmptyStateProps {
  icon: string;
  title: string;
  description: string;
  actionText?: string;
  onAction?: () => void;
  variant?: 'primary' | 'secondary' | 'success' | 'danger' | 'warning' | 'info';
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  icon,
  title,
  description,
  actionText,
  onAction,
  variant = 'secondary',
  size = 'md',
  className = '',
}) => {
  const iconSize = size === 'sm' ? '2rem' : size === 'lg' ? '4rem' : '3rem';
  
  return (
    <Card className={`text-center border-0 bg-light ${className}`}>
      <Card.Body className="py-5">
        <div 
          className="mb-3"
          style={{ fontSize: iconSize }}
        >
          {icon}
        </div>
        <Card.Title className="h5 text-muted mb-2">
          {title}
        </Card.Title>
        <Card.Text className="text-muted mb-3">
          {description}
        </Card.Text>
        {actionText && onAction && (
          <Button 
            variant={variant}
            onClick={onAction}
            size={size === 'sm' ? 'sm' : 'md'}
          >
            {actionText}
          </Button>
        )}
      </Card.Body>
    </Card>
  );
};

// Предустановленные пустые состояния
export const EmptyPositions: React.FC<{ onStartTrading?: () => void }> = ({ onStartTrading }) => (
  <EmptyState
    icon="📊"
    title="Нет открытых позиций"
    description="Движок еще не открыл ни одной позиции. Убедитесь, что движок запущен и сканирует рынок."
    actionText="Запустить торговлю"
    onAction={onStartTrading}
    variant="primary"
  />
);

export const EmptyOrders: React.FC<{ onViewScanner?: () => void }> = ({ onViewScanner }) => (
  <EmptyState
    icon="📋"
    title="Нет ордеров"
    description="Ордера появятся здесь, когда движок начнет торговать. Проверьте сканер для поиска возможностей."
    actionText="Открыть сканер"
    onAction={onViewScanner}
    variant="info"
  />
);

export const EmptyScanResults: React.FC<{ onStartScan?: () => void }> = ({ onStartScan }) => (
  <EmptyState
    icon="🔍"
    title="Нет результатов сканирования"
    description="Запустите сканирование рынка, чтобы найти торговые возможности."
    actionText="Начать сканирование"
    onAction={onStartScan}
    variant="primary"
  />
);

export const EmptyLogs: React.FC<{ onRefresh?: () => void }> = ({ onRefresh }) => (
  <EmptyState
    icon="📝"
    title="Нет логов"
    description="Логи появятся здесь, когда система начнет работать."
    actionText="Обновить"
    onAction={onRefresh}
    variant="secondary"
  />
);
