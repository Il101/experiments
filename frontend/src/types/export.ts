/**
 * Export & Reporting Type Definitions
 * Types for data export functionality
 */

// ==================== Export Format Types ====================

export type ExportFormat = 'csv' | 'json' | 'excel' | 'pdf';

export type ExportDataType = 'positions' | 'trades' | 'alerts' | 'analytics' | 'performance';

// ==================== Export Configuration ====================

export interface ExportConfig {
  format: ExportFormat;
  dataType: ExportDataType;
  itemIds?: string[]; // Specific items to export, or all if undefined
  fields?: string[]; // Specific fields to include, or all if undefined
  dateRange?: {
    start: string; // ISO date string
    end: string;   // ISO date string
  };
  filters?: Record<string, any>; // Applied filters
  sorting?: {
    field: string;
    direction: 'asc' | 'desc';
  };
  grouping?: string; // Group by field
  includeCharts?: boolean; // For PDF exports
  includeStatistics?: boolean;
  templateId?: string; // Use specific template
}

// ==================== Export Template ====================

export interface ExportTemplate {
  id: string;
  name: string;
  description: string;
  dataType: ExportDataType;
  format: ExportFormat;
  fields: string[];
  includeCharts: boolean;
  includeStatistics: boolean;
  isDefault: boolean;
  createdAt: string;
  updatedAt: string;
}

// ==================== Export Job ====================

export interface ExportJob {
  id: string;
  config: ExportConfig;
  status: 'pending' | 'processing' | 'completed' | 'failed' | 'cancelled';
  progress: number; // 0-100
  totalItems: number;
  processedItems: number;
  startedAt: string;
  completedAt?: string;
  fileUrl?: string;
  fileName?: string;
  fileSize?: number; // bytes
  error?: string;
}

// ==================== Scheduled Export ====================

export interface ScheduledExport {
  id: string;
  name: string;
  description?: string;
  config: ExportConfig;
  schedule: ExportSchedule;
  enabled: boolean;
  lastRunAt?: string;
  nextRunAt: string;
  emailRecipients?: string[];
  createdAt: string;
  updatedAt: string;
}

export interface ExportSchedule {
  type: 'daily' | 'weekly' | 'monthly' | 'custom';
  time: string; // HH:mm format
  dayOfWeek?: number; // 0-6 for weekly
  dayOfMonth?: number; // 1-31 for monthly
  cronExpression?: string; // For custom schedules
}

// ==================== Export History ====================

export interface ExportHistoryItem {
  id: string;
  config: ExportConfig;
  fileName: string;
  fileSize: number;
  format: ExportFormat;
  status: 'success' | 'failed';
  exportedAt: string;
  downloadUrl?: string;
  expiresAt?: string; // When download link expires
  error?: string;
}

// ==================== Field Configuration ====================

export interface ExportField {
  key: string;
  label: string;
  type: 'string' | 'number' | 'boolean' | 'date' | 'currency';
  format?: string; // e.g., "0.00" for numbers, "YYYY-MM-DD" for dates
  width?: number; // Column width for Excel
  required?: boolean;
  defaultValue?: any;
}

// ==================== Report Template ====================

export interface ReportTemplate {
  id: string;
  name: string;
  description: string;
  type: 'daily' | 'weekly' | 'monthly' | 'custom';
  sections: ReportSection[];
  cover?: ReportCoverConfig;
  footer?: string;
  isPublic: boolean;
  createdBy: string;
  createdAt: string;
}

export interface ReportSection {
  id: string;
  type: 'summary' | 'table' | 'chart' | 'text' | 'statistics';
  title: string;
  dataSource?: ExportDataType;
  config: Record<string, any>;
  order: number;
}

export interface ReportCoverConfig {
  title: string;
  subtitle?: string;
  logo?: string;
  dateFormat?: string;
  includeGeneratedDate: boolean;
}

// ==================== Export Options ====================

export interface ExportOptions {
  delimiter?: string; // For CSV (default: ',')
  encoding?: 'utf-8' | 'utf-16' | 'iso-8859-1';
  dateFormat?: string; // Date formatting (default: YYYY-MM-DD)
  timeFormat?: string; // Time formatting (default: HH:mm:ss)
  currencySymbol?: string; // Currency symbol (default: $)
  decimalPlaces?: number; // Number decimals (default: 2)
  includeHeaders?: boolean; // Include column headers (default: true)
  includeRowNumbers?: boolean; // Include row numbers (default: false)
  sheetName?: string; // For Excel (default: 'Sheet1')
  paperSize?: 'A4' | 'Letter' | 'Legal'; // For PDF (default: A4)
  orientation?: 'portrait' | 'landscape'; // For PDF (default: portrait)
  compression?: boolean; // Compress output (default: false)
}

// ==================== Export Statistics ====================

export interface ExportStatistics {
  totalExports: number;
  exportsByFormat: Record<ExportFormat, number>;
  exportsByType: Record<ExportDataType, number>;
  totalDataExported: number; // Total rows/items
  totalFileSize: number; // Total bytes
  averageExportTime: number; // Milliseconds
  mostUsedTemplate?: string;
  recentExports: ExportHistoryItem[];
}

// ==================== API Types ====================

export interface CreateExportRequest {
  config: ExportConfig;
  options?: ExportOptions;
}

export interface CreateExportResponse {
  jobId: string;
  status: 'pending' | 'processing';
  estimatedTime?: number; // Seconds
}

export interface ExportStatusResponse {
  job: ExportJob;
  downloadUrl?: string;
}

export interface CreateTemplateRequest {
  name: string;
  description?: string;
  dataType: ExportDataType;
  format: ExportFormat;
  fields: string[];
  includeCharts?: boolean;
  includeStatistics?: boolean;
}

export interface CreateScheduledExportRequest {
  name: string;
  description?: string;
  config: ExportConfig;
  schedule: ExportSchedule;
  emailRecipients?: string[];
}

// ==================== Email Delivery ====================

export interface EmailDeliveryConfig {
  recipients: string[];
  subject: string;
  body?: string;
  attachmentName?: string;
  sendOnSuccess: boolean;
  sendOnFailure: boolean;
}

// ==================== Export Preview ====================

export interface ExportPreview {
  fields: ExportField[];
  sampleData: Record<string, any>[];
  totalRecords: number;
  estimatedFileSize: number; // bytes
  estimatedTime: number; // seconds
}
