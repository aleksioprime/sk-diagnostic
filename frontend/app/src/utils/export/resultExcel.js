import { buildDomikiResultsSpec } from './result/domiki'
import { buildMotivationResultsSpec } from './result/motivation'

const RESULTS_SPEC_BUILDERS = {
  domiki_emotion_primary: buildDomikiResultsSpec,
  motivation_learning: buildMotivationResultsSpec,
}

function getNowSuffix() {
  const now = new Date()
  const yyyy = now.getFullYear()
  const mm = String(now.getMonth() + 1).padStart(2, '0')
  const dd = String(now.getDate()).padStart(2, '0')
  const hh = String(now.getHours()).padStart(2, '0')
  const min = String(now.getMinutes()).padStart(2, '0')
  return `${yyyy}-${mm}-${dd}_${hh}-${min}`
}

function triggerFileDownload(blob, fileName) {
  const link = document.createElement('a')
  const url = URL.createObjectURL(blob)
  link.href = url
  link.download = fileName
  document.body.appendChild(link)
  link.click()
  link.remove()
  setTimeout(() => URL.revokeObjectURL(url), 0)
}

async function createWorkbook() {
  const exceljsModule = await import('exceljs')
  const ExcelJS = exceljsModule.default || exceljsModule
  return new ExcelJS.Workbook()
}

async function downloadWorkbook({ workbook, filePrefix }) {
  const buffer = await workbook.xlsx.writeBuffer()
  const blob = new Blob(
    [buffer],
    { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' },
  )
  triggerFileDownload(blob, `${filePrefix}-${getNowSuffix()}.xlsx`)
}

function styleHeaderRow(worksheet, rowNumber, columns) {
  columns.forEach((column, index) => {
    const cell = worksheet.getCell(rowNumber, index + 1)
    cell.value = column.title
    cell.font = { bold: true, color: { argb: 'FF111827' } }
    cell.fill = {
      type: 'pattern',
      pattern: 'solid',
      fgColor: { argb: 'FFF1F5F9' },
    }
    cell.alignment = { vertical: 'middle', horizontal: 'center', wrapText: true }
    cell.border = {
      top: { style: 'thin', color: { argb: 'FFCBD5E1' } },
      left: { style: 'thin', color: { argb: 'FFCBD5E1' } },
      bottom: { style: 'thin', color: { argb: 'FFCBD5E1' } },
      right: { style: 'thin', color: { argb: 'FFCBD5E1' } },
    }
  })
}

function styleDataCell(cell, align = 'left') {
  cell.alignment = { vertical: 'top', horizontal: align, wrapText: true }
  cell.border = {
    top: { style: 'thin', color: { argb: 'FFE2E8F0' } },
    left: { style: 'thin', color: { argb: 'FFE2E8F0' } },
    bottom: { style: 'thin', color: { argb: 'FFE2E8F0' } },
    right: { style: 'thin', color: { argb: 'FFE2E8F0' } },
  }
}

function styleDomikiDomainStatusCell(cell, value) {
  const normalized = String(value || '').trim().toLowerCase()
  if (normalized === 'отклонений нет') {
    cell.fill = {
      type: 'pattern',
      pattern: 'solid',
      fgColor: { argb: 'FFDCFCE7' },
    }
    cell.font = { color: { argb: 'FF166534' } }
    return
  }

  if (normalized === 'обратить внимание') {
    cell.fill = {
      type: 'pattern',
      pattern: 'solid',
      fgColor: { argb: 'FFFFEDD5' },
    }
    cell.font = { color: { argb: 'FF9A3412' } }
  }
}

function styleMotivationNormLevelCell(cell, value) {
  const normalized = String(value || '').trim().toLowerCase()

  if (normalized === 'высокий' || normalized === 'high') {
    cell.fill = {
      type: 'pattern',
      pattern: 'solid',
      fgColor: { argb: 'FFDCFCE7' },
    }
    cell.font = { color: { argb: 'FF166534' } }
    return
  }

  if (normalized === 'средний' || normalized === 'medium') {
    cell.fill = {
      type: 'pattern',
      pattern: 'solid',
      fgColor: { argb: 'FFFEF3C7' },
    }
    cell.font = { color: { argb: 'FF92400E' } }
    return
  }

  if (normalized === 'низкий' || normalized === 'low') {
    cell.fill = {
      type: 'pattern',
      pattern: 'solid',
      fgColor: { argb: 'FFFEE2E2' },
    }
    cell.font = { color: { argb: 'FF991B1B' } }
  }
}

function buildExportSpec(rows, templateId) {
  const builder = RESULTS_SPEC_BUILDERS[templateId]
  if (!builder) {
    throw new Error('Экспорт для данного типа диагностики пока не поддерживается.')
  }
  return builder(rows)
}

function pickFirstNonEmpty(values = []) {
  return values.find((value) => typeof value === 'string' && value.trim())?.trim() || ''
}

function resolveExportTitle(rows, fallbackTitle) {
  const firstAttempt = rows[0]?.attempt || {}
  const assignment = firstAttempt.test_assignment || {}

  const assignmentTitle = pickFirstNonEmpty([
    assignment.title,
    assignment.name,
    firstAttempt.test_assignment_title,
  ])
  const testTitle = pickFirstNonEmpty([
    assignment?.test?.title,
    assignment.test_title,
    firstAttempt?.test?.title,
  ])

  if (assignmentTitle && testTitle) return `${assignmentTitle} (${testTitle})`
  if (assignmentTitle) return assignmentTitle
  if (testTitle) return testTitle
  return fallbackTitle
}

export async function exportSelectedDiagnosticRowsToExcel({ rows }) {
  if (!rows?.length) {
    throw new Error('Нет выбранных записей для экспорта.')
  }

  const templateId = rows[0]?.template?.id
  if (!rows.every((row) => row?.template?.id === templateId)) {
    throw new Error('Для экспорта выберите записи только одного типа диагностики.')
  }

  const spec = buildExportSpec(rows, templateId)
  const exportColumns = [{ key: 'row_number', title: '№', width: 8 }, ...spec.columns]
  const workbook = await createWorkbook()
  const worksheet = workbook.addWorksheet(spec.sheetName)
  worksheet.columns = exportColumns.map((column) => ({ key: column.key, width: column.width }))

  worksheet.mergeCells(1, 1, 1, exportColumns.length)
  const titleCell = worksheet.getCell(1, 1)
  titleCell.value = resolveExportTitle(rows, spec.sheetName)
  titleCell.font = { bold: true, size: 14, color: { argb: 'FF0F172A' } }
  titleCell.alignment = { vertical: 'middle', horizontal: 'left' }

  styleHeaderRow(worksheet, 3, exportColumns)

  spec.data.forEach((entry, index) => {
    const rowNumber = 4 + index
    exportColumns.forEach((column, columnIndex) => {
      const cell = worksheet.getCell(rowNumber, columnIndex + 1)
      cell.value = column.key === 'row_number'
        ? index + 1
        : (entry[column.key] == null ? '—' : entry[column.key])

      const isMotivationLongText = spec.sheetName === 'Мотивация'
        && ['level_description', 'interpretation'].includes(column.key)
      const horizontalAlign = (column.key === 'student_name' || isMotivationLongText) ? 'left' : 'center'
      styleDataCell(cell, horizontalAlign)

      if (spec.sheetName === 'Домики' && String(column.key).startsWith('domain_')) {
        styleDomikiDomainStatusCell(cell, cell.value)
      }

      if (spec.sheetName === 'Мотивация' && String(column.key).endsWith('_level')) {
        styleMotivationNormLevelCell(cell, cell.value)
      }
    })
  })

  await downloadWorkbook({ workbook, filePrefix: spec.filePrefix })
}
