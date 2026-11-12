import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'
import * as api from '@/api/diagnostic'
import MotivationResult from '@/components/results/MotivationResult.vue'
import AssignmentListView from '@/views/assignments/AssignmentListView.vue'

const push = vi.fn()
vi.mock('vue-router', () => ({ RouterLink: { template: '<a><slot /></a>' }, useRoute: () => ({ query: {} }), useRouter: () => ({ push }) }))
vi.mock('@/api/diagnostic', () => ({
  listAssignments: vi.fn(async () => []),
  listTests: vi.fn(async () => []),
  listClasses: vi.fn(async () => [{ id: 1, name: '5А', students_count: 2 }]),
  createAssignment: vi.fn(async () => ({ id: 7 })),
}))

async function openForm() {
  const wrapper = mount(AssignmentListView, { attachTo: document.body })
  await flushPromises()
  await wrapper.findAll('button').find((b) => b.text() === 'Выдать классу').trigger('click')
  return wrapper
}

describe('выдача методики', () => {
  afterEach(() => vi.clearAllMocks())

  it('без методики не отправляет форму и показывает ошибку', async () => {
    const wrapper = await openForm()
    await wrapper.get('form').trigger('submit')
    expect(api.createAssignment).not.toHaveBeenCalled()
    expect(wrapper.get('[role="alert"]').text()).toBe('Выберите методику и класс')
    expect(wrapper.findAll('[role="combobox"]')[0].attributes('aria-invalid')).toBe('true')
    wrapper.unmount()
  })

  it('отправляет выбранные методику и класс', async () => {
    api.listTests.mockResolvedValueOnce([{ id: 3, title: 'Мотивация' }])
    const wrapper = await openForm()
    await wrapper.get('form').trigger('submit')
    await flushPromises()
    expect(api.createAssignment).toHaveBeenCalledWith({ test_id: 3, class_id: 1, title: '' })
    expect(push).toHaveBeenCalledWith({ name: 'assignment', params: { id: 7 } })
    wrapper.unmount()
  })
})

describe('результат мотивации', () => {
  it('показывает уровень шкалы значком нужного цвета', () => {
    const data = { result: {}, student: {}, scales: [{ code: 'a', title: 'Шкала', value: 1, level: 'low', level_label: 'Низкий' }] }
    const badge = mount(MotivationResult, { props: { data } }).get('tbody span')
    expect(badge.text()).toBe('Низкий')
    expect(badge.classes()).toContain('bg-amber-100')
  })
})
