/**
 * AlertsPage Component
 * Main page for alert management with tabs
 */

import React, { useState } from 'react';
import { Plus, Bell, LayoutTemplate, Clock, Settings } from 'lucide-react';
import { useAlertStore } from '../store/useAlertStore';
import { AlertBuilder } from '../components/alerts/AlertBuilder';
import { AlertList } from '../components/alerts/AlertList';
import { AlertTemplates } from '../components/alerts/AlertTemplates';
import { AlertNotifications } from '../components/alerts/AlertNotifications';
import { AlertStatistics } from '../components/alerts/AlertStatistics';
import { AlertPreferences } from '../components/alerts/AlertPreferences';

// ==================== Types ====================

type TabType = 'alerts' | 'templates' | 'notifications' | 'statistics' | 'preferences';

// ==================== Component ====================

export const AlertsPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState<TabType>('alerts');
  const [builderOpen, setBuilderOpen] = useState(false);
  
  const { notifications, getStatistics } = useAlertStore();
  const stats = getStatistics();
  
  const unreadCount = notifications.filter((n: any) => !n.read && !n.dismissed).length;

  const tabs: Array<{ id: TabType; label: string; icon: any; badge?: number }> = [
    { id: 'alerts', label: 'Alerts', icon: Bell, badge: stats.activeAlerts },
    { id: 'templates', label: 'Templates', icon: LayoutTemplate },
    { id: 'notifications', label: 'Notifications', icon: Bell, badge: unreadCount },
    { id: 'statistics', label: 'Statistics', icon: Clock },
    { id: 'preferences', label: 'Preferences', icon: Settings },
  ];

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 dark:border-gray-700">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
            Smart Alerts
          </h1>
          <p className="text-sm text-gray-600 dark:text-gray-400">
            Set up automated notifications for trading events
          </p>
        </div>
        
        {activeTab === 'alerts' && (
          <button
            onClick={() => setBuilderOpen(true)}
            className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors font-medium"
          >
            <Plus className="w-4 h-4" />
            Create Alert
          </button>
        )}
      </div>

      {/* Stats Cards */}
      <div className="px-6 py-4 bg-gray-50 dark:bg-gray-900/50 border-b border-gray-200 dark:border-gray-700">
        <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
          <div className="bg-white dark:bg-gray-900 p-4 rounded-lg border border-gray-200 dark:border-gray-700">
            <div className="text-sm text-gray-600 dark:text-gray-400 mb-1">
              Total Alerts
            </div>
            <div className="text-2xl font-bold text-gray-900 dark:text-gray-100">
              {stats.totalAlerts}
            </div>
          </div>
          
          <div className="bg-white dark:bg-gray-900 p-4 rounded-lg border border-gray-200 dark:border-gray-700">
            <div className="text-sm text-gray-600 dark:text-gray-400 mb-1">
              Active Now
            </div>
            <div className="text-2xl font-bold text-green-600 dark:text-green-400">
              {stats.activeAlerts}
            </div>
          </div>
          
          <div className="bg-white dark:bg-gray-900 p-4 rounded-lg border border-gray-200 dark:border-gray-700">
            <div className="text-sm text-gray-600 dark:text-gray-400 mb-1">
              Triggers Today
            </div>
            <div className="text-2xl font-bold text-blue-600 dark:text-blue-400">
              {stats.triggersToday}
            </div>
          </div>
          
          <div className="bg-white dark:bg-gray-900 p-4 rounded-lg border border-gray-200 dark:border-gray-700">
            <div className="text-sm text-gray-600 dark:text-gray-400 mb-1">
              Success Rate
            </div>
            <div className="text-2xl font-bold text-purple-600 dark:text-purple-400">
              {stats.successRate.toFixed(0)}%
            </div>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex items-center gap-1 px-6 pt-4 border-b border-gray-200 dark:border-gray-700">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`relative flex items-center gap-2 px-4 py-2 rounded-t-lg font-medium transition-colors ${
              activeTab === tab.id
                ? 'bg-white dark:bg-gray-900 text-blue-600 dark:text-blue-400 border-t border-l border-r border-gray-200 dark:border-gray-700'
                : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200'
            }`}
          >
            <tab.icon className="w-4 h-4" />
            {tab.label}
            {tab.badge !== undefined && tab.badge > 0 && (
              <span className="absolute -top-1 -right-1 w-5 h-5 bg-red-500 text-white text-xs font-bold rounded-full flex items-center justify-center">
                {tab.badge > 99 ? '99+' : tab.badge}
              </span>
            )}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      <div className="flex-1 overflow-y-auto">
        <div className="p-6">
          {activeTab === 'alerts' && <AlertList />}
          {activeTab === 'templates' && <AlertTemplates />}
          {activeTab === 'notifications' && <AlertNotifications />}
          {activeTab === 'statistics' && <AlertStatistics />}
          {activeTab === 'preferences' && <AlertPreferences />}
        </div>
      </div>

      {/* Alert Builder Modal */}
      {builderOpen && <AlertBuilder onClose={() => setBuilderOpen(false)} />}
    </div>
  );
};
