import api from '../api'
import logger from './logger'

const DEFAULT_PAGE_SIZE = 500

export function normalizeId(value) {
  if (value === null || value === undefined || value === '') return value
  if (typeof value === 'number') return value
  if (/^\d+$/.test(String(value))) return Number(value)
  return value
}

export function toFilter(filter) {
  return JSON.stringify(filter)
}

export function dedupe(values = []) {
  return [...new Set(values.filter((value) => value !== null && value !== undefined && value !== ''))]
}

function toArray(value) {
  if (Array.isArray(value)) return value
  if (typeof value === 'string' && value) return value.split(',').map((s) => s.trim())
  return undefined
}

function normalizeParams(params) {
  const result = { ...params }
  if (result.appends !== undefined) result.appends = toArray(result.appends)
  if (result.sort !== undefined) result.sort = toArray(result.sort)
  return result
}

export async function list(collection, params = {}) {
  const normalized = normalizeParams({ pageSize: DEFAULT_PAGE_SIZE, ...params })
  logger.debug(`list ${collection}`, normalized)
  const { data } = await api.get(`/${collection}:list`, { params: normalized })
  logger.debug(`list ${collection} → ${data.data?.length ?? 0} records`)
  return data.data || []
}

export async function get(collection, id, params = {}) {
  const normalized = normalizeParams({ filterByTk: id, ...params })
  logger.debug(`get ${collection}`, normalized)
  const { data } = await api.get(`/${collection}:get`, { params: normalized })
  logger.debug(`get ${collection} → id=${data.data?.id}`)
  return data.data
}

export async function create(collection, payload) {
  logger.debug(`create ${collection}`, payload)
  const { data } = await api.post(`/${collection}:create`, payload)
  logger.debug(`create ${collection} → id=${data.data?.id}`)
  return data.data
}

export async function update(collection, id, payload) {
  logger.debug(`update ${collection} id=${id}`, payload)
  const { data } = await api.post(`/${collection}:update?filterByTk=${id}`, payload)
  logger.debug(`update ${collection} id=${id} → ok`)
  return data.data
}

export async function destroy(collection, id) {
  logger.debug(`destroy ${collection} id=${id}`)
  try {
    await api.delete(`/${collection}:destroy?filterByTk=${id}`)
  } catch {
    await api.post(`/${collection}:destroy?filterByTk=${id}`)
  }
  logger.debug(`destroy ${collection} id=${id} → ok`)
}
