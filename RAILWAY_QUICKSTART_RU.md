# 🚂 Быстрый запуск на Railway

## ⚡ Вариант 1: Через Web (самый простой)

### 1. Подготовка
```bash
# Убедитесь, что код в Git репозитории
git add .
git commit -m "Prepare for Railway deployment"
git push
```

### 2. Деплой
1. Откройте [railway.app](https://railway.app/)
2. Нажмите **"Start a New Project"**
3. Выберите **"Deploy from GitHub repo"**
4. Выберите ваш репозиторий
5. Railway автоматически обнаружит Dockerfile и начнет сборку

### 3. Настройка переменных (обязательно!)
В разделе **Variables** добавьте:
```env
TRADING_MODE=paper
EXCHANGE_NAME=binance
EXCHANGE_SANDBOX=true
SECRET_KEY=ваш-секретный-ключ
```

### 4. Готово! 🎉
Ваше приложение доступно по адресу: `https://your-app.railway.app`

---

## ⚡ Вариант 2: Через CLI (для продвинутых)

### 1. Установка CLI
```bash
# macOS
brew install railway

# Или через npm
npm i -g @railway/cli
```

### 2. Деплой
```bash
# Авторизация
railway login

# В директории проекта
cd /Users/iliazarikov/Documents/Python_crypto/Barahlo/experiments

# Инициализация
railway init

# Деплой
railway up

# Настройка переменных
railway variables set TRADING_MODE=paper
railway variables set EXCHANGE_SANDBOX=true
```

### 3. Проверка
```bash
# Просмотр логов
railway logs

# Открыть в браузере
railway open
```

---

## 🔍 Проверка работы

```bash
# Замените на ваш URL
curl https://your-app.railway.app/api/health

# Документация API
open https://your-app.railway.app/docs
```

---

## 📚 Полная документация

См. [RAILWAY_DEPLOYMENT_GUIDE_RU.md](./RAILWAY_DEPLOYMENT_GUIDE_RU.md) для подробной инструкции.

---

## ⚠️ Важно!

1. **НЕ** коммитьте `.env` с реальными ключами
2. Используйте `EXCHANGE_SANDBOX=true` для тестирования
3. Установите сильный `SECRET_KEY` в production

Генерация ключа:
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```
