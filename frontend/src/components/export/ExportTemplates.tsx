/**
 * Export Templates Component
 * Manages export templates for quick reuse
 */

import React, { useState } from 'react';
import { FileText, Plus, Trash2, Edit2, Copy, Check } from 'lucide-react';
import { useExportStore } from '../../store/useExportStore';
import type { ExportTemplate } from '../../types/export';

export const ExportTemplates: React.FC = () => {
  const { templates, createTemplate, deleteTemplate, openExportDialog } = useExportStore();
  const [_isCreating, setIsCreating] = useState(false);
  
  const customTemplates = templates.filter((t) => !t.isDefault);
  const defaultTemplates = templates.filter((t) => t.isDefault);
  
  const handleUseTemplate = (template: ExportTemplate) => {
    openExportDialog(template.id);
  };
  
  const handleDuplicate = (template: ExportTemplate) => {
    createTemplate({
      name: `${template.name} (Copy)`,
      description: template.description,
      dataType: template.dataType,
      format: template.format,
      fields: [...template.fields],
      includeCharts: template.includeCharts,
      includeStatistics: template.includeStatistics,
      isDefault: false,
    });
  };
  
  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Export Templates</h2>
          <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
            Quick configurations for common export scenarios
          </p>
        </div>
        <button
          onClick={() => setIsCreating(true)}
          className="flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
        >
          <Plus className="h-4 w-4" />
          New Template
        </button>
      </div>
      
      {/* Default Templates */}
      <div className="mb-8">
        <h3 className="mb-3 text-sm font-medium text-gray-700 dark:text-gray-300">
          Built-in Templates
        </h3>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {defaultTemplates.map((template) => (
            <TemplateCard
              key={template.id}
              template={template}
              onUse={() => handleUseTemplate(template)}
              onDuplicate={() => handleDuplicate(template)}
              readOnly
            />
          ))}
        </div>
      </div>
      
      {/* Custom Templates */}
      {customTemplates.length > 0 && (
        <div>
          <h3 className="mb-3 text-sm font-medium text-gray-700 dark:text-gray-300">
            Custom Templates
          </h3>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {customTemplates.map((template) => (
              <TemplateCard
                key={template.id}
                template={template}
                onUse={() => handleUseTemplate(template)}
                onEdit={() => {/* TODO: Open edit dialog */}}
                onDuplicate={() => handleDuplicate(template)}
                onDelete={() => deleteTemplate(template.id)}
              />
            ))}
          </div>
        </div>
      )}
      
      {customTemplates.length === 0 && (
        <div className="rounded-lg border-2 border-dashed border-gray-300 p-8 text-center dark:border-gray-700">
          <FileText className="mx-auto h-12 w-12 text-gray-400" />
          <h3 className="mt-2 text-sm font-medium text-gray-900 dark:text-white">
            No custom templates yet
          </h3>
          <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
            Create a template to save your export configurations
          </p>
          <button
            onClick={() => setIsCreating(true)}
            className="mt-4 inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
          >
            <Plus className="h-4 w-4" />
            Create Template
          </button>
        </div>
      )}
    </div>
  );
};

interface TemplateCardProps {
  template: ExportTemplate;
  onUse: () => void;
  onEdit?: () => void;
  onDuplicate?: () => void;
  onDelete?: () => void;
  readOnly?: boolean;
}

const TemplateCard: React.FC<TemplateCardProps> = ({
  template,
  onUse,
  onEdit,
  onDuplicate,
  onDelete,
  readOnly,
}) => {
  const formatBadgeColor = {
    csv: 'bg-green-50 text-green-700 dark:bg-green-900/20 dark:text-green-400',
    json: 'bg-purple-50 text-purple-700 dark:bg-purple-900/20 dark:text-purple-400',
    excel: 'bg-blue-50 text-blue-700 dark:bg-blue-900/20 dark:text-blue-400',
    pdf: 'bg-red-50 text-red-700 dark:bg-red-900/20 dark:text-red-400',
  };
  
  return (
    <div className="group relative rounded-lg border border-gray-200 bg-white p-4 transition-shadow hover:shadow-md dark:border-gray-700 dark:bg-gray-900">
      <div className="mb-3 flex items-start justify-between">
        <div className="flex items-center gap-2">
          <FileText className="h-5 w-5 text-gray-400" />
          <span className={`rounded-full px-2 py-1 text-xs font-medium ${formatBadgeColor[template.format]}`}>
            {template.format.toUpperCase()}
          </span>
        </div>
        {template.isDefault && (
          <span className="rounded-full bg-gray-100 px-2 py-1 text-xs font-medium text-gray-600 dark:bg-gray-800 dark:text-gray-400">
            Built-in
          </span>
        )}
      </div>
      
      <h4 className="mb-1 font-medium text-gray-900 dark:text-white">{template.name}</h4>
      <p className="mb-3 text-sm text-gray-600 dark:text-gray-400">{template.description}</p>
      
      <div className="mb-3 flex flex-wrap gap-1">
        {template.includeCharts && (
          <span className="rounded-full bg-blue-50 px-2 py-1 text-xs text-blue-700 dark:bg-blue-900/20 dark:text-blue-400">
            Charts
          </span>
        )}
        {template.includeStatistics && (
          <span className="rounded-full bg-purple-50 px-2 py-1 text-xs text-purple-700 dark:bg-purple-900/20 dark:text-purple-400">
            Stats
          </span>
        )}
        <span className="rounded-full bg-gray-100 px-2 py-1 text-xs text-gray-700 dark:bg-gray-800 dark:text-gray-400">
          {template.fields.length} fields
        </span>
      </div>
      
      <div className="flex items-center gap-2">
        <button
          onClick={onUse}
          className="flex-1 rounded-lg bg-blue-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-blue-700"
        >
          <Check className="mx-auto h-4 w-4" />
        </button>
        
        {!readOnly && onEdit && (
          <button
            onClick={onEdit}
            className="rounded-lg border border-gray-300 p-1.5 text-gray-600 hover:bg-gray-50 dark:border-gray-600 dark:text-gray-400 dark:hover:bg-gray-800"
          >
            <Edit2 className="h-4 w-4" />
          </button>
        )}
        
        {onDuplicate && (
          <button
            onClick={onDuplicate}
            className="rounded-lg border border-gray-300 p-1.5 text-gray-600 hover:bg-gray-50 dark:border-gray-600 dark:text-gray-400 dark:hover:bg-gray-800"
          >
            <Copy className="h-4 w-4" />
          </button>
        )}
        
        {!readOnly && onDelete && (
          <button
            onClick={onDelete}
            className="rounded-lg border border-red-300 p-1.5 text-red-600 hover:bg-red-50 dark:border-red-600 dark:text-red-400 dark:hover:bg-red-900/20"
          >
            <Trash2 className="h-4 w-4" />
          </button>
        )}
      </div>
    </div>
  );
};
