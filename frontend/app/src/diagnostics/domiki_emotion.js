/**
 * Поддержка методики «Домики» на фронтенде.
 *
 * Определяет Tailwind-классы цветов, функции для
 * автоопределения режима вопроса (ranking / scale)
 * и состояния ранжирования.
 */

const DOMIKI_CODES = ['domiki_emotion_primary', 'domiki_emotion_middle', 'domiki_orekhova']
const COLOR_CODES = ['blue', 'green', 'red', 'yellow', 'violet', 'brown', 'gray', 'black']

const COLOR_META = {
  blue:   { hex: '#203e69' },
  green:  { hex: '#007f79' },
  red:    { hex: '#ff4325' },
  yellow: { hex: '#fce435' },
  violet: { hex: '#d13e7f' },
  brown:  { hex: '#886753' },
  gray:   { hex: '#bfcac6' },
  black:  { hex: '#272c30' },
}

function normalizeCode(value) {
  return typeof value === 'string' ? value.toLowerCase() : ''
}

function isColorCode(value) {
  return COLOR_CODES.includes(normalizeCode(value))
}

function hasDomikiColorScaleOptions(question) {
  const values = (question?.scaleOptions || []).map((option) => normalizeCode(option.value)).filter(Boolean)
  return values.length >= 6 && values.every(isColorCode)
}

function hasDomikiColorRankingOptions(question) {
  const values = (question?.options || []).map((option) => normalizeCode(option.value)).filter(Boolean)
  return values.length >= 6 && values.every(isColorCode)
}

export function isDomikiEmotionTest(testCode) {
  return DOMIKI_CODES.includes(normalizeCode(testCode))
}

export function getDiagnosticQuestionMode(testCode, question) {
  if (!question) return null
  const isDomikiByCode = isDomikiEmotionTest(testCode)
  const isDomikiScale = hasDomikiColorScaleOptions(question)
  const isDomikiRanking = hasDomikiColorRankingOptions(question)

  if ((isDomikiByCode || isDomikiRanking) && question.question_type === 'ranking') {
    return 'domiki-ranking'
  }

  if ((isDomikiByCode || isDomikiScale) && question.question_type === 'scale' && question.scaleOptions?.length) {
    return 'domiki-scale'
  }

  return null
}

export function getDomikiColorMeta(colorCode) {
  return COLOR_META[normalizeCode(colorCode)] || { hex: null }
}

export function getDomikiRankingState(question) {
  const selectedIds = question.rankingItems?.length
    ? question.rankingItems
      .slice()
      .sort((left, right) => (left.rank ?? 999) - (right.rank ?? 999))
      .map((item) => item.option_id)
    : []

  const optionsById = Object.fromEntries((question.options || []).map((option) => [option.id, option]))

  const selectedOptions = selectedIds
    .map((id) => optionsById[id])
    .filter(Boolean)

  const remainingOptions = (question.options || []).filter((option) => !selectedIds.includes(option.id))

  return {
    selectedIds,
    selectedOptions,
    remainingOptions,
    totalCount: (question.options || []).length,
  }
}
