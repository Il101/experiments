/**
 * Export Progress Component
 * Shows real-time progress of ongoing export jobs
 */

import React, { useEffect } from 'react';
import { Loader2, CheckCircle, XCircle, X, Download } from 'lucide-react';
import { useExportStore } from '../../store/useExportStore';

export const ExportProgress: React.FC = () => {
  const { jobs, cancelJob } = useExportStore();
  
  // Filter active and recent completed jobs
  const activeJobs = jobs.filter((job) => job.status === 'pending' || job.status === 'processing');
  const recentCompleted = jobs
    .filter((job) => job.status === 'completed' || job.status === 'failed' || job.status === 'cancelled')
    .slice(0, 3);
  
  const visibleJobs = [...activeJobs, ...recentCompleted];
  
  if (visibleJobs.length === 0) return null;
  
  return (
    <div className="fixed bottom-4 right-4 z-50 space-y-2">
      {visibleJobs.map((job) => (
        <ExportProgressCard key={job.id} job={job} onCancel={() => cancelJob(job.id)} />
      ))}
    </div>
  );
};

interface ExportProgressCardProps {
  job: any;
  onCancel: () => void;
}

const ExportProgressCard: React.FC<ExportProgressCardProps> = ({ job, onCancel }) => {
  const [dismissed, setDismissed] = React.useState(false);
  
  // Auto-dismiss completed jobs after 5 seconds
  useEffect(() => {
    if (job.status === 'completed' || job.status === 'failed' || job.status === 'cancelled') {
      const timer = setTimeout(() => {
        setDismissed(true);
      }, 5000);
      return () => clearTimeout(timer);
    }
  }, [job.status]);
  
  if (dismissed) return null;
  
  const getStatusIcon = () => {
    switch (job.status) {
      case 'completed':
        return <CheckCircle className="h-5 w-5 text-green-600" />;
      case 'failed':
        return <XCircle className="h-5 w-5 text-red-600" />;
      case 'cancelled':
        return <XCircle className="h-5 w-5 text-orange-600" />;
      default:
        return <Loader2 className="h-5 w-5 animate-spin text-blue-600" />;
    }
  };
  
  const getStatusColor = () => {
    switch (job.status) {
      case 'completed':
        return 'border-l-green-500';
      case 'failed':
        return 'border-l-red-500';
      case 'cancelled':
        return 'border-l-orange-500';
      default:
        return 'border-l-blue-500';
    }
  };
  
  const getStatusText = () => {
    switch (job.status) {
      case 'completed':
        return 'Export completed';
      case 'failed':
        return 'Export failed';
      case 'cancelled':
        return 'Export cancelled';
      case 'processing':
        return 'Exporting...';
      default:
        return 'Export pending...';
    }
  };
  
  const handleDownload = () => {
    if (job.fileUrl) {
      const link = document.createElement('a');
      link.href = job.fileUrl;
      link.download = job.fileName || 'export';
      link.click();
    }
  };
  
  return (
    <div
      className={`w-80 rounded-lg border-l-4 bg-white p-4 shadow-lg dark:bg-gray-900 ${getStatusColor()}`}
    >
      <div className="flex items-start gap-3">
        <div className="mt-0.5">{getStatusIcon()}</div>
        
        <div className="flex-1">
          <div className="mb-1 flex items-center justify-between">
            <p className="text-sm font-medium text-gray-900 dark:text-white">
              {getStatusText()}
            </p>
            <button
              onClick={() => {
                if (job.status === 'pending' || job.status === 'processing') {
                  onCancel();
                } else {
                  setDismissed(true);
                }
              }}
              className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
          
          {job.fileName && (
            <p className="text-xs text-gray-600 dark:text-gray-400">{job.fileName}</p>
          )}
          
          {/* Progress Bar */}
          {(job.status === 'pending' || job.status === 'processing') && (
            <div className="mt-2">
              <div className="mb-1 flex items-center justify-between text-xs text-gray-600 dark:text-gray-400">
                <span>
                  {job.processedItems} / {job.totalItems || '?'} items
                </span>
                <span>{job.progress}%</span>
              </div>
              <div className="h-2 w-full overflow-hidden rounded-full bg-gray-200 dark:bg-gray-700">
                <div
                  className="h-full bg-blue-600 transition-all duration-300"
                  style={{ width: `${job.progress}%` }}
                />
              </div>
            </div>
          )}
          
          {/* Completed Status */}
          {job.status === 'completed' && (
            <div className="mt-2">
              <p className="text-xs text-gray-600 dark:text-gray-400">
                {job.processedItems} items • {(job.fileSize / 1024).toFixed(1)} KB
              </p>
              {job.fileUrl && (
                <button
                  onClick={handleDownload}
                  className="mt-2 flex items-center gap-1 text-xs font-medium text-blue-600 hover:text-blue-700 dark:text-blue-400"
                >
                  <Download className="h-3 w-3" />
                  Download
                </button>
              )}
            </div>
          )}
          
          {/* Error Message */}
          {job.status === 'failed' && job.error && (
            <p className="mt-1 text-xs text-red-600 dark:text-red-400">{job.error}</p>
          )}
        </div>
      </div>
    </div>
  );
};
