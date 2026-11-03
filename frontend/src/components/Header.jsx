import React, { useState } from 'react'
import {
  BookOpen,
  Network,
  FileText,
  UploadCloud,
  Activity,
  Trash2,
  CheckSquare,
  Square,
  Settings,
  Key,
  Cpu,
  X,
  Check,
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
  onSaveSettings,
}) {
  const [isSettingsOpen, setIsSettingsOpen] = useState(false)
  const storedKey =
    typeof window !== 'undefined' ? localStorage.getItem('scholargraph_gemini_key') || '' : ''
  const [synthesisMode, setSynthesisMode] = useState(() => {
    if (storedKey === 'LOCAL_FALLBACK') return 'local'
    if (storedKey) return 'custom'
    return 'default'
  })
  const [customApiKey, setCustomApiKey] = useState(
    storedKey && storedKey !== 'LOCAL_FALLBACK' ? storedKey : ''
  )

  const handleApplySettings = (e) => {
    e.preventDefault()
    if (synthesisMode === 'local') {
      localStorage.setItem('scholargraph_gemini_key', 'LOCAL_FALLBACK')
      onSaveSettings?.('Switched synthesis engine to 100% offline Extractive Fallback.')
    } else if (synthesisMode === 'custom' && customApiKey.trim()) {
      localStorage.setItem('scholargraph_gemini_key', customApiKey.trim())
      onSaveSettings?.('Saved custom Gemini API key for grounded synthesis.')
    } else {
      localStorage.removeItem('scholargraph_gemini_key')
      onSaveSettings?.('Using server default synthesis configuration (.env).')
    }
    setIsSettingsOpen(false)
  }

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

        {/* Right Controls: Upload Button + Tab Switcher + Settings + Health Indicator */}
        <div className="flex items-center gap-2.5">
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

          <button
            type="button"
            onClick={() => setIsSettingsOpen(true)}
            className="p-2 rounded-lg bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-300 hover:text-white transition cursor-pointer"
            title="Synthesis & API Key Settings"
          >
            <Settings className="w-4 h-4" />
          </button>

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

      {/* Settings / API Key Configuration Modal (T049) */}
      {isSettingsOpen && (
        <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="w-full max-w-md rounded-2xl bg-slate-900 border border-slate-700 shadow-2xl overflow-hidden">
            <div className="px-5 py-4 border-b border-slate-800 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Settings className="w-4 h-4 text-sky-400" />
                <h3 className="text-sm font-bold text-slate-100">
                  Synthesis Engine &amp; API Key Settings
                </h3>
              </div>
              <button
                type="button"
                onClick={() => setIsSettingsOpen(false)}
                className="text-slate-400 hover:text-white cursor-pointer"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <form onSubmit={handleApplySettings} className="p-5 space-y-4">
              <div className="space-y-2">
                <label className="flex items-start gap-3 p-3 rounded-xl border border-slate-700/80 bg-slate-800/50 cursor-pointer hover:border-sky-500/50 transition">
                  <input
                    type="radio"
                    name="synthesisMode"
                    checked={synthesisMode === 'default'}
                    onChange={() => setSynthesisMode('default')}
                    className="mt-1"
                  />
                  <div>
                    <p className="text-xs font-semibold text-slate-100">
                      Server Default (.env Configuration)
                    </p>
                    <p className="text-[11px] text-slate-400">
                      Uses backend <code className="text-sky-300">GEMINI_API_KEY</code> if configured ({health?.gemini_api_configured ? 'Active' : 'Not set'}), otherwise falls back to offline extractive synthesis.
                    </p>
                  </div>
                </label>

                <label className="flex items-start gap-3 p-3 rounded-xl border border-slate-700/80 bg-slate-800/50 cursor-pointer hover:border-sky-500/50 transition">
                  <input
                    type="radio"
                    name="synthesisMode"
                    checked={synthesisMode === 'custom'}
                    onChange={() => setSynthesisMode('custom')}
                    className="mt-1"
                  />
                  <div className="flex-1 space-y-2">
                    <p className="text-xs font-semibold text-slate-100 flex items-center gap-1.5">
                      <Key className="w-3.5 h-3.5 text-amber-400" />
                      Custom Gemini API Key
                    </p>
                    <input
                      type="password"
                      value={customApiKey}
                      onChange={(e) => {
                        setSynthesisMode('custom')
                        setCustomApiKey(e.target.value)
                      }}
                      placeholder="AIzaSy..."
                      className="w-full px-3 py-1.5 rounded-lg bg-slate-950 border border-slate-700 text-xs text-slate-100 focus:outline-none focus:border-sky-400"
                    />
                  </div>
                </label>

                <label className="flex items-start gap-3 p-3 rounded-xl border border-slate-700/80 bg-slate-800/50 cursor-pointer hover:border-emerald-500/50 transition">
                  <input
                    type="radio"
                    name="synthesisMode"
                    checked={synthesisMode === 'local'}
                    onChange={() => setSynthesisMode('local')}
                    className="mt-1"
                  />
                  <div>
                    <p className="text-xs font-semibold text-emerald-300 flex items-center gap-1.5">
                      <Cpu className="w-3.5 h-3.5" />
                      100% Local Extractive Fallback (Offline Mode)
                    </p>
                    <p className="text-[11px] text-slate-400">
                      Bypasses external LLM calls and synthesizes grounded answers directly from top Cross-Encoder passages.
                    </p>
                  </div>
                </label>
              </div>

              <div className="flex items-center justify-end gap-2 pt-2 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setIsSettingsOpen(false)}
                  className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-xs text-slate-300 cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-1.5 rounded-lg bg-sky-500 hover:bg-sky-400 text-slate-950 text-xs font-bold flex items-center gap-1.5 cursor-pointer"
                >
                  <Check className="w-3.5 h-3.5" />
                  Save Settings
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </>
  )
}
