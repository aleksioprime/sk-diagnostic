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

function tileClass(option) {
  return getDomikiColorMeta(option.value).tileClass
}

function badgeClass(option) {
  return getDomikiColorMeta(option.value).badgeClass
}
</script>

<template>
  <div class="grid gap-4">
    <div class="rounded-[24px] border border-slate-200/80 bg-slate-50/80 px-4 py-4">
      <div class="flex flex-wrap items-center justify-between gap-3">
        <div>
          <div class="text-sm font-semibold text-slate-900">
            Выбрано {{ rankingState.selectedOptions.length }} из {{ rankingState.totalCount }}
          </div>
          <div class="mt-1 text-sm text-slate-500">
            Выберите самый приятный цвет. После выбора плитка исчезает, и вы переходите к следующему месту.
          </div>
        </div>
        <button
          v-if="rankingState.selectedOptions.length"
          class="ghost-button"
          :disabled="disabled"
          @click="$emit('reset')"
        >
          Сбросить порядок
        </button>
      </div>
    </div>

    <div v-if="rankingState.selectedOptions.length" class="grid gap-2">
      <div class="text-xs font-semibold uppercase tracking-[0.2em] text-slate-400">Выбранный порядок</div>
      <div class="flex flex-wrap gap-2">
        <button
          v-for="(option, index) in rankingState.selectedOptions"
          :key="option.id"
          class="cursor-pointer rounded-full border px-3 py-2 text-sm transition disabled:cursor-not-allowed disabled:opacity-60"
          :class="tileClass(option)"
          :disabled="disabled"
          @click="$emit('remove', option.id)"
        >
          {{ index + 1 }}. {{ option.label }}
        </button>
      </div>
      <p class="text-xs text-slate-400">Нажмите на выбранный цвет, чтобы убрать его из порядка.</p>
    </div>

    <div v-if="rankingState.remainingOptions.length" class="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
      <button
        v-for="option in rankingState.remainingOptions"
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
          <span class="badge" :class="badgeClass(option)">
            {{ rankingState.selectedOptions.length + 1 }}
          </span>
        </div>
      </button>
    </div>

    <div v-else class="rounded-[24px] border border-emerald-200 bg-emerald-50 px-4 py-4 text-sm text-emerald-800">
      Порядок цветов полностью сформирован.
    </div>
  </div>
</template>
