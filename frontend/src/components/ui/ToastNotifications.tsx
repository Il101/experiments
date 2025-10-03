/**
 * Toast Notification Component
 * Simple success/error notifications for user actions
 */

import React from 'react';
import { Toast, ToastContainer } from 'react-bootstrap';

export interface ToastNotification {
  id: string;
  title: string;
  message: string;
  variant: 'success' | 'danger' | 'warning' | 'info';
  icon?: string;
}

export interface ToastNotificationsProps {
  notifications: ToastNotification[];
  onClose: (id: string) => void;
  position?: 'top-end' | 'top-start' | 'bottom-end' | 'bottom-start';
}

export const ToastNotifications: React.FC<ToastNotificationsProps> = ({
  notifications,
  onClose,
  position = 'top-end',
}) => {
  const getBgVariant = (variant: ToastNotification['variant']) => {
    switch (variant) {
      case 'success':
        return 'success';
      case 'danger':
        return 'danger';
      case 'warning':
        return 'warning';
      case 'info':
        return 'info';
      default:
        return 'light';
    }
  };

  return (
    <ToastContainer position={position} className="p-3" style={{ zIndex: 9999 }}>
      {notifications.map((notification) => (
        <Toast
          key={notification.id}
          onClose={() => onClose(notification.id)}
          show={true}
          delay={5000}
          autohide
          bg={getBgVariant(notification.variant)}
        >
          <Toast.Header>
            {notification.icon && (
              <span className="me-2" style={{ fontSize: '1.2rem' }}>
                {notification.icon}
              </span>
            )}
            <strong className="me-auto">{notification.title}</strong>
          </Toast.Header>
          <Toast.Body className={notification.variant === 'success' || notification.variant === 'danger' ? 'text-white' : ''}>
            {notification.message}
          </Toast.Body>
        </Toast>
      ))}
    </ToastContainer>
  );
};

export default ToastNotifications;
