/**
 * Grouped Navigation Header
 * Organized navigation: 8 tabs → 4 groups with sub-navigation
 */

import React, { useState } from 'react';
import { Navbar, Nav, Container, Dropdown } from 'react-bootstrap';
import { Link, useLocation } from 'react-router-dom';
import { useAppStore } from '../../store';
import { StatusBadge } from '../ui';
import { NAVIGATION_GROUPS, getActiveGroup, isGroupActive } from '../../constants/navigation';
import './GroupedHeader.css';

export const GroupedHeader: React.FC = () => {
  const location = useLocation();
  const { isConnected, engineStatus, lastHeartbeat } = useAppStore();
  const [expandedGroup, setExpandedGroup] = useState<string | null>(null);

  const activeGroup = getActiveGroup(location.pathname);

  const getConnectionStatus = () => {
    if (!isConnected) return { text: 'Disconnected', variant: 'danger' as const };
    if (!lastHeartbeat) return { text: 'Connecting', variant: 'warning' as const };
    
    const timeSinceHeartbeat = Date.now() - lastHeartbeat;
    if (timeSinceHeartbeat > 30000) return { text: 'Stale', variant: 'warning' as const };
    
    return { text: 'Connected', variant: 'success' as const };
  };

  const connectionStatus = getConnectionStatus();

  const handleGroupClick = (groupId: string) => {
    setExpandedGroup(expandedGroup === groupId ? null : groupId);
  };

  return (
    <>
      {/* Main Navigation */}
      <Navbar bg="white" expand="lg" className="border-bottom shadow-sm grouped-header">
        <Container fluid>
          <Navbar.Brand as={Link} to="/dashboard" className="fw-bold">
            <span className="brand-icon">🤖</span>
            Breakout Bot
          </Navbar.Brand>
          
          <Navbar.Toggle aria-controls="grouped-navbar-nav" />
          
          <Navbar.Collapse id="grouped-navbar-nav">
            {/* Main Groups */}
            <Nav className="me-auto navigation-groups">
              {NAVIGATION_GROUPS.map((group) => {
                const isActive = isGroupActive(group, location.pathname);
                
                if (group.items.length === 1) {
                  // Single item group - direct link
                  return (
                    <Nav.Link
                      key={group.id}
                      as={Link}
                      to={group.path}
                      className={`nav-group-link ${isActive ? 'active' : ''}`}
                    >
                      <span className="group-icon">{group.icon}</span>
                      <span className="group-label">{group.label}</span>
                    </Nav.Link>
                  );
                }

                // Multi-item group - dropdown
                return (
                  <Dropdown
                    key={group.id}
                    className={`nav-group-dropdown ${isActive ? 'active' : ''}`}
                    show={expandedGroup === group.id}
                    onToggle={() => handleGroupClick(group.id)}
                  >
                    <Dropdown.Toggle
                      as={Nav.Link}
                      className="nav-group-toggle"
                    >
                      <span className="group-icon">{group.icon}</span>
                      <span className="group-label">{group.label}</span>
                      <span className="dropdown-arrow">▾</span>
                    </Dropdown.Toggle>

                    <Dropdown.Menu>
                      {group.items.map((item) => (
                        <Dropdown.Item
                          key={item.path}
                          as={Link}
                          to={item.path}
                          active={location.pathname === item.path}
                          onClick={() => setExpandedGroup(null)}
                        >
                          {item.icon && <span className="item-icon">{item.icon}</span>}
                          {item.label}
                        </Dropdown.Item>
                      ))}
                    </Dropdown.Menu>
                  </Dropdown>
                );
              })}
            </Nav>
            
            {/* Status Indicators */}
            <Nav className="ms-auto status-indicators">
              <Nav.Item className="d-flex align-items-center me-3">
                <span className="status-label">Connection:</span>
                <StatusBadge 
                  status={connectionStatus.text} 
                  variant={connectionStatus.variant}
                />
              </Nav.Item>
              
              {engineStatus && (
                <Nav.Item className="d-flex align-items-center">
                  <span className="status-label">Engine:</span>
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

      {/* Sub-Navigation (Breadcrumb style) */}
      {activeGroup && activeGroup.items.length > 1 && (
        <div className="sub-navigation">
          <Container fluid>
            <Nav className="sub-nav-tabs">
              {activeGroup.items.map((item) => (
                <Nav.Link
                  key={item.path}
                  as={Link}
                  to={item.path}
                  className={location.pathname === item.path ? 'active' : ''}
                >
                  {item.icon && <span className="sub-nav-icon">{item.icon}</span>}
                  {item.label}
                </Nav.Link>
              ))}
            </Nav>
          </Container>
        </div>
      )}
    </>
  );
};

export default GroupedHeader;
