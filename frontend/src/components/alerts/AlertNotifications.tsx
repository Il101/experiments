/**
 * AlertNotifications Component
 * Display recent alert notifications
 */

import React from 'react';
import { Bell, BellOff, X, Check } from 'lucide-react';
import { useAlertStore } from '../../store/useAlertStore';
import type { AlertPriority } from '../../types/alerts';

// ==================== Component ====================

export const AlertNotifications: React.FC = () => {
  const {
    notifications,
    markNotificationRead,
    dismissNotification,
    clearNotifications,
  } = useAlertStore();

  const unreadCount = notifications.filter((n) => !n.read && !n.dismissed).length;

  const getPriorityColor = (priority: AlertPriority) => {
    switch (priority) {
      case 'low':
        return 'border-l-gray-400 dark:border-l-gray-600';
      case 'medium':
        return 'border-l-blue-500 dark:border-l-blue-400';
      case 'high':
        return 'border-l-orange-500 dark:border-l-orange-400';
      case 'critical':
        return 'border-l-red-500 dark:border-l-red-400';
    }
  };

  const formatTime = (timestamp: string) => {
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;
    return date.toLocaleDateString();
  };

  const visibleNotifications = notifications.filter((n) => !n.dismissed);

  if (visibleNotifications.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-12 px-4">
        <div className="w-16 h-16 bg-gray-100 dark:bg-gray-800 rounded-full flex items-center justify-center mb-4">
          <BellOff className="w-8 h-8 text-gray-400 dark:text-gray-600" />
        </div>
        <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-2">
          No Notifications
        </h3>
        <p className="text-sm text-gray-600 dark:text-gray-400 text-center max-w-sm">
          You're all caught up! Alert notifications will appear here when triggered.
        </p>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 dark:border-gray-700">
        <div>
          <h2 className="text-xl font-bold text-gray-900 dark:text-gray-100">
            Notifications
          </h2>
          {unreadCount > 0 && (
            <p className="text-sm text-gray-600 dark:text-gray-400">
              {unreadCount} unread notification{unreadCount !== 1 ? 's' : ''}
            </p>
          )}
        </div>
        
        {visibleNotifications.length > 0 && (
          <button
            onClick={clearNotifications}
            className="text-sm text-blue-600 dark:text-blue-400 hover:text-blue-700 dark:hover:text-blue-300 font-medium"
          >
            Clear All
          </button>
        )}
      </div>

      {/* Notifications List */}
      <div className="flex-1 overflow-y-auto">
        <div className="divide-y divide-gray-200 dark:divide-gray-700">
          {visibleNotifications.map((notification) => (
            <div
              key={notification.id}
              className={`p-4 border-l-4 ${getPriorityColor(notification.priority)} ${
                !notification.read
                  ? 'bg-blue-50 dark:bg-blue-900/10'
                  : 'bg-white dark:bg-gray-900'
              } hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors`}
            >
              <div className="flex items-start gap-3">
                {/* Icon */}
                <div className={`p-2 rounded-lg ${
                  notification.priority === 'critical'
                    ? 'bg-red-100 dark:bg-red-900/30 text-red-600 dark:text-red-400'
                    : notification.priority === 'high'
                    ? 'bg-orange-100 dark:bg-orange-900/30 text-orange-600 dark:text-orange-400'
                    : 'bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400'
                }`}>
                  <Bell className="w-4 h-4" />
                </div>

                {/* Content */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-start justify-between gap-2 mb-1">
                    <h4 className="text-sm font-semibold text-gray-900 dark:text-gray-100">
                      {notification.title}
                    </h4>
                    <span className="text-xs text-gray-500 dark:text-gray-400 whitespace-nowrap">
                      {formatTime(notification.createdAt)}
                    </span>
                  </div>
                  
                  <p className="text-sm text-gray-600 dark:text-gray-400 mb-2">
                    {notification.message}
                  </p>

                  <div className="text-xs text-gray-500 dark:text-gray-500">
                    Alert: {notification.alertName}
                  </div>
                </div>

                {/* Actions */}
                <div className="flex items-center gap-1">
                  {!notification.read && (
                    <button
                      onClick={() => markNotificationRead(notification.id)}
                      className="p-1.5 hover:bg-gray-200 dark:hover:bg-gray-700 rounded transition-colors"
                      title="Mark as read"
                    >
                      <Check className="w-4 h-4 text-gray-600 dark:text-gray-400" />
                    </button>
                  )}
                  <button
                    onClick={() => dismissNotification(notification.id)}
                    className="p-1.5 hover:bg-gray-200 dark:hover:bg-gray-700 rounded transition-colors"
                    title="Dismiss"
                  >
                    <X className="w-4 h-4 text-gray-600 dark:text-gray-400" />
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
