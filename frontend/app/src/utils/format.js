/**
 * Форматирование дат, длительностей, статусов и прочих значений для UI.
 */

/** Полная дата со временем (русская локаль). */
export function formatDateTime(value) {
  if (!value) return '—'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '—'
  return new Intl.DateTimeFormat('ru-RU', {
    day: '2-digit',
    month: 'long',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(date)
}

/** Краткая дата (DD.MM.YYYY). */
export function formatShortDate(value) {
  if (!value) return '—'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '—'
  return new Intl.DateTimeFormat('ru-RU', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
  }).format(date)
}

/** Человекочитаемая продолжительность в секундах → «3 мин 42 сек». */
export function formatDuration(seconds) {
  if (seconds == null || Number.isNaN(Number(seconds))) return '—'
  const totalSeconds = Math.max(0, Math.round(Number(seconds)))
  const hours = Math.floor(totalSeconds / 3600)
  const minutes = Math.floor((totalSeconds % 3600) / 60)
  const restSeconds = totalSeconds % 60

  if (hours) return `${hours} ч ${minutes} мин`
  if (minutes) return `${minutes} мин ${restSeconds} сек`
  return `${restSeconds} сек`
}

/** Метаданные статуса попытки: метка и CSS-класс. */
export function getAttemptStatusMeta(status) {
  const normalized = status || 'assigned'
  const map = {
    assigned: { label: 'Выдан', className: 'bg-slate-100 text-slate-600 whitespace-nowrap' },
    in_progress: { label: 'В работе', className: 'bg-primary/10 text-primary whitespace-nowrap' },
    started: { label: 'Начат', className: 'bg-primary/10 text-primary whitespace-nowrap' },
    submitted: { label: 'Отправлен', className: 'bg-emerald-100 text-emerald-700 whitespace-nowrap' },
    completed: { label: 'Обработан', className: 'bg-emerald-100 text-emerald-700 whitespace-nowrap' },
    checking: { label: 'В расчете', className: 'bg-amber-100 text-amber-700 whitespace-nowrap' },
    error: { label: 'Ошибка', className: 'bg-red-100 text-red-700 whitespace-nowrap' },
  }

  return map[normalized] || { label: normalized, className: 'bg-slate-100 text-slate-600 whitespace-nowrap' }
}

/** Метаданные статуса результата: метка и CSS-класс. */
export function getResultStatusMeta(status) {
  const normalized = status || 'pending'
  const map = {
    pending: { label: 'Ожидает', className: 'bg-slate-100 text-slate-600 whitespace-nowrap' },
    processing: { label: 'Рассчитывается', className: 'bg-amber-100 text-amber-700 whitespace-nowrap' },
    success: { label: 'Готов', className: 'bg-emerald-100 text-emerald-700 whitespace-nowrap' },
    error: { label: 'Ошибка', className: 'bg-red-100 text-red-700 whitespace-nowrap' },
  }

  return map[normalized] || { label: normalized, className: 'bg-slate-100 text-slate-600 whitespace-nowrap' }
}

/** Отображаемое имя пользователя из объекта person. */
export function personDisplayName(person, fallbackId = null) {
  if (!person) return fallbackId != null ? `#${fallbackId}` : '—'
  return person.short_name || person.full_name || [person.last_name, person.first_name].filter(Boolean).join(' ') || person.email || person.nickname || person.username || (fallbackId != null ? `#${fallbackId}` : '—')
}

/** Проверка на null / undefined / пустую строку. */
export function isNil(value) {
  return value === null || value === undefined || value === ''
}

/** Превратить любое значение в строку для отображения в UI. */
export function stringifyValue(value) {
  if (value === null || value === undefined || value === '') return '—'
  if (typeof value === 'boolean') return value ? 'Да' : 'Нет'
  if (Array.isArray(value)) {
    const parts = value.map((item) => stringifyValue(item)).filter((item) => item !== '—')
    return parts.length ? parts.join(', ') : '—'
  }
  if (typeof value === 'object') return JSON.stringify(value, null, 2)
  return String(value)
}
