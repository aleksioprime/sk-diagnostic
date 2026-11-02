<script setup>
import { COLOR_HEX } from '@/utils/colors'

defineProps({ data: { type: Object, required: true } })
</script>

<template>
  <div class="grid gap-5">
    <div class="grid gap-3 sm:grid-cols-2">
      <section class="rounded-control bg-canvas p-4">
        <p class="text-xs text-ink-muted">Вегетативный коэффициент</p>
        <p class="text-2xl font-bold tabular-nums">{{ data.result.vegetative_coefficient.value }}</p>
        <p class="font-medium">{{ data.result.vegetative_coefficient.label }}</p>
        <p class="mt-1 text-sm text-ink-muted">{{ data.result.vegetative_coefficient.interpretation }}</p>
      </section>
      <section class="rounded-control bg-canvas p-4">
        <p class="text-xs text-ink-muted">Суммарное отклонение от аутогенной нормы</p>
        <p class="text-2xl font-bold tabular-nums">{{ data.result.emotional_background.value }}</p>
        <p class="font-medium">{{ data.result.emotional_background.title }}</p>
        <p class="mt-1 text-sm text-ink-muted">{{ data.result.emotional_background.interpretation }}</p>
      </section>
      <section class="rounded-control bg-canvas p-4">
        <p class="text-xs text-ink-muted">Самооценка</p>
        <p class="text-lg font-semibold">{{ data.result.self_esteem.label }}</p>
      </section>
      <section class="rounded-control bg-canvas p-4">
        <p class="text-xs text-ink-muted">Отношение к школе</p>
        <p class="text-lg font-semibold">{{ data.result.school_relation.label }}</p>
        <p class="mt-1 text-sm text-ink-muted">{{ data.result.school_relation.interpretation }}</p>
      </section>
    </div>

    <div>
      <h3 class="font-semibold">Домики</h3>
      <ul class="mt-2 grid gap-2 sm:grid-cols-2">
        <li
          v-for="domain in data.domains"
          :key="domain.code"
          class="flex items-start gap-3 rounded-control border px-3 py-2"
          :class="domain.status === 'attention' ? 'border-amber-300 bg-amber-50' : 'border-line'"
        >
          <span class="mt-0.5 size-6 shrink-0 rounded-md" :style="{ backgroundColor: COLOR_HEX[domain.color_code] }" :title="domain.color_title" />
          <span class="min-w-0">
            <span class="font-medium">{{ domain.title }}</span>
            <span class="block text-xs text-ink-muted">{{ domain.color_title }} · {{ domain.status_label }}</span>
            <span v-if="domain.description" class="block text-sm">{{ domain.description }}</span>
          </span>
        </li>
      </ul>
    </div>
  </div>
</template>
