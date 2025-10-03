/**
 * Основной layout компонент
 */

import React, { useEffect } from 'react';
import { Outlet } from 'react-router-dom';
import { Container } from 'react-bootstrap';
import { GroupedHeader } from './GroupedHeader';
import { Breadcrumbs } from './Breadcrumbs';
import { useAppStore, useWebSocketStore } from '../../store';
import { useEngineStatus } from '../../hooks';
import './Layout.css';

export const Layout: React.FC = () => {
  const { setEngineStatus, setConnected, setLastHeartbeat } = useAppStore();
  const { connect, disconnect, lastMessage } = useWebSocketStore();
  const { data: engineStatus } = useEngineStatus();

  // Подключение к WebSocket при монтировании
  useEffect(() => {
    connect();
    return () => disconnect();
  }, [connect, disconnect]);

  // Обновление статуса движка при получении данных
  useEffect(() => {
    if (engineStatus) {
      setEngineStatus(engineStatus);
    }
  }, [engineStatus, setEngineStatus]);

  // Обработка WebSocket сообщений
  useEffect(() => {
    if (lastMessage) {
      setLastHeartbeat(lastMessage.ts);
      
      if (lastMessage.type === 'HEARTBEAT') {
        setConnected(true);
      } else if (lastMessage.type === 'ENGINE_UPDATE') {
        setEngineStatus(lastMessage.data);
      }
    }
  }, [lastMessage, setLastHeartbeat, setConnected, setEngineStatus]);

  return (
    <div className="app-container">
      <GroupedHeader />
      <Breadcrumbs />
      <main className="app-main">
        <Container fluid className="app-content">
          <div className="page-container">
            <Outlet />
          </div>
        </Container>
      </main>
    </div>
  );
};


