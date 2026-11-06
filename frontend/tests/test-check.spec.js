import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'
import * as api from '@/api/diagnostic'
import { resolveAccess } from '@/router'
import { isAnswered } from '@/utils/answers'
import TestCheckView from '@/views/admin/TestCheckView.vue'
import TestPreviewView from '@/views/admin/TestPreviewView.vue'

vi.mock('vue-router', async (original) => ({
  ...(await original()),
  RouterLink: { template: '<a><slot /></a>' },
  useRoute: () => ({ params: { id: '5' } }),
}))
vi.mock('@/api/diagnostic', () => ({
  getAdminTest: vi.fn(),
  getTestReadiness: vi.fn(),
  patchAdminTest: vi.fn(async () => ({ ...test, is_active: true })),
  getTestPreview: vi.fn(),
  previewResult: vi.fn(),
}))

const test = { id: 5, code: 'x', title: 'X', is_active: false }
const button = (wrapper, text) => wrapper.findAll('button').find((b) => b.text() === text)
const option = (id, label) => ({ id, label, description: '', value: String(id), score: id })
const question = (id, text) => ({ id, order: id, code: null, text, description: '', question_type: 'single_choice', is_required: true, is_random: false, min_selections: null, max_selections: null, options: [option(1, 'А'), option(2, 'Б')], scale_options: [] })

afterEach(() => vi.clearAllMocks())

async function openCheck(readiness) {
  api.getAdminTest.mockResolvedValue(test)
  api.getTestReadiness.mockResolvedValue(readiness)
  const wrapper = mount(TestCheckView)
  await flushPromises()
  return wrapper
}

describe('проверка готовности', () => {
  it('с ошибками кнопка «Включить» недоступна', async () => {
    const wrapper = await openCheck({ ready: false, problems: [{ level: 'error', text: 'Нет расчёта', tab: 'scoring' }] })
    expect(wrapper.text()).toContain('Мешает включить')
    expect(wrapper.text()).toContain('Нет расчёта')
    expect(button(wrapper, 'Включить').attributes('disabled')).toBeDefined()
  })

  it('предупреждения не мешают включить', async () => {
    const wrapper = await openCheck({ ready: true, problems: [{ level: 'warning', text: 'Нет summary', tab: 'scoring' }] })
    await button(wrapper, 'Включить').trigger('click')
    await flushPromises()
    expect(api.patchAdminTest).toHaveBeenCalledWith('5', { is_active: true })
    expect(wrapper.text()).toContain('Методика включена')
    expect(button(wrapper, 'Отключить')).toBeDefined()
  })
})

describe('предпросмотр', () => {
  async function openPreview(needsBirthDate = false) {
    api.getTestPreview.mockResolvedValue({ test: { title: 'Опрос', description: 'Описание' }, needs_birth_date: needsBirthDate, questions: [question(10, 'Первый'), question(11, 'Второй')] })
    api.previewResult.mockResolvedValue({ output: { total: 3, summary: { Балл: 3 } }, error: null, line: null, logs: [], summary: { Балл: 3 } })
    const wrapper = mount(TestPreviewView, { props: { id: '5' } })
    await flushPromises()
    return wrapper
  }

  const choose = async (wrapper, label) => {
    await wrapper.findAll('label, button, [role="radio"]').find((node) => node.text() === label).trigger('click')
  }

  it('проходится как у ученика и показывает результат без сохранения ответов', async () => {
    const wrapper = await openPreview()
    expect(wrapper.text()).toContain('Ответы не сохраняются')
    await button(wrapper, 'Начать').trigger('click')
    expect(wrapper.text()).toContain('Вопрос 1 из 2')
    expect(button(wrapper, 'Далее').attributes('disabled')).toBeDefined()
    await choose(wrapper, 'А')
    await button(wrapper, 'Далее').trigger('click')
    await choose(wrapper, 'Б')
    await button(wrapper, 'Завершить').trigger('click')
    await flushPromises()
    const body = api.previewResult.mock.calls[0][1]
    expect(body.answers.map((a) => [a.question_id, a.option_id])).toEqual([[10, 1], [11, 2]])
    expect(wrapper.text()).toContain('Балл')
    await button(wrapper, 'Пройти ещё раз').trigger('click')
    expect(button(wrapper, 'Начать')).toBeDefined()
  })

  it('показывает вопрос со случайным порядком вариантов', async () => {
    api.getTestPreview.mockResolvedValue({ test: { title: 'Опрос', description: '' }, needs_birth_date: false, questions: [{ ...question(356213359902720, 'Цвет'), is_random: true }] })
    const wrapper = mount(TestPreviewView, { props: { id: '5' } })
    await flushPromises()
    await button(wrapper, 'Начать').trigger('click')
    expect(wrapper.text()).toContain('Цвет')
    expect(wrapper.text()).toContain('А')
    expect(wrapper.text()).toContain('Б')
  })

  it('спрашивает дату рождения, если она нужна методике', async () => {
    const wrapper = await openPreview(true)
    await button(wrapper, 'Начать').trigger('click')
    expect(wrapper.text()).toContain('Укажите дату рождения')
    expect(wrapper.text()).not.toContain('Вопрос 1 из 2')
  })
})

describe('общие правила', () => {
  it('упорядочивание считается отвеченным, когда расставлены все варианты', () => {
    const q = { question_type: 'ranking', min_selections: null, options: [{}, {}] }
    expect(isAnswered(q, { ranking: [1] })).toBe(false)
    expect(isAnswered(q, { ranking: [1, 2] })).toBe(true)
  })

  it('предпросмотр только администратору', () => {
    const to = { name: 'admin-test-preview', meta: { admin: true }, fullPath: '/x' }
    expect(resolveAccess(to, { isAuthenticated: true, isAdmin: false })).toEqual({ name: 'home' })
  })
})
