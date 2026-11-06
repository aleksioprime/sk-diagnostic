import { http } from 'sk-ui'

const get = async (url, config) => (await http.get(url, config)).data
const post = async (url, body) => (await http.post(url, body)).data
const put = async (url, body) => (await http.put(url, body)).data
const patch = async (url, body) => (await http.patch(url, body)).data

// Ученик
export const myAttempts = () => get('/v1/my/attempts')
export const myAttempt = (id) => get(`/v1/my/attempts/${id}`)
export const startAttempt = (id, birthDate = null) => post(`/v1/my/attempts/${id}/start`, { birth_date: birthDate })
export const saveAnswer = (id, questionId, answer) => put(`/v1/my/attempts/${id}/answers/${questionId}`, answer)
export const submitAttempt = (id) => http.post(`/v1/my/attempts/${id}/submit`)

// Психологическая служба
export const listTests = () => get('/v1/tests')
export const listClasses = () => get('/v1/classes')
export const searchStudents = (q) => get('/v1/students', { params: { q } })
export const setBirthDate = (personId, birthDate) => put(`/v1/persons/${personId}/birth-date`, { birth_date: birthDate })
export const listAssignments = () => get('/v1/assignments')
export const createAssignment = (body) => post('/v1/assignments', body)
export const getAssignment = (id) => get(`/v1/assignments/${id}`)
export const updateAssignment = (id, body) => patch(`/v1/assignments/${id}`, body)
export const syncAssignment = (id) => post(`/v1/assignments/${id}/sync`)
export const addStudents = (id, personIds) => post(`/v1/assignments/${id}/students`, { person_ids: personIds })
export const recalculateAssignment = (id) => post(`/v1/assignments/${id}/recalculate`)
export const exportUrl = (id) => `/api/v1/assignments/${id}/export.xlsx`
export const getAttempt = (id) => get(`/v1/attempts/${id}`)
export const recalculateAttempt = (id) => post(`/v1/attempts/${id}/recalculate`)
export const deleteAttempt = (id) => http.delete(`/v1/attempts/${id}`)

// Администратор
export const listPsychologists = () => get('/v1/psychologists')
export const setPsychologists = (personIds) => put('/v1/psychologists', { person_ids: personIds })
export const searchEmployees = (q) => get('/v1/directory/employees', { params: { q } })

// Администратор: методики и скрипты расчёта
export const listAdminTests = () => get('/v1/admin/tests')
export const getAdminTest = (id) => get(`/v1/admin/tests/${id}`)
export const createTest = (body) => post('/v1/admin/tests', body)
export const copyTest = (id, body) => post(`/v1/admin/tests/${id}/copy`, body)
export const getTestContent = (id) => get(`/v1/admin/tests/${id}/content`)
export const saveTestContent = (id, body) => put(`/v1/admin/tests/${id}/content`, body)
export const createScale = (testId, body) => post(`/v1/admin/tests/${testId}/scales`, body)
export const saveScale = (testId, scaleId, body) => put(`/v1/admin/tests/${testId}/scales/${scaleId}`, body)
export const importTest = (test, replace = false) => post('/v1/admin/tests/import', { test, replace })
export const exportTest = (id) => get(`/v1/admin/tests/${id}/export`)
export const patchAdminTest = (id, body) => patch(`/v1/admin/tests/${id}`, body)
export const deleteAdminTest = (id) => http.delete(`/v1/admin/tests/${id}`)
export const saveTestScript = (id, script) => put(`/v1/admin/tests/${id}/script`, { script })
export const getSampleInput = (id, mode) => get(`/v1/admin/tests/${id}/sample-input`, { params: { mode } })
export const runTestScript = (id, script, input) => post(`/v1/admin/tests/${id}/run`, { script, input })
