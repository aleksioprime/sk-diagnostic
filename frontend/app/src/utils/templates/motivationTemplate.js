import { personDisplayName } from '../format'

export const motivationTemplate = {
  id: 'motivation_learning',
  aliases: ['motivation'],

  getTableColumns() {
    return [
      {
        key: 'level',
        label: 'Уровень',
        value: (row) => row.resultRecord?.json_results?.result?.level || '—',
      },
      {
        key: 'total_score',
        label: 'Сумма',
        value: (row) => row.resultRecord?.json_results?.result?.total_score ?? '—',
      },
      {
        key: 'cognitive_activity',
        label: 'ПА',
        value: (row) => row.resultRecord?.json_results?.scales?.find((item) => item.code === 'cognitive_activity')?.value ?? '—',
      },
      {
        key: 'achievement_motivation',
        label: 'МД',
        value: (row) => row.resultRecord?.json_results?.scales?.find((item) => item.code === 'achievement_motivation')?.value ?? '—',
      },
      {
        key: 'anxiety',
        label: 'Тревожность',
        value: (row) => row.resultRecord?.json_results?.scales?.find((item) => item.code === 'anxiety')?.value ?? '—',
      },
      {
        key: 'anger',
        label: 'Гнев',
        value: (row) => row.resultRecord?.json_results?.scales?.find((item) => item.code === 'anger')?.value ?? '—',
      },
    ]
  },

  buildHero({ attempt, resultRecord }) {
    const json = resultRecord?.json_results || {}
    return {
      eyebrow: attempt?.test?.title || 'Диагностика мотивации',
      title: json.student?.name || personDisplayName(attempt?.person, attempt?.person_id),
    }
  },

  buildSections({ attempt, resultRecord }) {
    const json = resultRecord?.json_results || {}
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
          { key: 'level_label', label: 'Уровень нормы' },
        ],
        rows: scales.map((item) => ({
          title: item.title,
          value: item.value,
          level_label: item.level_label || item.level || '—',
        })),
      },
    ]
  },

  buildGroupSummary(_rows) {
    return { stub: 'Сводная информация по мотивационному тесту в разработке.' }
  },
}
