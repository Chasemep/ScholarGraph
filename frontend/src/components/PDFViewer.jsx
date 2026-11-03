import React, { useEffect, useRef, useState } from 'react'
import { FileText, ZoomIn, ZoomOut, Highlighter } from 'lucide-react'
import * as pdfjsLib from 'pdfjs-dist'
import pdfjsWorkerUrl from 'pdfjs-dist/build/pdf.worker.min.mjs?url'
import { getPaperPdfUrl } from '../services/api'

pdfjsLib.GlobalWorkerOptions.workerSrc = pdfjsWorkerUrl

/**
 * Renders a single page inside the continuous scrollable PDF stream,
 * including the citation bounding-box highlight when active on this page.
 */
function PDFPageItem({
  pdfDoc,
  pageNumber,
  totalPages,
  scale,
  isCitedPage,
  activeCitation,
  pageRef,
  highlightRef,
  onCitedPageRendered,
}) {
  const canvasRef = useRef(null)
  const [dimensions, setDimensions] = useState({ width: 0, height: 0 })

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
        setDimensions({ width: viewport.width, height: viewport.height })

        renderTask = page.render({
          canvasContext: context,
          viewport,
        })
        return renderTask.promise
      })
      .then(() => {
        if (!cancelled && isCitedPage && onCitedPageRendered) {
          onCitedPageRendered()
        }
      })
      .catch(() => {})

    return () => {
      cancelled = true
      if (renderTask && renderTask.cancel) {
        renderTask.cancel()
      }
    }
  }, [pdfDoc, pageNumber, scale])

  const showHighlight =
    isCitedPage && activeCitation?.bbox && dimensions.width > 0

  return (
    <div
      ref={pageRef}
      data-page-number={pageNumber}
      className="relative shadow-2xl border border-[#27272a] bg-white shrink-0 rounded-sm"
      style={{
        width: dimensions.width || 'auto',
        height: dimensions.height || 'auto',
        minHeight: dimensions.height ? undefined : Math.round(780 * scale),
        minWidth: dimensions.width ? undefined : Math.round(600 * scale),
      }}
    >
      <canvas ref={canvasRef} className="block" />

      {/* Subtle Page Number Pill */}
      <div className="absolute bottom-2.5 right-3 px-2 py-0.5 rounded bg-[#09090b]/75 text-[#f4f4f5] text-[10px] font-mono pointer-events-none backdrop-blur-sm">
        Page {pageNumber} of {totalPages}
      </div>

      {/* Citation Bounding-Box Highlight Overlay */}
      {showHighlight && (
        <div
          ref={highlightRef}
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
  )
}

export default function PDFViewer({
  activePaper,
  papers = [],
  onSelectPaper,
  activeCitation,
}) {
  const scrollContainerRef = useRef(null)
  const pageRefs = useRef({})
  const highlightRef = useRef(null)

  const [pdfDoc, setPdfDoc] = useState(null)
  const [totalPages, setTotalPages] = useState(0)
  const [scale, setScale] = useState(1.2)
  const [loadError, setLoadError] = useState(null)

  // Load PDF document when activePaper changes
  useEffect(() => {
    if (!activePaper) {
      setPdfDoc(null)
      setTotalPages(0)
      return
    }
    let cancelled = false
    setLoadError(null)
    setPdfDoc(null)
    setTotalPages(0)
    pageRefs.current = {}

    const pdfUrl = getPaperPdfUrl(activePaper.id)
    const loadingTask = pdfjsLib.getDocument(pdfUrl)

    loadingTask.promise
      .then((loadedPdf) => {
        if (cancelled) return
        setPdfDoc(loadedPdf)
        setTotalPages(loadedPdf.numPages)
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

  const scrollToActiveCitation = () => {
    if (!activeCitation || !activePaper || activeCitation.paper_id !== activePaper.id) {
      return
    }
    const targetPage = Math.max(1, Number(activeCitation.page) || 1)
    if (highlightRef.current) {
      highlightRef.current.scrollIntoView({ behavior: 'smooth', block: 'center' })
    } else if (pageRefs.current[targetPage]) {
      pageRefs.current[targetPage].scrollIntoView({ behavior: 'smooth', block: 'start' })
    }
  }

  // Smoothly scroll to the cited page/highlight whenever activeCitation changes
  useEffect(() => {
    if (!pdfDoc || !activeCitation || !activePaper) return
    if (activeCitation.paper_id !== activePaper.id) return

    const timer = setTimeout(() => {
      scrollToActiveCitation()
    }, 120)
    return () => clearTimeout(timer)
  }, [activeCitation, pdfDoc, activePaper?.id])

  const hasActiveCitationInCurrentPaper =
    activeCitation &&
    activePaper &&
    activeCitation.paper_id === activePaper.id

  const pageNumbers = Array.from({ length: totalPages }, (_, i) => i + 1)

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
          {totalPages > 0 && (
            <span className="text-[11px] font-mono text-[#a1a1aa] px-2 py-0.5 rounded bg-[#18181b] border border-[#27272a] shrink-0">
              {totalPages} {totalPages === 1 ? 'Page' : 'Pages'}
            </span>
          )}
        </div>

        {/* Zoom Controls */}
        <div className="flex items-center gap-2">
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

      {/* Active Highlight Banner (Click to re-scroll to highlighted citation) */}
      {hasActiveCitationInCurrentPaper && (
        <div className="px-4 py-1.5 bg-[#18181b] border-b border-[#27272a] flex items-center justify-between text-xs text-[#f4f4f5] shrink-0">
          <div className="flex items-center gap-2 truncate">
            <Highlighter className="w-3.5 h-3.5 text-[#6366f1] shrink-0" />
            <span className="truncate text-[#a1a1aa]">
              Highlighted citation on{' '}
              <strong className="text-[#f4f4f5]">Page {activeCitation.page}</strong>
              {activeCitation.section ? ` (${activeCitation.section})` : ''}
            </span>
          </div>
          <button
            type="button"
            onClick={scrollToActiveCitation}
            className="text-[11px] font-medium text-[#818cf8] hover:text-[#a5b4fc] shrink-0 ml-2 cursor-pointer"
          >
            Jump to highlight
          </button>
        </div>
      )}

      {/* Continuous Scrollable PDF Document Stream */}
      <div
        ref={scrollContainerRef}
        className="flex-1 overflow-auto flex flex-col items-center gap-6 p-6 bg-[#09090b]"
      >
        {loadError ? (
          <div className="my-auto text-center space-y-2 p-6 rounded-xl bg-[#18181b] border border-[#27272a] max-w-md">
            <p className="text-sm text-rose-400 font-medium">{loadError}</p>
            <p className="text-xs text-[#a1a1aa]">
              Select a paper from the dropdown above to read its pages.
            </p>
          </div>
        ) : (
          pageNumbers.map((pageNum) => {
            const isCitedPage =
              hasActiveCitationInCurrentPaper &&
              Number(activeCitation.page) === pageNum
            return (
              <PDFPageItem
                key={`${activePaper?.id}-p${pageNum}`}
                pdfDoc={pdfDoc}
                pageNumber={pageNum}
                totalPages={totalPages}
                scale={scale}
                isCitedPage={isCitedPage}
                activeCitation={activeCitation}
                pageRef={(el) => {
                  if (el) pageRefs.current[pageNum] = el
                }}
                highlightRef={isCitedPage ? highlightRef : null}
                onCitedPageRendered={scrollToActiveCitation}
              />
            )
          })
        )}
      </div>
    </div>
  )
}
