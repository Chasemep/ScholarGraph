import React, { useEffect, useState } from 'react'
import Header from './components/Header'
import ChatWorkspace from './components/ChatWorkspace'
import PDFViewer from './components/PDFViewer'
import GraphCanvas from './components/GraphCanvas'
import UploadModal from './components/UploadModal'
import { CheckCircle2, AlertCircle, X } from 'lucide-react'
import {
  fetchDocuments,
  submitQuery,
  deleteDocument,
  checkSystemHealth,
  fetchKnowledgeGraph,
  highlightKnowledgeGraph,
} from './services/api'

export default function App() {
  const [papers, setPapers] = useState([])
  const [selectedPaperIds, setSelectedPaperIds] = useState([])
  const [activePaper, setActivePaper] = useState(null)
  const [activeCitation, setActiveCitation] = useState(null)
  const [messages, setMessages] = useState([])
  const [isLoading, setIsLoading] = useState(false)
  const [isWorkspaceLoading, setIsWorkspaceLoading] = useState(true)
  const [health, setHealth] = useState(null)
  const [isUploadOpen, setIsUploadOpen] = useState(false)
  const [toast, setToast] = useState(null)

  // Right-pane tab state: 'graph' | 'pdf'
  const [rightTab, setRightTab] = useState('graph')
  const [graphData, setGraphData] = useState({
    elements: { nodes: [], edges: [] },
    total_nodes: 0,
    total_edges: 0,
  })
  const [activeGraphQuery, setActiveGraphQuery] = useState('')

  const showToast = (message, type = 'success') => {
    setToast({ message, type })
    setTimeout(() => {
      setToast((prev) => (prev?.message === message ? null : prev))
    }, 4000)
  }

  const loadWorkspaceData = async () => {
    setIsWorkspaceLoading(true)
    try {
      const docs = await fetchDocuments()
      setPapers(docs)
      if (docs.length > 0 && !activePaper) {
        setActivePaper(docs[0])
      }
    } catch (err) {
      showToast(`Failed to load papers: ${err.message}`, 'error')
    }

    try {
      const graphRes = await fetchKnowledgeGraph({ minDegree: 1 })
      setGraphData(graphRes)
    } catch (err) {
      showToast(`Failed to load knowledge graph: ${err.message}`, 'error')
    } finally {
      setIsWorkspaceLoading(false)
    }
  }

  useEffect(() => {
    loadWorkspaceData()
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

      const citedChunkIds = (res.citations || []).map((c) => c.chunk_id)
      const highlightedGraph = await highlightKnowledgeGraph({
        query: queryText,
        activeChunkIds: citedChunkIds,
        paperIds: filterIds,
      })
      setGraphData(highlightedGraph)
      setActiveGraphQuery(queryText)

      if (res.citations && res.citations.length > 0) {
        const topCit = res.citations[0]
        setActiveCitation(topCit)
        const targetPaper = papers.find((p) => p.id === topCit.paper_id)
        if (targetPaper) {
          setActivePaper(targetPaper)
        }
      }
    } catch (err) {
      showToast(`Search error: ${err.message}`, 'error')
      setMessages((prev) => [
        ...prev,
        {
          id: `err-${Date.now()}`,
          role: 'assistant',
          content: `Unable to complete search: ${err.message}`,
          status: 'error',
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
    setRightTab('pdf')
  }

  const handleResetGraphHighlight = async () => {
    try {
      const freshGraph = await fetchKnowledgeGraph({ minDegree: 1 })
      setGraphData(freshGraph)
      setActiveGraphQuery('')
    } catch (err) {
      showToast(`Failed to reset graph: ${err.message}`, 'error')
    }
  }

  const handleOpenPaperFromGraph = (paperId, pageNum = 1) => {
    const found = papers.find((p) => p.id === paperId)
    if (found) {
      setActivePaper(found)
      setActiveCitation({
        paper_id: paperId,
        paper_title: found.title,
        page: pageNum,
        bbox: null,
      })
      setRightTab('pdf')
    }
  }

  const togglePaperFilter = (paperId) => {
    setSelectedPaperIds((prev) =>
      prev.includes(paperId) ? prev.filter((id) => id !== paperId) : [...prev, paperId]
    )
  }

  const handleDeletePaper = async (paperId) => {
    try {
      const target = papers.find((p) => p.id === paperId)
      await deleteDocument(paperId)
      const updated = papers.filter((p) => p.id !== paperId)
      setPapers(updated)
      setSelectedPaperIds((prev) => prev.filter((id) => id !== paperId))
      if (activePaper?.id === paperId) {
        setActivePaper(updated[0] || null)
      }
      const freshGraph = await fetchKnowledgeGraph({ minDegree: 1 })
      setGraphData(freshGraph)
      showToast(`Removed "${target?.title || paperId}" from your papers.`)
    } catch (err) {
      showToast(`Failed to delete paper: ${err.message}`, 'error')
    }
  }

  return (
    <div className="h-screen w-screen overflow-hidden flex flex-col bg-[#09090b] text-[#f4f4f5] relative">
      {/* Toast Notification Banner */}
      {toast && (
        <div
          className={`fixed bottom-5 right-5 z-50 px-3.5 py-2.5 rounded-lg border shadow-2xl flex items-center gap-2.5 text-xs font-medium backdrop-blur-md transition ${
            toast.type === 'error'
              ? 'bg-rose-950/90 border-rose-500/40 text-rose-200'
              : 'bg-[#18181b]/95 border-[#27272a] text-[#f4f4f5]'
          }`}
        >
          {toast.type === 'error' ? (
            <AlertCircle className="w-4 h-4 text-rose-400 shrink-0" />
          ) : (
            <CheckCircle2 className="w-4 h-4 text-[#6366f1] shrink-0" />
          )}
          <span>{toast.message}</span>
          <button
            type="button"
            onClick={() => setToast(null)}
            className="ml-2 text-[#a1a1aa] hover:text-[#f4f4f5] cursor-pointer"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      )}

      <Header
        papers={papers}
        activePaper={activePaper}
        selectedPaperIds={selectedPaperIds}
        onSelectPaper={(paper) => {
          setActivePaper(paper)
          setRightTab('pdf')
        }}
        onTogglePaperFilter={togglePaperFilter}
        onClearPaperFilters={() => setSelectedPaperIds([])}
        onDeletePaper={handleDeletePaper}
        rightTab={rightTab}
        onChangeRightTab={setRightTab}
        graphNodeCount={graphData?.total_nodes || 0}
        onOpenUploadModal={() => setIsUploadOpen(true)}
        health={health}
        onSaveSettings={(msg) => showToast(msg, 'success')}
      />

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
        <div className="lg:col-span-7 h-full min-h-0 overflow-hidden relative">
          {isWorkspaceLoading ? (
            <div className="h-full w-full flex flex-col items-center justify-center p-8 bg-[#09090b] space-y-3 animate-pulse">
              <div className="w-10 h-10 rounded-lg bg-[#18181b] border border-[#27272a]" />
              <div className="h-3.5 w-48 bg-[#18181b] rounded" />
              <div className="h-2.5 w-32 bg-[#18181b]/70 rounded" />
            </div>
          ) : rightTab === 'graph' ? (
            <GraphCanvas
              graphData={graphData}
              activeQuery={activeGraphQuery}
              onResetHighlight={handleResetGraphHighlight}
              onOpenPaperInReader={handleOpenPaperFromGraph}
              onAskAboutNode={handleSendQuery}
            />
          ) : (
            <PDFViewer
              activePaper={activePaper}
              papers={papers}
              onSelectPaper={setActivePaper}
              activeCitation={activeCitation}
            />
          )}
        </div>
      </main>

      <UploadModal
        isOpen={isUploadOpen}
        onClose={() => setIsUploadOpen(false)}
        onUploadComplete={() => {
          loadWorkspaceData()
          showToast('PDF upload complete. Your papers and graph have been updated.')
        }}
      />
    </div>
  )
}
