/** Черновик вопросов и шкал в редакторе методики: у новых элементов ещё нет id, поэтому нужен свой ключ. */

let counter = 0
export const newKey = () => `new-${++counter}`

export const QUESTION_TYPES = [
  { value: 'scale', label: 'Шкала' },
  { value: 'single_choice', label: 'Один вариант' },
  { value: 'ranking', label: 'Упорядочить варианты' },
  { value: 'text', label: 'Текст' },
  { value: 'number', label: 'Число' },
  { value: 'yes_no', label: 'Да / нет' },
]

export const hasOptions = (type) => type === 'single_choice' || type === 'ranking'

export function swap(list, from, to) {
  const moved = list[from]
  list[from] = list[to]
  list[to] = moved
}

function optionsWithKeys(options) {
  return options.map((option) => ({ ...option, key: option.id ?? newKey() }))
}

/** Вопрос или шкала с ответа API → черновик с ключами. */
export function withKeys(item) {
  return { ...item, key: item.id ?? newKey(), options: optionsWithKeys(item.options || []) }
}

/** Заготовка вариантов: новому вопросу с выбором сразу есть что заполнять. */
export function starterOptions() {
  return optionsWithKeys(
    ['Первый вариант', 'Второй вариант'].map((label, n) => ({ id: null, label, description: '', value: String(n + 1), score: n + 1 })),
  )
}

export function newQuestion() {
  return withKeys({
    id: null,
    code: null,
    text: '',
    description: '',
    question_type: 'single_choice',
    is_required: true,
    is_random: false,
    scale_id: null,
    options: starterOptions(),
  })
}

function optionBody({ id, label, description, value, score }) {
  return { id, label, description, value: String(value ?? ''), score: score === '' || score === null || score === undefined ? null : Number(score) }
}

export function scaleBody(scale) {
  return { title: scale.title, description: scale.description, options: scale.options.map(optionBody) }
}

export function contentBody(content) {
  return {
    title: content.title,
    description: content.description,
    is_sequential: content.is_sequential,
    questions: content.questions.map((q) => ({
      id: q.id,
      code: q.code || null,
      text: q.text,
      description: q.description,
      question_type: q.question_type,
      is_required: q.is_required,
      is_random: q.is_random,
      scale_id: q.question_type === 'scale' ? q.scale_id : null,
      options: hasOptions(q.question_type) ? q.options.map(optionBody) : [],
    })),
  }
}

/** Копия вопроса: новые id появятся при сохранении, код у каждого вопроса свой. */
export function copyQuestion(question) {
  return {
    ...question,
    id: null,
    code: null,
    key: newKey(),
    options: question.options.map((option) => ({ ...option, id: null, key: newKey() })),
  }
}

/** Что не заполнено в вопросе. Сервер проверит то же, но здесь понятнее, какой вопрос поправить. */
export function questionProblem(q) {
  if (!q.text.trim()) return 'заполните текст'
  if (q.question_type === 'scale' && !q.scale_id) return 'выберите шкалу'
  if (hasOptions(q.question_type)) {
    if (!q.options.length) return 'добавьте варианты ответа'
    if (q.options.some((o) => !o.label.trim())) return 'заполните подписи вариантов'
  }
  return ''
}

export function contentProblem(content) {
  if (!content.title.trim()) return 'Заполните название методики'
  for (const [index, q] of content.questions.entries()) {
    const problem = questionProblem(q)
    if (problem) return `Вопрос ${index + 1}: ${problem}`
  }
  return ''
}

/** Короткое описание ответа для свёрнутой строки вопроса. */
export function answerSummary(question, scales) {
  const type = QUESTION_TYPES.find((item) => item.value === question.question_type)?.label ?? question.question_type
  if (question.question_type === 'scale') {
    const scale = scales.find((item) => item.id === question.scale_id)
    return scale ? `${type}: ${scale.title}` : `${type}: не выбрана`
  }
  return hasOptions(question.question_type) ? `${type} · ${question.options.length}` : type
}
