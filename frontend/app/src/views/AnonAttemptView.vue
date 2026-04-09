<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import DomikiColorRankingQuestion from '../components/diagnostics/DomikiColorRankingQuestion.vue'
import DomikiColorScaleQuestion from '../components/diagnostics/DomikiColorScaleQuestion.vue'
import publicApi from '../api/public'
import { getDiagnosticQuestionMode } from '../diagnostics'
import { formatDateTime, formatDuration, getAttemptStatusMeta, isNil, stringifyValue } from '../utils/format'

const props = defineProps({
  publicToken: {
    type: String,
    default: null,
  },
  token: {
    type: String,
    default: null,
  },
})

const phase = ref('loading')
const error = ref('')
const globalNotice = ref('')
const starting = ref(false)
const submitting = ref(false)
const elapsedSeconds = ref(null)

const testInfo = ref(null)
const attempt = ref(null)
const questions = ref([])
const answers = ref([])
const options = ref([])
const scales = ref([])
const scaleOptions = ref([])
const rankingItems = ref([])

// Определяем, в каком режиме мы находимся
const isIntroPhase = computed(() => !!props.publicToken && !props.token)
const attemptToken = computed(() => props.token || null)
const publicToken = computed(() => props.publicToken || null)

const textDrafts = reactive({})
const numberDrafts = reactive({})
const savingState = reactive({})
const shuffledOrders = reactive({})

function shuffleArray(array) {
  const arr = [...array]
  for (let i = arr.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1))
    ;[arr[i], arr[j]] = [arr[j], arr[i]]
  }
  return arr
}

let timerHandle = null

const answersByQuestionId = computed(() => Object.fromEntries(answers.value.map((answer) => [answer.question_id, answer])))
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
    const rawOptions = optionsByQuestionId.value[question.id] || []
    const rawScaleOptions = scaleOptionsByScaleId.value[question.scale_id] || []
    let resolvedOptions = rawOptions
    let resolvedScaleOptions = rawScaleOptions

    if (question.random && shuffledOrders[question.id]) {
      const { optionIds, scaleOptionIds } = shuffledOrders[question.id]
      if (optionIds) resolvedOptions = optionIds.map((id) => rawOptions.find((o) => o.id === id)).filter(Boolean)
      if (scaleOptionIds) resolvedScaleOptions = scaleOptionIds.map((id) => rawScaleOptions.find((o) => o.id === id)).filter(Boolean)
    }

    return {
      ...question,
      answer,
      options: resolvedOptions,
      scale: scalesById.value[question.scale_id] || null,
      scaleOptions: resolvedScaleOptions,
      rankingItems: answer ? rankingByAnswerId.value[answer.id] || [] : [],
    }
  })
})

const completedRequiredCount = computed(() => normalizedQuestions.value.filter((question) => !question.is_required || isQuestionAnswered(question)).length)
const canSubmit = computed(() => normalizedQuestions.value.every((question) => !question.is_required || isQuestionAnswered(question)))
const attemptStatus = computed(() => getAttemptStatusMeta(attempt.value?.status))
const isReadOnly = computed(() => ['submitted', 'completed'].includes(attempt.value?.status))
const displayDuration = computed(() => formatDuration(elapsedSeconds.value ?? attempt.value?.duration))
const diagnosticCode = computed(() => attempt.value?.test_assignment?.test?.code || null)

const currentStep = ref(0)
const isSequential = computed(() => Boolean(attempt.value?.test_assignment?.test?.is_sequential))
const submitWarning = ref('')

function goToStep(index) {
  currentStep.value = Math.max(0, Math.min(index, normalizedQuestions.value.length - 1))
}

function nextStep() {
  if (currentStep.value < normalizedQuestions.value.length - 1) currentStep.value++
}

function prevStep() {
  if (currentStep.value > 0) currentStep.value--
}

function jumpToFirstUnanswered() {
  if (!isSequential.value) return
  const index = normalizedQuestions.value.findIndex((q) => !isQuestionAnswered(q) && !q.answer?.is_skipped)
  if (index !== -1) currentStep.value = index
}

function scrollToQuestion(index) {
  if (isSequential.value) {
    goToStep(index)
  } else {
    document.getElementById(`question-${index}`)?.scrollIntoView({ behavior: 'smooth', block: 'center' })
  }
}

function initDrafts() {
  normalizedQuestions.value.forEach((question) => {
    if (question.answer) {
      textDrafts[question.answer.id] = question.answer.text || ''
      numberDrafts[question.answer.id] = question.answer.number ?? ''
    }
  })
}

function stopTimer() {
  if (timerHandle) {
    window.clearInterval(timerHandle)
    timerHandle = null
  }
}

function refreshElapsed() {
  if (!attempt.value?.started_at) {
    elapsedSeconds.value = attempt.value?.duration ?? null
    return
  }
  const startedAt = new Date(attempt.value.started_at).getTime()
  if (Number.isNaN(startedAt)) {
    elapsedSeconds.value = attempt.value?.duration ?? null
    return
  }
  elapsedSeconds.value = Math.max(0, Math.round((Date.now() - startedAt) / 1000))
}

function syncTimer() {
  stopTimer()
  if (!attempt.value) {
    elapsedSeconds.value = null
    return
  }
  if (attempt.value.started_at && !isReadOnly.value) {
    refreshElapsed()
    timerHandle = window.setInterval(refreshElapsed, 1000)
    return
  }
  elapsedSeconds.value = attempt.value.duration ?? null
}

function applyBundle(bundle) {
  attempt.value = bundle.attempt || null
  questions.value = bundle.questions || []
  answers.value = bundle.answers || []
  options.value = bundle.options || []
  scales.value = bundle.scales || []
  scaleOptions.value = bundle.scale_options || []
  rankingItems.value = bundle.ranking_items || []

  const optsByQuestion = options.value.reduce((map, opt) => {
    if (!map[opt.question_id]) map[opt.question_id] = []
    map[opt.question_id].push(opt)
    return map
  }, {})
  const scaleOptsByScale = scaleOptions.value.reduce((map, opt) => {
    if (!map[opt.scale_id]) map[opt.scale_id] = []
    map[opt.scale_id].push(opt)
    return map
  }, {})
  questions.value.forEach((question) => {
    if (!question.random) return
    const rawOpts = optsByQuestion[question.id] || []
    const rawScOpts = scaleOptsByScale[question.scale_id] || []
    shuffledOrders[question.id] = {
      optionIds: rawOpts.length ? shuffleArray(rawOpts.map((o) => o.id)) : null,
      scaleOptionIds: rawScOpts.length ? shuffleArray(rawScOpts.map((o) => o.id)) : null,
    }
  })

  initDrafts()
  syncTimer()
  jumpToFirstUnanswered()
}

function isQuestionAnswered(question) {
  const answer = question.answer
  if (!answer) return false
  if (answer.is_skipped) return false
  if (question.question_type === 'ranking') {
    return question.options.length > 0 && question.rankingItems.length === question.options.length
  }
  if (!isNil(answer.option_id)) return true
  if (!isNil(answer.scale_option_id)) return true
  if (!isNil(answer.boolean)) return true
  if (!isNil(answer.number)) return true
  if (!isNil(answer.text)) return true
  if (Array.isArray(answer.options) && answer.options.length) return true
  return false
}

function answerSelectedOptions(answer) {
  return Array.isArray(answer?.options) ? answer.options.map((option) => option.id) : []
}

function questionDiagnosticMode(question) {
  return getDiagnosticQuestionMode(diagnosticCode.value, question)
}

function patchAnswer(answer) {
  answers.value = answers.value.map((current) => (current.id === answer.id ? answer : current))
}

async function loadAttempt() {
  if (isIntroPhase.value) {
    // Загружаем информацию о тесте по публичному токену
    const { data } = await publicApi.get(`/public/tests/${publicToken.value}`)
    testInfo.value = data
    phase.value = 'intro'
  } else {
    // Загружаем информацию о попытке по токену
    const { data } = await publicApi.get(`/public/attempts/${attemptToken.value}`)
    applyBundle(data)
    phase.value = attempt.value?.status === 'assigned' ? 'intro' : 'test'
  }
}

async function saveAnswerValue(questionId, payload) {
  const { data } = await publicApi.patch(`/public/attempts/${attemptToken.value}/answers/${questionId}`, payload)
  return data
}

async function withSaving(questionId, action) {
  savingState[questionId] = { pending: true, error: '' }
  globalNotice.value = ''

  try {
    await action()
    savingState[questionId] = { pending: false, error: '' }
    globalNotice.value = 'Ответ сохранён'
  } catch (error) {
    const details = error.response?.data?.detail || error.response?.data?.errors?.[0]?.message
    savingState[questionId] = { pending: false, error: details || 'Не удалось сохранить ответ' }
  }
}

async function startAttempt() {
  starting.value = true
  error.value = ''

  try {
    if (isIntroPhase.value) {
      // Создаём новую попытку по публичному токену
      const { data } = await publicApi.post(`/public/tests/${publicToken.value}/start`)
      applyBundle(data)
      // Перенаправляем на URL с токеном попытки
      const attemptTokenValue = data.attempt?.token
      if (attemptTokenValue) {
        window.location.href = `/a/${attemptTokenValue}`
      } else {
        error.value = 'Не удалось получить токен попытки'
        phase.value = 'error'
      }
    } else {
      // Начинаем существующую попытку
      const { data } = await publicApi.post(`/public/attempts/${attemptToken.value}/start`)
      applyBundle(data)
      phase.value = 'test'
      globalNotice.value = 'Прохождение началось'
    }
  } catch {
    error.value = 'Не удалось начать прохождение'
    phase.value = 'error'
  } finally {
    starting.value = false
  }
}

async function saveSingleChoice(question, optionId) {
  if (!question.answer || isReadOnly.value) return
  await withSaving(question.id, async () => {
    const result = await saveAnswerValue(question.id, {
      option_id: optionId,
      scale_option_id: null,
      text: null,
      number: null,
      boolean: null,
      is_skipped: false,
    })
    patchAnswer(result.answer)
  })
}

async function saveScaleOption(question, scaleOptionId) {
  if (!question.answer || isReadOnly.value) return
  await withSaving(question.id, async () => {
    const result = await saveAnswerValue(question.id, {
      scale_option_id: scaleOptionId,
      option_id: null,
      text: null,
      number: null,
      boolean: null,
      is_skipped: false,
    })
    patchAnswer(result.answer)
  })
}

async function saveScaleNumber(question) {
  if (!question.answer || isReadOnly.value) return
  await withSaving(question.id, async () => {
    const raw = numberDrafts[question.answer.id]
    const value = raw === '' ? null : Number(raw)
    const result = await saveAnswerValue(question.id, {
      number: value,
      option_id: null,
      scale_option_id: null,
      text: null,
      boolean: null,
      is_skipped: false,
    })
    patchAnswer(result.answer)
  })
}

async function saveBoolean(question, value) {
  if (!question.answer || isReadOnly.value) return
  await withSaving(question.id, async () => {
    const result = await saveAnswerValue(question.id, {
      boolean: value,
      option_id: null,
      scale_option_id: null,
      text: null,
      number: null,
      is_skipped: false,
    })
    patchAnswer(result.answer)
  })
}

async function saveNumber(question) {
  if (!question.answer || isReadOnly.value) return
  await withSaving(question.id, async () => {
    const raw = numberDrafts[question.answer.id]
    const value = raw === '' ? null : Number(raw)
    const result = await saveAnswerValue(question.id, {
      number: value,
      option_id: null,
      scale_option_id: null,
      text: null,
      boolean: null,
      is_skipped: false,
    })
    patchAnswer(result.answer)
  })
}

async function saveText(question) {
  if (!question.answer || isReadOnly.value) return
  await withSaving(question.id, async () => {
    const value = textDrafts[question.answer.id] || null
    const result = await saveAnswerValue(question.id, {
      text: value,
      option_id: null,
      scale_option_id: null,
      number: null,
      boolean: null,
      is_skipped: false,
    })
    patchAnswer(result.answer)
  })
}

async function toggleMultiple(question, optionId) {
  if (!question.answer || isReadOnly.value) return
  const selectedIds = answerSelectedOptions(question.answer)
  const isSelected = selectedIds.includes(optionId)
  const nextIds = isSelected ? selectedIds.filter((id) => id !== optionId) : [...selectedIds, optionId]

  if (question.max_selections && nextIds.length > Number(question.max_selections)) {
    savingState[question.id] = { pending: false, error: `Можно выбрать не больше ${question.max_selections}` }
    return
  }

  await withSaving(question.id, async () => {
    const result = await saveAnswerValue(question.id, { options: nextIds })
    patchAnswer(result.answer)
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
    const result = await saveAnswerValue(question.id, { ranking: next })
    patchAnswer(result.answer)
    rankingItems.value = [
      ...rankingItems.value.filter((item) => item.answer_id !== question.answer.id),
      ...(result.ranking_items || []),
    ]
  })
}

async function appendRankingSelection(question, optionId) {
  if (!question.answer || isReadOnly.value) return
  const currentOrder = question.rankingItems.length
    ? question.rankingItems.map((item) => item.option_id)
    : []

  if (currentOrder.includes(optionId)) return

  await withSaving(question.id, async () => {
    const result = await saveAnswerValue(question.id, { ranking: [...currentOrder, optionId] })
    patchAnswer(result.answer)
    rankingItems.value = [
      ...rankingItems.value.filter((item) => item.answer_id !== question.answer.id),
      ...(result.ranking_items || []),
    ]
  })
}

async function removeRankingSelection(question, optionId) {
  if (!question.answer || isReadOnly.value) return
  const currentOrder = question.rankingItems.length
    ? question.rankingItems.map((item) => item.option_id)
    : []

  if (!currentOrder.includes(optionId)) return

  await withSaving(question.id, async () => {
    const result = await saveAnswerValue(question.id, { ranking: currentOrder.filter((id) => id !== optionId) })
    patchAnswer(result.answer)
    rankingItems.value = [
      ...rankingItems.value.filter((item) => item.answer_id !== question.answer.id),
      ...(result.ranking_items || []),
    ]
  })
}

async function resetRankingSelection(question) {
  if (!question.answer || isReadOnly.value) return
  await withSaving(question.id, async () => {
    const result = await saveAnswerValue(question.id, { ranking: [] })
    patchAnswer(result.answer)
    rankingItems.value = [
      ...rankingItems.value.filter((item) => item.answer_id !== question.answer.id),
      ...(result.ranking_items || []),
    ]
  })
}

async function toggleSkip(question) {
  if (!question.answer || isReadOnly.value || question.is_required) return
  const nextValue = !question.answer.is_skipped
  await withSaving(question.id, async () => {
    const result = await saveAnswerValue(question.id, {
      option_id: null,
      scale_option_id: null,
      text: null,
      number: null,
      boolean: null,
      options: [],
      ranking: [],
      is_skipped: nextValue,
    })
    textDrafts[question.answer.id] = ''
    numberDrafts[question.answer.id] = ''
    patchAnswer(result.answer)
    rankingItems.value = rankingItems.value.filter((item) => item.answer_id !== question.answer.id)
  })
}

async function handleSubmit() {
  if (!attempt.value || isReadOnly.value) return

  if (!canSubmit.value) {
    submitWarning.value = 'Не на все обязательные вопросы даны ответы'
    return
  }

  submitting.value = true
  error.value = ''
  submitWarning.value = ''

  try {
    const { data } = await publicApi.post(`/public/attempts/${attemptToken.value}/submit`)
    attempt.value = { ...attempt.value, ...data.attempt }
    stopTimer()
    phase.value = 'done'
  } catch {
    error.value = 'Не удалось отправить тест'
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

async function init() {
  phase.value = 'loading'
  error.value = ''

  try {
    await loadAttempt()
  } catch {
    error.value = 'Ссылка недействительна или прохождение недоступно.'
    phase.value = 'error'
  }
}

onMounted(init)
onBeforeUnmount(stopTimer)
</script>

<template>
  <section class="w-full">
    <div v-if="phase === 'loading'" class="glass-panel p-10 text-center text-sm text-slate-500">Загрузка теста…</div>

    <div v-else-if="phase === 'error'" class="glass-panel p-10 text-center">
      <div class="text-xl font-semibold text-red-700">Ошибка</div>
      <p class="mt-3 text-sm text-slate-600">{{ error }}</p>
    </div>

    <div v-else-if="phase === 'intro'" class="flex justify-center py-4 sm:py-10">
      <div class="glass-panel w-full max-w-3xl p-6 sm:p-8">
        <h1 class="text-3xl font-semibold tracking-tight text-slate-900">{{ (attempt || testInfo?.test_assignment)?.test?.title || 'Тест' }}</h1>

        <div class="mt-6 grid gap-3 sm:grid-cols-3">
          <div class="rounded-[24px] bg-slate-50/90 p-4">
            <div class="text-xs font-semibold uppercase tracking-[0.18em] text-slate-400">Формат</div>
            <div class="mt-2 text-sm font-medium text-slate-900">Ответы сохраняются автоматически</div>
          </div>
          <div class="rounded-[24px] bg-slate-50/90 p-4">
            <div class="text-xs font-semibold uppercase tracking-[0.18em] text-slate-400">Важно</div>
            <div class="mt-2 text-sm font-medium text-slate-900">Таймер запустится после старта</div>
          </div>
        </div>

        <p class="mt-6 text-sm leading-6 text-slate-600">После начала прохождения откроются вопросы, и будет зафиксировано время старта.</p>

        <div class="mt-6 flex flex-wrap justify-end gap-3">
          <button class="primary-button" :disabled="starting" @click="startAttempt">
            {{ starting ? 'Запускаем…' : 'Начать прохождение' }}
          </button>
        </div>
      </div>
    </div>

    <div v-else-if="phase === 'test' && attempt">
      <div class="mb-5 flex flex-wrap items-center gap-3">
        <span class="badge" :class="attemptStatus.className">{{ attemptStatus.label }}</span>
        <span v-if="attempt.started_at" class="badge bg-slate-100 text-slate-700">Таймер: {{ displayDuration }}</span>
        <span v-if="globalNotice" class="badge bg-emerald-100 text-emerald-700">{{ globalNotice }}</span>
      </div>

      <div class="grid gap-5 xl:grid-cols-[minmax(0,1fr)_21rem]">
        <div class="grid gap-5">
          <div class="glass-panel p-6 sm:p-7">
            <h1 class="text-3xl font-semibold tracking-tight text-slate-900">{{ attempt.test_assignment?.test?.title || `Тест #${attempt.test_assignment?.test_id}` }}</h1>
            <div class="mt-5 flex flex-wrap gap-3 text-sm text-slate-500">
              <span>Начало: {{ formatDateTime(attempt.started_at) }}</span>
              <span>Таймер: {{ displayDuration }}</span>
              <span>Вопросов: {{ normalizedQuestions.length }}</span>
            </div>
          </div>

          <template v-for="(question, index) in normalizedQuestions" :key="question.id">
            <div
              v-show="!isSequential || index === currentStep"
              :id="`question-${index}`"
              class="glass-panel overflow-hidden p-5 sm:p-6 transition-colors"
              :class="{
                'ring-2 ring-emerald-300/60': !isReadOnly && isQuestionAnswered(question),
                'ring-2 ring-orange-300/60': !isReadOnly && !isQuestionAnswered(question) && question.is_required && !question.answer?.is_skipped,
              }"
            >
            <div class="flex flex-wrap items-start justify-between gap-3">
              <div>
                <p class="text-xs font-semibold uppercase tracking-[0.22em] text-slate-400">Вопрос {{ index + 1 }}</p>
                <h2 class="mt-2 text-xl font-semibold text-slate-900">{{ question.text }}</h2>
                <p v-if="question.description" class="mt-2 text-sm leading-6 text-slate-500">{{ question.description }}</p>
              </div>
              <div class="flex flex-wrap items-center gap-2">
                <span v-if="question.is_required && !isQuestionAnswered(question)" class="badge bg-orange-100 text-orange-700">Обязательный</span>
                <span v-if="question.is_required && isQuestionAnswered(question)" class="badge bg-emerald-100 text-emerald-700">Отвечено</span>
                <button v-if="!question.is_required && !isReadOnly" class="ghost-button" @click="toggleSkip(question)">
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
                <button v-for="option in question.options" :key="option.id" class="cursor-pointer rounded-3xl border px-4 py-4 text-left transition" :class="question.answer?.option_id === option.id ? 'border-primary bg-primary/8 text-slate-900 shadow-sm' : 'border-slate-200/80 bg-white/80 text-slate-700 hover:border-primary/40'" @click="saveSingleChoice(question, option.id)">
                  <div class="font-medium">{{ option.label }}</div>
                  <div v-if="option.description" class="mt-1 text-sm text-slate-500">{{ option.description }}</div>
                </button>
              </div>

              <div v-else-if="question.question_type === 'multiple_choice'" class="grid gap-3">
                <div class="rounded-3xl bg-slate-50/80 px-4 py-3 text-sm text-slate-600">
                  Выбрано {{ answerSelectedOptions(question.answer).length }}<span v-if="question.max_selections"> из максимум {{ question.max_selections }}</span>
                </div>
                <button v-for="option in question.options" :key="option.id" class="cursor-pointer rounded-3xl border px-4 py-4 text-left transition" :class="answerSelectedOptions(question.answer).includes(option.id) ? 'border-primary bg-primary/8 text-slate-900 shadow-sm' : 'border-slate-200/80 bg-white/80 text-slate-700 hover:border-primary/40'" @click="toggleMultiple(question, option.id)">
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

              <DomikiColorScaleQuestion
                v-else-if="questionDiagnosticMode(question) === 'domiki-scale'"
                :question="question"
                :disabled="savingState[question.id]?.pending"
                @select="saveScaleOption(question, $event)"
              />

              <div v-else-if="question.question_type === 'scale' && question.scaleOptions.length" class="grid gap-3">
                <button v-for="option in question.scaleOptions" :key="option.id" class="cursor-pointer rounded-3xl border px-4 py-4 text-left transition" :class="question.answer?.scale_option_id === option.id ? 'border-primary bg-primary/8 text-slate-900 shadow-sm' : 'border-slate-200/80 bg-white/80 text-slate-700 hover:border-primary/40'" @click="saveScaleOption(question, option.id)">
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
                <div class="rounded-3xl border border-slate-200/80 bg-white/85 p-4">
                  <div class="mb-3 flex items-center justify-between gap-3">
                    <div>
                      <div class="text-sm font-semibold text-slate-900">{{ question.scale?.title || 'Числовая шкала' }}</div>
                      <div v-if="question.scale?.min_value != null && question.scale?.max_value != null" class="mt-1 text-sm text-slate-500">
                        {{ question.scale.min_value }}–{{ question.scale.max_value }}
                      </div>
                    </div>
                    <span class="badge bg-slate-100 text-slate-600">{{ numberDrafts[question.answer?.id] || '—' }}</span>
                  </div>
                  <input v-model="numberDrafts[question.answer?.id]" class="w-full accent-primary" type="range" :min="question.scale?.min_value ?? 0" :max="question.scale?.max_value ?? 10" :step="question.scale?.step ?? 1" @change="saveScaleNumber(question)" />
                  <div class="mt-3 flex items-center justify-between text-xs text-slate-400">
                    <span>{{ question.scale?.min_value ?? 0 }}</span>
                    <span>{{ question.scale?.max_value ?? 10 }}</span>
                  </div>
                </div>
              </div>

              <div v-else-if="question.question_type === 'yes_no'" class="grid gap-3 sm:grid-cols-2">
                <button class="cursor-pointer rounded-3xl border px-4 py-5 text-left transition" :class="question.answer?.boolean === true ? 'border-primary bg-primary/8 text-slate-900 shadow-sm' : 'border-slate-200/80 bg-white/80 text-slate-700 hover:border-primary/40'" @click="saveBoolean(question, true)">
                  <div class="text-lg font-semibold">Да</div>
                </button>
                <button class="cursor-pointer rounded-3xl border px-4 py-5 text-left transition" :class="question.answer?.boolean === false ? 'border-primary bg-primary/8 text-slate-900 shadow-sm' : 'border-slate-200/80 bg-white/80 text-slate-700 hover:border-primary/40'" @click="saveBoolean(question, false)">
                  <div class="text-lg font-semibold">Нет</div>
                </button>
              </div>

              <div v-else-if="question.question_type === 'text'">
                <textarea v-model="textDrafts[question.answer?.id]" class="field-input min-h-36 resize-y" placeholder="Введите ответ" @blur="saveText(question)"></textarea>
                <p class="mt-2 text-xs text-slate-400">Ответ сохраняется при потере фокуса.</p>
              </div>

              <div v-else-if="question.question_type === 'number'">
                <input v-model="numberDrafts[question.answer?.id]" class="field-input max-w-xs" type="number" placeholder="Введите число" @blur="saveNumber(question)" />
                <p class="mt-2 text-xs text-slate-400">Ответ сохраняется при потере фокуса.</p>
              </div>

              <DomikiColorRankingQuestion
                v-else-if="questionDiagnosticMode(question) === 'domiki-ranking'"
                :question="question"
                :disabled="savingState[question.id]?.pending"
                @select="appendRankingSelection(question, $event)"
                @remove="removeRankingSelection(question, $event)"
                @reset="resetRankingSelection(question)"
              />

              <div v-else-if="question.question_type === 'ranking'" class="grid gap-3">
                <div v-for="(item, position) in (question.rankingItems.length ? question.rankingItems : question.options.map((option, index) => ({ option_id: option.id, option, rank: index + 1 })))" :key="item.option_id" class="flex items-center justify-between gap-4 rounded-3xl border border-slate-200/80 bg-white/85 px-4 py-4">
                  <div class="flex items-center gap-3">
                    <span class="flex h-9 w-9 items-center justify-center rounded-full bg-slate-100 text-sm font-semibold text-slate-600">{{ position + 1 }}</span>
                    <div class="font-medium text-slate-900">{{ item.option?.label || question.options.find((option) => option.id === item.option_id)?.label }}</div>
                  </div>
                  <div class="flex items-center gap-2">
                    <button class="ghost-button h-10 w-10 !rounded-full !px-0" :disabled="position === 0" @click="moveRanking(question, item.option_id, -1)">↑</button>
                    <button class="ghost-button h-10 w-10 !rounded-full !px-0" :disabled="position === ((question.rankingItems.length ? question.rankingItems : question.options).length - 1)" @click="moveRanking(question, item.option_id, 1)">↓</button>
                  </div>
                </div>
                <p class="text-xs text-slate-400">Меняйте порядок кнопками вверх/вниз. Каждое действие сохраняется сразу.</p>
              </div>

              <div v-else class="rounded-3xl bg-red-50 px-4 py-3 text-sm text-red-700">Тип вопроса <code>{{ question.question_type }}</code> не поддержан.</div>
            </div>
          </div>
          </template>

          <div v-if="isSequential && !isReadOnly && normalizedQuestions.length > 1" class="flex items-center justify-between gap-3">
            <button v-if="currentStep > 0" class="ghost-button" @click="prevStep">← Назад</button>
            <div v-else class="invisible ghost-button pointer-events-none">← Назад</div>
            <span class="text-sm text-slate-500">{{ currentStep + 1 }} из {{ normalizedQuestions.length }}</span>
            <button v-if="currentStep < normalizedQuestions.length - 1" :class="isQuestionAnswered(normalizedQuestions[currentStep]) ? 'primary-button' : 'ghost-button'" @click="nextStep">Вперёд →</button>
            <div v-else class="invisible ghost-button pointer-events-none">Вперёд →</div>
          </div>
        </div>

        <aside class="space-y-5 xl:sticky xl:top-24 xl:self-start">
          <div class="glass-panel p-5">
            <div class="text-sm font-semibold uppercase tracking-[0.2em] text-slate-400">Статус прохождения</div>
            <div class="mt-4 text-4xl font-semibold text-slate-900">{{ completedRequiredCount }} / {{ normalizedQuestions.length }}</div>
            <div class="mt-2 text-sm text-slate-500">Таймер: {{ displayDuration }}</div>
            <div class="mt-4 h-2 overflow-hidden rounded-full bg-slate-200">
              <div class="h-full rounded-full bg-primary" :style="{ width: `${normalizedQuestions.length ? Math.round((completedRequiredCount / normalizedQuestions.length) * 100) : 0}%` }"></div>
            </div>

            <div class="mt-4 flex flex-wrap gap-1.5">
              <button
                v-for="(question, index) in normalizedQuestions"
                :key="question.id"
                class="flex h-8 w-8 items-center justify-center rounded-full text-xs font-semibold transition"
                :class="{
                  'bg-emerald-100 text-emerald-700': isQuestionAnswered(question),
                  'bg-orange-100 text-orange-700': !isQuestionAnswered(question) && question.is_required && !question.answer?.is_skipped,
                  'bg-slate-100 text-slate-500': !isQuestionAnswered(question) && !question.is_required && !question.answer?.is_skipped,
                  'bg-slate-200 text-slate-400 line-through': question.answer?.is_skipped,
                  'ring-2 ring-primary': isSequential && index === currentStep,
                }"
                @click="scrollToQuestion(index)"
              >
                {{ index + 1 }}
              </button>
            </div>

            <p v-if="submitWarning" class="mt-4 text-sm text-amber-700">{{ submitWarning }}</p>

            <button v-if="!isReadOnly" class="primary-button mt-6 w-full" :disabled="submitting || !canSubmit" @click="handleSubmit">
              {{ submitting ? 'Отправляем…' : 'Завершить тест' }}
            </button>

            <p v-else class="mt-6 rounded-3xl bg-emerald-50 px-4 py-3 text-sm text-emerald-700">
              Тест отправлен {{ formatDateTime(attempt.submitted_at) }}.
            </p>
          </div>
        </aside>
      </div>
    </div>

    <div v-else-if="phase === 'done'" class="flex justify-center py-4 sm:py-10">
      <div class="glass-panel w-full max-w-xl p-6 sm:p-8 text-center">
        <div class="text-4xl">✓</div>
        <h1 class="mt-4 text-2xl font-semibold text-slate-900">Тест завершён</h1>
        <p class="mt-3 text-sm leading-6 text-slate-600">Ваши ответы успешно отправлены. Спасибо за прохождение!</p>
      </div>
    </div>
  </section>
</template>
