<script setup>
import { computed, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { list, toFilter } from '../utils/nocobase'

const loading = ref(true)
const error = ref('')
const tests = ref([])
const attempts = ref([])
const search = ref('')

const attemptsByTestId = computed(() => {
  return attempts.value.reduce((map, attempt) => {
    const testId = attempt.test_assignment?.test_id ?? attempt.test_assignment?.test?.id
    if (testId == null) return map
    if (!map[testId]) map[testId] = []
    map[testId].push(attempt)
    return map
  }, {})
})

const rows = computed(() => {
  const query = search.value.trim().toLowerCase()

  return tests.value
    .map((test) => {
      const testAttempts = attemptsByTestId.value[test.id] || []
      return {
        test,
        attemptsCount: testAttempts.length,
      }
    })
    .filter((row) => {
      if (!query) return true
      const haystack = [row.test.title, row.test.code, row.test.description].filter(Boolean).join(' ').toLowerCase()
      return haystack.includes(query)
    })
})

async function loadData() {
  loading.value = true
  error.value = ''

  try {
    const [loadedTests, loadedAttempts] = await Promise.all([
      list('tests', { sort: 'title,id' }),
      list('attempts', {
        appends: 'test_assignment',
        sort: '-submitted_at,-started_at,-id',
      }),
    ])

    tests.value = loadedTests
    attempts.value = loadedAttempts
  } catch {
    error.value = 'Не удалось загрузить список тестов'
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
        <h1 class="section-title">Тесты</h1>
        <p class="mt-2 max-w-3xl text-sm leading-6 text-slate-500">Выберите тест, чтобы перейти к списку попыток и открыть нужный результат.</p>
      </div>
      <div class="flex w-full gap-3 lg:w-auto">
        <input v-model="search" class="field-input lg:w-80" type="text" placeholder="Название или код теста" />
        <button class="ghost-button shrink-0" @click="loadData" :disabled="loading">
          {{ loading ? 'Загрузка…' : 'Обновить' }}
        </button>
      </div>
    </div>

    <div v-if="loading" class="glass-panel p-10 text-center text-sm text-slate-500">Загрузка тестов…</div>
    <div v-else-if="error" class="glass-panel p-10 text-center text-sm text-red-700">{{ error }}</div>
    <div v-else-if="!rows.length" class="glass-panel p-10 text-center text-sm text-slate-500">Тесты не найдены.</div>

    <div v-else class="grid gap-4 lg:grid-cols-2">
      <article
        v-for="row in rows"
        :key="row.test.id"
        class="glass-panel flex h-full flex-col overflow-hidden p-6"
      >
        <div class="flex items-start justify-between gap-3">
          <h2 class="text-2xl font-semibold text-slate-900">{{ row.test.title }}</h2>
        </div>

        <div class="mt-6 flex items-center justify-between gap-3">
          <div class="text-sm text-slate-500">
            <span>{{ row.attemptsCount }} попыт{{ row.attemptsCount === 1 ? 'ка' : row.attemptsCount >= 2 && row.attemptsCount <= 4 ? 'ки' : 'ок' }}</span>
          </div>
          <RouterLink
            :to="{ name: 'results-test', params: { testId: row.test.id } }"
            class="primary-button shrink-0 no-underline"
          >
            Открыть
          </RouterLink>
        </div>
      </article>
    </div>
  </section>
</template>
