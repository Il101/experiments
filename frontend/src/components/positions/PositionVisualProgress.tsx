/**
 * Position Visual Progress - визуальный прогресс-бар позиции
 * Показывает SL → Entry → Current → TP
 */

import React, { useMemo } from 'react';
import { OverlayTrigger, Tooltip } from 'react-bootstrap';
import './PositionCard.css';

export interface PositionVisualProgressProps {
  side: 'long' | 'short';
  sl?: number;
  entry: number;
  current: number;
  tp?: number;
  compact?: boolean;
}

export const PositionVisualProgress: React.FC<PositionVisualProgressProps> = ({
  side,
  sl,
  entry,
  current,
  tp,
  compact = false,
}) => {
  const progress = useMemo(() => {
    // Для LONG: SL < Entry < Current < TP
    // Для SHORT: TP < Current < Entry < SL
    
    const isLong = side === 'long';
    
    // Определяем диапазон
    const min = isLong 
      ? (sl || entry * 0.95) 
      : (tp || entry * 0.95);
    const max = isLong 
      ? (tp || entry * 1.05) 
      : (sl || entry * 1.05);
    
    const range = max - min;
    
    // Позиции в процентах (0-100%)
    const slPosition = sl 
      ? ((sl - min) / range) * 100 
      : (isLong ? 0 : 100);
    const entryPosition = ((entry - min) / range) * 100;
    const currentPosition = ((current - min) / range) * 100;
    const tpPosition = tp 
      ? ((tp - min) / range) * 100 
      : (isLong ? 100 : 0);

    // Прогресс от Entry к TP
    const entryToTP = isLong 
      ? tpPosition - entryPosition 
      : entryPosition - tpPosition;
    const currentProgress = isLong
      ? ((currentPosition - entryPosition) / entryToTP) * 100
      : ((entryPosition - currentPosition) / entryToTP) * 100;

    // Защита от выхода за пределы
    const clampedProgress = Math.max(0, Math.min(100, currentProgress));
    
    // В прибыли или убытке?
    const inProfit = isLong ? current > entry : current < entry;
    const inLoss = isLong ? current < entry : current > entry;

    return {
      slPosition: Math.max(0, Math.min(100, slPosition)),
      entryPosition: Math.max(0, Math.min(100, entryPosition)),
      currentPosition: Math.max(0, Math.min(100, currentPosition)),
      tpPosition: Math.max(0, Math.min(100, tpPosition)),
      currentProgress: clampedProgress,
      inProfit,
      inLoss,
      isLong,
    };
  }, [side, sl, entry, current, tp]);

  const progressColor = progress.inProfit 
    ? 'success' 
    : progress.inLoss 
    ? 'danger' 
    : 'warning';

  const renderMarker = (
    label: string,
    position: number,
    color: string,
    value?: number
  ) => {
    const marker = (
      <div
        className={`progress-marker marker-${color}`}
        style={{ left: `${position}%` }}
      >
        <div className="marker-line"></div>
        {!compact && (
          <div className="marker-label">
            <span className="marker-text">{label}</span>
            {value && <span className="marker-value">${value.toFixed(2)}</span>}
          </div>
        )}
      </div>
    );

    if (value && compact) {
      return (
        <OverlayTrigger
          placement="top"
          overlay={
            <Tooltip>
              <strong>{label}:</strong> ${value.toFixed(2)}
            </Tooltip>
          }
        >
          {marker}
        </OverlayTrigger>
      );
    }

    return marker;
  };

  return (
    <div className={`position-visual-progress ${compact ? 'compact' : ''}`}>
      {/* Progress Bar Track */}
      <div className="progress-track">
        {/* Entry to Current (filled) */}
        <div
          className={`progress-fill progress-fill-${progressColor}`}
          style={{
            left: `${Math.min(progress.entryPosition, progress.currentPosition)}%`,
            width: `${Math.abs(progress.currentPosition - progress.entryPosition)}%`,
          }}
        ></div>
        
        {/* Risk Zone (Entry to SL) */}
        {sl && (
          <div
            className="progress-risk-zone"
            style={{
              left: `${Math.min(progress.slPosition, progress.entryPosition)}%`,
              width: `${Math.abs(progress.entryPosition - progress.slPosition)}%`,
            }}
          ></div>
        )}
      </div>

      {/* Markers */}
      {sl && renderMarker('SL', progress.slPosition, 'danger', sl)}
      {renderMarker('Entry', progress.entryPosition, 'info', entry)}
      {renderMarker('Now', progress.currentPosition, progressColor, current)}
      {tp && renderMarker('TP', progress.tpPosition, 'success', tp)}

      {/* Progress Percentage (for compact) */}
      {compact && (
        <div className="progress-percentage">
          <small className={`text-${progressColor}`}>
            {progress.currentProgress.toFixed(0)}%
          </small>
        </div>
      )}
    </div>
  );
};

export default PositionVisualProgress;
