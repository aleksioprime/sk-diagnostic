/** Цвета методики «Домики» (О. А. Орехова): оттенки как в бланке методики. */
export const COLOR_HEX = {
  blue: '#203e69',
  green: '#007f79',
  red: '#ff4325',
  yellow: '#fce435',
  violet: '#d13e7f',
  brown: '#886753',
  gray: '#bfcac6',
  black: '#272c30',
}

export const isColor = (value) => Object.hasOwn(COLOR_HEX, (value || '').toLowerCase())

/** Вопрос с цветами вместо подписей: все варианты — цвета методики. */
export function isColorQuestion(question) {
  const values = question.question_type === 'ranking' ? question.options : question.scale_options
  return values.length >= 6 && values.every((item) => isColor(item.value))
}
