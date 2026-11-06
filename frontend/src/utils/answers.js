/** Ответ ученика в форме API. */
export const emptyAnswer = () => ({ option_id: null, scale_option_id: null, text: null, number: null, boolean: null, ranking: [] })

export function isAnswered(question, answer) {
  if (!answer) return false
  if (question.question_type === 'ranking') return (answer.ranking || []).length >= (question.min_selections || question.options.length)
  return [answer.option_id, answer.scale_option_id, answer.number, answer.boolean].some((v) => v != null) || !!answer.text?.trim()
}
