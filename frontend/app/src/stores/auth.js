import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import api from '../api'
import logger from '../utils/logger'

const PSYCHO_ROLE = 'psycho'
const ADMIN_ROLE = 'admin'

async function tryLoadPersonByUserId(userId) {
  const filters = [
    { user_id: userId },
    { user: userId },
    { user: { id: userId } },
  ]

  for (const filter of filters) {
    try {
      const { data } = await api.get('/persons:list', {
        params: {
          filter: JSON.stringify(filter),
          pageSize: 1,
        },
      })
      const list = data.data || []
      if (list.length) return list[0]
    } catch (error) {
      logger.debug('fetchPerson skipped filter', filter, error.response?.status)
    }
  }

  return null
}

export const useAuthStore = defineStore('auth', () => {
  const token = ref(localStorage.getItem('token') || '')
  const user = ref(null)
  const person = ref(null)

  const isAuthenticated = computed(() => Boolean(token.value))
  const personId = computed(() => person.value?.id ?? null)
  const roleNames = computed(() => {
    return (user.value?.roles || []).flatMap((role) => [
      role.name?.toLowerCase(),
      role.title?.toLowerCase(),
    ].filter(Boolean))
  })
  const isPsycho = computed(() => {
    return roleNames.value.includes(PSYCHO_ROLE) || roleNames.value.includes(ADMIN_ROLE)
  })
  const displayName = computed(() => {
    const p = person.value
    if (p) {
      return p.short_name || p.full_name || [p.last_name, p.first_name].filter(Boolean).join(' ') || p.email || ''
    }
    return user.value?.nickname || user.value?.username || user.value?.email || `User #${user.value?.id ?? ''}`
  })

  async function login(account, password) {
    const { data } = await api.post('/auth:signIn', { account, password }, {
      headers: { 'X-Authenticator': 'basic' },
    })
    token.value = data.data.token
    localStorage.setItem('token', token.value)
    await fetchUser()
  }

  async function fetchUser() {
    const { data } = await api.get('/auth:check')
    user.value = data.data
    logger.debug('auth:check →', user.value?.id)
    await fetchPerson()
    return user.value
  }

  async function fetchPerson() {
    if (!user.value?.id) return
    try {
      person.value = await tryLoadPersonByUserId(user.value.id)
      logger.debug('person →', person.value?.id, person.value?.short_name)
    } catch (error) {
      logger.error('fetchPerson failed', error.response?.status, error.response?.data)
      person.value = null
    }
  }

  async function logout() {
    try {
      await api.post('/auth:signOut')
    } catch {
      // noop
    }
    token.value = ''
    user.value = null
    person.value = null
    localStorage.removeItem('token')
  }

  return {
    token,
    user,
    person,
    personId,
    roleNames,
    displayName,
    isAuthenticated,
    isPsycho,
    login,
    fetchUser,
    logout,
  }
})
