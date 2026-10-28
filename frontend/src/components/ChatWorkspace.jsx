import React, { useState } from 'react'
import { Send, Sparkles, BookOpen, ShieldCheck, AlertTriangle, Clock, MapPin } from 'lucide-react'

const SUGGESTED_PROMPTS = [
  'Compare the parameter efficiency and memory overhead of LoRA versus full fine-tuning.',
  'How does Scaled Dot-Product Attention work and why is the 1/sqrt(d_k) scaling factor used?',
  'How does FlashAttention reduce GPU HBM memory accesses from O(N^2) to O(N)?',
  'Compare Rotary Position Embedding (RoPE) in RoFormer with sinusoidal positional encodings.',
]

/**
 * Parses inline citation markers like [paper_hu2021, Page 4] and turns them into
 * interactive buttons linked to the corresponding CitationToken object.
 */
function renderAnswerWithCitations(answerText, citations = [], onSelectCitation) {
  if (!answerText) return null

  const tokenRegex = /\[([a-zA-Z0-9_-]+),\s*Page\s*(\d+)\]/g
  const parts = []
  let lastIndex = 0
  let match

  while ((match = tokenRegex.exec(answerText)) !== null) {
    if (match.index > lastIndex) {
      parts.push(answerText.slice(lastIndex, match.index))
    }
    const paperId = match[1]
    const pageNum = parseInt(match[2], 10)

    const matchedCitation =
      citations.find((c) => c.paper_id === paperId && Number(c.page) === pageNum) ||
      citations.find((c) => c.paper_id === paperId) ||
      citations[0]

    parts.push(
      <button
        key={`${paperId}-${pageNum}-${match.index}`}
        type="button"
        onClick={() => matchedCitation && onSelectCitation(matchedCitation)}
        className="inline-flex items-center gap-1 mx-1 px-2 py-0.5 rounded-md text-xs font-semibold bg-sky-500/20 text-sky-300 border border-sky-400/40 hover:bg-sky-400/30 hover:border-sky-300 transition cursor-pointer align-baseline shadow-sm"
        title={
          matchedCitation
            ? `Click to jump to ${matchedCitation.paper_title} — Page ${pageNum} & highlight source passage`
            : `Jump to ${paperId}, Page ${pageNum}`
        }
      >
        <MapPin className="w-3 h-3 text-amber-300 shrink-0" />
        <span>
          {paperId.replace(/^paper_/, '')} · p.{pageNum}
        </span>
      </button>
    )

    lastIndex = tokenRegex.lastIndex
  }

  if (lastIndex < answerText.length) {
    parts.push(answerText.slice(lastIndex))
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
    <div className="flex flex-col h-full bg-slate-900/70 border-r border-slate-800">
      {/* Workspace Subheader */}
      <div className="px-4 py-3 border-b border-slate-800 flex items-center justify-between bg-slate-900/90">
        <div className="flex items-center gap-2">
          <Sparkles className="w-4 h-4 text-sky-400" />
          <h2 className="text-sm font-semibold text-slate-200">
            Grounded Literature Synthesis
          </h2>
        </div>
        <span className="text-xs px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-300 border border-emerald-500/30 flex items-center gap-1">
          <ShieldCheck className="w-3.5 h-3.5" />
          Zero-Hallucination Guard
        </span>
      </div>

      {/* Message History */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 ? (
          <div className="space-y-4 py-6">
            <div className="p-4 rounded-xl bg-slate-800/60 border border-slate-700/70 space-y-2">
              <h3 className="text-sm font-semibold text-sky-300 flex items-center gap-2">
                <BookOpen className="w-4 h-4" />
                Ask Comparative Questions Across Your Corpus
              </h3>
              <p className="text-xs text-slate-300 leading-relaxed">
                Every claim is verified via Hybrid Retrieval (<code className="text-sky-300">BM25 + ChromaDB → RRF → Cross-Encoder</code>).
                Click any citation badge to jump directly to the exact PDF page and highlight the source paragraph.
              </p>
            </div>

            <div className="space-y-2">
              <p className="text-xs font-medium uppercase tracking-wider text-slate-400">
                Try a sample comparative query:
              </p>
              <div className="grid grid-cols-1 gap-2">
                {SUGGESTED_PROMPTS.map((prompt) => (
                  <button
                    key={prompt}
                    type="button"
                    onClick={() => onSendQuery(prompt)}
                    disabled={isLoading}
                    className="text-left text-xs p-3 rounded-lg bg-slate-800/40 hover:bg-slate-800 border border-slate-700/60 hover:border-sky-500/50 text-slate-200 transition flex items-start justify-between gap-2 group"
                  >
                    <span>{prompt}</span>
                    <Send className="w-3.5 h-3.5 text-slate-500 group-hover:text-sky-400 shrink-0 mt-0.5" />
                  </button>
                ))}
              </div>
            </div>
          </div>
        ) : (
          messages.map((msg) => (
            <div
              key={msg.id}
              className={`rounded-xl p-4 ${
                msg.role === 'user'
                  ? 'bg-sky-600/20 border border-sky-500/30 ml-6'
                  : 'bg-slate-800/80 border border-slate-700/80 mr-2'
              }`}
            >
              <div className="flex items-center justify-between mb-1.5">
                <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                  {msg.role === 'user' ? 'Researcher Query' : 'ScholarGraph Synthesis'}
                </span>
                {msg.role === 'assistant' && msg.meta && (
                  <div className="flex items-center gap-2 text-[11px] text-slate-400">
                    <span className="flex items-center gap-1">
                      <Clock className="w-3 h-3 text-sky-400" />
                      IR: {msg.meta.retrieval_latency_ms}ms
                    </span>
                    <span className="px-1.5 py-0.5 rounded bg-slate-900/80 text-slate-300 border border-slate-700">
                      {msg.meta.model_used}
                    </span>
                  </div>
                )}
              </div>

              {msg.role === 'user' ? (
                <p className="text-sm text-slate-100">{msg.content}</p>
              ) : (
                <div className="space-y-3">
                  {msg.status === 'insufficient_context' && (
                    <div className="flex items-center gap-2 p-2.5 rounded-lg bg-amber-500/10 border border-amber-500/30 text-amber-200 text-xs">
                      <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0" />
                      <span>
                        Out-of-Scope / Insufficient Evidence Guardrail Triggered — 0 Hallucinations
                      </span>
                    </div>
                  )}

                  <div className="text-sm text-slate-100 leading-relaxed whitespace-pre-wrap">
                    {renderAnswerWithCitations(msg.content, msg.citations, onSelectCitation)}
                  </div>

                  {/* Grounded Provenance Citation Cards */}
                  {msg.citations && msg.citations.length > 0 && (
                    <div className="pt-2 border-t border-slate-700/70 space-y-2">
                      <p className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">
                        Verified Source Passages (Click to Highlight in PDF):
                      </p>
                      <div className="grid grid-cols-1 gap-1.5">
                        {msg.citations.map((cit) => {
                          const isActive =
                            activeCitation && activeCitation.chunk_id === cit.chunk_id
                          return (
                            <button
                              key={cit.chunk_id}
                              type="button"
                              onClick={() => onSelectCitation(cit)}
                              className={`text-left p-2.5 rounded-lg border transition flex flex-col gap-1 ${
                                isActive
                                  ? 'bg-amber-400/15 border-amber-400 text-amber-100 shadow-md'
                                  : 'bg-slate-900/70 border-slate-700/70 hover:border-sky-400/60 text-slate-200'
                              }`}
                            >
                              <div className="flex items-center justify-between gap-2">
                                <span className="text-xs font-semibold text-sky-300 flex items-center gap-1.5 truncate">
                                  <MapPin className="w-3.5 h-3.5 text-amber-400 shrink-0" />
                                  {cit.paper_title}
                                </span>
                                <div className="flex items-center gap-1.5 shrink-0">
                                  <span className="text-[11px] px-1.5 py-0.5 rounded bg-slate-800 text-amber-300 font-mono">
                                    Page {cit.page}
                                  </span>
                                  <span className="text-[11px] px-1.5 py-0.5 rounded bg-emerald-500/15 text-emerald-300 font-mono">
                                    {(cit.relevance_score * 100).toFixed(1)}%
                                  </span>
                                </div>
                              </div>
                              <p className="text-xs text-slate-400 line-clamp-2 italic">
                                &ldquo;{cit.snippet}&rdquo;
                              </p>
                            </button>
                          )
                        })}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          ))
        )}

        {isLoading && (
          <div className="rounded-xl p-4 bg-slate-800/60 border border-slate-700/70 animate-pulse space-y-2">
            <div className="h-3 w-44 bg-slate-700 rounded" />
            <div className="h-3 w-full bg-slate-700/70 rounded" />
            <div className="h-3 w-5/6 bg-slate-700/70 rounded" />
          </div>
        )}
      </div>

      {/* Prompt Input Bar */}
      <form onSubmit={handleSubmit} className="p-3 border-t border-slate-800 bg-slate-900">
        {selectedPaperIds && selectedPaperIds.length > 0 && (
          <div className="mb-2 text-[11px] text-sky-300 flex items-center gap-1.5">
            <span>Filtering across {selectedPaperIds.length} selected paper(s)</span>
          </div>
        )}
        <div className="flex items-center gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask a scientific question across the indexed papers..."
            disabled={isLoading}
            className="flex-1 bg-slate-800/90 border border-slate-700 focus:border-sky-400 rounded-lg px-3.5 py-2.5 text-sm text-slate-100 placeholder-slate-400 focus:outline-none transition"
          />
          <button
            type="submit"
            disabled={isLoading || !input.trim()}
            className="px-4 py-2.5 rounded-lg bg-sky-500 hover:bg-sky-400 disabled:bg-slate-700 disabled:text-slate-500 text-slate-950 font-semibold text-sm transition flex items-center gap-1.5 cursor-pointer"
          >
            <Send className="w-4 h-4" />
            <span>Ask</span>
          </button>
        </div>
      </form>
    </div>
  )
}

