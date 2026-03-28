import { stringifyValue, personDisplayName } from './format'

function primitiveEntries(source = {}) {
  return Object.entries(source).filter(([, value]) => {
    return value === null || ['string', 'number', 'boolean'].includes(typeof value)
  })
}

function prettifyPath(path) {
  return path
    .split('.')
    .map((chunk) => chunk.replaceAll('_', ' '))
    .map((chunk) => chunk.charAt(0).toUpperCase() + chunk.slice(1))
    .join(' / ')
}

function flattenJson(value, prefix = '', rows = []) {
  if (Array.isArray(value)) {
    value.forEach((item, index) => flattenJson(item, prefix ? `${prefix}[${index}]` : `[${index}]`, rows))
    return rows
  }

  if (value && typeof value === 'object') {
    for (const [key, nested] of Object.entries(value)) {
      flattenJson(nested, prefix ? `${prefix}.${key}` : key, rows)
    }
    return rows
  }

  rows.push({
    path: prefix || 'value',
    label: prettifyPath(prefix || 'value'),
    value: stringifyValue(value),
    type: Array.isArray(value) ? 'array' : typeof value,
  })
  return rows
}

function detectTemplateId(context) {
  const test = context?.test || {}
  const resultRecord = context?.resultRecord || {}
  const json = resultRecord?.json || {}

  return (
    resultRecord?.page_template_id ||
    resultRecord?.template_page_id ||
    json?.meta?.page_template_id ||
    test?.result_page_template_id ||
    test?.template_page_id ||
    test?.code ||
    'generic'
  )
}

function detectTableTemplateId(context) {
  const test = context?.test || {}
  const resultRecord = context?.resultRecord || {}
  const json = resultRecord?.json || {}

  return (
    resultRecord?.table_template_id ||
    resultRecord?.template_table_id ||
    json?.meta?.table_template_id ||
    test?.result_table_template_id ||
    test?.template_table_id ||
    test?.code ||
    'generic'
  )
}

function genericSummary(row) {
  const resultJson = row.resultRecord?.json || {}
  const summaryEntries = primitiveEntries(resultJson.result || {})
  if (summaryEntries.length) {
    return summaryEntries.map(([key, value]) => `${prettifyPath(key)}: ${stringifyValue(value)}`).join(' · ')
  }
  return 'Без вычисленного summary'
}

const genericTemplate = {
  id: 'generic',
  getTableColumns() {
    return [
      {
        key: 'summary',
        label: 'Сводка',
        value: (row) => genericSummary(row),
      },
    ]
  },
  buildHero({ attempt, resultRecord }) {
    const json = resultRecord?.json || {}
    return {
      eyebrow: attempt?.test?.title || 'Результат диагностики',
      title: json.student?.name || personDisplayName(attempt?.person, attempt?.person_id),
      subtitle: genericSummary({ attempt, resultRecord }),
      badges: [],
    }
  },
  buildSections({ resultRecord }) {
    const json = resultRecord?.json || {}
    return [
      {
        kind: 'table',
        title: 'Основные поля',
        columns: [
          { key: 'label', label: 'Поле' },
          { key: 'value', label: 'Значение' },
        ],
        rows: flattenJson(json),
      },
    ]
  },
}

const motivationTemplate = {
  id: 'motivation_learning',
  aliases: ['motivation'],
  getTableColumns() {
    return [
      {
        key: 'level',
        label: 'Уровень',
        value: (row) => row.resultRecord?.json?.result?.level || '—',
      },
      {
        key: 'total_score',
        label: 'Сумма',
        value: (row) => row.resultRecord?.json?.result?.total_score ?? '—',
      },
      {
        key: 'cognitive_activity',
        label: 'ПА',
        value: (row) => row.resultRecord?.json?.scales?.find((item) => item.code === 'cognitive_activity')?.value ?? '—',
      },
      {
        key: 'achievement_motivation',
        label: 'МД',
        value: (row) => row.resultRecord?.json?.scales?.find((item) => item.code === 'achievement_motivation')?.value ?? '—',
      },
      {
        key: 'anxiety',
        label: 'Тревожность',
        value: (row) => row.resultRecord?.json?.scales?.find((item) => item.code === 'anxiety')?.value ?? '—',
      },
      {
        key: 'anger',
        label: 'Гнев',
        value: (row) => row.resultRecord?.json?.scales?.find((item) => item.code === 'anger')?.value ?? '—',
      },
    ]
  },
  buildHero({ attempt, resultRecord }) {
    const json = resultRecord?.json || {}
    return {
      eyebrow: attempt?.test?.title || 'Диагностика мотивации',
      title: json.student?.name || personDisplayName(attempt?.person, attempt?.person_id),
      subtitle: json.result?.interpretation || 'Интерпретация пока не получена',
      badges: [
        { label: `Уровень ${json.result?.level || '—'}`, tone: 'primary' },
        { label: `Сумма ${json.result?.total_score ?? '—'}`, tone: 'accent' },
      ],
    }
  },
  buildSections({ attempt, resultRecord }) {
    const json = resultRecord?.json || {}
    const student = json.student || {}
    const result = json.result || {}
    const scales = json.scales || []

    return [
      {
        kind: 'stats',
        title: 'Профиль результата',
        items: [
          { label: 'Уровень', value: result.level || '—' },
          { label: 'Суммарный балл', value: result.total_score ?? '—' },
          { label: 'Возраст', value: student.age ?? '—' },
          { label: 'Пол', value: student.gender_label || student.gender || '—' },
        ],
      },
      {
        kind: 'text',
        title: 'Интерпретация',
        text: result.interpretation || 'Нет интерпретации',
      },
      {
        kind: 'table',
        title: 'Шкалы',
        columns: [
          { key: 'title', label: 'Шкала' },
          { key: 'value', label: 'Значение' },
          { key: 'level', label: 'Уровень нормы' },
        ],
        rows: scales.map((item) => ({
          title: item.title,
          value: item.value,
          level: item.level,
        })),
      },
      {
        kind: 'keyValue',
        title: 'Контекст попытки',
        items: [
          { label: 'Тест', value: attempt?.test?.title || '—' },
          { label: 'Пользователь', value: personDisplayName(attempt?.person, attempt?.person_id) },
          { label: 'Код теста', value: json.test?.code || attempt?.test?.code || '—' },
          { label: 'ID попытки', value: attempt?.id || '—' },
        ],
      },
    ]
  },
}

const templates = [motivationTemplate, genericTemplate]

function resolveById(id) {
  return templates.find((template) => {
    return template.id === id || template.aliases?.includes(id)
  }) || genericTemplate
}

export function resolveResultTemplate(context) {
  return resolveById(detectTemplateId(context))
}

export function resolveTableTemplate(context) {
  return resolveById(detectTableTemplateId(context))
}
