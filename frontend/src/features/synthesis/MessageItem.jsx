import React, { useState } from 'react'
import { AlertCircle, Info, ChevronDown } from 'lucide-react'
import { renderMathSegment } from '../../utils/mathRenderer'
import { buildPaperReferenceMap } from '../../utils/citationParser'
import MarkdownBlockRenderer from './MarkdownBlockRenderer'

export default function MessageItem({
  message,
  activeCitation,
  onSelectCitation,
  onSendQuery,
}) {
  const [showTelemetry, setShowTelemetry] = useState(false)

  if (message.role === 'user') {
    return (
      <div className="flex justify-end pt-2">
        <div className="max-w-[85%] rounded-2xl rounded-tr-sm bg-[#18181b] border border-[#27272a] px-4 py-2.5 text-[13.5px] text-[#f4f4f5] leading-relaxed shadow-sm">
          {message.content}
        </div>
      </div>
    )
  }

  const { registerPaperId } = buildPaperReferenceMap(message.content, message.citations || [])
  const isExtractiveFallback = message.meta?.model_used === 'extractive-fallback'
  const isInsufficient = message.status === 'insufficient_context'

  const displayedAnswer =
    message.content ||
    (isInsufficient
      ? "I couldn't find relevant information in your uploaded papers to answer this question."
      : '')

  return (
    <article className="pb-6 border-b border-[#27272a] last:border-b-0 space-y-3.5 relative">
      {/* Response Telemetry Toggle (Sanitized behind collapsible info toggle) */}
      {message.meta && (
        <div className="flex justify-end -mb-2">
          <div className="relative inline-flex items-center">
            <button
              type="button"
              onClick={() => setShowTelemetry((prev) => !prev)}
              className="p-1 rounded text-[#a1a1aa]/70 hover:text-[#f4f4f5] hover:bg-[#18181b] transition flex items-center gap-1 text-[11px]"
              aria-label="Toggle response telemetry"
              title="View latency and inference telemetry"
            >
              <Info className="w-3.5 h-3.5" />
              <ChevronDown
                className={`w-3 h-3 transition-transform ${showTelemetry ? 'rotate-180' : ''}`}
              />
            </button>
            {showTelemetry && (
              <div className="absolute right-0 top-7 z-30 w-max max-w-xs px-2.5 py-1.5 rounded-md bg-[#18181b] border border-[#27272a] shadow-xl text-[11px] text-[#a1a1aa] font-mono flex items-center gap-2">
                <span>Search: {message.meta.retrieval_latency_ms}ms</span>
                {message.meta.synthesis_latency_ms != null && (
                  <>
                    <span>·</span>
                    <span>Response: {message.meta.synthesis_latency_ms}ms</span>
                  </>
                )}
                <span>·</span>
                <span className="text-[#f4f4f5]">{message.meta.model_used}</span>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Notice when Offline / Extractive Fallback is active */}
      {isExtractiveFallback && (
        <div className="flex items-start gap-2.5 p-3 rounded-lg bg-rose-500/10 border border-rose-500/35 text-rose-200 text-xs leading-relaxed">
          <AlertCircle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
          <div>
            <p className="font-semibold text-rose-200">
              Offline Mode Active (Extractive Passages)
            </p>
            <p className="text-rose-300/90 mt-0.5">
              The AI service could not be reached or offline mode is enabled. The response below contains direct excerpts matching your question.
            </p>
          </div>
        </div>
      )}

      {/* Markdown & Formula Body */}
      <MarkdownBlockRenderer
        content={displayedAnswer}
        citations={message.citations}
        onSelectCitation={onSelectCitation}
        registerPaperId={registerPaperId}
      />

      {/* Suggested Follow-Up Prompts */}
      {message.suggested_followups && message.suggested_followups.length > 0 && (
        <div className="pt-2 flex flex-wrap gap-2">
          {message.suggested_followups.map((sug, sIdx) => (
            <button
              key={`${message.id}-sug-${sIdx}`}
              type="button"
              onClick={() => onSendQuery(sug)}
              className="text-left text-xs px-3 py-1.5 rounded-lg bg-[#6366f1]/10 text-[#a5b4fc] border border-[#6366f1]/30 hover:bg-[#6366f1]/20 hover:border-[#6366f1]/60 transition cursor-pointer"
            >
              💡 {sug}
            </button>
          ))}
        </div>
      )}

      {/* Verified Source Passages */}
      {message.citations && message.citations.length > 0 && (
        <div className="pt-3 border-t border-[#27272a]/70 space-y-2">
          <p className="text-[11px] font-medium uppercase tracking-wider text-[#a1a1aa]">
            Cited Sources ({message.citations.length})
          </p>
          <div className="grid grid-cols-1 gap-1.5">
            {message.citations.map((cit) => {
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
}

