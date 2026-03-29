# Настройка NocoBase для диагностики и анонимного прохождения

## Что теперь изменилось

Анонимное прохождение по ссылке `/t/<token>` больше не работает напрямую через публичные права NocoBase.
Теперь frontend обращается в FastAPI backend, а backend уже работает с NocoBase через `API_KEY` из `.env`.

Это значит:
- `API_KEY` хранится только на сервере.
- Публичной роли не нужен доступ на запись в `attempts`, `answers`, `answer_ranking_items`.
- Все изменения статусов и времени попытки выполняет backend.

## Обязательные поля и данные

### 1. Поле `token` в коллекции `attempts`

Поле уже добавлено. Оно должно оставаться:
- тип: `string`
- уникальное: `true`
- желательно с индексом

По этому токену backend находит попытку для публичной ссылки.

### 2. Поле `is_archived` в `attempts`

Frontend и backend показывают только попытки, у которых:
- `is_archived = false`

Если попытка архивирована, она не должна открываться ни у испытуемого, ни у специалиста.

### 3. Пустые `answers`

Текущая логика ожидает, что после создания `attempt` пустые `answers` уже существуют для всех активных вопросов теста.
У вас это уже создаётся workflow, и это нужно сохранить.

## API токен NocoBase

1. Создайте API token в NocoBase.
2. Запишите его в `.env` проекта:

```env
API_KEY=your_nocobase_api_token
NOCOBASE_URL=https://flow.skeducator.ru
```

Backend использует этот токен для:
- загрузки попытки по `token`
- получения вопросов и ответов
- перевода `assigned -> in_progress`
- записи `started_at`
- сохранения ответов
- перевода `submitted`
- записи `submitted_at` и `duration`

## Как должна создаваться попытка по ссылке

При создании анонимной попытки в `attempts` должны быть заполнены:
- `test_id`
- `token`
- `status = assigned`
- `is_archived = false`

Дополнительно:
- `started_at` пустое
- `submitted_at` пустое
- `user_id` может быть пустым
- `person_id` может быть пустым

После этого ссылка имеет вид:

```text
https://<domain>/t/<token>
```

## Жизненный цикл попытки

### До старта

Пока пользователь только открыл ссылку или карточку теста:
- статус остаётся `assigned`
- время старта не фиксируется

### При подтверждении старта

Когда пользователь подтверждает начало прохождения, backend пишет:
- `status = in_progress`
- `started_at = текущее время`

### При завершении

Когда пользователь отправляет тест, backend пишет:
- `status = submitted`
- `submitted_at = текущее время`
- `duration = разница между now и started_at`

## Workflow, который должен остаться в NocoBase

Нужен workflow, который после создания `attempt` создаёт пустые `answers` для всех активных вопросов теста.

Минимальная логика:

1. `Trigger`: after create on `attempts`
2. Получить `questions`, где:
   - `test_id = attempt.test_id`
   - `is_active = true`
3. Для каждого вопроса создать `answer`:
   - `attempt_id = attempt.id`
   - `question_id = question.id`

## Публичные права NocoBase

Для анонимного режима больше не требуется открывать наружу запись в диагностические коллекции.

То есть для роли `public` не нужно давать:
- update/create на `attempts`
- update/create/destroy на `answers`
- update/create/destroy на `answer_ranking_items`
- set relation на `answers.options`

Публичный доступ к этим операциям теперь заменён backend-слоем.

## Проверка настройки

Проверьте, что:
- [ ] `API_KEY` записан в `.env`
- [ ] `NOCOBASE_URL` указывает на `https://flow.skeducator.ru`
- [ ] у `attempts` есть `token`
- [ ] у `attempts` есть `is_archived`
- [ ] новая попытка создаётся со статусом `assigned`
- [ ] у новой попытки `is_archived = false`
- [ ] workflow создаёт пустые `answers`
- [ ] ссылка `/t/<token>` открывает попытку без авторизации
- [ ] после подтверждения старта в попытке появляются `started_at` и `status = in_progress`
- [ ] после завершения появляются `submitted_at`, `duration` и `status = submitted`
