<script setup>
/**
 * Прохождение методики учеником: по одному вопросу на экране, ответ сохраняется сразу.
 * Можно закрыть страницу и продолжить позже — с того вопроса, где остановились.
 */
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { myAttempt, saveAnswer, startAttempt, submitAttempt } from '@/api/diagnostic'
import { BrandMark, errorMessage, SchoolFooter, SkeletonPage, UiButton, UiCard, UiInput, UiBreadcrumbs } from 'sk-ui'
import QuestionStep from '@/components/questions/QuestionStep.vue'
import { pageTitle } from '@/brand'
import { emptyAnswer, isAnswered } from '@/utils/answers'

const props = defineProps({ id: { type: String, required: true } })

const attempt = ref(null)
const stage = ref('loading') // loading | intro | questions | done | error
const error = ref('')
const answers = ref({})
const index = ref(0)
const birthDate = ref('')
const busy = ref(false)
const saveState = ref('')
let textTimer = null
// Сохранения идут по очереди, последнее состояние ответа всегда уходит на сервер последним
let queue = Promise.resolve(true)

const questions = computed(() => attempt.value?.questions || [])
const question = computed(() => questions.value[index.value])
const isLast = computed(() => index.value === questions.value.length - 1)

const answered = (q) => isAnswered(q, answers.value[q.id])

function apply(data) {
  attempt.value = data
  answers.value = Object.fromEntries(data.questions.map((q) => [q.id, emptyAnswer()]))
  for (const saved of data.answers) answers.value[saved.question_id] = { ...emptyAnswer(), ...saved, ranking: saved.ranking_ids }
}

onMounted(async () => {
  try {
    const data = await myAttempt(props.id)
    apply(data)
    document.title = pageTitle(data.test.title)
    if (data.status === 'submitted') stage.value = 'done'
    else if (!data.is_open) {
      error.value = 'Диагностика закрыта.'
      stage.value = 'error'
    } else stage.value = 'intro'
  } catch (e) {
    error.value = errorMessage(e, 'Диагностика не найдена')
    stage.value = 'error'
  }
})

onBeforeUnmount(() => clearTimeout(textTimer))

async function begin() {
  error.value = ''
  if (attempt.value.needs_birth_date && !birthDate.value) {
    error.value = 'Укажите дату рождения'
    return
  }
  busy.value = true
  try {
    apply(await startAttempt(props.id, birthDate.value || null))
    const firstOpen = questions.value.findIndex((q) => !answered(q))
    index.value = firstOpen === -1 ? questions.value.length - 1 : firstOpen
    stage.value = 'questions'
  } catch (e) {
    error.value = errorMessage(e)
  } finally {
    busy.value = false
  }
}

function persist(q) {
  saveState.value = 'saving'
  queue = queue.then(async () => {
    try {
      await saveAnswer(props.id, q.id, answers.value[q.id])
      saveState.value = 'saved'
      return true
    } catch (e) {
      saveState.value = ''
      error.value = errorMessage(e, 'Ответ не сохранился. Проверьте подключение и попробуйте ещё раз.')
      return false
    }
  })
  return queue
}

function onChange(q, value) {
  answers.value[q.id] = value
  error.value = ''
  clearTimeout(textTimer)
  if (q.question_type === 'text' || q.question_type === 'number') textTimer = setTimeout(() => persist(q), 600)
  else persist(q)
}

async function next() {
  clearTimeout(textTimer)
  if (!(await persist(question.value))) return
  if (isLast.value) return finish()
  index.value += 1
  saveState.value = ''
  window.scrollTo({ top: 0 })
}

async function finish() {
  busy.value = true
  try {
    await submitAttempt(props.id)
    stage.value = 'done'
  } catch (e) {
    const missing = e?.response?.data?.detail?.question_ids
    if (missing?.length) index.value = questions.value.findIndex((q) => missing.includes(q.id))
    error.value = errorMessage(e)
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <div class="flex min-h-dvh flex-col">
    <div class="mx-auto w-full max-w-xl flex-1 px-4 py-8 sm:py-12">
      <BrandMark class="mb-6" />
      <UiBreadcrumbs
        :items="[
          { label: 'Мои диагностики', to: { name: 'my' } },
          { label: 'Прохождение' },
        ]"
      />

      <SkeletonPage v-if="stage === 'loading'" class="mt-6" />

      <UiCard v-else-if="stage === 'error'" class="mt-6 p-6">
        <h1 class="text-xl font-bold">Диагностика недоступна</h1>
        <p class="mt-2 text-ink-muted">{{ error }}</p>
      </UiCard>

      <template v-else>
        <h1 class="mt-4 text-2xl font-bold">{{ attempt.test.title }}</h1>

        <UiCard v-if="stage === 'intro'" class="mt-6 p-6">
          <p v-if="attempt.test.description" class="whitespace-pre-line">{{ attempt.test.description }}</p>
          <p class="mt-4 text-sm text-ink-muted">
            Вопросов: {{ questions.length }}. Правильных и неправильных ответов нет — отвечайте так, как чувствуете. Ответы
            сохраняются сразу, можно продолжить позже.
          </p>
          <UiInput
            v-if="attempt.needs_birth_date"
            v-model="birthDate"
            class="mt-5 max-w-xs"
            label="Дата рождения"
            type="date"
            hint="Нужна, чтобы сравнить ответы с нормами для вашего возраста."
          />
          <p v-if="error" role="alert" class="mt-4 rounded-control bg-red-100 px-3 py-2 text-sm text-red-800">{{ error }}</p>
          <UiButton class="mt-6" variant="primary" :loading="busy" @click="begin">
            {{ attempt.status === 'in_progress' ? 'Продолжить' : 'Начать' }}
          </UiButton>
        </UiCard>

        <QuestionStep
          v-else-if="stage === 'questions' && question"
          class="mt-6"
          :question="question"
          :index="index"
          :total="questions.length"
          :answer="answers[question.id]"
          :shuffle-seed="attempt.id"
          :busy="busy"
          :error="error"
          :status="{ saving: 'Сохраняем…', saved: 'Сохранено' }[saveState] || ''"
          @change="onChange(question, $event)"
          @back="(index -= 1), (saveState = '')"
          @next="next"
        />

        <UiCard v-else-if="stage === 'done'" class="mt-6 p-6 text-center">
          <div class="mx-auto grid size-12 place-items-center rounded-full bg-brand-100 text-2xl text-brand-700" aria-hidden="true">✓</div>
          <h2 class="mt-4 text-xl font-bold">Спасибо!</h2>
          <p class="mt-2 text-ink-muted">Ответы отправлены. Результаты увидит психолог гимназии.</p>
          <RouterLink :to="{ name: 'my' }" class="mt-5 inline-block font-medium text-brand-700">К списку диагностик</RouterLink>
        </UiCard>
      </template>
    </div>
    <SchoolFooter />
  </div>
</template>
