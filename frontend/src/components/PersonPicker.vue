<script setup>
/** Выбор сотрудников из справочника SkolStream. */
import { UiInput } from 'sk-ui'
import { ref, watch } from 'vue'
import { searchEmployees } from '@/api/diagnostic'

const props = defineProps({
  label: { type: String, required: true },
  hint: { type: String, default: '' },
})
// [{ person_id, full_name, email }]
const model = defineModel({ type: Array, default: () => [] })

const query = ref('')
const found = ref([])
let timer = null

watch(query, (value) => {
  clearTimeout(timer)
  if (value.trim().length < 2) {
    found.value = []
    return
  }
  timer = setTimeout(async () => {
    try {
      const chosen = new Set(model.value.map((p) => p.person_id))
      found.value = (await searchEmployees(value.trim())).filter((p) => !chosen.has(p.id))
    } catch {
      found.value = []
    }
  }, 300)
})

function add(person) {
  model.value = [...model.value, { person_id: person.id, full_name: person.full_name, email: person.email }]
  query.value = ''
  found.value = []
}

function remove(personId) {
  model.value = model.value.filter((p) => p.person_id !== personId)
}
</script>

<template>
  <div class="grid gap-2">
    <p class="text-sm font-medium">{{ props.label }}</p>
    <p v-if="props.hint" class="-mt-1 text-xs text-ink-muted">{{ props.hint }}</p>
    <ul v-if="model.length" class="flex flex-wrap gap-2">
      <li v-for="person in model" :key="person.person_id" class="flex items-center gap-2 rounded-full bg-brand-50 py-1 pl-3 pr-1 text-sm">
        <span :title="person.email">{{ person.full_name }}</span>
        <button type="button" class="grid size-6 place-items-center rounded-full hover:bg-brand-100" :aria-label="`Убрать ${person.full_name}`" @click="remove(person.person_id)">✕</button>
      </li>
    </ul>
    <div class="relative">
      <UiInput v-model="query" type="search" placeholder="Фамилия или email сотрудника" :aria-label="`Добавить: ${props.label}`" />
      <ul v-if="found.length" class="absolute inset-x-0 top-11 z-10 max-h-64 overflow-auto rounded-control border border-line bg-surface shadow-lg">
        <li v-for="person in found" :key="person.id">
          <button type="button" class="w-full px-3 py-2 text-left hover:bg-brand-50" @click="add(person)">
            {{ person.full_name }}
            <span class="block text-xs text-ink-muted">{{ [person.email, ...person.departments].filter(Boolean).join(' · ') }}</span>
          </button>
        </li>
      </ul>
    </div>
  </div>
</template>
