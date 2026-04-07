<script setup>
defineProps({
  sections: {
    type: Array,
    default: () => [],
  },
})
</script>

<template>
  <div class="grid gap-5">
    <section
      v-for="section in sections"
      :key="section.title"
      class="glass-panel overflow-hidden p-5 sm:p-6"
    >
      <div class="mb-4 flex items-center justify-between gap-3">
        <h2 class="text-lg font-semibold text-slate-900">{{ section.title }}</h2>
      </div>

      <div v-if="section.kind === 'stats'" class="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <div
          v-for="item in section.items"
          :key="item.label"
          class="rounded-3xl border border-slate-200/70 bg-white/85 p-4"
        >
          <div class="text-xs font-semibold uppercase tracking-[0.18em] text-slate-400">{{ item.label }}</div>
          <div class="mt-2 text-2xl font-semibold text-slate-900">{{ item.value }}</div>
        </div>
      </div>

      <div v-else-if="section.kind === 'text'" class="rounded-3xl border border-primary/15 bg-primary/6 p-5 text-sm leading-7 text-slate-700">
        {{ section.text }}
      </div>

      <div v-else-if="section.kind === 'keyValue'" class="grid gap-3 md:grid-cols-2">
        <div
          v-for="item in section.items"
          :key="item.label"
          class="rounded-3xl border border-slate-200/70 bg-white/85 p-4"
        >
          <div class="text-xs font-semibold uppercase tracking-[0.18em] text-slate-400">{{ item.label }}</div>
          <div class="mt-2 text-sm font-medium text-slate-800">{{ item.value }}</div>
        </div>
      </div>

      <div v-else-if="section.kind === 'table'" class="overflow-hidden rounded-3xl border border-slate-200/70 bg-white/92">
        <div class="overflow-x-auto">
          <table class="min-w-full border-collapse text-left text-sm">
            <thead class="bg-slate-50 text-slate-500">
              <tr>
                <th
                  v-for="column in section.columns"
                  :key="column.key"
                  class="px-4 py-3 font-semibold"
                >
                  {{ column.label }}
                </th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="(row, index) in section.rows"
                :key="index"
                class="border-t border-slate-100"
                :class="{
                  'bg-amber-50/70': row._tone === 'warning',
                }"
              >
                <td
                  v-for="column in section.columns"
                  :key="column.key"
                  class="px-4 py-3"
                  :class="row._tone === 'warning' ? 'text-amber-900' : 'text-slate-800'"
                >
                  {{ row[column.key] }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </section>
  </div>
</template>
