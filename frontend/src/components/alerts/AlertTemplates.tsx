/**
 * AlertTemplates Component
 * Gallery of pre-built alert templates
 */

import React, { useState } from 'react';
import { Check, Search } from 'lucide-react';
import { useAlertStore } from '../../store/useAlertStore';
import type { AlertTemplate } from '../../types/alerts';

// ==================== Component ====================

export const AlertTemplates: React.FC = () => {
  const { templates, applyTemplate, closeAlertBuilder } = useAlertStore();
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<string>('all');

  const categories = [
    { id: 'all', label: 'All Templates', count: templates.length },
    {
      id: 'profit',
      label: 'Profit',
      count: templates.filter((t) => t.category === 'profit').length,
    },
    {
      id: 'loss',
      label: 'Loss',
      count: templates.filter((t) => t.category === 'loss').length,
    },
    {
      id: 'risk',
      label: 'Risk',
      count: templates.filter((t) => t.category === 'risk').length,
    },
    {
      id: 'performance',
      label: 'Performance',
      count: templates.filter((t) => t.category === 'performance').length,
    },
  ];

  const filteredTemplates = templates.filter((template) => {
    const matchesSearch =
      searchQuery === '' ||
      template.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      template.description.toLowerCase().includes(searchQuery.toLowerCase());

    const matchesCategory =
      selectedCategory === 'all' || template.category === selectedCategory;

    return matchesSearch && matchesCategory;
  });

  const handleApplyTemplate = async (templateId: string) => {
    try {
      await applyTemplate(templateId);
      closeAlertBuilder();
    } catch (error) {
      console.error('Failed to apply template:', error);
    }
  };

  const getCategoryColor = (category: AlertTemplate['category']) => {
    switch (category) {
      case 'profit':
        return 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300';
      case 'loss':
        return 'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300';
      case 'risk':
        return 'bg-orange-100 dark:bg-orange-900/30 text-orange-700 dark:text-orange-300';
      case 'performance':
        return 'bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300';
      case 'time':
        return 'bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-300';
      default:
        return 'bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300';
    }
  };

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="p-6 border-b border-gray-200 dark:border-gray-700">
        <h2 className="text-xl font-bold text-gray-900 dark:text-gray-100 mb-2">
          Alert Templates
        </h2>
        <p className="text-sm text-gray-600 dark:text-gray-400">
          Start with a pre-built template and customize it to your needs
        </p>
      </div>

      {/* Search */}
      <div className="p-6 border-b border-gray-200 dark:border-gray-700">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search templates..."
            className="w-full pl-10 pr-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
        </div>
      </div>

      {/* Categories */}
      <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700 overflow-x-auto">
        <div className="flex gap-2">
          {categories.map((category) => (
            <button
              key={category.id}
              onClick={() => setSelectedCategory(category.id)}
              className={`px-4 py-2 rounded-lg text-sm font-medium whitespace-nowrap transition-colors ${
                selectedCategory === category.id
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-700'
              }`}
            >
              {category.label} ({category.count})
            </button>
          ))}
        </div>
      </div>

      {/* Templates Grid */}
      <div className="flex-1 overflow-y-auto p-6">
        {filteredTemplates.length === 0 ? (
          <div className="text-center py-12">
            <p className="text-gray-600 dark:text-gray-400">
              No templates found matching your criteria
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {filteredTemplates.map((template) => (
              <div
                key={template.id}
                className="p-4 border border-gray-200 dark:border-gray-700 rounded-lg hover:border-blue-500 dark:hover:border-blue-400 transition-colors cursor-pointer group"
                onClick={() => handleApplyTemplate(template.id)}
              >
                {/* Header */}
                <div className="flex items-start justify-between mb-3">
                  <div className="flex items-center gap-2">
                    {template.icon && (
                      <span className="text-2xl">{template.icon}</span>
                    )}
                    <div>
                      <h3 className="text-base font-semibold text-gray-900 dark:text-gray-100">
                        {template.name}
                      </h3>
                      <span
                        className={`inline-block px-2 py-0.5 rounded text-xs font-medium capitalize mt-1 ${getCategoryColor(
                          template.category
                        )}`}
                      >
                        {template.category}
                      </span>
                    </div>
                  </div>
                </div>

                {/* Description */}
                <p className="text-sm text-gray-600 dark:text-gray-400 mb-3">
                  {template.description}
                </p>

                {/* Details */}
                <div className="flex items-center gap-4 text-xs text-gray-500 dark:text-gray-500 mb-3">
                  <span>
                    {template.conditions.length} condition
                    {template.conditions.length !== 1 ? 's' : ''}
                  </span>
                  <span>•</span>
                  <span>
                    {template.actions.length} action
                    {template.actions.length !== 1 ? 's' : ''}
                  </span>
                  <span>•</span>
                  <span className="capitalize">{template.priority}</span>
                </div>

                {/* Customizable Badge */}
                {Object.values(template.customizable).some((v) => v) && (
                  <div className="flex items-center gap-1 text-xs text-blue-600 dark:text-blue-400">
                    <Check className="w-3 h-3" />
                    <span>Customizable</span>
                  </div>
                )}

                {/* Hover State */}
                <div className="mt-3 pt-3 border-t border-gray-200 dark:border-gray-700 opacity-0 group-hover:opacity-100 transition-opacity">
                  <button className="w-full px-3 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm font-medium transition-colors">
                    Use This Template
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
