/**
 * Alert Store
 * Zustand store for managing alerts, triggers, and preferences
 */

import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type {
  Alert,
  AlertTemplate,
  AlertTrigger,
  AlertNotification,
  AlertPreferences,
  AlertStatistics,
  CreateAlertRequest,
  UpdateAlertRequest,
  AlertCondition,
  AlertAction,
} from '../types/alerts';

// ==================== Store State ====================

interface AlertState {
  // Data
  alerts: Alert[];
  templates: AlertTemplate[];
  triggers: AlertTrigger[];
  notifications: AlertNotification[];
  preferences: AlertPreferences;
  
  // UI State
  selectedAlertId: string | null;
  isAlertBuilderOpen: boolean;
  
  // Loading states
  isLoading: boolean;
  error: string | null;
  
  // Actions - Alerts
  createAlert: (request: CreateAlertRequest) => Promise<Alert>;
  updateAlert: (id: string, request: UpdateAlertRequest) => Promise<Alert>;
  deleteAlert: (id: string) => Promise<void>;
  toggleAlert: (id: string) => void;
  duplicateAlert: (id: string) => Promise<Alert>;
  
  // Actions - Templates
  loadTemplates: () => void;
  createTemplate: (alert: Alert) => Promise<AlertTemplate>;
  deleteTemplate: (id: string) => Promise<void>;
  applyTemplate: (templateId: string) => Promise<Alert>;
  
  // Actions - Triggers
  recordTrigger: (trigger: AlertTrigger) => void;
  loadTriggers: (alertId?: string) => Promise<void>;
  clearTriggers: (alertId?: string) => void;
  
  // Actions - Notifications
  addNotification: (notification: Omit<AlertNotification, 'id' | 'createdAt'>) => void;
  markNotificationRead: (id: string) => void;
  dismissNotification: (id: string) => void;
  clearNotifications: () => void;
  
  // Actions - Preferences
  updatePreferences: (preferences: Partial<AlertPreferences>) => void;
  requestNotificationPermission: () => Promise<boolean>;
  
  // Actions - UI
  setSelectedAlert: (id: string | null) => void;
  openAlertBuilder: () => void;
  closeAlertBuilder: () => void;
  
  // Statistics
  getStatistics: () => AlertStatistics;
}

// ==================== Default Values ====================

const defaultPreferences: AlertPreferences = {
  enabled: true,
  browserNotificationsEnabled: true,
  desktopNotificationsEnabled: false,
  soundEnabled: true,
  emailEnabled: false,
  defaultSound: '/sounds/notification.mp3',
  volume: 0.5,
  showInActivityFeed: true,
  persistNotifications: false,
  notificationDuration: 5,
  quietHoursEnabled: false,
  quietHoursStart: '22:00',
  quietHoursEnd: '08:00',
  quietHoursDays: [],
  emailDigestEnabled: false,
  emailDigestTime: '09:00',
  maxNotificationsPerHour: 20,
  groupSimilarNotifications: true,
};

const builtInTemplates: AlertTemplate[] = [
  {
    id: 'profit-target',
    name: 'Profit Target Reached',
    description: 'Alert when total P&L reaches profit target',
    category: 'profit',
    icon: '💰',
    conditions: [
      {
        type: 'pnl_threshold',
        operator: 'greater_than_or_equal',
        value: 1000,
        label: 'Total P&L >= $1000',
      },
    ],
    actions: [
      {
        type: 'browser_notification',
        config: {
          title: 'Profit Target Reached! 🎉',
          message: 'Your total P&L has reached $1000',
        },
        enabled: true,
      },
      {
        type: 'sound',
        config: {
          soundFile: '/sounds/success.mp3',
          volume: 0.7,
        },
        enabled: true,
      },
    ],
    priority: 'high',
    frequency: 'once',
    customizable: {
      conditions: true,
      actions: true,
      priority: true,
      frequency: true,
    },
    isBuiltIn: true,
    tags: ['profit', 'milestone'],
  },
  {
    id: 'stop-loss-hit',
    name: 'Stop Loss Hit',
    description: 'Alert when position hits stop loss',
    category: 'loss',
    icon: '🛑',
    conditions: [
      {
        type: 'pnl_percent',
        operator: 'less_than_or_equal',
        value: -2,
        label: 'Position P&L <= -2%',
      },
    ],
    actions: [
      {
        type: 'browser_notification',
        config: {
          title: 'Stop Loss Hit',
          message: 'Position has reached stop loss level',
        },
        enabled: true,
      },
      {
        type: 'sound',
        config: {
          soundFile: '/sounds/alert.mp3',
          volume: 0.8,
        },
        enabled: true,
      },
    ],
    priority: 'critical',
    frequency: 'once',
    customizable: {
      conditions: true,
      actions: true,
      priority: false,
      frequency: false,
    },
    isBuiltIn: true,
    tags: ['loss', 'risk'],
  },
  {
    id: 'max-positions',
    name: 'Max Positions Reached',
    description: 'Alert when maximum position count is reached',
    category: 'risk',
    icon: '⚠️',
    conditions: [
      {
        type: 'position_count',
        operator: 'greater_than_or_equal',
        value: 10,
        label: 'Open Positions >= 10',
      },
    ],
    actions: [
      {
        type: 'browser_notification',
        config: {
          title: 'Max Positions Warning',
          message: 'You have reached maximum position count',
        },
        enabled: true,
      },
    ],
    priority: 'medium',
    frequency: 'cooldown',
    customizable: {
      conditions: true,
      actions: true,
      priority: true,
      frequency: true,
    },
    isBuiltIn: true,
    tags: ['risk', 'positions'],
  },
  {
    id: 'win-streak',
    name: 'Win Streak Milestone',
    description: 'Celebrate consecutive winning trades',
    category: 'performance',
    icon: '🔥',
    conditions: [
      {
        type: 'win_streak',
        operator: 'greater_than_or_equal',
        value: 5,
        label: 'Win Streak >= 5',
      },
    ],
    actions: [
      {
        type: 'browser_notification',
        config: {
          title: 'Win Streak! 🔥',
          message: 'You are on a 5-trade winning streak!',
        },
        enabled: true,
      },
      {
        type: 'sound',
        config: {
          soundFile: '/sounds/celebration.mp3',
          volume: 0.6,
        },
        enabled: true,
      },
    ],
    priority: 'low',
    frequency: 'once',
    customizable: {
      conditions: true,
      actions: true,
      priority: true,
      frequency: true,
    },
    isBuiltIn: true,
    tags: ['performance', 'milestone'],
  },
  {
    id: 'daily-loss-limit',
    name: 'Daily Loss Limit',
    description: 'Alert when daily loss limit is reached',
    category: 'risk',
    icon: '🚨',
    conditions: [
      {
        type: 'daily_pnl',
        operator: 'less_than_or_equal',
        value: -500,
        label: 'Daily P&L <= -$500',
      },
    ],
    actions: [
      {
        type: 'browser_notification',
        config: {
          title: 'Daily Loss Limit Reached',
          message: 'Consider stopping trading for today',
        },
        enabled: true,
      },
      {
        type: 'sound',
        config: {
          soundFile: '/sounds/warning.mp3',
          volume: 1.0,
        },
        enabled: true,
      },
      {
        type: 'pause_engine',
        config: {
          reason: 'Daily loss limit reached',
        },
        enabled: false,
      },
    ],
    priority: 'critical',
    frequency: 'once_per_day',
    customizable: {
      conditions: true,
      actions: true,
      priority: false,
      frequency: false,
    },
    isBuiltIn: true,
    tags: ['risk', 'loss', 'daily'],
  },
];

// ==================== Store Implementation ====================

export const useAlertStore = create<AlertState>()(
  persist(
    (set, get) => ({
      // Initial state
      alerts: [],
      templates: builtInTemplates,
      triggers: [],
      notifications: [],
      preferences: defaultPreferences,
      selectedAlertId: null,
      isAlertBuilderOpen: false,
      isLoading: false,
      error: null,

      // ==================== Alert Actions ====================

      createAlert: async (request: CreateAlertRequest) => {
        const newAlert: Alert = {
          id: `alert_${Date.now()}`,
          name: request.name,
          description: request.description,
          conditions: request.conditions.map((c, i) => ({
            ...c,
            id: `condition_${Date.now()}_${i}`,
          })),
          actions: request.actions.map((a, i) => ({
            ...a,
            id: `action_${Date.now()}_${i}`,
          })),
          logicOperator: 'AND',
          priority: request.priority,
          frequency: request.frequency,
          cooldownMinutes: request.cooldownMinutes,
          status: 'active',
          enabled: true,
          createdAt: new Date().toISOString(),
          updatedAt: new Date().toISOString(),
          expiresAt: request.expiresAt,
          triggerCount: 0,
          successCount: 0,
          failureCount: 0,
          tags: request.tags || [],
        };

        set((state) => ({
          alerts: [...state.alerts, newAlert],
        }));

        return newAlert;
      },

      updateAlert: async (id: string, request: UpdateAlertRequest) => {
        set((state) => ({
          alerts: state.alerts.map((alert) => {
            if (alert.id !== id) return alert;
            
            const updated: Alert = {
              ...alert,
              updatedAt: new Date().toISOString(),
            };
            
            if (request.name !== undefined) updated.name = request.name;
            if (request.description !== undefined) updated.description = request.description;
            if (request.priority !== undefined) updated.priority = request.priority;
            if (request.frequency !== undefined) updated.frequency = request.frequency;
            if (request.cooldownMinutes !== undefined) updated.cooldownMinutes = request.cooldownMinutes;
            if (request.enabled !== undefined) updated.enabled = request.enabled;
            if (request.status !== undefined) updated.status = request.status;
            if (request.tags !== undefined) updated.tags = request.tags;
            if (request.expiresAt !== undefined) updated.expiresAt = request.expiresAt;
            
            if (request.conditions) {
              updated.conditions = request.conditions.map((c, i) => ({
                ...(c as AlertCondition),
                id: `condition_${Date.now()}_${i}`,
              }));
            }
            
            if (request.actions) {
              updated.actions = request.actions.map((a, i) => ({
                ...(a as AlertAction),
                id: `action_${Date.now()}_${i}`,
              }));
            }
            
            return updated;
          }),
        }));

        return get().alerts.find((a) => a.id === id)!;
      },

      deleteAlert: async (id: string) => {
        set((state) => ({
          alerts: state.alerts.filter((a) => a.id !== id),
          selectedAlertId: state.selectedAlertId === id ? null : state.selectedAlertId,
        }));
      },

      toggleAlert: (id: string) => {
        set((state) => ({
          alerts: state.alerts.map((alert) =>
            alert.id === id
              ? { ...alert, enabled: !alert.enabled, updatedAt: new Date().toISOString() }
              : alert
          ),
        }));
      },

      duplicateAlert: async (id: string) => {
        const original = get().alerts.find((a) => a.id === id);
        if (!original) throw new Error('Alert not found');

        const duplicate: Alert = {
          ...original,
          id: `alert_${Date.now()}`,
          name: `${original.name} (Copy)`,
          createdAt: new Date().toISOString(),
          updatedAt: new Date().toISOString(),
          triggerCount: 0,
          successCount: 0,
          failureCount: 0,
          lastTriggeredAt: undefined,
        };

        set((state) => ({
          alerts: [...state.alerts, duplicate],
        }));

        return duplicate;
      },

      // ==================== Template Actions ====================

      loadTemplates: () => {
        // Templates are loaded from builtInTemplates by default
        // This method can be extended to load user templates from API
      },

      createTemplate: async (alert: Alert) => {
        const template: AlertTemplate = {
          id: `template_${Date.now()}`,
          name: alert.name,
          description: alert.description || '',
          category: 'custom',
          conditions: alert.conditions.map(({ id, ...rest }) => rest),
          actions: alert.actions.map(({ id, ...rest }) => rest),
          priority: alert.priority,
          frequency: alert.frequency,
          customizable: {
            conditions: true,
            actions: true,
            priority: true,
            frequency: true,
          },
          isBuiltIn: false,
          tags: alert.tags,
        };

        set((state) => ({
          templates: [...state.templates, template],
        }));

        return template;
      },

      deleteTemplate: async (id: string) => {
        set((state) => ({
          templates: state.templates.filter((t) => t.id !== id && !t.isBuiltIn),
        }));
      },

      applyTemplate: async (templateId: string) => {
        const template = get().templates.find((t) => t.id === templateId);
        if (!template) throw new Error('Template not found');

        return get().createAlert({
          name: template.name,
          description: template.description,
          conditions: template.conditions,
          actions: template.actions,
          priority: template.priority,
          frequency: template.frequency,
          tags: template.tags,
        });
      },

      // ==================== Trigger Actions ====================

      recordTrigger: (trigger: AlertTrigger) => {
        set((state) => ({
          triggers: [trigger, ...state.triggers].slice(0, 100), // Keep last 100
          alerts: state.alerts.map((alert) =>
            alert.id === trigger.alertId
              ? {
                  ...alert,
                  triggerCount: alert.triggerCount + 1,
                  successCount:
                    alert.successCount +
                    trigger.actionsExecuted.filter((a) => a.success).length,
                  failureCount:
                    alert.failureCount +
                    trigger.actionsExecuted.filter((a) => !a.success).length,
                  lastTriggeredAt: trigger.triggeredAt,
                }
              : alert
          ),
        }));
      },

      loadTriggers: async (alertId?: string) => {
        // TODO: Load from API
        // For now, triggers are stored in state
        console.log('Loading triggers for alert:', alertId || 'all');
      },

      clearTriggers: (alertId?: string) => {
        set((state) => ({
          triggers: alertId
            ? state.triggers.filter((t) => t.alertId !== alertId)
            : [],
        }));
      },

      // ==================== Notification Actions ====================

      addNotification: (notification) => {
        const newNotification: AlertNotification = {
          ...notification,
          id: `notif_${Date.now()}`,
          createdAt: new Date().toISOString(),
          read: false,
          dismissed: false,
        };

        set((state) => ({
          notifications: [newNotification, ...state.notifications].slice(0, 50),
        }));
      },

      markNotificationRead: (id: string) => {
        set((state) => ({
          notifications: state.notifications.map((n) =>
            n.id === id
              ? { ...n, read: true, readAt: new Date().toISOString() }
              : n
          ),
        }));
      },

      dismissNotification: (id: string) => {
        set((state) => ({
          notifications: state.notifications.map((n) =>
            n.id === id
              ? { ...n, dismissed: true, dismissedAt: new Date().toISOString() }
              : n
          ),
        }));
      },

      clearNotifications: () => {
        set({ notifications: [] });
      },

      // ==================== Preference Actions ====================

      updatePreferences: (preferences) => {
        set((state) => ({
          preferences: { ...state.preferences, ...preferences },
        }));
      },

      requestNotificationPermission: async () => {
        if (!('Notification' in window)) {
          console.warn('Notifications not supported');
          return false;
        }

        if (Notification.permission === 'granted') {
          set((state) => ({
            preferences: { ...state.preferences, browserNotificationsEnabled: true },
          }));
          return true;
        }

        if (Notification.permission !== 'denied') {
          const permission = await Notification.requestPermission();
          const granted = permission === 'granted';
          
          set((state) => ({
            preferences: { ...state.preferences, browserNotificationsEnabled: granted },
          }));
          
          return granted;
        }

        return false;
      },

      // ==================== UI Actions ====================

      setSelectedAlert: (id) => {
        set({ selectedAlertId: id });
      },

      openAlertBuilder: () => {
        set({ isAlertBuilderOpen: true });
      },

      closeAlertBuilder: () => {
        set({ isAlertBuilderOpen: false, selectedAlertId: null });
      },

      // ==================== Statistics ====================

      getStatistics: () => {
        const state = get();
        const now = new Date();
        const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
        const weekAgo = new Date(today.getTime() - 7 * 24 * 60 * 60 * 1000);
        const monthAgo = new Date(today.getTime() - 30 * 24 * 60 * 60 * 1000);

        const triggersToday = state.triggers.filter(
          (t) => new Date(t.triggeredAt) >= today
        ).length;

        const triggersThisWeek = state.triggers.filter(
          (t) => new Date(t.triggeredAt) >= weekAgo
        ).length;

        const triggersThisMonth = state.triggers.filter(
          (t) => new Date(t.triggeredAt) >= monthAgo
        ).length;

        const successCount = state.triggers.reduce(
          (sum, t) => sum + t.actionsExecuted.filter((a) => a.success).length,
          0
        );
        const totalActions = state.triggers.reduce(
          (sum, t) => sum + t.actionsExecuted.length,
          0
        );

        const triggerCountByAlert = state.alerts.map((alert) => ({
          alertId: alert.id,
          alertName: alert.name,
          triggerCount: alert.triggerCount,
        }));

        const mostTriggered = triggerCountByAlert
          .sort((a, b) => b.triggerCount - a.triggerCount)
          .slice(0, 5);

        return {
          totalAlerts: state.alerts.length,
          activeAlerts: state.alerts.filter((a) => a.enabled).length,
          inactiveAlerts: state.alerts.filter((a) => !a.enabled).length,
          totalTriggers: state.triggers.length,
          triggersToday,
          triggersThisWeek,
          triggersThisMonth,
          successRate: totalActions > 0 ? (successCount / totalActions) * 100 : 0,
          averageTriggersPerAlert:
            state.alerts.length > 0
              ? state.triggers.length / state.alerts.length
              : 0,
          mostTriggered,
          recentTriggers: state.triggers.slice(0, 10),
        };
      },
    }),
    {
      name: 'alert-store',
      partialize: (state) => ({
        alerts: state.alerts,
        templates: state.templates.filter((t) => !t.isBuiltIn), // Don't persist built-in templates
        preferences: state.preferences,
      }),
    }
  )
);
