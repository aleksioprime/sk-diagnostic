import { baseColumns, buildBaseRow } from './base'

function normalizeDomainStatusLabel(domain) {
  const status = String(domain?.status || '').toLowerCase()
  if (status === 'attention') return 'Обратить внимание'
  if (status === 'ok') return 'Отклонений нет'

  const statusLabel = String(domain?.status_label || '').trim()
  if (statusLabel) {
    const lowered = statusLabel.toLowerCase()
    if (lowered.includes('вним')) return 'Обратить внимание'
    if (lowered.includes('отклон')) return 'Отклонений нет'
    return statusLabel
  }

  return '—'
}

function collectDomainColumns(rows) {
  const columns = []
  const seen = new Set()

  rows.forEach((row) => {
    const domains = row.resultRecord?.json_results?.domains || []
    domains.forEach((domain) => {
      if (!domain || domain.code === 'custom_house') return

      const domainCode = String(domain.code || '').trim()
      const domainTitle = String(domain.title || '').trim()
      const signature = domainCode || domainTitle
      if (!signature || seen.has(signature)) return

      seen.add(signature)
      columns.push({
        key: `domain_${domainCode || columns.length + 1}`,
        code: domainCode || null,
        title: domainTitle || `Сфера #${columns.length + 1}`,
      })
    })
  })

  return columns
}

function hasCustomHouse(rows) {
  return rows.some((row) => {
    const domains = row.resultRecord?.json_results?.domains || []
    return domains.some((domain) => domain?.code === 'custom_house')
  })
}

function domikiColumns(domainColumns = [], includeCustomHouse = false) {
  return [
    ...baseColumns(),
    { key: 'vk_value', title: 'ВК', width: 12 },
    { key: 'work_capacity', title: 'Работоспособность', width: 26 },
    { key: 'emotional_background', title: 'Эмоциональный фон', width: 26 },
    { key: 'self_esteem', title: 'Самооценка', width: 20 },
    { key: 'school_relation', title: 'Отношение к школе', width: 26 },
    ...domainColumns.map((column) => ({
      key: column.key,
      title: column.title,
      width: 24,
    })),
    ...(includeCustomHouse
      ? [
        { key: 'custom_house_color', title: 'Собственный домик: цвет', width: 28 },
        { key: 'custom_house_description', title: 'Собственный домик: описание', width: 48 },
      ]
      : []),
  ]
}

function buildDomikiRow(row, domainColumns = [], includeCustomHouse = false) {
  const json = row.resultRecord?.json_results || {}
  const result = json.result || {}
  const domains = json.domains || []
  const customHouse = domains.find((item) => item.code === 'custom_house') || {}
  const domainValues = Object.fromEntries(domainColumns.map((column) => [column.key, '—']))

  domainColumns.forEach((column) => {
    const matchedDomain = column.code
      ? domains.find((domain) => domain?.code === column.code)
      : domains.find((domain) => String(domain?.title || '').trim() === column.title)

    if (matchedDomain) {
      domainValues[column.key] = normalizeDomainStatusLabel(matchedDomain)
    }
  })

  return {
    ...buildBaseRow(row),
    vk_value: result.vegetative_coefficient?.value ?? '—',
    work_capacity: result.vegetative_coefficient?.label || '—',
    emotional_background: result.emotional_background?.label || result.emotional_background?.title || '—',
    self_esteem: result.self_esteem?.label || '—',
    school_relation: result.school_relation?.label || '—',
    ...domainValues,
    ...(includeCustomHouse
      ? {
        custom_house_color: customHouse.color_title || '—',
        custom_house_description: customHouse.description || '—',
      }
      : {}),
  }
}

export function buildDomikiResultsSpec(rows) {
  const domainColumns = collectDomainColumns(rows)
  const includeCustomHouse = hasCustomHouse(rows)

  return {
    filePrefix: 'diagnostic-domiki-selected',
    sheetName: 'Домики',
    columns: domikiColumns(domainColumns, includeCustomHouse),
    data: rows.map((row) => buildDomikiRow(row, domainColumns, includeCustomHouse)),
  }
}
