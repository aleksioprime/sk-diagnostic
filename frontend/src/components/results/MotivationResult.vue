<script setup>
import { UiBadge } from 'sk-ui'

defineProps({ data: { type: Object, required: true } })

const LEVEL_TONES = { high: 'brand', medium: 'neutral', low: 'warning' }
</script>

<template>
  <div class="grid gap-4">
    <dl class="grid grid-cols-2 gap-3 sm:grid-cols-4">
      <div class="rounded-control bg-canvas p-3">
        <dt class="text-xs text-ink-muted">Уровень мотивации</dt>
        <dd class="text-2xl font-bold">{{ data.result.level }}</dd>
      </div>
      <div class="rounded-control bg-canvas p-3">
        <dt class="text-xs text-ink-muted">Суммарный балл</dt>
        <dd class="text-2xl font-bold tabular-nums">{{ data.result.total_score }}</dd>
      </div>
      <div class="rounded-control bg-canvas p-3">
        <dt class="text-xs text-ink-muted">Возраст</dt>
        <dd class="text-2xl font-bold tabular-nums">{{ data.student.age }}</dd>
      </div>
      <div class="rounded-control bg-canvas p-3">
        <dt class="text-xs text-ink-muted">Пол</dt>
        <dd class="text-lg font-semibold">{{ data.student.gender_label }}</dd>
      </div>
    </dl>
    <div>
      <h3 class="font-semibold">Описание уровня</h3>
      <p class="mt-1">{{ data.result.level_description }}</p>
    </div>
    <div>
      <h3 class="font-semibold">Интерпретация</h3>
      <p class="mt-1">{{ data.result.interpretation }}</p>
    </div>
    <table class="w-full text-sm">
      <thead class="text-left text-ink-muted">
        <tr>
          <th class="py-2 font-medium">Шкала</th>
          <th class="py-2 font-medium">Баллы</th>
          <th class="py-2 font-medium">Уровень по нормам</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="scale in data.scales" :key="scale.code" class="border-t border-line">
          <td class="py-2">{{ scale.title }}</td>
          <td class="py-2 tabular-nums">{{ scale.value }}</td>
          <td class="py-2">
            <UiBadge :tone="LEVEL_TONES[scale.level]">{{ scale.level_label }}</UiBadge>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
