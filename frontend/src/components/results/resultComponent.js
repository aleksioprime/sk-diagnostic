import DomikiResult from './DomikiResult.vue'
import MotivationResult from './MotivationResult.vue'
import SummaryResult from './SummaryResult.vue'

/** Карточка результата выбирается по его форме, а не по коду: так копия методики выглядит как исходная. */
export function resultComponent(data) {
  const result = data?.result || {}
  if ('level' in result) return MotivationResult
  if ('vegetative_coefficient' in result) return DomikiResult
  return SummaryResult
}
