import { createRouter, createWebHistory } from 'vue-router'
import { setUnauthorizedHandler } from '@/api/http'
import AppLayout from '@/layouts/AppLayout.vue'
import { useAuthStore } from '@/stores/auth'

export const routes = [
  { path: '/login', name: 'login', component: () => import('@/views/auth/LoginView.vue'), meta: { public: true } },
  {
    path: '/auth/magic',
    name: 'magic-link',
    component: () => import('@/views/auth/MagicLinkView.vue'),
    meta: { public: true },
  },
  {
    path: '/my/:id',
    name: 'attempt-pass',
    component: () => import('@/views/my/AttemptPassView.vue'),
    props: true,
  },
  {
    path: '/',
    component: AppLayout,
    children: [
      { path: '', name: 'home', component: { render: () => null } },
      { path: 'my', name: 'my', component: () => import('@/views/my/MyAttemptsView.vue') },
      {
        path: 'assignments',
        name: 'assignments',
        component: () => import('@/views/assignments/AssignmentListView.vue'),
        meta: { psychologist: true },
      },
      {
        path: 'assignments/:id',
        name: 'assignment',
        component: () => import('@/views/assignments/AssignmentView.vue'),
        props: true,
        meta: { psychologist: true },
      },
      {
        path: 'attempts/:id',
        name: 'attempt',
        component: () => import('@/views/attempts/AttemptResultView.vue'),
        props: true,
        meta: { psychologist: true },
      },
      { path: 'profile', name: 'profile', component: () => import('@/views/profile/ProfileView.vue') },
      {
        path: 'admin/people',
        name: 'admin-people',
        component: () => import('@/views/admin/PeopleView.vue'),
        meta: { admin: true },
      },
      {
        path: 'admin/psychologists',
        name: 'admin-psychologists',
        component: () => import('@/views/admin/PsychologistsView.vue'),
        meta: { admin: true },
      },
    ],
  },
  { path: '/:pathMatch(.*)*', redirect: { name: 'home' } },
]

export const router = createRouter({
  history: createWebHistory(),
  routes,
})

/** Проверка доступа к маршруту. Вынесена отдельно, чтобы её можно было протестировать. */
export function resolveAccess(to, auth) {
  if (to.meta.public) return true
  if (!auth.isAuthenticated) return { name: 'login', query: { next: to.fullPath } }
  if (to.name === 'home') return { name: auth.isPsychologist ? 'assignments' : 'my' }
  if (to.meta.psychologist && !auth.isPsychologist) return { name: 'my' }
  if (to.meta.admin && !auth.isAdmin) return { name: 'home' }
  return true
}

router.beforeEach(async (to) => {
  const auth = useAuthStore()
  await auth.load()
  return resolveAccess(to, auth)
})

setUnauthorizedHandler(() => {
  const auth = useAuthStore()
  auth.setUser(null)
  const current = router.currentRoute.value
  // До завершения первой навигации маршрута ещё нет: доступ решит beforeEach
  if (!current.matched.length || current.meta.public) return
  router.push({ name: 'login', query: { next: current.fullPath } })
})
