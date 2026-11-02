# Развёртывание в Coolify

Прод — ресурс «Docker Compose» в проекте Diagnostic панели `devops.skolhub.ru` (сервер `skl-web-app`)
с файлом [`infra/coolify/docker-compose.prod.yaml`](../infra/coolify/docker-compose.prod.yaml).
Образы собирает GitHub Actions при пуше в `main`; API идёт через nginx фронтенда, нужен один домен.

## 1. DNS

`diagnostic.skolhub.ru` — A-запись на `5.252.65.50` (вся зона `skolhub.ru` уже ведёт туда).

## 2. Переменные

`.env.prod` в корне репозитория (в git не попадает):

```
COOLIFY_URL=https://devops.skolhub.ru
COOLIFY_API_TOKEN=…
SECRET_KEY=…              # openssl rand -hex 32
DB__PASSWORD=…            # openssl rand -hex 16
BOOTSTRAP_ADMIN_EMAILS=["…"]
SMTP__USER=…
SMTP__PASSWORD=…
SKOLSTREAM__CLIENT_ID=…
SKOLSTREAM__CLIENT_SECRET=…
SKOLSTREAM__DIRECTORY_TOKEN=…
```

## 3. Ресурс

```bash
python3 infra/coolify/deploy.py --dry-run
python3 infra/coolify/deploy.py
```

Скрипт создаёт ресурс `sk-diagnostic`, передаёт переменные, задаёт домен и запускает сборку. Домены Coolify
принимает после первой сборки — тогда скрипт нужно запустить ещё раз.

## 4. SkolStream

OAuth-приложение «SK Diagnostic» в админке SkolStream: Confidential, Authorization code, redirect
`https://diagnostic.skolhub.ru/api/v1/auth/skolstream/callback`, Skip authorization. Токен выгрузки
справочника — отдельный для сервиса. Подробнее — README пакета sk-common.

## 5. Перенос из NocoBase

Разовая операция. **Сначала синхронизируйте справочник** («Люди» → «Обновить из SkolStream», полный срез):
ученики сопоставляются по UUID SkolStream. Выгрузка только читает API NocoBase:

```bash
NOCOBASE_URL=https://flow.skolhub.ru NOCOBASE_API_KEY=… python -m app.cli nocobase-fetch ./nocobase
```

JSON-файлы копируются в том `nocobase_data` контейнера `backend`, затем:

```bash
python -m app.cli nocobase-load /data/nocobase
```

- ID методик, вопросов, выдач и попыток сохраняются;
- даты рождения из NocoBase переносятся ученикам, у которых их ещё нет;
- пустые ответы-заготовки NocoBase не переносятся;
- результаты завершённых попыток считаются заново и сверяются с NocoBase; расхождения — в `report.json`;
- повторный запуск пропускает уже перенесённое.

Психологов назначает администратор в разделе «Психологи» (раньше — роль `psycho` в NocoBase).
