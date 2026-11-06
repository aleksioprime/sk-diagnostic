import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'
import * as api from '@/api/diagnostic'
import TestContentView from '@/views/admin/TestContentView.vue'
import { contentBody, contentProblem, newQuestion } from '@/utils/testDraft'

vi.mock('vue-router', () => ({
  RouterLink: { template: '<a><slot /></a>' },
  useRoute: () => ({ params: { id: '5' } }),
  onBeforeRouteLeave: vi.fn(),
}))
vi.mock('@/api/diagnostic', () => ({
  getTestContent: vi.fn(),
  saveTestContent: vi.fn(async (id, body) => ({ ...base, ...body, questions: body.questions.map((q, n) => ({ ...q, id: q.id ?? 100 + n })) })),
  createScale: vi.fn(),
  saveScale: vi.fn(),
}))

const option = (id, label) => ({ id, label, description: '', value: String(id), score: id })
const question = (id, text) => ({ id, code: null, text, description: '', question_type: 'single_choice', is_required: true, is_random: false, scale_id: null, options: [option(1, 'А'), option(2, 'Б')] })
const base = { id: 5, code: 'x', title: 'X', description: '', is_sequential: true, mode: 'full', lock_reason: null, scales: [], questions: [question(10, 'Первый'), question(11, 'Второй')] }

async function open(content = base) {
  api.getTestContent.mockResolvedValue(structuredClone(content))
  const wrapper = mount(TestContentView, { attachTo: document.body })
  await flushPromises()
  return wrapper
}

const button = (wrapper, text) => wrapper.findAll('button').find((b) => b.text() === text)
const byLabel = (wrapper, label) => wrapper.find(`button[aria-label="${label}"]`)

afterEach(() => vi.clearAllMocks())

describe('редактор вопросов', () => {
  it('меняет порядок вопросов и добавляет новый', async () => {
    const wrapper = await open()
    expect(button(wrapper, 'Сохранить вопросы').attributes('disabled')).toBeDefined()
    await byLabel(wrapper, 'Вопрос 2 выше').trigger('click')
    await button(wrapper, 'Добавить вопрос').trigger('click')
    const areas = wrapper.findAll('textarea')
    await areas[areas.length - 1].setValue('Третий')
    await button(wrapper, 'Сохранить вопросы').trigger('click')
    await flushPromises()
    const body = api.saveTestContent.mock.calls[0][1]
    expect(body.questions.map((q) => q.text)).toEqual(['Второй', 'Первый', 'Третий'])
    expect(body.questions.map((q) => q.id)).toEqual([11, 10, null])
    expect(wrapper.text()).toContain('Сохранено')
  })

  it('не отправляет незаполненный вопрос', async () => {
    const wrapper = await open()
    await button(wrapper, 'Добавить вопрос').trigger('click')
    await button(wrapper, 'Сохранить вопросы').trigger('click')
    expect(api.saveTestContent).not.toHaveBeenCalled()
    expect(wrapper.text()).toContain('Вопрос 3: заполните текст')
  })

  it('у выданной методики правятся только тексты', async () => {
    const wrapper = await open({ ...base, mode: 'text', lock_reason: 'Уже выдавали.' })
    expect(wrapper.text()).toContain('Уже выдавали.')
    expect(button(wrapper, 'Добавить вопрос')).toBeUndefined()
    expect(button(wrapper, 'Удалить')).toBeUndefined()
    expect(byLabel(wrapper, 'Удалить вариант 1').exists()).toBe(false)
    expect(wrapper.find('input[aria-label="Баллы варианта 1"]').attributes('disabled')).toBeDefined()
    expect(wrapper.find('input[aria-label="Подпись варианта 1"]').attributes('disabled')).toBeUndefined()
  })
})

describe('черновик', () => {
  it('пустые баллы и лишние поля не уходят на сервер', () => {
    const q = { ...newQuestion(), text: 'Т', options: [{ id: null, key: 'k', label: 'А', description: '', value: 1, score: '' }] }
    const body = contentBody({ title: 'Т', description: '', is_sequential: true, questions: [q] })
    expect(body.questions[0].options[0]).toEqual({ id: null, label: 'А', description: '', value: '1', score: null })
    expect(body.questions[0].key).toBeUndefined()
  })

  it('шкала обязательна для вопроса со шкалой', () => {
    const q = { ...newQuestion(), text: 'Т', question_type: 'scale' }
    expect(contentProblem({ title: 'Т', questions: [q] })).toBe('Вопрос 1: выберите шкалу')
  })
})
