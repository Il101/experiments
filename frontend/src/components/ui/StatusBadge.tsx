/**
 * Компонент статусного бейджа с иконками и улучшенным UX
 */

import React from 'react';
import { Badge } from 'react-bootstrap';

export interface StatusBadgeProps {
  status: string;
  variant?: 'primary' | 'secondary' | 'success' | 'danger' | 'warning' | 'info' | 'light' | 'dark';
  size?: 'sm' | 'lg';
  className?: string;
  showIcon?: boolean;
}

interface StatusConfig {
  variant: string;
  icon: string;
  description: string;
}

const getStatusConfig = (status: string): StatusConfig => {
  const statusLower = status.toLowerCase();
  
  // Engine states
  if (statusLower === 'idle') {
    return { variant: 'secondary', icon: '⏸️', description: 'Движок остановлен' };
  }
  if (statusLower === 'scanning') {
    return { variant: 'info', icon: '🔍', description: 'Сканирование рынка' };
  }
  if (statusLower === 'signal_wait') {
    return { variant: 'warning', icon: '⏳', description: 'Ожидание сигналов' };
  }
  if (statusLower === 'execution') {
    return { variant: 'primary', icon: '⚡', description: 'Исполнение ордеров' };
  }
  if (statusLower === 'managing') {
    return { variant: 'success', icon: '📊', description: 'Управление позициями' };
  }
  if (statusLower === 'error') {
    return { variant: 'danger', icon: '❌', description: 'Ошибка системы' };
  }
  if (statusLower === 'emergency') {
    return { variant: 'danger', icon: '🚨', description: 'Аварийная остановка' };
  }
  
  // Connection states
  if (statusLower === 'connected') {
    return { variant: 'success', icon: '🟢', description: 'Подключено' };
  }
  if (statusLower === 'disconnected') {
    return { variant: 'danger', icon: '🔴', description: 'Отключено' };
  }
  if (statusLower === 'connecting') {
    return { variant: 'warning', icon: '🟡', description: 'Подключение...' };
  }
  
  // Trading states
  if (statusLower === 'paper') {
    return { variant: 'info', icon: '📄', description: 'Бумажная торговля' };
  }
  if (statusLower === 'live') {
    return { variant: 'success', icon: '💰', description: 'Реальная торговля' };
  }
  
  // Generic states
  if (statusLower.includes('running') || statusLower.includes('active') || statusLower.includes('success')) {
    return { variant: 'success', icon: '✅', description: 'Активно' };
  }
  if (statusLower.includes('stopped') || statusLower.includes('inactive') || statusLower.includes('error')) {
    return { variant: 'danger', icon: '❌', description: 'Остановлено' };
  }
  if (statusLower.includes('pending') || statusLower.includes('waiting') || statusLower.includes('loading')) {
    return { variant: 'warning', icon: '⏳', description: 'Ожидание' };
  }
  if (statusLower.includes('paused')) {
    return { variant: 'secondary', icon: '⏸️', description: 'Приостановлено' };
  }
  
  return { variant: 'primary', icon: 'ℹ️', description: status };
};

export const StatusBadge: React.FC<StatusBadgeProps> = ({
  status,
  variant,
  size = 'sm',
  className = '',
  showIcon = true,
}) => {
  const statusConfig = getStatusConfig(status);
  const badgeVariant = variant || statusConfig.variant;
  
  return (
    <Badge
      bg={badgeVariant}
      className={`${size === 'lg' ? 'fs-6' : ''} ${className}`}
      title={statusConfig.description}
    >
      {showIcon && statusConfig.icon} {status}
    </Badge>
  );
};


