<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'
import * as api from '@/api/diagnostic'
import { errorMessage, UiBadge, UiButton, UiConfirm, UiInput } from 'sk-ui'
import { STATUS_TITLES, STATUS_TONES, formatDateTime } from '@/utils/format'

const props = defineProps({ id: { type: String, required: true } })

const assignment = ref(null)
const error = ref('')
const notice = ref('')
const busy = ref('')
const query = ref('')
const found = ref([])
const removal = ref(null) // попытка ученика, которую подтверждают

// Колонки сводки: первые показатели результата (уровень, ВК и т. п.)
const columns = computed(() => {
  const keys = []
  for (const attempt of assignment.value?.attempts || []) for (const key of Object.keys(attempt.summary)) if (!keys.includes(key)) keys.push(key)
  return keys.slice(0, 4)
})

onMounted(load)

async function load() {
  try {
    assignment.value = await api.getAssignment(props.id)
  } catch (e) {
    error.value = errorMessage(e)
  }
}

async function act(name, action, success) {
  busy.value = name
  error.value = ''
  notice.value = ''
  try {
    assignment.value = await action()
    notice.value = success
  } catch (e) {
    error.value = errorMessage(e)
  } finally {
    busy.value = ''
  }
}

const sync = () => act('sync', () => api.syncAssignment(props.id), 'Список учеников обновлён по классу')
const recalc = () => act('recalc', () => api.recalculateAssignment(props.id), 'Результаты пересчитаны')
const toggle = () =>
  act('toggle', () => api.updateAssignment(props.id, { is_active: !assignment.value.is_active }), assignment.value.is_active ? 'Выдача закрыта' : 'Выдача снова открыта')

async function addStudent(person) {
  query.value = ''
  found.value = []
  await act('add', () => api.addStudents(props.id, [person.person_id]), `${person.full_name} добавлен(а)`)
}

async function remove() {
  const attempt = removal.value
  await act(
    'remove',
    async () => {
      await api.deleteAttempt(attempt.id)
      return api.getAssignment(props.id)
    },
    'Ученик убран',
  )
  removal.value = null
}

let timer = null
watch(query, (value) => {
  clearTimeout(timer)
  if (value.trim().length < 2) {
    found.value = []
    return
  }
  timer = setTimeout(async () => {
    try {
      const inList = new Set(assignment.value.attempts.map((a) => a.student.person_id))
      found.value = (await api.searchStudents(value.trim())).filter((p) => !inList.has(p.person_id))
    } catch {
      found.value = []
    }
  }, 300)
})
</script>

<template>
  <div>
    <RouterLink :to="{ name: 'assignments' }" class="text-sm text-ink-muted hover:text-ink">← Диагностики</RouterLink>
    <p v-if="error" role="alert" class="mt-4 rounded-control bg-red-100 px-3 py-2 text-sm text-red-800">{{ error }}</p>
    <p v-if="notice" role="status" class="mt-4 rounded-control bg-brand-50 px-3 py-2 text-sm text-brand-700">{{ notice }}</p>

    <template v-if="assignment">
      <div class="mt-2 flex flex-wrap items-start gap-4">
        <!-- Базовая ширина: на узком экране кнопки переносятся под заголовок, а не сжимают его -->
        <div class="min-w-0 flex-1 basis-80">
          <p class="text-sm text-ink-muted">{{ assignment.test_title }}<template v-if="assignment.class_name"> · {{ assignment.class_name }}</template></p>
          <h1 class="text-2xl font-bold">{{ assignment.title }}</h1>
          <p class="mt-2 flex flex-wrap gap-2">
            <UiBadge :tone="assignment.is_active ? 'success' : 'neutral'">{{ assignment.is_active ? 'Идёт' : 'Закрыта' }}</UiBadge>
            <UiBadge>Завершили {{ assignment.submitted }} из {{ assignment.total }}</UiBadge>
            <UiBadge v-if="assignment.in_progress" tone="warning">В процессе {{ assignment.in_progress }}</UiBadge>
          </p>
        </div>
        <div class="flex flex-wrap gap-2">
          <a :href="api.exportUrl(props.id)" class="inline-flex h-10 items-center rounded-control bg-brand-600 px-4 font-medium text-white hover:bg-brand-700">Скачать Excel</a>
          <UiButton v-if="assignment.class_id" :loading="busy === 'sync'" @click="sync">Новые ученики класса</UiButton>
          <UiButton :loading="busy === 'recalc'" @click="recalc">Пересчитать</UiButton>
          <UiButton variant="ghost" :loading="busy === 'toggle'" @click="toggle">{{ assignment.is_active ? 'Закрыть' : 'Открыть снова' }}</UiButton>
        </div>
      </div>

      <div class="mt-6 overflow-x-auto rounded-card border border-line bg-surface">
        <table class="w-full text-sm" :class="{ 'min-w-[720px]': columns.length }">
          <thead class="bg-canvas text-left text-ink-muted">
            <tr>
              <th class="px-4 py-3 font-medium">Ученик</th>
              <th class="px-4 py-3 font-medium">Статус</th>
              <th v-for="column in columns" :key="column" class="px-4 py-3 font-medium">{{ column }}</th>
              <th class="px-4 py-3" />
            </tr>
          </thead>
          <tbody>
            <tr v-for="attempt in assignment.attempts" :key="attempt.id" class="border-t border-line align-top">
              <td class="px-4 py-3">
                <RouterLink v-if="attempt.status === 'submitted'" :to="{ name: 'attempt', params: { id: attempt.id } }" class="font-medium text-brand-700 hover:underline">
                  {{ attempt.student.full_name }}
                </RouterLink>
                <span v-else>{{ attempt.student.full_name }}</span>
                <span v-if="!attempt.student.birth_date && assignment.needs_birth_date" class="block text-xs text-amber-700">нет даты рождения</span>
              </td>
              <td class="px-4 py-3">
                <UiBadge :tone="attempt.result_status === 'error' ? 'danger' : STATUS_TONES[attempt.status]">
                  {{ attempt.result_status === 'error' ? 'Ошибка расчёта' : STATUS_TITLES[attempt.status] }}
                </UiBadge>
                <span v-if="attempt.submitted_at" class="mt-1 block text-xs text-ink-muted">{{ formatDateTime(attempt.submitted_at) }}</span>
              </td>
              <td v-for="column in columns" :key="column" class="max-w-56 px-4 py-3">{{ attempt.summary[column] ?? '' }}</td>
              <td class="px-4 py-3 text-right">
                <button v-if="attempt.status === 'assigned'" type="button" class="text-xs text-ink-muted hover:text-red-600" @click="removal = attempt">Убрать</button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <div class="relative mt-6 max-w-md">
        <UiInput v-model="query" label="Добавить ученика из другого класса" type="search" placeholder="Фамилия ученика" />
        <ul v-if="found.length" class="absolute inset-x-0 z-10 mt-1 max-h-64 overflow-auto rounded-control border border-line bg-surface shadow-lg">
          <li v-for="person in found" :key="person.person_id">
            <button type="button" class="w-full px-3 py-2 text-left hover:bg-brand-50" @click="addStudent(person)">
              {{ person.full_name }} <span class="text-xs text-ink-muted">{{ person.class_name }}</span>
            </button>
          </li>
        </ul>
      </div>

      <UiConfirm
        :open="!!removal"
        title="Убрать ученика из выдачи?"
        confirm-label="Убрать"
        variant="danger"
        :loading="busy === 'remove'"
        @update:open="removal = null"
        @confirm="remove"
      >
        {{ removal?.student.full_name }}
      </UiConfirm>
    </template>
  </div>
</template>
