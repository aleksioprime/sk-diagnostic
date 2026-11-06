<script setup>
/** Методика глазами ученика: те же экраны, что при прохождении. Ответы остаются в браузере, расчёт ничего не сохраняет. */
import { computed, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { getTestPreview, previewResult } from '@/api/diagnostic'
import { BrandMark, errorMessage, SchoolFooter, SkeletonPage, UiButton, UiCard, UiInput } from 'sk-ui'
import QuestionStep from '@/components/questions/QuestionStep.vue'
import { resultComponent } from '@/components/results/resultComponent'
import { pageTitle } from '@/brand'
import { emptyAnswer } from '@/utils/answers'

const props = defineProps({ id: { type: String, required: true } })

const preview = ref(null)
const loadError = ref('')
const stage = ref('intro') // intro | questions | result
const answers = ref({})
const index = ref(0)
const birthDate = ref('')
const error = ref('')
const busy = ref(false)
const run = ref(null)

const questions = computed(() => preview.value?.questions || [])
const question = computed(() => questions.value[index.value])
const template = computed(() => resultComponent(run.value?.output))

function reset() {
  answers.value = Object.fromEntries(questions.value.map((q) => [q.id, emptyAnswer()]))
  index.value = 0
  error.value = ''
  run.value = null
  stage.value = 'intro'
}

onMounted(async () => {
  try {
    preview.value = await getTestPreview(props.id)
    document.title = pageTitle(`Предпросмотр: ${preview.value.test.title}`)
    reset()
  } catch (e) {
    loadError.value = errorMessage(e, 'Методика не найдена')
  }
})

function begin() {
  error.value = ''
  if (preview.value.needs_birth_date && !birthDate.value) {
    error.value = 'Укажите дату рождения'
    return
  }
  stage.value = 'questions'
}

async function next() {
  if (index.value < questions.value.length - 1) {
    index.value += 1
    window.scrollTo({ top: 0 })
    return
  }
  busy.value = true
  error.value = ''
  try {
    run.value = await previewResult(props.id, {
      birth_date: birthDate.value || null,
      answers: questions.value.map((q) => ({ ...answers.value[q.id], question_id: q.id })),
    })
    stage.value = 'result'
    window.scrollTo({ top: 0 })
  } catch (e) {
    error.value = errorMessage(e)
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <div class="flex min-h-dvh flex-col">
    <p class="bg-amber-100 px-4 py-2 text-center text-sm text-amber-900">Предпросмотр: так методику видит ученик. Ответы не сохраняются.</p>
    <div class="mx-auto w-full max-w-xl flex-1 px-4 py-8 sm:py-12">
      <BrandMark class="mb-6" />
      <RouterLink :to="{ name: 'admin-test-check', params: { id } }" class="text-sm text-ink-muted hover:text-ink">← К проверке методики</RouterLink>

      <UiCard v-if="loadError" class="mt-6 p-6">
        <h1 class="text-xl font-bold">Предпросмотр недоступен</h1>
        <p class="mt-2 text-ink-muted">{{ loadError }}</p>
      </UiCard>
      <SkeletonPage v-else-if="!preview" class="mt-6" />

      <template v-else>
        <h1 class="mt-4 text-2xl font-bold">{{ preview.test.title }}</h1>

        <UiCard v-if="stage === 'intro'" class="mt-6 p-6">
          <p v-if="preview.test.description" class="whitespace-pre-line">{{ preview.test.description }}</p>
          <p class="mt-4 text-sm text-ink-muted">
            Вопросов: {{ questions.length }}. Правильных и неправильных ответов нет — отвечайте так, как чувствуете. Ответы
            сохраняются сразу, можно продолжить позже.
          </p>
          <UiInput
            v-if="preview.needs_birth_date"
            v-model="birthDate"
            class="mt-5 max-w-xs"
            label="Дата рождения"
            type="date"
            hint="Нужна, чтобы сравнить ответы с нормами для вашего возраста."
          />
          <p v-if="error" role="alert" class="mt-4 rounded-control bg-red-100 px-3 py-2 text-sm text-red-800">{{ error }}</p>
          <p v-if="!questions.length" class="mt-4 text-sm text-amber-800">В методике пока нет вопросов.</p>
          <UiButton class="mt-6" variant="primary" :disabled="!questions.length" @click="begin">Начать</UiButton>
        </UiCard>

        <QuestionStep
          v-else-if="stage === 'questions' && question"
          class="mt-6"
          :question="question"
          :index="index"
          :total="questions.length"
          :answer="answers[question.id]"
          shuffle-seed="preview"
          :busy="busy"
          :error="error"
          @change="answers[question.id] = $event"
          @back="index -= 1"
          @next="next"
        />

        <template v-else-if="stage === 'result'">
          <p class="mt-6 text-sm text-ink-muted">
            Ученик на этом шаге увидит только благодарность. Ниже результат, который увидит психолог; в расчёт подставлен выдуманный ученик.
          </p>
          <UiCard class="mt-3">
            <div v-if="run.error" role="alert" class="rounded-control bg-amber-50 px-4 py-3 text-amber-900">
              <p class="font-semibold">Результат не рассчитан</p>
              <p class="mt-1 text-sm"><span v-if="run.line">Строка {{ run.line }}: </span>{{ run.error }}</p>
            </div>
            <component :is="template" v-else :data="run.output" />
          </UiCard>
          <UiButton class="mt-4" @click="reset">Пройти ещё раз</UiButton>
        </template>
      </template>
    </div>
    <SchoolFooter />
  </div>
</template>
