/**
 * Breadcrumbs Component
 * Shows navigation path: Group > Item
 */

import React from 'react';
import { Breadcrumb } from 'react-bootstrap';
import { Link, useLocation } from 'react-router-dom';
import { getActiveGroup, getActiveItem } from '../../constants/navigation';
import './Breadcrumbs.css';

export const Breadcrumbs: React.FC = () => {
  const location = useLocation();
  const activeGroup = getActiveGroup(location.pathname);
  const activeItem = getActiveItem(location.pathname);

  // Don't show breadcrumbs on dashboard (single-item group)
  if (!activeGroup || activeGroup.items.length === 1) {
    return null;
  }

  return (
    <div className="breadcrumbs-container">
      <Breadcrumb>
        <Breadcrumb.Item
          linkAs={Link}
          linkProps={{ to: activeGroup.path }}
          active={location.pathname === activeGroup.path}
        >
          <span className="breadcrumb-icon">{activeGroup.icon}</span>
          {activeGroup.label}
        </Breadcrumb.Item>
        
        {activeItem && location.pathname !== activeGroup.path && (
          <Breadcrumb.Item active>
            {activeItem.icon && <span className="breadcrumb-icon">{activeItem.icon}</span>}
            {activeItem.label}
          </Breadcrumb.Item>
        )}
      </Breadcrumb>
    </div>
  );
};

export default Breadcrumbs;
