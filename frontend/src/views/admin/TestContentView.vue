<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref, shallowRef, watch } from 'vue'
import { onBeforeRouteLeave } from 'vue-router'
import { getTestContent, saveTestContent } from '@/api/diagnostic'
import { errorMessage, SkeletonPage, UiButton, UiCard, UiFormActions, UiInput, UiSelect, UiBreadcrumbs, useUrlQuery } from 'sk-ui'
import OptionsEditor from '@/components/tests/OptionsEditor.vue'
import ScaleCard from '@/components/tests/ScaleCard.vue'
import TestTabs from '@/components/tests/TestTabs.vue'
import { detailedError } from '@/utils/apiErrors'
import {
  answerSummary,
  contentBody,
  contentProblem,
  copyQuestion,
  hasOptions,
  newKey,
  newQuestion,
  QUESTION_TYPES,
  questionProblem,
  starterOptions,
  swap,
  withKeys,
} from '@/utils/testDraft'

const { route, setQuery } = useUrlQuery()
const content = ref(null)
const savedContent = shallowRef(null)
const scales = ref([])
const dirtyScales = reactive(new Set())
const loadError = ref('')
const error = ref('')
const notice = ref('')
const saving = ref(false)
// Раскрыт один вопрос: в длинной методике остальные остаются одной строкой
const draftOpenKey = ref(null)
const openKey = computed(() => draftOpenKey.value ?? content.value?.questions.find(
  (question) => question.id != null && String(question.id) === route.query.question,
)?.key ?? null)
watch(() => route.query.question, () => { draftOpenKey.value = null })
const invalidKey = ref(null)
const dragFrom = ref(null)
const dragOver = ref(null)

const locked = computed(() => content.value?.mode === 'text')
const body = computed(() => content.value && contentBody(content.value))
const savedBody = computed(() => savedContent.value && contentBody(savedContent.value))
const dirty = computed(() => JSON.stringify(body.value) !== JSON.stringify(savedBody.value))
const savedQuestions = computed(() => new Map(savedContent.value?.questions.map(({ key }, index) => [
  key, { index, body: JSON.stringify(savedBody.value.questions[index]) },
])))
const changedQuestions = computed(() => new Set(content.value?.questions.filter(({ key }, index) => {
  const saved = savedQuestions.value.get(key)
  return !saved || saved.index !== index || saved.body !== JSON.stringify(body.value.questions[index])
}).map(({ key }) => key)))
const fieldChanged = (key) => body.value[key] !== savedBody.value[key]
const anythingDirty = computed(() => dirty.value || dirtyScales.size > 0)
// В вопросе можно выбрать только сохранённую шкалу
const savedScales = computed(() => scales.value.filter((scale) => scale.id !== null))

function apply(answer) {
  savedContent.value = { ...answer, questions: answer.questions.map(withKeys) }
  content.value = structuredClone(savedContent.value)
}

onMounted(async () => {
  try {
    const answer = await getTestContent(route.params.id)
    apply(answer)
    scales.value = answer.scales.map((scale) => ({ ...scale, key: scale.id }))
  } catch (e) {
    loadError.value = errorMessage(e)
  }
})

function openQuestion(question, options) {
  draftOpenKey.value = question?.id == null ? question?.key ?? null : null
  if (draftOpenKey.value == null) {
    return setQuery({ question: question ? String(question.id) : undefined }, options)
  }
}

function removeQuestion(index) {
  const [question] = content.value.questions.splice(index, 1)
  if (question.key === draftOpenKey.value || (question.id != null && String(question.id) === route.query.question)) {
    openQuestion(null, { replace: true })
  }
}

function addQuestion() {
  const question = newQuestion()
  content.value.questions.push(question)
  openQuestion(question)
}

function toggleQuestion(question) {
  openQuestion(openKey.value === question.key ? null : question)
}

function duplicateQuestion(index) {
  const copy = copyQuestion(content.value.questions[index])
  content.value.questions.splice(index + 1, 0, copy)
  openQuestion(copy)
}

function startDrag(index, event) {
  dragFrom.value = index
  event.dataTransfer.effectAllowed = 'move'
  event.dataTransfer.setData('text/plain', String(index))
}

function dropOn(index) {
  if (dragFrom.value !== null && dragFrom.value !== index) {
    const [moved] = content.value.questions.splice(dragFrom.value, 1)
    content.value.questions.splice(index, 0, moved)
  }
  dragFrom.value = dragOver.value = null
}

function showProblem(number) {
  const question = content.value.questions[number - 1]
  if (question) {
    invalidKey.value = question.key
    openQuestion(question, { replace: true })
  }
}

function changeType(question, type) {
  question.question_type = type
  if (hasOptions(type) && !question.options.length) question.options = starterOptions()
}

function cancelChanges() {
  content.value = structuredClone(savedContent.value)
  draftOpenKey.value = null
  invalidKey.value = null
  error.value = ''
  notice.value = ''
}

async function save() {
  if (!dirty.value || saving.value) return
  error.value = contentProblem(content.value)
  notice.value = ''
  invalidKey.value = null
  if (error.value) {
    showProblem(content.value.questions.findIndex((q) => questionProblem(q)) + 1)
    return
  }
  saving.value = true
  try {
    const answer = await saveTestContent(route.params.id, body.value)
    const index = draftOpenKey.value == null ? -1 : content.value.questions.findIndex((q) => q.key === draftOpenKey.value)
    apply(answer)
    if (index >= 0) await openQuestion(content.value.questions[index], { replace: true })
    notice.value = 'Сохранено.'
  } catch (e) {
    error.value = detailedError(e)
    const place = /Вопрос (\d+)/.exec(error.value)
    if (place) showProblem(Number(place[1]))
  } finally {
    saving.value = false
  }
}

function addScale() {
  scales.value.push({
    id: null,
    key: newKey(),
    mode: 'full',
    title: '',
    description: '',
    options: [1, 2, 3].map((n) => ({ id: null, label: '', description: '', value: String(n), score: n })),
  })
}

function scaleSaved(index, answer) {
  scales.value[index] = { ...answer, key: scales.value[index].key }
}

function setScaleDirty(key, value) {
  if (value) dirtyScales.add(key)
  else dirtyScales.delete(key)
}

function removeNewScale(index) {
  dirtyScales.delete(scales.value[index].key)
  scales.value.splice(index, 1)
}

function warnOnClose(event) {
  if (anythingDirty.value) event.preventDefault()
}
window.addEventListener('beforeunload', warnOnClose)
onBeforeUnmount(() => window.removeEventListener('beforeunload', warnOnClose))
onBeforeRouteLeave(() => !saving.value && (!anythingDirty.value || window.confirm('Есть несохранённые изменения. Уйти со страницы?')))
</script>

<template>
  <p v-if="loadError" role="alert" class="rounded-control bg-red-100 px-3 py-2 text-sm text-red-800">{{ loadError }}</p>
  <SkeletonPage v-else-if="!content" />
  <div v-else class="max-w-4xl">
    <UiBreadcrumbs
      :items="[
        { label: 'Методики', to: { name: 'admin-tests' } },
        { label: content.title, to: { name: 'admin-test', params: { id: route.params.id } } },
        { label: 'Вопросы' },
      ]"
    />
    <h1 class="mt-2 text-2xl font-bold">{{ content.title }}</h1>
    <TestTabs :id="route.params.id" class="mt-4" />

    <p v-if="content.lock_reason" class="mt-4 rounded-control bg-amber-50 px-3 py-2 text-sm text-amber-900">
      {{ content.lock_reason }} Чтобы изменить что-то ещё, сделайте копию методики на странице «Методики».
    </p>

    <form @submit.prevent="save">
      <fieldset :disabled="saving" class="min-w-0">
        <UiCard class="mt-4 grid gap-3">
          <UiInput v-model="content.title" label="Название" :class="{ 'ui-changed': fieldChanged('title') }" />
          <label class="grid gap-1 text-sm font-medium" :class="{ 'ui-changed': fieldChanged('description') }">
            Описание
            <textarea v-model="content.description" rows="3" class="rounded-control border border-line bg-surface p-3 font-normal"></textarea>
          </label>
        </UiCard>

        <section class="mt-6">
          <h2 class="text-lg font-semibold">Вопросы ({{ content.questions.length }})</h2>
          <ol aria-label="Вопросы методики" class="mt-3 grid grid-cols-[minmax(0,1fr)] gap-2">
            <li
              v-for="(question, index) in content.questions"
              :key="question.key"
              class="rounded-card border bg-surface"
              :class="[invalidKey === question.key ? 'border-red-500' : 'border-line', { 'border-brand-500': dragOver === index && dragFrom !== index }]"
              @dragover.prevent="dragFrom !== null && (dragOver = index)"
              @drop.prevent="dropOn(index)"
            >
              <div class="flex items-center gap-1 pr-2" :class="{ 'ui-changed': changedQuestions.has(question.key) }">
                <span
                  v-if="!locked"
                  class="cursor-grab select-none py-3 pl-2 text-ink-muted"
                  draggable="true"
                  title="Перетащить"
                  aria-hidden="true"
                  @dragstart="startDrag(index, $event)"
                  @dragend="dragFrom = dragOver = null"
                >⠿</span>
                <button
                  type="button"
                  class="flex min-w-0 flex-1 items-baseline gap-2 py-3 pl-2 text-left"
                  :aria-expanded="openKey === question.key"
                  @click="toggleQuestion(question)"
                >
                  <span class="text-sm text-ink-muted">{{ index + 1 }}</span>
                  <span class="min-w-0 flex-1 truncate font-medium" :class="{ 'text-ink-muted': !question.text }">{{ question.text || 'Без текста' }}</span>
                  <span class="hidden shrink-0 text-sm text-ink-muted sm:inline">{{ answerSummary(question, savedScales) }}</span>
                  <span class="shrink-0 text-xs text-ink-muted" aria-hidden="true">{{ openKey === question.key ? '▲' : '▼' }}</span>
                </button>
              </div>

              <div v-if="openKey === question.key" class="grid gap-3 border-t border-line p-4">
                <label class="grid gap-1 text-sm font-medium">
                  Текст вопроса
                  <textarea v-model="question.text" rows="2" class="rounded-control border border-line bg-surface p-3 font-normal"></textarea>
                </label>
                <div class="grid gap-3 sm:grid-cols-2">
                  <div class="grid gap-1.5">
                    <span class="text-sm font-medium">Тип ответа</span>
                    <UiSelect :model-value="question.question_type" :disabled="locked" aria-label="Тип ответа" class="w-full" @update:model-value="changeType(question, $event)">
                      <option v-for="type in QUESTION_TYPES" :key="type.value" :value="type.value">{{ type.label }}</option>
                      <option v-if="!QUESTION_TYPES.some((t) => t.value === question.question_type)" :value="question.question_type">{{ question.question_type }}</option>
                    </UiSelect>
                  </div>
                  <div v-if="question.question_type === 'scale'" class="grid gap-1.5">
                    <span class="text-sm font-medium">Шкала</span>
                    <UiSelect v-model="question.scale_id" :disabled="locked" aria-label="Шкала" class="w-full">
                      <option :value="null" disabled>Выберите шкалу</option>
                      <option v-for="scale in savedScales" :key="scale.id" :value="scale.id">{{ scale.title }}</option>
                    </UiSelect>
                  </div>
                </div>
                <OptionsEditor v-if="hasOptions(question.question_type)" v-model="question.options" :fixed="locked" />
                <div class="flex flex-wrap items-center gap-x-5 gap-y-2 text-sm">
                  <label class="flex items-center gap-2"><input v-model="question.is_required" type="checkbox" :disabled="locked" class="size-4 accent-brand-600" /> Обязательный</label>
                  <label v-if="hasOptions(question.question_type)" class="flex items-center gap-2">
                    <input v-model="question.is_random" type="checkbox" :disabled="locked" class="size-4 accent-brand-600" /> Варианты в случайном порядке
                  </label>
                </div>
                <details class="text-sm" :open="!!question.description">
                  <summary class="cursor-pointer text-ink-muted">Дополнительно</summary>
                  <div class="mt-3 grid gap-3 sm:grid-cols-2">
                    <UiInput v-model="question.description" label="Пояснение для ученика" />
                    <UiInput
                      v-model="question.code"
                      label="Код для скрипта"
                      hint="Необязательно. Не меняется при перестановке вопросов, в отличие от номера."
                      :disabled="locked"
                      class="[&_input:disabled]:bg-canvas [&_input:disabled]:text-ink-muted"
                    />
                  </div>
                </details>
                <div v-if="!locked" class="flex flex-wrap gap-1 border-t border-line pt-3">
                  <UiButton size="sm" variant="ghost" :disabled="index === 0" :aria-label="`Вопрос ${index + 1} выше`" @click="swap(content.questions, index, index - 1)">↑</UiButton>
                  <UiButton size="sm" variant="ghost" :disabled="index === content.questions.length - 1" :aria-label="`Вопрос ${index + 1} ниже`" @click="swap(content.questions, index, index + 1)">↓</UiButton>
                  <UiButton size="sm" @click="duplicateQuestion(index)">Дублировать</UiButton>
                  <UiButton size="sm" variant="danger-outline" class="ml-auto" @click="removeQuestion(index)">Удалить</UiButton>
                </div>
              </div>
            </li>
          </ol>
          <p v-if="!content.questions.length" class="mt-3 text-ink-muted">Вопросов пока нет.</p>
          <UiButton v-if="!locked" class="mt-3" @click="addQuestion">Добавить вопрос</UiButton>
        </section>
      </fieldset>

      <p v-if="error" role="alert" class="mt-4 whitespace-pre-line text-sm text-red-800">{{ error }}</p>
      <p v-else-if="notice && !dirty" role="status" class="mt-4 text-sm text-brand-700">{{ notice }}</p>
      <UiFormActions v-if="dirty" class="mt-4" save-label="Сохранить вопросы" :loading="saving" @cancel="cancelChanges" />
    </form>

    <section class="mt-6">
      <h2 class="text-lg font-semibold">Шкалы</h2>
      <p class="mt-1 text-sm text-ink-muted">Общие варианты ответа для нескольких вопросов. Сохраняются отдельно от вопросов.</p>
      <div class="mt-3 grid gap-3">
        <ScaleCard
          v-for="(scale, index) in scales"
          :key="scale.key"
          :scale="scale"
          :test-id="route.params.id"
          @saved="scaleSaved(index, $event)"
          @cancel="removeNewScale(index)"
          @dirty="setScaleDirty(scale.key, $event)"
        />
      </div>
      <UiButton class="mt-3" @click="addScale">Новая шкала</UiButton>
    </section>
  </div>
</template>
