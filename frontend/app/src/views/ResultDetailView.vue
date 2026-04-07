<script setup>
import { computed, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import JsonResultTable from '../components/results/JsonResultTable.vue'
import ResultSections from '../components/results/ResultSections.vue'
import { get, list, normalizeId, toFilter } from '../utils/nocobase'
import { formatDateTime, formatDuration, getAttemptStatusMeta, getResultStatusMeta } from '../utils/format'
import { resolveResultTemplate } from '../utils/resultTemplates'

const props = defineProps({
  testId: {
    type: [String, Number],
    required: true,
  },
  attemptId: {
    type: [String, Number],
    required: true,
  },
})

const loading = ref(true)
const error = ref('')
const attempt = ref(null)
const resultRecord = ref(null)
const questions = ref([])
const answers = ref([])
const rankingItems = ref([])

const answersByQuestionId = computed(() => Object.fromEntries(answers.value.map((answer) => [answer.question_id, answer])))
const rankingByAnswerId = computed(() => {
  return rankingItems.value.reduce((map, item) => {
    if (!map[item.answer_id]) map[item.answer_id] = []
    map[item.answer_id].push(item)
    return map
  }, {})
})

const template = computed(() => {
  return resolveResultTemplate({
    test: attempt.value?.test_assignment?.test,
    attempt: attempt.value,
    resultRecord: resultRecord.value,
  })
})

const hero = computed(() => template.value.buildHero({
  attempt: attempt.value,
  resultRecord: resultRecord.value,
}))

const sections = computed(() => template.value.buildSections({
  attempt: attempt.value,
  resultRecord: resultRecord.value,
}))

const answersPreview = computed(() => {
  return questions.value.map((question) => {
    const answer = answersByQuestionId.value[question.id]
    const ranking = answer ? (rankingByAnswerId.value[answer.id] || []) : []
    const selectedOptions = Array.isArray(answer?.options) ? answer.options.map((option) => option.label).join(', ') : ''

    let value = '—'
    if (!answer) value = 'Ответ не найден'
    else if (answer.is_skipped) value = 'Пропущено'
    else if (answer.option?.label) value = answer.option.label
    else if (selectedOptions) value = selectedOptions
    else if (answer.scale_option?.label) value = answer.scale_option.label
    else if (answer.text) value = answer.text
    else if (answer.number !== null && answer.number !== undefined) value = String(answer.number)
    else if (answer.boolean !== null && answer.boolean !== undefined) value = answer.boolean ? 'Да' : 'Нет'
    else if (ranking.length) value = ranking.map((item) => item.option?.label || `#${item.option_id}`).join(' → ')

    return {
      id: question.id,
      title: question.text,
      value,
    }
  })
})

const attemptStatus = computed(() => getAttemptStatusMeta(attempt.value?.status))
const resultStatus = computed(() => getResultStatusMeta(resultRecord.value?.status))
const resultStudent = computed(() => resultRecord.value?.json_results?.student || {})

async function loadData() {
  loading.value = true
  error.value = ''

  try {
    const loadedAttempt = await get('attempts', props.attemptId, { appends: 'test_assignment,test_assignment.test,person' })
    if (!loadedAttempt) {
      throw new Error('archived')
    }
    const attemptTestId = loadedAttempt.test_assignment?.test_id ?? loadedAttempt.test_assignment?.test?.id
    if (String(attemptTestId) !== String(props.testId)) {
      throw new Error('wrong_test')
    }

    const [loadedQuestions, loadedAnswers, resultRecords] = await Promise.all([
      list('questions', {
        filter: toFilter({ test_id: normalizeId(props.testId), is_active: true }),
        sort: 'order,id',
      }),
      list('answers', {
        filter: toFilter({ attempt_id: normalizeId(props.attemptId) }),
        appends: 'option,scale_option,options,question',
        sort: 'id',
      }),
      list('attempt_results', {
        filter: toFilter({ attempt_id: normalizeId(props.attemptId) }),
        sort: '-id',
      }),
    ])

    const answerIds = loadedAnswers.map((answer) => answer.id)
    const loadedRankingItems = answerIds.length
      ? await list('answer_ranking_items', {
        filter: toFilter({ answer_id: { $in: answerIds } }),
        appends: 'option',
        sort: 'rank,id',
      })
      : []

    attempt.value = loadedAttempt
    resultRecord.value = resultRecords[0] || null
    questions.value = loadedQuestions
    answers.value = loadedAnswers
    rankingItems.value = loadedRankingItems
  } catch {
    error.value = 'Не удалось загрузить результат'
  } finally {
    loading.value = false
  }
}

onMounted(loadData)
</script>

<template>
  <section class="w-full">
    <div class="mb-5 flex flex-wrap items-center gap-3">
      <RouterLink :to="{ name: 'results-test', params: { testId: props.testId } }" class="ghost-button no-underline">← К прохождениям по тесту</RouterLink>
      <span v-if="attempt" class="badge" :class="attemptStatus.className">{{ attemptStatus.label }}</span>
      <span v-if="resultRecord" class="badge" :class="resultStatus.className">{{ resultStatus.label }}</span>
    </div>

    <div v-if="loading" class="glass-panel p-10 text-center text-sm text-slate-500">Загрузка детального результата…</div>
    <div v-else-if="error" class="glass-panel p-10 text-center text-sm text-red-700">{{ error }}</div>
    <div v-else-if="attempt && resultRecord" class="grid gap-5">
      <div class="glass-panel overflow-hidden p-6 sm:p-7">
        <p class="text-sm font-semibold uppercase tracking-[0.26em] text-slate-400">{{ hero.eyebrow }}</p>
        <h1 class="mt-3 text-4xl leading-none font-semibold tracking-tight text-slate-900">{{ hero.title }}</h1>

        <div class="mt-6 grid gap-3 text-sm text-slate-500 sm:grid-cols-2 xl:grid-cols-4">
          <div>Пол: <span class="font-medium text-slate-800">{{ resultStudent.gender_value || resultStudent.gender_label || resultStudent.gender || '—' }}</span></div>
          <div>Возраст: <span class="font-medium text-slate-800">{{ resultStudent.age ?? '—' }}</span></div>
          <div>Отправлен: <span class="font-medium text-slate-800">{{ formatDateTime(attempt.submitted_at) }}</span></div>
          <div>Длительность: <span class="font-medium text-slate-800">{{ formatDuration(attempt.duration) }}</span></div>
        </div>
      </div>

      <ResultSections :sections="sections" />

      <details class="glass-panel p-5 sm:p-6">
        <summary class="flex cursor-pointer list-none items-start justify-between gap-2 [&::-webkit-details-marker]:hidden">
          <div>
            <h2 class="text-lg font-semibold text-slate-900">Ответы пользователя</h2>
            <p class="mt-1 text-sm text-slate-500">Сводка по ответам, которые были даны во время прохождения.</p>
          </div>
          <span class="mt-1 shrink-0 text-slate-400 select-none">▾</span>
        </summary>
        <div class="mt-4 grid gap-3">
          <div
            v-for="item in answersPreview"
            :key="item.id"
            class="rounded-3xl border border-slate-200/70 bg-white/82 px-4 py-4"
          >
            <div class="text-sm font-semibold text-slate-900">{{ item.title }}</div>
            <div class="mt-2 text-sm leading-6 text-slate-600">{{ item.value }}</div>
          </div>
        </div>
      </details>

      <details class="glass-panel p-5 sm:p-6">
        <summary class="flex cursor-pointer list-none items-start justify-between gap-2 [&::-webkit-details-marker]:hidden">
          <div>
            <h2 class="text-lg font-semibold text-slate-900">Подробные данные результата</h2>
            <p class="mt-1 text-sm text-slate-500">Табличное представление всех полей результата.</p>
          </div>
          <span class="mt-1 shrink-0 text-slate-400 select-none">▾</span>
        </summary>
        <div class="mt-4">
          <JsonResultTable :value="resultRecord.json_results" />
        </div>
      </details>
    </div>
    <div v-else class="glass-panel p-10 text-center text-sm text-slate-500">
      Для этого прохождения пока нет результата.
    </div>
  </section>
</template>
