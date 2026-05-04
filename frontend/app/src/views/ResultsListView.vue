<script setup>
import { computed, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { list, normalizeId } from '../utils/nocobase'

const loading = ref(true)
const error = ref('')
const assignments = ref([])
const attempts = ref([])
const search = ref('')

const attemptsByAssignmentId = computed(() => {
  return attempts.value.reduce((map, attempt) => {
    const assignmentId = normalizeId(attempt.test_assignment_id ?? attempt.test_assignment?.id)
    if (assignmentId == null) return map
    if (!map[assignmentId]) map[assignmentId] = []
    map[assignmentId].push(attempt)
    return map
  }, {})
})

function issuedWord(count) {
  if (count % 10 === 1 && count % 100 !== 11) return 'Выдана'
  if ([2, 3, 4].includes(count % 10) && ![12, 13, 14].includes(count % 100)) return 'Выданы'
  return 'Выдано'
}

const rows = computed(() => {
  const query = search.value.trim().toLowerCase()

  return assignments.value
    .map((assignment) => {
      const assignmentAttempts = attemptsByAssignmentId.value[assignment.id] || []
      const uniqueStudents = new Set(
        assignmentAttempts
          .map((attempt) => normalizeId(attempt.person_id))
          .filter((id) => id !== null && id !== undefined && id !== ''),
      )

      return {
        assignment,
        attemptsCount: assignmentAttempts.length,
        studentsCount: uniqueStudents.size,
        completedCount: assignmentAttempts.filter((attempt) => ['submitted', 'completed'].includes(attempt.status)).length,
      }
    })
    .filter((row) => {
      if (!query) return true
      const haystack = [
        row.assignment.title,
        row.assignment.test?.title,
        row.assignment.test?.code,
        row.assignment.id,
      ]
        .filter(Boolean)
        .join(' ')
        .toLowerCase()
      return haystack.includes(query)
    })
})

async function loadData() {
  loading.value = true
  error.value = ''

  try {
    const [loadedAssignments, loadedAttempts] = await Promise.all([
      list('test_assignments', {
        appends: 'test',
        sort: '-id',
      }),
      list('attempts', {
        appends: 'test_assignment',
        sort: '-submitted_at,-started_at,-id',
      }),
    ])

    assignments.value = loadedAssignments
    attempts.value = loadedAttempts
  } catch {
    error.value = 'Не удалось загрузить список выдач'
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
        <p class="mb-2 text-sm font-semibold uppercase tracking-[0.24em] text-slate-400">Результаты</p>
        <h1 class="section-title">Выдачи тестов</h1>
        <p class="mt-2 max-w-3xl text-sm leading-6 text-slate-500">Выберите выдачу, чтобы перейти к списку прохождений и открыть нужный результат.</p>
      </div>
      <div class="flex w-full gap-3 lg:w-auto">
        <input v-model="search" class="field-input lg:w-80" type="text" placeholder="Название выдачи или теста" />
        <button class="ghost-button shrink-0" @click="loadData" :disabled="loading">
          {{ loading ? 'Загрузка…' : 'Обновить' }}
        </button>
      </div>
    </div>

    <div v-if="loading" class="glass-panel p-10 text-center text-sm text-slate-500">Загрузка выдач…</div>
    <div v-else-if="error" class="glass-panel p-10 text-center text-sm text-red-700">{{ error }}</div>
    <div v-else-if="!rows.length" class="glass-panel p-10 text-center text-sm text-slate-500">Выдачи не найдены.</div>

    <div v-else class="grid gap-4 lg:grid-cols-2">
      <article
        v-for="row in rows"
        :key="row.assignment.id"
        class="glass-panel flex h-full flex-col overflow-hidden p-6"
      >
        <div class="flex items-start justify-between gap-3">
          <h2 class="text-2xl font-semibold text-slate-900">{{ row.assignment.title || `Выдача #${row.assignment.id}` }}</h2>
        </div>

        <p class="mt-2 text-sm text-slate-500">
          Тест: <span class="font-medium text-slate-700">{{ row.assignment.test?.title || `#${row.assignment.test_id}` }}</span>
        </p>

        <div class="mt-6 flex items-center justify-between gap-3">
          <div class="text-sm text-slate-500">
            <span>
              {{ issuedWord(row.studentsCount) }}: {{ row.studentsCount }} · Пройдено: {{ row.completedCount }}
            </span>
          </div>
          <RouterLink
            :to="{ name: 'results-assignment', params: { assignmentId: row.assignment.id } }"
            class="primary-button shrink-0 no-underline"
          >
            Открыть
          </RouterLink>
        </div>
      </article>
    </div>
  </section>
</template>
