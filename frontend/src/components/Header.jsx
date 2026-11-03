import React, { useState, useRef, useEffect } from 'react'
import {
  BookOpen,
  Network,
  FileText,
  UploadCloud,
  Trash2,
  CheckSquare,
  Square,
  Settings,
  Key,
  Cpu,
  X,
  Check,
  ChevronDown,
  Library,
  ExternalLink,
} from 'lucide-react'

export default function Header({
  papers = [],
  activePaper,
  selectedPaperIds = [],
  onSelectPaper,
  onTogglePaperFilter,
  onClearPaperFilters,
  onDeletePaper,
  rightTab,
  onChangeRightTab,
  graphNodeCount = 0,
  onOpenUploadModal,
  health,
  onSaveSettings,
}) {
  const [isSettingsOpen, setIsSettingsOpen] = useState(false)
  const [isCorpusOpen, setIsCorpusOpen] = useState(false)
  const corpusPopoverRef = useRef(null)

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

  useEffect(() => {
    const handleClickOutside = (e) => {
      if (corpusPopoverRef.current && !corpusPopoverRef.current.contains(e.target)) {
        setIsCorpusOpen(false)
      }
    }
    if (isCorpusOpen) {
      document.addEventListener('mousedown', handleClickOutside)
    }
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [isCorpusOpen])

  const handleApplySettings = (e) => {
    e.preventDefault()
    if (synthesisMode === 'local') {
      localStorage.setItem('scholargraph_gemini_key', 'LOCAL_FALLBACK')
      onSaveSettings?.('Switched to Offline Mode (Extractive Fallback).')
    } else if (synthesisMode === 'custom' && customApiKey.trim()) {
      localStorage.setItem('scholargraph_gemini_key', customApiKey.trim())
      onSaveSettings?.('Saved custom Gemini API key.')
    } else {
      localStorage.removeItem('scholargraph_gemini_key')
      onSaveSettings?.('Using default AI model settings.')
    }
    setIsSettingsOpen(false)
  }

  return (
    <>
      {/* Single 48px Minimalist Top Navbar */}
      <header className="h-12 px-4 border-b border-[#27272a] bg-[#09090b] flex items-center justify-between shrink-0 select-none z-30">
        {/* Left: App Title + Papers Popover Trigger */}
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 rounded-md bg-[#18181b] border border-[#27272a] flex items-center justify-center">
              <BookOpen className="w-3.5 h-3.5 text-[#6366f1]" />
            </div>
            <h1 className="text-sm font-semibold tracking-tight text-[#f4f4f5]">
              ScholarGraph
            </h1>
          </div>

          <div className="h-4 w-px bg-[#27272a]" />

          {/* Uploaded Papers Popover Container */}
          <div className="relative" ref={corpusPopoverRef}>
            <button
              type="button"
              onClick={() => setIsCorpusOpen((prev) => !prev)}
              className={`px-2.5 py-1 rounded-md border text-xs font-medium flex items-center gap-1.5 transition cursor-pointer ${
                isCorpusOpen || selectedPaperIds.length > 0
                  ? 'bg-[#18181b] border-[#6366f1]/60 text-[#f4f4f5]'
                  : 'bg-[#18181b] hover:bg-[#27272a]/70 border-[#27272a] text-[#a1a1aa] hover:text-[#f4f4f5]'
              }`}
            >
              <Library className="w-3.5 h-3.5 text-[#6366f1]" />
              <span>Papers ({papers.length})</span>
              {selectedPaperIds.length > 0 && (
                <span className="px-1.5 py-0.2 rounded bg-[#6366f1]/20 text-[#818cf8] text-[10px] font-mono">
                  {selectedPaperIds.length} selected
                </span>
              )}
              <ChevronDown
                className={`w-3.5 h-3.5 text-[#a1a1aa] transition-transform ${
                  isCorpusOpen ? 'rotate-180' : ''
                }`}
              />
            </button>

            {isCorpusOpen && (
              <div className="absolute left-0 mt-2 w-[460px] max-w-[92vw] rounded-xl bg-[#18181b] border border-[#27272a] shadow-2xl overflow-hidden z-50">
                <div className="px-3.5 py-2.5 border-b border-[#27272a] bg-[#09090b]/60 flex items-center justify-between">
                  <div>
                    <p className="text-xs font-semibold text-[#f4f4f5]">
                      Uploaded Papers ({papers.length})
                    </p>
                    <p className="text-[11px] text-[#a1a1aa]">
                      Check papers to filter your chat answers, or click a title to read the PDF
                    </p>
                  </div>
                  {selectedPaperIds.length > 0 && (
                    <button
                      type="button"
                      onClick={() => onClearPaperFilters?.()}
                      className="text-[11px] font-medium text-[#818cf8] hover:text-[#a5b4fc] cursor-pointer shrink-0 ml-2"
                    >
                      Clear selection ({selectedPaperIds.length})
                    </button>
                  )}
                </div>

                <div className="max-h-[380px] overflow-y-auto divide-y divide-[#27272a]">
                  {papers.length === 0 ? (
                    <div className="p-6 text-center text-xs text-[#a1a1aa]">
                      No papers uploaded yet. Click &ldquo;Upload PDFs&rdquo; to add papers.
                    </div>
                  ) : (
                    papers.map((paper) => {
                      const isChecked = selectedPaperIds.includes(paper.id)
                      const isCurrent = activePaper?.id === paper.id
                      const authorStr =
                        Array.isArray(paper.authors) && paper.authors.length > 0
                          ? paper.authors.slice(0, 3).join(', ') +
                            (paper.authors.length > 3 ? ' et al.' : '')
                          : 'Unknown Author'

                      return (
                        <div
                          key={paper.id}
                          className={`px-3.5 py-2.5 flex items-start gap-2.5 transition ${
                            isCurrent
                              ? 'bg-[#6366f1]/10'
                              : 'hover:bg-[#27272a]/40'
                          }`}
                        >
                          <button
                            type="button"
                            onClick={() => onTogglePaperFilter(paper.id)}
                            className="mt-0.5 text-[#a1a1aa] hover:text-[#f4f4f5] cursor-pointer shrink-0"
                            title="Include in chat filter"
                          >
                            {isChecked ? (
                              <CheckSquare className="w-4 h-4 text-[#6366f1]" />
                            ) : (
                              <Square className="w-4 h-4" />
                            )}
                          </button>

                          <button
                            type="button"
                            onClick={() => {
                              onSelectPaper(paper)
                              setIsCorpusOpen(false)
                            }}
                            className="flex-1 min-w-0 text-left group cursor-pointer"
                            title="Open in PDF Reader"
                          >
                            <p className="text-xs font-medium text-[#f4f4f5] group-hover:text-[#818cf8] leading-snug line-clamp-2 transition">
                              {paper.title}
                            </p>
                            <div className="mt-1 flex items-center gap-2 text-[11px] text-[#a1a1aa]">
                              <span className="truncate">{authorStr}</span>
                              {paper.year && (
                                <>
                                  <span>·</span>
                                  <span className="font-mono">{paper.year}</span>
                                </>
                              )}
                              <span>·</span>
                              <span className="font-mono">{paper.total_pages}p</span>
                              <ExternalLink className="w-3 h-3 opacity-0 group-hover:opacity-100 text-[#818cf8] transition ml-auto shrink-0" />
                            </div>
                          </button>

                          <button
                            type="button"
                            onClick={() => onDeletePaper(paper.id)}
                            className="mt-0.5 p-1 rounded text-[#a1a1aa] hover:text-rose-400 hover:bg-rose-500/10 transition cursor-pointer shrink-0"
                            title="Remove paper"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      )
                    })
                  )}
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Right Controls: Upload Button + View Switcher + Settings */}
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={onOpenUploadModal}
            className="px-2.5 py-1 rounded-md bg-[#18181b] hover:bg-[#27272a] border border-[#27272a] text-[#f4f4f5] text-xs font-medium flex items-center gap-1.5 transition cursor-pointer"
          >
            <UploadCloud className="w-3.5 h-3.5 text-[#6366f1]" />
            <span>Upload PDFs</span>
          </button>

          <div className="flex items-center bg-[#18181b] p-0.5 rounded-md border border-[#27272a] text-xs">
            <button
              type="button"
              onClick={() => onChangeRightTab('graph')}
              className={`px-2.5 py-1 rounded-[5px] font-medium flex items-center gap-1.5 transition cursor-pointer ${
                rightTab === 'graph'
                  ? 'bg-[#6366f1] text-white shadow-sm'
                  : 'text-[#a1a1aa] hover:text-[#f4f4f5]'
              }`}
            >
              <Network className="w-3.5 h-3.5" />
              <span>Graph ({graphNodeCount})</span>
            </button>
            <button
              type="button"
              onClick={() => onChangeRightTab('pdf')}
              className={`px-2.5 py-1 rounded-[5px] font-medium flex items-center gap-1.5 transition cursor-pointer ${
                rightTab === 'pdf'
                  ? 'bg-[#6366f1] text-white shadow-sm'
                  : 'text-[#a1a1aa] hover:text-[#f4f4f5]'
              }`}
            >
              <FileText className="w-3.5 h-3.5" />
              <span>PDF Reader</span>
            </button>
          </div>

          <button
            type="button"
            onClick={() => setIsSettingsOpen(true)}
            className="p-1.5 rounded-md bg-[#18181b] hover:bg-[#27272a] border border-[#27272a] text-[#a1a1aa] hover:text-[#f4f4f5] transition cursor-pointer"
            title="AI Model & API Key Settings"
          >
            <Settings className="w-3.5 h-3.5" />
          </button>
        </div>
      </header>

      {/* Settings / API Key Configuration Modal */}
      {isSettingsOpen && (
        <div className="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="w-full max-w-md rounded-xl bg-[#18181b] border border-[#27272a] shadow-2xl overflow-hidden">
            <div className="px-5 py-3.5 border-b border-[#27272a] flex items-center justify-between bg-[#09090b]/50">
              <div className="flex items-center gap-2">
                <Settings className="w-4 h-4 text-[#6366f1]" />
                <h3 className="text-sm font-semibold text-[#f4f4f5]">
                  AI Model &amp; API Key Settings
                </h3>
              </div>
              <button
                type="button"
                onClick={() => setIsSettingsOpen(false)}
                className="text-[#a1a1aa] hover:text-[#f4f4f5] cursor-pointer"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <form onSubmit={handleApplySettings} className="p-5 space-y-4">
              <div className="space-y-2">
                <label className="flex items-start gap-3 p-3 rounded-lg border border-[#27272a] bg-[#09090b]/60 cursor-pointer hover:border-[#6366f1]/50 transition">
                  <input
                    type="radio"
                    name="synthesisMode"
                    checked={synthesisMode === 'default'}
                    onChange={() => setSynthesisMode('default')}
                    className="mt-1 accent-[#6366f1]"
                  />
                  <div>
                    <p className="text-xs font-medium text-[#f4f4f5]">
                      Default AI Model
                    </p>
                    <p className="text-[11px] text-[#a1a1aa] mt-0.5">
                      Uses the server&apos;s configured Gemini API key ({health?.gemini_api_configured ? 'Connected' : 'Not configured'}).
                    </p>
                  </div>
                </label>

                <label className="flex items-start gap-3 p-3 rounded-lg border border-[#27272a] bg-[#09090b]/60 cursor-pointer hover:border-[#6366f1]/50 transition">
                  <input
                    type="radio"
                    name="synthesisMode"
                    checked={synthesisMode === 'custom'}
                    onChange={() => setSynthesisMode('custom')}
                    className="mt-1 accent-[#6366f1]"
                  />
                  <div className="flex-1 space-y-2">
                    <p className="text-xs font-medium text-[#f4f4f5] flex items-center gap-1.5">
                      <Key className="w-3.5 h-3.5 text-[#818cf8]" />
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
                      className="w-full px-3 py-1.5 rounded-md bg-[#09090b] border border-[#27272a] text-xs text-[#f4f4f5] focus:outline-none focus:border-[#6366f1]"
                    />
                  </div>
                </label>

                <label className="flex items-start gap-3 p-3 rounded-lg border border-[#27272a] bg-[#09090b]/60 cursor-pointer hover:border-[#6366f1]/50 transition">
                  <input
                    type="radio"
                    name="synthesisMode"
                    checked={synthesisMode === 'local'}
                    onChange={() => setSynthesisMode('local')}
                    className="mt-1 accent-[#6366f1]"
                  />
                  <div>
                    <p className="text-xs font-medium text-[#f4f4f5] flex items-center gap-1.5">
                      <Cpu className="w-3.5 h-3.5 text-[#6366f1]" />
                      Offline Mode (Extractive Fallback)
                    </p>
                    <p className="text-[11px] text-[#a1a1aa] mt-0.5">
                      Skips the AI model and returns direct matching sentences from your papers.
                    </p>
                  </div>
                </label>
              </div>

              <div className="flex items-center justify-end gap-2 pt-2 border-t border-[#27272a]">
                <button
                  type="button"
                  onClick={() => setIsSettingsOpen(false)}
                  className="px-3 py-1.5 rounded-md bg-[#09090b] hover:bg-[#27272a] border border-[#27272a] text-xs text-[#a1a1aa] hover:text-[#f4f4f5] cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-3.5 py-1.5 rounded-md bg-[#6366f1] hover:bg-[#4f46e5] text-white text-xs font-medium flex items-center gap-1.5 cursor-pointer"
                >
                  <Check className="w-3.5 h-3.5" />
                  Save
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </>
  )
}
