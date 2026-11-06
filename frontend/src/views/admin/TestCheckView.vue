<script setup>
import { computed, onMounted, ref } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import { getAdminTest, getTestReadiness, patchAdminTest } from '@/api/diagnostic'
import { errorMessage, SkeletonPage, UiBadge, UiButton, UiCard } from 'sk-ui'
import TestTabs from '@/components/tests/TestTabs.vue'

const TABS = { questions: 'admin-test-questions', scoring: 'admin-test' }

const route = useRoute()
const test = ref(null)
const readiness = ref(null)
const loadError = ref('')
const error = ref('')
const notice = ref('')
const checking = ref(false)
const switching = ref(false)

const errors = computed(() => readiness.value?.problems.filter((p) => p.level === 'error') || [])
const warnings = computed(() => readiness.value?.problems.filter((p) => p.level === 'warning') || [])

async function check() {
  checking.value = true
  error.value = ''
  try {
    readiness.value = await getTestReadiness(route.params.id)
  } catch (e) {
    error.value = errorMessage(e)
  } finally {
    checking.value = false
  }
}

onMounted(async () => {
  try {
    test.value = await getAdminTest(route.params.id)
    await check()
  } catch (e) {
    loadError.value = errorMessage(e)
  }
})

async function setActive(value) {
  switching.value = true
  error.value = ''
  notice.value = ''
  try {
    test.value = await patchAdminTest(route.params.id, { is_active: value })
    notice.value = value ? 'Методика включена: психологи могут выдавать её классам.' : 'Методика отключена: новые выдачи недоступны.'
  } catch (e) {
    error.value = errorMessage(e)
    await check()
  } finally {
    switching.value = false
  }
}
</script>

<template>
  <p v-if="loadError" role="alert" class="rounded-control bg-red-100 px-3 py-2 text-sm text-red-800">{{ loadError }}</p>
  <SkeletonPage v-else-if="!test" />
  <div v-else class="max-w-4xl">
    <RouterLink :to="{ name: 'admin-tests' }" class="text-sm text-brand-700 hover:underline">← Все методики</RouterLink>
    <h1 class="mt-2 text-2xl font-bold">{{ test.title }}</h1>
    <p class="mt-1 text-sm text-ink-muted"><code>{{ test.code }}</code></p>
    <TestTabs :id="route.params.id" class="mt-4" />

    <p v-if="error" role="alert" class="mt-4 rounded-control bg-red-100 px-3 py-2 text-sm text-red-800">{{ error }}</p>
    <p v-if="notice" role="status" class="mt-4 rounded-control bg-brand-50 px-3 py-2 text-sm text-brand-700">{{ notice }}</p>

    <UiCard class="mt-4 grid gap-4">
      <div class="flex flex-wrap items-center gap-3">
        <h2 class="text-lg font-semibold">Готовность</h2>
        <UiBadge :tone="test.is_active ? 'success' : 'neutral'">{{ test.is_active ? 'Включена' : 'Отключена' }}</UiBadge>
        <UiButton class="ml-auto" size="sm" :loading="checking" @click="check">Проверить снова</UiButton>
      </div>

      <p v-if="readiness && !readiness.problems.length" class="rounded-control bg-green-100 px-3 py-2 text-sm text-green-800">
        Проблем не найдено: вопросы заполнены, расчёт работает на пробных ответах.
      </p>

      <div v-if="errors.length">
        <h3 class="text-sm font-medium text-red-800">Мешает включить</h3>
        <ul class="mt-2 grid gap-2">
          <li v-for="problem in errors" :key="problem.text" class="flex flex-wrap items-baseline gap-x-3 rounded-control bg-red-100 px-3 py-2 text-sm text-red-800">
            <span class="min-w-0 flex-1 break-words">{{ problem.text }}</span>
            <RouterLink :to="{ name: TABS[problem.tab], params: { id: route.params.id } }" class="font-medium underline">Исправить</RouterLink>
          </li>
        </ul>
      </div>

      <div v-if="warnings.length">
        <h3 class="text-sm font-medium text-amber-900">Стоит посмотреть</h3>
        <ul class="mt-2 grid gap-2">
          <li v-for="problem in warnings" :key="problem.text" class="flex flex-wrap items-baseline gap-x-3 rounded-control bg-amber-50 px-3 py-2 text-sm text-amber-900">
            <span class="min-w-0 flex-1 break-words">{{ problem.text }}</span>
            <RouterLink :to="{ name: TABS[problem.tab], params: { id: route.params.id } }" class="font-medium underline">Открыть</RouterLink>
          </li>
        </ul>
      </div>

      <div class="flex flex-wrap items-center gap-2">
        <RouterLink :to="{ name: 'admin-test-preview', params: { id: route.params.id } }" class="inline-flex h-10 items-center rounded-control border border-line bg-surface px-4 hover:bg-brand-50">
          Пройти как ученик
        </RouterLink>
        <UiButton v-if="test.is_active" :loading="switching" @click="setActive(false)">Отключить</UiButton>
        <UiButton v-else variant="primary" :loading="switching" :disabled="!readiness?.ready" @click="setActive(true)">Включить</UiButton>
      </div>
    </UiCard>
  </div>
</template>
