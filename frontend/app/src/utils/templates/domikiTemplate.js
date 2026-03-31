import { personDisplayName } from '../format'

const COLOR_HEX = {
  red: '#EF4444',
  yellow: '#EAB308',
  green: '#22C55E',
  blue: '#3B82F6',
  violet: '#A855F7',
  brown: '#92400E',
  gray: '#9CA3AF',
  black: '#1E293B',
}

function colorDot(code) {
  return COLOR_HEX[code] || '#CBD5E1'
}

function statusTone(status) {
  if (status === 'attention') return 'warning'
  return 'success'
}

export const domikiTemplate = {
  id: 'domiki_emotion',
  aliases: ['domiki'],

  getTableColumns() {
    return [
      {
        key: 'vk',
        label: 'ВК',
        value: (row) => row.resultRecord?.json?.result?.vegetative_coefficient?.value ?? '—',
      },
      {
        key: 'vk_level',
        label: 'Работоспособность',
        value: (row) => row.resultRecord?.json?.result?.vegetative_coefficient?.label || '—',
      },
      {
        key: 'emotional_bg',
        label: 'Эмоц. фон',
        value: (row) => row.resultRecord?.json?.result?.emotional_background?.label || '—',
      },
      {
        key: 'self_esteem',
        label: 'Самооценка',
        value: (row) => row.resultRecord?.json?.result?.self_esteem?.label || '—',
      },
      {
        key: 'school_relation',
        label: 'Школа',
        value: (row) => row.resultRecord?.json?.result?.school_relation?.label || '—',
      },
    ]
  },

  buildHero({ attempt, resultRecord }) {
    const json = resultRecord?.json || {}
    const result = json.result || {}
    const vk = result.vegetative_coefficient || {}
    const bg = result.emotional_background || {}

    return {
      eyebrow: attempt?.test?.title || 'Проективная методика «Домики»',
      title: json.student?.name || personDisplayName(attempt?.person, attempt?.person_id),
      subtitle: vk.interpretation || bg.interpretation || 'Интерпретация не получена',
      badges: [
        { label: `ВК ${vk.value ?? '—'}`, tone: 'primary' },
        { label: `Фон: ${bg.label || '—'}`, tone: bg.level === 'positive_background' ? 'accent' : 'primary' },
        { label: `Самооценка: ${result.self_esteem?.label || '—'}`, tone: 'primary' },
      ],
    }
  },

  buildSections({ attempt, resultRecord }) {
    const json = resultRecord?.json || {}
    const student = json.student || {}
    const result = json.result || {}
    const domains = json.domains || []
    const extra = json.extra || {}
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
        title: `Работоспособность — ${vk.label || ''}`,
        text: vk.interpretation,
      })
    }

    // 3. Интерпретация эмоционального фона
    if (bg.interpretation) {
      sections.push({
        kind: 'text',
        title: `Эмоциональный фон — ${bg.title || ''}`,
        text: `Суммарное отклонение от аутогенной нормы: ${bg.value ?? '—'}. ${bg.interpretation}`,
      })
    }

    // 4. Отношение к школе
    if (result.school_relation) {
      sections.push({
        kind: 'text',
        title: `Отношение к школе — ${result.school_relation.label || ''}`,
        text: result.school_relation.interpretation || 'Нет интерпретации',
      })
    }

    // 5. Домики — таблица сфер
    if (domains.length) {
      sections.push({
        kind: 'table',
        title: 'Оценка сфер жизни (домики)',
        columns: [
          { key: 'title', label: 'Сфера' },
          { key: 'color_title', label: 'Цвет' },
          { key: 'status_label', label: 'Статус' },
        ],
        rows: domains.map((d) => ({
          title: d.title,
          color_title: `${d.color_title}`,
          status_label: d.status_label,
        })),
      })
    }

    // 6. Собственный домик
    if (extra.custom_house) {
      sections.push({
        kind: 'keyValue',
        title: 'Собственный домик',
        items: [
          { label: 'Название', value: extra.custom_house.title || '—' },
          { label: 'Цвет', value: extra.custom_house.color_title || '—' },
          { label: 'Описание ребёнка', value: extra.custom_house.description || '—' },
        ],
      })
    }

    // 7. Контекст
    sections.push({
      kind: 'keyValue',
      title: 'Контекст прохождения',
      items: [
        { label: 'Тест', value: attempt?.test?.title || '—' },
        { label: 'Пользователь', value: personDisplayName(attempt?.person, attempt?.person_id) },
        { label: 'Возраст', value: student.age ?? '—' },
        { label: 'Пол', value: student.gender || '—' },
      ],
    })

    return sections
  },
}
