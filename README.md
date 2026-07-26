# 🤖 AI Talent Hub

Платформа для связи предпринимателей и специалистов по ИИ. Telegram-бот + Mini App.

## Что это

**AI Talent Hub** — экосистема, где:
- 🏢 **Предприниматели** находят талантливых специалистов по ИИ для своих проектов
- 🧠 **Специалисты по ИИ** находят проекты, зарабатывают и повышают свой рейтинг

Платформа работает как **Telegram-бот** (для регистрации и базовых действий) и как **Telegram Mini App** (полноценный интерфейс с карточками заказов, фильтрами, профилями).

## Архитектура

```
┌─────────────────────────────────────────────────────────┐
│                    Telegram Bot API                      │
│  (aiogram 3.x) — регистрация, уведомления, команды      │
└────────────────────────┬────────────────────────────────┘
                         │
        ┌────────────────┼────────────────┐
        │                │                │
   ┌────▼────┐    ┌──────▼──────┐   ┌────▼────┐
   │  SQLite  │    │ FastAPI     │   │ React   │
   │   БД     │◄──►│ Бэкенд API  │   │ Mini App│
   │          │    │ (Mini App)  │   │ (Vite)  │
   └──────────┘    └─────────────┘   └─────────┘
        │                │
        ▼                ▼
   ┌──────────┐    ┌─────────────┐
   │ YooKassa │    │ Vosk        │
   │ Платежи  │    │ Голосовой   │
   │          │    │ ввод        │
   └──────────┘    └─────────────┘
```

## Стек технологий

| Компонент | Технология | Назначение |
|-----------|-----------|------------|
| Бот | **aiogram 3.x** | Telegram-бот, FSM, обработчики |
| Бэкенд API | **FastAPI** | REST API для Mini App |
| Фронтенд | **React + Vite** | Telegram Mini App |
| База данных | **SQLite + aiosqlite** | Хранение данных |
| Платежи | **YooKassa** | Оплата через самозанятость |
| Голос | **Vosk** | Распознавание речи (русский) |
| Deploy | **Render** | Бесплатный хостинг бэкенда |

## Функционал

### 🏢 Для предпринимателей

- **Регистрация** — выбор роли, заполнение профиля
- **Создание заказов** — название, описание, бюджет (5-шаговый мастер)
- **Поиск специалистов** — по навыкам, рейтингу, ставке
- **Управление откликами** — просмотр, принятие/отклонение исполнителей
- **Оплата** — через YooKassa с автоматическими чеками
- **Отзывы и рейтинг** — оценка выполненной работы
- **Mini App** — карточки заказов, лента специалистов, профиль

### 🧠 Для специалистов

- **Регистрация** — навыки, портфолио, ставка (₽/час)
- **Лента заказов** — поиск, фильтры по категории, бюджету
- **Отклики** — сопроводительное сообщение + цена
- **Выполнение** — статусы заказов, уведомления
- **Оплата** — получение денег, чеки для самозанятых
- **Рейтинг** — растёт с каждым заказом и отзывом
- **Голосовой ввод** — заполнение профиля голосовыми сообщениями
- **Mini App** — все заказы, мои заказы, профиль с аватаром из Telegram

### 📱 Telegram Mini App

Запускается синей кнопкой в нижнем меню бота. Полноценный SPA:

**Специалист:**
| 📋 Все заказы | 🏆 Мои заказы | 👤 Профиль |
|---|---|---|
| Поиск + фильтры | В работе / Завершённые | Аватар из TG |
| Карточка заказа | | Навыки, портфолио |
| Отклик с текстом | | Статистика |

**Предприниматель:**
| 📋 Мои заказы | 🧠 Исполнители | 👤 Профиль |
|---|---|---|
| ＋ Создать заказ | Поиск по навыкам | Фото из TG |
| Управление откликами | Карточка + отзывы | Описание |
| ✅ Выбрать исполнителем | | Редактирование |

### 🎤 Голосовой ввод

Специалист может заполнять профиль голосом:
1. Пользователь отправляет голосовое сообщение боту
2. Бот конвертирует OGG → WAV (ffmpeg)
3. Vosk распознаёт русскую речь
4. Текст передаётся в текущий обработчик (имя, био, навыки и т.д.)

## Категории заказов

- 🤖 ML / Data Science
- 💬 LLM / NLP
- 👁️ Computer Vision
- 🤖 AI-агенты
- ⚙️ Автоматизация с ИИ
- 📊 ИИ-консалтинг
- 🔧 Другое

## Оплата через самозанятость

```
Работодатель → YooKassa → Платформа (5% комиссия) → Специалист
```

- Приём платежей через YooKassa
- Комиссия платформы настраивается (по умолчанию 5%)
- Специалист как самозанятый формирует чек в «Мой налог»
- Поддержка автоматических чеков через YooKassa

## Структура проекта

```
AI_talent_bot/
├── main.py                     # Запуск Telegram-бота
├── config.py                   # Конфигурация (.env)
├── keyboards.py                # Клавиатуры (Reply + Inline)
├── requirements.txt            # Зависимости Python
├── pyproject.toml              # Пакет Python
├── .env.example                # Шаблон переменных окружения
├── .gitignore
│
├── database/
│   └── db.py                   # SQLite, схема, инициализация
│
├── handlers/
│   ├── onboarding.py           # Регистрация, выбор роли
│   ├── profile.py              # Профиль, статистика, отзывы
│   ├── orders.py               # CRUD заказов
│   ├── applications.py         # Отклики на заказы
│   ├── search.py               # Поиск специалистов/заказов
│   ├── payments.py             # Оплата через YooKassa
│   └── voice.py                # Обработка голосовых сообщений
│
├── states/
│   └── user_states.py          # FSM-состояния
│
├── utils/
│   ├── helpers.py              # Форматирование, рейтинг
│   ├── db_queries.py           # SQL-запросы
│   ├── payments.py             # YooKassa интеграция
│   └── voice.py                # Vosk распознавание
│
├── assets/
│   └── welcome.jpg             # Приветственное изображение
│
├── scripts/
│   └── download_model.sh       # Скачивание модели Vosk
│
├── models/
│   └── vosk-model-small-ru/    # Модель Vosk (русский)
│
└── mini_app/
    ├── start.sh                # Скрипт запуска Mini App
    ├── backend/
    │   ├── main.py             # FastAPI: 20+ эндпоинтов
    │   ├── requirements.txt
    │   └── Procfile             # Для Render деплоя
    └── frontend/
        ├── index.html
        ├── vite.config.js
        ├── package.json
        ├── dist/               # Собранный фронтенд
        └── src/
            ├── main.jsx
            ├── App.jsx          # Роутинг + навигация
            ├── api.js           # API клиент
            ├── context.jsx      # Глобальный стейт
            ├── components.jsx   # UI компоненты
            └── pages/
                ├── SpecialistOrders.jsx
                ├── SpecialistMyOrders.jsx
                ├── SpecialistProfile.jsx
                ├── EmployerOrders.jsx
                ├── EmployerSpecialists.jsx
                └── EmployerProfile.jsx
```

## Быстрый старт

### 1. Клонировать репозиторий

```bash
git clone https://github.com/YOUR_USERNAME/AI_talent_bot.git
cd AI_talent_bot
```

### 2. Установить зависимости

```bash
# Python зависимости
pip install -r requirements.txt
pip install fastapi uvicorn[standard]

# Для голосового ввода (опционально)
sudo apt install ffmpeg          # Linux
# brew install ffmpeg            # macOS
bash scripts/download_model.sh   # Модель Vosk (~50 МБ)

# Фронтенд Mini App
cd mini_app/frontend
npm install
npm run build
cd ../..
```

### 3. Настроить окружение

```bash
cp .env.example .env
# Заполнить .env своими данными
```

**Обязательно:**
- `BOT_TOKEN` — получите у [@BotFather](https://t.me/BotFather)

**Для Mini App:**
- `MINI_APP_URL` — URL вашего бэкенда (Render, ngrok, или localhost)

**Для платежей (опционально):**
- `YOOKASSA_SHOP_ID` и `YOOKASSA_SECRET_KEY` — [yookassa.ru](https://yookassa.ru)

### 4. Запустить

```bash
# Терминал 1: Telegram-бот
python -m ai_talent_bot

# Терминал 2: Mini App бэкенд
cd mini_app/backend
uvicorn main:app --host 0.0.0.0 --port 8000
```

### 5. Настроить Mini App в BotFather

1. Откройте [@BotFather](https://t.me/BotFather)
2. `/myapps` → выберите бота
3. Configure Mini App → введите URL вашего бэкенда
4. Bot Settings → Menu Button → Configure Menu Button → введите URL

## Деплой на Render (бесплатно)

### Бэкенд (Web Service)

1. Зайдите на [render.com](https://render.com)
2. New → Web Service → подключите GitHub репозиторий
3. Настройки:
   - **Runtime:** Python
   - **Build Command:** `pip install -r requirements.txt && pip install fastapi uvicorn && cd mini_app/frontend && npm install && npm run build`
   - **Start Command:** `cd mini_app/backend && uvicorn main:app --host 0.0.0.0 --port $PORT`
   - **Plan:** Free
4. Environment Variables:
   - `BOT_TOKEN` = ваш токен
   - `MINI_APP_URL` = URL Render (например `https://ai-talent-bot.onrender.com`)
5. Deploy

### Бесплатный план Render

- ✅ 512 MB RAM
- ✅ Без карты
- ⚠️ Засыпает через 15 мин бездействия (первый запрос ~30 сек)
- ⚠️ 750 часов/месяц

## Платежи и самозанятость

### YooKassa (реализовано)

| Параметр | Значение |
|----------|----------|
| Комиссия | ~2.8-3.5% |
| Чеки НПД | ✅ Автоматические |
| Способы оплаты | Карты, СБП, SberPay |
| API | REST, Python SDK |

### Альтернативы

| Сервис | Комиссия | Чеки НПД | API |
|--------|----------|----------|-----|
| Тинькофф | ~1.7-2.5% | ✅ | REST |
| CloudPayments | ~2.5-3.5% | ✅ | REST |
| Robokassa | ~2.9-4.0% | ⚠️ | REST/XML |

## База данных

SQLite с таблицами:

| Таблица | Описание |
|---------|----------|
| `users` | Пользователи (роль, профиль, рейтинг, самозанятость) |
| `orders` | Заказы (статус, бюджет, категории) |
| `applications` | Отклики на заказы |
| `payments` | Платежи (YooKassa) |
| `reviews` | Отзывы и рейтинги |

## API эндпоинты (Mini App)

| Метод | Путь | Описание |
|-------|------|----------|
| GET | `/api/me` | Текущий пользователь |
| PATCH | `/api/me` | Обновить профиль |
| GET | `/api/me/stats` | Статистика |
| GET | `/api/orders` | Список заказов |
| GET | `/api/orders/:id` | Детали заказа |
| POST | `/api/orders` | Создать заказ |
| PATCH | `/api/orders/:id/status` | Изменить статус |
| GET | `/api/orders/:id/applications` | Отклики на заказ |
| POST | `/api/applications` | Откликнуться |
| PATCH | `/api/applications/:id/accept` | Принять отклик |
| PATCH | `/api/applications/:id/reject` | Отклонить отклик |
| GET | `/api/specialists` | Список специалистов |
| GET | `/api/specialists/:id` | Профиль специалиста |
| POST | `/api/reviews` | Оставить отзыв |
| GET | `/api/avatar/:tgId` | Аватар из Telegram |

## Лицензия

MIT
