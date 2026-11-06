<script setup>
import { computed } from 'vue'
import { RouterLink, RouterView, useRouter } from 'vue-router'
import { BrandMark, OverflowNav, SchoolFooter, UiButton } from 'sk-ui'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const router = useRouter()

const links = computed(() => [
  ...(auth.isPsychologist ? [{ to: { name: 'assignments' }, label: 'Диагностики' }] : []),
  { to: { name: 'my' }, label: 'Мои диагностики' },
  ...(auth.isAdmin
    ? [
        { to: { name: 'admin-tests' }, label: 'Методики' },
        { to: { name: 'admin-psychologists' }, label: 'Психологи' },
        { to: { name: 'admin-people' }, label: 'Люди' },
      ]
    : []),
  { to: { name: 'profile' }, label: 'Профиль' },
])

async function logout() {
  await auth.logout()
  await router.push({ name: 'login' })
}
</script>

<template>
  <div class="flex min-h-dvh flex-col">
    <header class="sticky top-0 z-10 border-b border-line bg-surface/90 backdrop-blur print:hidden">
      <div class="mx-auto flex h-14 max-w-6xl items-center gap-4 px-4">
        <RouterLink :to="{ name: 'home' }" class="shrink-0">
          <BrandMark />
        </RouterLink>
        <OverflowNav :links="links" />
        <div class="flex shrink-0 items-center gap-3 text-sm">
          <RouterLink
            :to="{ name: 'profile' }"
            class="hidden max-w-48 truncate text-ink-muted hover:text-ink md:inline"
            title="Профиль и пароль"
          >
            {{ auth.displayName }}
          </RouterLink>
          <UiButton size="sm" variant="ghost" @click="logout">Выйти</UiButton>
        </div>
      </div>
    </header>
    <main class="mx-auto w-full max-w-6xl flex-1 px-4 py-8">
      <RouterView />
    </main>
    <SchoolFooter />
  </div>
</template>
