/**
 * Filter System Type Definitions
 * Comprehensive filtering with AND/OR logic
 */

// ===== FILTER OPERATORS =====
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

// ===== FILTER FIELD TYPES =====
export type FilterFieldType = 'string' | 'number' | 'date' | 'boolean' | 'enum';

// ===== FILTER CONDITION =====
export interface FilterCondition {
  id: string;
  field: string;
  operator: FilterOperator;
  value: any;
  fieldType: FilterFieldType;
}

// ===== FILTER GROUP =====
export type FilterLogic = 'AND' | 'OR';

export interface FilterGroup {
  id: string;
  logic: FilterLogic;
  conditions: FilterCondition[];
  groups?: FilterGroup[]; // Nested groups for complex filters
}

// ===== FILTER DEFINITION =====
export interface Filter {
  id: string;
  name: string;
  description?: string;
  rootGroup: FilterGroup;
  createdAt: string;
  updatedAt: string;
  isQuickFilter?: boolean; // Quick filters appear in toolbar
  isPinned?: boolean; // Pinned filters appear at top
}

// ===== FILTER PRESET =====
export interface FilterPreset {
  id: string;
  name: string;
  description?: string;
  icon?: string;
  filter: Filter;
  category?: string;
  isDefault?: boolean;
  usageCount?: number;
  lastUsedAt?: string;
}

// ===== FILTER FIELD DEFINITION =====
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

// ===== FILTER CONTEXT =====
export type FilterContext = 'positions' | 'orders' | 'signals' | 'candidates' | 'logs';

// ===== FILTER HISTORY =====
export interface FilterHistory {
  id: string;
  filter: Filter;
  appliedAt: string;
  resultsCount: number;
  context: FilterContext;
}

// ===== FILTER STATS =====
export interface FilterStats {
  totalFilters: number;
  totalPresets: number;
  quickFilters: number;
  pinnedFilters: number;
  totalApplications: number;
  averageResultsCount: number;
  mostUsedFilter?: FilterPreset;
}

// ===== FILTER RESULT =====
export interface FilterResult<T = any> {
  data: T[];
  totalCount: number;
  filteredCount: number;
  filter: Filter;
  executionTimeMs: number;
}

// ===== EXPORT/IMPORT =====
export interface FilterExport {
  version: string;
  exportedAt: string;
  filters: Filter[];
  presets: FilterPreset[];
}

// ===== VALIDATION =====
export interface FilterValidation {
  isValid: boolean;
  errors: Array<{
    field: string;
    message: string;
  }>;
  warnings: Array<{
    field: string;
    message: string;
  }>;
}
