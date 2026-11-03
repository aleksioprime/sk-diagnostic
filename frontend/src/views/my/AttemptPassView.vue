<script setup>
/**
 * Прохождение методики учеником: по одному вопросу на экране, ответ сохраняется сразу.
 * Можно закрыть страницу и продолжить позже — с того вопроса, где остановились.
 */
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { myAttempt, saveAnswer, startAttempt, submitAttempt } from '@/api/diagnostic'
import { errorMessage } from '@/api/http'
import BrandMark from '@/components/brand/BrandMark.vue'
import SchoolFooter from '@/components/brand/SchoolFooter.vue'
import AnswerField from '@/components/questions/AnswerField.vue'
import UiButton from '@/components/ui/UiButton.vue'
import { pageTitle } from '@/brand'
import { seededShuffle } from '@/utils/shuffle'

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

const empty = () => ({ option_id: null, scale_option_id: null, text: null, number: null, boolean: null, ranking: [] })
const questions = computed(() => attempt.value?.questions || [])
const question = computed(() => questions.value[index.value])
const isLast = computed(() => index.value === questions.value.length - 1)
const progress = computed(() => (questions.value.length ? Math.round((index.value * 100) / questions.value.length) : 0))

function ordered(items, q) {
  return q.is_random ? seededShuffle(items, `${attempt.value.id}${q.id}`) : items
}

function answered(q) {
  const a = answers.value[q.id]
  if (!a) return false
  if (q.question_type === 'ranking') return (a.ranking || []).length >= (q.min_selections || q.options.length)
  return [a.option_id, a.scale_option_id, a.number, a.boolean].some((v) => v != null) || !!a.text?.trim()
}

function apply(data) {
  attempt.value = data
  answers.value = Object.fromEntries(data.questions.map((q) => [q.id, empty()]))
  for (const saved of data.answers) answers.value[saved.question_id] = { ...empty(), ...saved, ranking: saved.ranking_ids }
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
      <RouterLink :to="{ name: 'my' }" class="text-sm text-ink-muted hover:text-ink">← Мои диагностики</RouterLink>

      <p v-if="stage === 'loading'" class="mt-6 text-ink-muted" role="status">Загружаем…</p>

      <div v-else-if="stage === 'error'" class="mt-6 rounded-card border border-line bg-surface p-6">
        <h1 class="text-xl font-bold">Диагностика недоступна</h1>
        <p class="mt-2 text-ink-muted">{{ error }}</p>
      </div>

      <template v-else>
        <h1 class="mt-4 text-2xl font-bold">{{ attempt.test.title }}</h1>

        <section v-if="stage === 'intro'" class="mt-6 rounded-card border border-line bg-surface p-6">
          <p v-if="attempt.test.description" class="whitespace-pre-line">{{ attempt.test.description }}</p>
          <p class="mt-4 text-sm text-ink-muted">
            Вопросов: {{ questions.length }}. Правильных и неправильных ответов нет — отвечайте так, как чувствуете. Ответы
            сохраняются сразу, можно продолжить позже.
          </p>
          <label v-if="attempt.needs_birth_date" class="mt-5 grid max-w-xs gap-1.5 text-sm font-medium">
            Дата рождения
            <input v-model="birthDate" type="date" class="h-10 rounded-control border border-line bg-surface px-3" />
            <span class="font-normal text-ink-muted">Нужна, чтобы сравнить ответы с нормами для вашего возраста.</span>
          </label>
          <p v-if="error" role="alert" class="mt-4 rounded-control bg-red-100 px-3 py-2 text-sm text-red-800">{{ error }}</p>
          <UiButton class="mt-6" variant="primary" :loading="busy" @click="begin">
            {{ attempt.status === 'in_progress' ? 'Продолжить' : 'Начать' }}
          </UiButton>
        </section>

        <section v-else-if="stage === 'questions' && question" class="mt-6">
          <div class="flex justify-between text-sm text-ink-muted">
            <span>Вопрос {{ index + 1 }} из {{ questions.length }}</span>
            <span aria-live="polite">{{ { saving: 'Сохраняем…', saved: 'Сохранено' }[saveState] || '' }}</span>
          </div>
          <div class="mt-2 h-2 overflow-hidden rounded-full bg-line" role="progressbar" :aria-valuenow="progress" aria-valuemin="0" aria-valuemax="100">
            <div class="h-full rounded-full bg-brand-500 transition-all" :style="{ width: `${progress}%` }" />
          </div>

          <article class="mt-6 rounded-card border border-line bg-surface p-5 sm:p-6">
            <h2 class="text-lg font-semibold">{{ question.text }}</h2>
            <p v-if="question.description" class="mt-1 whitespace-pre-line text-sm text-ink-muted">{{ question.description }}</p>
            <AnswerField
              :key="question.id"
              class="mt-5"
              :model-value="answers[question.id]"
              :question="question"
              :options="ordered(question.options, question)"
              :scale-options="ordered(question.scale_options, question)"
              @update:model-value="onChange(question, $event)"
            />
          </article>

          <p v-if="error" role="alert" class="mt-4 rounded-control bg-red-100 px-3 py-2 text-sm text-red-800">{{ error }}</p>
          <div class="mt-6 flex justify-between gap-3">
            <UiButton :disabled="index === 0" @click="(index -= 1), (saveState = '')">Назад</UiButton>
            <UiButton variant="primary" :loading="busy" :disabled="question.is_required && !answered(question)" @click="next">
              {{ isLast ? 'Завершить' : 'Далее' }}
            </UiButton>
          </div>
        </section>

        <section v-else-if="stage === 'done'" class="mt-6 rounded-card border border-line bg-surface p-6 text-center">
          <div class="mx-auto grid size-12 place-items-center rounded-full bg-brand-100 text-2xl text-brand-700" aria-hidden="true">✓</div>
          <h2 class="mt-4 text-xl font-bold">Спасибо!</h2>
          <p class="mt-2 text-ink-muted">Ответы отправлены. Результаты увидит психолог гимназии.</p>
          <RouterLink :to="{ name: 'my' }" class="mt-5 inline-block font-medium text-brand-700">К списку диагностик</RouterLink>
        </section>
      </template>
    </div>
    <SchoolFooter />
  </div>
</template>
