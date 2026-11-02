/** Перемешивание, одинаковое для одного прохождения: при перезагрузке порядок вариантов не прыгает. */
export function seededShuffle(items, seed) {
  let state = Number(BigInt.asUintN(32, BigInt(seed || 1))) || 1
  const random = () => {
    state ^= state << 13
    state ^= state >>> 17
    state ^= state << 5
    return (state >>> 0) / 4294967296
  }
  const result = [...items]
  for (let i = result.length - 1; i > 0; i--) {
    const j = Math.floor(random() * (i + 1))
    ;[result[i], result[j]] = [result[j], result[i]]
  }
  return result
}
