/**
 * Конфигурация маршрутов приложения
 */

import { createBrowserRouter, Navigate } from 'react-router-dom';
import { Layout } from '../components/layout/Layout';
import { Dashboard } from '../pages/Dashboard';
import { EngineControl } from '../pages/EngineControl';
import { Trading } from '../pages/Trading';
import { Orders } from '../pages/Orders';
import { Scanner } from '../pages/Scanner';
import { Performance } from '../pages/Performance';
import { Logs } from '../pages/Logs';
import { Presets } from '../pages/Presets';
import { Monitoring } from '../pages/Monitoring';
import { NotFound } from '../pages/NotFound';

export const router = createBrowserRouter([
  {
    path: '/',
    element: <Layout />,
    children: [
      {
        index: true,
        element: <Navigate to="/dashboard" replace />,
      },
      {
        path: 'dashboard',
        element: <Dashboard />,
      },
      {
        path: 'engine',
        element: <EngineControl />,
      },
      {
        path: 'trading',
        element: <Trading />,
      },
      {
        path: 'trading/orders',
        element: <Orders />,
      },
      {
        path: 'scanner',
        element: <Scanner />,
      },
      {
        path: 'performance',
        element: <Performance />,
      },
      {
        path: 'logs',
        element: <Logs />,
      },
      {
        path: 'presets',
        element: <Presets />,
      },
      {
        path: 'monitoring',
        element: <Monitoring />,
      },
      {
        path: '*',
        element: <NotFound />,
      },
    ],
  },
]);


