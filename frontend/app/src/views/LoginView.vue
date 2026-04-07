<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
const router = useRouter()

const account = ref('')
const password = ref('')
const error = ref('')
const loading = ref(false)

async function handleLogin() {
  error.value = ''
  loading.value = true

  try {
    await auth.login(account.value, password.value)
    router.push({ name: 'assigned-tests' })
  } catch (loginError) {
    error.value = loginError.response?.data?.errors?.[0]?.message || 'Не удалось войти. Проверьте логин и пароль.'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <section class="flex w-full items-center justify-center py-8 sm:py-14">
    <div class="w-full max-w-md">
      <div class="mb-6 text-center">
        <p class="text-sm font-semibold uppercase tracking-[0.26em] text-primary">Диагностика SK</p>
      </div>

      <form class="glass-panel w-full p-8 sm:p-10" @submit.prevent="handleLogin">
        <p class="mb-3 text-sm font-semibold uppercase tracking-[0.26em] text-slate-400">Авторизация</p>
        <h2 class="text-3xl font-semibold tracking-tight text-slate-900">Войти в систему</h2>
        <p class="mt-3 text-sm leading-6 text-slate-500">Введите логин и пароль, чтобы открыть назначенные тесты и результаты.</p>

        <div class="mt-8 space-y-4">
          <label class="block">
            <span class="mb-2 block text-sm font-medium text-slate-700">Логин или email</span>
            <input v-model="account" class="field-input" type="text" autocomplete="username" required autofocus />
          </label>

          <label class="block">
            <span class="mb-2 block text-sm font-medium text-slate-700">Пароль</span>
            <input v-model="password" class="field-input" type="password" autocomplete="current-password" required />
          </label>
        </div>

        <p v-if="error" class="mt-4 rounded-2xl bg-red-50 px-4 py-3 text-sm text-red-700">{{ error }}</p>

        <button type="submit" class="primary-button mt-6 w-full" :disabled="loading">
          {{ loading ? 'Входим…' : 'Войти' }}
        </button>
      </form>
    </div>
  </section>
</template>
