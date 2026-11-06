<script setup>
import { computed, onMounted, ref } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import { deleteAdminTest, exportTest, importTest, listAdminTests, patchAdminTest } from '@/api/diagnostic'
import { errorMessage, SkeletonList, UiBadge, UiButton, UiCard, UiConfirm } from 'sk-ui'
import { detailedError } from '@/utils/apiErrors'
import { saveJsonFile } from '@/utils/download'

const SCORING = {
  script: { label: 'Скрипт', tone: 'brand' },
  builtin: { label: 'Встроенный расчёт', tone: 'neutral' },
  none: { label: 'Нет расчёта', tone: 'warning' },
}

const EXAMPLE = `{
  "code": "my_survey",
  "title": "Название методики",
  "description": "Описание для психолога",
  "needs_birth_date": false,
  "scoring_script": null,
  "scales": [
    {
      "code": "agree_1_3",
      "title": "Согласие",
      "options": [
        { "label": "Нет", "value": "1", "score": 1 },
        { "label": "Отчасти", "value": "2", "score": 2 },
        { "label": "Да", "value": "3", "score": 3 }
      ]
    }
  ],
  "questions": [
    { "text": "Мне нравится учиться", "question_type": "scale", "scale": "agree_1_3" },
    {
      "text": "Любимый предмет",
      "question_type": "single_choice",
      "options": [
        { "label": "Математика", "value": "math", "score": 1 },
        { "label": "Литература", "value": "lit", "score": 2 }
      ]
    },
    { "text": "Что хочется изменить?", "question_type": "text", "is_required": false }
  ]
}`

const router = useRouter()
const tests = ref([])
const loading = ref(true)
const error = ref('')
const notice = ref('')

const source = ref('')
const replace = ref(false)
const importing = ref(false)
const importError = ref('')

const toDelete = ref(null)
const deleting = ref(false)
const confirmOpen = computed({
  get: () => toDelete.value !== null,
  set: (value) => {
    if (!value) toDelete.value = null
  },
})

async function load() {
  try {
    tests.value = await listAdminTests()
  } catch (e) {
    error.value = errorMessage(e)
  } finally {
    loading.value = false
  }
}
onMounted(load)

async function pickFile(event) {
  const file = event.target.files?.[0]
  if (file) source.value = await file.text()
  event.target.value = ''
}

async function runImport() {
  importError.value = ''
  let parsed
  try {
    parsed = JSON.parse(source.value)
  } catch (e) {
    importError.value = `Это не JSON: ${e.message}`
    return
  }
  importing.value = true
  try {
    const test = await importTest(parsed, replace.value)
    router.push({ name: 'admin-test', params: { id: test.id } })
  } catch (e) {
    importError.value = detailedError(e)
  } finally {
    importing.value = false
  }
}

async function download(test) {
  error.value = ''
  try {
    saveJsonFile(`${test.code}.json`, await exportTest(test.id))
  } catch (e) {
    error.value = errorMessage(e)
  }
}

async function toggle(test) {
  error.value = ''
  try {
    const updated = await patchAdminTest(test.id, { is_active: !test.is_active })
    test.is_active = updated.is_active
  } catch (e) {
    error.value = errorMessage(e)
  }
}

async function remove() {
  deleting.value = true
  error.value = ''
  try {
    await deleteAdminTest(toDelete.value.id)
    notice.value = `Методика «${toDelete.value.title}» удалена`
    tests.value = tests.value.filter((t) => t.id !== toDelete.value.id)
  } catch (e) {
    error.value = errorMessage(e)
  } finally {
    deleting.value = false
    toDelete.value = null
  }
}
</script>

<template>
  <div>
    <h1 class="text-2xl font-bold">Методики</h1>
    <p class="mt-1 text-ink-muted">Загрузка методик из JSON и настройка расчёта результатов.</p>
    <p v-if="error" role="alert" class="mt-4 rounded-control bg-red-100 px-3 py-2 text-sm text-red-800">{{ error }}</p>
    <p v-if="notice" role="status" class="mt-4 rounded-control bg-brand-50 px-3 py-2 text-sm text-brand-700">{{ notice }}</p>

    <SkeletonList v-if="loading" class="mt-6" />
    <ul v-else class="mt-6 grid gap-3">
      <li v-for="test in tests" :key="test.id">
        <UiCard class="flex flex-wrap items-center gap-x-4 gap-y-2">
          <div class="min-w-64 flex-1">
            <RouterLink :to="{ name: 'admin-test', params: { id: test.id } }" class="font-semibold text-brand-700 hover:underline">
              {{ test.title }}
            </RouterLink>
            <p class="mt-1 text-sm text-ink-muted">
              <code>{{ test.code }}</code> · вопросов: {{ test.questions_count }} · выдач: {{ test.assignments_count }}
            </p>
          </div>
          <UiBadge :tone="SCORING[test.scoring].tone">{{ SCORING[test.scoring].label }}</UiBadge>
          <UiBadge v-if="!test.is_active" tone="danger">Отключена</UiBadge>
          <div class="flex flex-wrap gap-2">
            <UiButton size="sm" @click="download(test)">Скачать JSON</UiButton>
            <UiButton size="sm" @click="toggle(test)">{{ test.is_active ? 'Отключить' : 'Включить' }}</UiButton>
            <UiButton v-if="!test.assignments_count" size="sm" variant="ghost" @click="toDelete = test">Удалить</UiButton>
          </div>
        </UiCard>
      </li>
      <li v-if="!tests.length" class="text-ink-muted">Методик пока нет.</li>
    </ul>

    <section class="mt-8">
      <h2 class="text-lg font-semibold">Загрузить методику из JSON</h2>
      <UiCard class="mt-3 grid gap-3">
        <label for="test-source" class="text-sm font-medium">Содержимое файла</label>
        <textarea
          id="test-source"
          v-model="source"
          rows="10"
          spellcheck="false"
          class="w-full rounded-control border border-line bg-surface p-3 font-mono text-xs"
          placeholder="Вставьте JSON или выберите файл"
        ></textarea>
        <input type="file" accept="application/json,.json" aria-label="Файл JSON" class="text-sm" @change="pickFile" />
        <label class="flex items-center gap-2 text-sm">
          <input v-model="replace" type="checkbox" />
          Заменить методику с таким же кодом, если её ещё не выдавали
        </label>
        <p v-if="importError" role="alert" class="whitespace-pre-line rounded-control bg-red-100 px-3 py-2 text-sm text-red-800">{{ importError }}</p>
        <div class="flex flex-wrap gap-2">
          <UiButton variant="primary" :loading="importing" :disabled="!source.trim()" @click="runImport">Загрузить</UiButton>
          <UiButton @click="source = EXAMPLE">Вставить пример</UiButton>
        </div>
        <p class="text-sm text-ink-muted">
          Типы вопросов: <code>scale</code>, <code>single_choice</code>, <code>ranking</code>, <code>text</code>, <code>number</code>,
          <code>yes_no</code>. Номера вопросов (<code>order</code>) проставятся по порядку, если их не указать. Скрипт можно не задавать сразу: он пишется на странице методики.
        </p>
      </UiCard>
    </section>

    <UiConfirm v-model:open="confirmOpen" title="Удалить методику?" confirm-label="Удалить" variant="danger" :loading="deleting" @confirm="remove">
      «{{ toDelete?.title }}» и её вопросы будут удалены. Классам она ещё не выдавалась.
    </UiConfirm>
  </div>
</template>
