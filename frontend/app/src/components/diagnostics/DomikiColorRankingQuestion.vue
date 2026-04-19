<script setup>
import { computed } from 'vue'
import { getDomikiColorMeta, getDomikiRankingState } from '../../diagnostics'

const props = defineProps({
  question: {
    type: Object,
    required: true,
  },
  isSaved: {
    type: Boolean,
    default: false,
  },
  disabled: {
    type: Boolean,
    default: false,
  },
})

defineEmits(['select', 'remove', 'reset'])

const rankingState = computed(() => getDomikiRankingState(props.question))
const hasOptions = computed(() => rankingState.value.totalCount > 0)

function tileStyle(option) {
  const { hex } = getDomikiColorMeta(option.value)
  return hex ? { backgroundColor: hex, borderColor: hex } : {}
}
</script>

<template>
  <div class="grid gap-4">
    <div v-if="!hasOptions" class="rounded-[24px] border border-red-200 bg-red-50 px-4 py-4 text-sm text-red-700">
      Не удалось загрузить варианты для ранжирования. Проверьте, что для вопроса есть активные записи в таблице `options`.
    </div>

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

    <div
      v-if="hasOptions && !rankingState.remainingOptions.length"
      class="rounded-[24px] px-4 py-4 text-sm"
      :class="props.isSaved ? 'border border-emerald-200 bg-emerald-50 text-emerald-800' : 'border border-amber-200 bg-amber-50 text-amber-800'"
    >
      Порядок цветов полностью сформирован
    </div>
  </div>
</template>
