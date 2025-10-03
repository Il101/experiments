/**
 * AlertList Component
 * Display and manage all alerts
 */

import React, { useState } from 'react';
import {
  Bell,
  BellOff,
  Edit,
  Trash2,
  Copy,
  MoreVertical,
  Plus,
  AlertCircle,
  CheckCircle,
  Clock,
  Zap,
} from 'lucide-react';
import { useAlertStore } from '../../store/useAlertStore';
import type { Alert, AlertPriority } from '../../types/alerts';

// ==================== Component ====================

export const AlertList: React.FC = () => {
  const {
    alerts,
    toggleAlert,
    deleteAlert,
    duplicateAlert,
    setSelectedAlert,
    openAlertBuilder,
  } = useAlertStore();

  const [activeMenuId, setActiveMenuId] = useState<string | null>(null);

  const getPriorityColor = (priority: AlertPriority) => {
    switch (priority) {
      case 'low':
        return 'bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300';
      case 'medium':
        return 'bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300';
      case 'high':
        return 'bg-orange-100 dark:bg-orange-900/30 text-orange-700 dark:text-orange-300';
      case 'critical':
        return 'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300';
    }
  };

  const getPriorityIcon = (priority: AlertPriority) => {
    switch (priority) {
      case 'low':
        return <Clock className="w-4 h-4" />;
      case 'medium':
        return <Bell className="w-4 h-4" />;
      case 'high':
        return <AlertCircle className="w-4 h-4" />;
      case 'critical':
        return <Zap className="w-4 h-4" />;
    }
  };

  const getStatusBadge = (alert: Alert) => {
    if (!alert.enabled) {
      return (
        <span className="flex items-center gap-1 px-2 py-1 bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400 rounded text-xs font-medium">
          <BellOff className="w-3 h-3" />
          Disabled
        </span>
      );
    }

    if (alert.triggerCount > 0) {
      return (
        <span className="flex items-center gap-1 px-2 py-1 bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300 rounded text-xs font-medium">
          <CheckCircle className="w-3 h-3" />
          Active
        </span>
      );
    }

    return (
      <span className="flex items-center gap-1 px-2 py-1 bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 rounded text-xs font-medium">
        <Bell className="w-3 h-3" />
        Waiting
      </span>
    );
  };

  const formatFrequency = (alert: Alert) => {
    switch (alert.frequency) {
      case 'once':
        return 'Once';
      case 'always':
        return 'Always';
      case 'once_per_session':
        return 'Once/Session';
      case 'once_per_day':
        return 'Once/Day';
      case 'cooldown':
        return `Cooldown (${alert.cooldownMinutes}m)`;
      default:
        return alert.frequency;
    }
  };

  const handleDelete = async (id: string) => {
    if (confirm('Are you sure you want to delete this alert?')) {
      await deleteAlert(id);
    }
  };

  const handleDuplicate = async (id: string) => {
    await duplicateAlert(id);
  };

  const handleEdit = (id: string) => {
    setSelectedAlert(id);
    openAlertBuilder();
  };

  if (alerts.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-12 px-4">
        <div className="w-16 h-16 bg-gray-100 dark:bg-gray-800 rounded-full flex items-center justify-center mb-4">
          <Bell className="w-8 h-8 text-gray-400 dark:text-gray-600" />
        </div>
        <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-2">
          No Alerts Yet
        </h3>
        <p className="text-sm text-gray-600 dark:text-gray-400 text-center mb-6 max-w-sm">
          Create your first alert to get notified about important trading events
        </p>
        <button
          onClick={openAlertBuilder}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors"
        >
          <Plus className="w-4 h-4" />
          <span className="font-medium">Create Alert</span>
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {alerts.map((alert) => (
        <div
          key={alert.id}
          className={`p-4 border rounded-lg transition-colors ${
            alert.enabled
              ? 'border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900'
              : 'border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900/50 opacity-75'
          }`}
        >
          <div className="flex items-start justify-between mb-3">
            <div className="flex items-start gap-3 flex-1">
              {/* Priority Badge */}
              <div className={`p-2 rounded-lg ${getPriorityColor(alert.priority)}`}>
                {getPriorityIcon(alert.priority)}
              </div>

              {/* Alert Info */}
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <h3 className="text-base font-semibold text-gray-900 dark:text-gray-100 truncate">
                    {alert.name}
                  </h3>
                  {getStatusBadge(alert)}
                </div>

                {alert.description && (
                  <p className="text-sm text-gray-600 dark:text-gray-400 mb-2">
                    {alert.description}
                  </p>
                )}

                {/* Stats */}
                <div className="flex items-center gap-4 text-xs text-gray-500 dark:text-gray-500">
                  <span>
                    {alert.conditions.length} condition{alert.conditions.length !== 1 ? 's' : ''}
                  </span>
                  <span>•</span>
                  <span>
                    {alert.actions.length} action{alert.actions.length !== 1 ? 's' : ''}
                  </span>
                  <span>•</span>
                  <span>{formatFrequency(alert)}</span>
                  {alert.triggerCount > 0 && (
                    <>
                      <span>•</span>
                      <span>Triggered {alert.triggerCount}x</span>
                    </>
                  )}
                </div>
              </div>
            </div>

            {/* Actions Menu */}
            <div className="relative">
              <button
                onClick={() =>
                  setActiveMenuId(activeMenuId === alert.id ? null : alert.id)
                }
                className="p-2 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors"
              >
                <MoreVertical className="w-4 h-4 text-gray-600 dark:text-gray-400" />
              </button>

              {activeMenuId === alert.id && (
                <>
                  {/* Backdrop */}
                  <div
                    className="fixed inset-0 z-10"
                    onClick={() => setActiveMenuId(null)}
                  />

                  {/* Menu */}
                  <div className="absolute right-0 mt-2 w-48 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg z-20 py-1">
                    <button
                      onClick={() => {
                        toggleAlert(alert.id);
                        setActiveMenuId(null);
                      }}
                      className="w-full flex items-center gap-2 px-4 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
                    >
                      {alert.enabled ? (
                        <>
                          <BellOff className="w-4 h-4" />
                          Disable
                        </>
                      ) : (
                        <>
                          <Bell className="w-4 h-4" />
                          Enable
                        </>
                      )}
                    </button>

                    <button
                      onClick={() => {
                        handleEdit(alert.id);
                        setActiveMenuId(null);
                      }}
                      className="w-full flex items-center gap-2 px-4 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
                    >
                      <Edit className="w-4 h-4" />
                      Edit
                    </button>

                    <button
                      onClick={() => {
                        handleDuplicate(alert.id);
                        setActiveMenuId(null);
                      }}
                      className="w-full flex items-center gap-2 px-4 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
                    >
                      <Copy className="w-4 h-4" />
                      Duplicate
                    </button>

                    <div className="border-t border-gray-200 dark:border-gray-700 my-1" />

                    <button
                      onClick={() => {
                        handleDelete(alert.id);
                        setActiveMenuId(null);
                      }}
                      className="w-full flex items-center gap-2 px-4 py-2 text-sm text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors"
                    >
                      <Trash2 className="w-4 h-4" />
                      Delete
                    </button>
                  </div>
                </>
              )}
            </div>
          </div>

          {/* Last Triggered */}
          {alert.lastTriggeredAt && (
            <div className="text-xs text-gray-500 dark:text-gray-500">
              Last triggered:{' '}
              {new Date(alert.lastTriggeredAt).toLocaleString()}
            </div>
          )}
        </div>
      ))}
    </div>
  );
};
