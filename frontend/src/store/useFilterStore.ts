/**
 * Filter Store
 * Zustand store for managing filters, presets, and history
 */

import { create } from 'zustand';
import { devtools, persist } from 'zustand/middleware';
import type {
  Filter,
  FilterPreset,
  FilterHistory,
  FilterContext,
} from '../types/filters';
import { applyFilter } from '../utils/filterEngine';

// Simple UUID generator
const generateId = () => {
  return `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
};

interface FilterStore {
  // State
  filters: Record<string, Filter>;
  presets: Record<string, FilterPreset>;
  history: FilterHistory[];
  activeFilters: Record<FilterContext, string | null>; // Active filter ID per context
  
  // Filter Management
  createFilter: (name: string, description?: string) => Filter;
  updateFilter: (id: string, updates: Partial<Filter>) => void;
  deleteFilter: (id: string) => void;
  duplicateFilter: (id: string, newName: string) => Filter;
  
  // Preset Management
  createPreset: (preset: Omit<FilterPreset, 'id'>) => FilterPreset;
  updatePreset: (id: string, updates: Partial<FilterPreset>) => void;
  deletePreset: (id: string) => void;
  
  // Active Filter Management
  setActiveFilter: (context: FilterContext, filterId: string | null) => void;
  getActiveFilter: (context: FilterContext) => Filter | null;
  clearActiveFilter: (context: FilterContext) => void;
  
  // Apply Filters
  applyFilterToData: <T>(context: FilterContext, data: T[]) => T[];
  
  // History
  addToHistory: (filterId: string, context: FilterContext, resultsCount: number) => void;
  clearHistory: () => void;
  getRecentFilters: (limit?: number) => FilterHistory[];
  
  // Quick Filters
  toggleQuickFilter: (filterId: string) => void;
  getQuickFilters: () => Filter[];
  
  // Pinned Filters
  togglePinFilter: (filterId: string) => void;
  getPinnedFilters: () => Filter[];
  
  // Import/Export
  exportFilters: (filterIds?: string[]) => string;
  importFilters: (jsonData: string) => void;
  
  // Utilities
  getFilter: (id: string) => Filter | undefined;
  getPreset: (id: string) => FilterPreset | undefined;
  getAllFilters: () => Filter[];
  getAllPresets: () => FilterPreset[];
  searchFilters: (query: string) => Filter[];
}

const createEmptyFilter = (name: string, description?: string): Filter => ({
  id: generateId(),
  name,
  description,
  rootGroup: {
    id: generateId(),
    logic: 'AND',
    conditions: [],
  },
  createdAt: new Date().toISOString(),
  updatedAt: new Date().toISOString(),
});

export const useFilterStore = create<FilterStore>()(
  devtools(
    persist(
      (set, get) => ({
        // Initial State
        filters: {},
        presets: {},
        history: [],
        activeFilters: {
          positions: null,
          orders: null,
          signals: null,
          candidates: null,
          logs: null,
        },

        // Filter Management
        createFilter: (name, description) => {
          const filter = createEmptyFilter(name, description);
          set((state) => ({
            filters: {
              ...state.filters,
              [filter.id]: filter,
            },
          }));
          return filter;
        },

        updateFilter: (id, updates) => {
          set((state) => {
            const filter = state.filters[id];
            if (!filter) return state;

            return {
              filters: {
                ...state.filters,
                [id]: {
                  ...filter,
                  ...updates,
                  updatedAt: new Date().toISOString(),
                },
              },
            };
          });
        },

        deleteFilter: (id) => {
          set((state) => {
            const { [id]: removed, ...remainingFilters } = state.filters;
            
            // Also remove from active filters
            const activeFilters = { ...state.activeFilters };
            Object.keys(activeFilters).forEach((context) => {
              if (activeFilters[context as FilterContext] === id) {
                activeFilters[context as FilterContext] = null;
              }
            });

            return {
              filters: remainingFilters,
              activeFilters,
            };
          });
        },

        duplicateFilter: (id, newName) => {
          const original = get().filters[id];
          if (!original) throw new Error(`Filter ${id} not found`);

          const duplicate: Filter = {
            ...original,
            id: generateId(),
            name: newName,
            createdAt: new Date().toISOString(),
            updatedAt: new Date().toISOString(),
            isQuickFilter: false,
            isPinned: false,
          };

          set((state) => ({
            filters: {
              ...state.filters,
              [duplicate.id]: duplicate,
            },
          }));

          return duplicate;
        },

        // Preset Management
        createPreset: (preset) => {
          const newPreset: FilterPreset = {
            ...preset,
            id: generateId(),
            usageCount: 0,
          };

          set((state) => ({
            presets: {
              ...state.presets,
              [newPreset.id]: newPreset,
            },
          }));

          return newPreset;
        },

        updatePreset: (id, updates) => {
          set((state) => {
            const preset = state.presets[id];
            if (!preset) return state;

            return {
              presets: {
                ...state.presets,
                [id]: {
                  ...preset,
                  ...updates,
                },
              },
            };
          });
        },

        deletePreset: (id) => {
          set((state) => {
            const { [id]: removed, ...remainingPresets } = state.presets;
            return { presets: remainingPresets };
          });
        },

        // Active Filter Management
        setActiveFilter: (context, filterId) => {
          set((state) => ({
            activeFilters: {
              ...state.activeFilters,
              [context]: filterId,
            },
          }));

          // Update preset usage if applicable
          if (filterId) {
            const preset = Object.values(get().presets).find(
              (p) => p.filter.id === filterId
            );

            if (preset) {
              get().updatePreset(preset.id, {
                usageCount: (preset.usageCount || 0) + 1,
                lastUsedAt: new Date().toISOString(),
              });
            }
          }
        },

        getActiveFilter: (context) => {
          const filterId = get().activeFilters[context];
          return filterId ? get().filters[filterId] || null : null;
        },

        clearActiveFilter: (context) => {
          set((state) => ({
            activeFilters: {
              ...state.activeFilters,
              [context]: null,
            },
          }));
        },

        // Apply Filters
        applyFilterToData: <T>(context: FilterContext, data: T[]): T[] => {
          const filter = get().getActiveFilter(context);
          if (!filter) return data;

          const result = applyFilter(data, filter);
          return result.data;
        },

        // History
        addToHistory: (filterId, context, resultsCount) => {
          const filter = get().filters[filterId];
          if (!filter) return;

          const historyEntry: FilterHistory = {
            id: generateId(),
            filter,
            appliedAt: new Date().toISOString(),
            resultsCount,
            context,
          };

          set((state) => ({
            history: [historyEntry, ...state.history].slice(0, 100), // Keep last 100
          }));
        },

        clearHistory: () => {
          set({ history: [] });
        },

        getRecentFilters: (limit = 10) => {
          return get().history.slice(0, limit);
        },

        // Quick Filters
        toggleQuickFilter: (filterId) => {
          const filter = get().filters[filterId];
          if (!filter) return;

          get().updateFilter(filterId, {
            isQuickFilter: !filter.isQuickFilter,
          });
        },

        getQuickFilters: () => {
          return Object.values(get().filters).filter((f) => f.isQuickFilter);
        },

        // Pinned Filters
        togglePinFilter: (filterId) => {
          const filter = get().filters[filterId];
          if (!filter) return;

          get().updateFilter(filterId, {
            isPinned: !filter.isPinned,
          });
        },

        getPinnedFilters: () => {
          return Object.values(get().filters).filter((f) => f.isPinned);
        },

        // Import/Export
        exportFilters: (filterIds) => {
          const filters = filterIds
            ? filterIds.map((id) => get().filters[id]).filter(Boolean)
            : Object.values(get().filters);

          const presets = Object.values(get().presets);

          const exportData = {
            version: '1.0.0',
            exportedAt: new Date().toISOString(),
            filters,
            presets,
          };

          return JSON.stringify(exportData, null, 2);
        },

        importFilters: (jsonData) => {
          try {
            const importData = JSON.parse(jsonData);

            // Validate version
            if (importData.version !== '1.0.0') {
              throw new Error('Unsupported export version');
            }

            // Import filters
            const newFilters: Record<string, Filter> = {};
            (importData.filters || []).forEach((filter: Filter) => {
              newFilters[filter.id] = filter;
            });

            // Import presets
            const newPresets: Record<string, FilterPreset> = {};
            (importData.presets || []).forEach((preset: FilterPreset) => {
              newPresets[preset.id] = preset;
            });

            set((state) => ({
              filters: { ...state.filters, ...newFilters },
              presets: { ...state.presets, ...newPresets },
            }));
          } catch (error) {
            console.error('Failed to import filters:', error);
            throw error;
          }
        },

        // Utilities
        getFilter: (id) => get().filters[id],
        getPreset: (id) => get().presets[id],
        getAllFilters: () => Object.values(get().filters),
        getAllPresets: () => Object.values(get().presets),

        searchFilters: (query) => {
          const lowerQuery = query.toLowerCase();
          return Object.values(get().filters).filter(
            (filter) =>
              filter.name.toLowerCase().includes(lowerQuery) ||
              filter.description?.toLowerCase().includes(lowerQuery)
          );
        },
      }),
      {
        name: 'filter-store',
        partialize: (state) => ({
          filters: state.filters,
          presets: state.presets,
          activeFilters: state.activeFilters,
        }),
      }
    ),
    { name: 'FilterStore' }
  )
);
