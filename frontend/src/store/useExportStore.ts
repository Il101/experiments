/**
 * Export Store
 * Zustand store for managing exports and reporting
 */

import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type {
  ExportJob,
  ExportTemplate,
  ScheduledExport,
  ExportHistoryItem,
  ExportStatistics,
  CreateExportRequest,
} from '../types/export';

// ==================== Store State ====================

interface ExportStoreState {
  // Jobs
  jobs: ExportJob[];
  activeJobId: string | null;
  
  // Templates
  templates: ExportTemplate[];
  
  // Scheduled Exports
  scheduledExports: ScheduledExport[];
  
  // History
  history: ExportHistoryItem[];
  maxHistorySize: number;
  
  // UI State
  exportDialogOpen: boolean;
  selectedTemplate: string | null;
  
  // Job Actions
  createExport: (request: CreateExportRequest) => Promise<string>;
  updateJobProgress: (jobId: string, progress: number, processedItems: number) => void;
  completeJob: (jobId: string, fileUrl: string, fileName: string, fileSize: number) => void;
  failJob: (jobId: string, error: string) => void;
  cancelJob: (jobId: string) => void;
  getJob: (jobId: string) => ExportJob | undefined;
  clearJobs: () => void;
  
  // Template Actions
  loadTemplates: () => void;
  createTemplate: (template: Omit<ExportTemplate, 'id' | 'createdAt' | 'updatedAt'>) => void;
  updateTemplate: (id: string, updates: Partial<ExportTemplate>) => void;
  deleteTemplate: (id: string) => void;
  getTemplate: (id: string) => ExportTemplate | undefined;
  
  // Scheduled Export Actions
  createScheduledExport: (scheduledExport: Omit<ScheduledExport, 'id' | 'createdAt' | 'updatedAt'>) => void;
  updateScheduledExport: (id: string, updates: Partial<ScheduledExport>) => void;
  deleteScheduledExport: (id: string) => void;
  toggleScheduledExport: (id: string) => void;
  
  // History Actions
  addToHistory: (item: Omit<ExportHistoryItem, 'id'>) => void;
  clearHistory: () => void;
  getHistoryByFormat: (format: string) => ExportHistoryItem[];
  
  // Statistics
  getStatistics: () => ExportStatistics;
  
  // UI Actions
  openExportDialog: (templateId?: string) => void;
  closeExportDialog: () => void;
}

// ==================== Built-in Templates ====================

const builtInTemplates: ExportTemplate[] = [
  {
    id: 'positions-csv',
    name: 'Positions Export (CSV)',
    description: 'Export all position details to CSV',
    dataType: 'positions',
    format: 'csv',
    fields: ['symbol', 'side', 'size', 'entryPrice', 'currentPrice', 'pnl', 'roi', 'tags'],
    includeCharts: false,
    includeStatistics: false,
    isDefault: true,
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
  },
  {
    id: 'trades-excel',
    name: 'Trade History (Excel)',
    description: 'Detailed trade history with statistics',
    dataType: 'trades',
    format: 'excel',
    fields: ['symbol', 'side', 'entryTime', 'exitTime', 'entryPrice', 'exitPrice', 'size', 'pnl', 'commission', 'duration'],
    includeCharts: false,
    includeStatistics: true,
    isDefault: true,
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
  },
  {
    id: 'performance-pdf',
    name: 'Performance Report (PDF)',
    description: 'Comprehensive performance report with charts',
    dataType: 'performance',
    format: 'pdf',
    fields: ['date', 'totalPnL', 'winRate', 'profitFactor', 'sharpeRatio', 'maxDrawdown'],
    includeCharts: true,
    includeStatistics: true,
    isDefault: true,
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
  },
  {
    id: 'alerts-json',
    name: 'Alerts Backup (JSON)',
    description: 'Export alerts configuration as JSON',
    dataType: 'alerts',
    format: 'json',
    fields: ['name', 'conditions', 'actions', 'priority', 'enabled', 'triggerCount'],
    includeCharts: false,
    includeStatistics: false,
    isDefault: true,
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
  },
];

// ==================== Store Implementation ====================

export const useExportStore = create<ExportStoreState>()(
  persist(
    (set, get) => ({
      // Initial state
      jobs: [],
      activeJobId: null,
      templates: builtInTemplates,
      scheduledExports: [],
      history: [],
      maxHistorySize: 100,
      exportDialogOpen: false,
      selectedTemplate: null,
      
      // Job Actions
      createExport: async (request) => {
        const jobId = `export_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
        const newJob: ExportJob = {
          id: jobId,
          config: request.config,
          status: 'pending',
          progress: 0,
          totalItems: 0,
          processedItems: 0,
          startedAt: new Date().toISOString(),
        };
        
        set((state) => ({
          jobs: [...state.jobs, newJob],
          activeJobId: jobId,
        }));
        
        // Simulate export processing
        setTimeout(() => {
          set((state) => ({
            jobs: state.jobs.map((job) =>
              job.id === jobId ? { ...job, status: 'processing' as const } : job
            ),
          }));
        }, 100);
        
        return jobId;
      },
      
      updateJobProgress: (jobId, progress, processedItems) => {
        set((state) => ({
          jobs: state.jobs.map((job) =>
            job.id === jobId
              ? { ...job, progress, processedItems }
              : job
          ),
        }));
      },
      
      completeJob: (jobId, fileUrl, fileName, fileSize) => {
        set((state) => {
          const job = state.jobs.find((j) => j.id === jobId);
          if (!job) return state;
          
          const historyItem: ExportHistoryItem = {
            id: `history_${Date.now()}`,
            config: job.config,
            fileName,
            fileSize,
            format: job.config.format,
            status: 'success',
            exportedAt: new Date().toISOString(),
            downloadUrl: fileUrl,
            expiresAt: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString(), // 7 days
          };
          
          return {
            jobs: state.jobs.map((job) =>
              job.id === jobId
                ? {
                    ...job,
                    status: 'completed' as const,
                    progress: 100,
                    completedAt: new Date().toISOString(),
                    fileUrl,
                    fileName,
                    fileSize,
                  }
                : job
            ),
            history: [historyItem, ...state.history].slice(0, state.maxHistorySize),
            activeJobId: null,
          };
        });
      },
      
      failJob: (jobId, error) => {
        set((state) => ({
          jobs: state.jobs.map((job) =>
            job.id === jobId
              ? {
                  ...job,
                  status: 'failed' as const,
                  completedAt: new Date().toISOString(),
                  error,
                }
              : job
          ),
          activeJobId: null,
        }));
      },
      
      cancelJob: (jobId) => {
        set((state) => ({
          jobs: state.jobs.map((job) =>
            job.id === jobId
              ? {
                  ...job,
                  status: 'cancelled' as const,
                  completedAt: new Date().toISOString(),
                }
              : job
          ),
          activeJobId: null,
        }));
      },
      
      getJob: (jobId) => {
        return get().jobs.find((job) => job.id === jobId);
      },
      
      clearJobs: () => {
        set({ jobs: [], activeJobId: null });
      },
      
      // Template Actions
      loadTemplates: () => {
        // Templates already loaded with built-in ones
        console.log('Templates loaded:', get().templates.length);
      },
      
      createTemplate: (template) => {
        const newTemplate: ExportTemplate = {
          ...template,
          id: `template_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
          createdAt: new Date().toISOString(),
          updatedAt: new Date().toISOString(),
        };
        
        set((state) => ({
          templates: [...state.templates, newTemplate],
        }));
      },
      
      updateTemplate: (id, updates) => {
        set((state) => ({
          templates: state.templates.map((template) =>
            template.id === id
              ? { ...template, ...updates, updatedAt: new Date().toISOString() }
              : template
          ),
        }));
      },
      
      deleteTemplate: (id) => {
        set((state) => ({
          templates: state.templates.filter((template) => template.id !== id),
        }));
      },
      
      getTemplate: (id) => {
        return get().templates.find((template) => template.id === id);
      },
      
      // Scheduled Export Actions
      createScheduledExport: (scheduledExport) => {
        const newScheduledExport: ScheduledExport = {
          ...scheduledExport,
          id: `scheduled_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
          createdAt: new Date().toISOString(),
          updatedAt: new Date().toISOString(),
        };
        
        set((state) => ({
          scheduledExports: [...state.scheduledExports, newScheduledExport],
        }));
      },
      
      updateScheduledExport: (id, updates) => {
        set((state) => ({
          scheduledExports: state.scheduledExports.map((scheduled) =>
            scheduled.id === id
              ? { ...scheduled, ...updates, updatedAt: new Date().toISOString() }
              : scheduled
          ),
        }));
      },
      
      deleteScheduledExport: (id) => {
        set((state) => ({
          scheduledExports: state.scheduledExports.filter((scheduled) => scheduled.id !== id),
        }));
      },
      
      toggleScheduledExport: (id) => {
        set((state) => ({
          scheduledExports: state.scheduledExports.map((scheduled) =>
            scheduled.id === id
              ? { ...scheduled, enabled: !scheduled.enabled, updatedAt: new Date().toISOString() }
              : scheduled
          ),
        }));
      },
      
      // History Actions
      addToHistory: (item) => {
        const historyItem: ExportHistoryItem = {
          ...item,
          id: `history_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
        };
        
        set((state) => ({
          history: [historyItem, ...state.history].slice(0, state.maxHistorySize),
        }));
      },
      
      clearHistory: () => {
        set({ history: [] });
      },
      
      getHistoryByFormat: (format) => {
        return get().history.filter((item) => item.format === format);
      },
      
      // Statistics
      getStatistics: () => {
        const state = get();
        const completedJobs = state.jobs.filter((job) => job.status === 'completed');
        
        const exportsByFormat = state.history.reduce((acc, item) => {
          acc[item.format] = (acc[item.format] || 0) + 1;
          return acc;
        }, {} as Record<string, number>);
        
        const exportsByType = state.history.reduce((acc, item) => {
          acc[item.config.dataType] = (acc[item.config.dataType] || 0) + 1;
          return acc;
        }, {} as Record<string, number>);
        
        const totalDataExported = completedJobs.reduce((sum, job) => sum + job.processedItems, 0);
        const totalFileSize = state.history.reduce((sum, item) => sum + item.fileSize, 0);
        
        const totalTime = completedJobs.reduce((sum, job) => {
          if (job.completedAt && job.startedAt) {
            return sum + (new Date(job.completedAt).getTime() - new Date(job.startedAt).getTime());
          }
          return sum;
        }, 0);
        
        const averageExportTime = completedJobs.length > 0 ? totalTime / completedJobs.length : 0;
        
        return {
          totalExports: state.history.length,
          exportsByFormat,
          exportsByType,
          totalDataExported,
          totalFileSize,
          averageExportTime,
          recentExports: state.history.slice(0, 10),
        };
      },
      
      // UI Actions
      openExportDialog: (templateId) => {
        set({ exportDialogOpen: true, selectedTemplate: templateId || null });
      },
      
      closeExportDialog: () => {
        set({ exportDialogOpen: false, selectedTemplate: null });
      },
    }),
    {
      name: 'export-storage',
      partialize: (state) => ({
        templates: state.templates.filter((t) => !t.isDefault), // Only persist custom templates
        scheduledExports: state.scheduledExports,
        history: state.history.slice(0, 50), // Keep last 50 in storage
      }),
    }
  )
);
