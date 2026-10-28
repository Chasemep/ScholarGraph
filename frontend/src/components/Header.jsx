import React from 'react'
import {
  BookOpen,
  Network,
  FileText,
  UploadCloud,
  Activity,
  Trash2,
  CheckSquare,
  Square,
} from 'lucide-react'

export default function Header({
  papers = [],
  activePaper,
  selectedPaperIds = [],
  onSelectPaper,
  onTogglePaperFilter,
  onDeletePaper,
  rightTab,
  onChangeRightTab,
  graphNodeCount = 0,
  onOpenUploadModal,
  health,
}) {
  return (
    <>
      {/* Primary Top Navigation Header */}
      <header className="h-14 px-5 border-b border-slate-800 bg-slate-900 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-sky-500/20 border border-sky-400/40 flex items-center justify-center">
            <BookOpen className="w-4 h-4 text-sky-400" />
          </div>
          <div>
            <h1 className="text-base font-bold tracking-tight text-slate-100 flex items-center gap-2">
              ScholarGraph
              <span className="hidden md:inline-block text-[11px] font-medium px-2 py-0.5 rounded bg-sky-500/15 text-sky-300 border border-sky-500/30">
                Hybrid IR + Knowledge Graph + Spatial Provenance
              </span>
            </h1>
          </div>
        </div>

        {/* Right Controls: Upload Button + Tab Switcher + Health Indicator */}
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={onOpenUploadModal}
            className="px-3 py-1.5 rounded-lg bg-emerald-500/20 hover:bg-emerald-500/30 border border-emerald-400/50 text-emerald-200 text-xs font-semibold flex items-center gap-1.5 transition cursor-pointer shadow-sm"
          >
            <UploadCloud className="w-4 h-4 text-emerald-300" />
            <span>Upload PDFs</span>
          </button>

          <div className="flex items-center bg-slate-800 p-1 rounded-lg border border-slate-700 text-xs">
            <button
              type="button"
              onClick={() => onChangeRightTab('graph')}
              className={`px-3 py-1.5 rounded-md font-semibold flex items-center gap-1.5 transition cursor-pointer ${
                rightTab === 'graph'
                  ? 'bg-sky-500 text-slate-950 shadow-sm'
                  : 'text-slate-300 hover:text-white'
              }`}
            >
              <Network className="w-3.5 h-3.5" />
              Knowledge Graph ({graphNodeCount})
            </button>
            <button
              type="button"
              onClick={() => onChangeRightTab('pdf')}
              className={`px-3 py-1.5 rounded-md font-semibold flex items-center gap-1.5 transition cursor-pointer ${
                rightTab === 'pdf'
                  ? 'bg-sky-500 text-slate-950 shadow-sm'
                  : 'text-slate-300 hover:text-white'
              }`}
            >
              <FileText className="w-3.5 h-3.5" />
              PDF Bounding-Box Reader
            </button>
          </div>

          {health && (
            <span className="hidden sm:flex px-2.5 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/30 text-emerald-300 text-xs items-center gap-1.5">
              <Activity className="w-3.5 h-3.5" />
              API Ready
            </span>
          )}
        </div>
      </header>

      {/* Collection Management & Document Selector Sub-Bar */}
      <div className="px-5 py-2 bg-slate-900/60 border-b border-slate-800 flex items-center gap-2 overflow-x-auto shrink-0">
        <span className="text-xs font-medium text-slate-400 shrink-0">
          Indexed Papers ({papers.length}):
        </span>
        {papers.map((paper) => {
          const isChecked = selectedPaperIds.includes(paper.id)
          const isCurrent = activePaper?.id === paper.id
          return (
            <div
              key={paper.id}
              className={`flex items-center gap-1.5 px-2.5 py-1 rounded-md border text-xs shrink-0 transition ${
                isCurrent
                  ? 'bg-sky-500/15 border-sky-400/50 text-sky-200'
                  : 'bg-slate-800/70 border-slate-700/70 text-slate-300'
              }`}
            >
              <button
                type="button"
                onClick={() => onTogglePaperFilter(paper.id)}
                className="text-slate-400 hover:text-sky-300 cursor-pointer"
                title="Toggle inclusion in Q&A filter"
              >
                {isChecked ? (
                  <CheckSquare className="w-3.5 h-3.5 text-sky-400" />
                ) : (
                  <Square className="w-3.5 h-3.5" />
                )}
              </button>
              <button
                type="button"
                onClick={() => onSelectPaper(paper)}
                className="truncate max-w-[180px] font-medium hover:text-white cursor-pointer"
                title={`${paper.title} (${paper.total_pages} pages) — Click to open in PDF Reader`}
              >
                {paper.title}
              </button>
              <button
                type="button"
                onClick={() => onDeletePaper(paper.id)}
                className="text-slate-500 hover:text-rose-400 ml-1 cursor-pointer"
                title="Remove paper from workspace"
              >
                <Trash2 className="w-3 h-3" />
              </button>
            </div>
          )
        })}
      </div>
    </>
  )
}

