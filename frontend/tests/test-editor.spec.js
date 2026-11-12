import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import * as api from '@/api/diagnostic'
import { detailedError } from '@/utils/apiErrors'
import TestEditorView from '@/views/admin/TestEditorView.vue'

vi.mock('vue-router', () => ({
  RouterLink: { template: '<a><slot /></a>' },
  useRoute: () => ({ params: { id: '5' } }),
  onBeforeRouteLeave: vi.fn(),
}))
vi.mock('@/components/CodeEditor.vue', () => ({
  default: {
    props: ['modelValue', 'label'],
    emits: ['update:modelValue'],
    template: '<textarea :aria-label="label" :value="modelValue" @input="$emit(\'update:modelValue\', $event.target.value)"></textarea>',
  },
}))
vi.mock('@/api/diagnostic', () => ({
  getAdminTest: vi.fn(),
  getSampleInput: vi.fn(async () => ({ answers: [] })),
  runTestScript: vi.fn(async () => ({ output: { total: 3 }, error: null, line: null, logs: ['лог'], duration_ms: 4, summary: { Сумма: 3 } })),
  saveTestScript: vi.fn(async (id, script) => ({ ...base, scoring: 'script', scoring_script: script })),
  patchAdminTest: vi.fn(),
}))

const base = { id: 5, code: 'x', title: 'X', questions_count: 1, assignments_count: 0, scoring: 'none', scoring_script: null, needs_birth_date: false }

async function open(test = base) {
  api.getAdminTest.mockResolvedValue(test)
  const wrapper = mount(TestEditorView)
  await flushPromises()
  return wrapper
}

const editor = (wrapper, label) => wrapper.find(`textarea[aria-label="${label}"]`)

beforeEach(() => vi.useFakeTimers())
afterEach(() => {
  vi.useRealTimers()
  vi.clearAllMocks()
})

describe('страница скрипта расчёта', () => {
  it('сразу показывает входные данные и итог запуска на заготовке', async () => {
    const wrapper = await open()
    expect(api.runTestScript).toHaveBeenCalledOnce()
    expect(editor(wrapper, 'Входные данные расчёта').element.value).toContain('answers')
    expect(wrapper.text()).toContain('"total": 3')
    expect(wrapper.text()).toContain('лог')
    expect(wrapper.text()).toContain('Сумма')
  })

  it('проверка на лету включена сразу', async () => {
    const wrapper = await open()
    const toggle = wrapper.findAll('label').find((l) => l.text().includes('Проверять на лету')).find('input')
    expect(toggle.element.checked).toBe(true)
  })

  it('запускает скрипт на лету и один раз после паузы в наборе', async () => {
    const wrapper = await open()
    api.runTestScript.mockClear()
    await editor(wrapper, 'Скрипт расчёта').setValue('return {a: 1}')
    await editor(wrapper, 'Скрипт расчёта').setValue('return {a: 2}')
    expect(api.runTestScript).not.toHaveBeenCalled()
    await vi.advanceTimersByTimeAsync(700)
    expect(api.runTestScript).toHaveBeenCalledOnce()
    expect(api.runTestScript.mock.calls[0][1]).toBe('return {a: 2}')
  })

  it('не запускает скрипт на неверном JSON и подсказывает ошибку', async () => {
    const wrapper = await open()
    api.runTestScript.mockClear()
    await editor(wrapper, 'Входные данные расчёта').setValue('{нет')
    await vi.advanceTimersByTimeAsync(700)
    expect(api.runTestScript).not.toHaveBeenCalled()
    expect(wrapper.text()).toContain('не JSON')
  })

  it('показывает строку ошибки и сохраняет скрипт', async () => {
    api.runTestScript.mockResolvedValueOnce({ output: null, error: 'Error: boom', line: 7, logs: [], duration_ms: 1, summary: {} })
    const wrapper = await open()
    expect(wrapper.text()).toContain('Строка 7')
    await editor(wrapper, 'Скрипт расчёта').setValue('return {a: 1}')
    await wrapper.get('form').trigger('submit')
    await flushPromises()
    expect(api.saveTestScript).toHaveBeenCalledWith('5', 'return {a: 1}')
    expect(wrapper.text()).not.toContain('Не сохранён')
  })

})

describe('detailedError', () => {
  it('называет место ошибки в файле методики', () => {
    const error = { response: { data: { detail: [{ loc: ['body', 'test', 'questions', 0, 'text'], msg: 'Field required' }] } } }
    expect(detailedError(error)).toBe('questions.0.text: Field required')
  })
})
