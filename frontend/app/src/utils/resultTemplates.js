/**
 * Реестр шаблонов отображения результатов диагностик.
 *
 * Каждый шаблон определён в отдельном файле в ./templates/
 * и подключается здесь. generic — шаблон по умолчанию.
 */

import { stringifyValue } from './format'
import { domikiTemplate } from './templates/domikiTemplate'
import { motivationTemplate } from './templates/motivationTemplate'

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
      title: json.student?.name || '',
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

const templates = [domikiTemplate, motivationTemplate, genericTemplate]

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
