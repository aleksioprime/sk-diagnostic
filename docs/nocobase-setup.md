# Настройка NocoBase для SK Diagnostic

## Содержание

- [Обзор архитектуры](#обзор-архитектуры)
- [Коллекции и поля](#коллекции-и-поля)
- [Связи между коллекциями](#связи-между-коллекциями)
- [Настройка API-токена](#настройка-api-токена)
- [Настройка ролей и прав доступа](#настройка-ролей-и-прав-доступа)
- [Workflow: создание пустых ответов](#workflow-создание-пустых-ответов)
- [Анонимные тесты по ссылке](#анонимные-тесты-по-ссылке)
- [Чеклист проверки](#чеклист-проверки)

---

## Обзор архитектуры

В системе два режима работы:

| Режим | Путь запросов | Авторизация |
|-------|---------------|-------------|
| Зарегистрированный пользователь | Frontend → NocoBase напрямую | Bearer-токен пользователя |
| Анонимное прохождение по ссылке | Frontend → FastAPI Backend → NocoBase | API-ключ на бэкенде |

```
┌──────────┐     Авторизованный     ┌───────────┐
│ Frontend ├───────────────────────►│  NocoBase │
│  (Vue)   │                        │    API    │
│          ├──── Анонимный ────┐    │           │
└──────────┘                   │    └───────────┘
                               ▼          ▲
                         ┌──────────┐     │
                         │ Backend  ├─────┘
                         │ (FastAPI)│  API_KEY
                         └──────────┘
```

---

## Коллекции и поля

### tests

Определения диагностических тестов.

| Поле | Тип | Описание |
|------|-----|----------|
| `id` | integer | Первичный ключ |
| `code` | string | Код диагностики (`domiki_emotion`, `motivation` и т.д.) |
| `name` | string | Название теста |
| `is_sequential` | boolean | Пошаговый режим прохождения |
| `is_active` | boolean | Активен ли тест |

---

### questions

Вопросы теста.

| Поле | Тип | Описание |
|------|-----|----------|
| `id` | integer | Первичный ключ |
| `test_id` | integer | FK → `tests` |
| `question_type` | string | Тип: `single_choice`, `multiple_choice`, `scale`, `ranking`, `text`, `number`, `boolean` |
| `text` | string | Текст вопроса |
| `order` | integer | Порядок отображения |
| `is_active` | boolean | Активен ли вопрос |
| `is_required` | boolean | Обязателен ли для завершения теста |
| `scale_id` | integer | FK → `scales` (для типа `scale`) |

---

### options

Варианты ответов для вопросов.

| Поле | Тип | Описание |
|------|-----|----------|
| `id` | integer | Первичный ключ |
| `question_id` | integer | FK → `questions` |
| `text` | string | Текст варианта |
| `order` | integer | Порядок отображения |
| `is_active` | boolean | Активен ли вариант |

---

### scales

Шкалы для вопросов типа `scale`.

| Поле | Тип | Описание |
|------|-----|----------|
| `id` | integer | Первичный ключ |
| `name` | string | Название шкалы |
| `is_active` | boolean | Активна ли шкала |

---

### scale_options

Деления шкалы (например, от 1 до 5).

| Поле | Тип | Описание |
|------|-----|----------|
| `id` | integer | Первичный ключ |
| `scale_id` | integer | FK → `scales` |
| `value` | string | Значение/метка |
| `order` | integer | Порядок отображения |
| `is_active` | boolean | Активна ли деление |

---

### attempts

Попытки прохождения тестов.

| Поле | Тип | Описание |
|------|-----|----------|
| `id` | integer | Первичный ключ |
| `test_id` | integer | FK → `tests` |
| `person_id` | integer | FK → `persons` (может быть пустым для анонимных) |
| `token` | string | **Уникальный** токен для анонимного доступа |
| `status` | string | `assigned` → `in_progress` → `submitted` → `completed` |
| `started_at` | datetime | Время начала прохождения |
| `submitted_at` | datetime | Время отправки |
| `duration` | integer | Длительность в секундах |
| `is_archived` | boolean | Архивирована ли попытка |

**Важно:** поле `token` должно быть уникальным (unique: true), желательно с индексом.

---

### answers

Ответы на вопросы.

| Поле | Тип | Описание |
|------|-----|----------|
| `id` | integer | Первичный ключ |
| `attempt_id` | integer | FK → `attempts` |
| `question_id` | integer | FK → `questions` |
| `option_id` | integer | FK → `options` (одиночный выбор) |
| `scale_option_id` | integer | FK → `scale_options` (шкальный ответ) |
| `text` | string | Текстовый ответ |
| `number` | number | Числовой ответ |
| `boolean` | boolean | Логический ответ |
| `is_skipped` | boolean | Пропущен ли вопрос |

**Связи:**
- `option` — Many-to-one → `options`
- `scale_option` — Many-to-one → `scale_options`
- `question` — Many-to-one → `questions`
- `options` — Many-to-many → `options` (для множественного выбора)

---

### answer_ranking_items

Элементы ранжирования (для вопросов типа `ranking`).

| Поле | Тип | Описание |
|------|-----|----------|
| `id` | integer | Первичный ключ |
| `answer_id` | integer | FK → `answers` |
| `option_id` | integer | FK → `options` |
| `rank` | integer | Позиция в порядке (1, 2, 3, …) |

**Связи:**
- `option` — Many-to-one → `options`

---

### persons

Профили пользователей.

| Поле | Тип | Описание |
|------|-----|----------|
| `id` | integer | Первичный ключ |
| `user_id` | integer | FK → `users` (системный пользователь NocoBase) |
| `short_name` | string | Краткое имя |
| `full_name` | string | Полное имя |
| `first_name` | string | Имя |
| `last_name` | string | Фамилия |
| `email` | string | Email |

---

## Связи между коллекциями

```
tests
  ├── questions (test_id)
  │     ├── options (question_id)
  │     └── scale_id → scales
  │                      └── scale_options (scale_id)
  └── attempts (test_id)
        ├── person_id → persons
        │                 └── user_id → users
        └── answers (attempt_id)
              ├── question_id → questions
              ├── option_id → options
              ├── scale_option_id → scale_options
              ├── options (many-to-many → options)
              └── answer_ranking_items (answer_id)
                    └── option_id → options
```

---

## Настройка API-токена

Бэкенд обращается к NocoBase от имени системного пользователя через API-ключ.

1. Откройте NocoBase → **Settings** → **API keys** (или профиль пользователя → API tokens)
2. Создайте токен для пользователя с полными правами на нужные коллекции
3. Запишите в `.env`:

```env
NOCOBASE_URL=https://flow.skeducator.ru
API_KEY=your_nocobase_api_token
```

Бэкенд использует этот токен для всех операций анонимного режима:
загрузка попыток, вопросов, ответов, сохранение ответов, смена статусов.

---

## Настройка ролей и прав доступа

### Роль `psycho` (специалист)

Зарегистрированные пользователи с ролью `psycho` работают с NocoBase напрямую.
Нужны права:

| Коллекция | Чтение | Запись | Удаление |
|-----------|--------|--------|----------|
| `tests` | ✅ | — | — |
| `questions` | ✅ | — | — |
| `options` | ✅ | — | — |
| `scales` | ✅ | — | — |
| `scale_options` | ✅ | — | — |
| `attempts` | ✅ | ✅ | — |
| `answers` | ✅ | ✅ | — |
| `answer_ranking_items` | ✅ | ✅ | ✅ |
| `persons` | ✅ (свой) | — | — |

### Роль `public`

Для анонимного режима **не нужны** права на запись в диагностические коллекции — всё делает бэкенд через API-ключ.

---

## Workflow: создание пустых ответов

При создании новой попытки (`attempt`) необходимо автоматически создать пустые записи `answers` для всех активных вопросов теста.

### Настройка в NocoBase

1. **Trigger:** After create on `attempts`
2. **Шаг 1:** Получить вопросы:
   - Коллекция: `questions`
   - Фильтр: `test_id = {{attempt.test_id}}` AND `is_active = true`
3. **Шаг 2:** Для каждого вопроса создать запись:
   - Коллекция: `answers`
   - Поля:
     - `attempt_id = {{attempt.id}}`
     - `question_id = {{question.id}}`

Без этого workflow тест не сможет быть пройден — приложение ожидает, что при загрузке попытки уже существуют пустые ответы для всех вопросов.

---

## Анонимные тесты по ссылке

### Как создать анонимную попытку

Для формирования ссылки на анонимное прохождение нужно создать запись в `attempts` со следующими полями:

| Поле | Значение |
|------|----------|
| `test_id` | ID нужного теста |
| `token` | Уникальная строка (UUID, nanoid и т.д.) |
| `status` | `assigned` |
| `is_archived` | `false` |
| `person_id` | Пустое (или ID персоны, если известна) |
| `started_at` | Пустое |
| `submitted_at` | Пустое |

### Формат ссылки

```
https://<домен>/t/<token>
```

Примеры:
```
https://diagnostic.example.com/t/abc123def456
https://diagnostic.example.com/t/550e8400-e29b-41d4-a716-446655440000
```

### Жизненный цикл попытки

```
    Создание попытки           Клик «Начать»          Клик «Отправить»
         в NocoBase             в приложении            в приложении
              │                      │                       │
              ▼                      ▼                       ▼
┌─────────────────┐    ┌──────────────────┐    ┌───────────────────────┐
│ status: assigned│───►│status: in_progress│───►│  status: submitted    │
│ started_at: null│    │started_at: <now> │    │  submitted_at: <now>  │
│ duration: null  │    │                  │    │  duration: <секунды>  │
└─────────────────┘    └──────────────────┘    └───────────────────────┘
```

### Что происходит при открытии ссылки

1. Фронтенд запрашивает у бэкенда: `GET /api/v1/public/attempts/{token}`
2. Бэкенд ищет в NocoBase попытку с `token = <token>` и `is_archived ≠ true`
3. Если найдена — загружает всю связанную информацию (тест, вопросы, варианты, ответы, шкалы)
4. Отдаёт фронтенду готовый пакет данных
5. Пользователь видит тест и может начать прохождение

### Ограничения

- Токен должен быть **уникальным** — при дублях бэкенд вернёт ошибку
- Если `is_archived = true` — попытка не будет найдена
- Если статус не `assigned` и не `in_progress` — попытка считается завершённой
- Workflow должен успеть создать пустые `answers` до того, как пользователь откроет ссылку

---

## Чеклист проверки

### Общая настройка

- [ ] NocoBase запущен и доступен по `NOCOBASE_URL`
- [ ] API-токен создан и записан в `.env` как `API_KEY`
- [ ] Все коллекции созданы с полями из таблиц выше
- [ ] Связи между коллекциями настроены
- [ ] Роль `psycho` имеет нужные права
- [ ] Workflow для создания пустых ответов работает

### Анонимные тесты

- [ ] У коллекции `attempts` есть поле `token` (unique: true)
- [ ] У коллекции `attempts` есть поле `is_archived` (boolean)
- [ ] Создана попытка со статусом `assigned` и заполненным `token`
- [ ] Workflow создал пустые `answers` для всех активных вопросов теста
- [ ] Ссылка `/t/<token>` открывается без авторизации
- [ ] После начала прохождения: `status = in_progress`, `started_at` заполнено
- [ ] После завершения: `status = submitted`, `submitted_at` и `duration` заполнены
