<script setup>
import { computed } from 'vue'

// Результат методики со скриптом расчёта: поля summary — таблицей, весь ответ скрипта — по запросу.
const props = defineProps({ data: { type: Object, required: true } })

const rows = computed(() => Object.entries(props.data.summary || {}))
const display = (value) => (value !== null && typeof value === 'object' ? JSON.stringify(value) : value)
</script>

<template>
  <dl v-if="rows.length" class="grid gap-3 sm:grid-cols-[minmax(10rem,auto)_1fr]">
    <template v-for="[key, value] in rows" :key="key">
      <dt class="text-sm text-ink-muted">{{ key }}</dt>
      <dd class="font-medium">{{ display(value) }}</dd>
    </template>
  </dl>
  <details class="text-sm" :class="{ 'mt-4': rows.length }" :open="!rows.length">
    <summary class="cursor-pointer text-ink-muted">Все данные результата</summary>
    <pre class="mt-2 overflow-auto text-xs">{{ JSON.stringify(data, null, 2) }}</pre>
  </details>
</template>
