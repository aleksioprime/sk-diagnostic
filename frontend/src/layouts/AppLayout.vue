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
        <OverflowNav :links="links">
          <template #burger-footer>
            <RouterLink :to="{ name: 'profile' }" class="grid rounded-control px-3 py-2.5 hover:bg-brand-50" active-class="bg-brand-100!" title="Профиль и пароль">
              <span class="truncate font-medium text-ink">{{ auth.displayName }}</span>
              <span class="text-xs text-ink-muted">Профиль и пароль</span>
            </RouterLink>
            <UiButton variant="ghost" class="w-full justify-start! px-3!" @click="logout">Выйти</UiButton>
          </template>
        </OverflowNav>
        <div class="hidden shrink-0 items-center gap-3 text-sm sm:flex">
          <RouterLink
            :to="{ name: 'profile' }"
            class="max-w-32 truncate text-ink-muted hover:text-ink lg:max-w-48"
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
