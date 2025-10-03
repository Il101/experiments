/**
 * Filter Engine
 * Core filtering logic with AND/OR support
 */

import type {
  Filter,
  FilterGroup,
  FilterCondition,
  FilterResult,
  FilterOperator,
} from '../types/filters';

// ===== OPERATOR EVALUATORS =====
const evaluateCondition = (itemValue: any, operator: FilterOperator, filterValue: any): boolean => {
  // Handle null/undefined
  if (itemValue === null || itemValue === undefined) {
    if (operator === 'is_empty') return true;
    if (operator === 'is_not_empty') return false;
    return false;
  }

  switch (operator) {
    case 'equals':
      return itemValue === filterValue;

    case 'not_equals':
      return itemValue !== filterValue;

    case 'greater_than':
      return Number(itemValue) > Number(filterValue);

    case 'less_than':
      return Number(itemValue) < Number(filterValue);

    case 'greater_than_or_equal':
      return Number(itemValue) >= Number(filterValue);

    case 'less_than_or_equal':
      return Number(itemValue) <= Number(filterValue);

    case 'contains':
      return String(itemValue).toLowerCase().includes(String(filterValue).toLowerCase());

    case 'not_contains':
      return !String(itemValue).toLowerCase().includes(String(filterValue).toLowerCase());

    case 'starts_with':
      return String(itemValue).toLowerCase().startsWith(String(filterValue).toLowerCase());

    case 'ends_with':
      return String(itemValue).toLowerCase().endsWith(String(filterValue).toLowerCase());

    case 'in':
      return Array.isArray(filterValue) && filterValue.includes(itemValue);

    case 'not_in':
      return Array.isArray(filterValue) && !filterValue.includes(itemValue);

    case 'between':
      if (!Array.isArray(filterValue) || filterValue.length !== 2) return false;
      const [min, max] = filterValue;
      const numValue = Number(itemValue);
      return numValue >= Number(min) && numValue <= Number(max);

    case 'is_empty':
      if (Array.isArray(itemValue)) return itemValue.length === 0;
      if (typeof itemValue === 'string') return itemValue.trim() === '';
      return itemValue === null || itemValue === undefined;

    case 'is_not_empty':
      if (Array.isArray(itemValue)) return itemValue.length > 0;
      if (typeof itemValue === 'string') return itemValue.trim() !== '';
      return itemValue !== null && itemValue !== undefined;

    default:
      console.warn(`Unknown operator: ${operator}`);
      return false;
  }
};

// ===== GET NESTED VALUE =====
const getNestedValue = (obj: any, path: string): any => {
  const keys = path.split('.');
  let value = obj;

  for (const key of keys) {
    if (value === null || value === undefined) return undefined;
    value = value[key];
  }

  return value;
};

// ===== EVALUATE CONDITION =====
const evaluateFilterCondition = (item: any, condition: FilterCondition): boolean => {
  const itemValue = getNestedValue(item, condition.field);
  return evaluateCondition(itemValue, condition.operator, condition.value);
};

// ===== EVALUATE GROUP =====
const evaluateFilterGroup = (item: any, group: FilterGroup): boolean => {
  // Evaluate all conditions in this group
  const conditionResults = group.conditions.map((condition) =>
    evaluateFilterCondition(item, condition)
  );

  // Evaluate nested groups recursively
  const groupResults = (group.groups || []).map((nestedGroup) =>
    evaluateFilterGroup(item, nestedGroup)
  );

  // Combine all results
  const allResults = [...conditionResults, ...groupResults];

  if (allResults.length === 0) return true; // Empty group = pass

  // Apply logic (AND/OR)
  if (group.logic === 'AND') {
    return allResults.every((result) => result);
  } else {
    return allResults.some((result) => result);
  }
};

// ===== APPLY FILTER =====
export const applyFilter = <T = any>(
  data: T[],
  filter: Filter
): FilterResult<T> => {
  const startTime = performance.now();

  const filteredData = data.filter((item) =>
    evaluateFilterGroup(item, filter.rootGroup)
  );

  const endTime = performance.now();

  return {
    data: filteredData,
    totalCount: data.length,
    filteredCount: filteredData.length,
    filter,
    executionTimeMs: endTime - startTime,
  };
};

// ===== VALIDATE FILTER =====
export const validateFilter = (filter: Filter): { isValid: boolean; errors: string[] } => {
  const errors: string[] = [];

  const validateGroup = (group: FilterGroup, path: string = 'root') => {
    // Check if group has at least one condition or nested group
    if (group.conditions.length === 0 && (!group.groups || group.groups.length === 0)) {
      errors.push(`${path}: Group must have at least one condition or nested group`);
    }

    // Validate conditions
    group.conditions.forEach((condition, index) => {
      if (!condition.field) {
        errors.push(`${path}.condition[${index}]: Field is required`);
      }
      if (!condition.operator) {
        errors.push(`${path}.condition[${index}]: Operator is required`);
      }
      if (condition.value === undefined || condition.value === null) {
        if (condition.operator !== 'is_empty' && condition.operator !== 'is_not_empty') {
          errors.push(`${path}.condition[${index}]: Value is required for operator ${condition.operator}`);
        }
      }
    });

    // Validate nested groups recursively
    (group.groups || []).forEach((nestedGroup, index) => {
      validateGroup(nestedGroup, `${path}.group[${index}]`);
    });
  };

  validateGroup(filter.rootGroup);

  return {
    isValid: errors.length === 0,
    errors,
  };
};

// ===== COUNT MATCHING ITEMS =====
export const countMatchingItems = <T = any>(data: T[], filter: Filter): number => {
  return data.filter((item) => evaluateFilterGroup(item, filter.rootGroup)).length;
};

// ===== TEST SINGLE ITEM =====
export const testItemAgainstFilter = <T = any>(item: T, filter: Filter): boolean => {
  return evaluateFilterGroup(item, filter.rootGroup);
};

// ===== FILTER STATISTICS =====
export const getFilterStatistics = <T = any>(
  data: T[],
  filter: Filter
): {
  totalCount: number;
  matchingCount: number;
  matchingPercentage: number;
  executionTimeMs: number;
} => {
  const startTime = performance.now();
  const matchingCount = countMatchingItems(data, filter);
  const endTime = performance.now();

  return {
    totalCount: data.length,
    matchingCount,
    matchingPercentage: data.length > 0 ? (matchingCount / data.length) * 100 : 0,
    executionTimeMs: endTime - startTime,
  };
};

// ===== OPTIMIZE FILTER =====
export const optimizeFilter = (filter: Filter): Filter => {
  // Remove empty groups
  const optimizeGroup = (group: FilterGroup): FilterGroup | null => {
    const filteredConditions = group.conditions.filter(
      (condition) => condition.field && condition.operator
    );

    const filteredGroups = (group.groups || [])
      .map(optimizeGroup)
      .filter((g): g is FilterGroup => g !== null);

    // If no conditions and no nested groups, remove this group
    if (filteredConditions.length === 0 && filteredGroups.length === 0) {
      return null;
    }

    return {
      ...group,
      conditions: filteredConditions,
      groups: filteredGroups.length > 0 ? filteredGroups : undefined,
    };
  };

  const optimizedRootGroup = optimizeGroup(filter.rootGroup);

  if (!optimizedRootGroup) {
    // Return empty filter
    return {
      ...filter,
      rootGroup: {
        id: filter.rootGroup.id,
        logic: 'AND',
        conditions: [],
      },
    };
  }

  return {
    ...filter,
    rootGroup: optimizedRootGroup,
  };
};
