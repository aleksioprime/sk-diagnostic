<script setup>
/**
 * Ответ на вопрос методики. v-model — ответ в форме API:
 * { option_id, scale_option_id, text, number, boolean, ranking }.
 * Вопросы с цветами («Домики») показываются цветными плитками без подписей.
 */
import { computed } from 'vue'
import { COLOR_HEX, isColorQuestion } from '@/utils/colors'

const props = defineProps({
  question: { type: Object, required: true },
  // Порядок вариантов для этой попытки (при is_random — перемешанный)
  options: { type: Array, required: true },
  scaleOptions: { type: Array, required: true },
  disabled: { type: Boolean, default: false },
})
const model = defineModel({ type: Object, required: true })

const colors = computed(() => isColorQuestion(props.question))
const ranked = computed(() => model.value.ranking || [])
const remaining = computed(() => props.options.filter((o) => !ranked.value.includes(o.id)))
const rankedOptions = computed(() => ranked.value.map((id) => props.options.find((o) => o.id === id)).filter(Boolean))

function set(changes) {
  model.value = { ...model.value, ...changes }
}

const tile = (value) => ({ backgroundColor: COLOR_HEX[value.toLowerCase()] })
</script>

<template>
  <div class="grid gap-4">
    <!-- Шкала: цвета или подписи -->
    <template v-if="question.question_type === 'scale'">
      <div v-if="colors" class="grid grid-cols-4 gap-3 sm:gap-4" role="radiogroup" :aria-label="question.text">
        <button
          v-for="(option, index) in scaleOptions"
          :key="option.id"
          type="button"
          role="radio"
          :aria-checked="model.scale_option_id === option.id"
          :aria-label="`Цвет ${index + 1}`"
          :disabled="disabled"
          class="aspect-square rounded-2xl transition"
          :class="[
            model.scale_option_id === option.id ? 'scale-95 ring-4 ring-brand-500 ring-offset-2' : '',
            model.scale_option_id && model.scale_option_id !== option.id ? 'opacity-30' : '',
          ]"
          :style="tile(option.value)"
          @click="set({ scale_option_id: option.id })"
        />
      </div>
      <div v-else class="grid gap-2" role="radiogroup" :aria-label="question.text">
        <button
          v-for="option in scaleOptions"
          :key="option.id"
          type="button"
          role="radio"
          :aria-checked="model.scale_option_id === option.id"
          :disabled="disabled"
          class="rounded-control border px-4 py-3 text-left font-medium transition"
          :class="model.scale_option_id === option.id ? 'border-brand-500 bg-brand-50 ring-1 ring-brand-500' : 'border-line bg-surface hover:border-brand-200'"
          @click="set({ scale_option_id: option.id })"
        >
          {{ option.label }}
        </button>
      </div>
    </template>

    <!-- Расстановка по порядку: нажимать в порядке предпочтения -->
    <template v-else-if="question.question_type === 'ranking'">
      <p class="text-sm text-ink-muted">
        Нажимайте по очереди: сначала {{ colors ? 'цвет' : 'вариант' }}, который нравится больше всего, затем следующий — и так до
        последнего.
      </p>
      <div v-if="remaining.length" :class="colors ? 'grid grid-cols-4 gap-3 sm:gap-4' : 'flex flex-wrap gap-2'">
        <button
          v-for="option in remaining"
          :key="option.id"
          type="button"
          :disabled="disabled"
          :aria-label="colors ? 'Выбрать цвет' : option.label"
          :class="colors ? 'aspect-square rounded-2xl transition hover:scale-95' : 'rounded-control border border-line bg-surface px-3 py-2 hover:border-brand-200'"
          :style="colors ? tile(option.value) : undefined"
          @click="set({ ranking: [...ranked, option.id] })"
        >
          <template v-if="!colors">{{ option.label }}</template>
        </button>
      </div>
      <div v-if="rankedOptions.length" class="grid gap-2">
        <p class="text-sm font-medium">Ваш порядок</p>
        <ol class="flex flex-wrap gap-2">
          <li v-for="(option, index) in rankedOptions" :key="option.id" class="flex items-center gap-1.5">
            <span class="text-sm tabular-nums text-ink-muted">{{ index + 1 }}</span>
            <span v-if="colors" class="size-9 rounded-lg" :style="tile(option.value)" aria-hidden="true" />
            <span v-else class="rounded-control bg-brand-50 px-2 py-1 text-sm">{{ option.label }}</span>
          </li>
        </ol>
        <button type="button" class="justify-self-start text-sm font-medium text-brand-700" :disabled="disabled" @click="set({ ranking: [] })">
          Начать заново
        </button>
      </div>
    </template>

    <div v-else-if="question.question_type === 'single_choice'" class="grid gap-2" role="radiogroup" :aria-label="question.text">
      <button
        v-for="option in options"
        :key="option.id"
        type="button"
        role="radio"
        :aria-checked="model.option_id === option.id"
        :disabled="disabled"
        class="rounded-control border px-4 py-3 text-left transition"
        :class="model.option_id === option.id ? 'border-brand-500 bg-brand-50 ring-1 ring-brand-500' : 'border-line bg-surface hover:border-brand-200'"
        @click="set({ option_id: option.id })"
      >
        {{ option.label }}
      </button>
    </div>

    <textarea
      v-else-if="question.question_type === 'text'"
      :value="model.text || ''"
      rows="4"
      :disabled="disabled"
      class="w-full rounded-control border border-line bg-surface p-3 outline-none focus:border-brand-500"
      placeholder="Ваш ответ"
      :aria-label="question.text"
      @input="set({ text: $event.target.value })"
    />

    <input
      v-else-if="question.question_type === 'number'"
      type="number"
      :value="model.number ?? ''"
      :disabled="disabled"
      class="h-10 max-w-xs rounded-control border border-line bg-surface px-3"
      :aria-label="question.text"
      @input="set({ number: $event.target.value === '' ? null : Number($event.target.value) })"
    />

    <div v-else-if="question.question_type === 'yes_no'" class="flex gap-2">
      <button
        v-for="choice in [{ value: true, label: 'Да' }, { value: false, label: 'Нет' }]"
        :key="choice.label"
        type="button"
        :disabled="disabled"
        class="min-w-24 rounded-control border px-5 py-2.5 font-medium"
        :class="model.boolean === choice.value ? 'border-brand-500 bg-brand-50 ring-1 ring-brand-500' : 'border-line bg-surface'"
        @click="set({ boolean: choice.value })"
      >
        {{ choice.label }}
      </button>
    </div>
  </div>
</template>
