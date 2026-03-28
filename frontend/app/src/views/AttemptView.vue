<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { RouterLink } from 'vue-router'
import api from '../api'
import { get, list, create, update, destroy, normalizeId, toFilter, dedupe } from '../utils/nocobase'
import { formatDateTime, formatDuration, getAttemptStatusMeta, isNil, stringifyValue } from '../utils/format'
import logger from '../utils/logger'

const props = defineProps({
  attemptId: {
    type: [String, Number],
    required: true,
  },
})

const loading = ref(true)
const submitting = ref(false)
const error = ref('')
const globalNotice = ref('')

const attempt = ref(null)
const questions = ref([])
const answers = ref([])
const options = ref([])
const scales = ref([])
const scaleOptions = ref([])
const rankingItems = ref([])

const textDrafts = reactive({})
const numberDrafts = reactive({})
const savingState = reactive({})

const answersByQuestionId = computed(() => {
  return Object.fromEntries(answers.value.map((answer) => [answer.question_id, answer]))
})

const optionsByQuestionId = computed(() => {
  return options.value.reduce((map, option) => {
    if (!map[option.question_id]) map[option.question_id] = []
    map[option.question_id].push(option)
    return map
  }, {})
})

const scalesById = computed(() => Object.fromEntries(scales.value.map((scale) => [scale.id, scale])))

const scaleOptionsByScaleId = computed(() => {
  return scaleOptions.value.reduce((map, option) => {
    if (!map[option.scale_id]) map[option.scale_id] = []
    map[option.scale_id].push(option)
    return map
  }, {})
})

const rankingByAnswerId = computed(() => {
  return rankingItems.value.reduce((map, item) => {
    if (!map[item.answer_id]) map[item.answer_id] = []
    map[item.answer_id].push(item)
    return map
  }, {})
})

const normalizedQuestions = computed(() => {
  return questions.value.map((question) => {
    const answer = answersByQuestionId.value[question.id] || null
    const questionOptions = optionsByQuestionId.value[question.id] || []
    const scale = scalesById.value[question.scale_id] || null
    const questionScaleOptions = scaleOptionsByScaleId.value[question.scale_id] || []
    const questionRanking = answer ? rankingByAnswerId.value[answer.id] || [] : []

    return {
      ...question,
      answer,
      options: questionOptions,
      scale,
      scaleOptions: questionScaleOptions,
      rankingItems: questionRanking,
    }
  })
})

const completedRequiredCount = computed(() => {
  return normalizedQuestions.value.filter((question) => !question.is_required || isQuestionAnswered(question)).length
})

const canSubmit = computed(() => {
  return normalizedQuestions.value.every((question) => !question.is_required || isQuestionAnswered(question))
})

const attemptStatus = computed(() => getAttemptStatusMeta(attempt.value?.status))
const isReadOnly = computed(() => ['submitted', 'completed'].includes(attempt.value?.status))

function initDrafts() {
  normalizedQuestions.value.forEach((question) => {
    if (question.answer) {
      textDrafts[question.answer.id] = question.answer.text || ''
      numberDrafts[question.answer.id] = question.answer.number ?? ''
    }
  })
}

function isQuestionAnswered(question) {
  const answer = question.answer
  if (!answer) return false
  if (answer.is_skipped) return false
  if (!isNil(answer.option_id)) return true
  if (!isNil(answer.scale_option_id)) return true
  if (!isNil(answer.boolean)) return true
  if (!isNil(answer.number)) return true
  if (!isNil(answer.text)) return true
  if (Array.isArray(answer.options) && answer.options.length) return true
  if ((rankingByAnswerId.value[answer.id] || []).length) return true
  return false
}

function answerSelectedOptions(answer) {
  return Array.isArray(answer?.options) ? answer.options.map((option) => option.id) : []
}

async function saveAnswerValue(answerId, payload) {
  logger.log('saveAnswerValue', { answerId, payload })
  return update('answers', answerId, payload)
}

async function saveMultipleChoice(answerId, optionIds) {
  logger.log('saveMultipleChoice', { answerId, optionIds })
  const ids = dedupe(optionIds.map((value) => normalizeId(value)))
  const strategies = [
    () => update('answers', answerId, { options: ids, is_skipped: false }),
    () => update('answers', answerId, { options: ids.map((id) => ({ id })), is_skipped: false }),
    () => api.post(`/answers/${answerId}/options:set`, { values: ids }),
    () => api.post(`/answers/${answerId}/options:set`, ids),
  ]

  let lastError = null
  for (const strategy of strategies) {
    try {
      const response = await strategy()
      return response?.data?.data || response
    } catch (err) {
      lastError = err
    }
  }
  throw lastError
}

async function saveRanking(answerId, rankedOptionIds) {
  logger.log('saveRanking', { answerId, rankedOptionIds })
  const existingItems = await list('answer_ranking_items', {
    filter: toFilter({ answer_id: normalizeId(answerId) }),
    sort: 'rank,id',
  })

  const existingByOptionId = new Map(existingItems.map((item) => [item.option_id, item]))
  const nextOptionIds = dedupe(rankedOptionIds.map((value) => normalizeId(value)))

  const deletions = existingItems.filter((item) => !nextOptionIds.includes(item.option_id))
  await Promise.all(deletions.map((item) => destroy('answer_ranking_items', item.id)))

  await Promise.all(nextOptionIds.map((optionId, index) => {
    const existing = existingByOptionId.get(optionId)
    const payload = { answer_id: normalizeId(answerId), option_id: optionId, rank: index + 1 }
    return existing
      ? update('answer_ranking_items', existing.id, payload)
      : create('answer_ranking_items', payload)
  }))

  await update('answers', answerId, { is_skipped: false })

  return list('answer_ranking_items', {
    filter: toFilter({ answer_id: normalizeId(answerId) }),
    appends: 'option',
    sort: 'rank,id',
  })
}

async function withSaving(questionId, action) {
  savingState[questionId] = { pending: true, error: '' }
  globalNotice.value = ''

  try {
    await action()
    savingState[questionId] = { pending: false, error: '' }
    globalNotice.value = 'Ответ сохранён'
  } catch {
    savingState[questionId] = { pending: false, error: 'Не удалось сохранить ответ' }
  }
}

function patchAnswer(answerId, patch) {
  answers.value = answers.value.map((answer) => {
    return answer.id === answerId ? { ...answer, ...patch } : answer
  })
}

async function saveSingleChoice(question, optionId) {
  if (!question.answer || isReadOnly.value) return
  await withSaving(question.id, async () => {
    const updated = await saveAnswerValue(question.answer.id, {
      option_id: optionId,
      scale_option_id: null,
      text: null,
      number: null,
      boolean: null,
      is_skipped: false,
    })
    patchAnswer(question.answer.id, { ...question.answer, ...updated, option_id: optionId, is_skipped: false })
  })
}

async function saveScaleOption(question, scaleOptionId) {
  if (!question.answer || isReadOnly.value) return
  await withSaving(question.id, async () => {
    const updated = await saveAnswerValue(question.answer.id, {
      scale_option_id: scaleOptionId,
      option_id: null,
      text: null,
      number: null,
      boolean: null,
      is_skipped: false,
    })
    patchAnswer(question.answer.id, { ...question.answer, ...updated, scale_option_id: scaleOptionId, is_skipped: false })
  })
}

async function saveScaleNumber(question) {
  if (!question.answer || isReadOnly.value) return
  await withSaving(question.id, async () => {
    const raw = numberDrafts[question.answer.id]
    const value = raw === '' ? null : Number(raw)
    const updated = await saveAnswerValue(question.answer.id, {
      number: value,
      option_id: null,
      scale_option_id: null,
      text: null,
      boolean: null,
      is_skipped: false,
    })
    patchAnswer(question.answer.id, { ...question.answer, ...updated, number: value, scale_option_id: null, is_skipped: false })
  })
}

async function saveBoolean(question, value) {
  if (!question.answer || isReadOnly.value) return
  await withSaving(question.id, async () => {
    const updated = await saveAnswerValue(question.answer.id, {
      boolean: value,
      option_id: null,
      scale_option_id: null,
      text: null,
      number: null,
      is_skipped: false,
    })
    patchAnswer(question.answer.id, { ...question.answer, ...updated, boolean: value, is_skipped: false })
  })
}

async function saveNumber(question) {
  if (!question.answer || isReadOnly.value) return
  await withSaving(question.id, async () => {
    const raw = numberDrafts[question.answer.id]
    const value = raw === '' ? null : Number(raw)
    const updated = await saveAnswerValue(question.answer.id, {
      number: value,
      option_id: null,
      scale_option_id: null,
      text: null,
      boolean: null,
      is_skipped: false,
    })
    patchAnswer(question.answer.id, { ...question.answer, ...updated, number: value, is_skipped: false })
  })
}

async function saveText(question) {
  if (!question.answer || isReadOnly.value) return
  await withSaving(question.id, async () => {
    const value = textDrafts[question.answer.id] || null
    const updated = await saveAnswerValue(question.answer.id, {
      text: value,
      option_id: null,
      scale_option_id: null,
      number: null,
      boolean: null,
      is_skipped: false,
    })
    patchAnswer(question.answer.id, { ...question.answer, ...updated, text: value, is_skipped: false })
  })
}

async function toggleMultiple(question, optionId) {
  if (!question.answer || isReadOnly.value) return
  const selectedIds = answerSelectedOptions(question.answer)
  const isSelected = selectedIds.includes(optionId)
  const nextIds = isSelected
    ? selectedIds.filter((id) => id !== optionId)
    : [...selectedIds, optionId]

  if (question.max_selections && nextIds.length > Number(question.max_selections)) {
    savingState[question.id] = { pending: false, error: `Можно выбрать не больше ${question.max_selections}` }
    return
  }

  await withSaving(question.id, async () => {
    await saveMultipleChoice(question.answer.id, nextIds)
    const nextOptions = question.options.filter((option) => nextIds.includes(option.id))
    patchAnswer(question.answer.id, { ...question.answer, options: nextOptions, is_skipped: false })
  })
}

async function moveRanking(question, optionId, direction) {
  if (!question.answer || isReadOnly.value) return
  const currentOrder = question.rankingItems.length
    ? question.rankingItems.map((item) => item.option_id)
    : question.options.map((option) => option.id)

  const index = currentOrder.indexOf(optionId)
  const targetIndex = index + direction
  if (index === -1 || targetIndex < 0 || targetIndex >= currentOrder.length) return

  const next = [...currentOrder]
  ;[next[index], next[targetIndex]] = [next[targetIndex], next[index]]

  await withSaving(question.id, async () => {
    const updatedItems = await saveRanking(question.answer.id, next)
    rankingItems.value = [
      ...rankingItems.value.filter((item) => item.answer_id !== question.answer.id),
      ...updatedItems,
    ]
  })
}

async function toggleSkip(question) {
  if (!question.answer || isReadOnly.value || question.is_required) return
  const nextValue = !question.answer.is_skipped
  await withSaving(question.id, async () => {
    const updated = await saveAnswerValue(question.answer.id, {
      option_id: null,
      scale_option_id: null,
      text: null,
      number: null,
      boolean: null,
      is_skipped: nextValue,
    })
    textDrafts[question.answer.id] = ''
    numberDrafts[question.answer.id] = ''
    patchAnswer(question.answer.id, {
      ...question.answer,
      ...updated,
      option_id: null,
      scale_option_id: null,
      text: null,
      number: null,
      boolean: null,
      options: [],
      is_skipped: nextValue,
    })
    rankingItems.value = rankingItems.value.filter((item) => item.answer_id !== question.answer.id)
  })
}

async function handleSubmit() {
  if (!attempt.value || isReadOnly.value || !canSubmit.value) return
  submitting.value = true
  error.value = ''

  try {
    const submittedAt = new Date().toISOString()
    const startedAt = attempt.value.started_at ? new Date(attempt.value.started_at).getTime() : null
    const duration = startedAt ? Math.max(0, Math.round((Date.now() - startedAt) / 1000)) : attempt.value.duration

    attempt.value = await update('attempts', attempt.value.id, {
      status: 'submitted',
      submitted_at: submittedAt,
      duration,
    })
    globalNotice.value = 'Попытка отправлена'
  } catch {
    error.value = 'Не удалось отправить попытку'
  } finally {
    submitting.value = false
  }
}

function readOnlySummary(question) {
  const answer = question.answer
  if (!answer) return 'Ответ не найден'
  if (answer.is_skipped) return 'Пропущено'
  if (!isNil(answer.option_id)) {
    return question.options.find((option) => option.id === answer.option_id)?.label || `Вариант #${answer.option_id}`
  }
  if (Array.isArray(answer.options) && answer.options.length) {
    return answer.options.map((option) => option.label).join(', ')
  }
  if (!isNil(answer.scale_option_id)) {
    return question.scaleOptions.find((option) => option.id === answer.scale_option_id)?.label || `Значение #${answer.scale_option_id}`
  }
  if (!isNil(answer.boolean)) return answer.boolean ? 'Да' : 'Нет'
  if (!isNil(answer.number)) return stringifyValue(answer.number)
  if (!isNil(answer.text)) return answer.text
  if (question.rankingItems.length) {
    return question.rankingItems
      .slice()
      .sort((left, right) => left.rank - right.rank)
      .map((item) => item.option?.label || `Вариант #${item.option_id}`)
      .join(' → ')
  }
  return '—'
}

async function loadData() {
  loading.value = true
  error.value = ''

  try {
    logger.log('loadData: fetchAttemptQuestionBundle', { attemptId: props.attemptId })
    const loadedAttempt = await get('attempts', props.attemptId, { appends: 'test,person' })
    const testId = loadedAttempt?.test_id ?? loadedAttempt?.test?.id

    const [loadedQuestions, loadedAnswers] = await Promise.all([
      list('questions', {
        filter: toFilter({ test_id: testId, is_active: true }),
        sort: 'order,id',
      }),
      list('answers', {
        filter: toFilter({ attempt_id: normalizeId(props.attemptId) }),
        appends: 'option,scale_option,options,question',
        sort: 'id',
      }),
    ])

    const questionIds = loadedQuestions.map((q) => q.id)
    const scaleIds = dedupe(loadedQuestions.map((q) => q.scale_id))

    const [loadedOptions, loadedScales, loadedScaleOptions, loadedRankingItems] = await Promise.all([
      questionIds.length ? list('options', {
        filter: toFilter({ question_id: { $in: questionIds }, is_active: true }),
        sort: 'order,id',
      }) : Promise.resolve([]),
      scaleIds.length ? list('scales', {
        filter: toFilter({ id: { $in: scaleIds }, is_active: true }),
        sort: 'id',
      }) : Promise.resolve([]),
      scaleIds.length ? list('scale_options', {
        filter: toFilter({ scale_id: { $in: scaleIds }, is_active: true }),
        sort: 'order,id',
      }) : Promise.resolve([]),
      loadedAnswers.length ? list('answer_ranking_items', {
        filter: toFilter({ answer_id: { $in: loadedAnswers.map((a) => a.id) } }),
        appends: 'option',
        sort: 'rank,id',
      }) : Promise.resolve([]),
    ])

    attempt.value = loadedAttempt
    questions.value = loadedQuestions
    answers.value = loadedAnswers
    options.value = loadedOptions
    scales.value = loadedScales
    scaleOptions.value = loadedScaleOptions
    rankingItems.value = loadedRankingItems
    initDrafts()
  } catch {
    error.value = 'Не удалось загрузить тест'
  } finally {
    loading.value = false
  }
}

onMounted(loadData)
</script>

<template>
  <section class="w-full">
    <div class="mb-5 flex flex-wrap items-center gap-3">
      <RouterLink :to="{ name: 'assigned-tests' }" class="ghost-button no-underline">
        ← К списку попыток
      </RouterLink>
      <span v-if="attempt" class="badge" :class="attemptStatus.className">{{ attemptStatus.label }}</span>
      <span v-if="globalNotice" class="badge bg-emerald-100 text-emerald-700">{{ globalNotice }}</span>
    </div>

    <div v-if="loading" class="glass-panel p-10 text-center text-sm text-slate-500">Загрузка теста…</div>
    <div v-else-if="error" class="glass-panel p-10 text-center text-sm text-red-700">{{ error }}</div>
    <div v-else-if="attempt" class="grid gap-5 xl:grid-cols-[minmax(0,1fr)_21rem]">
      <div class="grid gap-5">
        <div class="glass-panel p-6 sm:p-7">
          <p class="mb-2 text-sm font-semibold uppercase tracking-[0.24em] text-slate-400">{{ attempt.test?.code || 'test' }}</p>
          <h1 class="text-3xl font-semibold tracking-tight text-slate-900">{{ attempt.test?.title || `Тест #${attempt.test_id}` }}</h1>
          <p v-if="attempt.test?.description" class="mt-3 max-w-3xl text-sm leading-7 text-slate-600">
            {{ attempt.test.description }}
          </p>
          <div class="mt-5 flex flex-wrap gap-3 text-sm text-slate-500">
            <span>Начало: {{ formatDateTime(attempt.started_at) }}</span>
            <span>Длительность: {{ formatDuration(attempt.duration) }}</span>
            <span>Вопросов: {{ normalizedQuestions.length }}</span>
          </div>
        </div>

        <div
          v-for="(question, index) in normalizedQuestions"
          :key="question.id"
          class="glass-panel overflow-hidden p-5 sm:p-6"
        >
          <div class="flex flex-wrap items-start justify-between gap-3">
            <div>
              <p class="text-xs font-semibold uppercase tracking-[0.22em] text-slate-400">Вопрос {{ index + 1 }}</p>
              <h2 class="mt-2 text-xl font-semibold text-slate-900">{{ question.text }}</h2>
              <p v-if="question.description" class="mt-2 text-sm leading-6 text-slate-500">{{ question.description }}</p>
            </div>

            <div class="flex flex-wrap items-center gap-2">
              <span v-if="question.is_required" class="badge bg-orange-100 text-orange-700">Обязательный</span>
              <button
                v-if="!question.is_required && !isReadOnly"
                class="ghost-button"
                @click="toggleSkip(question)"
              >
                {{ question.answer?.is_skipped ? 'Вернуть вопрос' : 'Пропустить' }}
              </button>
            </div>
          </div>

          <div v-if="savingState[question.id]?.error" class="mt-4 rounded-2xl bg-red-50 px-4 py-3 text-sm text-red-700">
            {{ savingState[question.id].error }}
          </div>

          <div v-if="isReadOnly" class="mt-5 rounded-[26px] border border-slate-200/70 bg-white/85 p-5">
            <div class="text-xs font-semibold uppercase tracking-[0.2em] text-slate-400">Сохранённый ответ</div>
            <div class="mt-3 text-sm leading-7 text-slate-800">{{ readOnlySummary(question) }}</div>
          </div>

          <div v-else class="mt-5">
            <div v-if="question.question_type === 'single_choice'" class="grid gap-3">
              <button
                v-for="option in question.options"
                :key="option.id"
                class="cursor-pointer rounded-[24px] border px-4 py-4 text-left transition"
                :class="question.answer?.option_id === option.id ? 'border-primary bg-primary/8 text-slate-900 shadow-sm' : 'border-slate-200/80 bg-white/80 text-slate-700 hover:border-primary/40'"
                @click="saveSingleChoice(question, option.id)"
              >
                <div class="font-medium">{{ option.label }}</div>
                <div v-if="option.description" class="mt-1 text-sm text-slate-500">{{ option.description }}</div>
              </button>
            </div>

            <div v-else-if="question.question_type === 'multiple_choice'" class="grid gap-3">
              <div class="rounded-[24px] bg-slate-50/80 px-4 py-3 text-sm text-slate-600">
                Выбрано {{ answerSelectedOptions(question.answer).length }}<span v-if="question.max_selections"> из максимум {{ question.max_selections }}</span>
              </div>
              <button
                v-for="option in question.options"
                :key="option.id"
                class="cursor-pointer rounded-[24px] border px-4 py-4 text-left transition"
                :class="answerSelectedOptions(question.answer).includes(option.id) ? 'border-primary bg-primary/8 text-slate-900 shadow-sm' : 'border-slate-200/80 bg-white/80 text-slate-700 hover:border-primary/40'"
                @click="toggleMultiple(question, option.id)"
              >
                <div class="flex items-start justify-between gap-3">
                  <div>
                    <div class="font-medium">{{ option.label }}</div>
                    <div v-if="option.description" class="mt-1 text-sm text-slate-500">{{ option.description }}</div>
                  </div>
                  <span class="badge" :class="answerSelectedOptions(question.answer).includes(option.id) ? 'bg-primary/12 text-primary' : 'bg-slate-100 text-slate-500'">
                    {{ answerSelectedOptions(question.answer).includes(option.id) ? 'Выбрано' : 'Выбрать' }}
                  </span>
                </div>
              </button>
            </div>

            <div v-else-if="question.question_type === 'scale' && question.scaleOptions.length" class="grid gap-3">
              <button
                v-for="option in question.scaleOptions"
                :key="option.id"
                class="cursor-pointer rounded-[24px] border px-4 py-4 text-left transition"
                :class="question.answer?.scale_option_id === option.id ? 'border-primary bg-primary/8 text-slate-900 shadow-sm' : 'border-slate-200/80 bg-white/80 text-slate-700 hover:border-primary/40'"
                @click="saveScaleOption(question, option.id)"
              >
                <div class="flex items-center justify-between gap-3">
                  <div>
                    <div class="font-medium">{{ option.label }}</div>
                    <div v-if="option.description" class="mt-1 text-sm text-slate-500">{{ option.description }}</div>
                  </div>
                  <span class="badge bg-slate-100 text-slate-600">{{ option.value }}</span>
                </div>
              </button>
            </div>

            <div v-else-if="question.question_type === 'scale'" class="grid gap-4">
              <div class="rounded-[24px] border border-slate-200/80 bg-white/85 p-4">
                <div class="mb-3 flex items-center justify-between gap-3">
                  <div>
                    <div class="text-sm font-semibold text-slate-900">Шкала</div>
                    <div class="mt-1 text-sm text-slate-500">
                      {{ question.scale?.title || 'Числовая шкала' }}
                      <span v-if="question.scale?.min_value != null && question.scale?.max_value != null">
                        · {{ question.scale.min_value }}–{{ question.scale.max_value }}
                      </span>
                    </div>
                  </div>
                  <span class="badge bg-slate-100 text-slate-600">{{ numberDrafts[question.answer?.id] || '—' }}</span>
                </div>
                <input
                  v-model="numberDrafts[question.answer?.id]"
                  class="w-full accent-primary"
                  type="range"
                  :min="question.scale?.min_value ?? 0"
                  :max="question.scale?.max_value ?? 10"
                  :step="question.scale?.step ?? 1"
                  @change="saveScaleNumber(question)"
                />
                <div class="mt-3 flex items-center justify-between text-xs text-slate-400">
                  <span>{{ question.scale?.min_value ?? 0 }}</span>
                  <span>{{ question.scale?.max_value ?? 10 }}</span>
                </div>
              </div>
            </div>

            <div v-else-if="question.question_type === 'yes_no'" class="grid gap-3 sm:grid-cols-2">
              <button
                class="cursor-pointer rounded-[24px] border px-4 py-5 text-left transition"
                :class="question.answer?.boolean === true ? 'border-primary bg-primary/8 text-slate-900 shadow-sm' : 'border-slate-200/80 bg-white/80 text-slate-700 hover:border-primary/40'"
                @click="saveBoolean(question, true)"
              >
                <div class="text-lg font-semibold">Да</div>
                <div class="mt-1 text-sm text-slate-500">Утверждение подходит</div>
              </button>
              <button
                class="cursor-pointer rounded-[24px] border px-4 py-5 text-left transition"
                :class="question.answer?.boolean === false ? 'border-primary bg-primary/8 text-slate-900 shadow-sm' : 'border-slate-200/80 bg-white/80 text-slate-700 hover:border-primary/40'"
                @click="saveBoolean(question, false)"
              >
                <div class="text-lg font-semibold">Нет</div>
                <div class="mt-1 text-sm text-slate-500">Утверждение не подходит</div>
              </button>
            </div>

            <div v-else-if="question.question_type === 'text'">
              <textarea
                v-model="textDrafts[question.answer?.id]"
                class="field-input min-h-36 resize-y"
                placeholder="Введите ответ"
                @blur="saveText(question)"
              ></textarea>
              <p class="mt-2 text-xs text-slate-400">Ответ сохраняется при потере фокуса.</p>
            </div>

            <div v-else-if="question.question_type === 'number'">
              <input
                v-model="numberDrafts[question.answer?.id]"
                class="field-input max-w-xs"
                type="number"
                placeholder="Введите число"
                @blur="saveNumber(question)"
              />
              <p class="mt-2 text-xs text-slate-400">Ответ сохраняется при потере фокуса.</p>
            </div>

            <div v-else-if="question.question_type === 'ranking'" class="grid gap-3">
              <div
                v-for="(item, position) in (question.rankingItems.length ? question.rankingItems : question.options.map((option, index) => ({ option_id: option.id, option, rank: index + 1 })))"
                :key="item.option_id"
                class="flex items-center justify-between gap-4 rounded-[24px] border border-slate-200/80 bg-white/85 px-4 py-4"
              >
                <div class="flex items-center gap-3">
                  <span class="flex h-9 w-9 items-center justify-center rounded-full bg-slate-100 text-sm font-semibold text-slate-600">{{ position + 1 }}</span>
                  <div>
                    <div class="font-medium text-slate-900">{{ item.option?.label || question.options.find((option) => option.id === item.option_id)?.label }}</div>
                    <div v-if="item.option?.description || question.options.find((option) => option.id === item.option_id)?.description" class="mt-1 text-sm text-slate-500">
                      {{ item.option?.description || question.options.find((option) => option.id === item.option_id)?.description }}
                    </div>
                  </div>
                </div>
                <div class="flex items-center gap-2">
                  <button class="ghost-button h-10 w-10 !rounded-full !px-0" :disabled="position === 0" @click="moveRanking(question, item.option_id, -1)">↑</button>
                  <button class="ghost-button h-10 w-10 !rounded-full !px-0" :disabled="position === ((question.rankingItems.length ? question.rankingItems : question.options).length - 1)" @click="moveRanking(question, item.option_id, 1)">↓</button>
                </div>
              </div>
              <p class="text-xs text-slate-400">Меняйте порядок кнопками вверх/вниз. Каждое действие сохраняется сразу.</p>
            </div>

            <div v-else class="rounded-[24px] bg-red-50 px-4 py-3 text-sm text-red-700">
              Тип вопроса <code>{{ question.question_type }}</code> пока не поддержан во фронтенде.
            </div>
          </div>
        </div>
      </div>

      <aside class="space-y-5 xl:sticky xl:top-24 xl:self-start">
        <div class="glass-panel p-5">
          <div class="text-sm font-semibold uppercase tracking-[0.2em] text-slate-400">Статус прохождения</div>
          <div class="mt-4 text-4xl font-semibold text-slate-900">{{ completedRequiredCount }} / {{ normalizedQuestions.length }}</div>
          <p class="mt-2 text-sm leading-6 text-slate-500">
            Для отправки должны быть заполнены все обязательные вопросы.
          </p>

          <div class="mt-4 h-2 overflow-hidden rounded-full bg-slate-200">
            <div class="h-full rounded-full bg-primary" :style="{ width: `${normalizedQuestions.length ? Math.round((completedRequiredCount / normalizedQuestions.length) * 100) : 0}%` }"></div>
          </div>

          <button
            v-if="!isReadOnly"
            class="primary-button mt-6 w-full"
            :disabled="submitting || !canSubmit"
            @click="handleSubmit"
          >
            {{ submitting ? 'Отправляем…' : 'Завершить попытку' }}
          </button>

          <p v-else class="mt-6 rounded-[24px] bg-emerald-50 px-4 py-3 text-sm text-emerald-700">
            Попытка уже отправлена {{ formatDateTime(attempt.submitted_at) }}.
          </p>
        </div>
      </aside>
    </div>
  </section>
</template>
