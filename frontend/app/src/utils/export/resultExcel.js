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

function buildExportSpec(rows, templateId) {
  const builder = RESULTS_SPEC_BUILDERS[templateId]
  if (!builder) {
    throw new Error('Экспорт для данного типа диагностики пока не поддерживается.')
  }
  return builder(rows)
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
  const workbook = await createWorkbook()
  const worksheet = workbook.addWorksheet(spec.sheetName)
  worksheet.columns = spec.columns.map((column) => ({ key: column.key, width: column.width }))

  worksheet.mergeCells(1, 1, 1, spec.columns.length)
  const titleCell = worksheet.getCell(1, 1)
  titleCell.value = `Экспорт результатов (${spec.sheetName}) · Выбрано: ${rows.length}`
  titleCell.font = { bold: true, size: 14, color: { argb: 'FF0F172A' } }
  titleCell.alignment = { vertical: 'middle', horizontal: 'left' }

  styleHeaderRow(worksheet, 3, spec.columns)

  spec.data.forEach((entry, index) => {
    const rowNumber = 4 + index
    spec.columns.forEach((column, columnIndex) => {
      const cell = worksheet.getCell(rowNumber, columnIndex + 1)
      cell.value = entry[column.key] == null ? '—' : entry[column.key]
      styleDataCell(cell, columnIndex === 0 ? 'left' : 'center')
    })
  })

  await downloadWorkbook({ workbook, filePrefix: spec.filePrefix })
}
