import { baseColumns, buildBaseRow } from './base'

function domikiColumns() {
  return [
    ...baseColumns(),
    { key: 'vk_value', title: 'ВК', width: 12 },
    { key: 'work_capacity', title: 'Работоспособность', width: 26 },
    { key: 'emotional_background', title: 'Эмоциональный фон', width: 26 },
    { key: 'self_esteem', title: 'Самооценка', width: 20 },
    { key: 'school_relation', title: 'Отношение к школе', width: 26 },
    { key: 'custom_house_color', title: 'Собственный домик: цвет', width: 28 },
    { key: 'custom_house_description', title: 'Собственный домик: описание', width: 48 },
  ]
}

function buildDomikiRow(row) {
  const json = row.resultRecord?.json_results || {}
  const result = json.result || {}
  const domains = json.domains || []
  const customHouse = domains.find((item) => item.code === 'custom_house') || {}

  return {
    ...buildBaseRow(row),
    vk_value: result.vegetative_coefficient?.value ?? '—',
    work_capacity: result.vegetative_coefficient?.label || '—',
    emotional_background: result.emotional_background?.label || result.emotional_background?.title || '—',
    self_esteem: result.self_esteem?.label || '—',
    school_relation: result.school_relation?.label || '—',
    custom_house_color: customHouse.color_title || '—',
    custom_house_description: customHouse.description || '—',
  }
}

export function buildDomikiResultsSpec(rows) {
  return {
    filePrefix: 'diagnostic-domiki-selected',
    sheetName: 'Домики',
    columns: domikiColumns(),
    data: rows.map(buildDomikiRow),
  }
}
