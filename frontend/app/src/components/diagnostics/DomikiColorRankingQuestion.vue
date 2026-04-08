<script setup>
import { computed } from 'vue'
import { getDomikiColorMeta, getDomikiRankingState } from '../../diagnostics'

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

defineEmits(['select', 'remove', 'reset'])

const rankingState = computed(() => getDomikiRankingState(props.question))

function tileStyle(option) {
  const { hex } = getDomikiColorMeta(option.value)
  return hex ? { backgroundColor: hex, borderColor: hex } : {}
}
</script>

<template>
  <div class="grid gap-4">
    <div v-if="rankingState.remainingOptions.length" class="grid grid-cols-4 gap-3">
      <button
        v-for="option in rankingState.remainingOptions"
        :key="option.id"
        class="aspect-square cursor-pointer rounded-[16px] border-4 transition disabled:cursor-not-allowed disabled:opacity-60"
        :style="tileStyle(option)"
        :disabled="disabled"
        @click="$emit('select', option.id)"
      />
    </div>

    <div v-if="rankingState.selectedOptions.length" class="flex justify-start">
      <button class="ghost-button" :disabled="disabled" @click="$emit('reset')">Сбросить</button>
    </div>

    <div v-if="!rankingState.remainingOptions.length" class="rounded-[24px] border border-emerald-200 bg-emerald-50 px-4 py-4 text-sm text-emerald-800">
      Порядок цветов полностью сформирован
    </div>
  </div>
</template>
