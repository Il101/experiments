/**
 * Export Dialog Component
 * Main dialog for configuring and triggering exports
 */

import React, { useState, useEffect } from 'react';
import { X, Download, FileText, Calendar, Settings, ChevronDown } from 'lucide-react';
import { useExportStore } from '../../store/useExportStore';
import type { ExportFormat, ExportDataType, ExportConfig } from '../../types/export';
import { FieldSelector } from './FieldSelector';
import { DateRangePicker } from './DateRangePicker';

interface ExportDialogProps {
  dataType: ExportDataType;
  defaultItemIds?: string[];
  onClose?: () => void;
}

export const ExportDialog: React.FC<ExportDialogProps> = ({
  dataType,
  defaultItemIds,
  onClose,
}) => {
  const { exportDialogOpen, closeExportDialog, templates, createExport, selectedTemplate, getTemplate } = useExportStore();
  
  const [format, setFormat] = useState<ExportFormat>('csv');
  const [fileName, setFileName] = useState('');
  const [selectedFields, setSelectedFields] = useState<string[]>([]);
  const [dateRange, setDateRange] = useState<{ start: string; end: string } | null>(null);
  const [includeCharts, setIncludeCharts] = useState(false);
  const [includeStatistics, setIncludeStatistics] = useState(false);
  const [useTemplate, setUseTemplate] = useState(false);
  const [templateId, setTemplateId] = useState<string>('');
  const [isExporting, setIsExporting] = useState(false);
  
  // Load template if selected
  useEffect(() => {
    if (selectedTemplate) {
      const template = getTemplate(selectedTemplate);
      if (template) {
        setFormat(template.format);
        setSelectedFields(template.fields);
        setIncludeCharts(template.includeCharts);
        setIncludeStatistics(template.includeStatistics);
        setUseTemplate(true);
        setTemplateId(template.id);
      }
    }
  }, [selectedTemplate, getTemplate]);
  
  // Generate default filename
  useEffect(() => {
    const date = new Date().toISOString().split('T')[0];
    setFileName(`${dataType}_export_${date}.${format}`);
  }, [dataType, format]);
  
  // Available fields based on data type
  const availableFields: Record<ExportDataType, Array<{ key: string; label: string }>> = {
    positions: [
      { key: 'symbol', label: 'Symbol' },
      { key: 'side', label: 'Side' },
      { key: 'size', label: 'Size' },
      { key: 'entryPrice', label: 'Entry Price' },
      { key: 'currentPrice', label: 'Current Price' },
      { key: 'pnl', label: 'P&L' },
      { key: 'roi', label: 'ROI %' },
      { key: 'margin', label: 'Margin' },
      { key: 'leverage', label: 'Leverage' },
      { key: 'liquidationPrice', label: 'Liquidation Price' },
      { key: 'tags', label: 'Tags' },
    ],
    trades: [
      { key: 'symbol', label: 'Symbol' },
      { key: 'side', label: 'Side' },
      { key: 'entryTime', label: 'Entry Time' },
      { key: 'exitTime', label: 'Exit Time' },
      { key: 'entryPrice', label: 'Entry Price' },
      { key: 'exitPrice', label: 'Exit Price' },
      { key: 'size', label: 'Size' },
      { key: 'pnl', label: 'P&L' },
      { key: 'commission', label: 'Commission' },
      { key: 'duration', label: 'Duration' },
      { key: 'tags', label: 'Tags' },
    ],
    alerts: [
      { key: 'name', label: 'Name' },
      { key: 'type', label: 'Type' },
      { key: 'conditions', label: 'Conditions' },
      { key: 'actions', label: 'Actions' },
      { key: 'priority', label: 'Priority' },
      { key: 'enabled', label: 'Enabled' },
      { key: 'triggerCount', label: 'Trigger Count' },
      { key: 'lastTriggered', label: 'Last Triggered' },
    ],
    analytics: [
      { key: 'date', label: 'Date' },
      { key: 'totalPnL', label: 'Total P&L' },
      { key: 'trades', label: 'Trades' },
      { key: 'winRate', label: 'Win Rate' },
      { key: 'profitFactor', label: 'Profit Factor' },
      { key: 'sharpeRatio', label: 'Sharpe Ratio' },
      { key: 'maxDrawdown', label: 'Max Drawdown' },
    ],
    performance: [
      { key: 'period', label: 'Period' },
      { key: 'return', label: 'Return' },
      { key: 'volatility', label: 'Volatility' },
      { key: 'sharpe', label: 'Sharpe Ratio' },
      { key: 'maxDD', label: 'Max Drawdown' },
      { key: 'winRate', label: 'Win Rate' },
    ],
  };
  
  const relevantTemplates = templates.filter((t) => t.dataType === dataType);
  
  const handleExport = async () => {
    setIsExporting(true);
    
    try {
      const config: ExportConfig = {
        format,
        dataType,
        itemIds: defaultItemIds,
        fields: selectedFields.length > 0 ? selectedFields : undefined,
        dateRange: dateRange || undefined,
        includeCharts: format === 'pdf' ? includeCharts : false,
        includeStatistics,
        templateId: useTemplate ? templateId : undefined,
      };
      
      await createExport({ config });
      
      // Close dialog after short delay
      setTimeout(() => {
        setIsExporting(false);
        closeExportDialog();
        onClose?.();
      }, 500);
    } catch (error) {
      console.error('Export failed:', error);
      setIsExporting(false);
    }
  };
  
  if (!exportDialogOpen) return null;
  
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="w-full max-w-2xl rounded-lg bg-white p-6 shadow-xl dark:bg-gray-900">
        {/* Header */}
        <div className="mb-6 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-50 dark:bg-blue-900/20">
              <Download className="h-5 w-5 text-blue-600 dark:text-blue-400" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
                Export {dataType.charAt(0).toUpperCase() + dataType.slice(1)}
              </h2>
              <p className="text-sm text-gray-500 dark:text-gray-400">
                Configure export settings and download data
              </p>
            </div>
          </div>
          <button
            onClick={() => {
              closeExportDialog();
              onClose?.();
            }}
            className="rounded-lg p-2 text-gray-400 hover:bg-gray-100 hover:text-gray-600 dark:hover:bg-gray-800"
          >
            <X className="h-5 w-5" />
          </button>
        </div>
        
        {/* Template Selection */}
        {relevantTemplates.length > 0 && (
          <div className="mb-6">
            <label className="mb-2 flex items-center gap-2 text-sm font-medium text-gray-700 dark:text-gray-300">
              <FileText className="h-4 w-4" />
              Use Template (Optional)
            </label>
            <div className="flex items-center gap-3">
              <input
                type="checkbox"
                checked={useTemplate}
                onChange={(e) => setUseTemplate(e.target.checked)}
                className="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
              />
              <div className="relative flex-1">
                <select
                  value={templateId}
                  onChange={(e) => {
                    setTemplateId(e.target.value);
                    const template = getTemplate(e.target.value);
                    if (template) {
                      setFormat(template.format);
                      setSelectedFields(template.fields);
                      setIncludeCharts(template.includeCharts);
                      setIncludeStatistics(template.includeStatistics);
                    }
                  }}
                  disabled={!useTemplate}
                  className="w-full rounded-lg border border-gray-300 bg-white px-4 py-2 pr-10 text-sm text-gray-900 focus:border-blue-500 focus:ring-blue-500 disabled:bg-gray-100 disabled:text-gray-500 dark:border-gray-600 dark:bg-gray-800 dark:text-white dark:disabled:bg-gray-700"
                >
                  <option value="">Select a template...</option>
                  {relevantTemplates.map((template) => (
                    <option key={template.id} value={template.id}>
                      {template.name}
                    </option>
                  ))}
                </select>
                <ChevronDown className="pointer-events-none absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
              </div>
            </div>
          </div>
        )}
        
        {/* Format Selection */}
        <div className="mb-6">
          <label className="mb-2 block text-sm font-medium text-gray-700 dark:text-gray-300">
            Export Format
          </label>
          <div className="grid grid-cols-4 gap-3">
            {(['csv', 'json', 'excel', 'pdf'] as ExportFormat[]).map((fmt) => (
              <button
                key={fmt}
                onClick={() => setFormat(fmt)}
                className={`rounded-lg border-2 p-3 text-center text-sm font-medium transition-colors ${
                  format === fmt
                    ? 'border-blue-500 bg-blue-50 text-blue-700 dark:bg-blue-900/20 dark:text-blue-300'
                    : 'border-gray-200 bg-white text-gray-700 hover:border-gray-300 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-300'
                }`}
              >
                {fmt.toUpperCase()}
              </button>
            ))}
          </div>
        </div>
        
        {/* File Name */}
        <div className="mb-6">
          <label className="mb-2 block text-sm font-medium text-gray-700 dark:text-gray-300">
            File Name
          </label>
          <input
            type="text"
            value={fileName}
            onChange={(e) => setFileName(e.target.value)}
            className="w-full rounded-lg border border-gray-300 px-4 py-2 text-sm text-gray-900 focus:border-blue-500 focus:ring-blue-500 dark:border-gray-600 dark:bg-gray-800 dark:text-white"
          />
        </div>
        
        {/* Field Selection */}
        <div className="mb-6">
          <FieldSelector
            fields={availableFields[dataType]}
            selectedFields={selectedFields}
            onChange={setSelectedFields}
          />
        </div>
        
        {/* Date Range */}
        <div className="mb-6">
          <label className="mb-2 flex items-center gap-2 text-sm font-medium text-gray-700 dark:text-gray-300">
            <Calendar className="h-4 w-4" />
            Date Range (Optional)
          </label>
          <DateRangePicker value={dateRange} onChange={setDateRange} />
        </div>
        
        {/* Options */}
        <div className="mb-6">
          <label className="mb-2 flex items-center gap-2 text-sm font-medium text-gray-700 dark:text-gray-300">
            <Settings className="h-4 w-4" />
            Options
          </label>
          <div className="space-y-2">
            {format === 'pdf' && (
              <label className="flex items-center gap-2 text-sm text-gray-700 dark:text-gray-300">
                <input
                  type="checkbox"
                  checked={includeCharts}
                  onChange={(e) => setIncludeCharts(e.target.checked)}
                  className="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                />
                Include Charts
              </label>
            )}
            <label className="flex items-center gap-2 text-sm text-gray-700 dark:text-gray-300">
              <input
                type="checkbox"
                checked={includeStatistics}
                onChange={(e) => setIncludeStatistics(e.target.checked)}
                className="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
              />
              Include Statistics
            </label>
          </div>
        </div>
        
        {/* Footer */}
        <div className="flex items-center justify-end gap-3 border-t border-gray-200 pt-6 dark:border-gray-700">
          <button
            onClick={() => {
              closeExportDialog();
              onClose?.();
            }}
            className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 dark:border-gray-600 dark:text-gray-300 dark:hover:bg-gray-800"
          >
            Cancel
          </button>
          <button
            onClick={handleExport}
            disabled={isExporting || !fileName}
            className="flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:bg-gray-400"
          >
            <Download className="h-4 w-4" />
            {isExporting ? 'Exporting...' : 'Export'}
          </button>
        </div>
      </div>
    </div>
  );
};
