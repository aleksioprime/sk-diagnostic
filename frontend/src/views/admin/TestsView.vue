<script setup>
import { computed, onMounted, ref } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import { copyTest, createTest, deleteAdminTest, exportTest, importTest, listAdminTests, patchAdminTest } from '@/api/diagnostic'
import { errorMessage, SkeletonList, UiBadge, UiButton, UiCard, UiConfirm, UiInput } from 'sk-ui'
import { detailedError } from '@/utils/apiErrors'
import { saveJsonFile } from '@/utils/download'

const SCORING = {
  script: { label: 'Скрипт', tone: 'brand' },
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

// Новая методика: пустая или копия существующей (copyFrom)
const draft = ref(null)
const creating = ref(false)
const createError = ref('')
const draftOpen = computed({
  get: () => draft.value !== null,
  set: (value) => {
    if (!value) draft.value = null
  },
})

function startNew(source = null) {
  createError.value = ''
  draft.value = source
    ? { copyFrom: source, title: `${source.title} (копия)` }
    : { copyFrom: null, title: '' }
}

async function create() {
  const { copyFrom, title } = draft.value
  if (!title.trim()) {
    createError.value = 'Заполните название'
    return
  }
  creating.value = true
  createError.value = ''
  try {
    const body = { title: title.trim() }
    const test = copyFrom ? await copyTest(copyFrom.id, body) : await createTest(body)
    router.push({ name: 'admin-test-questions', params: { id: test.id } })
  } catch (e) {
    createError.value = detailedError(e)
  } finally {
    creating.value = false
  }
}

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
  // Включение идёт через проверку готовности
  if (!test.is_active) {
    router.push({ name: 'admin-test-check', params: { id: test.id } })
    return
  }
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
    <div class="flex flex-wrap items-center justify-between gap-3">
      <div>
        <h1 class="text-2xl font-bold">Методики</h1>
        <p class="mt-1 text-ink-muted">Вопросы, ответы и расчёт результатов.</p>
      </div>
      <UiButton variant="primary" @click="startNew()">Новая методика</UiButton>
    </div>
    <p v-if="error" role="alert" class="mt-4 rounded-control bg-red-100 px-3 py-2 text-sm text-red-800">{{ error }}</p>
    <p v-if="notice" role="status" class="mt-4 rounded-control bg-brand-50 px-3 py-2 text-sm text-brand-700">{{ notice }}</p>

    <SkeletonList v-if="loading" class="mt-6" />
    <ul v-else class="mt-6 grid gap-3">
      <li v-for="test in tests" :key="test.id">
        <UiCard class="flex flex-wrap items-center gap-x-4 gap-y-2">
          <div class="min-w-0 flex-1 basis-64">
            <RouterLink :to="{ name: 'admin-test-questions', params: { id: test.id } }" class="font-semibold text-brand-700 hover:underline">
              {{ test.title }}
            </RouterLink>
            <p class="mt-1 text-sm text-ink-muted">
              Вопросов: {{ test.questions_count }} · выдач: {{ test.assignments_count }}
            </p>
          </div>
          <UiBadge :tone="SCORING[test.scoring].tone">{{ SCORING[test.scoring].label }}</UiBadge>
          <UiBadge v-if="!test.is_active" tone="danger">Отключена</UiBadge>
          <div class="flex flex-wrap gap-2">
            <UiButton size="sm" @click="startNew(test)">Копировать</UiButton>
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
      <UiCard class="mt-3 grid grid-cols-[minmax(0,1fr)] gap-3">
        <label for="test-source" class="text-sm font-medium">Содержимое файла</label>
        <textarea
          id="test-source"
          v-model="source"
          rows="10"
          spellcheck="false"
          class="w-full rounded-control border border-line bg-surface p-3 font-mono text-xs"
          placeholder="Вставьте JSON или выберите файл"
        ></textarea>
        <input type="file" accept="application/json,.json" aria-label="Файл JSON" class="w-full min-w-0 text-sm" @change="pickFile" />
        <label class="flex items-center gap-2 text-sm">
          <input v-model="replace" type="checkbox" class="size-4 accent-brand-600" />
          Заменить методику с таким же кодом, если её ещё не выдавали
        </label>
        <p v-if="importError" role="alert" class="whitespace-pre-line rounded-control bg-red-100 px-3 py-2 text-sm text-red-800">{{ importError }}</p>
        <div class="flex flex-wrap gap-2">
          <UiButton variant="primary" :loading="importing" :disabled="!source.trim()" @click="runImport">Загрузить</UiButton>
          <UiButton @click="source = EXAMPLE">Вставить пример</UiButton>
        </div>
        <p class="text-sm text-ink-muted">
          Типы вопросов: <code>scale</code>, <code>single_choice</code>, <code>ranking</code>, <code>text</code>, <code>number</code>,
          <code>yes_no</code>. Номера вопросов (<code>order</code>) проставятся по порядку, если их не указать. Скрипт можно не задавать сразу: он пишется на странице методики. Загруженная методика отключена, пока не пройдёт проверку готовности.
        </p>
      </UiCard>
    </section>

    <UiConfirm
      v-model:open="draftOpen"
      :title="draft?.copyFrom ? 'Копия методики' : 'Новая методика'"
      :confirm-label="draft?.copyFrom ? 'Создать копию' : 'Создать'"
      :loading="creating"
      @confirm="create"
    >
      <div v-if="draft" class="grid gap-3">
        <p v-if="draft.copyFrom" class="text-sm text-ink-muted">
          Копируются вопросы, ответы, шкалы и скрипт расчёта. Правки копии не затронут исходную методику. Копия будет отключена, пока вы её не включите.
        </p>
        <UiInput v-model="draft.title" label="Название" />
        <p v-if="createError" role="alert" class="whitespace-pre-line rounded-control bg-red-100 px-3 py-2 text-sm text-red-800">{{ createError }}</p>
      </div>
    </UiConfirm>

    <UiConfirm v-model:open="confirmOpen" title="Удалить методику?" confirm-label="Удалить" variant="danger" :loading="deleting" @confirm="remove">
      «{{ toDelete?.title }}» и её вопросы будут удалены. Классам она ещё не выдавалась.
    </UiConfirm>
  </div>
</template>
