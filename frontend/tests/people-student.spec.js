import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { createUser } from '@/api/people'
import { updatePerson } from '@/api/diagnostic'
import PersonEditCard from '@/components/PersonEditCard.vue'
import PeopleView from '@/views/admin/PeopleView.vue'

vi.mock('@/stores/auth', () => ({ useAuthStore: () => ({ user: { id: 1 } }) }))
vi.mock('@/api/diagnostic', () => ({
  getPerson: vi.fn(async () => ({ id: 9, last_name: 'Гостева', first_name: '', middle_name: '', email: 'guest@example.org', gender: null, birth_date: null, class_id: null, is_student: true, is_employee: false, has_account: true, has_password: false })),
  updatePerson: vi.fn(async (id, body) => ({ id, last_name: 'Гостева', first_name: '', email: 'guest@example.org', ...body })),
  listClasses: vi.fn(async () => []),
}))
vi.mock('@/api/people', () => ({
  createUser: vi.fn(async (body) => ({ email: body.email, has_password: !!body.password, person: { id: 9 } })),
  fetchPersons: vi.fn(async () => ({ items: [], total: 0 })),
  fetchUsers: vi.fn(async () => ({ items: [], total: 0 })),
  fetchSyncRuns: vi.fn(async () => []),
  setPersonAdmin: vi.fn(),
  startSync: vi.fn(),
  updateUser: vi.fn(),
}))

async function openForm() {
  const wrapper = mount(PeopleView)
  await flushPromises()
  const form = wrapper.findAll('form').find((f) => f.text().includes('Создать'))
  const [email, , password] = form.findAll('input')
  await email.setValue('guest@example.org')
  const student = form.findAll('label').find((l) => l.text().includes('Ученик')).find('input')
  await student.setValue(true)
  return { wrapper, form, password }
}

afterEach(() => vi.clearAllMocks())

describe('новый ученик не из SkolStream', () => {
  it('без пароля не создаётся', async () => {
    const { wrapper, form, password } = await openForm()
    expect(password.attributes('required')).toBeDefined()
    await form.trigger('submit')
    await flushPromises()
    expect(createUser).not.toHaveBeenCalled()
    expect(wrapper.text()).toContain('Задайте пароль')
  })

  it('с паролем создаётся и отмечается учеником', async () => {
    const { form, password } = await openForm()
    await password.setValue('fixture-pass-123')
    await form.trigger('submit')
    await flushPromises()
    expect(createUser.mock.calls[0][0]).toMatchObject({ email: 'guest@example.org', password: 'fixture-pass-123', is_employee: false })
    expect(updatePerson).toHaveBeenCalledWith(9, { is_student: true })
  })
})

describe('редактирование человека не из SkolStream', () => {
  const byLabel = (wrapper, text) => wrapper.findAll('label').find((l) => l.text().startsWith(text)).element.control

  it('отправляет только изменённые поля и пароль', async () => {
    const wrapper = mount(PersonEditCard, { props: { personId: 9 } })
    await flushPromises()
    expect(wrapper.text()).toContain('Пароль не задан')
    const name = byLabel(wrapper, 'Имя')
    name.value = 'Анна'
    name.dispatchEvent(new Event('input'))
    const pass = byLabel(wrapper, 'Новый пароль')
    pass.value = 'fixture-pass-123'
    pass.dispatchEvent(new Event('input'))
    await wrapper.find('form').trigger('submit')
    await flushPromises()
    expect(updatePerson).toHaveBeenCalledWith(9, { first_name: 'Анна', password: 'fixture-pass-123' })
    expect(wrapper.emitted('saved')).toHaveLength(1)
  })

  it('короткий пароль не отправляется', async () => {
    const wrapper = mount(PersonEditCard, { props: { personId: 9 } })
    await flushPromises()
    const pass = byLabel(wrapper, 'Новый пароль')
    pass.value = 'short'
    pass.dispatchEvent(new Event('input'))
    await wrapper.find('form').trigger('submit')
    await flushPromises()
    expect(updatePerson).not.toHaveBeenCalled()
    expect(wrapper.text()).toContain('не короче 8')
  })
})
