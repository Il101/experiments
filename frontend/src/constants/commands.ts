/**
 * Конфигурация команд управления движком
 * Включает иконки, описания, tooltips и настройки подтверждения
 */

import { TOOLTIPS } from './tooltips';

export interface CommandConfig {
  id: string;
  label: string;
  icon: string;
  tooltip: string;
  variant: 'success' | 'danger' | 'warning' | 'secondary' | 'primary' | 'info';
  requireConfirm: boolean;
  confirmDialog?: {
    title: string;
    message: string;
    confirmText?: string;
    cancelText?: string;
    danger?: boolean;
  };
}

export const COMMAND_CONFIGS: Record<string, CommandConfig> = {
  start: {
    id: 'start',
    label: 'Start',
    icon: '▶️',
    tooltip: TOOLTIPS.CMD_START,
    variant: 'success',
    requireConfirm: false,
  },
  
  stop: {
    id: 'stop',
    label: 'Stop',
    icon: '⏹️',
    tooltip: TOOLTIPS.CMD_STOP,
    variant: 'danger',
    requireConfirm: true,
    confirmDialog: {
      title: 'Остановить бота?',
      message: 'Бот прекратит работу, но НЕ закроет открытые позиции. Для закрытия всех позиций используйте "Panic Exit".',
      confirmText: 'Остановить',
      cancelText: 'Отмена',
      danger: false,
    },
  },
  
  pause: {
    id: 'pause',
    label: 'Pause',
    icon: '⏸️',
    tooltip: TOOLTIPS.CMD_PAUSE,
    variant: 'warning',
    requireConfirm: false,
  },
  
  resume: {
    id: 'resume',
    label: 'Resume',
    icon: '▶️',
    tooltip: TOOLTIPS.CMD_RESUME,
    variant: 'success',
    requireConfirm: false,
  },
  
  reload: {
    id: 'reload',
    label: 'Reload',
    icon: '🔄',
    tooltip: TOOLTIPS.CMD_RELOAD,
    variant: 'info',
    requireConfirm: false,
  },
  
  time_stop: {
    id: 'time_stop',
    label: 'Time Stop',
    icon: '⏱️',
    tooltip: TOOLTIPS.CMD_TIME_STOP,
    variant: 'warning',
    requireConfirm: true,
    confirmDialog: {
      title: 'Остановка по времени',
      message: 'Закрыть все позиции в конце торговой сессии?',
      confirmText: 'Да, активировать',
      cancelText: 'Отмена',
      danger: false,
    },
  },
  
  panic_exit: {
    id: 'panic_exit',
    label: 'Panic Exit',
    icon: '🚨',
    tooltip: TOOLTIPS.CMD_PANIC_EXIT,
    variant: 'danger',
    requireConfirm: true,
    confirmDialog: {
      title: '⚠️ АВАРИЙНЫЙ ВЫХОД',
      message: 'Все позиции будут закрыты НЕМЕДЛЕННО ПО РЫНОЧНОЙ ЦЕНЕ!\n\n' +
               '⚠️ Возможно проскальзывание и незапланированные потери.\n\n' +
               'Используйте только в критических ситуациях!\n\n' +
               'Вы уверены?',
      confirmText: 'Да, закрыть ВСЁ',
      cancelText: 'Отмена',
      danger: true,
    },
  },
  
  kill_switch: {
    id: 'kill_switch',
    label: 'Kill Switch',
    icon: '🔴',
    tooltip: TOOLTIPS.CMD_KILL_SWITCH,
    variant: 'danger',
    requireConfirm: true,
    confirmDialog: {
      title: '🚨 АКТИВИРОВАТЬ KILL SWITCH?',
      message: 'Kill Switch:\n\n' +
               '1. Закроет ВСЕ открытые позиции\n' +
               '2. Заблокирует открытие новых сделок\n' +
               '3. Потребует ручной отмены для возобновления работы\n\n' +
               'Обычно активируется автоматически при достижении лимита просадки.\n\n' +
               'Вы уверены, что хотите активировать вручную?',
      confirmText: 'Да, активировать Kill Switch',
      cancelText: 'Отмена',
      danger: true,
    },
  },
};

/**
 * Получить конфигурацию команды по ID
 */
export function getCommandConfig(commandId: string): CommandConfig | undefined {
  return COMMAND_CONFIGS[commandId.toLowerCase()];
}

/**
 * Проверить, доступна ли команда в текущем состоянии
 */
export function isCommandAvailable(commandId: string, availableCommands: string[]): boolean {
  return availableCommands.map(cmd => cmd.toLowerCase()).includes(commandId.toLowerCase());
}
