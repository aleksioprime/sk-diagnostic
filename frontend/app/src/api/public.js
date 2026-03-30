/**
 * Axios-инстанс для запросов к BFF-бэкенду (публичное API).
 *
 * Используется для анонимного прохождения тестов по ссылке —
 * авторизация не требуется, запросы идут через /backend → FastAPI.
 */

import axios from 'axios'
import logger from '../utils/logger'

const rawBaseUrl = import.meta.env.VITE_BACKEND_API_URL || '/backend'
const baseURL = rawBaseUrl.endsWith('/') ? rawBaseUrl.slice(0, -1) : rawBaseUrl

const publicApi = axios.create({
  baseURL,
})

// ─── Логирование запросов/ответов ─────────────────────────────────────────

publicApi.interceptors.request.use((config) => {
  logger.debug(`→ [public] ${config.method?.toUpperCase()} ${config.baseURL}${config.url}`, config.params || '')
  return config
})

publicApi.interceptors.response.use(
  (response) => {
    logger.debug(`← [public] ${response.status} ${response.config.url}`)
    return response
  },
  (error) => {
    const status = error.response?.status
    const body = error.response?.data
    logger.error(`← [public] ${status} ${error.config?.url}`, body)
    return Promise.reject(error)
  },
)

export default publicApi
