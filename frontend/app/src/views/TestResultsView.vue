<script setup>
import { computed, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { get, list, normalizeId, toFilter, dedupe } from '../utils/nocobase'
import {
  formatDateTime,
  getAttemptStatusMeta,
  getResultStatusMeta,
  personDisplayName,
} from '../utils/format'
import { resolveTableTemplate } from '../utils/resultTemplates'

const props = defineProps({
  testId: {
    type: [String, Number],
    required: true,
  },
})

const loading = ref(true)
const error = ref('')
const test = ref(null)
const attempts = ref([])
const results = ref([])
const persons = ref([])
const search = ref('')
const selectedResultStatus = ref('')

const personsById = computed(() => Object.fromEntries(persons.value.map((person) => [person.id, person])))
const resultByAttemptId = computed(() => Object.fromEntries(results.value.map((result) => [result.attempt_id, result])))

const rows = computed(() => {
  const normalizedQuery = search.value.trim().toLowerCase()

  return attempts.value
    .map((attempt) => {
      const person = attempt.person || personsById.value[attempt.person_id] || null
      const resultRecord = resultByAttemptId.value[attempt.id] || null
      const row = {
        attempt: {
          ...attempt,
          person,
          attemptStatus: getAttemptStatusMeta(attempt.status),
          resultStatus: getResultStatusMeta(resultRecord?.status),
        },
        resultRecord,
      }
      return {
        ...row,
        template: resolveTableTemplate({
          test: test.value,
          attempt: row.attempt,
          resultRecord,
        }),
      }
    })
    .filter((row) => {
      if (selectedResultStatus.value && row.resultRecord?.status !== selectedResultStatus.value) return false
      if (!normalizedQuery) return true

      const haystack = [
        personDisplayName(row.attempt.person, row.attempt.person_id),
        row.resultRecord?.json?.student?.name,
        String(row.attempt.id),
      ]
        .filter(Boolean)
        .join(' ')
        .toLowerCase()

      return haystack.includes(normalizedQuery)
    })
})

const hasSingleTemplate = computed(() => {
  return new Set(rows.value.map((row) => row.template.id)).size === 1
})

const activeTemplateColumns = computed(() => {
  if (!rows.value.length || !hasSingleTemplate.value) return []
  return rows.value[0].template.getTableColumns?.() || []
})

async function loadData() {
  loading.value = true
  error.value = ''

  try {
    const loadedTest = await get('tests', props.testId)
    const loadedAttempts = await list('attempts', {
      filter: toFilter({
        test_id: normalizeId(props.testId),
        is_archived: { $ne: true },
      }),
      appends: 'test,person',
      sort: '-submitted_at,-started_at,-id',
    })

    const attemptIds = loadedAttempts.map((attempt) => normalizeId(attempt.id))
    const loadedResults = attemptIds.length
      ? await list('attempt_results', {
        filter: toFilter({ attempt_id: { $in: attemptIds } }),
        sort: '-id',
      })
      : []

    const missingPersonIds = dedupe(
      loadedAttempts
        .filter((attempt) => !attempt.person && attempt.person_id != null)
        .map((attempt) => attempt.person_id),
    )

    const loadedPersons = missingPersonIds.length
      ? await list('persons', {
        filter: toFilter({ id: { $in: missingPersonIds } }),
        sort: 'id',
      })
      : []

    test.value = loadedTest
    attempts.value = loadedAttempts
    results.value = loadedResults
    persons.value = loadedPersons
  } catch {
    error.value = 'Не удалось загрузить прохождения по тесту'
  } finally {
    loading.value = false
  }
}

onMounted(loadData)
</script>

<template>
  <section class="w-full">
    <div class="mb-5 flex flex-wrap items-center gap-3">
      <RouterLink :to="{ name: 'results' }" class="ghost-button no-underline">← К списку тестов</RouterLink>
    </div>

    <div class="mb-6 flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
      <div>
        <p class="mb-2 text-sm font-semibold uppercase tracking-[0.24em] text-slate-400">Результаты</p>
        <h1 class="section-title">{{ test?.title || 'Прохождения по тесту' }}</h1>
      </div>
      <div class="grid gap-3 sm:grid-cols-[1fr_auto_auto]">
        <input v-model="search" class="field-input" type="text" placeholder="ФИО или ID прохождения" />
        <select v-model="selectedResultStatus" class="field-input">
          <option value="">Все статусы</option>
          <option value="pending">pending</option>
          <option value="processing">processing</option>
          <option value="success">success</option>
          <option value="error">error</option>
        </select>
        <button class="ghost-button" @click="loadData" :disabled="loading">
          {{ loading ? 'Загрузка…' : 'Обновить' }}
        </button>
      </div>
    </div>

    <div v-if="loading" class="glass-panel p-10 text-center text-sm text-slate-500">Загрузка попыток…</div>
    <div v-else-if="error" class="glass-panel p-10 text-center text-sm text-red-700">{{ error }}</div>
    <div v-else-if="!rows.length" class="glass-panel p-10 text-center text-sm text-slate-500">По этому тесту пока нет доступных попыток.</div>
    <div v-else class="overflow-hidden rounded-[30px] border border-white/60 bg-white/92 shadow-[0_20px_60px_rgba(15,23,42,0.08)]">
      <div class="overflow-x-auto">
        <table class="min-w-full border-collapse text-left text-sm">
          <thead class="bg-slate-50 text-slate-500">
            <tr>
              <th class="px-4 py-3 font-semibold">Тестируемый</th>
              <th class="px-4 py-3 font-semibold">Прохождение</th>
              <th class="px-4 py-3 font-semibold">Статусы</th>
              <th class="px-4 py-3 font-semibold">Отправлен</th>
              <th v-for="column in activeTemplateColumns" :key="column.key" class="px-4 py-3 font-semibold">
                {{ column.label }}
              </th>
              <th v-if="!activeTemplateColumns.length" class="px-4 py-3 font-semibold">Сводка</th>
              <th class="px-4 py-3 font-semibold"></th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in rows" :key="row.attempt.id" class="border-t border-slate-100 align-top">
              <td class="px-4 py-4">
                <div class="font-semibold text-slate-900">{{ row.resultRecord?.json?.student?.name || personDisplayName(row.attempt.person, row.attempt.person_id) }}</div>
                <div class="mt-1 text-xs text-slate-500">{{ personDisplayName(row.attempt.person, row.attempt.person_id) }}</div>
              </td>
              <td class="px-4 py-4 font-mono text-xs text-slate-600">{{ row.attempt.id }}</td>
              <td class="px-4 py-4">
                <div class="flex flex-col gap-2">
                  <span class="badge" :class="row.attempt.attemptStatus.className">{{ row.attempt.attemptStatus.label }}</span>
                  <span v-if="row.resultRecord" class="badge" :class="row.attempt.resultStatus.className">{{ row.attempt.resultStatus.label }}</span>
                  <span v-else class="badge bg-slate-100 text-slate-500">Нет результата</span>
                </div>
              </td>
              <td class="px-4 py-4 text-slate-600">{{ formatDateTime(row.attempt.submitted_at) }}</td>
              <td v-for="column in activeTemplateColumns" :key="column.key" class="px-4 py-4 text-slate-800">
                {{ column.value(row) }}
              </td>
              <td v-if="!activeTemplateColumns.length" class="px-4 py-4 text-slate-700">
                {{ row.template.getTableColumns?.()[0]?.value?.(row) || '—' }}
              </td>
              <td class="px-4 py-4">
                <RouterLink
                  :to="{ name: 'result-detail', params: { testId: props.testId, attemptId: row.attempt.id } }"
                  class="ghost-button no-underline"
                >
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
