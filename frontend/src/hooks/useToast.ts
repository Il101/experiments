/**
 * Toast Notifications Hook
 * Manages toast notifications state
 */

import { useState, useCallback } from 'react';
import type { ToastNotification } from '../components/ui/ToastNotifications';

export const useToast = () => {
  const [notifications, setNotifications] = useState<ToastNotification[]>([]);

  const showToast = useCallback((
    title: string,
    message: string,
    variant: ToastNotification['variant'] = 'info',
    icon?: string
  ) => {
    const id = `toast-${Date.now()}-${Math.random()}`;
    const notification: ToastNotification = {
      id,
      title,
      message,
      variant,
      icon,
    };
    
    setNotifications((prev) => [...prev, notification]);
    
    // Auto-remove after 5 seconds
    setTimeout(() => {
      removeToast(id);
    }, 5000);
    
    return id;
  }, []);

  const removeToast = useCallback((id: string) => {
    setNotifications((prev) => prev.filter((n) => n.id !== id));
  }, []);

  const showSuccess = useCallback((title: string, message: string) => {
    return showToast(title, message, 'success', '✅');
  }, [showToast]);

  const showError = useCallback((title: string, message: string) => {
    return showToast(title, message, 'danger', '❌');
  }, [showToast]);

  const showWarning = useCallback((title: string, message: string) => {
    return showToast(title, message, 'warning', '⚠️');
  }, [showToast]);

  const showInfo = useCallback((title: string, message: string) => {
    return showToast(title, message, 'info', 'ℹ️');
  }, [showToast]);

  return {
    notifications,
    showToast,
    showSuccess,
    showError,
    showWarning,
    showInfo,
    removeToast,
  };
};
