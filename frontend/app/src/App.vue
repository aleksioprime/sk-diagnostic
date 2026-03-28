<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import AppHeader from './components/AppHeader.vue'

const route = useRoute()
const appTitle = 'Диагностика SK'
const showHeader = computed(() => route.name !== 'login' && route.name !== 'anon-attempt')
</script>

<template>
  <div class="relative min-h-screen overflow-hidden">
    <div class="pointer-events-none absolute inset-0 opacity-80">
      <div class="absolute left-[-10rem] top-[-6rem] h-72 w-72 rounded-full bg-primary/10 blur-3xl"></div>
      <div class="absolute bottom-[-8rem] right-[-8rem] h-80 w-80 rounded-full bg-orange-500/10 blur-3xl"></div>
    </div>

    <div class="relative flex min-h-screen flex-col">
      <AppHeader v-if="showHeader" :app-title="appTitle" />
      <main class="mx-auto flex w-full max-w-7xl flex-1 px-4 py-5 sm:px-6 lg:px-8 lg:py-8">
        <router-view />
      </main>
      <footer class="border-t border-gray-200/70 px-4 py-4 text-center text-xs text-slate-500 sm:px-6">
        Сервисы автоматизации Гимназии Сколково · © 2026 Алексей Семочкин
      </footer>
    </div>
  </div>
</template>
