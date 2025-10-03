/**
 * AlertBuilder Component
 * Multi-step form for creating and editing alerts
 */

import React, { useState } from 'react';
import { X, Plus, Trash2, AlertCircle, Check } from 'lucide-react';
import { useAlertStore } from '../../store/useAlertStore';
import type {
  AlertCondition,
  AlertAction,
  AlertPriority,
  AlertFrequency,
  CreateAlertRequest,
} from '../../types/alerts';

// ==================== Component ====================

interface AlertBuilderProps {
  onClose?: () => void;
}

export const AlertBuilder: React.FC<AlertBuilderProps> = ({ onClose }) => {
  const { isAlertBuilderOpen, closeAlertBuilder, createAlert } = useAlertStore();
  
  const handleClose = () => {
    if (onClose) {
      onClose();
    } else {
      closeAlertBuilder();
    }
  };
  
  // Form state
  const [step, setStep] = useState<'basic' | 'conditions' | 'actions' | 'settings'>('basic');
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [conditions, setConditions] = useState<Omit<AlertCondition, 'id'>[]>([]);
  const [actions, setActions] = useState<Omit<AlertAction, 'id'>[]>([]);
  const [priority, setPriority] = useState<AlertPriority>('medium');
  const [frequency, setFrequency] = useState<AlertFrequency>('always');
  const [cooldownMinutes, setCooldownMinutes] = useState<number>(5);
  
  // Validation
  const [errors, setErrors] = useState<Record<string, string>>({});
  
  if (!isAlertBuilderOpen) return null;

  const validateStep = (): boolean => {
    const newErrors: Record<string, string> = {};
    
    if (step === 'basic') {
      if (!name.trim()) newErrors.name = 'Name is required';
    }
    
    if (step === 'conditions') {
      if (conditions.length === 0) newErrors.conditions = 'At least one condition is required';
    }
    
    if (step === 'actions') {
      if (actions.length === 0) newErrors.actions = 'At least one action is required';
    }
    
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleNext = () => {
    if (!validateStep()) return;
    
    if (step === 'basic') setStep('conditions');
    else if (step === 'conditions') setStep('actions');
    else if (step === 'actions') setStep('settings');
  };

  const handleBack = () => {
    if (step === 'settings') setStep('actions');
    else if (step === 'actions') setStep('conditions');
    else if (step === 'conditions') setStep('basic');
  };

  const handleSubmit = async () => {
    if (!validateStep()) return;
    
    const request: CreateAlertRequest = {
      name,
      description,
      conditions,
      actions,
      priority,
      frequency,
      cooldownMinutes: frequency === 'cooldown' ? cooldownMinutes : undefined,
    };
    
    try {
      await createAlert(request);
      handleClose();
      resetForm();
    } catch (error) {
      console.error('Failed to create alert:', error);
      setErrors({ submit: 'Failed to create alert' });
    }
  };

  const resetForm = () => {
    setName('');
    setDescription('');
    setConditions([]);
    setActions([]);
    setPriority('medium');
    setFrequency('always');
    setCooldownMinutes(5);
    setErrors({});
    setStep('basic');
  };

  const addCondition = () => {
    setConditions([
      ...conditions,
      {
        type: 'pnl_threshold',
        operator: 'greater_than_or_equal',
        value: 0,
      },
    ]);
  };

  const removeCondition = (index: number) => {
    setConditions(conditions.filter((_, i) => i !== index));
  };

  const updateCondition = (index: number, updates: Partial<Omit<AlertCondition, 'id'>>) => {
    setConditions(
      conditions.map((c, i) => (i === index ? { ...c, ...updates } : c))
    );
  };

  const addAction = () => {
    setActions([
      ...actions,
      {
        type: 'browser_notification',
        config: {
          title: '',
          message: '',
        },
        enabled: true,
      },
    ]);
  };

  const removeAction = (index: number) => {
    setActions(actions.filter((_, i) => i !== index));
  };

  const updateAction = (index: number, updates: Partial<Omit<AlertAction, 'id'>>) => {
    setActions(
      actions.map((a, i) => (i === index ? { ...a, ...updates } : a))
    );
  };

  // Only show if prop onClose is provided OR isAlertBuilderOpen is true
  if (!onClose && !isAlertBuilderOpen) {
    return null;
  }

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/50 z-40"
        onClick={handleClose}
      />

      {/* Modal */}
      <div className="fixed inset-y-0 right-0 w-full max-w-2xl bg-white dark:bg-gray-900 shadow-xl z-50 flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 dark:border-gray-700">
          <div>
            <h2 className="text-xl font-bold text-gray-900 dark:text-gray-100">
              Create Alert
            </h2>
            <p className="text-sm text-gray-600 dark:text-gray-400">
              Set up custom alerts for trading events
            </p>
          </div>
          <button
            onClick={handleClose}
            className="p-2 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors"
          >
            <X className="w-5 h-5 text-gray-600 dark:text-gray-400" />
          </button>
        </div>

        {/* Progress Steps */}
        <div className="flex items-center px-6 py-4 border-b border-gray-200 dark:border-gray-700">
          {(['basic', 'conditions', 'actions', 'settings'] as const).map((s, i) => (
            <React.Fragment key={s}>
              <div
                className={`flex items-center ${
                  step === s ? 'text-blue-600 dark:text-blue-400' : 'text-gray-400 dark:text-gray-600'
                }`}
              >
                <div
                  className={`w-8 h-8 rounded-full flex items-center justify-center ${
                    step === s
                      ? 'bg-blue-600 text-white'
                      : 'bg-gray-200 dark:bg-gray-700'
                  }`}
                >
                  {i + 1}
                </div>
                <span className="ml-2 text-sm font-medium capitalize">{s}</span>
              </div>
              {i < 3 && (
                <div className="flex-1 h-0.5 bg-gray-200 dark:bg-gray-700 mx-4" />
              )}
            </React.Fragment>
          ))}
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto px-6 py-6">
          {/* Basic Info Step */}
          {step === 'basic' && (
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Alert Name *
                </label>
                <input
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="e.g., Profit Target Reached"
                  className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
                {errors.name && (
                  <p className="mt-1 text-sm text-red-600 dark:text-red-400">
                    {errors.name}
                  </p>
                )}
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Description (Optional)
                </label>
                <textarea
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="Describe what this alert does..."
                  rows={3}
                  className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
              </div>
            </div>
          )}

          {/* Conditions Step */}
          {step === 'conditions' && (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
                  When should this alert trigger?
                </h3>
                <button
                  onClick={addCondition}
                  className="flex items-center gap-2 px-3 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors"
                >
                  <Plus className="w-4 h-4" />
                  <span className="text-sm font-medium">Add Condition</span>
                </button>
              </div>

              {conditions.length === 0 && (
                <div className="flex items-center gap-3 p-4 bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg">
                  <AlertCircle className="w-5 h-5 text-yellow-600 dark:text-yellow-400 flex-shrink-0" />
                  <p className="text-sm text-yellow-800 dark:text-yellow-200">
                    Add at least one condition to define when the alert should trigger
                  </p>
                </div>
              )}

              {conditions.map((condition, index) => (
                <div
                  key={index}
                  className="p-4 border border-gray-200 dark:border-gray-700 rounded-lg space-y-3"
                >
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                      Condition {index + 1}
                    </span>
                    <button
                      onClick={() => removeCondition(index)}
                      className="p-1 hover:bg-red-100 dark:hover:bg-red-900/20 rounded transition-colors"
                    >
                      <Trash2 className="w-4 h-4 text-red-600 dark:text-red-400" />
                    </button>
                  </div>

                  {/* Condition Type */}
                  <div>
                    <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">
                      Type
                    </label>
                    <select
                      value={condition.type}
                      onChange={(e) =>
                        updateCondition(index, {
                          type: e.target.value as any,
                        })
                      }
                      className="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100"
                    >
                      <option value="pnl_threshold">Total P&L Threshold</option>
                      <option value="pnl_percent">P&L Percentage</option>
                      <option value="price_level">Price Level</option>
                      <option value="daily_pnl">Daily P&L</option>
                      <option value="position_count">Position Count</option>
                      <option value="win_streak">Win Streak</option>
                      <option value="loss_streak">Loss Streak</option>
                    </select>
                  </div>

                  {/* Operator */}
                  <div>
                    <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">
                      Operator
                    </label>
                    <select
                      value={condition.operator}
                      onChange={(e) =>
                        updateCondition(index, {
                          operator: e.target.value as any,
                        })
                      }
                      className="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100"
                    >
                      <option value="greater_than">Greater Than</option>
                      <option value="less_than">Less Than</option>
                      <option value="greater_than_or_equal">Greater Than or Equal</option>
                      <option value="less_than_or_equal">Less Than or Equal</option>
                      <option value="equals">Equals</option>
                    </select>
                  </div>

                  {/* Value */}
                  <div>
                    <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">
                      Value
                    </label>
                    <input
                      type="number"
                      value={condition.value as number}
                      onChange={(e) =>
                        updateCondition(index, {
                          value: parseFloat(e.target.value),
                        })
                      }
                      className="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100"
                    />
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Actions Step */}
          {step === 'actions' && (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
                  What should happen when triggered?
                </h3>
                <button
                  onClick={addAction}
                  className="flex items-center gap-2 px-3 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors"
                >
                  <Plus className="w-4 h-4" />
                  <span className="text-sm font-medium">Add Action</span>
                </button>
              </div>

              {actions.length === 0 && (
                <div className="flex items-center gap-3 p-4 bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg">
                  <AlertCircle className="w-5 h-5 text-yellow-600 dark:text-yellow-400 flex-shrink-0" />
                  <p className="text-sm text-yellow-800 dark:text-yellow-200">
                    Add at least one action to define what happens when the alert triggers
                  </p>
                </div>
              )}

              {actions.map((action, index) => (
                <div
                  key={index}
                  className="p-4 border border-gray-200 dark:border-gray-700 rounded-lg space-y-3"
                >
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                      Action {index + 1}
                    </span>
                    <button
                      onClick={() => removeAction(index)}
                      className="p-1 hover:bg-red-100 dark:hover:bg-red-900/20 rounded transition-colors"
                    >
                      <Trash2 className="w-4 h-4 text-red-600 dark:text-red-400" />
                    </button>
                  </div>

                  {/* Action Type */}
                  <div>
                    <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">
                      Type
                    </label>
                    <select
                      value={action.type}
                      onChange={(e) =>
                        updateAction(index, {
                          type: e.target.value as any,
                        })
                      }
                      className="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100"
                    >
                      <option value="browser_notification">Browser Notification</option>
                      <option value="sound">Play Sound</option>
                      <option value="email">Send Email</option>
                      <option value="log">Log Message</option>
                    </select>
                  </div>

                  {/* Notification Config */}
                  {action.type === 'browser_notification' && (
                    <>
                      <div>
                        <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">
                          Title
                        </label>
                        <input
                          type="text"
                          value={action.config.title || ''}
                          onChange={(e) =>
                            updateAction(index, {
                              config: { ...action.config, title: e.target.value },
                            })
                          }
                          placeholder="Alert triggered"
                          className="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100"
                        />
                      </div>
                      <div>
                        <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">
                          Message
                        </label>
                        <textarea
                          value={action.config.message || ''}
                          onChange={(e) =>
                            updateAction(index, {
                              config: { ...action.config, message: e.target.value },
                            })
                          }
                          placeholder="Your alert condition has been met"
                          rows={2}
                          className="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100"
                        />
                      </div>
                    </>
                  )}
                </div>
              ))}
            </div>
          )}

          {/* Settings Step */}
          {step === 'settings' && (
            <div className="space-y-6">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Priority
                </label>
                <div className="grid grid-cols-4 gap-2">
                  {(['low', 'medium', 'high', 'critical'] as const).map((p) => (
                    <button
                      key={p}
                      onClick={() => setPriority(p)}
                      className={`px-3 py-2 rounded-lg text-sm font-medium transition-colors capitalize ${
                        priority === p
                          ? 'bg-blue-600 text-white'
                          : 'bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-700'
                      }`}
                    >
                      {p}
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Frequency
                </label>
                <select
                  value={frequency}
                  onChange={(e) => setFrequency(e.target.value as AlertFrequency)}
                  className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100"
                >
                  <option value="once">Trigger Once (then disable)</option>
                  <option value="always">Always Trigger</option>
                  <option value="once_per_session">Once Per Session</option>
                  <option value="once_per_day">Once Per Day</option>
                  <option value="cooldown">With Cooldown Period</option>
                </select>
              </div>

              {frequency === 'cooldown' && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    Cooldown (Minutes)
                  </label>
                  <input
                    type="number"
                    value={cooldownMinutes}
                    onChange={(e) => setCooldownMinutes(parseInt(e.target.value))}
                    min={1}
                    className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100"
                  />
                </div>
              )}

              {/* Summary */}
              <div className="p-4 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg">
                <div className="flex items-start gap-3">
                  <Check className="w-5 h-5 text-blue-600 dark:text-blue-400 flex-shrink-0 mt-0.5" />
                  <div className="space-y-1">
                    <p className="text-sm font-medium text-blue-900 dark:text-blue-100">
                      Alert Summary
                    </p>
                    <p className="text-sm text-blue-800 dark:text-blue-200">
                      <strong>{name}</strong> will trigger when <strong>{conditions.length}</strong>{' '}
                      condition(s) are met, performing <strong>{actions.length}</strong> action(s) with{' '}
                      <strong>{priority}</strong> priority.
                    </p>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between px-6 py-4 border-t border-gray-200 dark:border-gray-700">
          <button
            onClick={step === 'basic' ? closeAlertBuilder : handleBack}
            className="px-4 py-2 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors"
          >
            {step === 'basic' ? 'Cancel' : 'Back'}
          </button>
          
          <button
            onClick={step === 'settings' ? handleSubmit : handleNext}
            className="px-6 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors font-medium"
          >
            {step === 'settings' ? 'Create Alert' : 'Next'}
          </button>
        </div>
      </div>
    </>
  );
};
