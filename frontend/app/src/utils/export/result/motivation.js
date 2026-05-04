import { baseColumns, buildBaseRow } from './base'

function motivationColumns() {
  return [
    ...baseColumns(),
    { key: 'level', title: 'Уровень', width: 12 },
    { key: 'total_score', title: 'Суммарный балл', width: 16 },
    { key: 'level_description', title: 'Описание уровня', width: 54 },
    { key: 'interpretation', title: 'Интерпретация', width: 54 },
    { key: 'pa', title: 'ПА', width: 10 },
    { key: 'md', title: 'МД', width: 10 },
    { key: 'anxiety', title: 'Тревожность', width: 14 },
    { key: 'anger', title: 'Гнев', width: 10 },
    { key: 'pa_level', title: 'ПА (уровень нормы)', width: 20 },
    { key: 'md_level', title: 'МД (уровень нормы)', width: 20 },
    { key: 'anxiety_level', title: 'Тревожность (уровень нормы)', width: 28 },
    { key: 'anger_level', title: 'Гнев (уровень нормы)', width: 20 },
  ]
}

function scaleByCode(scales = [], code) {
  return scales.find((item) => item.code === code) || {}
}

function buildMotivationRow(row) {
  const json = row.resultRecord?.json_results || {}
  const result = json.result || {}
  const scales = json.scales || []
  const pa = scaleByCode(scales, 'cognitive_activity')
  const md = scaleByCode(scales, 'achievement_motivation')
  const anxiety = scaleByCode(scales, 'anxiety')
  const anger = scaleByCode(scales, 'anger')

  return {
    ...buildBaseRow(row),
    level: result.level || '—',
    total_score: result.total_score ?? '—',
    level_description: result.level_description || '—',
    interpretation: result.interpretation || '—',
    pa: pa.value ?? '—',
    md: md.value ?? '—',
    anxiety: anxiety.value ?? '—',
    anger: anger.value ?? '—',
    pa_level: pa.level_label || pa.level || '—',
    md_level: md.level_label || md.level || '—',
    anxiety_level: anxiety.level_label || anxiety.level || '—',
    anger_level: anger.level_label || anger.level || '—',
  }
}

export function buildMotivationResultsSpec(rows) {
  return {
    filePrefix: 'diagnostic-motivation-selected',
    sheetName: 'Мотивация',
    columns: motivationColumns(),
    data: rows.map(buildMotivationRow),
  }
}
