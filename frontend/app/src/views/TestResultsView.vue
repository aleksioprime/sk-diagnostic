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
const classes = ref([])
const departments = ref([])
const search = ref('')
const selectedResultStatus = ref('')
const selectedClassId = ref('')
const selectedDepartmentId = ref('')
const selectedIds = ref(new Set())
const showSummaryModal = ref(false)

const personsById = computed(() => Object.fromEntries(persons.value.map((person) => [person.id, person])))
const resultByAttemptId = computed(() => Object.fromEntries(results.value.map((result) => [result.attempt_id, result])))

const resultStatusOptions = ['pending', 'processing', 'calculated', 'error'].map((value) => ({
  value,
  label: getResultStatusMeta(value).label,
}))

function mergePersonData(primary, secondary) {
  if (primary && secondary) {
    return {
      ...primary,
      ...secondary,
      current_class: secondary.current_class || primary.current_class,
      departments: secondary.departments || primary.departments,
    }
  }
  return primary || secondary || null
}

function extractClassLabel(cls) {
  if (!cls) return '—'
  const grade = cls.grade != null && cls.grade !== '' ? String(cls.grade).trim() : ''
  const letter = cls.letter != null && cls.letter !== '' ? String(cls.letter).trim() : ''
  const gradeLetter = `${grade}${letter}`.trim()
  return gradeLetter || cls.title || cls.name || (cls.id != null ? `Класс #${cls.id}` : '—')
}

function extractDepartmentLabel(department) {
  if (!department) return '—'
  return department.title || department.name || department.code || (department.id != null ? `Подразделение #${department.id}` : '—')
}

function personClassId(person) {
  return normalizeId(person?.current_class_id ?? person?.current_class?.id)
}

function personDepartmentIds(person) {
  const byObjects = Array.isArray(person?.departments)
    ? person.departments.map((item) => normalizeId(item?.id ?? item)).filter((id) => id !== null && id !== undefined && id !== '')
    : []
  if (byObjects.length) return byObjects

  return Array.isArray(person?.department_ids)
    ? person.department_ids.map((id) => normalizeId(id)).filter((id) => id !== null && id !== undefined && id !== '')
    : []
}

const classOptions = computed(() => {
  return classes.value
    .map((cls) => ({
      id: normalizeId(cls.id),
      label: extractClassLabel(cls),
      grade: Number(cls.grade) || 0,
      letter: String(cls.letter || '').trim(),
    }))
    .sort((a, b) => {
      if (a.grade !== b.grade) return a.grade - b.grade

      const byLetter = a.letter.localeCompare(b.letter, 'ru', {
        sensitivity: 'base',
        numeric: true,
      })
      if (byLetter !== 0) return byLetter

      return a.label.localeCompare(b.label, 'ru', { sensitivity: 'base', numeric: true })
    })
    .map(({ id, label }) => ({ id, label }))
})

const departmentOptions = computed(() => {
  return departments.value
    .map((department) => ({ id: normalizeId(department.id), label: extractDepartmentLabel(department) }))
    .sort((a, b) => a.label.localeCompare(b.label, 'ru'))
})

const rows = computed(() => {
  const normalizedQuery = search.value.trim().toLowerCase()

  return attempts.value
    .map((attempt) => {
      const person = mergePersonData(attempt.person || null, personsById.value[attempt.person_id] || null)
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

      if (selectedClassId.value) {
        const classId = personClassId(row.attempt.person)
        if (String(classId) !== String(selectedClassId.value)) return false
      }

      if (selectedDepartmentId.value) {
        const departmentIds = personDepartmentIds(row.attempt.person)
        if (!departmentIds.some((id) => String(id) === String(selectedDepartmentId.value))) return false
      }

      if (!normalizedQuery) return true

      const haystack = [
        personDisplayName(row.attempt.person, row.attempt.person_id),
        row.resultRecord?.json_results?.student?.name,
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

const selectedRows = computed(() => rows.value.filter((row) => selectedIds.value.has(row.attempt.id)))

const isAllSelected = computed(() => rows.value.length > 0 && rows.value.every((row) => selectedIds.value.has(row.attempt.id)))

const hasActiveFilters = computed(() => {
  return Boolean(search.value || selectedResultStatus.value || selectedClassId.value || selectedDepartmentId.value)
})

const summaryPalette = ['#0f766e', '#c2410c', '#0369a1', '#15803d', '#7c3aed', '#b45309', '#0f172a', '#dc2626', '#0891b2', '#4d7c0f']
const moodStatusColors = {
  ok: '#15803d',
  attention: '#c2410c',
}

const domikiSummaryTables = computed(() => {
  if (summaryContent.value?.kind !== 'domiki-distributions') return []
  return summaryContent.value.tables || []
})

function formatPercent(percent) {
  const fixed = Number(percent || 0).toFixed(1)
  return fixed.endsWith('.0') ? `${Math.trunc(Number(fixed))}%` : `${fixed}%`
}

function chartColor(index) {
  return summaryPalette[index % summaryPalette.length]
}

function pieChartStyle(items = []) {
  if (!items.length) {
    return {
      background: '#e2e8f0',
    }
  }

  let offset = 0
  const segments = items
    .map((item, index) => {
      const start = offset
      offset += Number(item.percent || 0)
      const end = Math.min(offset, 100)
      return `${chartColor(index)} ${start}% ${end}%`
    })
    .join(', ')

  return {
    background: `conic-gradient(${segments})`,
  }
}

const summaryContent = computed(() => {
  if (!selectedRows.value.length || !hasSingleTemplate.value) return null
  const template = selectedRows.value[0]?.template
  return template?.buildGroupSummary?.(selectedRows.value) ?? null
})

function toggleSelectRow(id) {
  const next = new Set(selectedIds.value)
  if (next.has(id)) next.delete(id)
  else next.add(id)
  selectedIds.value = next
}

function toggleSelectAll() {
  if (isAllSelected.value) {
    selectedIds.value = new Set()
  } else {
    selectedIds.value = new Set(rows.value.map((row) => row.attempt.id))
  }
}

function resetFilters() {
  search.value = ''
  selectedResultStatus.value = ''
  selectedClassId.value = ''
  selectedDepartmentId.value = ''
}

async function loadData() {
  loading.value = true
  error.value = ''

  try {
    const loadedTest = await get('tests', props.testId)
    const loadedAttempts = await list('attempts', {
      filter: toFilter({
        test_assignment: { test_id: normalizeId(props.testId) },
      }),
      appends: 'test_assignment,test_assignment.test,person',
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
        .filter((attempt) => attempt.person_id != null)
        .map((attempt) => normalizeId(attempt.person_id)),
    )

    const [loadedPersonsResult, loadedClassesResult, loadedDepartmentsResult] = await Promise.allSettled([
      missingPersonIds.length
        ? list('persons', {
          filter: toFilter({ id: { $in: missingPersonIds } }),
          sort: 'id',
          appends: 'current_class,departments',
        })
        : Promise.resolve([]),
      list('classes', { sort: 'grade,letter,id' }),
      list('departments', { sort: 'title,id' }),
    ])

    const loadedPersons = loadedPersonsResult.status === 'fulfilled' ? loadedPersonsResult.value : []
    const loadedClasses = loadedClassesResult.status === 'fulfilled' ? loadedClassesResult.value : []
    const loadedDepartments = loadedDepartmentsResult.status === 'fulfilled' ? loadedDepartmentsResult.value : []

    test.value = loadedTest
    attempts.value = loadedAttempts
    results.value = loadedResults
    persons.value = loadedPersons
    classes.value = loadedClasses
    departments.value = loadedDepartments
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

    <div class="mb-6 space-y-4">
      <div>
        <p class="mb-2 text-sm font-semibold uppercase tracking-[0.24em] text-slate-400">Результаты</p>
        <h1 class="section-title">{{ test?.title || 'Прохождения по тесту' }}</h1>
      </div>

      <div class="glass-panel p-4 sm:p-5">
        <div class="grid gap-3 sm:grid-cols-2 lg:grid-cols-[minmax(260px,2fr)_minmax(180px,1fr)_minmax(200px,1fr)_auto_auto]">
          <input v-model="search" class="field-input" type="text" placeholder="Поиск по ФИО" />
          <select v-model="selectedResultStatus" class="field-input">
            <option value="">Все статусы</option>
            <option v-for="option in resultStatusOptions" :key="option.value" :value="option.value">{{ option.label }}</option>
          </select>
          <select v-model="selectedDepartmentId" class="field-input">
            <option value="">Все подразделения</option>
            <option v-for="option in departmentOptions" :key="`department-${option.id}`" :value="option.id">{{ option.label }}</option>
          </select>
          <button class="ghost-button" @click="loadData" :disabled="loading">
            {{ loading ? 'Загрузка…' : 'Обновить' }}
          </button>
          <button class="ghost-button" @click="resetFilters" :disabled="!hasActiveFilters">
            Сбросить фильтры
          </button>
        </div>

        <div class="mt-4">
          <p class="mb-2 text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">Класс</p>
          <div class="flex flex-wrap gap-2">
            <button
              class="rounded-full border px-3 py-1.5 text-sm font-medium transition"
              :class="selectedClassId === ''
                ? 'border-primary bg-primary text-white'
                : 'border-slate-300 bg-white text-slate-700 hover:bg-slate-50'"
              @click="selectedClassId = ''"
            >
              Все классы
            </button>
            <button
              v-for="option in classOptions"
              :key="`class-chip-${option.id}`"
              class="rounded-full border px-3 py-1.5 text-sm font-medium transition"
              :class="String(selectedClassId) === String(option.id)
                ? 'border-primary bg-primary text-white'
                : 'border-slate-300 bg-white text-slate-700 hover:bg-slate-50'"
              @click="selectedClassId = option.id"
            >
              {{ option.label }}
            </button>
          </div>
        </div>
      </div>
    </div>

    <div v-if="loading" class="glass-panel p-10 text-center text-sm text-slate-500">Загрузка попыток…</div>
    <div v-else-if="error" class="glass-panel p-10 text-center text-sm text-red-700">{{ error }}</div>
    <div v-else-if="!rows.length" class="glass-panel p-10 text-center text-sm text-slate-500">По этому тесту пока нет доступных попыток.</div>
    <div v-else class="overflow-hidden border border-white/60 bg-white/92 shadow-[0_20px_60px_rgba(15,23,42,0.08)]">
      <div class="overflow-x-auto">
        <table class="min-w-full border-collapse text-left text-sm">
          <thead class="bg-slate-50 text-slate-500">
            <tr>
              <th class="px-4 py-3">
                <input type="checkbox" :checked="isAllSelected" @change="toggleSelectAll" class="cursor-pointer" />
              </th>
              <th class="px-4 py-3 font-semibold">Тестируемый</th>
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
            <tr v-for="row in rows" :key="row.attempt.id" class="border-t border-slate-100 align-top" :class="{ 'bg-primary/5': selectedIds.has(row.attempt.id) }">
              <td class="px-4 py-4">
                <input type="checkbox" :checked="selectedIds.has(row.attempt.id)" @change="toggleSelectRow(row.attempt.id)" class="cursor-pointer" />
              </td>
              <td class="px-4 py-4">
                <div class="font-semibold text-slate-900">{{ row.resultRecord?.json_results?.student?.name || personDisplayName(row.attempt.person, row.attempt.person_id) }}</div>
              </td>
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

    <!-- Кнопка сводной информации -->
    <div v-if="selectedIds.size >= 2" class="mt-4 flex items-center gap-3">
      <span class="text-sm text-slate-500">Выбрано: {{ selectedIds.size }}</span>
      <button class="ghost-button" @click="showSummaryModal = true">Сводная информация</button>
      <button class="ghost-button text-slate-400" @click="selectedIds = new Set()">Сбросить выбор</button>
    </div>

    <!-- Модальное окно сводной информации -->
    <Teleport to="body">
      <div v-if="showSummaryModal" class="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto p-4 sm:items-center" @click.self="showSummaryModal = false">
        <div class="absolute inset-0 bg-slate-900/40 backdrop-blur-sm" @click="showSummaryModal = false"></div>
        <div class="relative z-10 my-2 w-full max-w-2xl max-h-[calc(100vh-2rem)] overflow-y-auto rounded-3xl border border-white/60 bg-white p-6 shadow-[0_30px_80px_rgba(15,23,42,0.18)] sm:my-6 sm:p-8">
          <div class="mb-5 flex items-start justify-between gap-4">
            <div>
              <h2 class="text-xl font-semibold text-slate-900">Сводная информация</h2>
            </div>
            <button class="ghost-button shrink-0" @click="showSummaryModal = false">Закрыть</button>
          </div>
          <div v-if="summaryContent">
            <div v-if="summaryContent.stub" class="rounded-2xl border border-dashed border-slate-300 bg-slate-50 p-6 text-center text-sm text-slate-500">
              {{ summaryContent.stub }}
            </div>
            <div v-else-if="summaryContent.kind === 'domiki-distributions'" class="space-y-6">
              <p class="text-sm text-slate-500">
                Процентное распределение по {{ summaryContent.total }} выбранным прохождениям.
              </p>

              <article
                v-for="table in domikiSummaryTables"
                :key="table.id"
                class="rounded-2xl border border-slate-200/80 bg-slate-50/70 p-4 sm:p-5"
              >
                <h3 class="mb-3 text-base font-semibold text-slate-900">{{ table.title }}</h3>

                <div class="grid gap-4 lg:grid-cols-[minmax(0,1fr)_220px]">
                  <div class="overflow-x-auto">
                    <table class="min-w-full border-collapse text-sm">
                      <thead v-if="table.id !== 'domains_mood'">
                        <tr class="border-b border-slate-200 text-left text-slate-500">
                          <th class="px-2 py-2 font-semibold">Результат</th>
                          <th class="px-2 py-2 font-semibold">Кол-во</th>
                          <th class="px-2 py-2 font-semibold">%</th>
                        </tr>
                      </thead>
                      <thead v-else>
                        <tr class="border-b border-slate-200 text-left text-slate-500">
                          <th class="px-2 py-2 font-semibold">Сфера</th>
                          <th class="px-2 py-2 font-semibold">Отклонений нет</th>
                          <th class="px-2 py-2 font-semibold">Обратить внимание</th>
                        </tr>
                      </thead>
                      <tbody v-if="table.id !== 'domains_mood'">
                        <tr v-for="(item, index) in table.items" :key="`${table.id}-${item.label}`" class="border-b border-slate-100 last:border-b-0">
                          <td class="px-2 py-2 text-slate-800">
                            <span class="inline-flex items-center gap-2">
                              <span class="h-2.5 w-2.5 rounded-full" :style="{ backgroundColor: chartColor(index) }"></span>
                              {{ item.label }}
                            </span>
                          </td>
                          <td class="px-2 py-2 text-slate-700">{{ item.count }}</td>
                          <td class="px-2 py-2 font-medium text-slate-900">{{ formatPercent(item.percent) }}</td>
                        </tr>
                      </tbody>
                      <tbody v-else>
                        <tr v-for="item in table.items" :key="`${table.id}-${item.label}`" class="border-b border-slate-100 last:border-b-0">
                          <td class="px-2 py-2 text-slate-800">{{ item.label }}</td>
                          <td class="px-2 py-2 font-medium text-emerald-700">{{ formatPercent(item.okPercent) }}</td>
                          <td class="px-2 py-2 font-medium text-amber-700">{{ formatPercent(item.attentionPercent) }}</td>
                        </tr>
                      </tbody>
                    </table>
                  </div>

                  <div v-if="table.chartType === 'pie'" class="flex items-center justify-center">
                    <div class="relative h-44 w-44 rounded-full border border-white/70 shadow-inner" :style="pieChartStyle(table.items)">
                      <div class="absolute inset-0 m-auto h-20 w-20 rounded-full bg-white/95 shadow-[0_0_0_1px_rgba(148,163,184,0.2)]"></div>
                    </div>
                  </div>

                  <div v-else-if="table.chartType === 'stackedBar'" class="space-y-3">
                    <div class="flex items-center gap-4 text-xs text-slate-600">
                      <span class="inline-flex items-center gap-1.5">
                        <span class="h-2.5 w-2.5 rounded-full" :style="{ backgroundColor: moodStatusColors.ok }"></span>
                        Отклонений нет
                      </span>
                      <span class="inline-flex items-center gap-1.5">
                        <span class="h-2.5 w-2.5 rounded-full" :style="{ backgroundColor: moodStatusColors.attention }"></span>
                        Обратить внимание
                      </span>
                    </div>

                    <div v-for="item in table.items" :key="`${table.id}-stack-${item.label}`" class="rounded-xl bg-white/80 p-2">
                      <div class="mb-1 flex items-center justify-between gap-2 text-xs text-slate-600">
                        <span class="truncate">{{ item.label }}</span>
                        <span>{{ formatPercent(item.okPercent) }} / {{ formatPercent(item.attentionPercent) }}</span>
                      </div>
                      <div class="flex h-2 overflow-hidden rounded-full bg-slate-200">
                        <div class="h-full" :style="{ width: `${item.okPercent}%`, backgroundColor: moodStatusColors.ok }"></div>
                        <div class="h-full" :style="{ width: `${item.attentionPercent}%`, backgroundColor: moodStatusColors.attention }"></div>
                      </div>
                    </div>
                  </div>

                  <div v-else class="space-y-2">
                    <div v-for="(item, index) in table.items" :key="`${table.id}-bar-${item.label}`" class="rounded-xl bg-white/80 p-2">
                      <div class="mb-1 flex items-center justify-between gap-2 text-xs text-slate-600">
                        <span class="truncate">{{ item.label }}</span>
                        <span>{{ formatPercent(item.percent) }}</span>
                      </div>
                      <div class="h-2 overflow-hidden rounded-full bg-slate-200">
                        <div class="h-full rounded-full" :style="{ width: `${item.percent}%`, backgroundColor: chartColor(index) }"></div>
                      </div>
                    </div>
                  </div>
                </div>
              </article>
            </div>
            <div v-else class="text-sm text-slate-700">{{ summaryContent }}</div>
          </div>
          <div v-else class="rounded-2xl border border-dashed border-slate-300 bg-slate-50 p-6 text-center text-sm text-slate-500">
            Сводная информация для данного типа теста ещё не реализована.
          </div>
        </div>
      </div>
    </Teleport>
  </section>
</template>
