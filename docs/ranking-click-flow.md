# Что происходит при клике на цвет в вопросе ранжирования

## Общая схема

```
Клик на цвет → Компонент → AttemptView → attemptAnswers.js → NocoBase API → Обновление UI
```

---

## Пошаговый разбор

### 1. Пользователь кликает на цвет

**Файл:** `DomikiColorRankingQuestion.vue`

Компонент рисует палитру неиспользованных цветов. При клике отправляется событие:

```vue
@click="$emit('select', option.id)"
```

Никаких запросов — просто передача ID цвета наверх.

---

### 2. AttemptView ловит событие

**Файл:** `AttemptView.vue`

```vue
<DomikiColorRankingQuestion
  @select="appendRankingSelection(question, $event)"
  @remove="removeRankingSelection(question, $event)"
  @reset="resetRankingSelection(question)"
/>
```

Вызывается функция `appendRankingSelection(question, optionId)`.

---

### 3. Формируется новый порядок цветов

**Файл:** `AttemptView.vue` → `appendRankingSelection`

```js
const currentOrder = question.rankingItems.map(item => item.option_id) // текущие выбранные
const newOrder = [...currentOrder, optionId]                           // + новый цвет в конец
```

Если цвет уже есть в списке — функция прекращает работу (защита от дублей).

---

### 4. Включается индикатор загрузки

**Файл:** `AttemptView.vue` → `withSaving`

```js
savingState[question.id] = { pending: true, error: '' }
```

Кнопки блокируются (`disabled`), пока идёт сохранение.

---

### 5. Вызывается `saveRanking`

**Файл:** `attemptAnswers.js`

Это основная функция. Она выполняет **3 последовательных шага**:

#### Шаг A — Загрузить текущее состояние из базы

```
GET /answer_ranking_items:list?filter={"answer_id": 123}&appends=option&sort=rank,id
```

Получаем список уже сохранённых элементов ранжирования.

#### Шаг B — Обновить элементы (параллельно, одним запросом `Promise.all`)

Формируются операции:

| Ситуация | Действие | Запрос |
|----------|----------|--------|
| Цвет был, но больше не нужен | Удалить | `DELETE /answer_ranking_items:destroy?filterByTk={id}` |
| Цвет уже был, изменился ранг | Обновить | `POST /answer_ranking_items:update?filterByTk={id}` |
| Цвет новый | Создать | `POST /answer_ranking_items:create` |

Все эти операции выполняются **одновременно** — не по очереди.

#### Шаг C — Получить итоговое состояние (параллельно)

Две операции одновременно:

```
POST /answers:update?filterByTk={answerId}           → пометить ответ как не пропущенный
GET  /answer_ranking_items:list?filter={answer_id}    → загрузить финальный порядок
```

---

### 6. Обновляется локальное состояние

**Файл:** `AttemptView.vue`

```js
patchAnswer(question.answer.id, updatedAnswer)   // обновить объект ответа
rankingItems.value = [...updatedRankingItems]      // обновить список ранжирования
```

Vue реактивно перерисовывает компонент — цвет перемещается из палитры в выбранный ряд.

---

### 7. Индикатор загрузки снимается

```js
savingState[question.id] = { pending: false, error: '' }
globalNotice.value = 'Ответ сохранён'
```

---

## Сколько HTTP-запросов делается за один клик

| Этап | Запросов | Выполнение |
|------|----------|------------|
| Загрузка текущего состояния | 1 | последовательно |
| Удаление + обновление + создание | 1–N | **параллельно** |
| Пометка ответа + загрузка итога | 2 | **параллельно** |

**Типичный пример** — выбор 6-го цвета из 8:
- 1 запрос — загрузить 5 существующих элементов
- 6 запросов параллельно — обновить 5 существующих + создать 1 новый
- 2 запроса параллельно — обновить ответ + загрузить итог
- **Итого:** 9 запросов, но из них 8 идут параллельно → **3 последовательных раунда**

---

## Визуально

```
Клик
  │
  ▼
┌─────────────────────────────┐
│ savingState = pending: true │  ← кнопки заблокированы
└─────────────┬───────────────┘
              ▼
      GET existing items          ~160 ms
              │
              ▼
   ┌──────────┼──────────┐
   │          │          │
 DELETE    UPDATE     CREATE       ~200 ms (параллельно)
   │          │          │
   └──────────┼──────────┘
              ▼
      ┌───────┼───────┐
      │               │
  UPDATE answer   GET items       ~330 ms (параллельно)
      │               │
      └───────┼───────┘
              ▼
┌─────────────────────────────┐
│ savingState = pending: false│  ← кнопки разблокированы
│ «Ответ сохранён»           │
└─────────────────────────────┘

Итого: ~500–700 ms
```
