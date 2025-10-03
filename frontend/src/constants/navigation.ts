/**
 * Navigation Groups Configuration
 * Organizing 8 tabs into 4 logical groups
 */

export interface NavigationItem {
  path: string;
  label: string;
  icon?: string;
}

export interface NavigationGroup {
  id: string;
  label: string;
  icon: string;
  path: string; // Primary path for the group
  items: NavigationItem[];
}

export const NAVIGATION_GROUPS: NavigationGroup[] = [
  {
    id: 'overview',
    label: 'Overview',
    icon: '📊',
    path: '/dashboard',
    items: [
      { path: '/dashboard', label: 'Dashboard', icon: '📈' },
    ],
  },
  {
    id: 'trading',
    label: 'Trading',
    icon: '💹',
    path: '/trading',
    items: [
      { path: '/trading', label: 'Positions', icon: '📇' },
      { path: '/trading/orders', label: 'Orders', icon: '📋' },
      { path: '/scanner', label: 'Scanner', icon: '🔍' },
    ],
  },
  {
    id: 'analytics',
    label: 'Analytics',
    icon: '📈',
    path: '/performance',
    items: [
      { path: '/performance', label: 'Performance', icon: '🎯' },
      { path: '/monitoring', label: 'Monitoring', icon: '👁️' },
    ],
  },
  {
    id: 'settings',
    label: 'Settings',
    icon: '⚙️',
    path: '/engine',
    items: [
      { path: '/engine', label: 'Engine', icon: '🤖' },
      { path: '/presets', label: 'Presets', icon: '📝' },
      { path: '/logs', label: 'Logs', icon: '📜' },
    ],
  },
];

/**
 * Get group by path
 */
export const getActiveGroup = (pathname: string): NavigationGroup | undefined => {
  return NAVIGATION_GROUPS.find((group) =>
    group.items.some((item) => pathname.startsWith(item.path))
  );
};

/**
 * Get active item by path
 */
export const getActiveItem = (pathname: string): NavigationItem | undefined => {
  for (const group of NAVIGATION_GROUPS) {
    const item = group.items.find((item) => pathname.startsWith(item.path));
    if (item) return item;
  }
  return undefined;
};

/**
 * Check if path belongs to group
 */
export const isGroupActive = (group: NavigationGroup, pathname: string): boolean => {
  return group.items.some((item) => pathname.startsWith(item.path));
};
