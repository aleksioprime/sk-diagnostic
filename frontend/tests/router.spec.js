import { describe, expect, it } from 'vitest'
import { resolveAccess } from '@/router'

const route = (name, meta = {}) => ({ name, meta, fullPath: `/${name}` })

describe('resolveAccess', () => {
  it('отправляет на вход с возвратом', () => {
    expect(resolveAccess(route('my'), { isAuthenticated: false })).toEqual({ name: 'login', query: { next: '/my' } })
  })

  it('главная: психологу — выдачи, ученику — свои диагностики', () => {
    expect(resolveAccess(route('home'), { isAuthenticated: true, isPsychologist: true })).toEqual({ name: 'assignments' })
    expect(resolveAccess(route('home'), { isAuthenticated: true, isPsychologist: false })).toEqual({ name: 'my' })
  })

  it('результаты только психологам', () => {
    expect(resolveAccess(route('attempt', { psychologist: true }), { isAuthenticated: true, isPsychologist: false })).toEqual({
      name: 'my',
    })
  })
})
