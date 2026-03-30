/**
 * Функции сохранения ответов пользователя через NocoBase API.
 *
 * Используется в AttemptView (авторизованный режим).
 * Для публичного прохождения (AnonAttemptView) запросы идут
 * через BFF-бэкенд (publicApi).
 */

import api from '../api'
import { create, destroy, get, list, normalizeId, toFilter, update, dedupe } from './nocobase'

function answerAppends() {
  return 'option,scale_option,options,question'
}

async function fetchAnswer(answerId) {
  return get('answers', answerId, { appends: answerAppends() })
}

async function fetchRankingItems(answerId) {
  return list('answer_ranking_items', {
    filter: toFilter({ answer_id: normalizeId(answerId) }),
    appends: 'option',
    sort: 'rank,id',
  })
}

async function runStrategies(strategies, label = 'runStrategies') {
  let lastError = null
  const t0 = performance.now()

  for (let i = 0; i < strategies.length; i++) {
    try {
      const result = await strategies[i]()
      console.log(`[RANKING] ${label}: стратегия #${i + 1}/${strategies.length} ✅ (${(performance.now() - t0).toFixed(1)} ms)`)
      return result
    } catch (error) {
      console.warn(`[RANKING] ${label}: стратегия #${i + 1}/${strategies.length} ❌ (${(performance.now() - t0).toFixed(1)} ms)`, error.message || error)
      lastError = error
    }
  }

  throw lastError
}

export async function saveAnswerValue(answerId, payload) {
  await update('answers', answerId, payload)
  return fetchAnswer(answerId)
}

export async function saveMultipleChoice(answerId, optionIds) {
  const ids = dedupe(optionIds.map((value) => normalizeId(value)))

  await runStrategies([
    () => update('answers', answerId, { options: ids, is_skipped: false }),
    () => update('answers', answerId, { options: ids.map((id) => ({ id })), is_skipped: false }),
    () => api.post(`/answers/${answerId}/options:set`, { values: ids }),
    () => api.post(`/answers/${answerId}/options:set`, ids),
  ])

  await update('answers', answerId, {
    option_id: null,
    scale_option_id: null,
    text: null,
    number: null,
    boolean: null,
    is_skipped: false,
  })

  return fetchAnswer(answerId)
}

export async function saveRanking(answerId, rankedOptionIds) {
  const totalStart = performance.now()
  console.group(`[RANKING] saveRanking answerId=${answerId}, options=[${rankedOptionIds}]`)

  const normalizedAnswerId = normalizeId(answerId)
  const nextOptionIds = dedupe(rankedOptionIds.map((value) => normalizeId(value)))

  // 1. Получаем текущие элементы ранжирования
  let t = performance.now()
  const existingItems = await fetchRankingItems(normalizedAnswerId)
  console.log(`[RANKING] 1) fetch existing: ${existingItems.length} шт. — ${(performance.now() - t).toFixed(1)} ms`)

  const existingByOptionId = new Map(
    existingItems.map((item) => [normalizeId(item.option_id ?? item.option?.id), item]),
  )

  // 2. Формируем все операции: удаление лишних + обновление/создание нужных
  const deleteOps = existingItems
    .filter((item) => !nextOptionIds.includes(normalizeId(item.option_id ?? item.option?.id)))
    .map((item) => destroy('answer_ranking_items', item.id))

  const upsertOps = nextOptionIds.map((optionId, index) => {
    const existing = existingByOptionId.get(optionId)
    if (existing) {
      return update('answer_ranking_items', existing.id, {
        answer_id: normalizedAnswerId,
        option_id: optionId,
        rank: index + 1,
      })
    }
    return create('answer_ranking_items', {
      answer: { id: normalizedAnswerId },
      option: { id: optionId },
      rank: index + 1,
    })
  })

  // 3. Выполняем все удаления и upsert-ы параллельно (один Promise.all)
  t = performance.now()
  await Promise.all([...deleteOps, ...upsertOps])
  console.log(`[RANKING] 2) delete ${deleteOps.length} + upsert ${upsertOps.length} (параллельно) — ${(performance.now() - t).toFixed(1)} ms`)

  // 4. Сохраняем ответ + получаем итог параллельно
  t = performance.now()
  const [answer, rankingItems] = await Promise.all([
    saveAnswerValue(normalizedAnswerId, { is_skipped: false }),
    fetchRankingItems(normalizedAnswerId),
  ])
  console.log(`[RANKING] 3) saveAnswer + fetchRanking (параллельно) — ${(performance.now() - t).toFixed(1)} ms`)

  console.log(`[RANKING] === ИТОГО: ${(performance.now() - totalStart).toFixed(1)} ms ===`)
  console.groupEnd()
  return { answer, rankingItems }
}
