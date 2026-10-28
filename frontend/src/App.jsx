import React, { useEffect, useState } from 'react'
import Header from './components/Header'
import ChatWorkspace from './components/ChatWorkspace'
import PDFViewer from './components/PDFViewer'
import GraphCanvas from './components/GraphCanvas'
import UploadModal from './components/UploadModal'
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
  const [health, setHealth] = useState(null)
  const [isUploadOpen, setIsUploadOpen] = useState(false)

  // Right-pane tab state: 'graph' | 'pdf'
  const [rightTab, setRightTab] = useState('graph')
  const [graphData, setGraphData] = useState({
    elements: { nodes: [], edges: [] },
    total_nodes: 0,
    total_edges: 0,
  })
  const [activeGraphQuery, setActiveGraphQuery] = useState('')

  const loadWorkspaceData = async () => {
    try {
      const docs = await fetchDocuments()
      setPapers(docs)
      if (docs.length > 0 && !activePaper) {
        setActivePaper(docs[0])
      }
    } catch (err) {
      console.error('Failed to load documents:', err)
    }

    try {
      const graphRes = await fetchKnowledgeGraph({ minDegree: 1 })
      setGraphData(graphRes)
    } catch (err) {
      console.error('Failed to load knowledge graph:', err)
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
    setRightTab('pdf')
  }

  const handleResetGraphHighlight = async () => {
    try {
      const freshGraph = await fetchKnowledgeGraph({ minDegree: 1 })
      setGraphData(freshGraph)
      setActiveGraphQuery('')
    } catch (err) {
      console.error('Failed to reset graph:', err)
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
      await deleteDocument(paperId)
      const updated = papers.filter((p) => p.id !== paperId)
      setPapers(updated)
      setSelectedPaperIds((prev) => prev.filter((id) => id !== paperId))
      if (activePaper?.id === paperId) {
        setActivePaper(updated[0] || null)
      }
      const freshGraph = await fetchKnowledgeGraph({ minDegree: 1 })
      setGraphData(freshGraph)
    } catch (err) {
      console.error('Delete failed:', err)
    }
  }

  return (
    <div className="h-screen w-screen overflow-hidden flex flex-col bg-slate-950 text-slate-100">
      <Header
        papers={papers}
        activePaper={activePaper}
        selectedPaperIds={selectedPaperIds}
        onSelectPaper={(paper) => {
          setActivePaper(paper)
          setRightTab('pdf')
        }}
        onTogglePaperFilter={togglePaperFilter}
        onDeletePaper={handleDeletePaper}
        rightTab={rightTab}
        onChangeRightTab={setRightTab}
        graphNodeCount={graphData?.total_nodes || 0}
        onOpenUploadModal={() => setIsUploadOpen(true)}
        health={health}
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
        <div className="lg:col-span-7 h-full min-h-0 overflow-hidden">
          {rightTab === 'graph' ? (
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
        onUploadComplete={loadWorkspaceData}
      />
    </div>
  )
}
