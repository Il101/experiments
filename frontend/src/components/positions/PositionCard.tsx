/**
 * Position Card - визуальная карточка позиции с прогресс-баром
 * Замена скучной таблице
 */

import React, { useMemo } from 'react';
import { Card, Badge, Button, ButtonGroup, Dropdown } from 'react-bootstrap';
import { PositionVisualProgress } from './PositionVisualProgress';
import type { Position } from '../../types';
import './PositionCard.css';

export interface PositionCardProps {
  position: Position;
  onClose?: (positionId: string, percentage?: number) => void;
  onMoveSL?: (positionId: string, toBreakeven: boolean) => void;
  onEdit?: (positionId: string) => void;
  compact?: boolean;
}

export const PositionCard: React.FC<PositionCardProps> = ({
  position,
  onClose,
  onMoveSL,
  compact = false,
}) => {
  // Расчёт метрик
  const metrics = useMemo(() => {
    const currentPrice = position.currentPrice || position.entry;
    const pnlUsd = position.pnlUsd || 0;
    const pnlR = position.pnlR || 0;
    const pnlPercent = ((currentPrice - position.entry) / position.entry) * 100;
    
    // Расстояние до уровней (в %)
    const distanceToSL = position.sl 
      ? ((currentPrice - position.sl) / position.entry) * 100 
      : 0;
    const distanceToTP = position.tp 
      ? ((position.tp - currentPrice) / position.entry) * 100 
      : 0;

    const isProfit = pnlUsd >= 0;
    const isProfitable = pnlR >= 0.5; // 0.5R = частично в прибыли
    
    return {
      currentPrice,
      pnlUsd,
      pnlR,
      pnlPercent,
      distanceToSL,
      distanceToTP,
      isProfit,
      isProfitable,
    };
  }, [position]);

  const sideColor = position.side === 'long' ? 'success' : 'danger';
  const pnlColor = metrics.isProfit ? 'success' : 'danger';

  const handleClosePartial = (percentage: number) => {
    if (onClose) {
      onClose(position.id, percentage);
    }
  };

  const handleCloseFull = () => {
    if (onClose) {
      onClose(position.id, 100);
    }
  };

  const handleMoveToBreakeven = () => {
    if (onMoveSL) {
      onMoveSL(position.id, true);
    }
  };

  if (compact) {
    return (
      <div className="position-card-compact">
        <div className="compact-header">
          <div className="compact-symbol">
            <Badge bg={sideColor} className="me-2">
              {position.side.toUpperCase()}
            </Badge>
            <strong>{position.symbol}</strong>
          </div>
          <div className={`compact-pnl text-${pnlColor}`}>
            {metrics.pnlR.toFixed(2)}R
          </div>
        </div>
        <PositionVisualProgress
          side={position.side}
          sl={position.sl}
          entry={position.entry}
          current={metrics.currentPrice}
          tp={position.tp}
          compact={true}
        />
      </div>
    );
  }

  return (
    <Card className="position-card">
      <Card.Body>
        {/* Header */}
        <div className="position-header">
          <div className="position-title">
            <h5 className="mb-1">
              <Badge bg={sideColor} className="me-2">
                {position.side.toUpperCase()}
              </Badge>
              {position.symbol}
            </h5>
            <div className="position-meta text-muted small">
              Opened {new Date(position.openTime || position.openedAt).toLocaleString('ru-RU', {
                day: '2-digit',
                month: '2-digit',
                hour: '2-digit',
                minute: '2-digit',
              })}
            </div>
          </div>
          <div className="position-pnl">
            <div className={`pnl-value text-${pnlColor}`}>
              {metrics.pnlR >= 0 ? '+' : ''}{metrics.pnlR.toFixed(2)}R
            </div>
            <div className={`pnl-usd text-${pnlColor} small`}>
              {metrics.pnlUsd >= 0 ? '+' : ''}${metrics.pnlUsd.toFixed(2)}
            </div>
            <div className="pnl-percent text-muted small">
              ({metrics.pnlPercent >= 0 ? '+' : ''}{metrics.pnlPercent.toFixed(2)}%)
            </div>
          </div>
        </div>

        {/* Visual Progress */}
        <div className="position-progress-section">
          <PositionVisualProgress
            side={position.side}
            sl={position.sl}
            entry={position.entry}
            current={metrics.currentPrice}
            tp={position.tp}
          />
        </div>

        {/* Price Levels */}
        <div className="position-levels">
          <div className="level-row">
            <span className="level-label text-danger">SL:</span>
            <span className="level-value">${position.sl?.toFixed(2) || 'N/A'}</span>
            <span className="level-distance text-muted small">
              ({metrics.distanceToSL.toFixed(1)}%)
            </span>
          </div>
          <div className="level-row">
            <span className="level-label text-info">Entry:</span>
            <span className="level-value">${position.entry.toFixed(2)}</span>
          </div>
          <div className="level-row">
            <span className="level-label">Current:</span>
            <span className="level-value fw-bold">${metrics.currentPrice.toFixed(2)}</span>
          </div>
          <div className="level-row">
            <span className="level-label text-success">TP:</span>
            <span className="level-value">${position.tp?.toFixed(2) || 'N/A'}</span>
            <span className="level-distance text-muted small">
              ({metrics.distanceToTP.toFixed(1)}%)
            </span>
          </div>
        </div>

        {/* Size & Risk */}
        <div className="position-info">
          <div className="info-item">
            <span className="info-label">Size:</span>
            <span className="info-value">{position.size} {position.symbol.replace('USDT', '')}</span>
          </div>
          <div className="info-item">
            <span className="info-label">Value:</span>
            <span className="info-value">${(position.size * metrics.currentPrice).toFixed(2)}</span>
          </div>
          {position.riskR && (
            <div className="info-item">
              <span className="info-label">Risk:</span>
              <span className="info-value">{position.riskR.toFixed(2)}R</span>
            </div>
          )}
        </div>

        {/* Actions */}
        <div className="position-actions">
          <ButtonGroup className="w-100">
            <Button
              variant="outline-success"
              size="sm"
              onClick={handleMoveToBreakeven}
              disabled={!metrics.isProfitable || !onMoveSL}
              title={metrics.isProfitable ? 'Move SL to breakeven' : 'Not profitable yet'}
            >
              🔒 SL to BE
            </Button>
            
            <Dropdown as={ButtonGroup}>
              <Button
                variant="outline-warning"
                size="sm"
                onClick={() => handleClosePartial(50)}
                disabled={!onClose}
              >
                ✂️ Close 50%
              </Button>
              <Dropdown.Toggle 
                split 
                variant="outline-warning" 
                size="sm"
                disabled={!onClose}
              />
              <Dropdown.Menu>
                <Dropdown.Item onClick={() => handleClosePartial(25)}>
                  Close 25%
                </Dropdown.Item>
                <Dropdown.Item onClick={() => handleClosePartial(75)}>
                  Close 75%
                </Dropdown.Item>
                <Dropdown.Divider />
                <Dropdown.Item onClick={handleCloseFull} className="text-danger">
                  Close 100%
                </Dropdown.Item>
              </Dropdown.Menu>
            </Dropdown>

            <Button
              variant="outline-danger"
              size="sm"
              onClick={handleCloseFull}
              disabled={!onClose}
            >
              ❌ Close All
            </Button>
          </ButtonGroup>
        </div>
      </Card.Body>
    </Card>
  );
};

export default PositionCard;
