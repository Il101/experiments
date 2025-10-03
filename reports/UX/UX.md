📋 ПЛАН ПРАВОК UI/UX — ПО ПРИОРИТЕТУ
🔥 PHASE 1: КРИТИЧЕСКИЕ УЛУЧШЕНИЯ (1-2 недели)
Приоритет: CRITICAL | Effort: Medium
✅ 1.1. Live Activity Feed — показать "что происходит сейчас"
Файлы:

Создать: frontend/src/components/LiveActivityFeed.tsx
Изменить: Dashboard.tsx
Создать API: backend/api/events/stream.py
Задачи:

API endpoint:

✅ 1.2. Tooltip система для всех метрик
Файлы:

Создать: frontend/src/components/ui/Tooltip.tsx
Создать: frontend/src/constants/tooltips.ts
Изменить: все компоненты с метриками
Задачи:

Компоненты для обновления:

Dashboard.tsx (все метрики)
Performance.tsx (графики и статистика)
MetricCard.tsx (добавить проп tooltip)
Trading.tsx (PnL, R-multiple)
✅ 1.3. Карточки позиций вместо таблицы
Файлы:

Создать: frontend/src/components/trading/PositionCard.tsx
Создать: frontend/src/components/trading/PositionVisualProgress.tsx
Изменить: Trading.tsx
Задачи:

Переключатель вида:

✅ 1.4. Группировка навигации — с 8 до 4 вкладок
Файлы:

Изменить: Header.tsx
Изменить: routes.tsx
Создать: подстраницы с табами
Новая структура:

Реализация:

✅ 1.5. Подсказки для кнопок управления Engine
Файлы:

Изменить: EngineControl.tsx
Создать: frontend/src/components/ui/ConfirmDialog.tsx
Задачи:

⚡ PHASE 2: ВАЖНЫЕ УЛУЧШЕНИЯ (2-3 недели)
Приоритет: HIGH | Effort: Medium-High
✅ 2.1. FSM Visualizer с анимацией и прогрессом
Файлы:

Изменить: StateMachineVisualizer.tsx
Добавить: CSS анимации
Задачи:

CSS анимации:

✅ 2.2. Улучшенные логи с группировкой и поиском
Файлы:

Изменить: Logs.tsx
Создать: frontend/src/components/logs/LogEntry.tsx
Создать: frontend/src/components/logs/LogFilters.tsx
Задачи:

CSS:

✅ 2.3. Scanner с объяснениями результатов
Файлы:

Изменить: Scanner.tsx
Создать: frontend/src/components/scanner/ScanResultCard.tsx
Задачи:

✅ 2.4. График Equity с маркерами сделок
Файлы:

Изменить: Performance.tsx
Создать: frontend/src/components/charts/AnnotatedEquityCurve.tsx
Задачи:

🎨 PHASE 3: КАЧЕСТВО ЖИЗНИ (2-3 недели)
Приоритет: MEDIUM | Effort: Low-Medium
✅ 3.1. Система уведомлений
Файлы:

Создать: frontend/src/components/notifications/NotificationCenter.tsx
Создать: frontend/src/components/notifications/Toast.tsx
Создать: frontend/src/hooks/useNotifications.ts
Задачи:

✅ 3.2. Onboarding для новых пользователей
Файлы:

Создать: frontend/src/components/onboarding/WelcomeWizard.tsx
Создать: frontend/src/components/onboarding/steps/*.tsx
Задачи:

Показывать один раз:

✅ 3.3. Горячие клавиши (Keyboard Shortcuts)
Файлы:

Создать: frontend/src/hooks/useKeyboardShortcuts.ts
Создать: frontend/src/components/ShortcutsHelp.tsx
Задачи:

✅ 3.4. Тёмная тема
Файлы:

Создать: frontend/src/styles/themes.css
Изменить: App.tsx
Создать: frontend/src/components/ThemeToggle.tsx
Задачи:

✅ 3.5. Мобильная адаптация
Файлы:

Изменить: все страницы
Создать: frontend/src/components/mobile/BottomNavigation.tsx
Изменить: CSS для мобильных
Задачи:

🎯 QUICK WINS (можно сделать за 1-2 дня)
Приоритет: LOW | Effort: LOW
✅ QW.1. Title атрибуты везде
✅ QW.2. Loading states
✅ QW.3. Цветовое кодирование логов
✅ QW.4. Скрытие неактивных кнопок
✅ QW.5. Empty states с действиями
📊 TIMELINE ОЦЕНКА
🎯 РЕКОМЕНДУЕМЫЙ ПОРЯДОК ВЫПОЛНЕНИЯ
Week 1-2:

Tooltips (QW.1 + 1.2) ← Быстро, сразу улучшает UX
Loading states (QW.2) ← Быстро
Live Activity Feed (1.1) ← Ключевая фича
Группировка навигации (1.4) ← Упрощает интерфейс
Week 3-4: 5. Карточки позиций (1.3) ← Визуализация 6. Подсказки для кнопок (1.5) ← Безопасность 7. Цветовые логи (QW.3) ← Быстро 8. Empty states (QW.5) ← Быстро

Week 5-6: 9. FSM визуализация (2.1) ← Показывает процесс 10. Улучшенные логи (2.2) ← Дебаг 11. Scanner с объяснениями (2.3) ← Прозрачность

Week 7-8: 12. Графики с аннотациями (2.4) ← Аналитика 13. Система уведомлений (3.1) ← Real-time feedback 14. Горячие клавиши (3.3) ← Productivity

Week 9 (опционально): 15. Onboarding (3.2) ← Для новых пользователей 16. Тёмная тема (3.4) ← Nice to have 17. Мобильная адаптация (3.5) ← Если нужна

✅ КРИТЕРИИ ГОТОВНОСТИ (Definition of Done)
Для каждой задачи:

✅ Компонент создан/изменён
✅ TypeScript типы определены
✅ Responsive для desktop (tablet опционально)
✅ Tooltips добавлены где нужно
✅ Loading/Error states обработаны
✅ API endpoints готовы (если нужны)
✅ Базовое тестирование пройдено
✅ CSS стили согласованы с дизайн-системой
Этот план можно начинать выполнять последовательно, фокусируясь на Quick Wins и Phase 1 для быстрых результатов! 🚀
