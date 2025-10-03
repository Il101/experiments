/**
 * Alert System Types
 * Comprehensive type definitions for smart alerts
 */

// ==================== Core Alert Types ====================

export type AlertConditionType =
  | 'pnl_threshold'           // P&L reaches threshold
  | 'pnl_percent'             // P&L % reaches threshold
  | 'price_level'             // Price reaches level
  | 'price_change'            // Price change % in timeframe
  | 'time_based'              // Time-based trigger
  | 'position_duration'       // Position open for X time
  | 'drawdown_threshold'      // Drawdown exceeds threshold
  | 'win_streak'              // Win streak reaches count
  | 'loss_streak'             // Loss streak reaches count
  | 'daily_pnl'               // Daily P&L threshold
  | 'risk_exposure'           // Total risk % threshold
  | 'position_count';         // Number of open positions

export type AlertOperator =
  | 'equals'
  | 'not_equals'
  | 'greater_than'
  | 'less_than'
  | 'greater_than_or_equal'
  | 'less_than_or_equal'
  | 'between'
  | 'not_between';

export type AlertActionType =
  | 'browser_notification'    // Browser notification
  | 'desktop_notification'    // Desktop notification (if supported)
  | 'sound'                   // Play sound
  | 'email'                   // Send email
  | 'webhook'                 // Call webhook
  | 'log'                     // Log to console/file
  | 'pause_engine'            // Pause trading engine
  | 'close_position';         // Close specific position

export type AlertPriority = 'low' | 'medium' | 'high' | 'critical';

export type AlertStatus = 'active' | 'inactive' | 'triggered' | 'expired';

export type AlertFrequency =
  | 'once'                    // Trigger once, then disable
  | 'always'                  // Trigger every time condition met
  | 'once_per_session'        // Once per browser session
  | 'once_per_day'            // Once per calendar day
  | 'cooldown';               // With cooldown period

// ==================== Alert Condition ====================

export interface AlertCondition {
  id: string;
  type: AlertConditionType;
  operator: AlertOperator;
  value: number | string | boolean;
  value2?: number | string;     // For 'between' operator
  
  // Optional filters
  symbol?: string;              // Apply to specific symbol
  positionId?: string;          // Apply to specific position
  
  // Metadata
  label?: string;               // Human-readable label
  description?: string;
}

// ==================== Alert Action ====================

export interface AlertAction {
  id: string;
  type: AlertActionType;
  
  // Action-specific configuration
  config: {
    // Browser/Desktop notification
    title?: string;
    message?: string;
    icon?: string;
    
    // Sound
    soundFile?: string;
    volume?: number;            // 0-1
    
    // Email
    emailTo?: string;
    emailSubject?: string;
    emailBody?: string;
    
    // Webhook
    webhookUrl?: string;
    webhookMethod?: 'GET' | 'POST';
    webhookPayload?: Record<string, any>;
    
    // Position action
    positionId?: string;
    reason?: string;
  };
  
  // Metadata
  label?: string;
  enabled: boolean;
}

// ==================== Main Alert ====================

export interface Alert {
  id: string;
  name: string;
  description?: string;
  
  // Conditions (AND logic by default)
  conditions: AlertCondition[];
  logicOperator?: 'AND' | 'OR';   // How to combine conditions
  
  // Actions to perform
  actions: AlertAction[];
  
  // Alert behavior
  priority: AlertPriority;
  frequency: AlertFrequency;
  cooldownMinutes?: number;       // For 'cooldown' frequency
  
  // Status and tracking
  status: AlertStatus;
  enabled: boolean;
  
  // Timestamps
  createdAt: string;
  updatedAt: string;
  lastTriggeredAt?: string;
  expiresAt?: string;             // Optional expiration
  
  // Statistics
  triggerCount: number;
  successCount: number;           // Actions executed successfully
  failureCount: number;           // Actions that failed
  
  // Metadata
  tags?: string[];
  color?: string;
  icon?: string;
}

// ==================== Alert Template ====================

export interface AlertTemplate {
  id: string;
  name: string;
  description: string;
  category: 'profit' | 'loss' | 'risk' | 'time' | 'performance' | 'custom';
  icon?: string;
  
  // Template configuration
  conditions: Omit<AlertCondition, 'id'>[];
  actions: Omit<AlertAction, 'id'>[];
  priority: AlertPriority;
  frequency: AlertFrequency;
  
  // User customization allowed
  customizable: {
    conditions: boolean;
    actions: boolean;
    priority: boolean;
    frequency: boolean;
  };
  
  // Metadata
  isBuiltIn: boolean;           // System template vs user template
  createdBy?: string;
  tags?: string[];
}

// ==================== Alert History ====================

export interface AlertTrigger {
  id: string;
  alertId: string;
  alertName: string;
  
  // When and why triggered
  triggeredAt: string;
  conditionsMet: AlertCondition[];
  
  // Actions performed
  actionsExecuted: {
    actionId: string;
    actionType: AlertActionType;
    success: boolean;
    error?: string;
    executedAt: string;
  }[];
  
  // Context at trigger time
  context: {
    totalPnL?: number;
    positionCount?: number;
    symbolPrice?: Record<string, number>;
    [key: string]: any;
  };
}

// ==================== Alert Notification ====================

export interface AlertNotification {
  id: string;
  alertId: string;
  alertName: string;
  priority: AlertPriority;
  
  // Notification content
  title: string;
  message: string;
  icon?: string;
  color?: string;
  
  // Status
  read: boolean;
  dismissed: boolean;
  
  // Timestamps
  createdAt: string;
  readAt?: string;
  dismissedAt?: string;
  
  // Actions
  actions?: {
    label: string;
    action: () => void;
  }[];
}

// ==================== Alert Statistics ====================

export interface AlertStatistics {
  totalAlerts: number;
  activeAlerts: number;
  inactiveAlerts: number;
  
  // Trigger stats
  totalTriggers: number;
  triggersToday: number;
  triggersThisWeek: number;
  triggersThisMonth: number;
  
  // Success rate
  successRate: number;            // %
  averageTriggersPerAlert: number;
  
  // Most active alerts
  mostTriggered: {
    alertId: string;
    alertName: string;
    triggerCount: number;
  }[];
  
  // Recent activity
  recentTriggers: AlertTrigger[];
}

// ==================== Alert Preferences ====================

export interface AlertPreferences {
  // Global settings
  enabled: boolean;
  
  // Notification permissions
  browserNotificationsEnabled: boolean;
  desktopNotificationsEnabled: boolean;
  soundEnabled: boolean;
  emailEnabled: boolean;
  
  // Sound settings
  defaultSound: string;
  volume: number;                 // 0-1
  
  // Notification behavior
  showInActivityFeed: boolean;
  persistNotifications: boolean;  // Keep until dismissed
  notificationDuration: number;   // Seconds
  
  // Quiet hours
  quietHoursEnabled: boolean;
  quietHoursStart: string;        // HH:mm format
  quietHoursEnd: string;          // HH:mm format
  quietHoursDays: number[];       // 0-6 (Sun-Sat)
  
  // Email settings
  emailAddress?: string;
  emailDigestEnabled: boolean;    // Daily digest instead of individual
  emailDigestTime: string;        // HH:mm format
  
  // Advanced
  maxNotificationsPerHour: number;
  groupSimilarNotifications: boolean;
  autoMarkReadAfterSeconds?: number;
}

// ==================== Alert Builder State ====================

export interface AlertBuilderState {
  // Current alert being built
  name: string;
  description: string;
  conditions: AlertCondition[];
  actions: AlertAction[];
  priority: AlertPriority;
  frequency: AlertFrequency;
  cooldownMinutes?: number;
  
  // Builder state
  currentStep: 'conditions' | 'actions' | 'settings' | 'review';
  isValid: boolean;
  errors: Record<string, string>;
  
  // Template usage
  fromTemplate?: string;          // Template ID if using template
}

// ==================== Helper Types ====================

export interface ConditionOption {
  type: AlertConditionType;
  label: string;
  description: string;
  icon?: string;
  category: 'profit' | 'loss' | 'risk' | 'time' | 'performance';
  
  // What operators are valid
  validOperators: AlertOperator[];
  
  // Value type
  valueType: 'number' | 'percent' | 'duration' | 'count' | 'price';
  valueUnit?: string;
  
  // Min/max constraints
  minValue?: number;
  maxValue?: number;
}

export interface ActionOption {
  type: AlertActionType;
  label: string;
  description: string;
  icon?: string;
  category: 'notify' | 'action' | 'integration';
  
  // Required permissions
  requiresPermission?: 'notifications' | 'email';
  
  // Configuration fields
  configFields: {
    name: string;
    label: string;
    type: 'text' | 'number' | 'select' | 'textarea' | 'url';
    required: boolean;
    placeholder?: string;
    options?: { value: string; label: string }[];
  }[];
}

// ==================== API Types ====================

export interface CreateAlertRequest {
  name: string;
  description?: string;
  conditions: Omit<AlertCondition, 'id'>[];
  actions: Omit<AlertAction, 'id'>[];
  priority: AlertPriority;
  frequency: AlertFrequency;
  cooldownMinutes?: number;
  expiresAt?: string;
  tags?: string[];
}

export interface UpdateAlertRequest extends Partial<CreateAlertRequest> {
  enabled?: boolean;
  status?: AlertStatus;
}

export interface AlertsQuery {
  status?: AlertStatus;
  priority?: AlertPriority;
  enabled?: boolean;
  tags?: string[];
  search?: string;
  sortBy?: 'name' | 'createdAt' | 'lastTriggeredAt' | 'triggerCount';
  sortOrder?: 'asc' | 'desc';
  limit?: number;
  offset?: number;
}

export interface AlertTriggersQuery {
  alertId?: string;
  startDate?: string;
  endDate?: string;
  limit?: number;
  offset?: number;
}
