# SK Diagnostics

Frontend для прохождения диагностик и просмотра результатов, работающий поверх NocoBase.

## Что есть

- авторизация через NocoBase;
- список выданных попыток пользователя;
- прохождение теста по уже созданным `attempts` и `answers`;
- кабинет `psycho` с таблицей результатов;
- детальная страница результата: оформленный отчёт + JSON-таблица;
- Docker Compose для локального и production-запуска;
- GitHub Actions для сборки Docker-образа и деплоя через Coolify.

## Структура

```text
sk-diagnostics/
├── docker-compose.yaml
├── docker-compose.prod.yaml
├── .env.example
├── frontend/
│   ├── Dockerfile
│   ├── nginx/nginx.conf
│   └── app/
│       ├── package.json
│       └── src/
└── .github/workflows/
    ├── build.yml
    └── deploy.yml
```

## Переменные окружения

Основные переменные лежат в `.env`.

```bash
cp .env.example .env
```

Доступные переменные:

- `VITE_API_URL` — адрес NocoBase для dev proxy. По умолчанию `https://flow.skeducator.ru`.
- `VITE_APP_TITLE` — название приложения во frontend.
- `VITE_PSYCHO_ROLE` — имя роли для доступа к страницам результатов.
- `VITE_ADMIN_ROLE` — роль администратора.
- `VITE_LOGGING` — резерв под клиентский логгер/диагностику.
- `FRONTEND_IMAGE_TAG` — тег production-образа в `docker-compose.prod.yaml`.

## Локальный запуск

Как в `sk-contest`, локальная разработка идёт через Vite внутри контейнера и bind mount только для `src`.

```bash
cp .env.example .env
docker compose -p sk-diagnostics up -d --build
```

После старта приложение доступно на `http://localhost:3000`.

## Production

Production-compose ожидает, что образ уже лежит в GHCR:

```bash
docker compose -f docker-compose.prod.yaml up -d
```

По умолчанию используется:

```text
ghcr.io/aleksioprime/sk-diagnostic-frontend:${FRONTEND_IMAGE_TAG}
```

Контейнер подключается к внешней сети `apps_net`, как и в образце.

## GitHub Actions

### Build

Workflow `.github/workflows/build.yml`:

- запускает `npm ci` и `npm run build` для frontend;
- собирает production-образ;
- пушит его в GHCR с тегами `latest` и `${GITHUB_SHA}`;
- при наличии секретов обновляет `FRONTEND_IMAGE_TAG` в Coolify.

### Deploy

Workflow `.github/workflows/deploy.yml`:

- вручную триггерит deploy в Coolify;
- умеет передавать `force=true/false`.

### Нужные secrets

- `COOLIFY_API`
- `COOLIFY_TOKEN`
- `COOLIFY_APP`

### Нужные repository variables

- `VITE_API_URL`
- `VITE_APP_TITLE`
- `VITE_PSYCHO_ROLE`
- `VITE_ADMIN_ROLE`
- `VITE_LOGGING`

Если variables не заданы, workflow использует безопасные значения по умолчанию из shell.
