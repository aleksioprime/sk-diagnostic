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
  const selectedId = props.question.answer?.scale_option_id
  const isSelected = selectedId === option.id
  const isDimmed = selectedId && !isSelected
  return [
    isSelected ? 'ring-4 ring-primary ring-offset-2 shadow-lg scale-95' : '',
    isDimmed ? 'opacity-30' : '',
  ].join(' ')
}

function tileStyle(option) {
  const { hex } = getDomikiColorMeta(option.value)
  return hex ? { backgroundColor: hex, borderColor: hex } : {}
}
</script>

<template>
  <div class="grid grid-cols-4 gap-3">
    <button
      v-for="option in question.scaleOptions"
      :key="option.id"
      class="aspect-square cursor-pointer rounded-[16px] border-4 transition disabled:cursor-not-allowed disabled:opacity-60"
      :class="tileClass(option)"
      :style="tileStyle(option)"
      :disabled="disabled"
      @click="$emit('select', option.id)"
    />
  </div>
</template>
