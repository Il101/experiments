/**
 * Export Utilities
 * Helper functions for data export operations
 */

import type { ExportConfig, ExportOptions } from '../types/export';

// ==================== CSV Export ====================

export const exportToCSV = (
  data: Record<string, any>[],
  config: ExportConfig,
  options: ExportOptions = {}
): string => {
  const {
    delimiter = ',',
    includeHeaders = true,
    dateFormat = 'YYYY-MM-DD',
    currencySymbol = '$',
    decimalPlaces = 2,
  } = options;
  
  if (data.length === 0) return '';
  
  // Determine fields to export
  const fields = config.fields || Object.keys(data[0]);
  
  const lines: string[] = [];
  
  // Add headers
  if (includeHeaders) {
    lines.push(fields.map((field) => escapeCSV(field)).join(delimiter));
  }
  
  // Add data rows
  data.forEach((item) => {
    const row = fields.map((field) => {
      let value = item[field];
      
      // Format value based on type
      if (value === null || value === undefined) {
        return '';
      }
      
      if (typeof value === 'number') {
        if (field.toLowerCase().includes('price') || field.toLowerCase().includes('pnl')) {
          return `${currencySymbol}${value.toFixed(decimalPlaces)}`;
        }
        return value.toFixed(decimalPlaces);
      }
      
      if (value instanceof Date) {
        return formatDate(value, dateFormat);
      }
      
      if (typeof value === 'object') {
        return JSON.stringify(value);
      }
      
      return escapeCSV(String(value));
    });
    
    lines.push(row.join(delimiter));
  });
  
  return lines.join('\n');
};

const escapeCSV = (value: string): string => {
  if (value.includes(',') || value.includes('"') || value.includes('\n')) {
    return `"${value.replace(/"/g, '""')}"`;
  }
  return value;
};

// ==================== JSON Export ====================

export const exportToJSON = (
  data: Record<string, any>[],
  config: ExportConfig,
  options: ExportOptions = {}
): string => {
  const { dateFormat = 'YYYY-MM-DD' } = options;
  
  // Filter fields if specified
  let exportData = data;
  if (config.fields && config.fields.length > 0) {
    exportData = data.map((item) => {
      const filtered: Record<string, any> = {};
      config.fields!.forEach((field) => {
        filtered[field] = item[field];
      });
      return filtered;
    });
  }
  
  // Format dates
  exportData = exportData.map((item) => {
    const formatted = { ...item };
    Object.keys(formatted).forEach((key) => {
      if (formatted[key] instanceof Date) {
        formatted[key] = formatDate(formatted[key], dateFormat);
      }
    });
    return formatted;
  });
  
  return JSON.stringify(exportData, null, 2);
};

// ==================== Excel Export (requires xlsx library) ====================

export const exportToExcel = async (
  data: Record<string, any>[],
  config: ExportConfig,
  options: ExportOptions = {}
): Promise<Blob> => {
  // This would use a library like xlsx
  // For now, return a mock blob
  const csv = exportToCSV(data, config, options);
  return new Blob([csv], { type: 'application/vnd.ms-excel' });
};

// ==================== PDF Export (requires jsPDF library) ====================

export const exportToPDF = async (
  data: Record<string, any>[],
  config: ExportConfig,
  options: ExportOptions = {}
): Promise<Blob> => {
  // This would use a library like jsPDF
  // For now, return a mock blob with table content
  const { paperSize = 'A4', orientation = 'portrait' } = options;
  
  // Mock PDF generation
  const text = `PDF Export - ${config.dataType}\n\n${data.length} records\n\nConfiguration:\nPaper: ${paperSize}\nOrientation: ${orientation}`;
  
  return new Blob([text], { type: 'application/pdf' });
};

// ==================== Date Formatting ====================

const formatDate = (date: Date, format: string): string => {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  const hours = String(date.getHours()).padStart(2, '0');
  const minutes = String(date.getMinutes()).padStart(2, '0');
  const seconds = String(date.getSeconds()).padStart(2, '0');
  
  return format
    .replace('YYYY', String(year))
    .replace('MM', month)
    .replace('DD', day)
    .replace('HH', hours)
    .replace('mm', minutes)
    .replace('ss', seconds);
};

// ==================== Download Trigger ====================

export const downloadFile = (
  content: string | Blob,
  fileName: string,
  mimeType: string
): void => {
  const blob = typeof content === 'string'
    ? new Blob([content], { type: mimeType })
    : content;
  
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = fileName;
  link.click();
  
  // Clean up
  setTimeout(() => URL.revokeObjectURL(url), 100);
};

// ==================== Mock Export Function ====================

export const performExport = async (
  data: Record<string, any>[],
  config: ExportConfig,
  options: ExportOptions = {}
): Promise<{ fileUrl: string; fileName: string; fileSize: number }> => {
  // Simulate export process
  await new Promise((resolve) => setTimeout(resolve, 1000));
  
  let content: string | Blob;
  let mimeType: string;
  let extension: string;
  
  switch (config.format) {
    case 'csv':
      content = exportToCSV(data, config, options);
      mimeType = 'text/csv';
      extension = 'csv';
      break;
    case 'json':
      content = exportToJSON(data, config, options);
      mimeType = 'application/json';
      extension = 'json';
      break;
    case 'excel':
      content = await exportToExcel(data, config, options);
      mimeType = 'application/vnd.ms-excel';
      extension = 'xlsx';
      break;
    case 'pdf':
      content = await exportToPDF(data, config, options);
      mimeType = 'application/pdf';
      extension = 'pdf';
      break;
    default:
      throw new Error(`Unsupported format: ${config.format}`);
  }
  
  const blob = typeof content === 'string'
    ? new Blob([content], { type: mimeType })
    : content;
  
  const fileUrl = URL.createObjectURL(blob);
  const fileName = `${config.dataType}_export_${Date.now()}.${extension}`;
  const fileSize = blob.size;
  
  return { fileUrl, fileName, fileSize };
};

// ==================== File Size Estimation ====================

export const estimateFileSize = (
  dataCount: number,
  fieldsCount: number,
  format: string
): number => {
  // Rough estimation based on format
  const bytesPerField = 20; // Average field size
  const overhead = {
    csv: 1.2,
    json: 2.5,
    excel: 1.5,
    pdf: 3.0,
  };
  
  const multiplier = overhead[format as keyof typeof overhead] || 1;
  return Math.round(dataCount * fieldsCount * bytesPerField * multiplier);
};
