<script setup>
import { onMounted, ref } from 'vue'
import { listPsychologists, setPsychologists } from '@/api/diagnostic'
import { errorMessage } from '@/api/http'
import PersonPicker from '@/components/PersonPicker.vue'
import UiButton from '@/components/ui/UiButton.vue'

const people = ref([])
const error = ref('')
const notice = ref('')
const saving = ref(false)

onMounted(async () => {
  try {
    people.value = await listPsychologists()
  } catch (e) {
    error.value = errorMessage(e)
  }
})

async function save() {
  saving.value = true
  error.value = ''
  notice.value = ''
  try {
    people.value = await setPsychologists(people.value.map((p) => p.person_id))
    notice.value = 'Сохранено'
  } catch (e) {
    error.value = errorMessage(e)
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <div class="max-w-2xl">
    <h1 class="text-2xl font-bold">Психологическая служба</h1>
    <p class="mt-1 text-ink-muted">Психологи выдают методики классам и видят результаты учеников. Остальные сотрудники и ученики результатов не видят.</p>
    <p v-if="error" role="alert" class="mt-4 rounded-control bg-red-100 px-3 py-2 text-sm text-red-800">{{ error }}</p>
    <p v-if="notice" role="status" class="mt-4 rounded-control bg-brand-50 px-3 py-2 text-sm text-brand-700">{{ notice }}</p>
    <div class="mt-6 grid gap-4 rounded-card border border-line bg-surface p-5">
      <PersonPicker v-model="people" label="Психологи" hint="Сотрудники из справочника SkolStream." />
      <UiButton variant="primary" class="justify-self-start" :loading="saving" @click="save">Сохранить</UiButton>
    </div>
  </div>
</template>
