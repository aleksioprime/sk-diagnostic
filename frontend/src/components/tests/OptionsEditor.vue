<script setup>
import { UiButton, UiInput } from 'sk-ui'
import { newKey, swap } from '@/utils/testDraft'

// Варианты ответа. fixed — только подписи, readonly — только просмотр.
const props = defineProps({
  fixed: { type: Boolean, default: false },
  readonly: { type: Boolean, default: false },
})
const options = defineModel({ type: Array, required: true })

const canRestructure = () => !props.fixed && !props.readonly

function add() {
  options.value.push({ id: null, key: newKey(), label: '', description: '', value: String(options.value.length + 1), score: options.value.length + 1 })
}
</script>

<template>
  <div class="grid gap-2">
    <div class="hidden grid-cols-[1fr_7rem_5rem_6.5rem] gap-2 text-xs text-ink-muted sm:grid">
      <span>Подпись</span><span>Значение</span><span>Баллы</span>
    </div>
    <div v-for="(option, index) in options" :key="option.key" class="grid items-center gap-2 sm:grid-cols-[1fr_7rem_5rem_6.5rem]">
      <UiInput v-model="option.label" :disabled="readonly" :aria-label="`Подпись варианта ${index + 1}`" class="[&_input:disabled]:bg-canvas [&_input:disabled]:text-ink-muted" />
      <UiInput v-model="option.value" :disabled="fixed || readonly" :aria-label="`Значение варианта ${index + 1}`" class="[&_input:disabled]:bg-canvas [&_input:disabled]:text-ink-muted" />
      <UiInput v-model="option.score" type="number" step="any" :disabled="fixed || readonly" :aria-label="`Баллы варианта ${index + 1}`" class="[&_input:disabled]:bg-canvas [&_input:disabled]:text-ink-muted" />
      <div v-if="canRestructure()" class="flex gap-1">
        <UiButton size="sm" variant="ghost" :disabled="index === 0" :aria-label="`Вариант ${index + 1} выше`" @click="swap(options, index, index - 1)">↑</UiButton>
        <UiButton size="sm" variant="ghost" :disabled="index === options.length - 1" :aria-label="`Вариант ${index + 1} ниже`" @click="swap(options, index, index + 1)">↓</UiButton>
        <UiButton size="sm" variant="ghost" :aria-label="`Удалить вариант ${index + 1}`" @click="options.splice(index, 1)">✕</UiButton>
      </div>
    </div>
    <UiButton v-if="canRestructure()" size="sm" class="justify-self-start" @click="add">Добавить вариант</UiButton>
  </div>
</template>

