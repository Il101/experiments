/**
 * useExport Hook
 * Composable hook for export functionality
 */

import { useState, useCallback } from 'react';
import { useExportStore } from '../store/useExportStore';
import { performExport } from '../utils/export';
import type { ExportConfig, ExportOptions, CreateExportRequest } from '../types/export';

interface UseExportOptions {
  onSuccess?: (fileName: string) => void;
  onError?: (error: string) => void;
}

export const useExport = (options: UseExportOptions = {}) => {
  const { createExport: createExportJob, updateJobProgress, completeJob } = useExportStore();
  const [isExporting, setIsExporting] = useState(false);
  
  const exportData = useCallback(
    async (
      data: Record<string, any>[],
      config: ExportConfig,
      exportOptions: ExportOptions = {}
    ) => {
      setIsExporting(true);
      
      try {
        // Create export job
        const request: CreateExportRequest = { config, options: exportOptions };
        const jobId = await createExportJob(request);
        
        // Update progress
        updateJobProgress(jobId, 0, 0);
        
        // Simulate batch processing with progress updates
        const batchSize = 100;
        const totalItems = data.length;
        let processedItems = 0;
        
        // Process in batches
        const batches = Math.ceil(totalItems / batchSize);
        for (let i = 0; i < batches; i++) {
          await new Promise((resolve) => setTimeout(resolve, 200));
          processedItems = Math.min((i + 1) * batchSize, totalItems);
          const progress = Math.round((processedItems / totalItems) * 100);
          updateJobProgress(jobId, progress, processedItems);
        }
        
        // Perform actual export
        const result = await performExport(data, config, exportOptions);
        
        // Complete job
        completeJob(jobId, result.fileUrl, result.fileName, result.fileSize);
        
        // Trigger download
        const link = document.createElement('a');
        link.href = result.fileUrl;
        link.download = result.fileName;
        link.click();
        
        options.onSuccess?.(result.fileName);
        setIsExporting(false);
        
        return result;
      } catch (error) {
        const errorMessage = error instanceof Error ? error.message : 'Export failed';
        options.onError?.(errorMessage);
        setIsExporting(false);
        throw error;
      }
    },
    [createExportJob, updateJobProgress, completeJob, options]
  );
  
  return {
    exportData,
    isExporting,
  };
};
