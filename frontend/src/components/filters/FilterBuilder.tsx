/**
 * Filter Builder Component
 * Visual builder for creating complex filters with AND/OR logic
 */

import React, { useState } from 'react';
import { Plus, X, Trash2, Save } from 'lucide-react';
import type {
  Filter,
  FilterGroup,
  FilterCondition,
  FilterContext,
} from '../../types/filters';
import type { FilterFieldDefinition } from '../../config/filterFields';
import { FILTER_FIELDS_BY_CONTEXT, OPERATOR_LABELS } from '../../config/filterFields';
import { useFilterStore } from '../../store/useFilterStore';

interface FilterBuilderProps {
  context: FilterContext;
  initialFilter?: Filter;
  onSave?: (filter: Filter) => void;
  onCancel?: () => void;
}

const generateId = () => `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;

// ===== CONDITION EDITOR =====
interface ConditionEditorProps {
  condition: FilterCondition;
  fields: FilterFieldDefinition[];
  onChange: (condition: FilterCondition) => void;
  onRemove: () => void;
}

const ConditionEditor: React.FC<ConditionEditorProps> = ({
  condition,
  fields,
  onChange,
  onRemove,
}) => {
  const fieldDef = fields.find((f) => f.key === condition.field);
  const operators = fieldDef?.operators || [];

  const handleFieldChange = (newField: string) => {
    const newFieldDef = fields.find((f) => f.key === newField);
    onChange({
      ...condition,
      field: newField,
      fieldType: newFieldDef?.type || 'string',
      operator: newFieldDef?.operators[0] || 'equals',
      value: undefined,
    });
  };

  const renderValueInput = () => {
    if (!fieldDef) return null;

    // Boolean type
    if (fieldDef.type === 'boolean') {
      return (
        <select
          value={condition.value?.toString() || 'true'}
          onChange={(e) => onChange({ ...condition, value: e.target.value === 'true' })}
          className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100"
        >
          <option value="true">True</option>
          <option value="false">False</option>
        </select>
      );
    }

    // Enum type
    if (fieldDef.type === 'enum' && fieldDef.options) {
      if (condition.operator === 'in' || condition.operator === 'not_in') {
        // Multi-select for 'in' operators
        return (
          <select
            multiple
            value={condition.value || []}
            onChange={(e) => {
              const selected = Array.from(e.target.selectedOptions).map((o) => o.value);
              onChange({ ...condition, value: selected });
            }}
            className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 min-h-[80px]"
          >
            {fieldDef.options.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        );
      } else {
        // Single select
        return (
          <select
            value={condition.value || ''}
            onChange={(e) => onChange({ ...condition, value: e.target.value })}
            className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100"
          >
            <option value="">Select...</option>
            {fieldDef.options.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        );
      }
    }

    // Between operator (two inputs)
    if (condition.operator === 'between') {
      const [min, max] = condition.value || [0, 0];
      return (
        <div className="flex items-center gap-2">
          <input
            type={fieldDef.type === 'date' ? 'date' : 'number'}
            value={min || ''}
            onChange={(e) => onChange({ ...condition, value: [Number(e.target.value) || 0, max] })}
            placeholder="Min"
            className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 w-24"
            step={fieldDef.step}
          />
          <span className="text-gray-500">to</span>
          <input
            type={fieldDef.type === 'date' ? 'date' : 'number'}
            value={max || ''}
            onChange={(e) => onChange({ ...condition, value: [min, Number(e.target.value) || 0] })}
            placeholder="Max"
            className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 w-24"
            step={fieldDef.step}
          />
        </div>
      );
    }

    // Empty operators (no value needed)
    if (condition.operator === 'is_empty' || condition.operator === 'is_not_empty') {
      return null;
    }

    // Default input based on type
    if (fieldDef.type === 'number') {
      return (
        <input
          type="number"
          value={condition.value || ''}
          onChange={(e) => onChange({ ...condition, value: Number(e.target.value) || 0 })}
          placeholder={fieldDef.placeholder}
          className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100"
          min={fieldDef.min}
          max={fieldDef.max}
          step={fieldDef.step}
        />
      );
    }

    if (fieldDef.type === 'date') {
      return (
        <input
          type="date"
          value={condition.value || ''}
          onChange={(e) => onChange({ ...condition, value: e.target.value })}
          className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100"
        />
      );
    }

    // String type (default)
    return (
      <input
        type="text"
        value={condition.value || ''}
        onChange={(e) => onChange({ ...condition, value: e.target.value })}
        placeholder={fieldDef.placeholder || 'Enter value...'}
        className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100"
      />
    );
  };

  return (
    <div className="flex items-start gap-2 p-3 bg-gray-50 dark:bg-gray-800/50 rounded-lg border border-gray-200 dark:border-gray-700">
      {/* Field Selector */}
      <select
        value={condition.field}
        onChange={(e) => handleFieldChange(e.target.value)}
        className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 min-w-[150px]"
      >
        <option value="">Select field...</option>
        {fields.map((field) => (
          <option key={field.key} value={field.key}>
            {field.label}
          </option>
        ))}
      </select>

      {/* Operator Selector */}
      {condition.field && (
        <select
          value={condition.operator}
          onChange={(e) => onChange({ ...condition, operator: e.target.value as any })}
          className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 min-w-[150px]"
        >
          {operators.map((op) => (
            <option key={op} value={op}>
              {OPERATOR_LABELS[op] || op}
            </option>
          ))}
        </select>
      )}

      {/* Value Input */}
      {condition.field && renderValueInput()}

      {/* Remove Button */}
      <button
        onClick={onRemove}
        className="p-2 text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg transition-colors"
        title="Remove condition"
      >
        <X className="w-4 h-4" />
      </button>
    </div>
  );
};

// ===== GROUP EDITOR =====
interface GroupEditorProps {
  group: FilterGroup;
  fields: FilterFieldDefinition[];
  onChange: (group: FilterGroup) => void;
  onRemove?: () => void;
  level?: number;
}

const GroupEditor: React.FC<GroupEditorProps> = ({
  group,
  fields,
  onChange,
  onRemove,
  level = 0,
}) => {
  const addCondition = () => {
    const newCondition: FilterCondition = {
      id: generateId(),
      field: '',
      operator: 'equals',
      value: undefined,
      fieldType: 'string',
    };

    onChange({
      ...group,
      conditions: [...group.conditions, newCondition],
    });
  };

  const updateCondition = (index: number, condition: FilterCondition) => {
    const updated = [...group.conditions];
    updated[index] = condition;
    onChange({ ...group, conditions: updated });
  };

  const removeCondition = (index: number) => {
    onChange({
      ...group,
      conditions: group.conditions.filter((_, i) => i !== index),
    });
  };

  const addGroup = () => {
    const newGroup: FilterGroup = {
      id: generateId(),
      logic: 'AND',
      conditions: [],
    };

    onChange({
      ...group,
      groups: [...(group.groups || []), newGroup],
    });
  };

  const updateNestedGroup = (index: number, nestedGroup: FilterGroup) => {
    const updated = [...(group.groups || [])];
    updated[index] = nestedGroup;
    onChange({ ...group, groups: updated });
  };

  const removeNestedGroup = (index: number) => {
    onChange({
      ...group,
      groups: (group.groups || []).filter((_, i) => i !== index),
    });
  };

  const toggleLogic = () => {
    onChange({ ...group, logic: group.logic === 'AND' ? 'OR' : 'AND' });
  };

  return (
    <div
      className={`
        p-4 rounded-lg border-2
        ${level === 0 ? 'border-blue-300 dark:border-blue-700 bg-blue-50/50 dark:bg-blue-900/10' : 'border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900'}
      `}
      style={{ marginLeft: level > 0 ? '20px' : '0' }}
    >
      {/* Group Header */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <button
            onClick={toggleLogic}
            className={`
              px-3 py-1 rounded-lg font-medium text-sm transition-colors
              ${group.logic === 'AND' ? 'bg-blue-500 text-white' : 'bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300'}
            `}
          >
            {group.logic}
          </button>
          <span className="text-xs text-gray-500 dark:text-gray-400">
            Match {group.logic === 'AND' ? 'all' : 'any'} conditions
          </span>
        </div>

        {level > 0 && onRemove && (
          <button
            onClick={onRemove}
            className="p-1.5 text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg transition-colors"
            title="Remove group"
          >
            <Trash2 className="w-4 h-4" />
          </button>
        )}
      </div>

      {/* Conditions */}
      <div className="space-y-2 mb-3">
        {group.conditions.map((condition, index) => (
          <ConditionEditor
            key={condition.id}
            condition={condition}
            fields={fields}
            onChange={(updated) => updateCondition(index, updated)}
            onRemove={() => removeCondition(index)}
          />
        ))}
      </div>

      {/* Nested Groups */}
      {(group.groups || []).map((nestedGroup, index) => (
        <GroupEditor
          key={nestedGroup.id}
          group={nestedGroup}
          fields={fields}
          onChange={(updated) => updateNestedGroup(index, updated)}
          onRemove={() => removeNestedGroup(index)}
          level={level + 1}
        />
      ))}

      {/* Add Buttons */}
      <div className="flex gap-2 mt-3">
        <button
          onClick={addCondition}
          className="flex items-center gap-1.5 px-3 py-1.5 text-sm bg-blue-500 hover:bg-blue-600 text-white rounded-lg transition-colors"
        >
          <Plus className="w-4 h-4" />
          Add Condition
        </button>

        {level < 2 && (
          <button
            onClick={addGroup}
            className="flex items-center gap-1.5 px-3 py-1.5 text-sm bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 dark:hover:bg-gray-600 text-gray-700 dark:text-gray-300 rounded-lg transition-colors"
          >
            <Plus className="w-4 h-4" />
            Add Group
          </button>
        )}
      </div>
    </div>
  );
};

// ===== MAIN FILTER BUILDER =====
export const FilterBuilder: React.FC<FilterBuilderProps> = ({
  context,
  initialFilter,
  onSave,
  onCancel,
}) => {
  const { createFilter, updateFilter } = useFilterStore();
  const fields = FILTER_FIELDS_BY_CONTEXT[context];

  const [filter, setFilter] = useState<Filter>(
    initialFilter || {
      id: generateId(),
      name: 'New Filter',
      rootGroup: {
        id: generateId(),
        logic: 'AND',
        conditions: [],
      },
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    }
  );

  const handleSave = () => {
    if (initialFilter) {
      updateFilter(filter.id, filter);
    } else {
      createFilter(filter.name, filter.description);
    }

    onSave?.(filter);
  };

  return (
    <div className="space-y-4">
      {/* Filter Name */}
      <div>
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
          Filter Name
        </label>
        <input
          type="text"
          value={filter.name}
          onChange={(e) => setFilter({ ...filter, name: e.target.value })}
          placeholder="My Filter"
          className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100"
        />
      </div>

      {/* Filter Description */}
      <div>
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
          Description (optional)
        </label>
        <textarea
          value={filter.description || ''}
          onChange={(e) => setFilter({ ...filter, description: e.target.value })}
          placeholder="Describe what this filter does..."
          rows={2}
          className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100"
        />
      </div>

      {/* Filter Builder */}
      <GroupEditor
        group={filter.rootGroup}
        fields={fields}
        onChange={(rootGroup) =>
          setFilter({ ...filter, rootGroup, updatedAt: new Date().toISOString() })
        }
      />

      {/* Actions */}
      <div className="flex items-center justify-between pt-4 border-t border-gray-200 dark:border-gray-700">
        <div className="flex gap-2">
          <button
            onClick={handleSave}
            className="flex items-center gap-1.5 px-4 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded-lg transition-colors"
          >
            <Save className="w-4 h-4" />
            Save Filter
          </button>

          {onCancel && (
            <button
              onClick={onCancel}
              className="px-4 py-2 bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 dark:hover:bg-gray-600 text-gray-700 dark:text-gray-300 rounded-lg transition-colors"
            >
              Cancel
            </button>
          )}
        </div>

        <button
          onClick={() => {
            /* TODO: Preview results */
          }}
          className="px-4 py-2 bg-green-500 hover:bg-green-600 text-white rounded-lg transition-colors"
        >
          Preview Results
        </button>
      </div>
    </div>
  );
};
