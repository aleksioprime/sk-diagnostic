<script setup>
import { computed, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { list, normalizeId, toFilter, dedupe } from '../utils/nocobase'
import {
  formatDateTime,
  getAttemptStatusMeta,
  getResultStatusMeta,
  personDisplayName,
} from '../utils/format'
import { resolveTableTemplate } from '../utils/resultTemplates'
import logger from '../utils/logger'

const loading = ref(true)
const error = ref('')
const tests = ref([])
const attempts = ref([])
const results = ref([])
const persons = ref([])

const selectedTestId = ref('')
const selectedResultStatus = ref('')
const search = ref('')

const personsById = computed(() => Object.fromEntries(persons.value.map((p) => [p.id, p])))
const attemptsById = computed(() => Object.fromEntries(attempts.value.map((attempt) => [attempt.id, attempt])))

const rows = computed(() => {
  return results.value.map((resultRecord) => {
    const attempt = attemptsById.value[resultRecord.attempt_id]
    if (!attempt) return null
    const fallbackPerson = personsById.value[attempt.person_id]
    const decoratedAttempt = {
      ...attempt,
      person: attempt.person || fallbackPerson || null,
      attemptStatus: getAttemptStatusMeta(attempt.status),
      resultStatus: getResultStatusMeta(resultRecord.status),
    }

    return {
      attempt: decoratedAttempt,
      resultRecord,
      template: resolveTableTemplate({
        test: decoratedAttempt.test,
        attempt: decoratedAttempt,
        resultRecord,
      }),
    }
  }).filter(Boolean)
})

const filteredRows = computed(() => {
  const normalizedQuery = search.value.trim().toLowerCase()

  return rows.value.filter((row) => {
    if (selectedTestId.value && String(row.attempt.test_id) !== String(selectedTestId.value)) return false
    if (selectedResultStatus.value && row.resultRecord.status !== selectedResultStatus.value) return false

    if (!normalizedQuery) return true

    const haystack = [
      row.attempt.test?.title,
      row.attempt.test?.code,
      personDisplayName(row.attempt.person, row.attempt.person_id),
      row.resultRecord.json?.student?.name,
      String(row.attempt.id),
    ]
      .filter(Boolean)
      .join(' ')
      .toLowerCase()

    return haystack.includes(normalizedQuery)
  })
})

const hasSingleTemplate = computed(() => {
  return new Set(filteredRows.value.map((row) => row.template.id)).size === 1
})

const activeTemplateColumns = computed(() => {
  if (!filteredRows.value.length || !hasSingleTemplate.value) return []
  return filteredRows.value[0].template.getTableColumns?.() || []
})

async function loadData() {
  loading.value = true
  error.value = ''

  try {
    const testId = selectedTestId.value || undefined
    const status = selectedResultStatus.value || undefined

    const [testsPayload, resultsPayload] = await Promise.all([
      list('tests', { filter: toFilter({}), sort: 'title,id' }),
      (async () => {
        logger.log('loadData: listResults', { testId, status })
        const resultFilter = {}
        if (status) resultFilter.status = status

        const loadedResults = await list('attempt_results', {
          filter: toFilter(resultFilter),
          sort: '-id',
        })

        if (!loadedResults.length) return { attempts: [], results: [], persons: [] }

        const attemptIds = dedupe(loadedResults.map((item) => item.attempt_id))
        const loadedAttempts = await list('attempts', {
          filter: toFilter({
            id: { $in: attemptIds },
            ...(testId ? { test_id: normalizeId(testId) } : {}),
          }),
          appends: 'test,person',
          sort: '-submitted_at,-id',
        })

        const filteredAttemptIds = new Set(loadedAttempts.map((a) => a.id))
        const filteredResults = loadedResults.filter((r) => filteredAttemptIds.has(r.attempt_id))

        const missingPersonIds = dedupe(
          loadedAttempts
            .filter((a) => !a.person && a.person_id != null)
            .map((a) => a.person_id),
        )

        const loadedPersons = missingPersonIds.length
          ? await list('persons', { filter: toFilter({ id: { $in: missingPersonIds } }), sort: 'id' })
          : []

        return { attempts: loadedAttempts, results: filteredResults, persons: loadedPersons }
      })(),
    ])

    tests.value = testsPayload
    attempts.value = resultsPayload.attempts
    results.value = resultsPayload.results
    persons.value = resultsPayload.persons
  } catch {
    error.value = 'Не удалось загрузить результаты'
  } finally {
    loading.value = false
  }
}

onMounted(loadData)
</script>

<template>
  <section class="w-full">
    <div class="mb-6">
      <p class="mb-2 text-sm font-semibold uppercase tracking-[0.24em] text-slate-400">Результаты</p>
      <h1 class="section-title">Результаты прохождения тестов</h1>
      <p class="mt-2 max-w-3xl text-sm leading-6 text-slate-500">На этой странице можно найти нужного человека, отфильтровать результаты и открыть подробный просмотр.</p>
    </div>

    <div class="glass-panel mb-5 grid gap-4 p-5 lg:grid-cols-[1fr_0.8fr_0.8fr_auto]">
      <label class="block">
        <span class="mb-2 block text-xs font-semibold uppercase tracking-[0.18em] text-slate-400">Поиск</span>
        <input v-model="search" class="field-input" type="text" placeholder="ФИО, тест, код, ID попытки" />
      </label>

      <label class="block">
        <span class="mb-2 block text-xs font-semibold uppercase tracking-[0.18em] text-slate-400">Тест</span>
        <select v-model="selectedTestId" class="field-input">
          <option value="">Все тесты</option>
          <option v-for="test in tests" :key="test.id" :value="test.id">{{ test.title }}</option>
        </select>
      </label>

      <label class="block">
        <span class="mb-2 block text-xs font-semibold uppercase tracking-[0.18em] text-slate-400">Статус результата</span>
        <select v-model="selectedResultStatus" class="field-input">
          <option value="">Все статусы</option>
          <option value="pending">pending</option>
          <option value="processing">processing</option>
          <option value="success">success</option>
          <option value="error">error</option>
        </select>
      </label>

      <button class="primary-button self-end" @click="loadData" :disabled="loading">
        {{ loading ? 'Загрузка…' : 'Обновить' }}
      </button>
    </div>

    <div v-if="loading" class="glass-panel p-10 text-center text-sm text-slate-500">Загрузка таблицы результатов…</div>
    <div v-else-if="error" class="glass-panel p-10 text-center text-sm text-red-700">{{ error }}</div>
    <div v-else-if="!filteredRows.length" class="glass-panel p-10 text-center text-sm text-slate-500">Результаты не найдены.</div>
    <div v-else class="overflow-hidden rounded-[30px] border border-white/60 bg-white/92 shadow-[0_20px_60px_rgba(15,23,42,0.08)]">
      <div class="overflow-x-auto">
        <table class="min-w-full border-collapse text-left text-sm">
          <thead class="bg-slate-50 text-slate-500">
            <tr>
              <th class="px-4 py-3 font-semibold">Тестируемый</th>
              <th class="px-4 py-3 font-semibold">Тест</th>
              <th class="px-4 py-3 font-semibold">Попытка</th>
              <th class="px-4 py-3 font-semibold">Статусы</th>
              <th class="px-4 py-3 font-semibold">Отправлен</th>
              <th
                v-for="column in activeTemplateColumns"
                :key="column.key"
                class="px-4 py-3 font-semibold"
              >
                {{ column.label }}
              </th>
              <th v-if="!activeTemplateColumns.length" class="px-4 py-3 font-semibold">Сводка</th>
              <th class="px-4 py-3 font-semibold"></th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in filteredRows" :key="row.resultRecord.id" class="border-t border-slate-100 align-top">
              <td class="px-4 py-4">
                <div class="font-semibold text-slate-900">{{ row.resultRecord.json?.student?.name || personDisplayName(row.attempt.person, row.attempt.person_id) }}</div>
                <div class="mt-1 text-xs text-slate-500">{{ personDisplayName(row.attempt.person, row.attempt.person_id) }}</div>
              </td>
              <td class="px-4 py-4">
                <div class="font-medium text-slate-900">{{ row.attempt.test?.title || `Тест #${row.attempt.test_id}` }}</div>
                <div class="mt-1 text-xs text-slate-500">{{ row.attempt.test?.code || '—' }}</div>
              </td>
              <td class="px-4 py-4 font-mono text-xs text-slate-600">{{ row.attempt.id }}</td>
              <td class="px-4 py-4">
                <div class="flex flex-col gap-2">
                  <span class="badge" :class="row.attempt.attemptStatus.className">{{ row.attempt.attemptStatus.label }}</span>
                  <span class="badge" :class="row.attempt.resultStatus.className">{{ row.attempt.resultStatus.label }}</span>
                </div>
              </td>
              <td class="px-4 py-4 text-slate-600">{{ formatDateTime(row.attempt.submitted_at) }}</td>
              <td
                v-for="column in activeTemplateColumns"
                :key="column.key"
                class="px-4 py-4 text-slate-800"
              >
                {{ column.value(row) }}
              </td>
              <td v-if="!activeTemplateColumns.length" class="px-4 py-4 text-slate-700">
                {{ row.template.getTableColumns?.()[0]?.value?.(row) || '—' }}
              </td>
              <td class="px-4 py-4">
                <RouterLink :to="{ name: 'result-detail', params: { attemptId: row.attempt.id } }" class="ghost-button no-underline">
                  Открыть
                </RouterLink>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </section>
</template>
