<script setup>
import { computed, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { list, normalizeId, toFilter, dedupe } from '../utils/nocobase'
import { formatDateTime, getAttemptStatusMeta, getResultStatusMeta, isNil } from '../utils/format'
import logger from '../utils/logger'

const auth = useAuthStore()

const loading = ref(true)
const error = ref('')
const attempts = ref([])
const answers = ref([])
const results = ref([])

const answersByAttemptId = computed(() => {
  const map = {}
  answers.value.forEach((answer) => {
    if (!map[answer.attempt_id]) map[answer.attempt_id] = []
    map[answer.attempt_id].push(answer)
  })
  return map
})

const resultByAttemptId = computed(() => {
  return Object.fromEntries(results.value.map((result) => [result.attempt_id, result]))
})

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

const activeAttempts = computed(() => {
  return decoratedAttempts.value.filter((attempt) => !['submitted', 'completed'].includes(attempt.status))
})

const archivedAttempts = computed(() => {
  return decoratedAttempts.value.filter((attempt) => ['submitted', 'completed'].includes(attempt.status))
})

async function loadData() {
  loading.value = true
  error.value = ''

  try {
    logger.log('loadData: listAssignedAttempts', { personId: auth.personId })
    const loadedAttempts = await list('attempts', {
      filter: toFilter({ person_id: normalizeId(auth.personId) }),
      appends: 'test',
      sort: '-submitted_at,-started_at,-id',
    })

    if (!loadedAttempts.length) {
      attempts.value = []
      answers.value = []
      results.value = []
      return
    }

    const attemptIds = loadedAttempts.map((a) => a.id)
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
          <RouterLink
            v-for="attempt in activeAttempts"
            :key="attempt.id"
            :to="{ name: 'attempt', params: { attemptId: attempt.id } }"
            class="glass-panel block overflow-hidden p-5 no-underline transition hover:-translate-y-0.5 hover:shadow-[0_24px_60px_rgba(15,23,42,0.12)]"
          >
            <div class="flex items-start justify-between gap-3">
              <div>
                <p class="text-xs font-semibold uppercase tracking-[0.2em] text-slate-400">{{ attempt.test?.code || 'test' }}</p>
                <h3 class="mt-2 text-xl font-semibold text-slate-900">{{ attempt.test?.title || `Тест #${attempt.test_id}` }}</h3>
              </div>
              <span class="badge" :class="attempt.attemptStatus.className">{{ attempt.attemptStatus.label }}</span>
            </div>

            <p v-if="attempt.test?.description" class="mt-3 text-sm leading-6 text-slate-500">{{ attempt.test.description }}</p>

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
              <span>Начало: {{ formatDateTime(attempt.started_at) }}</span>
              <span class="font-medium text-primary">Открыть</span>
            </div>
          </RouterLink>
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
              <p class="text-xs font-semibold uppercase tracking-[0.2em] text-slate-400">{{ attempt.test?.code || 'test' }}</p>
              <h3 class="mt-2 text-lg font-semibold text-slate-900">{{ attempt.test?.title || `Тест #${attempt.test_id}` }}</h3>
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
  </section>
</template>
