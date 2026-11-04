/**
 * Citation Parsing Utilities for ScholarGraph.
 * Matches and structures bracketed citation tokens:
 *   [paper_hu2021, Page 4]
 *   [paper_a, Page 2, Page 6]
 *   [paper_a, Page 1-2]
 *   [paper_a, Page 1; paper_b, Page 2]
 */

export const CITATION_GROUP_SOURCE =
  '\\[((?:\\s*[a-zA-Z0-9_-]+,\\s*(?:Pages?|p\\.?)\\s*\\d+(?:\\s*[-–,]\\s*(?:Pages?|p\\.?)?\\s*\\d+)*\\s*;?)+)\\]'

/**
 * Parse the inside of a citation group into [{ paperId, pages: [..] }].
 */
export function parseCitationGroup(inner) {
  return inner
    .split(';')
    .map((part) => part.trim())
    .filter(Boolean)
    .map((part) => {
      const m = part.match(/^([a-zA-Z0-9_-]+),\s*(.*)$/)
      if (!m) return null
      const pagesStr = m[2]
      let pages = (pagesStr.match(/\d+/g) || []).map((s) => parseInt(s, 10))
      const range = pagesStr.match(/(\d+)\s*[-–]\s*(?:Pages?|p\.?)?\s*(\d+)/i)
      if (range && pages.length === 2) {
        const [a, b] = [parseInt(range[1], 10), parseInt(range[2], 10)]
        if (b >= a && b - a <= 10) pages = Array.from({ length: b - a + 1 }, (_, i) => a + i)
      }
      return { paperId: m[1], pages: pages.filter((n) => !Number.isNaN(n)) }
    })
    .filter(Boolean)
}

/**
 * Builds a deterministic 1-based reference number map (e.g. paper_vaswani2017 -> 1)
 * for all papers cited in an assistant response so inline superscript badges [1, p.2]
 * match the numbered Verified Sources list.
 */
export function buildPaperReferenceMap(answerText = '', citations = []) {
  const map = new Map()
  let nextIdx = 1

  const registerPaperId = (rawId) => {
    if (!rawId) return 1
    const clean = rawId.trim()
    const normalized = clean.startsWith('paper_') ? clean : `paper_${clean}`
    const stripped = clean.replace(/^paper_/, '')

    if (map.has(clean)) return map.get(clean)
    if (map.has(normalized)) return map.get(normalized)
    if (map.has(stripped)) return map.get(stripped)

    const assigned = nextIdx++
    map.set(clean, assigned)
    map.set(normalized, assigned)
    map.set(stripped, assigned)
    return assigned
  }

  citations.forEach((c) => {
    if (c?.paper_id) registerPaperId(c.paper_id)
  })

  const bracketRegex = new RegExp(CITATION_GROUP_SOURCE, 'gi')
  let match
  while ((match = bracketRegex.exec(answerText)) !== null) {
    parseCitationGroup(match[1]).forEach((g) => registerPaperId(g.paperId))
  }

  return { registerPaperId }
}

