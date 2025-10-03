/**
 * Filter Preset Selector
 * Grid/list view of saved filter presets
 */

import React, { useState, useMemo } from 'react';
import { Search, Star, Clock, TrendingUp, Grid3x3, List, Play, Edit2, Trash2 } from 'lucide-react';
import { useFilterStore } from '../../store/useFilterStore';
import type { FilterPreset, FilterContext } from '../../types/filters';

interface FilterPresetSelectorProps {
  context: FilterContext;
  onApplyPreset?: (preset: FilterPreset) => void;
  onEditPreset?: (preset: FilterPreset) => void;
  className?: string;
}

type ViewMode = 'grid' | 'list';
type SortMode = 'name' | 'recent' | 'popular';

export const FilterPresetSelector: React.FC<FilterPresetSelectorProps> = ({
  context,
  onApplyPreset,
  onEditPreset,
  className = '',
}) => {
  const { getAllPresets, deletePreset, setActiveFilter } = useFilterStore();
  const allPresets = getAllPresets();

  const [viewMode, setViewMode] = useState<ViewMode>('grid');
  const [sortMode, setSortMode] = useState<SortMode>('name');
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<string>('all');

  // Get unique categories
  const categories = useMemo(() => {
    const cats = new Set<string>();
    allPresets.forEach((preset) => {
      if (preset.category) cats.add(preset.category);
    });
    return ['all', ...Array.from(cats)];
  }, [allPresets]);

  // Filter and sort presets
  const filteredPresets = useMemo(() => {
    let filtered = allPresets;

    // Filter by search query
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      filtered = filtered.filter(
        (preset) =>
          preset.name.toLowerCase().includes(query) ||
          preset.description?.toLowerCase().includes(query)
      );
    }

    // Filter by category
    if (selectedCategory !== 'all') {
      filtered = filtered.filter((preset) => preset.category === selectedCategory);
    }

    // Sort
    filtered = [...filtered].sort((a, b) => {
      switch (sortMode) {
        case 'name':
          return a.name.localeCompare(b.name);
        case 'recent':
          return (
            new Date(b.lastUsedAt || 0).getTime() - new Date(a.lastUsedAt || 0).getTime()
          );
        case 'popular':
          return (b.usageCount || 0) - (a.usageCount || 0);
        default:
          return 0;
      }
    });

    return filtered;
  }, [allPresets, searchQuery, selectedCategory, sortMode]);

  const handleApplyPreset = (preset: FilterPreset) => {
    setActiveFilter(context, preset.filter.id);
    onApplyPreset?.(preset);
  };

  const handleDeletePreset = (presetId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (confirm('Are you sure you want to delete this preset?')) {
      deletePreset(presetId);
    }
  };

  return (
    <div className={`bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-700 ${className}`}>
      {/* Header */}
      <div className="p-4 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
            Filter Presets
          </h3>

          {/* View Mode Toggle */}
          <div className="flex items-center gap-2">
            <button
              onClick={() => setViewMode('grid')}
              className={`p-2 rounded-lg transition-colors ${
                viewMode === 'grid'
                  ? 'bg-blue-500 text-white'
                  : 'text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800'
              }`}
              title="Grid view"
            >
              <Grid3x3 className="w-4 h-4" />
            </button>
            <button
              onClick={() => setViewMode('list')}
              className={`p-2 rounded-lg transition-colors ${
                viewMode === 'list'
                  ? 'bg-blue-500 text-white'
                  : 'text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800'
              }`}
              title="List view"
            >
              <List className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Search & Filters */}
        <div className="flex gap-3 mb-3">
          {/* Search */}
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search presets..."
              className="w-full pl-10 pr-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 text-sm"
            />
          </div>

          {/* Sort */}
          <select
            value={sortMode}
            onChange={(e) => setSortMode(e.target.value as SortMode)}
            className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 text-sm"
          >
            <option value="name">Name</option>
            <option value="recent">Recently Used</option>
            <option value="popular">Most Popular</option>
          </select>
        </div>

        {/* Categories */}
        <div className="flex gap-2 flex-wrap">
          {categories.map((category) => (
            <button
              key={category}
              onClick={() => setSelectedCategory(category)}
              className={`
                px-3 py-1.5 text-sm rounded-lg transition-colors capitalize
                ${
                  selectedCategory === category
                    ? 'bg-blue-500 text-white'
                    : 'bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-700'
                }
              `}
            >
              {category}
            </button>
          ))}
        </div>
      </div>

      {/* Presets Grid/List */}
      <div className="p-4">
        {filteredPresets.length === 0 ? (
          <div className="text-center py-12">
            <Star className="w-12 h-12 text-gray-300 dark:text-gray-700 mx-auto mb-3" />
            <p className="text-gray-500 dark:text-gray-400 text-sm">
              {searchQuery ? 'No presets match your search' : 'No presets available'}
            </p>
          </div>
        ) : viewMode === 'grid' ? (
          // Grid View
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {filteredPresets.map((preset) => (
              <PresetCard
                key={preset.id}
                preset={preset}
                onApply={() => handleApplyPreset(preset)}
                onEdit={onEditPreset ? () => onEditPreset(preset) : undefined}
                onDelete={(e) => handleDeletePreset(preset.id, e)}
              />
            ))}
          </div>
        ) : (
          // List View
          <div className="space-y-2">
            {filteredPresets.map((preset) => (
              <PresetListItem
                key={preset.id}
                preset={preset}
                onApply={() => handleApplyPreset(preset)}
                onEdit={onEditPreset ? () => onEditPreset(preset) : undefined}
                onDelete={(e) => handleDeletePreset(preset.id, e)}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

// ===== PRESET CARD (GRID VIEW) =====
interface PresetCardProps {
  preset: FilterPreset;
  onApply: () => void;
  onEdit?: () => void;
  onDelete: (e: React.MouseEvent) => void;
}

const PresetCard: React.FC<PresetCardProps> = ({ preset, onApply, onEdit, onDelete }) => {
  return (
    <div className="group relative p-4 bg-gray-50 dark:bg-gray-800/50 rounded-lg border border-gray-200 dark:border-gray-700 hover:border-blue-500 dark:hover:border-blue-500 transition-all cursor-pointer">
      {/* Icon */}
      <div className="w-10 h-10 bg-blue-500 rounded-lg flex items-center justify-center text-white mb-3">
        {preset.icon ? (
          <span className="text-xl">{preset.icon}</span>
        ) : (
          <Star className="w-5 h-5" />
        )}
      </div>

      {/* Name */}
      <h4 className="font-semibold text-gray-900 dark:text-gray-100 mb-1">
        {preset.name}
      </h4>

      {/* Description */}
      {preset.description && (
        <p className="text-sm text-gray-600 dark:text-gray-400 mb-3 line-clamp-2">
          {preset.description}
        </p>
      )}

      {/* Stats */}
      <div className="flex items-center gap-3 text-xs text-gray-500 dark:text-gray-400">
        <div className="flex items-center gap-1">
          <TrendingUp className="w-3 h-3" />
          <span>{preset.usageCount || 0} uses</span>
        </div>
        {preset.lastUsedAt && (
          <div className="flex items-center gap-1">
            <Clock className="w-3 h-3" />
            <span>{new Date(preset.lastUsedAt).toLocaleDateString()}</span>
          </div>
        )}
      </div>

      {/* Actions (show on hover) */}
      <div className="absolute top-2 right-2 flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
        <button
          onClick={onApply}
          className="p-1.5 bg-blue-500 hover:bg-blue-600 text-white rounded-lg transition-colors"
          title="Apply preset"
        >
          <Play className="w-3 h-3" />
        </button>
        {onEdit && (
          <button
            onClick={onEdit}
            className="p-1.5 bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 dark:hover:bg-gray-600 text-gray-700 dark:text-gray-300 rounded-lg transition-colors"
            title="Edit preset"
          >
            <Edit2 className="w-3 h-3" />
          </button>
        )}
        <button
          onClick={onDelete}
          className="p-1.5 bg-red-500 hover:bg-red-600 text-white rounded-lg transition-colors"
          title="Delete preset"
        >
          <Trash2 className="w-3 h-3" />
        </button>
      </div>

      {/* Default Badge */}
      {preset.isDefault && (
        <div className="absolute top-2 left-2 px-2 py-0.5 bg-green-500 text-white text-xs font-medium rounded">
          Default
        </div>
      )}
    </div>
  );
};

// ===== PRESET LIST ITEM (LIST VIEW) =====
const PresetListItem: React.FC<PresetCardProps> = ({ preset, onApply, onEdit, onDelete }) => {
  return (
    <div className="group flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-800/50 rounded-lg border border-gray-200 dark:border-gray-700 hover:border-blue-500 dark:hover:border-blue-500 transition-all">
      <div className="flex items-center gap-3 flex-1 min-w-0">
        {/* Icon */}
        <div className="w-8 h-8 bg-blue-500 rounded-lg flex items-center justify-center text-white flex-shrink-0">
          {preset.icon ? (
            <span className="text-sm">{preset.icon}</span>
          ) : (
            <Star className="w-4 h-4" />
          )}
        </div>

        {/* Info */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <h4 className="font-medium text-gray-900 dark:text-gray-100 truncate">
              {preset.name}
            </h4>
            {preset.isDefault && (
              <span className="px-2 py-0.5 bg-green-500 text-white text-xs font-medium rounded">
                Default
              </span>
            )}
          </div>
          {preset.description && (
            <p className="text-sm text-gray-600 dark:text-gray-400 truncate">
              {preset.description}
            </p>
          )}
        </div>

        {/* Stats */}
        <div className="flex items-center gap-4 text-xs text-gray-500 dark:text-gray-400">
          <div className="flex items-center gap-1">
            <TrendingUp className="w-3 h-3" />
            <span>{preset.usageCount || 0}</span>
          </div>
          {preset.lastUsedAt && (
            <div className="flex items-center gap-1">
              <Clock className="w-3 h-3" />
              <span>{new Date(preset.lastUsedAt).toLocaleDateString()}</span>
            </div>
          )}
        </div>
      </div>

      {/* Actions */}
      <div className="flex gap-1 ml-3">
        <button
          onClick={onApply}
          className="p-2 bg-blue-500 hover:bg-blue-600 text-white rounded-lg transition-colors"
          title="Apply preset"
        >
          <Play className="w-4 h-4" />
        </button>
        {onEdit && (
          <button
            onClick={onEdit}
            className="p-2 bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 dark:hover:bg-gray-600 text-gray-700 dark:text-gray-300 rounded-lg transition-colors"
            title="Edit preset"
          >
            <Edit2 className="w-4 h-4" />
          </button>
        )}
        <button
          onClick={onDelete}
          className="p-2 bg-red-500 hover:bg-red-600 text-white rounded-lg transition-colors"
          title="Delete preset"
        >
          <Trash2 className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
};
