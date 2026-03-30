<script setup>
import { getDomikiColorMeta } from '../../diagnostics'

const props = defineProps({
  question: {
    type: Object,
    required: true,
  },
  disabled: {
    type: Boolean,
    default: false,
  },
})

defineEmits(['select'])

function tileClass(option) {
  const meta = getDomikiColorMeta(option.value)
  const isSelected = props.question.answer?.scale_option_id === option.id
  return isSelected
    ? `${meta.tileClass} ring-4 ring-primary ring-offset-2 shadow-lg translate-y-[-1px]`
    : meta.tileClass
}
</script>

<template>
  <div class="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
    <button
      v-for="option in question.scaleOptions"
      :key="option.id"
      class="cursor-pointer rounded-[24px] border px-4 py-4 text-left transition disabled:cursor-not-allowed disabled:opacity-60"
      :class="tileClass(option)"
      :disabled="disabled"
      @click="$emit('select', option.id)"
    >
      <div class="flex items-center justify-between gap-3">
        <div>
          <div class="font-medium">{{ option.label }}</div>
          <div v-if="option.description" class="mt-1 text-sm opacity-80">{{ option.description }}</div>
        </div>
        <span
          v-if="question.answer?.scale_option_id === option.id"
          class="badge bg-primary text-white"
        >
          Выбрано
        </span>
      </div>
    </button>
  </div>
</template>
