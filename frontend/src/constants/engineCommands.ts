/**
 * Engine Commands Configuration
 * Defines behavior, appearance, and confirmation requirements for all engine commands
 */

import type { CommandConfig } from '../components/ui/CommandButton';

export const ENGINE_COMMANDS: Record<string, CommandConfig> = {
  start: {
    command: 'start',
    label: 'Start Engine',
    icon: '🚀',
    variant: 'success',
    requiresConfirmation: false,
  },
  
  stop: {
    command: 'stop',
    label: 'Stop Engine',
    icon: '⏹️',
    variant: 'danger',
    requiresConfirmation: true,
    confirmTitle: 'Stop Engine',
    confirmMessage: 'Are you sure you want to stop the engine?',
    confirmDetails: [
      'Current scanning cycle will be interrupted',
      'Active orders will remain open',
      'Positions will continue to be managed',
    ],
    confirmVariant: 'warning',
  },
  
  pause: {
    command: 'pause',
    label: 'Pause',
    icon: '⏸️',
    variant: 'warning',
    requiresConfirmation: false,
  },
  
  resume: {
    command: 'resume',
    label: 'Resume',
    icon: '▶️',
    variant: 'success',
    requiresConfirmation: false,
  },
  
  reload: {
    command: 'reload',
    label: 'Reload Config',
    icon: '🔄',
    variant: 'secondary',
    requiresConfirmation: true,
    confirmTitle: 'Reload Configuration',
    confirmMessage: 'This will reload the engine configuration from disk.',
    confirmDetails: [
      'Current configuration will be replaced',
      'Running state will be preserved',
      'Changes may affect active trading logic',
    ],
    confirmVariant: 'warning',
  },
  
  retry: {
    command: 'retry',
    label: 'Retry',
    icon: '🔄',
    variant: 'info',
    requiresConfirmation: false,
  },
  
  time_stop: {
    command: 'time_stop',
    label: 'Time Stop',
    icon: '⏰',
    variant: 'outline-warning',
    requiresConfirmation: true,
    confirmTitle: 'Activate Time Stop',
    confirmMessage: 'This will prevent new positions from being opened.',
    confirmDetails: [
      'No new signals will be executed',
      'Existing positions will continue to be managed',
      'Scanner will continue running',
    ],
    confirmVariant: 'warning',
  },
  
  panic_exit: {
    command: 'panic_exit',
    label: 'Panic Exit',
    icon: '🚨',
    variant: 'outline-danger',
    requiresConfirmation: true,
    confirmTitle: '⚠️ PANIC EXIT',
    confirmMessage: 'This will immediately close ALL open positions at market price!',
    confirmDetails: [
      'ALL positions will be closed with market orders',
      'Stop losses will be ignored',
      'This action cannot be undone',
      'Engine will stop after closing positions',
      'Potential slippage may occur',
    ],
    confirmVariant: 'danger',
  },
  
  kill_switch: {
    command: 'kill_switch',
    label: 'Kill Switch',
    icon: '🔴',
    variant: 'outline-danger',
    requiresConfirmation: true,
    confirmTitle: '🚨 EMERGENCY KILL SWITCH',
    confirmMessage: 'DANGER: This will immediately terminate all engine operations!',
    confirmDetails: [
      'ALL positions will be closed at market price',
      'ALL pending orders will be cancelled',
      'Engine will be fully stopped',
      'This is an EMERGENCY action only',
      'Use only if normal stop is not working',
      'Potential slippage and losses may occur',
    ],
    confirmVariant: 'danger',
  },
};

/**
 * Get command configuration by name
 */
export const getCommandConfig = (command: string): CommandConfig | undefined => {
  return ENGINE_COMMANDS[command.toLowerCase()];
};

/**
 * Check if command requires confirmation
 */
export const requiresConfirmation = (command: string): boolean => {
  const config = getCommandConfig(command);
  return config?.requiresConfirmation ?? false;
};

/**
 * Group commands by category
 */
export const COMMAND_CATEGORIES = {
  primary: ['start', 'stop'],
  control: ['pause', 'resume', 'retry', 'reload'],
  emergency: ['time_stop', 'panic_exit', 'kill_switch'],
};

/**
 * Get commands by category
 */
export const getCommandsByCategory = (category: keyof typeof COMMAND_CATEGORIES): string[] => {
  return COMMAND_CATEGORIES[category];
};

/**
 * Filter available commands by category
 */
export const filterCommandsByCategory = (
  availableCommands: string[],
  category: keyof typeof COMMAND_CATEGORIES
): CommandConfig[] => {
  const categoryCommands = getCommandsByCategory(category);
  return availableCommands
    .filter(cmd => categoryCommands.includes(cmd.toLowerCase()))
    .map(cmd => getCommandConfig(cmd))
    .filter((config): config is CommandConfig => config !== undefined);
};
