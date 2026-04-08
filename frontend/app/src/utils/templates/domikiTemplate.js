import { personDisplayName } from '../format'

function statusTone(status) {
  if (status === 'attention') return 'warning'
  return null
}

function toPercent(value, total) {
  if (!total) return 0
  return Math.round((value / total) * 1000) / 10
}

function normalizeLabel(value) {
  if (typeof value === 'string' && value.trim()) return value.trim()
  return 'Нет данных'
}

function buildDistribution(rows, config) {
  const counts = new Map()

  rows.forEach((row) => {
    const label = normalizeLabel(config.pickLabel(row))
    counts.set(label, (counts.get(label) || 0) + 1)
  })

  return {
    id: config.id,
    title: config.title,
    chartType: config.chartType,
    items: [...counts.entries()]
      .map(([label, count]) => ({
        label,
        count,
        percent: toPercent(count, rows.length),
      }))
      .sort((a, b) => b.count - a.count),
  }
}

function buildDomainsAttentionDistribution(rows) {
  const domainStats = new Map()

  rows.forEach((row) => {
    const domains = row.resultRecord?.json_results?.domains || []

    domains.forEach((domain) => {
      if (domain?.code === 'custom_house') return

      const title = normalizeLabel(domain?.title)
      const next = domainStats.get(title) || { total: 0, attention: 0 }
      next.total += 1

      const isAttention = domain?.status === 'attention'
        || String(domain?.status_label || '').toLowerCase().includes('вним')

      if (isAttention) {
        next.attention += 1
      }

      domainStats.set(title, next)
    })
  })

  return {
    id: 'domains_mood',
    title: 'Настроение (домики)',
    chartType: 'stackedBar',
    items: [...domainStats.entries()]
      .map(([title, stats]) => {
        const attentionCount = stats.attention
        const okCount = Math.max(stats.total - stats.attention, 0)

        return {
          label: title,
          total: stats.total,
          okCount,
          attentionCount,
          okPercent: toPercent(okCount, stats.total),
          attentionPercent: toPercent(attentionCount, stats.total),
        }
      })
      .sort((a, b) => b.attentionPercent - a.attentionPercent),
  }
}

export const domikiTemplate = {
  id: 'domiki_emotion',
  aliases: ['domiki'],

  getTableColumns() {
    return [
      {
        key: 'vk',
        label: 'ВК',
        value: (row) => row.resultRecord?.json_results?.result?.vegetative_coefficient?.value ?? '—',
      },
      {
        key: 'vk_level',
        label: 'Работоспособность',
        value: (row) => row.resultRecord?.json_results?.result?.vegetative_coefficient?.label || '—',
      },
      {
        key: 'emotional_bg',
        label: 'Эмоц. фон',
        value: (row) => row.resultRecord?.json_results?.result?.emotional_background?.label || '—',
      },
      {
        key: 'self_esteem',
        label: 'Самооценка',
        value: (row) => row.resultRecord?.json_results?.result?.self_esteem?.label || '—',
      },
      {
        key: 'school_relation',
        label: 'Школа',
        value: (row) => row.resultRecord?.json_results?.result?.school_relation?.label || '—',
      },
    ]
  },

  buildHero({ attempt, resultRecord }) {
    const json = resultRecord?.json_results || {}
    const result = json.result || {}
    const vk = result.vegetative_coefficient || {}
    const bg = result.emotional_background || {}

    return {
      eyebrow: attempt?.test?.title || 'Проективная методика «Домики»',
      title: json.student?.name || personDisplayName(attempt?.person, attempt?.person_id),
      subtitle: vk.interpretation || bg.interpretation || 'Интерпретация не получена',
      badges: [
        { label: `ВК: ${vk.value ?? '—'} — ${vk.label || '?'}`, tone: 'primary' },
        { label: `ЭФ: ${bg.value ?? '—'} (${bg.label || '?'})`, tone: bg.level === 'positive_background' ? 'accent' : bg.level === 'negative_background' ? 'danger' : 'primary' },
        { label: `Самооценка: ${result.self_esteem?.label || '—'}`, tone: 'primary' },
      ],
    }
  },

  buildSections({ attempt, resultRecord }) {
    const json = resultRecord?.json_results || {}
    const student = json.student || {}
    const result = json.result || {}
    const domains = json.domains || []
    const vk = result.vegetative_coefficient || {}
    const bg = result.emotional_background || {}

    const sections = []

    // 1. Ключевые показатели
    sections.push({
      kind: 'stats',
      title: 'Ключевые показатели',
      items: [
        { label: 'Вегетативный коэффициент', value: vk.value ?? '—' },
        { label: 'Работоспособность', value: vk.label || '—' },
        { label: 'Эмоциональный фон', value: bg.title || '—' },
        { label: 'Самооценка', value: result.self_esteem?.label || '—' },
      ],
    })

    // 2. Интерпретация ВК
    if (vk.interpretation) {
      sections.push({
        kind: 'text',
        title: `Работоспособность: ${vk.label || ''}`,
        text: vk.interpretation,
      })
    }

    // 3. Интерпретация эмоционального фона
    if (bg.interpretation) {
      sections.push({
        kind: 'text',
        title: `Эмоциональный фон: ${bg.title || ''}`,
        text: `Суммарное отклонение от аутогенной нормы: ${bg.interpretation} (${bg.value ?? '—'})`,
      })
    }

    // 4. Отношение к школе
    if (result.school_relation) {
      sections.push({
        kind: 'text',
        title: `Отношение к школе: ${result.school_relation.label || ''}`,
        text: result.school_relation.interpretation || 'Нет интерпретации',
      })
    }

    // 5. Домики — таблица сфер
    if (domains.length) {
      sections.push({
        kind: 'table',
        title: 'Настроение (домики)',
        columns: [
          { key: 'title', label: 'Сфера' },
          { key: 'color_title', label: 'Цвет' },
          { key: 'status_label', label: 'Статус' },
        ],
        rows: domains.map((d) => ({
          title: d.title,
          color_title: d.color_title,
          status_label: d.status_label,
          _tone: statusTone(d.status),
        })),
      })
    }

    // 6. Собственный домик
    const customHouse = domains.find((d) => d.code === 'custom_house')
    if (customHouse?.description) {
      sections.push({
        kind: 'keyValue',
        title: 'Собственный домик',
        items: [
          { label: 'Цвет', value: customHouse.color_title || '—' },
          { label: 'Описание ребёнка', value: customHouse.description },
        ],
      })
    }

    return sections
  },

  buildGroupSummary(rows) {
    if (!rows?.length) {
      return { stub: 'Недостаточно данных для сводной информации.' }
    }

    return {
      kind: 'domiki-distributions',
      total: rows.length,
      tables: [
        buildDistribution(rows, {
          id: 'work_capacity',
          title: 'Работоспособность',
          chartType: 'pie',
          pickLabel: (row) => row.resultRecord?.json_results?.result?.vegetative_coefficient?.label,
        }),
        buildDistribution(rows, {
          id: 'emotional_background',
          title: 'Эмоциональный фон',
          chartType: 'pie',
          pickLabel: (row) => {
            const bg = row.resultRecord?.json_results?.result?.emotional_background
            return bg?.label || bg?.title
          },
        }),
        buildDistribution(rows, {
          id: 'self_esteem',
          title: 'Самооценка',
          chartType: 'pie',
          pickLabel: (row) => row.resultRecord?.json_results?.result?.self_esteem?.label,
        }),
        buildDistribution(rows, {
          id: 'school_relation',
          title: 'Отношение обучающихся',
          chartType: 'pie',
          pickLabel: (row) => row.resultRecord?.json_results?.result?.school_relation?.label,
        }),
        buildDomainsAttentionDistribution(rows),
      ],
    }
  },
}
