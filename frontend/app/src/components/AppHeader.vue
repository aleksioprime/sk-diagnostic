<script setup>
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const props = defineProps({
  appTitle: {
    type: String,
    default: 'Диагностика SK',
  },
})

const auth = useAuthStore()
const route = useRoute()
const router = useRouter()
const menuOpen = ref(false)

const navItems = computed(() => {
  const items = [{ label: 'Мои тесты', to: { name: 'assigned-tests' } }]
  if (auth.isPsycho) {
    items.push({ label: 'Результаты', to: { name: 'results' } })
  }
  return items
})

function isActive(item) {
  const targetName = item.to.name
  if (targetName === 'assigned-tests' && route.name === 'attempt') return true
  if (targetName === 'results' && route.name === 'result-detail') return true
  return route.name === targetName
}

async function logout() {
  menuOpen.value = false
  await auth.logout()
  router.push({ name: 'login' })
}
</script>

<template>
  <header class="sticky top-0 z-20 border-b border-white/40 bg-white/75 backdrop-blur-xl">
    <div class="mx-auto flex w-full max-w-7xl items-center justify-between gap-4 px-4 py-3 sm:px-6 lg:px-8">
      <div class="flex min-w-0 items-center gap-6">
        <router-link :to="{ name: 'assigned-tests' }" class="flex items-center gap-3 no-underline">
          <div class="flex h-11 w-11 items-center justify-center rounded-2xl bg-primary/12 text-primary shadow-[inset_0_0_0_1px_rgba(15,118,110,0.12)]">
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
              <path stroke-linecap="round" stroke-linejoin="round" d="M8 7h8M8 12h8M8 17h5" />
              <path stroke-linecap="round" stroke-linejoin="round" d="M5 3h14a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2Z" />
            </svg>
          </div>
          <div class="min-w-0">
            <p class="truncate text-sm font-semibold uppercase tracking-[0.24em] text-slate-400">SK Diagnostics</p>
            <p class="truncate text-base font-semibold text-slate-900">{{ props.appTitle }}</p>
          </div>
        </router-link>

        <nav class="hidden items-center gap-2 md:flex">
          <router-link
            v-for="item in navItems"
            :key="item.label"
            :to="item.to"
            class="rounded-full px-4 py-2 text-sm font-medium no-underline transition"
            :class="isActive(item) ? 'bg-primary text-white shadow-[0_10px_24px_rgba(15,118,110,0.18)]' : 'text-slate-600 hover:bg-slate-100'"
          >
            {{ item.label }}
          </router-link>
        </nav>
      </div>

      <div class="relative">
        <button
          class="flex cursor-pointer items-center gap-3 rounded-full border border-slate-200/70 bg-white/80 px-3 py-2 text-left shadow-sm transition hover:bg-white"
          @click="menuOpen = !menuOpen"
        >
          <div class="flex h-9 w-9 items-center justify-center rounded-full bg-slate-900 text-sm font-semibold text-white">
            {{ auth.displayName.slice(0, 1).toUpperCase() }}
          </div>
          <div class="hidden sm:block">
            <div class="max-w-44 truncate text-sm font-semibold text-slate-900">{{ auth.displayName }}</div>
            <div class="text-xs text-slate-500">{{ auth.isPsycho ? 'Специалист' : 'Личный кабинет' }}</div>
          </div>
        </button>

        <div v-if="menuOpen" class="fixed inset-0 z-10" @click="menuOpen = false"></div>
        <div v-if="menuOpen" class="absolute right-0 z-20 mt-3 w-72 overflow-hidden rounded-3xl border border-white/60 bg-white/92 p-2 shadow-[0_18px_55px_rgba(15,23,42,0.14)] backdrop-blur-xl">
          <div class="rounded-2xl bg-slate-50/80 px-4 py-3">
            <div class="text-sm font-semibold text-slate-900">{{ auth.displayName }}</div>
            <div class="mt-1 text-xs text-slate-500">{{ auth.isPsycho ? 'Доступ к результатам открыт' : 'Доступ к тестам открыт' }}</div>
          </div>

          <div class="flex flex-col gap-1 px-1 py-2 md:hidden">
            <router-link
              v-for="item in navItems"
              :key="item.label"
              :to="item.to"
              class="rounded-2xl px-3 py-2 text-sm no-underline transition"
              :class="isActive(item) ? 'bg-primary/10 text-primary' : 'text-slate-600 hover:bg-slate-100'"
              @click="menuOpen = false"
            >
              {{ item.label }}
            </router-link>
          </div>

          <button class="mt-1 flex w-full cursor-pointer items-center justify-between rounded-2xl border-none bg-transparent px-4 py-3 text-sm font-medium text-red-600 transition hover:bg-red-50" @click="logout">
            Выйти
            <svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
              <path stroke-linecap="round" stroke-linejoin="round" d="M15.75 9V5.25A2.25 2.25 0 0 0 13.5 3h-6a2.25 2.25 0 0 0-2.25 2.25v13.5A2.25 2.25 0 0 0 7.5 21h6a2.25 2.25 0 0 0 2.25-2.25V15" />
              <path stroke-linecap="round" stroke-linejoin="round" d="M18 12H9m0 0 3-3m-3 3 3 3" />
            </svg>
          </button>
        </div>
      </div>
    </div>
  </header>
</template>
