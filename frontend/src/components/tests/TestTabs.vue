<script setup>
import { RouterLink } from 'vue-router'

defineProps({ id: { type: [String, Number], required: true } })

const tabs = [
  { name: 'admin-test-questions', label: 'Вопросы и ответы' },
  { name: 'admin-test', label: 'Расчёт' },
]
</script>

<template>
  <nav class="flex gap-1 border-b border-line" aria-label="Разделы методики">
    <RouterLink
      v-for="tab in tabs"
      :key="tab.name"
      :to="{ name: tab.name, params: { id } }"
      class="-mb-px border-b-2 border-transparent px-3 py-2 text-sm font-medium text-ink-muted hover:text-ink"
      exact-active-class="!border-brand-600 !text-brand-700"
    >
      {{ tab.label }}
    </RouterLink>
  </nav>
</template>
