<script setup>
/**
 * Данные человека не из SkolStream. Отдельная карточка, а не диалог: списки UiSelect открываются поверх страницы
 * и оказались бы под модальным окном.
 */
import { onMounted, ref } from 'vue'
import { getPerson, listClasses, updatePerson } from '@/api/diagnostic'
import { errorMessage, SkeletonList, UiButton, UiCard, UiInput, UiSelect } from 'sk-ui'
import { detailedError } from '@/utils/apiErrors'

const props = defineProps({ personId: { type: [Number, String], required: true } })
const emit = defineEmits(['saved', 'cancel'])

const FIELDS = ['last_name', 'first_name', 'middle_name', 'email', 'gender', 'birth_date', 'class_id', 'is_student', 'is_employee']

const form = ref(null)
const original = ref(null)
const classes = ref([])
const password = ref('')
const error = ref('')
const saving = ref(false)
const root = ref(null)

onMounted(async () => {
  try {
    const [person, list] = await Promise.all([getPerson(props.personId), listClasses()])
    original.value = person
    form.value = { ...person, email: person.email ?? '', birth_date: person.birth_date ?? '' }
    classes.value = list
    root.value?.$el?.scrollIntoView?.({ block: 'nearest' })
  } catch (e) {
    error.value = errorMessage(e)
  }
})

// Пустые поля даты и почты уходят как null: иначе сервер не примет пустую строку
const normalized = (name) => (['email', 'birth_date'].includes(name) && form.value[name] === '' ? null : form.value[name])

async function save() {
  error.value = ''
  if (password.value && password.value.length < 8) {
    error.value = 'Пароль должен быть не короче 8 символов'
    return
  }
  const body = {}
  for (const name of FIELDS) {
    if (normalized(name) !== original.value[name]) body[name] = normalized(name)
  }
  if (password.value) body.password = password.value
  saving.value = true
  try {
    emit('saved', await updatePerson(props.personId, body))
  } catch (e) {
    error.value = detailedError(e)
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <UiCard ref="root">
    <template #title>Данные человека не из SkolStream</template>
    <p v-if="error" role="alert" class="mb-3 whitespace-pre-line rounded-control bg-red-100 px-3 py-2 text-sm text-red-800">{{ error }}</p>
    <SkeletonList v-if="!form && !error" />
    <form v-if="form" class="grid gap-3 text-sm sm:grid-cols-2 lg:grid-cols-3" novalidate @submit.prevent="save">
      <UiInput v-model="form.last_name" label="Фамилия" />
      <UiInput v-model="form.first_name" label="Имя" />
      <UiInput v-model="form.middle_name" label="Отчество" />
      <UiInput v-model="form.email" label="Email" type="email" autocomplete="off" />
      <UiInput v-model="form.birth_date" label="Дата рождения" type="date" />
      <div class="grid content-start gap-1.5">
        <span class="font-medium">Пол</span>
        <UiSelect v-model="form.gender" aria-label="Пол" class="w-full">
          <option :value="null">Не указан</option>
          <option value="female">Женский</option>
          <option value="male">Мужской</option>
        </UiSelect>
      </div>
      <div class="grid content-start gap-1.5">
        <span class="font-medium">Класс</span>
        <UiSelect v-model="form.class_id" aria-label="Класс" class="w-full">
          <option :value="null">Без класса</option>
          <option v-for="item in classes" :key="item.id" :value="item.id">{{ item.name }}</option>
        </UiSelect>
      </div>
      <UiInput
        v-model="password"
        label="Новый пароль"
        type="text"
        autocomplete="off"
        :hint="original.has_password ? 'Пусто — пароль не меняется.' : 'Пароль не задан: без него вход невозможен.'"
      />
      <div class="flex flex-wrap items-center gap-4">
        <label class="flex items-center gap-2"><input v-model="form.is_student" type="checkbox" class="size-4 accent-brand-600" /> Ученик</label>
        <label class="flex items-center gap-2"><input v-model="form.is_employee" type="checkbox" class="size-4 accent-brand-600" /> Сотрудник</label>
      </div>
      <div class="flex flex-wrap gap-2 sm:col-span-2 lg:col-span-3">
        <UiButton type="submit" variant="primary" :loading="saving">Сохранить</UiButton>
        <UiButton @click="emit('cancel')">Отмена</UiButton>
      </div>
    </form>
  </UiCard>
</template>
