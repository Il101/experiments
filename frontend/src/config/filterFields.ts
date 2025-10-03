/**
 * Filter Field Definitions
 * Defines available fields for filtering across different contexts
 */

import type { FilterContext } from '../types/filters';

// ===== FILTER FIELD TYPES =====
export type FilterFieldType = 'string' | 'number' | 'date' | 'boolean' | 'enum';

export type FilterOperator =
  | 'equals'
  | 'not_equals'
  | 'greater_than'
  | 'less_than'
  | 'greater_than_or_equal'
  | 'less_than_or_equal'
  | 'contains'
  | 'not_contains'
  | 'starts_with'
  | 'ends_with'
  | 'in'
  | 'not_in'
  | 'between'
  | 'is_empty'
  | 'is_not_empty';

export interface FilterFieldDefinition {
  key: string;
  label: string;
  type: FilterFieldType;
  operators: FilterOperator[];
  options?: Array<{ value: any; label: string }>; // For enum types
  placeholder?: string;
  min?: number;
  max?: number;
  step?: number;
}

// ===== POSITION FILTER FIELDS =====
export const POSITION_FILTER_FIELDS: FilterFieldDefinition[] = [
  {
    key: 'symbol',
    label: 'Symbol',
    type: 'string',
    operators: ['equals', 'not_equals', 'contains', 'not_contains', 'starts_with', 'ends_with'],
    placeholder: 'e.g. BTCUSDT',
  },
  {
    key: 'side',
    label: 'Side',
    type: 'enum',
    operators: ['equals', 'not_equals', 'in', 'not_in'],
    options: [
      { value: 'long', label: 'Long' },
      { value: 'short', label: 'Short' },
    ],
  },
  {
    key: 'size',
    label: 'Size',
    type: 'number',
    operators: ['equals', 'not_equals', 'greater_than', 'less_than', 'greater_than_or_equal', 'less_than_or_equal', 'between'],
    placeholder: '0.00',
    min: 0,
    step: 0.01,
  },
  {
    key: 'entry',
    label: 'Entry Price',
    type: 'number',
    operators: ['equals', 'not_equals', 'greater_than', 'less_than', 'greater_than_or_equal', 'less_than_or_equal', 'between'],
    placeholder: '0.00',
    min: 0,
    step: 0.01,
  },
  {
    key: 'currentPrice',
    label: 'Current Price',
    type: 'number',
    operators: ['greater_than', 'less_than', 'greater_than_or_equal', 'less_than_or_equal', 'between'],
    placeholder: '0.00',
    min: 0,
    step: 0.01,
  },
  {
    key: 'unrealizedPnlUsd',
    label: 'Unrealized P&L (USD)',
    type: 'number',
    operators: ['equals', 'not_equals', 'greater_than', 'less_than', 'greater_than_or_equal', 'less_than_or_equal', 'between'],
    placeholder: '0.00',
    step: 1,
  },
  {
    key: 'unrealizedPnlR',
    label: 'Unrealized P&L (R)',
    type: 'number',
    operators: ['equals', 'not_equals', 'greater_than', 'less_than', 'greater_than_or_equal', 'less_than_or_equal', 'between'],
    placeholder: '0.00',
    step: 0.1,
  },
  {
    key: 'riskR',
    label: 'Risk (R)',
    type: 'number',
    operators: ['equals', 'not_equals', 'greater_than', 'less_than', 'greater_than_or_equal', 'less_than_or_equal', 'between'],
    placeholder: '0.00',
    min: 0,
    step: 0.1,
  },
  {
    key: 'openedAt',
    label: 'Opened At',
    type: 'date',
    operators: ['equals', 'not_equals', 'greater_than', 'less_than', 'greater_than_or_equal', 'less_than_or_equal', 'between'],
  },
  {
    key: 'mode',
    label: 'Mode',
    type: 'string',
    operators: ['equals', 'not_equals', 'contains'],
    placeholder: 'e.g. breakout',
  },
];

// ===== ORDER FILTER FIELDS =====
export const ORDER_FILTER_FIELDS: FilterFieldDefinition[] = [
  {
    key: 'symbol',
    label: 'Symbol',
    type: 'string',
    operators: ['equals', 'not_equals', 'contains', 'not_contains', 'starts_with', 'ends_with'],
    placeholder: 'e.g. BTCUSDT',
  },
  {
    key: 'side',
    label: 'Side',
    type: 'enum',
    operators: ['equals', 'not_equals', 'in', 'not_in'],
    options: [
      { value: 'buy', label: 'Buy' },
      { value: 'sell', label: 'Sell' },
    ],
  },
  {
    key: 'type',
    label: 'Type',
    type: 'enum',
    operators: ['equals', 'not_equals', 'in', 'not_in'],
    options: [
      { value: 'market', label: 'Market' },
      { value: 'limit', label: 'Limit' },
      { value: 'stop', label: 'Stop' },
      { value: 'stop_limit', label: 'Stop Limit' },
    ],
  },
  {
    key: 'status',
    label: 'Status',
    type: 'enum',
    operators: ['equals', 'not_equals', 'in', 'not_in'],
    options: [
      { value: 'pending', label: 'Pending' },
      { value: 'open', label: 'Open' },
      { value: 'filled', label: 'Filled' },
      { value: 'cancelled', label: 'Cancelled' },
      { value: 'rejected', label: 'Rejected' },
    ],
  },
  {
    key: 'qty',
    label: 'Quantity',
    type: 'number',
    operators: ['equals', 'not_equals', 'greater_than', 'less_than', 'greater_than_or_equal', 'less_than_or_equal', 'between'],
    placeholder: '0.00',
    min: 0,
    step: 0.01,
  },
  {
    key: 'price',
    label: 'Price',
    type: 'number',
    operators: ['equals', 'not_equals', 'greater_than', 'less_than', 'greater_than_or_equal', 'less_than_or_equal', 'between'],
    placeholder: '0.00',
    min: 0,
    step: 0.01,
  },
  {
    key: 'createdAt',
    label: 'Created At',
    type: 'date',
    operators: ['equals', 'not_equals', 'greater_than', 'less_than', 'greater_than_or_equal', 'less_than_or_equal', 'between'],
  },
];

// ===== SIGNAL FILTER FIELDS =====
export const SIGNAL_FILTER_FIELDS: FilterFieldDefinition[] = [
  {
    key: 'symbol',
    label: 'Symbol',
    type: 'string',
    operators: ['equals', 'not_equals', 'contains', 'not_contains', 'starts_with', 'ends_with'],
    placeholder: 'e.g. BTCUSDT',
  },
  {
    key: 'direction',
    label: 'Direction',
    type: 'enum',
    operators: ['equals', 'not_equals'],
    options: [
      { value: 'long', label: 'Long' },
      { value: 'short', label: 'Short' },
    ],
  },
  {
    key: 'confidence',
    label: 'Confidence',
    type: 'number',
    operators: ['greater_than', 'less_than', 'greater_than_or_equal', 'less_than_or_equal', 'between'],
    placeholder: '0-100',
    min: 0,
    max: 100,
    step: 1,
  },
  {
    key: 'timestamp',
    label: 'Timestamp',
    type: 'date',
    operators: ['equals', 'not_equals', 'greater_than', 'less_than', 'greater_than_or_equal', 'less_than_or_equal', 'between'],
  },
];

// ===== CANDIDATE FILTER FIELDS =====
export const CANDIDATE_FILTER_FIELDS: FilterFieldDefinition[] = [
  {
    key: 'symbol',
    label: 'Symbol',
    type: 'string',
    operators: ['equals', 'not_equals', 'contains', 'not_contains', 'starts_with', 'ends_with'],
    placeholder: 'e.g. BTCUSDT',
  },
  {
    key: 'score',
    label: 'Score',
    type: 'number',
    operators: ['equals', 'not_equals', 'greater_than', 'less_than', 'greater_than_or_equal', 'less_than_or_equal', 'between'],
    placeholder: '0-100',
    min: 0,
    max: 100,
    step: 1,
  },
  {
    key: 'filters.liquidity',
    label: 'Liquidity Filter',
    type: 'boolean',
    operators: ['equals'],
  },
  {
    key: 'filters.volatility',
    label: 'Volatility Filter',
    type: 'boolean',
    operators: ['equals'],
  },
  {
    key: 'filters.volume_surge',
    label: 'Volume Surge Filter',
    type: 'boolean',
    operators: ['equals'],
  },
  {
    key: 'metrics.vol_surge_1h',
    label: 'Volume Surge 1h',
    type: 'number',
    operators: ['greater_than', 'less_than', 'greater_than_or_equal', 'less_than_or_equal', 'between'],
    placeholder: '0.00',
    min: 0,
    step: 0.1,
  },
  {
    key: 'metrics.atr15m_pct',
    label: 'ATR 15m %',
    type: 'number',
    operators: ['greater_than', 'less_than', 'greater_than_or_equal', 'less_than_or_equal', 'between'],
    placeholder: '0.00',
    min: 0,
    step: 0.1,
  },
];

// ===== FIELD MAP BY CONTEXT =====
export const FILTER_FIELDS_BY_CONTEXT: Record<FilterContext, FilterFieldDefinition[]> = {
  positions: POSITION_FILTER_FIELDS,
  orders: ORDER_FILTER_FIELDS,
  signals: SIGNAL_FILTER_FIELDS,
  candidates: CANDIDATE_FILTER_FIELDS,
  logs: [], // TODO: Define log filter fields
};

// ===== OPERATOR LABELS =====
export const OPERATOR_LABELS: Record<string, string> = {
  equals: 'equals',
  not_equals: 'does not equal',
  greater_than: 'greater than',
  less_than: 'less than',
  greater_than_or_equal: 'greater than or equal to',
  less_than_or_equal: 'less than or equal to',
  contains: 'contains',
  not_contains: 'does not contain',
  starts_with: 'starts with',
  ends_with: 'ends with',
  in: 'is one of',
  not_in: 'is not one of',
  between: 'is between',
  is_empty: 'is empty',
  is_not_empty: 'is not empty',
};

// ===== OPERATOR SYMBOLS =====
export const OPERATOR_SYMBOLS: Record<string, string> = {
  equals: '=',
  not_equals: '≠',
  greater_than: '>',
  less_than: '<',
  greater_than_or_equal: '≥',
  less_than_or_equal: '≤',
  contains: '⊇',
  not_contains: '⊉',
  in: '∈',
  not_in: '∉',
  between: '↔',
};
