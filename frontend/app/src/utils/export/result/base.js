import { formatDateTime, personDisplayName } from '../../format'

export function baseColumns() {
  return [
    { key: 'student_name', title: 'Тестируемый', width: 34 },
    { key: 'attempt_status', title: 'Статус попытки', width: 20 },
    { key: 'result_status', title: 'Статус результата', width: 20 },
    { key: 'submitted_at', title: 'Отправлен', width: 24 },
  ]
}

export function buildBaseRow(row) {
  return {
    student_name: row.resultRecord?.json_results?.student?.name || personDisplayName(row.attempt.person, row.attempt.person_id),
    attempt_status: row.attempt.attemptStatus?.label || '—',
    result_status: row.attempt.resultStatus?.label || 'Нет результата',
    submitted_at: formatDateTime(row.attempt.submitted_at),
  }
}
