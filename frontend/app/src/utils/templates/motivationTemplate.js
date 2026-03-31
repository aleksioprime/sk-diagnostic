import { personDisplayName } from '../format'

export const motivationTemplate = {
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
        title: 'Контекст прохождения',
        items: [
          { label: 'Тест', value: attempt?.test?.title || '—' },
          { label: 'Пользователь', value: personDisplayName(attempt?.person, attempt?.person_id) },
          { label: 'Код теста', value: json.test?.code || attempt?.test?.code || '—' },
          { label: 'ID прохождения', value: attempt?.id || '—' },
        ],
      },
    ]
  },
}
