/**
 * Tooltip компонент для показа подсказок
 * Использует Bootstrap Tooltip или кастомную реализацию
 */

import React from 'react';
import { OverlayTrigger, Tooltip as BSTooltip } from 'react-bootstrap';
import type { Placement } from 'react-bootstrap/esm/types';

export interface TooltipProps {
  content: string;
  children: React.ReactElement;
  placement?: Placement;
  delay?: number;
  className?: string;
  disabled?: boolean;
}

/**
 * Tooltip компонент с поддержкой многострочного текста
 */
export const Tooltip: React.FC<TooltipProps> = ({
  content,
  children,
  placement = 'top',
  delay = 200,
  className = '',
  disabled = false,
}) => {
  if (disabled || !content) {
    return children;
  }

  const renderTooltip = (props: any) => (
    <BSTooltip id="tooltip" {...props} className={className}>
      {content}
    </BSTooltip>
  );

  return (
    <OverlayTrigger
      placement={placement}
      delay={{ show: delay, hide: 0 }}
      overlay={renderTooltip}
    >
      {children}
    </OverlayTrigger>
  );
};

/**
 * Info Icon с tooltip для использования рядом с метриками
 */
export interface InfoIconProps {
  tooltip: string;
  placement?: Placement;
  className?: string;
}

export const InfoIcon: React.FC<InfoIconProps> = ({
  tooltip,
  placement = 'top',
  className = '',
}) => {
  return (
    <Tooltip content={tooltip} placement={placement}>
      <span
        className={`info-icon ${className}`}
        style={{
          marginLeft: '4px',
          cursor: 'help',
          color: '#6c757d',
          fontSize: '0.875rem',
        }}
      >
        ⓘ
      </span>
    </Tooltip>
  );
};

/**
 * Wrapper для текста с подсказкой снизу (underline dotted)
 */
export interface TooltipTextProps {
  children: React.ReactNode;
  tooltip: string;
  placement?: Placement;
}

export const TooltipText: React.FC<TooltipTextProps> = ({
  children,
  tooltip,
  placement = 'top',
}) => {
  return (
    <Tooltip content={tooltip} placement={placement}>
      <span
        style={{
          borderBottom: '1px dotted currentColor',
          cursor: 'help',
        }}
      >
        {children}
      </span>
    </Tooltip>
  );
};

/**
 * Tooltip для метрик с иконкой и значением
 */
export interface MetricTooltipProps {
  label: string;
  value: string | number;
  tooltip: string;
  icon?: string;
  className?: string;
}

export const MetricTooltip: React.FC<MetricTooltipProps> = ({
  label,
  value,
  tooltip,
  icon,
  className = '',
}) => {
  return (
    <div className={`d-flex justify-content-between align-items-center ${className}`}>
      <Tooltip content={tooltip} placement="left">
        <span style={{ cursor: 'help' }}>
          {icon && <span className="me-1">{icon}</span>}
          {label}:
        </span>
      </Tooltip>
      <span className="fw-bold">{value}</span>
    </div>
  );
};

export default Tooltip;
