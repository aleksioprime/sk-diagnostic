<script setup>
/** Один вопрос на экране: прогресс, вопрос, ответ и переход дальше. Общий для прохождения и предпросмотра. */
import { computed } from 'vue'
import { UiButton, UiCard } from 'sk-ui'
import AnswerField from '@/components/questions/AnswerField.vue'
import { isAnswered } from '@/utils/answers'
import { seededShuffle } from '@/utils/shuffle'

const props = defineProps({
  question: { type: Object, required: true },
  index: { type: Number, required: true },
  total: { type: Number, required: true },
  answer: { type: Object, required: true },
  // Порядок вариантов при is_random постоянен в рамках одной попытки
  shuffleSeed: { type: [String, Number], required: true },
  busy: { type: Boolean, default: false },
  error: { type: String, default: '' },
  status: { type: String, default: '' },
})
defineEmits(['change', 'back', 'next'])

const progress = computed(() => (props.total ? Math.round((props.index * 100) / props.total) : 0))
const answered = computed(() => isAnswered(props.question, props.answer))

function ordered(items) {
  return props.question.is_random ? seededShuffle(items, `${props.shuffleSeed}${props.question.id}`) : items
}
</script>

<template>
  <section>
    <div class="flex justify-between text-sm text-ink-muted">
      <span>Вопрос {{ index + 1 }} из {{ total }}</span>
      <span aria-live="polite">{{ status }}</span>
    </div>
    <div class="mt-2 h-2 overflow-hidden rounded-full bg-line" role="progressbar" :aria-valuenow="progress" aria-valuemin="0" aria-valuemax="100">
      <div class="h-full rounded-full bg-brand-500 transition-all" :style="{ width: `${progress}%` }" />
    </div>

    <UiCard class="mt-6 sm:p-6">
      <h2 class="text-lg font-semibold">{{ question.text }}</h2>
      <p v-if="question.description" class="mt-1 whitespace-pre-line text-sm text-ink-muted">{{ question.description }}</p>
      <AnswerField
        :key="question.id"
        class="mt-5"
        :model-value="answer"
        :question="question"
        :options="ordered(question.options)"
        :scale-options="ordered(question.scale_options)"
        @update:model-value="$emit('change', $event)"
      />
    </UiCard>

    <p v-if="error" role="alert" class="mt-4 rounded-control bg-red-100 px-3 py-2 text-sm text-red-800">{{ error }}</p>
    <div class="mt-6 flex justify-between gap-3">
      <UiButton :disabled="index === 0" @click="$emit('back')">Назад</UiButton>
      <UiButton variant="primary" :loading="busy" :disabled="question.is_required && !answered" @click="$emit('next')">
        {{ index === total - 1 ? 'Завершить' : 'Далее' }}
      </UiButton>
    </div>
  </section>
</template>
