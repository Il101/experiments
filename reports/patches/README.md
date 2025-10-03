# Patches Index

Этот каталог содержит патчи для исправления критических проблем фронтенда и его взаимодействия с API.

## 📋 Список патчей (по приоритету)

### P0 - Критические (требуют немедленного применения)

1. **001-add-zod-validation.patch.ts**
   - **Проблема:** Отсутствие runtime валидации WebSocket сообщений
   - **Решение:** Добавление Zod schemas для type-safe валидации
   - **Файлы:** `frontend/src/types/websocket.ts`, `frontend/src/store/useWebSocketStore.ts`
   - **Время:** ~30 минут

2. **002-fix-type-mismatches.patch.py**
   - **Проблема:** Несоответствие типов между backend и frontend (qty/size, strategy/mode)
   - **Решение:** Исправление field names в backend API или добавление adapter layer
   - **Файлы:** `backend/api/routers/trading.py`, `frontend/src/api/adapters/*.ts`
   - **Время:** ~45 минут

3. **007-add-security-headers.patch.ts**
   - **Проблема:** Отсутствие CSP и security headers (XSS, CSRF, clickjacking)
   - **Решение:** Добавление security headers в nginx, HTML, и FastAPI
   - **Файлы:** `frontend/index.html`, `frontend/nginx.conf`, `backend/api/main.py`
   - **Время:** ~20 минут

### P1 - Высокий приоритет

4. **003-fix-websocket-memory-leak.patch.ts**
   - **Проблема:** Утечки памяти из-за динамических imports в обработчике сообщений
   - **Решение:** Использование event bus и injection паттерна
   - **Файлы:** `frontend/src/store/useWebSocketStore.ts`, `frontend/src/components/layout/Layout.tsx`
   - **Время:** ~1 час

5. **004-add-error-boundaries.patch.tsx**
   - **Проблема:** Отсутствие Error Boundaries - ошибки падают до root
   - **Решение:** Создание ErrorBoundary компонента и применение к страницам
   - **Файлы:** `frontend/src/components/ErrorBoundary.tsx`, `frontend/src/router/routes.tsx`
   - **Время:** ~30 минут

6. **005-fix-websocket-reconnection.patch.ts**
   - **Проблема:** Reconnection без exponential backoff может создать infinite loop
   - **Решение:** Добавление exponential backoff с jitter и max attempts
   - **Файлы:** `frontend/src/store/useWebSocketStore.ts`
   - **Время:** ~45 минут

7. **006-add-request-cancellation.patch.ts**
   - **Проблема:** React Query queries не отменяются при unmount
   - **Решение:** Добавление AbortSignal support в queries
   - **Файлы:** `frontend/src/hooks/useEngine.ts`, `frontend/src/api/endpoints.ts`
   - **Время:** ~30 минут

### P2 - Средний приоритет

8. **008-optimize-performance.patch.tsx**
   - **Проблема:** Избыточные ре-рендеры компонентов
   - **Решение:** Добавление useMemo, useCallback, React.memo
   - **Файлы:** `frontend/src/pages/Trading.tsx`, `frontend/src/components/ui/Table.tsx`
   - **Время:** ~1.5 часа

9. **009-add-ws-type-safety.patch.ts**
   - **Проблема:** WebSocketMessage.data имеет тип `any`
   - **Решение:** Discriminated union types для type-safe message handling
   - **Файлы:** `frontend/src/types/websocket.ts`, `frontend/src/store/useWebSocketStore.ts`
   - **Время:** ~1 час

10. **010-add-offline-support.patch.tsx**
    - **Проблема:** Нет поддержки offline режима
    - **Решение:** Offline indicator, Service Worker для кэширования
    - **Файлы:** `frontend/src/hooks/useOnlineStatus.ts`, `frontend/public/service-worker.js`
    - **Время:** ~2 часа

## 🚀 Как применять патчи

### Общий порядок

1. **Прочитайте патч** полностью, чтобы понять изменения
2. **Создайте backup** перед применением
3. **Примените изменения** согласно инструкциям в патче
4. **Протестируйте** изменения локально
5. **Commit и push** изменения

### Пример применения патча 001

```bash
# 1. Установите зависимости (если нужно)
cd frontend
npm install zod

# 2. Создайте новый файл
# Скопируйте код из патча 001 в:
# frontend/src/types/websocket.ts

# 3. Обновите существующий файл
# Обновите frontend/src/store/useWebSocketStore.ts
# согласно патчу 001

# 4. Проверьте TypeScript
npm run tsc --noEmit

# 5. Запустите dev server
npm run dev

# 6. Проверьте работу
# - Откройте DevTools -> Console
# - Подключитесь к WebSocket
# - Проверьте, что сообщения валидируются
# - Отправьте невалидное сообщение (должна быть ошибка в консоли)

# 7. Commit
git add .
git commit -m "feat: add Zod validation for WebSocket messages (patch 001)"
```

## 📝 Checklist для каждого патча

- [ ] Прочитан и понят патч
- [ ] Создан backup измененных файлов
- [ ] Установлены необходимые зависимости
- [ ] Изменения применены
- [ ] TypeScript компилируется без ошибок
- [ ] ESLint не показывает ошибок
- [ ] Локальное тестирование пройдено
- [ ] Изменения задокументированы
- [ ] Commit создан с понятным сообщением

## 🧪 Тестирование после патчей

### После патча 001 (Zod Validation)
```typescript
// В консоли браузера:
// Проверьте, что невалидные сообщения логируются как ошибки

// Пример невалидного сообщения:
// Backend должен отклонить это сообщение
```

### После патча 002 (Type Mismatches)
```bash
# Проверьте API response:
curl http://localhost:8000/api/trading/positions | jq '.[0] | keys'
# Должны быть поля: size, mode (а не qty, strategy)

# Или в браузере:
# DevTools -> Network -> Fetch/XHR -> positions
# Проверьте response содержит правильные поля
```

### После патча 007 (Security Headers)
```bash
# Проверьте headers:
curl -I http://localhost:5173
# Должны быть:
# X-Frame-Options: DENY
# X-Content-Type-Options: nosniff
# X-XSS-Protection: 1; mode=block
# Content-Security-Policy: ...

# Проверьте CSP в браузере:
# DevTools -> Console
# Попробуйте: eval('1+1')
# Должна быть ошибка CSP violation
```

## 🔄 Rollback патчей

Если патч вызывает проблемы:

```bash
# 1. Восстановите из backup
cp frontend/src/store/useWebSocketStore.ts.backup frontend/src/store/useWebSocketStore.ts

# 2. Или используйте git
git checkout HEAD -- frontend/src/store/useWebSocketStore.ts

# 3. Перезапустите dev server
npm run dev
```

## 📚 Дополнительные ресурсы

- [Zod Documentation](https://zod.dev/)
- [React Query Cancellation](https://tanstack.com/query/latest/docs/react/guides/query-cancellation)
- [Content Security Policy](https://developer.mozilla.org/en-US/docs/Web/HTTP/CSP)
- [React Error Boundaries](https://react.dev/reference/react/Component#catching-rendering-errors-with-an-error-boundary)
- [Service Workers](https://developer.mozilla.org/en-US/docs/Web/API/Service_Worker_API)

## 💡 Tips

- **Применяйте патчи по одному**, тестируйте перед следующим
- **Не пропускайте P0 патчи** - они критичны для безопасности и стабильности
- **Адаптируйте код** под ваши специфические нужды
- **Документируйте изменения** в changelog
- **Обновите тесты** после применения патчей

## 🆘 Помощь

Если возникли проблемы с применением патчей:

1. Проверьте версии зависимостей
2. Убедитесь, что структура проекта соответствует ожидаемой
3. Проверьте логи ошибок
4. Создайте issue с описанием проблемы

## 📊 Прогресс применения

| Патч | Статус | Дата применения | Комментарии |
|------|--------|----------------|-------------|
| 001  | ⏳ Pending | - | - |
| 002  | ⏳ Pending | - | - |
| 003  | ⏳ Pending | - | - |
| 004  | ⏳ Pending | - | - |
| 005  | ⏳ Pending | - | - |
| 006  | ⏳ Pending | - | - |
| 007  | ⏳ Pending | - | - |
| 008  | ⏳ Pending | - | - |
| 009  | ⏳ Pending | - | - |
| 010  | ⏳ Pending | - | - |

**Легенда:**
- ⏳ Pending - не применен
- 🔄 In Progress - в процессе
- ✅ Applied - применен и протестирован
- ❌ Failed - применение не удалось
- ⏭️ Skipped - пропущен

---

**Последнее обновление:** 2 октября 2025  
**Автор патчей:** Senior Full-Stack Engineer
