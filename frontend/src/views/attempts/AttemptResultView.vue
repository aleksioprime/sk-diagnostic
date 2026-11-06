<script setup>
import { computed, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { getAttempt, recalculateAttempt, setBirthDate } from '@/api/diagnostic'
import { errorMessage, UiButton, UiCard, UiInput } from 'sk-ui'
import DomikiResult from '@/components/results/DomikiResult.vue'
import MotivationResult from '@/components/results/MotivationResult.vue'
import SummaryResult from '@/components/results/SummaryResult.vue'
import { formatDate, formatDateTime, formatDuration } from '@/utils/format'

const props = defineProps({ id: { type: String, required: true } })

const attempt = ref(null)
const error = ref('')
const notice = ref('')
const busy = ref(false)
const birthDate = ref('')
const showAnswers = ref(false)

const template = computed(() => {
  // По форме результата, а не по коду: так копия методики выглядит как исходная
  const result = attempt.value?.result?.result || {}
  if ('level' in result) return MotivationResult
  if ('vegetative_coefficient' in result) return DomikiResult
  return SummaryResult
})

onMounted(async () => {
  try {
    attempt.value = await getAttempt(props.id)
    birthDate.value = attempt.value.student.birth_date || ''
  } catch (e) {
    error.value = errorMessage(e)
  }
})

async function saveBirthDateAndRecalculate() {
  busy.value = true
  error.value = ''
  notice.value = ''
  try {
    await setBirthDate(attempt.value.student.person_id, birthDate.value || null)
    attempt.value = await recalculateAttempt(props.id)
    notice.value = 'Результат пересчитан'
  } catch (e) {
    error.value = errorMessage(e)
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <div>
    <RouterLink v-if="attempt" :to="{ name: 'assignment', params: { id: attempt.assignment_id } }" class="text-sm text-ink-muted hover:text-ink">
      ← {{ attempt.assignment_title }}
    </RouterLink>
    <p v-if="error" role="alert" class="mt-4 rounded-control bg-red-100 px-3 py-2 text-sm text-red-800">{{ error }}</p>
    <p v-if="notice" role="status" class="mt-4 rounded-control bg-brand-50 px-3 py-2 text-sm text-brand-700">{{ notice }}</p>

    <template v-if="attempt">
      <p class="mt-2 text-sm text-ink-muted">{{ attempt.test_title }}</p>
      <h1 class="text-2xl font-bold">{{ attempt.student.full_name }}</h1>
      <p class="mt-1 text-sm text-ink-muted">
        {{ attempt.student.class_name || 'Класс не указан' }} · дата рождения: {{ formatDate(attempt.student.birth_date) }} · завершена
        {{ formatDateTime(attempt.submitted_at) }} · {{ formatDuration(attempt.duration) }}
      </p>

      <UiCard class="mt-6">
        <div v-if="attempt.result_status === 'error'" class="rounded-control bg-amber-50 px-4 py-3 text-amber-900">
          <p class="font-semibold">Результат не рассчитан</p>
          <p class="mt-1 text-sm">{{ attempt.result_error }}</p>
        </div>
        <component :is="template" v-else-if="template && attempt.result" :data="attempt.result" />
      </UiCard>

      <form class="mt-4 flex flex-wrap items-end gap-3" @submit.prevent="saveBirthDateAndRecalculate">
        <UiInput v-model="birthDate" label="Дата рождения ученика" type="date" />
        <UiButton type="submit" :loading="busy">Сохранить и пересчитать</UiButton>
      </form>

      <section class="mt-6">
        <button type="button" class="font-medium text-brand-700" :aria-expanded="showAnswers" @click="showAnswers = !showAnswers">
          {{ showAnswers ? 'Скрыть ответы' : `Ответы ученика (${attempt.answers.length})` }}
        </button>
        <ol v-if="showAnswers" class="mt-3 grid gap-2">
          <li v-for="answer in attempt.answers" :key="answer.question_id" class="rounded-control border border-line bg-surface px-3 py-2 text-sm">
            <span class="text-ink-muted">{{ answer.order }}. {{ answer.text }}</span>
            <span class="block font-medium">{{ answer.answer ?? '—' }}</span>
          </li>
        </ol>
      </section>
    </template>
  </div>
</template>
