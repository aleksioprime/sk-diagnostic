import { renderDomikiSummaryWorkbook } from './summary/domiki'

const SUMMARY_EXPORTERS = {
  'domiki-distributions': {
    defaultFilePrefix: 'domiki-svod',
    render: renderDomikiSummaryWorkbook,
  },
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

export function canExportSummary(summaryContent) {
  const kind = summaryContent?.kind
  return Boolean(kind && SUMMARY_EXPORTERS[kind])
}

export async function exportSummaryByKindToExcel({ summaryContent, filePrefix }) {
  const kind = summaryContent?.kind
  const exporter = kind ? SUMMARY_EXPORTERS[kind] : null
  if (!exporter) {
    throw new Error('Экспорт для этой сводной информации пока не реализован.')
  }

  const workbook = await createWorkbook()
  exporter.render(workbook, summaryContent)

  await downloadWorkbook({
    workbook,
    filePrefix: filePrefix || exporter.defaultFilePrefix,
  })
}
