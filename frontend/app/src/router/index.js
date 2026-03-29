import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import LoginView from '../views/LoginView.vue'
import AssignedTestsView from '../views/AssignedTestsView.vue'
import AttemptView from '../views/AttemptView.vue'
import ResultsListView from '../views/ResultsListView.vue'
import TestResultsView from '../views/TestResultsView.vue'
import ResultDetailView from '../views/ResultDetailView.vue'
import AnonAttemptView from '../views/AnonAttemptView.vue'

const NoAccessView = {
  template: `
    <section class="flex min-h-[50vh] w-full items-center justify-center">
      <div class="glass-panel max-w-lg p-10 text-center">
        <p class="mb-2 text-sm font-semibold uppercase tracking-[0.24em] text-slate-400">Доступ ограничен</p>
        <h1 class="mb-3 text-3xl font-semibold text-slate-900">Доступ к результатам закрыт</h1>
        <p class="text-sm leading-6 text-slate-500">Эта часть приложения доступна только специалистам.</p>
      </div>
    </section>
  `,
}

const routes = [
  { path: '/login', name: 'login', component: LoginView, meta: { public: true } },
  { path: '/no-access', name: 'no-access', component: NoAccessView, meta: { public: true } },
  { path: '/t/:token', name: 'anon-attempt', component: AnonAttemptView, props: true, meta: { public: true } },
  { path: '/', name: 'assigned-tests', component: AssignedTestsView },
  { path: '/attempts/:attemptId', name: 'attempt', component: AttemptView, props: true },
  { path: '/results', name: 'results', component: ResultsListView, meta: { requiresPsycho: true } },
  { path: '/results/tests/:testId', name: 'results-test', component: TestResultsView, props: true, meta: { requiresPsycho: true } },
  { path: '/results/tests/:testId/attempts/:attemptId', name: 'result-detail', component: ResultDetailView, props: true, meta: { requiresPsycho: true } },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach(async (to) => {
  const auth = useAuthStore()

  if (to.name === 'login' && auth.isAuthenticated) {
    return { name: 'assigned-tests' }
  }

  if (to.meta.public) return true
  if (!auth.isAuthenticated) return { name: 'login' }

  if (!auth.user) {
    try {
      await auth.fetchUser()
    } catch {
      await auth.logout()
      return { name: 'login' }
    }
  }

  if (to.meta.requiresPsycho && !auth.isPsycho) {
    return { name: 'no-access' }
  }

  return true
})

export default router
