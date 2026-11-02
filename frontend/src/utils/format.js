export const STATUS_TITLES = { assigned: 'Не начата', in_progress: 'Начата', submitted: 'Завершена' }
export const STATUS_TONES = { assigned: 'neutral', in_progress: 'warning', submitted: 'success' }

export const formatDate = (value) =>
  value ? new Date(value).toLocaleDateString('ru-RU', { day: 'numeric', month: 'long', year: 'numeric' }) : '—'

export const formatDateTime = (value) =>
  value ? new Date(value).toLocaleString('ru-RU', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' }) : '—'

export function formatDuration(seconds) {
  if (seconds == null) return '—'
  const minutes = Math.round(seconds / 60)
  return minutes < 1 ? 'меньше минуты' : `${minutes} мин`
}
