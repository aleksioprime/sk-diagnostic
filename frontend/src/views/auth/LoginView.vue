<script setup>
/**
 * Вход только через SkolStream: ученики и сотрудники гимназии там уже есть.
 * Вход по паролю — запасной, для администратора (пароль задаётся в самом сервисе,
 * пароль от SkolStream здесь не подходит); он спрятан за ссылкой внизу.
 */
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { fetchProviders, loginWithPassword, skolstreamLoginUrl } from '@/api/auth'
import { BrandMark, errorMessage, SchoolFooter, UiButton, UiCard, UiInput } from 'sk-ui'
import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const next = computed(() => (typeof route.query.next === 'string' ? route.query.next : '/'))

const providers = ref({ skolstream: true })
const showPassword = ref(false)
const email = ref('')
const password = ref('')
const sending = ref(false)
const error = ref(typeof route.query.error === 'string' ? route.query.error : '')

onMounted(async () => {
  try {
    providers.value = await fetchProviders()
  } catch {
    // без списка способов показываем кнопку SkolStream
  }
  // Если вход через SkolStream не настроен, запасной вход — единственный
  if (!providers.value.skolstream) showPassword.value = true
})

async function submitPassword() {
  error.value = ''
  if (!email.value.trim() || !password.value) {
    error.value = 'Введите почту и пароль'
    return
  }
  sending.value = true
  try {
    const result = await loginWithPassword(email.value.trim(), password.value, next.value)
    await auth.load(true)
    await router.replace(result.next || '/')
  } catch (e) {
    error.value = errorMessage(e)
  } finally {
    sending.value = false
  }
}
</script>

<template>
  <div class="flex min-h-dvh flex-col">
    <main class="grid flex-1 place-items-center px-4 py-10">
      <div class="w-full max-w-sm">
        <BrandMark class="mb-8" size="lg" />

        <UiCard class="p-6">
          <h1 class="text-xl font-bold">Вход</h1>
          <p class="mt-1 text-sm text-ink-muted">Для учеников и психологической службы гимназии.</p>

          <p v-if="error" role="alert" class="mt-4 rounded-control bg-red-100 px-3 py-2 text-sm text-red-800">{{ error }}</p>

          <template v-if="providers.skolstream">
            <a
              :href="skolstreamLoginUrl(next)"
              class="mt-5 flex h-11 items-center justify-center rounded-control bg-brand-600 font-medium text-white hover:bg-brand-700"
            >
              Войти через SkolStream
            </a>
            <p class="mt-2 text-center text-xs text-ink-muted">Логин и пароль — те же, что в SkolStream</p>
          </template>

          <form v-if="showPassword" class="mt-6 grid gap-4 border-t border-line pt-5" novalidate @submit.prevent="submitPassword">
            <p class="text-sm text-ink-muted">Вход администратора по паролю этого сервиса. Пароль от SkolStream здесь не подходит.</p>
            <UiInput v-model="email" label="Электронная почта" type="email" autocomplete="username" />
            <UiInput v-model="password" label="Пароль" type="password" autocomplete="current-password" />
            <UiButton type="submit" variant="primary" :loading="sending">Войти</UiButton>
          </form>
        </UiCard>

        <button
          v-if="providers.skolstream && !showPassword"
          type="button"
          class="mt-4 w-full text-center text-xs text-ink-muted hover:text-ink"
          @click="showPassword = true"
        >
          Вход для администратора
        </button>
      </div>
    </main>
    <SchoolFooter />
  </div>
</template>
