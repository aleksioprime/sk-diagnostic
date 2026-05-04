const SUMMARY_PALETTE = [
  'FF0F766E',
  'FFC2410C',
  'FF0369A1',
  'FF15803D',
  'FF7C3AED',
  'FFB45309',
  'FF0F172A',
  'FFDC2626',
  'FF0891B2',
  'FF4D7C0F',
]

function safeSheetName(name, fallback = 'Лист') {
  const cleaned = String(name || fallback)
    .replace(/[\\/*?:\[\]]/g, ' ')
    .trim()
    .slice(0, 31)
  return cleaned || fallback
}

function toPercentNumber(value) {
  const numeric = Number(value)
  if (Number.isNaN(numeric)) return 0
  return Math.max(0, Math.min(100, numeric))
}

function styleTitleRow(worksheet, rowNumber, columnsCount, title) {
  worksheet.mergeCells(rowNumber, 1, rowNumber, columnsCount)
  const titleCell = worksheet.getCell(rowNumber, 1)
  titleCell.value = title
  titleCell.font = { bold: true, size: 14, color: { argb: 'FF0F172A' } }
  titleCell.alignment = { vertical: 'middle', horizontal: 'left' }
}

function styleHeaderRow(worksheet, rowNumber, headers) {
  headers.forEach((header, index) => {
    const cell = worksheet.getCell(rowNumber, index + 1)
    cell.value = header
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
  cell.alignment = { vertical: 'middle', horizontal: align }
  cell.border = {
    top: { style: 'thin', color: { argb: 'FFE2E8F0' } },
    left: { style: 'thin', color: { argb: 'FFE2E8F0' } },
    bottom: { style: 'thin', color: { argb: 'FFE2E8F0' } },
    right: { style: 'thin', color: { argb: 'FFE2E8F0' } },
  }
}

function createDistributionSheet(workbook, table, total) {
  const sheetName = safeSheetName(table.title)
  const worksheet = workbook.addWorksheet(sheetName)
  const headers = ['Результат', 'Кол-во', '%']

  worksheet.columns = [
    { width: 34 },
    { width: 12 },
    { width: 10 },
  ]

  styleTitleRow(worksheet, 1, headers.length, `${table.title} · Выбрано прохождений: ${total}`)
  styleHeaderRow(worksheet, 3, headers)

  table.items.forEach((item, index) => {
    const rowNumber = 4 + index
    const percent = toPercentNumber(item.percent)

    const labelCell = worksheet.getCell(rowNumber, 1)
    labelCell.value = item.label
    styleDataCell(labelCell)

    const countCell = worksheet.getCell(rowNumber, 2)
    countCell.value = Number(item.count) || 0
    styleDataCell(countCell, 'center')

    const percentCell = worksheet.getCell(rowNumber, 3)
    percentCell.value = percent / 100
    percentCell.numFmt = '0.0%'
    styleDataCell(percentCell, 'center')

    percentCell.font = { color: { argb: SUMMARY_PALETTE[index % SUMMARY_PALETTE.length] } }
  })
}

function createDomainsSheet(workbook, table, total) {
  const worksheet = workbook.addWorksheet(safeSheetName(table.title))
  const headers = ['Сфера', 'Без отклонений (чел)', 'Без отклонений (%)', 'Обратить внимание (чел)', 'Обратить внимание (%)']

  worksheet.columns = [
    { width: 34 },
    { width: 20 },
    { width: 19 },
    { width: 22 },
    { width: 20 },
  ]

  styleTitleRow(worksheet, 1, headers.length, `${table.title} · Выбрано прохождений: ${total}`)
  styleHeaderRow(worksheet, 3, headers)

  table.items.forEach((item, index) => {
    const rowNumber = 4 + index
    const okPercent = toPercentNumber(item.okPercent)
    const attentionPercent = toPercentNumber(item.attentionPercent)

    const labelCell = worksheet.getCell(rowNumber, 1)
    labelCell.value = item.label
    styleDataCell(labelCell)

    const okCountCell = worksheet.getCell(rowNumber, 2)
    okCountCell.value = Number(item.okCount) || 0
    styleDataCell(okCountCell, 'center')

    const okPercentCell = worksheet.getCell(rowNumber, 3)
    okPercentCell.value = okPercent / 100
    okPercentCell.numFmt = '0.0%'
    styleDataCell(okPercentCell, 'center')

    const attentionCountCell = worksheet.getCell(rowNumber, 4)
    attentionCountCell.value = Number(item.attentionCount) || 0
    styleDataCell(attentionCountCell, 'center')

    const attentionPercentCell = worksheet.getCell(rowNumber, 5)
    attentionPercentCell.value = attentionPercent / 100
    attentionPercentCell.numFmt = '0.0%'
    styleDataCell(attentionPercentCell, 'center')

    okPercentCell.font = { color: { argb: 'FF15803D' } }
    attentionPercentCell.font = { color: { argb: 'FFC2410C' } }
  })
}

export function renderDomikiSummaryWorkbook(workbook, summaryContent) {
  const total = summaryContent?.total || 0
  const tables = summaryContent?.tables || []

  tables.forEach((table) => {
    if (table?.id === 'domains_mood') {
      createDomainsSheet(workbook, table, total)
      return
    }
    createDistributionSheet(workbook, table, total)
  })
}
