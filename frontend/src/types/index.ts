/**
 * Основные типы приложения
 */

export * from './api';

// Re-export specific types for easier imports
export type { OrderEvent, PositionEvent, WebSocketMessage } from './api';

// ===== UI TYPES =====
export interface Theme {
  mode: 'light' | 'dark';
  primary: string;
  secondary: string;
  success: string;
  warning: string;
  error: string;
}

export interface TableColumn<T = any> {
  key: keyof T | string;
  title: string;
  render?: (value: any, item: T) => React.ReactNode;
  sortable?: boolean;
  width?: string | number;
}

export interface TableProps<T = any> {
  data: T[];
  columns: TableColumn<T>[];
  loading?: boolean;
  emptyMessage?: string;
  onRowClick?: (item: T) => void;
  className?: string;
}

// ===== FORM TYPES =====
export interface FormField {
  name: string;
  label: string;
  type: 'text' | 'number' | 'select' | 'checkbox' | 'textarea';
  required?: boolean;
  placeholder?: string;
  options?: { value: string; label: string }[];
  validation?: any;
}

// ===== CHART TYPES =====
export interface ChartDataPoint {
  x: string | number;
  y: number;
  [key: string]: any;
}

export interface ChartConfig {
  width?: number;
  height?: number;
  margin?: {
    top: number;
    right: number;
    bottom: number;
    left: number;
  };
  colors?: string[];
}

// ===== NOTIFICATION TYPES =====
export interface AppNotification {
  id: string;
  type: 'success' | 'error' | 'warning' | 'info';
  title: string;
  message: string;
  duration?: number;
  timestamp: number;
}

// ===== FILTER TYPES =====
export interface FilterOption {
  value: string;
  label: string;
  count?: number;
}

export interface FilterConfig {
  key: string;
  label: string;
  type: 'select' | 'multiselect' | 'date' | 'number';
  options?: FilterOption[];
  placeholder?: string;
}

// ===== PAGINATION TYPES =====
export interface Pagination {
  page: number;
  limit: number;
  total: number;
  totalPages: number;
}

export interface PaginatedResponse<T> {
  data: T[];
  pagination: Pagination;
}

// ===== SORT TYPES =====
export interface SortConfig {
  field: string;
  direction: 'asc' | 'desc';
}

// ===== SEARCH TYPES =====
export interface SearchConfig {
  query: string;
  fields: string[];
  filters?: Record<string, any>;
  sort?: SortConfig;
  pagination?: Pagination;
}
