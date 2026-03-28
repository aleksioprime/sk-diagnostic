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
    <div class="grid w-full max-w-6xl gap-6 lg:grid-cols-[1.05fr_0.95fr]">
      <div class="glass-panel hidden p-10 lg:block">
        <p class="mb-3 text-sm font-semibold uppercase tracking-[0.26em] text-primary">Диагностика</p>
        <h1 class="max-w-lg text-5xl leading-[1.02] font-semibold tracking-tight text-slate-900">
          Прохождение тестов и просмотр результатов в одном интерфейсе.
        </h1>
        <p class="mt-6 max-w-xl text-base leading-7 text-slate-600">
          Здесь можно проходить назначенные тесты, а специалисты могут просматривать и анализировать готовые результаты.
        </p>
        <div class="mt-8 grid gap-4 sm:grid-cols-2">
          <div class="rounded-[28px] border border-white/70 bg-white/82 p-5">
            <div class="text-sm font-semibold text-slate-900">Для пользователя</div>
            <div class="mt-2 text-sm leading-6 text-slate-600">Все назначенные тесты собраны в одном месте, чтобы к ним можно было вернуться в любой момент.</div>
          </div>
          <div class="rounded-[28px] border border-white/70 bg-white/82 p-5">
            <div class="text-sm font-semibold text-slate-900">Для специалиста</div>
            <div class="mt-2 text-sm leading-6 text-slate-600">Результаты доступны в удобной таблице и на отдельной странице с подробной расшифровкой.</div>
          </div>
        </div>
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
