<script setup>
import { computed, ref } from 'vue'
import { useAuthStore } from '../stores/auth'
import { update } from '../utils/nocobase'
import { formatGenderValue } from '../utils/format'

const auth = useAuthStore()

const saving = ref(false)
const success = ref('')
const error = ref('')
const birthDate = ref(auth.person?.birth_date ? String(auth.person.birth_date).slice(0, 10) : '')
const initialBirthDate = ref(auth.person?.birth_date ? String(auth.person.birth_date).slice(0, 10) : '')

const person = computed(() => auth.person || null)
const hasUnsavedChanges = computed(() => birthDate.value !== initialBirthDate.value)
const readonlyFields = computed(() => ({
  gender: formatGenderValue(person.value?.gender_label || person.value?.gender_value || person.value?.gender),
  firstName: person.value?.first_name || '—',
  middleName: person.value?.middle_name || '—',
  lastName: person.value?.last_name || '—',
  email: person.value?.email || auth.user?.email || '—',
}))

async function saveProfile() {
  success.value = ''
  error.value = ''

  if (!person.value?.id) {
    error.value = 'Профиль пользователя не найден.'
    return
  }

  saving.value = true
  try {
    await update('persons', person.value.id, {
      birth_date: birthDate.value || null,
    })
    await auth.fetchPerson()
    const freshBirthDate = auth.person?.birth_date ? String(auth.person.birth_date).slice(0, 10) : ''
    birthDate.value = freshBirthDate
    initialBirthDate.value = freshBirthDate
    success.value = 'Дата рождения обновлена.'
  } catch (saveError) {
    error.value = saveError.response?.data?.errors?.[0]?.message || 'Не удалось сохранить дату рождения.'
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <section class="w-full">
    <div class="mb-6">
      <p class="mb-2 text-sm font-semibold uppercase tracking-[0.24em] text-slate-400">Мой кабинет</p>
      <h1 class="section-title">Профиль</h1>
      <p class="mt-2 max-w-3xl text-sm leading-6 text-slate-500">Сейчас доступно редактирование только даты рождения. Остальные поля пока доступны в режиме просмотра.</p>
    </div>

    <div v-if="!person" class="glass-panel p-8 text-center text-sm text-red-700">
      Не удалось загрузить данные профиля.
    </div>

    <form v-else class="glass-panel max-w-3xl space-y-6 p-6 sm:p-7" @submit.prevent="saveProfile">
      <div class="grid gap-4 sm:grid-cols-2">
        <label class="block sm:col-span-2">
          <span class="mb-2 block text-sm font-medium text-slate-700">Дата рождения</span>
          <input v-model="birthDate" type="date" class="field-input" />
          <span v-if="hasUnsavedChanges" class="mt-2 block text-xs font-medium text-amber-700">Есть несохранённые изменения</span>
        </label>

        <label class="block">
          <span class="mb-2 block text-sm font-medium text-slate-700">Пол</span>
          <input :value="readonlyFields.gender" type="text" class="field-input bg-slate-100/70" readonly disabled />
        </label>

        <label class="block">
          <span class="mb-2 block text-sm font-medium text-slate-700">Email</span>
          <input :value="readonlyFields.email" type="text" class="field-input bg-slate-100/70" readonly disabled />
        </label>

        <label class="block">
          <span class="mb-2 block text-sm font-medium text-slate-700">Имя</span>
          <input :value="readonlyFields.firstName" type="text" class="field-input bg-slate-100/70" readonly disabled />
        </label>

        <label class="block">
          <span class="mb-2 block text-sm font-medium text-slate-700">Отчество</span>
          <input :value="readonlyFields.middleName" type="text" class="field-input bg-slate-100/70" readonly disabled />
        </label>

        <label class="block sm:col-span-2">
          <span class="mb-2 block text-sm font-medium text-slate-700">Фамилия</span>
          <input :value="readonlyFields.lastName" type="text" class="field-input bg-slate-100/70" readonly disabled />
        </label>
      </div>

      <p v-if="error" class="rounded-2xl bg-red-50 px-4 py-3 text-sm text-red-700">{{ error }}</p>
      <p v-if="success" class="rounded-2xl bg-emerald-50 px-4 py-3 text-sm text-emerald-700">{{ success }}</p>

      <div class="flex justify-end">
        <button type="submit" class="primary-button" :disabled="saving || !hasUnsavedChanges">
          {{ saving ? 'Сохранение…' : 'Сохранить' }}
        </button>
      </div>
    </form>
  </section>
</template>
