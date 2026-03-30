/**
 * Поддержка методики «Домики» на фронтенде.
 *
 * Определяет Tailwind-классы цветов, функции для
 * автоопределения режима вопроса (ranking / scale)
 * и состояния ранжирования.
 */

const DOMIKI_CODES = ['domiki_emotion', 'domiki_orekhova']
const COLOR_CODES = ['blue', 'green', 'red', 'yellow', 'violet', 'brown', 'gray', 'black']

const COLOR_META = {
  blue: {
    tileClass: 'border-sky-300 bg-sky-100 text-sky-950 hover:border-sky-400',
    badgeClass: 'bg-sky-200 text-sky-900',
  },
  green: {
    tileClass: 'border-emerald-300 bg-emerald-100 text-emerald-950 hover:border-emerald-400',
    badgeClass: 'bg-emerald-200 text-emerald-900',
  },
  red: {
    tileClass: 'border-rose-300 bg-rose-100 text-rose-950 hover:border-rose-400',
    badgeClass: 'bg-rose-200 text-rose-900',
  },
  yellow: {
    tileClass: 'border-amber-300 bg-amber-100 text-amber-950 hover:border-amber-400',
    badgeClass: 'bg-amber-200 text-amber-900',
  },
  violet: {
    tileClass: 'border-fuchsia-300 bg-fuchsia-100 text-fuchsia-950 hover:border-fuchsia-400',
    badgeClass: 'bg-fuchsia-200 text-fuchsia-900',
  },
  brown: {
    tileClass: 'border-amber-700 bg-amber-900/15 text-amber-950 hover:border-amber-800',
    badgeClass: 'bg-amber-900/20 text-amber-950',
  },
  gray: {
    tileClass: 'border-slate-300 bg-slate-100 text-slate-950 hover:border-slate-400',
    badgeClass: 'bg-slate-200 text-slate-900',
  },
  black: {
    tileClass: 'border-slate-800 bg-slate-900 text-white hover:border-black',
    badgeClass: 'bg-slate-800 text-white',
  },
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
  return COLOR_META[normalizeCode(colorCode)] || {
    tileClass: 'border-slate-200 bg-white text-slate-900 hover:border-slate-300',
    badgeClass: 'bg-slate-100 text-slate-700',
  }
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
