import axios from 'axios'
import router from '../router'
import logger from '../utils/logger'

/**
 * Сериализатор параметров для NocoBase API.
 * Массивы передаются в формате brackets: key[]=v1&key[]=v2.
 */
function serializeParams(params) {
  const parts = []
  for (const [key, value] of Object.entries(params)) {
    if (value === null || value === undefined) continue
    if (Array.isArray(value)) {
      value.forEach((v) => {
        parts.push(`${encodeURIComponent(key)}[]=${encodeURIComponent(v)}`)
      })
    } else {
      parts.push(`${encodeURIComponent(key)}=${encodeURIComponent(value)}`)
    }
  }
  return parts.join('&')
}

const api = axios.create({
  baseURL: '/api',
  headers: { 'Content-Type': 'application/json' },
  paramsSerializer: { serialize: serializeParams },
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  logger.debug(`→ ${config.method?.toUpperCase()} ${config.baseURL}${config.url}`, config.params || '')
  return config
})

api.interceptors.response.use(
  (response) => {
    logger.debug(`← ${response.status} ${response.config.url}`)
    return response
  },
  (error) => {
    const status = error.response?.status
    const body = error.response?.data
    logger.error(`← ${status} ${error.config?.url}`, body)
    if (status === 401) {
      localStorage.removeItem('token')
      router.push('/login')
    }
    return Promise.reject(error)
  },
)

export default api
