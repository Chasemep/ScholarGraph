import React from 'react'
import {
  X,
  BookOpen,
  MessageSquarePlus,
  ArrowRight,
  AlertTriangle,
  Quote,
} from 'lucide-react'
import { renderMathSegment } from '../../utils/mathRenderer'

/**
 * Sliding detail inspection drawer for selected Papers, Categories, or Citation Links.
 */
export default function NodeDetailDrawer({
  selectedNode,
  selectedEdge,
  selectedCategory,
  onClose,
  onSelectCitation,
  onOpenPaperInReader,
  onAskAboutNode,
}) {
  if (!selectedNode && !selectedEdge && !selectedCategory) return null

  const handleJumpToCitation = (occ) => {
    if (onSelectCitation && occ) {
      onSelectCitation({
        chunk_id: occ.chunk_id,
        paper_id: occ.paper_id,
        paper_title: occ.paper_title,
        page: occ.page || 1,
        section: occ.section || '',
        bbox: occ.bbox || null,
        snippet: occ.snippet || '',
      })
    } else if (onOpenPaperInReader && occ?.paper_id) {
      onOpenPaperInReader(occ.paper_id, occ.page || 1)
    }
  }

  // 1. Category Drawer View
  if (selectedCategory) {
    const categoryDetails = selectedCategory.metadata?.details
    const categoryPapers = categoryDetails?.papers || []

    return (
      <div className="absolute top-14 right-4 bottom-4 max-h-[calc(100%-4.5rem)] w-96 max-w-[92vw] p-4 rounded-xl bg-[#18181b]/95 border border-[#27272a] shadow-2xl flex flex-col gap-3 z-20 overflow-hidden backdrop-blur-md">
        <div className="flex items-center justify-between gap-2 shrink-0">
          <div className="flex items-center gap-1.5 flex-wrap">
            <span className="text-[10px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded bg-[#6366f1]/15 text-[#818cf8] border border-[#6366f1]/30">
              {selectedCategory.metadata?.categoryType || 'Category'} ({categoryPapers.length}{' '}
              {categoryPapers.length === 1 ? 'Paper' : 'Papers'})
            </span>
            {selectedCategory.metadata?.parentLabel && (
              <span className="text-[10px] font-medium px-2 py-0.5 rounded bg-[#27272a] text-[#e4e4e7]">
                in {selectedCategory.metadata.parentLabel}
              </span>
            )}
          </div>
          <button
            type="button"
            onClick={onClose}
            className="text-[#a1a1aa] hover:text-[#f4f4f5] cursor-pointer p-0.5 shrink-0"
            title="Close"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="shrink-0">
          <h4 className="text-sm font-semibold text-[#f4f4f5] leading-snug">
            {selectedCategory.label}
          </h4>
          {selectedCategory.metadata?.subcategories?.length > 0 && (
            <p className="text-[11px] text-[#a1a1aa] mt-1">
              Subcategories:{' '}
              <span className="text-[#e4e4e7]">
                {selectedCategory.metadata.subcategories.join(' · ')}
              </span>
            </p>
          )}
        </div>

        <div className="flex-1 min-h-0 overflow-y-auto space-y-3 pr-1.5">
          {categoryDetails?.overview && (
            <div className="p-3 rounded-lg bg-[#09090b]/80 border border-[#27272a] space-y-2">
              <p className="text-[10px] font-medium uppercase tracking-wider text-[#a1a1aa]">
                Topic Overview
              </p>
              <div className="space-y-2 text-xs text-[#e4e4e7] leading-relaxed">
                {categoryDetails.overview.split('\n\n').map((para, pIdx) => (
                  <p key={pIdx}>
                    {renderMathSegment(para, `cat-ov-${selectedCategory.id}-${pIdx}`)}
                  </p>
                ))}
              </div>
            </div>
          )}

          {(categoryDetails?.methods?.length > 0 || categoryDetails?.datasets?.length > 0) && (
            <div className="space-y-2">
              {categoryDetails.methods?.length > 0 && (
                <div className="p-2.5 rounded-lg bg-[#09090b]/60 border border-[#27272a]">
                  <p className="text-[10px] font-medium uppercase tracking-wider text-emerald-400 mb-1.5">
                    Methods in This Group ({categoryDetails.methods.length})
                  </p>
                  <div className="flex flex-wrap gap-1">
                    {categoryDetails.methods.map((m) => (
                      <span
                        key={m}
                        className="text-[11px] px-2 py-0.5 rounded bg-emerald-500/15 text-emerald-300 border border-emerald-500/30"
                      >
                        {m}
                      </span>
                    ))}
                  </div>
                </div>
              )}
              {categoryDetails.datasets?.length > 0 && (
                <div className="p-2.5 rounded-lg bg-[#09090b]/60 border border-[#27272a]">
                  <p className="text-[10px] font-medium uppercase tracking-wider text-amber-400 mb-1.5">
                    Datasets Evaluated ({categoryDetails.datasets.length})
                  </p>
                  <div className="flex flex-wrap gap-1">
                    {categoryDetails.datasets.map((d) => (
                      <span
                        key={d}
                        className="text-[11px] px-2 py-0.5 rounded bg-amber-500/15 text-amber-300 border border-amber-500/30"
                      >
                        {d}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {categoryPapers.length > 0 && (
            <div className="space-y-2">
              <p className="text-[10px] font-medium uppercase tracking-wider text-[#a1a1aa]">
                Papers &amp; Source Excerpts ({categoryPapers.length})
              </p>
              {categoryPapers.map((pItem, idx) => (
                <div
                  key={`${pItem.paper_id}-${idx}`}
                  className="p-3 rounded-lg bg-[#09090b]/70 border border-[#27272a] space-y-2"
                >
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <p className="text-xs font-semibold text-[#f4f4f5] leading-snug">
                        {pItem.paper_title}
                      </p>
                      <p className="text-[11px] text-[#a1a1aa] mt-0.5">
                        {pItem.authors?.slice(0, 3).join(', ')}
                        {pItem.authors?.length > 3 ? ' et al.' : ''}
                        {pItem.year ? ` · ${pItem.year}` : ''}
                      </p>
                    </div>
                    <button
                      type="button"
                      onClick={() =>
                        handleJumpToCitation({
                          chunk_id: pItem.chunk_id,
                          paper_id: pItem.paper_id,
                          paper_title: pItem.paper_title,
                          page: pItem.page || 1,
                          section: pItem.section || 'Abstract',
                          bbox: pItem.bbox || null,
                          snippet: pItem.excerpt || '',
                        })
                      }
                      className="px-2 py-1 rounded bg-[#6366f1]/15 hover:bg-[#6366f1]/25 text-[#818cf8] border border-[#6366f1]/30 text-[10px] font-mono font-semibold flex items-center gap-1 shrink-0 cursor-pointer transition"
                      title="Open passage in PDF Reader"
                    >
                      <BookOpen className="w-3 h-3" />
                      p.{pItem.page || 1}
                    </button>
                  </div>
                  {pItem.excerpt && (
                    <p className="text-xs text-[#e4e4e7] leading-relaxed bg-[#18181b]/70 p-2 rounded border border-[#27272a]/70">
                      &ldquo;
                      {renderMathSegment(pItem.excerpt, `cat-p-${idx}`)}
                      &rdquo;
                    </p>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>

        {onAskAboutNode && (
          <div className="pt-2 border-t border-[#27272a] shrink-0">
            <button
              type="button"
              onClick={() =>
                onAskAboutNode(
                  `Compare how the papers in the "${selectedCategory.label}" category (${categoryPapers
                    .map((p) => p.paper_title)
                    .join(', ')}) address this topic and build on one another.`
                )
              }
              className="w-full px-3 py-2 rounded-lg bg-[#6366f1] hover:bg-[#4f46e5] text-white text-xs font-medium flex items-center justify-center gap-1.5 transition cursor-pointer"
            >
              <MessageSquarePlus className="w-3.5 h-3.5" />
              Ask About This Category in Chat
            </button>
          </div>
        )}
      </div>
    )
  }

  // 2. Citation Edge Drawer View
  if (selectedEdge) {
    const edgeCitations = selectedEdge.metadata?.citations || []

    return (
      <div className="absolute top-14 right-4 bottom-4 max-h-[calc(100%-4.5rem)] w-96 max-w-[92vw] p-4 rounded-xl bg-[#18181b]/95 border border-[#27272a] shadow-2xl flex flex-col gap-3 z-20 overflow-hidden backdrop-blur-md">
        <div className="flex items-center justify-between gap-2 shrink-0">
          <span className="text-[10px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded bg-[#6366f1]/15 text-[#818cf8] border border-[#6366f1]/30">
            Citation Link ({edgeCitations.length || 1} Found)
          </span>
          <button
            type="button"
            onClick={onClose}
            className="text-[#a1a1aa] hover:text-[#f4f4f5] cursor-pointer p-0.5"
            title="Close"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="p-3 rounded-lg bg-[#09090b] border border-[#27272a] space-y-2 shrink-0">
          <div>
            <p className="text-[10px] font-medium uppercase tracking-wider text-[#a1a1aa]">
              Citing Paper ({selectedEdge.metadata?.citing_year || 'N/A'})
            </p>
            <p className="text-xs font-semibold text-[#f4f4f5] leading-snug mt-0.5">
              {selectedEdge.metadata?.citing_paper_title || selectedEdge.source}
            </p>
          </div>
          <div className="flex items-center gap-1.5 text-[11px] text-[#818cf8] font-medium">
            <ArrowRight className="w-3.5 h-3.5" />
            <span>cites</span>
          </div>
          <div>
            <p className="text-[10px] font-medium uppercase tracking-wider text-[#a1a1aa]">
              Cited Paper ({selectedEdge.metadata?.cited_year || 'N/A'})
            </p>
            <p className="text-xs font-semibold text-[#f4f4f5] leading-snug mt-0.5">
              {selectedEdge.metadata?.cited_paper_title || selectedEdge.target}
            </p>
          </div>
        </div>

        {selectedEdge.metadata?.is_preprint_anomaly && (
          <div className="p-3 rounded-lg bg-amber-500/10 border border-amber-500/35 text-amber-200 text-xs space-y-1 shrink-0">
            <p className="font-semibold flex items-center gap-1.5 text-amber-300">
              <AlertTriangle className="w-3.5 h-3.5 shrink-0" />
              <span>Preprint / Revision Year Difference</span>
            </p>
            <p className="text-[11px] text-amber-200/90 leading-relaxed">
              {selectedEdge.metadata.anomaly_note}
            </p>
          </div>
        )}

        <div className="flex-1 min-h-0 overflow-y-auto space-y-2 pr-1.5">
          <p className="text-[10px] font-medium uppercase tracking-wider text-[#a1a1aa]">
            Exact Citations in Paper (Click to View in PDF)
          </p>
          {edgeCitations.length === 0 ? (
            <p className="text-xs text-[#a1a1aa]">
              No passage details available for this link.
            </p>
          ) : (
            edgeCitations.map((occ, idx) => (
              <button
                key={`${occ.chunk_id || idx}-${occ.page}`}
                type="button"
                onClick={() => handleJumpToCitation(occ)}
                className="w-full text-left p-3 rounded-lg bg-[#09090b]/80 hover:bg-[#27272a]/50 border border-[#27272a] hover:border-[#6366f1]/60 transition space-y-1.5 group cursor-pointer"
              >
                <div className="flex items-center justify-between gap-2">
                  <span className="px-1.5 py-0.5 rounded bg-[#6366f1]/15 text-[#818cf8] border border-[#6366f1]/30 text-[10px] font-mono font-semibold">
                    Citation #{idx + 1} · Page {occ.page}
                  </span>
                  <span className="text-[11px] text-[#818cf8] group-hover:text-[#a5b4fc] flex items-center gap-1 font-medium">
                    <BookOpen className="w-3 h-3" />
                    View in PDF
                  </span>
                </div>
                {occ.section && (
                  <p className="text-[11px] text-[#a1a1aa] font-medium truncate">
                    Section: {occ.section}
                  </p>
                )}
                <p className="text-xs text-[#e4e4e7] leading-relaxed">
                  &ldquo;
                  {renderMathSegment(occ.snippet, `edge-occ-${idx}`)}
                  &rdquo;
                </p>
              </button>
            ))
          )}
        </div>
      </div>
    )
  }

  // 3. Node Drawer View
  const paperRelations = selectedNode.metadata?.relations || []

  return (
    <div className="absolute top-14 right-4 bottom-4 max-h-[calc(100%-4.5rem)] w-96 max-w-[92vw] p-4 rounded-xl bg-[#18181b]/95 border border-[#27272a] shadow-2xl flex flex-col gap-3 z-20 overflow-hidden backdrop-blur-md">
      <div className="flex items-center justify-between gap-2 shrink-0">
        <div className="flex items-center gap-1.5 flex-wrap">
          <span className="text-[10px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded bg-[#6366f1]/15 text-[#818cf8] border border-[#6366f1]/30">
            {selectedNode.type}
          </span>
          {selectedNode.metadata?.group_label && (
            <span className="text-[10px] font-medium px-2 py-0.5 rounded bg-[#27272a] text-[#e4e4e7]">
              {selectedNode.metadata.group_label}
              {selectedNode.metadata.subgroup_label
                ? ` › ${selectedNode.metadata.subgroup_label}`
                : ''}
            </span>
          )}
        </div>
        <div className="flex items-center gap-2 shrink-0">
          {selectedNode.metadata?.year && (
            <span className="text-xs font-mono text-[#a1a1aa]">
              {selectedNode.metadata.year}
            </span>
          )}
          <button
            type="button"
            onClick={onClose}
            className="text-[#a1a1aa] hover:text-[#f4f4f5] cursor-pointer p-0.5"
            title="Close"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      </div>

      <div className="shrink-0">
        <h4 className="text-sm font-semibold text-[#f4f4f5] leading-snug">
          {selectedNode.label}
        </h4>
        {selectedNode.type === 'Paper' && selectedNode.metadata?.authors && (
          <p className="text-xs text-[#a1a1aa] mt-1">
            {selectedNode.metadata.authors.slice(0, 4).join(', ')}
            {selectedNode.metadata.authors.length > 4 ? ' et al.' : ''}
          </p>
        )}
      </div>

      <div className="flex-1 min-h-0 overflow-y-auto space-y-3 pr-1.5">
        {selectedNode.metadata?.description && (
          <div className="p-3 rounded-lg bg-[#09090b]/80 border border-[#27272a] space-y-1">
            <p className="text-[10px] font-medium uppercase tracking-wider text-[#a1a1aa]">
              {selectedNode.type === 'Paper' ? 'Summary' : 'Overview'}
            </p>
            <p className="text-xs text-[#e4e4e7] leading-relaxed">
              {renderMathSegment(selectedNode.metadata.description, `desc-${selectedNode.id}`)}
            </p>
          </div>
        )}

        {selectedNode.type === 'Paper' && selectedNode.metadata && (
          <div className="space-y-2">
            {selectedNode.metadata.methods?.length > 0 && (
              <div className="p-2.5 rounded-lg bg-[#09090b]/60 border border-[#27272a]">
                <p className="text-[10px] font-medium uppercase tracking-wider text-emerald-400 mb-1.5">
                  Methods ({selectedNode.metadata.methods.length})
                </p>
                <div className="flex flex-wrap gap-1">
                  {selectedNode.metadata.methods.map((m) => (
                    <span
                      key={m}
                      className="text-[11px] px-2 py-0.5 rounded bg-emerald-500/15 text-emerald-300 border border-emerald-500/30"
                    >
                      {m}
                    </span>
                  ))}
                </div>
              </div>
            )}
            {selectedNode.metadata.datasets?.length > 0 && (
              <div className="p-2.5 rounded-lg bg-[#09090b]/60 border border-[#27272a]">
                <p className="text-[10px] font-medium uppercase tracking-wider text-amber-400 mb-1.5">
                  Datasets ({selectedNode.metadata.datasets.length})
                </p>
                <div className="flex flex-wrap gap-1">
                  {selectedNode.metadata.datasets.map((d) => (
                    <span
                      key={d}
                      className="text-[11px] px-2 py-0.5 rounded bg-amber-500/15 text-amber-300 border border-amber-500/30"
                    >
                      {d}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {paperRelations.length > 0 && (
          <div className="space-y-2">
            <p className="text-[10px] font-medium uppercase tracking-wider text-[#a1a1aa]">
              Connected Papers ({paperRelations.length})
            </p>
            {paperRelations.map((rel, idx) => (
              <div
                key={`${rel.paper_id}-${idx}`}
                className="p-2.5 rounded-lg bg-[#09090b]/60 border border-[#27272a] space-y-2"
              >
                <div className="flex items-center justify-between gap-2">
                  <span className="text-[10px] font-medium px-1.5 py-0.5 rounded bg-[#6366f1]/15 text-[#818cf8] border border-[#6366f1]/30">
                    {rel.role}
                  </span>
                  <button
                    type="button"
                    onClick={() =>
                      handleJumpToCitation({
                        paper_id: rel.paper_id,
                        paper_title: rel.paper_title,
                        page: rel.page || 1,
                        bbox: rel.bbox || null,
                        section: rel.section || '',
                        snippet: rel.explanation || '',
                      })
                    }
                    className="text-[11px] text-[#818cf8] hover:text-[#a5b4fc] flex items-center gap-1 font-mono cursor-pointer"
                  >
                    <BookOpen className="w-3 h-3" />
                    p.{rel.page || 1}
                  </button>
                </div>
                <p className="text-xs font-medium text-[#f4f4f5]">
                  {rel.paper_title} {rel.year ? `(${rel.year})` : ''}
                </p>
              </div>
            ))}
          </div>
        )}
      </div>

      {onAskAboutNode && selectedNode.type === 'Paper' && (
        <div className="pt-2 border-t border-[#27272a] shrink-0">
          <button
            type="button"
            onClick={() =>
              onAskAboutNode(`Summarize the key contributions and methodology of "${selectedNode.label}".`)
            }
            className="w-full px-3 py-2 rounded-lg bg-[#6366f1] hover:bg-[#4f46e5] text-white text-xs font-medium flex items-center justify-center gap-1.5 transition cursor-pointer"
          >
            <MessageSquarePlus className="w-3.5 h-3.5" />
            Ask About This Paper in Chat
          </button>
        </div>
      )}
    </div>
  )
}

