import { describe, expect, it } from 'vitest'
import { isColorQuestion } from '@/utils/colors'

const colors = ['blue', 'green', 'red', 'yellow', 'violet', 'brown', 'gray', 'black'].map((value, id) => ({ id, value }))

describe('isColorQuestion', () => {
  it('шкала из цветов методики — цветные плитки', () => {
    expect(isColorQuestion({ question_type: 'scale', scale_options: colors, options: [] })).toBe(true)
  })

  it('обычная шкала — подписи', () => {
    const scale = ['1', '2', '3', '4'].map((value, id) => ({ id, value }))
    expect(isColorQuestion({ question_type: 'scale', scale_options: scale, options: [] })).toBe(false)
  })

  it('расстановка цветов', () => {
    expect(isColorQuestion({ question_type: 'ranking', options: colors, scale_options: [] })).toBe(true)
  })
})
