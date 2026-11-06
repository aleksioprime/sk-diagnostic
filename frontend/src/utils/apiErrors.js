import { errorMessage } from 'sk-ui'

const LOCATION_SKIP = new Set(['body', 'test'])

/** Ошибка API. Для файла методики — что именно не так и где: иначе исправить файл вслепую трудно. */
export function detailedError(error) {
  const detail = error?.response?.data?.detail
  if (!Array.isArray(detail)) return errorMessage(error)
  return detail
    .slice(0, 5)
    .map((item) => {
      const place = (item.loc || []).filter((part) => !LOCATION_SKIP.has(part)).join('.')
      const message = String(item.msg || '').replace(/^Value error, /, '')
      return place ? `${place}: ${message}` : message
    })
    .join('\n')
}
