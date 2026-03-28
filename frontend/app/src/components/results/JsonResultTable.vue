<script setup>
import { computed } from 'vue'
import { stringifyValue } from '../../utils/format'

const props = defineProps({
  value: {
    type: [Object, Array, String, Number, Boolean, null],
    default: null,
  },
})

function flatten(value, prefix = '', rows = []) {
  if (Array.isArray(value)) {
    value.forEach((item, index) => flatten(item, prefix ? `${prefix}[${index}]` : `[${index}]`, rows))
    return rows
  }

  if (value && typeof value === 'object') {
    Object.entries(value).forEach(([key, nested]) => {
      flatten(nested, prefix ? `${prefix}.${key}` : key, rows)
    })
    return rows
  }

  rows.push({
    path: prefix || 'value',
    value: stringifyValue(value),
    type: value === null ? 'null' : typeof value,
  })
  return rows
}

const rows = computed(() => flatten(props.value))
</script>

<template>
  <div class="overflow-hidden rounded-[28px] border border-slate-200/70 bg-white/92 shadow-sm">
    <div class="overflow-x-auto">
      <table class="min-w-full border-collapse text-left text-sm">
        <thead class="bg-slate-50 text-slate-500">
          <tr>
            <th class="px-4 py-3 font-semibold">Поле</th>
            <th class="px-4 py-3 font-semibold">Тип</th>
            <th class="px-4 py-3 font-semibold">Значение</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in rows" :key="row.path" class="border-t border-slate-100 align-top">
            <td class="px-4 py-3 font-mono text-xs text-slate-600">{{ row.path }}</td>
            <td class="px-4 py-3 text-xs uppercase tracking-[0.18em] text-slate-400">{{ row.type }}</td>
            <td class="px-4 py-3 whitespace-pre-wrap text-slate-800">{{ row.value }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>
