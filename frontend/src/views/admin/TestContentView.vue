<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import { onBeforeRouteLeave, RouterLink, useRoute } from 'vue-router'
import { getTestContent, saveTestContent } from '@/api/diagnostic'
import { errorMessage, SkeletonPage, UiBadge, UiButton, UiCard, UiInput, UiSelect } from 'sk-ui'
import OptionsEditor from '@/components/tests/OptionsEditor.vue'
import ScaleCard from '@/components/tests/ScaleCard.vue'
import TestTabs from '@/components/tests/TestTabs.vue'
import { detailedError } from '@/utils/apiErrors'
import { contentBody, contentProblem, hasOptions, newKey, newQuestion, QUESTION_TYPES, starterOptions, swap, withKeys } from '@/utils/testDraft'

const route = useRoute()
const content = ref(null)
const savedBody = ref('')
const scales = ref([])
const dirtyScales = reactive(new Set())
const loadError = ref('')
const error = ref('')
const notice = ref('')
const saving = ref(false)

const locked = computed(() => content.value?.mode === 'text')
const dirty = computed(() => !!content.value && JSON.stringify(contentBody(content.value)) !== savedBody.value)
const anythingDirty = computed(() => dirty.value || dirtyScales.size > 0)
// В вопросе можно выбрать только сохранённую шкалу
const savedScales = computed(() => scales.value.filter((scale) => scale.id !== null))

function apply(answer) {
  content.value = { ...answer, questions: answer.questions.map(withKeys) }
  savedBody.value = JSON.stringify(contentBody(content.value))
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

function addQuestion() {
  content.value.questions.push(newQuestion())
}

function changeType(question, type) {
  question.question_type = type
  if (hasOptions(type) && !question.options.length) question.options = starterOptions()
}

async function save() {
  error.value = contentProblem(content.value)
  notice.value = ''
  if (error.value) return
  saving.value = true
  try {
    const answer = await saveTestContent(route.params.id, contentBody(content.value))
    apply(answer)
    notice.value = 'Сохранено.'
  } catch (e) {
    error.value = detailedError(e)
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
onBeforeRouteLeave(() => !anythingDirty.value || window.confirm('Есть несохранённые изменения. Уйти со страницы?'))
</script>

<template>
  <p v-if="loadError" role="alert" class="rounded-control bg-red-100 px-3 py-2 text-sm text-red-800">{{ loadError }}</p>
  <SkeletonPage v-else-if="!content" />
  <div v-else class="max-w-4xl">
    <RouterLink :to="{ name: 'admin-tests' }" class="text-sm text-brand-700 hover:underline">← Все методики</RouterLink>
    <h1 class="mt-2 text-2xl font-bold">{{ content.title }}</h1>
    <p class="mt-1 text-sm text-ink-muted"><code>{{ content.code }}</code></p>
    <TestTabs :id="route.params.id" class="mt-4" />

    <p v-if="content.lock_reason" class="mt-4 rounded-control bg-amber-50 px-3 py-2 text-sm text-amber-900">
      {{ content.lock_reason }} Чтобы изменить что-то ещё, сделайте копию методики на странице «Методики».
    </p>

    <UiCard class="mt-4 grid gap-3">
      <UiInput v-model="content.title" label="Название" />
      <label class="grid gap-1 text-sm font-medium">
        Описание
        <textarea v-model="content.description" rows="3" class="rounded-control border border-line bg-surface p-3 font-normal"></textarea>
      </label>
    </UiCard>

    <section class="mt-6">
      <h2 class="text-lg font-semibold">Вопросы ({{ content.questions.length }})</h2>
      <ol class="mt-3 grid gap-3">
        <li v-for="(question, index) in content.questions" :key="question.key">
          <UiCard class="grid gap-3">
            <div class="flex flex-wrap items-center gap-2">
              <span class="font-semibold">Вопрос {{ index + 1 }}</span>
              <div v-if="!locked" class="ml-auto flex gap-1">
                <UiButton size="sm" variant="ghost" :disabled="index === 0" :aria-label="`Вопрос ${index + 1} выше`" @click="swap(content.questions, index, index - 1)">↑</UiButton>
                <UiButton size="sm" variant="ghost" :disabled="index === content.questions.length - 1" :aria-label="`Вопрос ${index + 1} ниже`" @click="swap(content.questions, index, index + 1)">↓</UiButton>
                <UiButton size="sm" variant="ghost" @click="content.questions.splice(index, 1)">Удалить</UiButton>
              </div>
            </div>
            <label class="grid gap-1 text-sm font-medium">
              Текст вопроса
              <textarea v-model="question.text" rows="2" class="rounded-control border border-line bg-surface p-3 font-normal"></textarea>
            </label>
            <UiInput v-model="question.description" label="Пояснение для ученика" />
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
            <div class="flex flex-wrap items-end gap-x-5 gap-y-2 text-sm">
              <label class="flex h-10 items-center gap-2"><input v-model="question.is_required" type="checkbox" :disabled="locked" class="size-4 accent-brand-600" /> Обязательный</label>
              <label v-if="hasOptions(question.question_type)" class="flex h-10 items-center gap-2">
                <input v-model="question.is_random" type="checkbox" :disabled="locked" class="size-4 accent-brand-600" /> Варианты в случайном порядке
              </label>
              <UiInput v-model="question.code" label="Код для скрипта" :disabled="locked" class="ml-auto w-44 [&_input:disabled]:bg-canvas [&_input:disabled]:text-ink-muted" />
            </div>
          </UiCard>
        </li>
      </ol>
      <p v-if="!content.questions.length" class="mt-3 text-ink-muted">Вопросов пока нет.</p>
      <UiButton v-if="!locked" class="mt-3" @click="addQuestion">Добавить вопрос</UiButton>
    </section>

    <div class="sticky bottom-0 z-10 mt-4 flex flex-wrap items-center gap-3 border-t border-line bg-canvas py-3">
      <UiButton variant="primary" :loading="saving" :disabled="!dirty" @click="save">Сохранить вопросы</UiButton>
      <UiBadge v-if="dirty" tone="warning">Не сохранено</UiBadge>
      <p v-if="error" role="alert" class="whitespace-pre-line text-sm text-red-800">{{ error }}</p>
      <p v-else-if="notice" role="status" class="text-sm text-brand-700">{{ notice }}</p>
    </div>

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
