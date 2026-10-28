import React, { useEffect, useState } from 'react'
import { BookOpen, Trash2, CheckSquare, Square, Activity } from 'lucide-react'
import ChatWorkspace from './components/ChatWorkspace'
import PDFViewer from './components/PDFViewer'
import {
  fetchDocuments,
  submitQuery,
  deleteDocument,
  checkSystemHealth,
} from './services/api'

export default function App() {
  const [papers, setPapers] = useState([])
  const [selectedPaperIds, setSelectedPaperIds] = useState([])
  const [activePaper, setActivePaper] = useState(null)
  const [activeCitation, setActiveCitation] = useState(null)
  const [messages, setMessages] = useState([])
  const [isLoading, setIsLoading] = useState(false)
  const [health, setHealth] = useState(null)

  const loadPapers = async () => {
    try {
      const docs = await fetchDocuments()
      setPapers(docs)
      if (docs.length > 0 && !activePaper) {
        setActivePaper(docs[0])
      }
    } catch (err) {
      console.error('Failed to load papers:', err)
    }
  }

  useEffect(() => {
    loadPapers()
    checkSystemHealth()
      .then(setHealth)
      .catch(() => {})
  }, [])

  const handleSendQuery = async (queryText) => {
    const userMsg = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: queryText,
    }
    setMessages((prev) => [...prev, userMsg])
    setIsLoading(true)

    try {
      const filterIds = selectedPaperIds.length > 0 ? selectedPaperIds : null
      const res = await submitQuery({
        query: queryText,
        topK: 5,
        paperIds: filterIds,
      })

      const assistantMsg = {
        id: `assistant-${Date.now()}`,
        role: 'assistant',
        content: res.answer,
        status: res.status,
        citations: res.citations || [],
        meta: {
          model_used: res.model_used,
          retrieval_latency_ms: res.retrieval_latency_ms,
          synthesis_latency_ms: res.synthesis_latency_ms,
        },
      }
      setMessages((prev) => [...prev, assistantMsg])

      // Automatically focus the top-ranked citation in the PDF viewer
      if (res.citations && res.citations.length > 0) {
        handleSelectCitation(res.citations[0])
      }
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          id: `err-${Date.now()}`,
          role: 'assistant',
          content: `Error: ${err.message}`,
          status: 'insufficient_context',
          citations: [],
        },
      ])
    } finally {
      setIsLoading(false)
    }
  }

  const handleSelectCitation = (citation) => {
    setActiveCitation(citation)
    const targetPaper = papers.find((p) => p.id === citation.paper_id)
    if (targetPaper) {
      setActivePaper(targetPaper)
    }
  }

  const togglePaperFilter = (paperId) => {
    setSelectedPaperIds((prev) =>
      prev.includes(paperId) ? prev.filter((id) => id !== paperId) : [...prev, paperId]
    )
  }

  const handleDeletePaper = async (paperId) => {
    try {
      await deleteDocument(paperId)
      const updated = papers.filter((p) => p.id !== paperId)
      setPapers(updated)
      setSelectedPaperIds((prev) => prev.filter((id) => id !== paperId))
      if (activePaper?.id === paperId) {
        setActivePaper(updated[0] || null)
      }
    } catch (err) {
      console.error('Delete failed:', err)
    }
  }

  return (
    <div className="h-screen w-screen overflow-hidden flex flex-col bg-slate-950 text-slate-100">
      {/* Top Navigation Header */}
      <header className="h-14 px-5 border-b border-slate-800 bg-slate-900 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-sky-500/20 border border-sky-400/40 flex items-center justify-center">
            <BookOpen className="w-4 h-4 text-sky-400" />
          </div>
          <div>
            <h1 className="text-base font-bold tracking-tight text-slate-100 flex items-center gap-2">
              ScholarGraph
              <span className="text-[11px] font-medium px-2 py-0.5 rounded bg-sky-500/15 text-sky-300 border border-sky-500/30">
                Hybrid IR + Spatial Provenance
              </span>
            </h1>
          </div>
        </div>

        <div className="flex items-center gap-3 text-xs">
          <span className="text-slate-400">
            Indexed Corpus: <strong className="text-slate-200">{papers.length} papers</strong>
          </span>
          {health && (
            <span className="px-2.5 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/30 text-emerald-300 flex items-center gap-1.5">
              <Activity className="w-3.5 h-3.5" />
              API Ready
            </span>
          )}
        </div>
      </header>

      {/* Corpus Filter Bar */}
      <div className="px-5 py-2 bg-slate-900/60 border-b border-slate-800 flex items-center gap-2 overflow-x-auto shrink-0">
        <span className="text-xs font-medium text-slate-400 shrink-0">Corpus Filter:</span>
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
                onClick={() => togglePaperFilter(paper.id)}
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
                onClick={() => setActivePaper(paper)}
                className="truncate max-w-[180px] font-medium hover:text-white cursor-pointer"
                title={paper.title}
              >
                {paper.title}
              </button>
              <button
                type="button"
                onClick={() => handleDeletePaper(paper.id)}
                className="text-slate-500 hover:text-rose-400 ml-1 cursor-pointer"
                title="Remove paper from workspace"
              >
                <Trash2 className="w-3 h-3" />
              </button>
            </div>
          )
        })}
      </div>

      {/* Main Split-Screen Workspace: Left = Chat, Right = Synchronized PDF Reader */}
      <main className="flex-1 grid grid-cols-1 lg:grid-cols-12 min-h-0">
        <div className="lg:col-span-5 h-full min-h-0 overflow-hidden">
          <ChatWorkspace
            messages={messages}
            onSendQuery={handleSendQuery}
            isLoading={isLoading}
            onSelectCitation={handleSelectCitation}
            activeCitation={activeCitation}
            selectedPaperIds={selectedPaperIds}
          />
        </div>
        <div className="lg:col-span-7 h-full min-h-0 overflow-hidden">
          <PDFViewer
            activePaper={activePaper}
            papers={papers}
            onSelectPaper={setActivePaper}
            activeCitation={activeCitation}
          />
        </div>
      </main>
    </div>
  )
}
