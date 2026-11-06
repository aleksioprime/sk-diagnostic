<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { onBeforeRouteLeave, RouterLink, useRoute } from 'vue-router'
import { getAdminTest, getSampleInput, patchAdminTest, runTestScript, saveTestScript } from '@/api/diagnostic'
import { errorMessage, SkeletonPage, UiBadge, UiButton } from 'sk-ui'
import CodeEditor from '@/components/CodeEditor.vue'
import TestTabs from '@/components/tests/TestTabs.vue'

const LIVE_DELAY_MS = 600

const STARTER = `// data — ответы ученика и его данные: они показаны справа, в «Входных данных».
// Верните объект с результатом. Поле summary попадёт в таблицу класса и выгрузку Excel.

const total = data.answers.reduce(
  (sum, answer) => sum + (answer.scale_option?.score ?? answer.selected_option?.score ?? 0),
  0,
)

console.log('Ответов:', data.answers.length)

return {
  total,
  summary: {
    'Сумма баллов': total,
  },
}
`

const route = useRoute()
const test = ref(null)
const loadError = ref('')
const script = ref('')
const savedScript = ref('')
const input = ref('')
const live = ref(true)
const mode = ref('random')
const run = ref(null)
const running = ref(false)
const saving = ref(false)
const notice = ref('')
const error = ref('')

const isBuiltin = computed(() => test.value?.scoring === 'builtin')
const dirty = computed(() => !isBuiltin.value && script.value.trim() !== savedScript.value.trim())

const inputError = computed(() => {
  try {
    JSON.parse(input.value)
    return ''
  } catch (e) {
    return e.message
  }
})
const outputText = computed(() => (run.value?.output ? JSON.stringify(run.value.output, null, 2) : ''))
const summaryRows = computed(() => Object.entries(run.value?.summary || {}))

let timer = null
let lastRequest = 0

async function loadSample() {
  error.value = ''
  try {
    input.value = JSON.stringify(await getSampleInput(route.params.id, mode.value), null, 2)
  } catch (e) {
    error.value = errorMessage(e)
  }
}

async function check() {
  clearTimeout(timer)
  if (inputError.value) return
  const request = ++lastRequest
  running.value = true
  try {
    const answer = await runTestScript(route.params.id, isBuiltin.value ? null : script.value, JSON.parse(input.value))
    if (request === lastRequest) run.value = answer
  } catch (e) {
    if (request === lastRequest) run.value = { error: errorMessage(e), logs: [], output: null }
  } finally {
    if (request === lastRequest) running.value = false
  }
}

function schedule() {
  clearTimeout(timer)
  if (live.value && test.value) timer = setTimeout(check, LIVE_DELAY_MS)
}

watch([script, input, live], schedule)
watch(mode, async () => {
  await loadSample()
})

onMounted(async () => {
  try {
    test.value = await getAdminTest(route.params.id)
    savedScript.value = test.value.scoring_script || ''
    script.value = savedScript.value || (isBuiltin.value ? '' : STARTER)
    await loadSample()
    await check()
  } catch (e) {
    loadError.value = errorMessage(e)
  }
})

async function save() {
  saving.value = true
  error.value = ''
  notice.value = ''
  try {
    test.value = await saveTestScript(route.params.id, script.value)
    savedScript.value = test.value.scoring_script || ''
    notice.value = test.value.assignments_count
      ? 'Сохранено. Новые попытки считаются этим скриптом. Уже завершённые пересчитываются в выдаче: кнопка «Пересчитать».'
      : 'Сохранено.'
  } catch (e) {
    error.value = errorMessage(e)
  } finally {
    saving.value = false
  }
}

async function toggleBirthDate(event) {
  error.value = ''
  try {
    test.value = await patchAdminTest(route.params.id, { needs_birth_date: event.target.checked })
  } catch (e) {
    event.target.checked = test.value.needs_birth_date
    error.value = errorMessage(e)
  }
}

function warnOnClose(event) {
  if (dirty.value) event.preventDefault()
}
window.addEventListener('beforeunload', warnOnClose)
onBeforeUnmount(() => {
  clearTimeout(timer)
  window.removeEventListener('beforeunload', warnOnClose)
})
onBeforeRouteLeave(() => !dirty.value || window.confirm('Скрипт не сохранён. Уйти со страницы?'))
</script>

<template>
  <p v-if="loadError" role="alert" class="rounded-control bg-red-100 px-3 py-2 text-sm text-red-800">{{ loadError }}</p>
  <SkeletonPage v-else-if="!test" />
  <div v-else>
    <RouterLink :to="{ name: 'admin-tests' }" class="text-sm text-brand-700 hover:underline">← Все методики</RouterLink>
    <h1 class="mt-2 text-2xl font-bold">{{ test.title }}</h1>
    <p class="mt-1 text-sm text-ink-muted">
      <code>{{ test.code }}</code> · вопросов: {{ test.questions_count }} · выдач: {{ test.assignments_count }}
    </p>
    <TestTabs :id="route.params.id" class="mt-4" />
    <label class="mt-4 flex items-center gap-2 text-sm">
      <input type="checkbox" :checked="test.needs_birth_date" :disabled="isBuiltin" @change="toggleBirthDate" />
      Перед началом ученик указывает дату рождения (нужен возраст)
    </label>

    <p v-if="error" role="alert" class="mt-4 rounded-control bg-red-100 px-3 py-2 text-sm text-red-800">{{ error }}</p>
    <p v-if="notice" role="status" class="mt-4 rounded-control bg-brand-50 px-3 py-2 text-sm text-brand-700">{{ notice }}</p>

    <div class="mt-6 grid gap-4 lg:grid-cols-2">
      <!-- Скрипт -->
      <section class="grid min-w-0 grid-rows-[auto_34rem] gap-2">
        <div class="flex min-h-8 flex-wrap items-center gap-2">
          <h2 class="font-semibold">Скрипт расчёта (JavaScript)</h2>
          <UiBadge v-if="dirty" tone="warning">Не сохранён</UiBadge>
          <UiButton v-if="!isBuiltin" class="ml-auto" size="sm" variant="primary" :loading="saving" :disabled="!dirty" @click="save">Сохранить</UiButton>
        </div>
        <div v-if="isBuiltin" class="rounded-control border border-line bg-canvas p-4 text-sm">
          <p class="font-medium">Расчёт этой методики встроен в приложение</p>
          <p class="mt-2 text-ink-muted">
            Он написан на Python и сверен с результатами из NocoBase, поэтому заменить его скриптом нельзя. Справа можно посмотреть,
            какие данные он получает и что возвращает. Чтобы изменить расчёт, сделайте копию методики: у неё будет такой же скрипт на JavaScript.
          </p>
        </div>
        <CodeEditor v-else v-model="script" label="Скрипт расчёта" />
      </section>

      <!-- Входные данные -->
      <section class="grid min-w-0 grid-rows-[auto_34rem] gap-2">
        <div class="flex min-h-8 flex-wrap items-center gap-2">
          <h2 class="font-semibold">Входные данные (data)</h2>
          <select v-model="mode" aria-label="Какие ответы подставить" class="ml-auto h-8 rounded-control border border-line bg-surface px-2 text-sm">
            <option value="random">Случайные ответы</option>
            <option value="first">Первые варианты</option>
            <option value="last">Последние варианты</option>
          </select>
          <UiButton size="sm" @click="loadSample">Сгенерировать</UiButton>
        </div>
        <CodeEditor v-model="input" language="json" label="Входные данные расчёта" />
      </section>
    </div>
    <p v-if="inputError" role="alert" class="mt-2 text-sm text-red-800">Входные данные — не JSON: {{ inputError }}</p>

    <!-- Результат -->
    <section class="mt-6" aria-live="polite">
      <div class="flex flex-wrap items-center gap-3">
        <h2 class="font-semibold">Результат</h2>
        <label class="flex items-center gap-2 text-sm">
          <input v-model="live" type="checkbox" />
          Проверять на лету
        </label>
        <UiButton size="sm" :loading="running" :disabled="!!inputError" @click="check">Запустить</UiButton>
        <span v-if="run?.duration_ms" class="text-sm text-ink-muted">{{ run.duration_ms }} мс</span>
      </div>

      <div v-if="run?.error" role="alert" class="mt-3 rounded-control bg-red-100 px-3 py-2 text-sm text-red-800">
        <span v-if="run.line" class="font-semibold">Строка {{ run.line }}: </span>{{ run.error }}
      </div>

      <div class="mt-3 grid gap-4 lg:grid-cols-2">
        <div class="min-w-0">
          <h3 class="text-sm font-medium text-ink-muted">Что вернул скрипт</h3>
          <pre class="mt-1 max-h-96 overflow-auto rounded-control border border-line bg-surface p-3 text-xs">{{ outputText || '—' }}</pre>
        </div>
        <div class="grid min-w-0 content-start gap-4">
          <div>
            <h3 class="text-sm font-medium text-ink-muted">Колонки в таблице класса и Excel</h3>
            <dl v-if="summaryRows.length" class="mt-1 grid gap-x-4 gap-y-1 rounded-control border border-line bg-surface p-3 text-sm sm:grid-cols-[minmax(8rem,auto)_1fr]">
              <template v-for="[key, value] in summaryRows" :key="key">
                <dt class="text-ink-muted">{{ key }}</dt>
                <dd class="break-words">{{ value }}</dd>
              </template>
            </dl>
            <p v-else class="mt-1 text-sm text-ink-muted">Нет. Чтобы они появились, верните в результате поле <code>summary</code>.</p>
          </div>
          <div>
            <h3 class="text-sm font-medium text-ink-muted">Вывод console.log</h3>
            <pre class="mt-1 max-h-48 overflow-auto rounded-control border border-line bg-surface p-3 text-xs">{{ run?.logs?.join('\n') || '—' }}</pre>
          </div>
        </div>
      </div>
    </section>
  </div>
</template>
