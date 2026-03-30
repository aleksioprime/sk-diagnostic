# SK Diagnostic

Веб-приложение для проведения психологической диагностики учащихся Гимназии Сколково.
Позволяет проходить тесты, сохранять ответы в реальном времени и просматривать вычисленные результаты.

## Архитектура

```
┌─────────────┐       ┌────────────────┐        ┌──────────────┐
│  Frontend   │──────▷│  Backend (BFF) │───────▷│   NocoBase   │
│  Vue 3 SPA  │  HTTP │  FastAPI       │  HTTP  │   REST API   │
└─────────────┘       └────────────────┘        └──────────────┘
                             ▲
                             │
                      ┌──────┴──────┐
                      │   Scripts   │
                      │  Node.js    │
                      └─────────────┘
```

| Слой | Технологии | Назначение |
|------|-----------|------------|
| **Frontend** | Vue 3, Pinia, Vue Router, Tailwind CSS, Vite | SPA: прохождение тестов, кабинет пользователя, панель результатов |
| **Backend** | Python 3.12, FastAPI, httpx, Pydantic | BFF-прослойка для анонимного прохождения тестов по публичной ссылке |
| **NocoBase** | NocoBase (self-hosted) | Хранилище данных, авторизация, CRUD-управление коллекциями |
| **Scripts** | Node.js | Расчётные скрипты диагностик (Домики, Мотивация учения) |

## Возможности

- **Авторизация** через NocoBase (логин + пароль).
- **Личный кабинет** — список активных и завершённых попыток с прогрессом.
- **Прохождение теста** — single choice, multiple choice, scale, ranking, yes/no, text, number.
- **Методика «Домики»** — специальные цветовые компоненты для ranking и scale вопросов.
- **Анонимный доступ** — прохождение по ссылке `/t/:token` без авторизации (через BFF-бэкенд).
- **Последовательный режим** — вопросы по одному (пошаговая навигация).
- **Панель результатов** (роли `psycho` / `admin`) — таблица попыток, детальный отчёт с секциями и raw JSON.
- **Шаблонизация результатов** — подключаемые шаблоны для разных диагностик.
- **Скрипты расчёта** — запуск из CLI для вычисления итогов диагностик.

## Структура проекта

```
sk-diagnostic/
├── backend/                # FastAPI BFF-сервис
│   ├── src/
│   │   ├── main.py         # Точка входа приложения
│   │   ├── core/
│   │   │   ├── config.py   # Настройки из env-переменных
│   │   │   ├── logging.py  # Логирование и middleware
│   │   │   └── nocobase.py # HTTP-клиент к NocoBase
│   │   ├── routes/v1/      # Маршруты API v1
│   │   ├── schemas/        # Pydantic-схемы валидации
│   │   └── services/       # Бизнес-логика
│   ├── Dockerfile
│   ├── entrypoint.sh
│   └── requirements.txt
│
├── frontend/               # Vue 3 SPA
│   ├── app/
│   │   ├── src/
│   │   │   ├── api/        # Axios-инстансы (NocoBase + BFF)
│   │   │   ├── components/ # UI-компоненты
│   │   │   ├── diagnostics/# Логика конкретных диагностик
│   │   │   ├── router/     # Vue Router (маршруты + guards)
│   │   │   ├── stores/     # Pinia (auth-стор)
│   │   │   ├── utils/      # Утилиты и хелперы
│   │   │   └── views/      # Страницы приложения
│   │   ├── package.json
│   │   └── vite.config.js
│   ├── nginx/nginx.conf    # Конфиг Nginx для production
│   └── Dockerfile          # Multi-stage (dev + prod)
│
├── scripts/                # Скрипты расчёта результатов
│   ├── calculate.js        # Entrypoint: node scripts/calculate.js <name>
│   ├── colors/             # Методика «Домики» (Орехова)
│   └── motivation/         # Мотивация учения (10-16 лет)
│
├── docker-compose.yaml     # Локальная разработка
├── docker-compose.prod.yaml# Production (GHCR-образы)
└── NOCOBASE_SETUP.md       # Инструкция по настройке NocoBase
```

## Переменные окружения

Создайте файл `.env` в корне проекта:

```bash
cp .env.example .env
```

### Общие

| Переменная | Описание | По умолчанию |
|-----------|---------|-------------|
| `VITE_API_URL` | URL NocoBase для dev-прокси | `https://flow.skeducator.ru` |
| `VITE_BACKEND_API_URL` | URL BFF-бэкенда для фронтенда | `/backend` |
| `VITE_LOGGING` | Включить логирование на фронтенде (`1` / `0`) | `0` |

### Backend

| Переменная | Описание | По умолчанию |
|-----------|---------|-------------|
| `NOCOBASE_URL` | URL NocoBase API | — |
| `API_KEY` | Bearer-токен для NocoBase | — |
| `NOCOBASE_TIMEOUT` | Таймаут запросов к NocoBase (сек.) | `30` |
| `HOST` | Хост сервера | `0.0.0.0` |
| `PORT` | Порт сервера | `8000` |
| `CORS_ALLOW_ORIGINS` | Разрешённые Origin через запятую | `http://localhost:3000` |
| `RELOAD` | Включить hot-reload uvicorn (`1` / `0`) | `0` |

### Production

| Переменная | Описание |
|-----------|---------|
| `BACKEND_IMAGE_TAG` | Тег Docker-образа бэкенда |
| `FRONTEND_IMAGE_TAG` | Тег Docker-образа фронтенда |

## Быстрый старт

### Локальная разработка (Docker Compose)

```bash
# 1. Клонировать репозиторий
git clone https://github.com/aleksioprime/sk-diagnostic.git
cd sk-diagnostic

# 2. Создать .env
cp .env.example .env
# Заполнить NOCOBASE_URL и API_KEY

# 3. Запустить
docker compose -p sk-diagnostic up -d --build
```

Приложение будет доступно:
- **Frontend**: http://localhost:3000
- **Backend API docs**: http://localhost:8000/api/openapi

### Без Docker

**Backend:**
```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
```

**Frontend:**
```bash
cd frontend/app
npm install
npm run dev
```

### Production

```bash
docker compose -f docker-compose.prod.yaml up -d
```

Образы загружаются из GHCR:
- `ghcr.io/aleksioprime/sk-diagnostic-backend:${BACKEND_IMAGE_TAG}`
- `ghcr.io/aleksioprime/sk-diagnostic-frontend:${FRONTEND_IMAGE_TAG}`

Контейнеры подключаются к внешней Docker-сети `apps_net`.

## Скрипты расчёта

Диагностические скрипты выполняются через CLI:

```bash
node scripts/calculate.js <имя_диагностики>
```

Доступные диагностики:
- `colors` — Проективная методика «Домики» (Орехова)
- `motivation` — Мотивация учения школьников 10-16 лет

Каждая диагностика содержит:
- `script.js` — логика расчёта;
- `data.json` — пример входных данных для тестирования.

## API

### Публичный BFF (без авторизации)

| Метод | Путь | Описание |
|-------|------|---------|
| `GET` | `/api/v1/public/attempts/:token` | Получить бандл данных попытки |
| `POST` | `/api/v1/public/attempts/:token/start` | Начать прохождение |
| `PATCH` | `/api/v1/public/attempts/:token/answers/:questionId` | Сохранить ответ |
| `POST` | `/api/v1/public/attempts/:token/submit` | Отправить попытку |

Документация доступна на `/api/openapi` (Swagger UI).

### NocoBase (с авторизацией)

Фронтенд обращается к NocoBase напрямую для авторизованных пользователей:
- Авторизация: `POST /api/auth:signIn`
- CRUD коллекций: `/api/<collection>:list`, `:get`, `:create`, `:update`, `:destroy`

## CI/CD

### GitHub Actions

- **build.yml** — собирает Docker-образы, пушит в GHCR.
- **deploy.yml** — триггерит деплой через Coolify.

### Необходимые секреты

| Секрет | Назначение |
|--------|-----------|
| `COOLIFY_API` | URL API Coolify |
| `COOLIFY_TOKEN` | Токен авторизации Coolify |
| `COOLIFY_APP` | ID приложения в Coolify |

## Лицензия

© 2026 Алексей Семочкин — Сервисы автоматизации Гимназии Сколково.
