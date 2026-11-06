<script setup>
import { computed, ref, watch } from 'vue'
import { createScale, saveScale } from '@/api/diagnostic'
import { UiBadge, UiButton, UiCard, UiInput } from 'sk-ui'
import { detailedError } from '@/utils/apiErrors'
import { scaleBody, withKeys } from '@/utils/testDraft'
import OptionsEditor from './OptionsEditor.vue'

// Шкала сохраняется отдельно от вопросов: её выбирают в вопросах только сохранённой.
const props = defineProps({
  scale: { type: Object, required: true },
  testId: { type: [String, Number], required: true },
})
const emit = defineEmits(['saved', 'cancel', 'dirty'])

const draft = ref(withKeys(props.scale))
const saved = ref(JSON.stringify(scaleBody(draft.value)))
const saving = ref(false)
const error = ref('')

const isNew = computed(() => props.scale.id === null)
const dirty = computed(() => isNew.value || JSON.stringify(scaleBody(draft.value)) !== saved.value)
watch(dirty, (value) => emit('dirty', value), { immediate: true })

const NOTES = {
  text: 'Методика уже используется: можно менять только подписи.',
  none: 'Шкалу используют и другие методики, поэтому здесь её менять нельзя. Для другой шкалы создайте новую.',
}

async function save() {
  if (!draft.value.title.trim() || draft.value.options.some((o) => !o.label.trim())) {
    error.value = 'Заполните название шкалы и подписи всех вариантов'
    return
  }
  if (!draft.value.options.length) {
    error.value = 'Добавьте варианты'
    return
  }
  saving.value = true
  error.value = ''
  try {
    const body = scaleBody(draft.value)
    const answer = isNew.value ? await createScale(props.testId, body) : await saveScale(props.testId, props.scale.id, body)
    draft.value = withKeys(answer)
    saved.value = JSON.stringify(scaleBody(draft.value))
    emit('saved', answer)
  } catch (e) {
    error.value = detailedError(e)
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <UiCard class="grid gap-3">
    <div class="flex flex-wrap items-center gap-2">
      <UiInput v-model="draft.title" label="Название шкалы" class="min-w-64 flex-1 [&_input:disabled]:bg-canvas [&_input:disabled]:text-ink-muted" :disabled="scale.mode === 'none'" />
      <UiBadge v-if="dirty && !isNew" tone="warning">Не сохранена</UiBadge>
    </div>
    <p v-if="NOTES[scale.mode]" class="text-sm text-ink-muted">{{ NOTES[scale.mode] }}</p>
    <OptionsEditor v-model="draft.options" :fixed="scale.mode === 'text'" :readonly="scale.mode === 'none'" />
    <p v-if="error" role="alert" class="whitespace-pre-line rounded-control bg-red-100 px-3 py-2 text-sm text-red-800">{{ error }}</p>
    <div v-if="scale.mode !== 'none'" class="flex gap-2">
      <UiButton size="sm" variant="primary" :loading="saving" :disabled="!dirty" @click="save">Сохранить шкалу</UiButton>
      <UiButton v-if="isNew" size="sm" @click="emit('cancel')">Отмена</UiButton>
    </div>
  </UiCard>
</template>
