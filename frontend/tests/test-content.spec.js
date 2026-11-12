import { reactive } from 'vue'
import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'
import * as api from '@/api/diagnostic'
import TestContentView from '@/views/admin/TestContentView.vue'
import { contentBody, contentProblem, newQuestion } from '@/utils/testDraft'

const route = reactive({ params: { id: '5' }, path: '/admin/tests/5/questions', query: {}, hash: '' })
function navigate({ query }) {
  route.query = query
  return Promise.resolve()
}

vi.mock('vue-router', () => ({
  RouterLink: { template: '<a><slot /></a>' },
  useRoute: () => route,
  useRouter: () => ({ push: navigate, replace: navigate }),
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

async function open(content = base, query = {}) {
  route.query = query
  api.getTestContent.mockResolvedValue(structuredClone(content))
  const wrapper = mount(TestContentView, { attachTo: document.body })
  await flushPromises()
  return wrapper
}

const button = (wrapper, text) => wrapper.findAll('button').find((b) => b.text() === text)
const byLabel = (wrapper, label) => wrapper.find(`button[aria-label="${label}"]`)
const openQuestion = (wrapper, text) => wrapper.findAll('button[aria-expanded]').find((b) => b.text().includes(text)).trigger('click')

afterEach(() => vi.clearAllMocks())

describe('редактор вопросов', () => {
  it('меняет порядок вопросов и добавляет новый', async () => {
    const wrapper = await open()
    expect(button(wrapper, 'Сохранить вопросы')).toBeUndefined()
    await openQuestion(wrapper, 'Второй')
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
    expect(route.query.question).toBe('102')
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
    await openQuestion(wrapper, 'Первый')
    expect(button(wrapper, 'Добавить вопрос')).toBeUndefined()
    expect(button(wrapper, 'Удалить')).toBeUndefined()
    expect(byLabel(wrapper, 'Удалить вариант 1').exists()).toBe(false)
    expect(wrapper.find('input[aria-label="Баллы варианта 1"]').attributes('disabled')).toBeDefined()
    expect(wrapper.find('input[aria-label="Подпись варианта 1"]').attributes('disabled')).toBeUndefined()
  })
})

describe('компактный список вопросов', () => {
  it('раскрывает вопрос по ссылке и реагирует на изменение адреса', async () => {
    const wrapper = await open(base, { question: '11', source: 'share' })
    const expanded = () => wrapper.find('button[aria-expanded="true"]')
    expect(expanded().text()).toContain('Второй')
    await openQuestion(wrapper, 'Первый')
    expect(route.query).toEqual({ question: '10', source: 'share' })
    route.query = { question: '11', source: 'share' }
    await flushPromises()
    expect(expanded().text()).toContain('Второй')
    route.query = { question: ['10', '11'] }
    await flushPromises()
    expect(expanded().exists()).toBe(false)
    wrapper.unmount()
  })

  it('вопросы свёрнуты, раскрыт только один', async () => {
    const wrapper = await open()
    expect(wrapper.findAll('input[aria-label^="Подпись"]')).toHaveLength(0)
    expect(wrapper.text()).toContain('Один вариант · 2')
    await openQuestion(wrapper, 'Первый')
    expect(wrapper.findAll('input[aria-label^="Подпись"]')).toHaveLength(2)
    await openQuestion(wrapper, 'Второй')
    expect(wrapper.findAll('input[aria-label^="Подпись"]')).toHaveLength(2)
    expect(wrapper.findAll('button[aria-expanded="true"]')).toHaveLength(1)
  })

  it('незаполненный вопрос раскрывается сам и выделяется', async () => {
    const wrapper = await open()
    const areas = async () => {
      await openQuestion(wrapper, 'Второй')
      await wrapper.findAll('textarea').at(-1).setValue(' ')
    }
    await areas()
    await openQuestion(wrapper, 'Первый')
    await button(wrapper, 'Сохранить вопросы').trigger('click')
    expect(api.saveTestContent).not.toHaveBeenCalled()
    expect(wrapper.text()).toContain('Вопрос 2: заполните текст')
    expect(wrapper.findAll('li.border-red-500')).toHaveLength(1)
    expect(wrapper.find('button[aria-expanded="true"]').text()).toContain('2')
  })

  it('перетаскивание меняет порядок', async () => {
    const wrapper = await open()
    const rows = wrapper.get('ol[aria-label="Вопросы методики"]').findAll(':scope > li')
    await rows[1].find('[draggable="true"]').trigger('dragstart', { dataTransfer: { setData: () => {} } })
    await rows[0].trigger('drop')
    await button(wrapper, 'Сохранить вопросы').trigger('click')
    await flushPromises()
    expect(api.saveTestContent.mock.calls[0][1].questions.map((q) => q.id)).toEqual([11, 10])
  })

  it('дублирование создаёт новый вопрос без id и кода', async () => {
    const wrapper = await open({ ...base, questions: [{ ...question(10, 'Первый'), code: 'mood' }, question(11, 'Второй')] })
    await openQuestion(wrapper, 'Первый')
    await button(wrapper, 'Дублировать').trigger('click')
    await button(wrapper, 'Сохранить вопросы').trigger('click')
    await flushPromises()
    const saved = api.saveTestContent.mock.calls[0][1].questions
    expect(saved.map((q) => [q.id, q.text, q.code])).toEqual([[10, 'Первый', 'mood'], [null, 'Первый', null], [11, 'Второй', null]])
    expect(saved[1].options.map((o) => o.id)).toEqual([null, null])
  })

  it('у выданной методики нельзя перетаскивать', async () => {
    const wrapper = await open({ ...base, mode: 'text', lock_reason: 'Уже выдавали.' })
    expect(wrapper.find('[draggable="true"]').exists()).toBe(false)
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

describe('поля редактора', () => {
  it('баллы из поля уходят числом, а не строкой', async () => {
    const wrapper = await open()
    await openQuestion(wrapper, 'Первый')
    await wrapper.find('input[aria-label="Баллы варианта 1"]').setValue('7')
    await button(wrapper, 'Сохранить вопросы').trigger('click')
    await flushPromises()
    expect(api.saveTestContent.mock.calls[0][1].questions[0].options[0].score).toBe(7)
  })

  it('смена типа через общий список подставляет варианты', async () => {
    const wrapper = await open({ ...base, questions: [{ ...question(10, 'Первый'), question_type: 'text', options: [] }] })
    await openQuestion(wrapper, 'Первый')
    await wrapper.find('button[aria-label="Тип ответа"]').trigger('click')
    const item = [...document.body.querySelectorAll('[role="option"]')].find((node) => node.textContent.includes('Один вариант'))
    item.click()
    await flushPromises()
    expect(wrapper.find('input[aria-label="Подпись варианта 2"]').exists()).toBe(true)
    wrapper.unmount()
  })
})
