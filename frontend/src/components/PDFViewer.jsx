import React, { useEffect, useRef, useState } from 'react'
import { FileText, ChevronLeft, ChevronRight, ZoomIn, ZoomOut, Highlighter } from 'lucide-react'
import * as pdfjsLib from 'pdfjs-dist'
import pdfjsWorkerUrl from 'pdfjs-dist/build/pdf.worker.min.mjs?url'
import { getPaperPdfUrl } from '../services/api'

pdfjsLib.GlobalWorkerOptions.workerSrc = pdfjsWorkerUrl

export default function PDFViewer({
  activePaper,
  papers = [],
  onSelectPaper,
  activeCitation,
}) {
  const canvasRef = useRef(null)
  const containerRef = useRef(null)

  const [pdfDoc, setPdfDoc] = useState(null)
  const [pageNumber, setPageNumber] = useState(1)
  const [totalPages, setTotalPages] = useState(1)
  const [scale, setScale] = useState(1.25)
  const [renderDimensions, setRenderDimensions] = useState({ width: 0, height: 0 })
  const [loadError, setLoadError] = useState(null)

  // Load PDF document when activePaper changes
  useEffect(() => {
    if (!activePaper) {
      setPdfDoc(null)
      return
    }
    let cancelled = false
    setLoadError(null)
    const pdfUrl = getPaperPdfUrl(activePaper.id)

    const loadingTask = pdfjsLib.getDocument(pdfUrl)
    loadingTask.promise
      .then((loadedPdf) => {
        if (cancelled) return
        setPdfDoc(loadedPdf)
        setTotalPages(loadedPdf.numPages)
        if (activeCitation && activeCitation.paper_id === activePaper.id) {
          setPageNumber(Math.min(loadedPdf.numPages, Math.max(1, activeCitation.page)))
        } else {
          setPageNumber(1)
        }
      })
      .catch((err) => {
        if (!cancelled) {
          setLoadError(err?.message || 'Unable to render PDF document.')
        }
      })

    return () => {
      cancelled = true
    }
  }, [activePaper?.id])

  // Jump to cited page immediately when activeCitation changes
  useEffect(() => {
    if (activeCitation && activePaper && activeCitation.paper_id === activePaper.id) {
      setPageNumber(activeCitation.page)
    }
  }, [activeCitation, activePaper?.id])

  // Render current PDF page onto HTML5 canvas
  useEffect(() => {
    if (!pdfDoc || !canvasRef.current) return
    let renderTask = null
    let cancelled = false

    pdfDoc
      .getPage(pageNumber)
      .then((page) => {
        if (cancelled) return
        const viewport = page.getViewport({ scale })
        const canvas = canvasRef.current
        if (!canvas) return
        const context = canvas.getContext('2d')
        canvas.width = viewport.width
        canvas.height = viewport.height
        setRenderDimensions({ width: viewport.width, height: viewport.height })

        renderTask = page.render({
          canvasContext: context,
          viewport,
        })
        return renderTask.promise
      })
      .catch(() => {})

    return () => {
      cancelled = true
      if (renderTask && renderTask.cancel) {
        renderTask.cancel()
      }
    }
  }, [pdfDoc, pageNumber, scale])

  // Determine whether the current page has an active bounding-box highlight
  const showHighlight =
    activeCitation &&
    activePaper &&
    activeCitation.paper_id === activePaper.id &&
    Number(activeCitation.page) === Number(pageNumber) &&
    activeCitation.bbox &&
    renderDimensions.width > 0

  return (
    <div className="flex flex-col h-full bg-[#09090b]">
      {/* Reader Control Bar */}
      <div className="h-10 px-4 border-b border-[#27272a] bg-[#09090b] flex flex-wrap items-center justify-between gap-2 shrink-0">
        <div className="flex items-center gap-2 min-w-0">
          <FileText className="w-3.5 h-3.5 text-[#6366f1] shrink-0" />
          <select
            value={activePaper?.id || ''}
            onChange={(e) => {
              const found = papers.find((p) => p.id === e.target.value)
              if (found && onSelectPaper) onSelectPaper(found)
            }}
            className="bg-[#18181b] border border-[#27272a] rounded-md px-2.5 py-1 text-xs text-[#f4f4f5] max-w-xs truncate focus:outline-none focus:border-[#6366f1]"
          >
            {papers.map((p) => (
              <option key={p.id} value={p.id}>
                {p.title} ({p.year || 'N/A'})
              </option>
            ))}
          </select>
        </div>

        {/* Page Navigation & Zoom Controls */}
        <div className="flex items-center gap-2">
          <div className="flex items-center gap-1 bg-[#18181b] rounded-md px-2 py-0.5 border border-[#27272a]">
            <button
              type="button"
              onClick={() => setPageNumber((p) => Math.max(1, p - 1))}
              disabled={pageNumber <= 1}
              className="p-0.5 text-[#a1a1aa] hover:text-[#f4f4f5] disabled:opacity-40 cursor-pointer"
              title="Previous Page"
            >
              <ChevronLeft className="w-3.5 h-3.5" />
            </button>
            <span className="text-[11px] font-mono text-[#f4f4f5] px-1.5">
              {pageNumber} / {totalPages}
            </span>
            <button
              type="button"
              onClick={() => setPageNumber((p) => Math.min(totalPages, p + 1))}
              disabled={pageNumber >= totalPages}
              className="p-0.5 text-[#a1a1aa] hover:text-[#f4f4f5] disabled:opacity-40 cursor-pointer"
              title="Next Page"
            >
              <ChevronRight className="w-3.5 h-3.5" />
            </button>
          </div>

          <div className="flex items-center gap-1 bg-[#18181b] rounded-md px-2 py-0.5 border border-[#27272a]">
            <button
              type="button"
              onClick={() => setScale((s) => Math.max(0.75, +(s - 0.15).toFixed(2)))}
              className="p-0.5 text-[#a1a1aa] hover:text-[#f4f4f5] cursor-pointer"
              title="Zoom Out"
            >
              <ZoomOut className="w-3.5 h-3.5" />
            </button>
            <span className="text-[11px] font-mono text-[#a1a1aa] px-1">
              {Math.round(scale * 100)}%
            </span>
            <button
              type="button"
              onClick={() => setScale((s) => Math.min(2.2, +(s + 0.15).toFixed(2)))}
              className="p-0.5 text-[#a1a1aa] hover:text-[#f4f4f5] cursor-pointer"
              title="Zoom In"
            >
              <ZoomIn className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </div>

      {/* Active Highlight Banner */}
      {showHighlight && (
        <div className="px-4 py-1.5 bg-[#18181b] border-b border-[#27272a] flex items-center justify-between text-xs text-[#f4f4f5]">
          <div className="flex items-center gap-2 truncate">
            <Highlighter className="w-3.5 h-3.5 text-[#6366f1] shrink-0" />
            <span className="truncate text-[#a1a1aa]">
              Highlighted citation on <strong className="text-[#f4f4f5]">Page {pageNumber}</strong>
              {activeCitation.section ? ` (${activeCitation.section})` : ''}
            </span>
          </div>
        </div>
      )}

      {/* PDF Canvas & Bounding-Box Overlay */}
      <div
        ref={containerRef}
        className="flex-1 overflow-auto flex justify-center p-6 bg-[#09090b]"
      >
        {loadError ? (
          <div className="self-center text-center space-y-2 p-6 rounded-xl bg-[#18181b] border border-[#27272a] max-w-md">
            <p className="text-sm text-rose-400 font-medium">{loadError}</p>
            <p className="text-xs text-[#a1a1aa]">
              Select a paper from the dropdown above to read its pages.
            </p>
          </div>
        ) : (
          <div
            className="relative shadow-2xl border border-[#27272a] bg-white self-start"
            style={{
              width: renderDimensions.width || 'auto',
              height: renderDimensions.height || 'auto',
            }}
          >
            <canvas ref={canvasRef} className="block" />

            {/* Highlight Overlay */}
            {showHighlight && (
              <div
                data-testid="pdf-bbox-highlight"
                style={{
                  position: 'absolute',
                  left: `${Math.max(0, activeCitation.bbox.x * 100 - 1)}%`,
                  top: `${Math.max(0, activeCitation.bbox.y * 100 - 0.5)}%`,
                  width: `${Math.min(100, activeCitation.bbox.width * 100 + 2)}%`,
                  height: `${Math.min(100, activeCitation.bbox.height * 100 + 1.5)}%`,
                }}
                className="pointer-events-none rounded-md bg-indigo-500/25 border-2 border-[#6366f1] shadow-[0_0_20px_rgba(99,102,241,0.55)] transition-all duration-300"
              />
            )}
          </div>
        )}
      </div>
    </div>
  )
}
