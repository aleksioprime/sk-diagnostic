<script setup>
import { computed, onMounted, ref } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { list, normalizeId, toFilter, dedupe } from '../utils/nocobase'
import { formatDateTime, getAttemptStatusMeta, getResultStatusMeta, isNil } from '../utils/format'

const auth = useAuthStore()
const router = useRouter()

const loading = ref(true)
const error = ref('')
const attempts = ref([])
const answers = ref([])
const results = ref([])
const startCandidate = ref(null)

const answersByAttemptId = computed(() => {
  const map = {}
  answers.value.forEach((answer) => {
    if (!map[answer.attempt_id]) map[answer.attempt_id] = []
    map[answer.attempt_id].push(answer)
  })
  return map
})

const resultByAttemptId = computed(() => Object.fromEntries(results.value.map((result) => [result.attempt_id, result])))

function hasAnswerValue(answer) {
  return Boolean(
    !isNil(answer.option_id) ||
    !isNil(answer.scale_option_id) ||
    !isNil(answer.boolean) ||
    !isNil(answer.text) ||
    !isNil(answer.number) ||
    (Array.isArray(answer.options) && answer.options.length),
  )
}

const decoratedAttempts = computed(() => {
  return attempts.value.map((attempt) => {
    const relatedAnswers = answersByAttemptId.value[attempt.id] || []
    const answeredCount = relatedAnswers.filter(hasAnswerValue).length
    const totalCount = relatedAnswers.length
    const progress = totalCount ? Math.round((answeredCount / totalCount) * 100) : 0
    const attemptStatus = getAttemptStatusMeta(attempt.status)
    const result = resultByAttemptId.value[attempt.id] || null
    const resultStatus = result ? getResultStatusMeta(result.status) : null

    return {
      ...attempt,
      answeredCount,
      totalCount,
      progress,
      attemptStatus,
      result,
      resultStatus,
    }
  })
})

const activeAttempts = computed(() => decoratedAttempts.value.filter((attempt) => !['submitted', 'completed'].includes(attempt.status)))
const archivedAttempts = computed(() => decoratedAttempts.value.filter((attempt) => ['submitted', 'completed'].includes(attempt.status)))

async function loadData() {
  loading.value = true
  error.value = ''

  try {
    const personId = normalizeId(auth.personId)
    const filter = { is_archived: { $ne: true } }

    if (personId != null) {
      filter.person_id = personId
    }

    const loadedAttempts = await list('attempts', {
      filter: toFilter(filter),
      appends: 'test,person',
      sort: '-submitted_at,-started_at,-id',
    })

    if (!loadedAttempts.length) {
      attempts.value = []
      answers.value = []
      results.value = []
      return
    }

    const attemptIds = dedupe(loadedAttempts.map((attempt) => attempt.id))
    const [loadedAnswers, loadedResults] = await Promise.all([
      list('answers', {
        filter: toFilter({ attempt_id: { $in: attemptIds } }),
        appends: 'options,option,scale_option',
      }),
      list('attempt_results', {
        filter: toFilter({ attempt_id: { $in: attemptIds } }),
        sort: '-id',
      }),
    ])

    attempts.value = loadedAttempts
    answers.value = loadedAnswers
    results.value = loadedResults
  } catch {
    error.value = 'Не удалось загрузить список попыток'
  } finally {
    loading.value = false
  }
}

function openAttempt(attempt) {
  if (attempt.status === 'assigned') {
    startCandidate.value = attempt
    return
  }
  router.push({ name: 'attempt', params: { attemptId: attempt.id } })
}

function closeStartModal() {
  startCandidate.value = null
}

function confirmStart() {
  const attempt = startCandidate.value
  if (!attempt) return
  startCandidate.value = null
  router.push({ name: 'attempt', params: { attemptId: attempt.id }, query: { start: '1' } })
}

onMounted(loadData)
</script>

<template>
  <section class="w-full">
    <div class="mb-6 flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
      <div>
        <p class="mb-2 text-sm font-semibold uppercase tracking-[0.24em] text-slate-400">Мой кабинет</p>
        <h1 class="section-title">Выданные тесты</h1>
        <p class="mt-2 max-w-3xl text-sm leading-6 text-slate-500">Здесь собраны все тесты, которые доступны вам сейчас, а также завершённые прохождения.</p>
      </div>
      <button class="ghost-button self-start" @click="loadData" :disabled="loading">
        {{ loading ? 'Обновление…' : 'Обновить список' }}
      </button>
    </div>

    <div v-if="loading" class="glass-panel p-8 text-center text-sm text-slate-500">Загрузка попыток…</div>
    <div v-else-if="error" class="glass-panel p-8 text-center text-sm text-red-700">{{ error }}</div>
    <div v-else-if="!decoratedAttempts.length" class="glass-panel p-10 text-center">
      <div class="text-xl font-semibold text-slate-900">Пока нет выданных тестов</div>
      <p class="mt-2 text-sm text-slate-500">Когда для вас будет назначен тест, он появится на этой странице.</p>
    </div>

    <div v-else class="grid gap-8">
      <div>
        <div class="mb-4 flex items-center justify-between">
          <h2 class="text-lg font-semibold text-slate-900">Активные попытки</h2>
          <span class="badge bg-primary/10 text-primary">{{ activeAttempts.length }}</span>
        </div>

        <div v-if="!activeAttempts.length" class="glass-panel p-8 text-sm text-slate-500">Активных тестов нет.</div>
        <div v-else class="grid gap-4 lg:grid-cols-2">
          <button
            v-for="attempt in activeAttempts"
            :key="attempt.id"
            type="button"
            class="glass-panel block cursor-pointer overflow-hidden p-5 text-left transition hover:-translate-y-0.5 hover:shadow-[0_24px_60px_rgba(15,23,42,0.12)]"
            @click="openAttempt(attempt)"
          >
            <div class="flex items-start justify-between gap-3">
              <h3 class="text-xl font-semibold text-slate-900">{{ attempt.test?.title || `Тест #${attempt.test_id}` }}</h3>
              <span class="badge" :class="attempt.attemptStatus.className">{{ attempt.attemptStatus.label }}</span>
            </div>

            <div class="mt-5 rounded-[24px] bg-slate-50/90 p-4">
              <div class="mb-2 flex items-center justify-between text-sm">
                <span class="font-medium text-slate-600">Прогресс</span>
                <span class="font-semibold text-slate-900">{{ attempt.answeredCount }} / {{ attempt.totalCount }}</span>
              </div>
              <div class="h-2 overflow-hidden rounded-full bg-slate-200">
                <div class="h-full rounded-full bg-primary transition-all" :style="{ width: `${attempt.progress}%` }"></div>
              </div>
            </div>

            <div class="mt-4 flex items-center justify-between text-sm text-slate-500">
              <span>
                {{ attempt.status === 'assigned' ? 'Время начнётся после подтверждения' : `Начало: ${formatDateTime(attempt.started_at)}` }}
              </span>
              <span class="font-medium text-primary">{{ attempt.status === 'assigned' ? 'Начать' : 'Открыть' }}</span>
            </div>
          </button>
        </div>
      </div>

      <div>
        <div class="mb-4 flex items-center justify-between">
          <h2 class="text-lg font-semibold text-slate-900">Завершённые попытки</h2>
          <span class="badge bg-slate-100 text-slate-600">{{ archivedAttempts.length }}</span>
        </div>

        <div v-if="!archivedAttempts.length" class="glass-panel p-8 text-sm text-slate-500">Завершённых попыток пока нет.</div>
        <div v-else class="grid gap-4">
          <div
            v-for="attempt in archivedAttempts"
            :key="attempt.id"
            class="glass-panel flex flex-col gap-4 p-5 lg:flex-row lg:items-center lg:justify-between"
          >
            <div>
              <h3 class="text-lg font-semibold text-slate-900">{{ attempt.test?.title || `Тест #${attempt.test_id}` }}</h3>
              <p class="mt-2 text-sm text-slate-500">Отправлен: {{ formatDateTime(attempt.submitted_at) }}</p>
            </div>

            <div class="flex flex-wrap items-center gap-2">
              <span class="badge" :class="attempt.attemptStatus.className">{{ attempt.attemptStatus.label }}</span>
              <span v-if="attempt.resultStatus" class="badge" :class="attempt.resultStatus.className">
                {{ attempt.resultStatus.label }}
              </span>
              <RouterLink :to="{ name: 'attempt', params: { attemptId: attempt.id } }" class="ghost-button no-underline">
                Смотреть ответы
              </RouterLink>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div v-if="startCandidate" class="fixed inset-0 z-40 flex items-center justify-center bg-slate-950/45 px-4 backdrop-blur-sm">
      <div class="glass-panel w-full max-w-xl p-6 sm:p-7">
        <p class="text-sm font-semibold uppercase tracking-[0.24em] text-slate-400">Подтверждение</p>
        <h2 class="mt-3 text-2xl font-semibold text-slate-900">Начать прохождение</h2>
        <p class="mt-3 text-sm leading-6 text-slate-600">
          После подтверждения для этой попытки будет зафиксировано время старта и запустится таймер.
        </p>
        <div class="mt-5 rounded-[24px] bg-slate-50/90 p-4">
          <div class="text-sm font-semibold text-slate-900">{{ startCandidate.test?.title || `Тест #${startCandidate.test_id}` }}</div>
          <div class="mt-1 text-sm text-slate-500">{{ startCandidate.test?.description || 'Открыть вопросы и начать прохождение.' }}</div>
        </div>
        <div class="mt-6 flex flex-wrap justify-end gap-3">
          <button class="ghost-button" @click="closeStartModal">Отмена</button>
          <button class="primary-button" @click="confirmStart">Подтвердить старт</button>
        </div>
      </div>
    </div>
  </section>
</template>
