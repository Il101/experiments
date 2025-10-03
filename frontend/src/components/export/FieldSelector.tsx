/**
 * Field Selector Component
 * Allows selection of specific fields to include in export
 */

import React from 'react';
import { Check } from 'lucide-react';

interface Field {
  key: string;
  label: string;
}

interface FieldSelectorProps {
  fields: Field[];
  selectedFields: string[];
  onChange: (selectedFields: string[]) => void;
}

export const FieldSelector: React.FC<FieldSelectorProps> = ({
  fields,
  selectedFields,
  onChange,
}) => {
  const allSelected = selectedFields.length === fields.length;
  const noneSelected = selectedFields.length === 0;
  
  const handleToggleAll = () => {
    if (allSelected) {
      onChange([]);
    } else {
      onChange(fields.map((f) => f.key));
    }
  };
  
  const handleToggle = (key: string) => {
    if (selectedFields.includes(key)) {
      onChange(selectedFields.filter((k) => k !== key));
    } else {
      onChange([...selectedFields, key]);
    }
  };
  
  return (
    <div>
      <div className="mb-2 flex items-center justify-between">
        <label className="text-sm font-medium text-gray-700 dark:text-gray-300">
          Fields to Export {noneSelected && <span className="text-gray-500">(All fields)</span>}
        </label>
        <button
          onClick={handleToggleAll}
          className="text-sm font-medium text-blue-600 hover:text-blue-700 dark:text-blue-400"
        >
          {allSelected ? 'Deselect All' : 'Select All'}
        </button>
      </div>
      
      <div className="max-h-48 space-y-1 overflow-y-auto rounded-lg border border-gray-200 bg-gray-50 p-3 dark:border-gray-700 dark:bg-gray-800">
        {fields.map((field) => {
          const isSelected = selectedFields.includes(field.key);
          
          return (
            <label
              key={field.key}
              className="flex cursor-pointer items-center gap-3 rounded-lg px-3 py-2 hover:bg-white dark:hover:bg-gray-700"
            >
              <div
                className={`flex h-5 w-5 items-center justify-center rounded border-2 transition-colors ${
                  isSelected
                    ? 'border-blue-600 bg-blue-600'
                    : 'border-gray-300 bg-white dark:border-gray-600 dark:bg-gray-800'
                }`}
              >
                {isSelected && <Check className="h-3 w-3 text-white" />}
              </div>
              <input
                type="checkbox"
                checked={isSelected}
                onChange={() => handleToggle(field.key)}
                className="sr-only"
              />
              <span className="text-sm text-gray-700 dark:text-gray-300">{field.label}</span>
            </label>
          );
        })}
      </div>
    </div>
  );
};
