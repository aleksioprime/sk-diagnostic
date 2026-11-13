<script setup>
import { computed, onMounted, ref } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import { createAssignment, listAssignments, listClasses, listTests } from '@/api/diagnostic'
import { errorMessage, SkeletonTable, UiBadge, UiButton, UiInput, UiSelect, useUrlQuery } from 'sk-ui'
import { formatDate } from '@/utils/format'

const router = useRouter()
const assignments = ref([])
const tests = ref([])
const classes = ref([])
const loading = ref(true)
const error = ref('')
const form = ref(null)
const saving = ref(false)
const missing = ref(false)
const { route, setQuery } = useUrlQuery()
const filter = computed({
  get: () => route.query.status === 'closed' ? route.query.status : 'active',
  set: (value) => setQuery({ status: value === 'active' ? undefined : value }),
})

const shown = computed(() => assignments.value.filter((a) => (filter.value === 'active' ? a.is_active : !a.is_active)))

onMounted(async () => {
  try {
    ;[assignments.value, tests.value, classes.value] = await Promise.all([listAssignments(), listTests(), listClasses()])
  } catch (e) {
    error.value = errorMessage(e)
  } finally {
    loading.value = false
  }
})

function openForm() {
  form.value = { test_id: tests.value[0]?.id ?? null, class_id: classes.value[0]?.id ?? null, title: '' }
}

async function create() {
  // UiSelect - кнопка, браузер не проверяет её как обязательное поле
  missing.value = !form.value.test_id || !form.value.class_id
  error.value = missing.value ? 'Выберите методику и класс' : ''
  if (missing.value) return
  saving.value = true
  try {
    const assignment = await createAssignment(form.value)
    await router.push({ name: 'assignment', params: { id: assignment.id } })
  } catch (e) {
    error.value = errorMessage(e)
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <div>
    <div class="flex flex-wrap items-center justify-between gap-3">
      <h1 class="text-2xl font-bold">Диагностики</h1>
      <UiButton v-if="!form" variant="primary" :disabled="loading" @click="openForm">Выдать классу</UiButton>
    </div>

    <form v-if="form" class="mt-6 grid gap-4 rounded-card border border-brand-200 bg-surface p-5" @submit.prevent="create">
      <div class="grid gap-4 sm:grid-cols-2">
        <label class="grid gap-1.5 text-sm">
          <span class="font-medium">Методика</span>
          <UiSelect v-model="form.test_id" :invalid="missing && !form.test_id">
            <option v-for="test in tests" :key="test.id" :value="test.id">{{ test.title }}</option>
          </UiSelect>
        </label>
        <label class="grid gap-1.5 text-sm">
          <span class="font-medium">Класс</span>
          <UiSelect v-model="form.class_id" :invalid="missing && !form.class_id">
            <option v-for="c in classes" :key="c.id" :value="c.id">{{ c.name }} — учеников: {{ c.students_count }}</option>
          </UiSelect>
        </label>
      </div>
      <UiInput v-model="form.title" label="Название" hint="Пусто — «методика — класс»." />
      <p class="text-sm text-ink-muted">
        Каждый ученик класса получит диагностику в разделе «Мои диагностики» после входа через SkolStream.
        <template v-if="tests.find((t) => t.id === form.test_id)?.needs_birth_date">
          Для этой методики ученики укажут дату рождения, если её ещё нет.
        </template>
      </p>
      <div class="flex gap-2">
        <UiButton type="submit" variant="primary" :loading="saving">Выдать</UiButton>
        <UiButton variant="ghost" @click="form = null">Отмена</UiButton>
      </div>
    </form>

    <p v-if="error" role="alert" class="mt-4 rounded-control bg-red-100 px-3 py-2 text-sm text-red-800">{{ error }}</p>

    <div class="mt-6 flex gap-1 text-sm" role="tablist">
      <button
        v-for="(label, key) in { active: 'Идут', closed: 'Закрытые' }"
        :key="key"
        type="button"
        role="tab"
        :aria-selected="filter === key"
        class="rounded-control px-3 py-1.5"
        :class="filter === key ? 'bg-brand-100 font-medium text-brand-700' : 'text-ink-muted hover:bg-brand-50'"
        @click="filter = key"
      >
        {{ label }}
      </button>
    </div>

    <SkeletonTable v-if="loading" class="mt-4" :rows="4" />
    <p v-else-if="!shown.length" class="mt-10 text-center text-ink-muted">Здесь пока пусто.</p>
    <ul v-else class="mt-4 grid gap-3">
      <li v-for="a in shown" :key="a.id">
        <RouterLink
          :to="{ name: 'assignment', params: { id: a.id } }"
          class="flex flex-wrap items-center gap-x-6 gap-y-2 rounded-card border border-line bg-surface p-4 hover:border-brand-200"
        >
          <div class="min-w-0 flex-1">
            <p class="font-semibold">{{ a.title }}</p>
            <p class="mt-1 text-sm text-ink-muted">{{ a.test_title }} · {{ formatDate(a.created_at) }}</p>
          </div>
          <div class="flex flex-wrap gap-2">
            <UiBadge tone="success">Завершили {{ a.submitted }} из {{ a.total }}</UiBadge>
            <UiBadge v-if="a.in_progress" tone="warning">В процессе {{ a.in_progress }}</UiBadge>
          </div>
        </RouterLink>
      </li>
    </ul>
  </div>
</template>
