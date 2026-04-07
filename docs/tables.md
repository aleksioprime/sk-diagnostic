**Тесты (tests):**
- Идентификационный номер (id)
- Название (title)
- Код теста (code)
- Описание (description)
- Публичный (is_public)
- Пошаговый режим (is_sequential)

**Выдачи тестов (test_assignments):**
- Тест (test_id)
- Название (title)
- Публичный токен (public_token)
- Активный (is_active)

**Вопросы (questions):**
- Тест (test_id)
- Текст вопроса (text)
- Пояснение (description)
- Порядок (order)
- Обязательный (is_required)
- Тип вопроса (question_type):
    - single_choice - Один вариант
    - multiple_choice - Несколько вариантов
    - scale - Шкала
    - ranking - Расставить по порядку
    - text - Свободный текст
    - number - Число
    - yes_no - Да / Нет
- Минимум множественного выбора (min_selections)
- Максимум множественого выбора (max_selections)
- Шкала ответов (scale_id)
- Активный (is_active)
- Код (code)
- Случайный порядок (random)

**Варианты ответа (options):**
- Вопрос (question_id)
- Текст варианта (label)
- Пояснение (description)
- Значение (value)
- Баллы (score)
- Порядок (order)
- Активный (is_active)

**Попытки (attempts):**
- Выдача теста (test_assignment_id)
- Пользователь (person_id)
- Анонимный токен (token)
- Статус (status):
    - assigned - Выдана
    - in_progress - В процессе
    - submitted - Отправлена
- Начало (started_at)
- Завершение (submitted_at)
- Длительность (duration)

**Ответы (answers):**
- Попытка (attempt_id)
- Вопрос (question_id)
- Вариант ответа (option_id)
- Вариант шкалы (scale_option_id)
- Текст (text)
- Число (number)
- Да/Нет (boolean)
- Пропущен (is_skipped)
- Баллы (scores)
- Варианты ответа (options через таблицу связью many_to_many)

**Ответы выбора порядка (answer_ranking_items):**
- Ответ (answer_id)
- Вариант (option_id)
- Позиция (rank)
- Баллы (score)

**Шкалы (scales):**
- Название (title)
- Код (code)
- Пояснение (description)
- Тип (type)
- Минимальное значение (min_value)
- Максимальное значение (max_value)
- Шаг (step)
- Активный (is_active)

**Элементы шкалы (scale_options):**
- Шкала (scale_id)
- Название (label)
- Описание (description)
- Значение (value)
- Баллы (score)
- Порядок (order)
- Активный (is_active)

**Профили расчёта результата (result_profiles):**
- Тест (test_id)
- Название (title)
- Описание (description)
- Скрипт (script)

**Результаты попытки (attempt_results):**
- Попытка (attempt_id)
- Статус (status):
    - pending - Ожидание
    - calculated - Посчитано
    - error - Ошибка
- Балл (score)
- JSON ответов (json_answers)
- JSON результатов (json_results)