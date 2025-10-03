# 🚂 Руководство по развертыванию на Railway

## 📋 Содержание
1. [Подготовка проекта](#подготовка-проекта)
2. [Настройка Railway](#настройка-railway)
3. [Развертывание](#развертывание)
4. [Настройка переменных окружения](#настройка-переменных-окружения)
5. [Мониторинг и логи](#мониторинг-и-логи)
6. [Устранение неполадок](#устранение-неполадок)

---

## 🎯 Подготовка проекта

### 1. Убедитесь, что все необходимые файлы готовы:

- ✅ `Dockerfile` - Docker конфигурация
- ✅ `requirements.txt` - Python зависимости
- ✅ `railway.toml` или `railway.json` - Railway конфигурация
- ✅ `.env.example` - Пример переменных окружения

### 2. Проверьте структуру проекта:

```bash
├── Dockerfile
├── requirements.txt
├── railway.toml
├── railway.json
├── .env.example
├── breakout_bot/
│   ├── api/
│   │   └── main.py
│   └── ...
└── ...
```

---

## 🚀 Настройка Railway

### Способ 1: Через Web интерфейс

#### Шаг 1: Создайте аккаунт на Railway
1. Перейдите на [Railway.app](https://railway.app/)
2. Нажмите **"Start a New Project"**
3. Войдите через GitHub

#### Шаг 2: Создайте новый проект
1. Нажмите **"New Project"**
2. Выберите **"Deploy from GitHub repo"**
3. Выберите ваш репозиторий или загрузите код

#### Шаг 3: Настройте проект
1. Railway автоматически обнаружит `Dockerfile`
2. Проект начнет сборку автоматически

### Способ 2: Через Railway CLI

#### Шаг 1: Установите Railway CLI

```bash
# macOS с Homebrew
brew install railway

# Или через npm
npm i -g @railway/cli

# Или через curl
bash <(curl -fsSL cli.new)
```

#### Шаг 2: Авторизуйтесь

```bash
railway login
```

#### Шаг 3: Инициализируйте проект

```bash
# В корневой директории проекта
cd /Users/iliazarikov/Documents/Python_crypto/Barahlo/experiments

# Инициализация нового проекта
railway init

# Или подключение к существующему
railway link
```

#### Шаг 4: Разверните проект

```bash
railway up
```

---

## ⚙️ Настройка переменных окружения

### Через Web интерфейс:

1. Откройте ваш проект в Railway
2. Перейдите в раздел **Variables**
3. Добавьте следующие переменные:

```env
# Database (Railway предоставит автоматически если добавить PostgreSQL)
DATABASE_URL=sqlite:///app/data/breakout_bot.db

# Trading Configuration
TRADING_MODE=paper
PAPER_STARTING_BALANCE=100000.0

# Exchange Configuration (ВАЖНО: используйте безопасные значения!)
EXCHANGE_NAME=binance
EXCHANGE_API_KEY=your_api_key_here
EXCHANGE_SECRET_KEY=your_secret_key_here
EXCHANGE_SANDBOX=true

# Risk Management
MAX_DAILY_LOSS_PERCENT=5.0
MAX_POSITION_SIZE_PERCENT=2.0
KILL_SWITCH_DAILY_LOSS_PERCENT=10.0

# Logging
LOG_LEVEL=INFO

# Security (ОБЯЗАТЕЛЬНО ИЗМЕНИТЕ!)
SECRET_KEY=your_production_secret_key_here
JWT_SECRET_KEY=your_jwt_production_secret_here

# CORS (добавьте ваш домен Railway)
ENABLE_CORS=true
CORS_ORIGINS=https://your-app.railway.app

# Resource Limits
MAX_MEMORY_MB=2048
MAX_CPU_PERCENT=80.0
```

### Через CLI:

```bash
# Установить переменную
railway variables set TRADING_MODE=paper

# Установить несколько переменных из файла
railway variables set --from .env

# Просмотреть переменные
railway variables
```

---

## 🗄️ Добавление базы данных

### PostgreSQL (рекомендуется для production):

#### Через Web интерфейс:
1. В проекте нажмите **"+ New"**
2. Выберите **"Database"** → **"PostgreSQL"**
3. Railway автоматически создаст `DATABASE_URL`

#### Через CLI:
```bash
railway add --database postgresql
```

### Redis (опционально, для кэширования):

```bash
railway add --database redis
```

---

## 🔧 Развертывание

### Автоматическое развертывание (рекомендуется):

Railway автоматически разворачивает при каждом push в GitHub:

```bash
git add .
git commit -m "Deploy to Railway"
git push origin main
```

### Ручное развертывание через CLI:

```bash
# Развернуть текущую версию
railway up

# Развернуть с логами
railway up --detach=false
```

---

## 📊 Мониторинг и логи

### Просмотр логов:

#### Через Web:
1. Откройте проект в Railway
2. Перейдите в раздел **"Deployments"**
3. Выберите deployment для просмотра логов

#### Через CLI:
```bash
# Просмотр логов в реальном времени
railway logs

# Последние 100 строк
railway logs --lines 100
```

### Проверка состояния:

```bash
# Статус проекта
railway status

# Информация о deployment
railway run env
```

### Health Check:

После развертывания проверьте:
```bash
curl https://your-app.railway.app/api/health
```

---

## 🌐 Настройка домена

### Через Web интерфейс:
1. Откройте **Settings** → **Domains**
2. Нажмите **"Generate Domain"** для получения бесплатного поддомена
3. Или добавьте **Custom Domain** для вашего домена

### Через CLI:
```bash
railway domain
```

---

## 🐛 Устранение неполадок

### Проблема: Build fails

**Решение:**
```bash
# Проверьте логи сборки
railway logs --deployment

# Проверьте Dockerfile локально
docker build -t breakout-bot .
docker run -p 8000:8000 breakout-bot
```

### Проблема: Application crashes

**Решение:**
```bash
# Проверьте переменные окружения
railway variables

# Проверьте логи приложения
railway logs

# Проверьте использование ресурсов
railway run -- ps aux
```

### Проблема: Database connection error

**Решение:**
1. Убедитесь, что `DATABASE_URL` установлен правильно
2. Проверьте, что база данных создана
3. Проверьте права доступа

```bash
railway variables get DATABASE_URL
```

### Проблема: Port binding error

**Решение:**
Убедитесь, что приложение использует переменную `$PORT`:

```python
# В breakout_bot/api/main.py
import os
port = int(os.getenv("PORT", 8000))
```

Railway автоматически установит `$PORT`.

---

## 📝 Полезные команды Railway CLI

```bash
# Показать все проекты
railway list

# Открыть проект в браузере
railway open

# Выполнить команду в окружении Railway
railway run python manage.py migrate

# Подключиться к базе данных
railway connect

# Удалить проект
railway delete

# Обновить CLI
railway update
```

---

## 🔒 Безопасность

### ⚠️ ВАЖНО:

1. **НЕ** коммитьте `.env` файл с реальными ключами
2. Используйте Railway Variables для чувствительных данных
3. Включите `EXCHANGE_SANDBOX=true` для тестирования
4. Установите сильные значения для `SECRET_KEY` и `JWT_SECRET_KEY`
5. Ограничьте CORS только нужными доменами

### Генерация безопасных ключей:

```bash
# Генерация SECRET_KEY
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Или через openssl
openssl rand -base64 32
```

---

## 💰 Стоимость

Railway предоставляет:
- **$5** бесплатно каждый месяц для Hobby плана
- Оплата только за использованные ресурсы
- Калькулятор: [Railway Pricing](https://railway.app/pricing)

### Оптимизация затрат:

1. Используйте **Sleep on Idle** для dev окружений
2. Оптимизируйте использование памяти
3. Используйте кэширование (Redis)
4. Настройте автоматическое масштабирование

---

## 📚 Дополнительные ресурсы

- [Railway Docs](https://docs.railway.app/)
- [Railway CLI Reference](https://docs.railway.app/develop/cli)
- [Railway Templates](https://railway.app/templates)
- [Railway Discord](https://discord.gg/railway)

---

## 🎉 Готово!

Ваш Breakout Bot теперь развернут на Railway!

### Проверьте работу:

```bash
# Проверка API
curl https://your-app.railway.app/api/health

# Проверка документации API
open https://your-app.railway.app/docs
```

### Следующие шаги:

1. ✅ Настройте мониторинг и алерты
2. ✅ Подключите домен
3. ✅ Настройте CI/CD через GitHub
4. ✅ Добавьте production database (PostgreSQL)
5. ✅ Настройте бэкапы

---

## 📞 Поддержка

Если возникли проблемы:
1. Проверьте логи: `railway logs`
2. Проверьте статус: `railway status`
3. Обратитесь к [Railway Docs](https://docs.railway.app/)
4. Задайте вопрос в [Railway Discord](https://discord.gg/railway)

**Удачного деплоя! 🚀**
