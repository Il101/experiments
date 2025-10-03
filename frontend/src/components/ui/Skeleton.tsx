/**
 * Skeleton компонент для loading состояний
 * Показывает placeholder'ы вместо данных во время загрузки
 */

import React from 'react';
import './Skeleton.css';

export interface SkeletonProps {
  width?: string | number;
  height?: string | number;
  variant?: 'text' | 'circular' | 'rectangular';
  animation?: 'pulse' | 'wave' | 'none';
  count?: number;
  className?: string;
}

export const Skeleton: React.FC<SkeletonProps> = ({
  width = '100%',
  height = '1rem',
  variant = 'text',
  animation = 'pulse',
  count = 1,
  className = '',
}) => {
  const skeletonStyle: React.CSSProperties = {
    width: typeof width === 'number' ? `${width}px` : width,
    height: typeof height === 'number' ? `${height}px` : height,
  };

  const skeletonClass = [
    'skeleton',
    `skeleton-${variant}`,
    `skeleton-${animation}`,
    className,
  ]
    .filter(Boolean)
    .join(' ');

  if (count === 1) {
    return <div className={skeletonClass} style={skeletonStyle} />;
  }

  return (
    <>
      {Array.from({ length: count }).map((_, index) => (
        <div key={index} className={skeletonClass} style={skeletonStyle} />
      ))}
    </>
  );
};

/**
 * Skeleton для таблиц
 */
export interface TableSkeletonProps {
  rows?: number;
  columns?: number;
  className?: string;
}

export const TableSkeleton: React.FC<TableSkeletonProps> = ({
  rows = 5,
  columns = 4,
  className = '',
}) => {
  return (
    <div className={`table-skeleton ${className}`}>
      {/* Header */}
      <div className="skeleton-table-header">
        {Array.from({ length: columns }).map((_, index) => (
          <Skeleton key={`header-${index}`} height={20} />
        ))}
      </div>
      
      {/* Rows */}
      {Array.from({ length: rows }).map((_, rowIndex) => (
        <div key={`row-${rowIndex}`} className="skeleton-table-row">
          {Array.from({ length: columns }).map((_, colIndex) => (
            <Skeleton key={`cell-${rowIndex}-${colIndex}`} height={16} />
          ))}
        </div>
      ))}
    </div>
  );
};

/**
 * Skeleton для карточек метрик
 */
export const MetricCardSkeleton: React.FC<{ count?: number }> = ({ count = 1 }) => {
  return (
    <>
      {Array.from({ length: count }).map((_, index) => (
        <div key={index} className="metric-card-skeleton">
          <Skeleton variant="circular" width={40} height={40} className="mb-2" />
          <Skeleton height={32} width="60%" className="mb-1" />
          <Skeleton height={16} width="80%" />
        </div>
      ))}
    </>
  );
};

/**
 * Skeleton для позиций
 */
export const PositionCardSkeleton: React.FC<{ count?: number }> = ({ count = 3 }) => {
  return (
    <>
      {Array.from({ length: count }).map((_, index) => (
        <div key={index} className="position-card-skeleton mb-3">
          <div className="d-flex justify-content-between align-items-center mb-2">
            <Skeleton width={80} height={24} />
            <Skeleton width={60} height={24} />
          </div>
          <Skeleton height={40} className="mb-2" />
          <div className="d-flex gap-2">
            <Skeleton width="30%" height={16} />
            <Skeleton width="30%" height={16} />
            <Skeleton width="30%" height={16} />
          </div>
        </div>
      ))}
    </>
  );
};

/**
 * Skeleton для графика
 */
export const ChartSkeleton: React.FC<{ height?: number }> = ({ height = 400 }) => {
  return (
    <div className="chart-skeleton" style={{ height: `${height}px` }}>
      <div className="chart-skeleton-grid">
        {Array.from({ length: 5 }).map((_, index) => (
          <div key={index} className="chart-skeleton-line" />
        ))}
      </div>
      <div className="chart-skeleton-bars">
        {Array.from({ length: 12 }).map((_, index) => (
          <div
            key={index}
            className="chart-skeleton-bar"
            style={{ height: `${Math.random() * 80 + 20}%` }}
          />
        ))}
      </div>
    </div>
  );
};

/**
 * Skeleton для логов
 */
export const LogEntrySkeleton: React.FC<{ count?: number }> = ({ count = 10 }) => {
  return (
    <>
      {Array.from({ length: count }).map((_, index) => (
        <div key={index} className="log-entry-skeleton mb-2">
          <div className="d-flex align-items-center gap-2">
            <Skeleton variant="circular" width={8} height={8} />
            <Skeleton width={80} height={14} />
            <Skeleton width={100} height={14} />
            <Skeleton width="50%" height={14} />
          </div>
        </div>
      ))}
    </>
  );
};

export default Skeleton;
