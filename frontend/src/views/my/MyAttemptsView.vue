<script setup>
import { onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { myAttempts } from '@/api/diagnostic'
import { errorMessage, SkeletonTable, UiBadge } from 'sk-ui'
import { STATUS_TONES, formatDate } from '@/utils/format'

const attempts = ref([])
const loading = ref(true)
const error = ref('')

const TITLES = { assigned: 'Ждёт вас', in_progress: 'Начата', submitted: 'Пройдена' }

onMounted(async () => {
  try {
    attempts.value = await myAttempts()
  } catch (e) {
    error.value = errorMessage(e)
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div>
    <h1 class="text-2xl font-bold">Мои диагностики</h1>
    <p class="mt-1 text-ink-muted">Здесь появляются диагностики, которые психологическая служба назначила вашему классу.</p>
    <p v-if="error" role="alert" class="mt-4 rounded-control bg-red-100 px-3 py-2 text-sm text-red-800">{{ error }}</p>
    <SkeletonTable v-if="loading" class="mt-6" :rows="3" :columns="2" />
    <p v-else-if="!attempts.length" class="mt-10 text-center text-ink-muted">Сейчас назначенных диагностик нет.</p>
    <ul v-else class="mt-6 grid gap-3">
      <li v-for="attempt in attempts" :key="attempt.id" class="flex flex-wrap items-center gap-4 rounded-card border border-line bg-surface p-4">
        <div class="min-w-0 flex-1">
          <p class="font-semibold">{{ attempt.test.title }}</p>
          <p class="mt-1 text-sm text-ink-muted">
            {{ attempt.assignment_title }}
            <template v-if="attempt.submitted_at"> · пройдена {{ formatDate(attempt.submitted_at) }}</template>
          </p>
        </div>
        <UiBadge :tone="STATUS_TONES[attempt.status]">{{ TITLES[attempt.status] }}</UiBadge>
        <RouterLink
          v-if="attempt.is_open"
          :to="{ name: 'attempt-pass', params: { id: attempt.id } }"
          class="inline-flex h-10 items-center rounded-control bg-brand-600 px-4 font-medium text-white hover:bg-brand-700"
        >
          {{ attempt.status === 'in_progress' ? 'Продолжить' : 'Начать' }}
        </RouterLink>
      </li>
    </ul>
  </div>
</template>
