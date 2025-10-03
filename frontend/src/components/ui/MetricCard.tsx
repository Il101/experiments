/**
 * Компонент карточки метрики с цветовым кодированием и иконками
 */

import React from 'react';
import { Card } from 'react-bootstrap';

export interface MetricCardProps {
  title: string;
  value: string | number;
  icon?: string;
  trend?: 'up' | 'down' | 'neutral';
  variant?: 'primary' | 'secondary' | 'success' | 'danger' | 'warning' | 'info';
  size?: 'sm' | 'md' | 'lg';
  className?: string;
  subtitle?: string;
  isLoading?: boolean;
}

export const MetricCard: React.FC<MetricCardProps> = ({
  title,
  value,
  icon,
  trend,
  variant = 'primary',
  size = 'md',
  className = '',
  subtitle,
  isLoading = false,
}) => {
  const getTrendIcon = () => {
    if (trend === 'up') return '📈';
    if (trend === 'down') return '📉';
    return '➡️';
  };

  const getTrendColor = () => {
    if (trend === 'up') return 'text-success';
    if (trend === 'down') return 'text-danger';
    return 'text-muted';
  };

  const getVariantClass = () => {
    const variants = {
      primary: 'border-primary',
      secondary: 'border-secondary',
      success: 'border-success',
      danger: 'border-danger',
      warning: 'border-warning',
      info: 'border-info',
    };
    return variants[variant] || variants.primary;
  };

  const getSizeClass = () => {
    if (size === 'sm') return 'h6';
    if (size === 'lg') return 'h3';
    return 'h4';
  };

  if (isLoading) {
    return (
      <Card className={`${getVariantClass()} ${className}`}>
        <Card.Body className="text-center">
          <div className="spinner-border spinner-border-sm text-primary" role="status">
            <span className="visually-hidden">Загрузка...</span>
          </div>
          <div className="mt-2 text-muted">{title}</div>
        </Card.Body>
      </Card>
    );
  }

  return (
    <Card className={`${getVariantClass()} ${className}`}>
      <Card.Body className="text-center">
        {icon && (
          <div className="mb-2" style={{ fontSize: '1.5rem' }}>
            {icon}
          </div>
        )}
        <Card.Title className={`${getSizeClass()} mb-1`}>
          {value}
        </Card.Title>
        <Card.Text className="text-muted mb-1">
          {title}
        </Card.Text>
        {subtitle && (
          <Card.Text className="small text-muted">
            {subtitle}
          </Card.Text>
        )}
        {trend && (
          <div className={`small ${getTrendColor()}`}>
            {getTrendIcon()}
          </div>
        )}
      </Card.Body>
    </Card>
  );
};

// Специализированные компоненты для торговых метрик
export const PnLMetric: React.FC<{ value: number; currency?: string }> = ({ 
  value, 
  currency = 'R' 
}) => {
  const isPositive = value > 0;
  const isNegative = value < 0;
  
  return (
    <MetricCard
      title={`PnL (${currency})`}
      value={value.toFixed(2)}
      icon={isPositive ? '💰' : isNegative ? '📉' : '💼'}
      variant={isPositive ? 'success' : isNegative ? 'danger' : 'secondary'}
      trend={isPositive ? 'up' : isNegative ? 'down' : 'neutral'}
    />
  );
};

export const WinRateMetric: React.FC<{ value: number }> = ({ value }) => {
  const isGood = value >= 50;
  const isExcellent = value >= 70;
  
  return (
    <MetricCard
      title="Win Rate"
      value={`${value.toFixed(1)}%`}
      icon={isExcellent ? '🏆' : isGood ? '✅' : '📊'}
      variant={isExcellent ? 'success' : isGood ? 'info' : 'warning'}
    />
  );
};

export const LatencyMetric: React.FC<{ value: number }> = ({ value }) => {
  const isGood = value < 100;
  const isExcellent = value < 50;
  
  return (
    <MetricCard
      title="Latency"
      value={`${value}ms`}
      icon={isExcellent ? '⚡' : isGood ? '🚀' : '🐌'}
      variant={isExcellent ? 'success' : isGood ? 'info' : 'warning'}
    />
  );
};
