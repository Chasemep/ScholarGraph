import React, { useState } from 'react'
import { Send, BookOpen, AlertCircle, Info } from 'lucide-react'
import { renderMathSegment } from '../utils/mathRenderer'
import { MarkdownBlockRenderer } from './MarkdownBlockRenderer'

/**
 * Matches a bracketed citation group, including multi-source and page-range forms:
 *   [paper_hu2021, Page 4]
 *   [paper_a, Page 2, Page 6]
 *   [paper_a, Page 1-2]
 *   [paper_a, Page 1; paper_b, Page 2]
 */
const CITATION_GROUP_SOURCE =
  '\\[((?:\\s*[a-zA-Z0-9_-]+,\\s*(?:Pages?|p\\.?)\\s*\\d+(?:\\s*[-–,]\\s*(?:Pages?|p\\.?)?\\s*\\d+)*\\s*;?)+)\\]'

/** Parse the inside of a citation group into [{ paperId, pages: [..] }]. */
function parseCitationGroup(inner) {
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
 * Builds a deterministic 1-based reference number map (e.g. paper_cuckersmale_original -> 1)
 * for all papers cited in an assistant response so inline superscript badges [1, p.2]
 * match the numbered Verified Sources list.
 */
function buildPaperReferenceMap(answerText = '', citations = []) {
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

/**
 * Parses inline citation markers like:
 * - [paper_hu2021, Page 4]
 * - [paper_cuckersmale_original, Page 2, Page 6]
 * - [paper_a, Page 1-2] and [paper_a, Page 1; paper_b, Page 2]
 * - cuckersmale_original · p.2
 * and converts them into compact, clickable superscript badges (e.g. [1, p.2]),
 * while rendering all surrounding LaTeX math ($...$, $$...$$, \frac, x_i, etc.) via KaTeX.
 */
function renderAnswerWithCitations(answerText, citations = [], onSelectCitation, registerPaperId) {
  if (!answerText) return null

  const combinedCitationRegex = new RegExp(
    `${CITATION_GROUP_SOURCE}|(?:\\b(paper_[a-zA-Z0-9_-]+|[a-zA-Z0-9]+_[a-zA-Z0-9_-]+)\\s*·\\s*p\\.?\\s*(\\d+))`,
    'gi'
  )

  const parts = []
  let lastIndex = 0
  let match

  const findMatchingCitationObj = (rawPaperId, pageNum) => {
    const normalized = rawPaperId.startsWith('paper_') ? rawPaperId : `paper_${rawPaperId}`
    const stripped = rawPaperId.replace(/^paper_/, '')
    return (
      citations.find(
        (c) =>
          (c.paper_id === rawPaperId ||
            c.paper_id === normalized ||
            c.paper_id?.replace(/^paper_/, '') === stripped) &&
          Number(c.page) === pageNum
      ) ||
      citations.find(
        (c) =>
          c.paper_id === rawPaperId ||
          c.paper_id === normalized ||
          c.paper_id?.replace(/^paper_/, '') === stripped
      ) ||
      citations[0]
    )
  }

  while ((match = combinedCitationRegex.exec(answerText)) !== null) {
    if (match.index > lastIndex) {
      const textSlice = answerText.slice(lastIndex, match.index)
      parts.push(
        <React.Fragment key={`seg-${lastIndex}`}>
          {renderMathSegment(textSlice, `seg-${lastIndex}`)}
        </React.Fragment>
      )
    }

    const groups = match[1]
      ? parseCitationGroup(match[1])
      : [{ paperId: match[2], pages: [parseInt(match[3], 10)] }]

    groups.forEach(({ paperId: rawPaperId, pages: pageNums }, gIdx) => {
    const refNum = registerPaperId(rawPaperId)

    pageNums.forEach((pageNum, idx) => {
      const matchedCitation = findMatchingCitationObj(rawPaperId, pageNum)
      const resolvedPaperId =
        matchedCitation?.paper_id ||
        (rawPaperId.startsWith('paper_') ? rawPaperId : `paper_${rawPaperId}`)

      const citationPayload = matchedCitation
        ? { ...matchedCitation, page: pageNum }
        : { paper_id: resolvedPaperId, paper_title: rawPaperId, page: pageNum, bbox: null }

      parts.push(
        <button
          key={`${rawPaperId}-${pageNum}-${match.index}-${gIdx}-${idx}`}
          type="button"
          onClick={() => onSelectCitation(citationPayload)}
          className="inline-flex items-center mx-0.5 px-1.5 py-0.5 rounded text-[11px] font-mono font-medium bg-[#6366f1]/15 text-[#818cf8] border border-[#6366f1]/30 hover:bg-[#6366f1]/25 hover:text-[#a5b4fc] hover:border-[#6366f1]/60 transition cursor-pointer align-super leading-none"
          title={
            matchedCitation
              ? `[${refNum}] ${matchedCitation.paper_title} — Page ${pageNum} (Click to open in PDF Reader)`
              : `[${refNum}] ${rawPaperId} — Page ${pageNum}`
          }
        >
          [{refNum}, p.{pageNum}]
        </button>
      )
    })
    })

    lastIndex = combinedCitationRegex.lastIndex
  }

  if (lastIndex < answerText.length) {
    const tailSlice = answerText.slice(lastIndex)
    parts.push(
      <React.Fragment key={`seg-tail-${lastIndex}`}>
        {renderMathSegment(tailSlice, `seg-tail-${lastIndex}`)}
      </React.Fragment>
    )
  }

  return parts
}

export default function ChatWorkspace({
  messages,
  onSendQuery,
  isLoading,
  onSelectCitation,
  activeCitation,
  selectedPaperIds,
}) {
  const [input, setInput] = useState('')

  const handleSubmit = (e) => {
    e.preventDefault()
    const trimmed = input.trim()
    if (!trimmed || isLoading) return
    onSendQuery(trimmed)
    setInput('')
  }

  return (
    <div className="flex flex-col h-full bg-[#09090b] border-r border-[#27272a]">
      {/* Conversation Stream */}
      <div className="flex-1 overflow-y-auto px-6 py-5 space-y-5">
        {messages.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-center px-4 py-12">
            <div className="w-10 h-10 rounded-xl bg-[#18181b] border border-[#27272a] flex items-center justify-center mb-3">
              <BookOpen className="w-4 h-4 text-[#6366f1]" />
            </div>
            <h2 className="text-sm font-semibold text-[#f4f4f5] tracking-tight">
              Ask a question about your papers
            </h2>
            <p className="text-xs text-[#a1a1aa] leading-relaxed max-w-sm mt-1.5">
              Get answers backed by direct citations from your uploaded PDFs. Click any citation badge to jump to that page in the PDF reader.
            </p>
          </div>
        ) : (
          messages.map((msg) => {
            if (msg.role === 'user') {
              return (
                <div key={msg.id} className="flex justify-end pt-2">
                  <div className="max-w-[85%] rounded-2xl rounded-tr-sm bg-[#18181b] border border-[#27272a] px-4 py-2.5 text-[13.5px] text-[#f4f4f5] leading-relaxed shadow-sm">
                    {msg.content}
                  </div>
                </div>
              )
            }

            const { registerPaperId } = buildPaperReferenceMap(msg.content, msg.citations || [])
            const isExtractiveFallback = msg.meta?.model_used === 'extractive-fallback'
            const isInsufficient = msg.status === 'insufficient_context'

            const displayedAnswer = msg.content || (
              isInsufficient
                ? "I couldn't find relevant information in your uploaded papers to answer this question."
                : ""
            )

            return (
              <article
                key={msg.id}
                className="pb-6 border-b border-[#27272a] last:border-b-0 space-y-3.5 relative"
              >
                {/* Hover Telemetry Icon */}
                {msg.meta && (
                  <div className="flex justify-end -mb-2">
                    <div className="relative group inline-flex items-center">
                      <button
                        type="button"
                        className="p-1 rounded text-[#a1a1aa]/70 hover:text-[#f4f4f5] hover:bg-[#18181b] transition cursor-default"
                        aria-label="Response Info"
                      >
                        <Info className="w-3.5 h-3.5" />
                      </button>
                      <div className="pointer-events-none opacity-0 group-hover:opacity-100 transition-opacity duration-150 absolute right-0 top-6 z-30 w-max max-w-xs px-2.5 py-1.5 rounded-md bg-[#18181b] border border-[#27272a] shadow-xl text-[11px] text-[#a1a1aa] font-mono flex items-center gap-2">
                        <span>Search: {msg.meta.retrieval_latency_ms}ms</span>
                        {msg.meta.synthesis_latency_ms != null && (
                          <>
                            <span>·</span>
                            <span>Response: {msg.meta.synthesis_latency_ms}ms</span>
                          </>
                        )}
                        <span>·</span>
                        <span className="text-[#f4f4f5]">{msg.meta.model_used}</span>
                      </div>
                    </div>
                  </div>
                )}

                {/* Red Alert Banner when Extractive Fallback is active */}
                {isExtractiveFallback && (
                  <div className="flex items-start gap-2.5 p-3 rounded-lg bg-rose-500/10 border border-rose-500/35 text-rose-200 text-xs leading-relaxed">
                    <AlertCircle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
                    <div>
                      <p className="font-semibold text-rose-200">
                        Extractive Fallback Active (AI Model Unavailable)
                      </p>
                      <p className="text-rose-300/90 mt-0.5">
                        The AI model could not be reached or is turned off. Instead of a generated summary, the response below shows direct sentences pulled verbatim from your papers that best match your question.
                      </p>
                    </div>
                  </div>
                )}

                {/* Editorial Prose Body */}
                <MarkdownBlockRenderer
                  content={displayedAnswer}
                  citations={msg.citations}
                  onSelectCitation={onSelectCitation}
                  registerPaperId={registerPaperId}
                />

                {/* Interactive Suggested Follow-Up Prompt Pills on Failure / Clarification */}
                {msg.suggested_followups && msg.suggested_followups.length > 0 && (
                  <div className="pt-2 flex flex-wrap gap-2">
                    {msg.suggested_followups.map((sug, sIdx) => (
                      <button
                        key={`${msg.id}-sug-${sIdx}`}
                        type="button"
                        onClick={() => onSendQuery(sug)}
                        className="text-left text-xs px-3 py-1.5 rounded-lg bg-[#6366f1]/10 text-[#a5b4fc] border border-[#6366f1]/30 hover:bg-[#6366f1]/20 hover:border-[#6366f1]/60 transition cursor-pointer"
                      >
                        💡 {sug}
                      </button>
                    ))}
                  </div>
                )}

                {/* Compact Verified Source Passages */}
                {msg.citations && msg.citations.length > 0 && (
                  <div className="pt-3 border-t border-[#27272a]/70 space-y-2">
                    <p className="text-[11px] font-medium uppercase tracking-wider text-[#a1a1aa]">
                      Cited Sources ({msg.citations.length})
                    </p>
                    <div className="grid grid-cols-1 gap-1.5">
                      {msg.citations.map((cit) => {
                        const isActive =
                          activeCitation && activeCitation.chunk_id === cit.chunk_id
                        const refNum = registerPaperId(cit.paper_id)
                        return (
                          <button
                            key={cit.chunk_id}
                            type="button"
                            onClick={() => onSelectCitation(cit)}
                            className={`text-left px-3 py-2 rounded-lg border transition flex flex-col gap-1 cursor-pointer ${
                              isActive
                                ? 'bg-[#6366f1]/12 border-[#6366f1] text-[#f4f4f5]'
                                : 'bg-[#18181b]/80 border-[#27272a] hover:border-[#6366f1]/50 text-[#f4f4f5]'
                            }`}
                          >
                            <div className="flex items-center justify-between gap-2">
                              <div className="flex items-center gap-2 min-w-0">
                                <span className="px-1.5 py-0.5 rounded bg-[#6366f1]/15 text-[#818cf8] border border-[#6366f1]/30 text-[10px] font-mono font-semibold shrink-0">
                                  [{refNum}, p.{cit.page}]
                                </span>
                                <span className="text-xs font-medium text-[#f4f4f5] truncate">
                                  {cit.paper_title}
                                </span>
                              </div>
                              <span className="text-[10px] text-[#a1a1aa] font-mono shrink-0">
                                Page {cit.page}
                              </span>
                            </div>
                            <p className="text-xs text-[#a1a1aa] line-clamp-2 leading-relaxed">
                              &ldquo;{renderMathSegment(cit.snippet, `snip-${cit.chunk_id}`)}&rdquo;
                            </p>
                          </button>
                        )
                      })}
                    </div>
                  </div>
                )}
              </article>
            )
          })
        )}

        {isLoading && (
          <div className="py-4 space-y-2.5 animate-pulse">
            <div className="h-3 w-36 bg-[#18181b] rounded" />
            <div className="h-3 w-full bg-[#18181b] rounded" />
            <div className="h-3 w-5/6 bg-[#18181b] rounded" />
          </div>
        )}
      </div>

      {/* Prominent Prompt Composer */}
      <form
        onSubmit={handleSubmit}
        className="p-4 border-t border-[#27272a] bg-[#09090b]"
      >
        <div className="rounded-2xl bg-[#18181b] border border-[#3f3f46]/80 focus-within:border-[#6366f1] focus-within:ring-2 focus-within:ring-[#6366f1]/25 shadow-[0_8px_30px_rgb(0,0,0,0.45)] transition p-3.5">
          <textarea
            rows={2}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault()
                handleSubmit(e)
              }
            }}
            placeholder="Ask a question about your papers..."
            disabled={isLoading}
            className="w-full bg-transparent resize-none text-sm text-[#f4f4f5] placeholder-[#a1a1aa] leading-relaxed focus:outline-none min-h-[52px]"
          />
          <div className="flex items-center justify-between gap-2 pt-2 mt-1 border-t border-[#27272a]/80">
            <div className="text-[11px] text-[#a1a1aa] flex items-center gap-2">
              {selectedPaperIds && selectedPaperIds.length > 0 ? (
                <span className="px-2 py-0.5 rounded-md bg-[#6366f1]/15 text-[#818cf8] border border-[#6366f1]/30 font-medium">
                  Searching {selectedPaperIds.length} selected paper(s)
                </span>
              ) : (
                <span>Press Enter to ask · Shift+Enter for new line</span>
              )}
            </div>
            <button
              type="submit"
              disabled={isLoading || !input.trim()}
              className="px-4 py-2 rounded-xl bg-[#6366f1] hover:bg-[#4f46e5] disabled:bg-[#27272a] disabled:text-[#a1a1aa]/50 text-white font-semibold text-xs shadow-md transition flex items-center gap-1.5 cursor-pointer"
            >
              <Send className="w-3.5 h-3.5" />
              <span>Ask</span>
            </button>
          </div>
        </div>
      </form>
    </div>
  )
}
