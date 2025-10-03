/**
 * Компонент шапки приложения
 */

import React from 'react';
import { Navbar, Nav, Container } from 'react-bootstrap';
import { Link, useLocation } from 'react-router-dom';
import { useAppStore } from '../../store';
import { StatusBadge } from '../ui';
import './Header.css';

export const Header: React.FC = () => {
  const location = useLocation();
  const { isConnected, engineStatus, lastHeartbeat } = useAppStore();

  const getConnectionStatus = () => {
    if (!isConnected) return { text: 'Disconnected', variant: 'danger' as const };
    if (!lastHeartbeat) return { text: 'Connecting', variant: 'warning' as const };
    
    const timeSinceHeartbeat = Date.now() - lastHeartbeat;
    if (timeSinceHeartbeat > 30000) return { text: 'Stale', variant: 'warning' as const };
    
    return { text: 'Connected', variant: 'success' as const };
  };

  const connectionStatus = getConnectionStatus();

  return (
    <Navbar bg="white" expand="lg" className="border-bottom shadow-sm">
      <Container fluid>
        <Navbar.Brand as={Link} to="/dashboard" className="fw-bold">
          Breakout Bot
        </Navbar.Brand>
        
        <Navbar.Toggle aria-controls="basic-navbar-nav" />
        
        <Navbar.Collapse id="basic-navbar-nav">
          <Nav className="me-auto navigation-tabs">
            <Nav.Link as={Link} to="/dashboard" active={location.pathname === '/dashboard'}>
              Dashboard
            </Nav.Link>
            <Nav.Link as={Link} to="/engine" active={location.pathname === '/engine'}>
              Engine
            </Nav.Link>
            <Nav.Link as={Link} to="/trading" active={location.pathname === '/trading'}>
              Trading
            </Nav.Link>
            <Nav.Link as={Link} to="/scanner" active={location.pathname === '/scanner'}>
              Scanner
            </Nav.Link>
            <Nav.Link as={Link} to="/performance" active={location.pathname === '/performance'}>
              Performance
            </Nav.Link>
            <Nav.Link as={Link} to="/logs" active={location.pathname === '/logs'}>
              Logs
            </Nav.Link>
            <Nav.Link as={Link} to="/presets" active={location.pathname === '/presets'}>
              Presets
            </Nav.Link>
            <Nav.Link as={Link} to="/monitoring" active={location.pathname === '/monitoring'}>
              Monitoring
            </Nav.Link>
          </Nav>
          
          <Nav className="ms-auto">
            <Nav.Item className="d-flex align-items-center me-3">
              <span className="me-2">Status:</span>
              <StatusBadge 
                status={connectionStatus.text} 
                variant={connectionStatus.variant}
              />
            </Nav.Item>
            
            {engineStatus && (
              <Nav.Item className="d-flex align-items-center">
                <span className="me-2">Engine:</span>
                <StatusBadge 
                  status={engineStatus.state} 
                  variant={engineStatus.state === 'RUNNING' ? 'success' : 'secondary'}
                />
              </Nav.Item>
            )}
          </Nav>
        </Navbar.Collapse>
      </Container>
    </Navbar>
  );
};


