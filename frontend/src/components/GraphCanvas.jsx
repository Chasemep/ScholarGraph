import React, { useEffect, useRef, useState } from 'react'
import cytoscape from 'cytoscape'
import cola from 'cytoscape-cola'
import {
  Network,
  ZoomIn,
  ZoomOut,
  Maximize2,
  RotateCcw,
  Sparkles,
  ExternalLink,
  X,
  BookOpen,
  MessageSquarePlus,
} from 'lucide-react'

if (!cytoscape.prototype.hasInitialColaRegistered) {
  cytoscape.use(cola)
  cytoscape.prototype.hasInitialColaRegistered = true
}

const VIEW_MODES = [
  { id: 'CORE', label: 'Core Lineage (Papers + Methods + Datasets)' },
  { id: 'METHODS', label: 'Papers + Methods' },
  { id: 'DATASETS', label: 'Papers + Datasets' },
  { id: 'CITATIONS', label: 'Paper Citations Only' },
  { id: 'ALL', label: 'Full Graph (+Authors & Metrics)' },
]

const ENTITY_LEGEND = [
  { type: 'Paper', color: '#38BDF8' },
  { type: 'Method', color: '#34D399' },
  { type: 'Dataset', color: '#FBBF24' },
  { type: 'Metric', color: '#F472B6' },
  { type: 'Author', color: '#A78BFA' },
]

function formatShortNodeLabel(data) {
  const raw = String(data.label || '')
  if (data.type === 'Paper') {
    const shortTitle = raw.includes(':') ? raw.split(':')[0].trim() : raw
    const truncated =
      shortTitle.length > 28 ? `${shortTitle.slice(0, 26).trim()}…` : shortTitle
    const year = data.metadata?.year ? ` (${data.metadata.year})` : ''
    return `${truncated}${year}`
  }
  return raw.length > 26 ? `${raw.slice(0, 24).trim()}…` : raw
}

function computeNodeSize(data) {
  if (typeof data.relevance_score === 'number' && data.relevance_score !== null) {
    if (data.relevance_score >= 0.7) {
      return Math.round(42 + data.relevance_score * 24)
    }
    return 26
  }
  const deg = Number(data.degree || 1)
  if (data.type === 'Paper') {
    return Math.min(64, 42 + Math.round(Math.sqrt(deg) * 5))
  }
  return Math.min(48, 26 + Math.round(Math.sqrt(deg) * 4))
}

function getNodeShape(type) {
  switch (type) {
    case 'Paper':
      return 'round-rectangle'
    case 'Method':
      return 'hexagon'
    case 'Dataset':
      return 'diamond'
    case 'Metric':
      return 'octagon'
    case 'Author':
    default:
      return 'ellipse'
  }
}

function shouldKeepNode(nodeType, viewMode) {
  switch (viewMode) {
    case 'CORE':
      return nodeType === 'Paper' || nodeType === 'Method' || nodeType === 'Dataset'
    case 'METHODS':
      return nodeType === 'Paper' || nodeType === 'Method'
    case 'DATASETS':
      return nodeType === 'Paper' || nodeType === 'Dataset'
    case 'CITATIONS':
      return nodeType === 'Paper'
    case 'ALL':
    default:
      return true
  }
}

export default function GraphCanvas({
  graphData,
  activeQuery,
  onResetHighlight,
  onOpenPaperInReader,
  onAskAboutNode,
}) {
  const containerRef = useRef(null)
  const cyRef = useRef(null)

  const [selectedNode, setSelectedNode] = useState(null)
  const [viewMode, setViewMode] = useState('CORE')
  const [visibleCounts, setVisibleCounts] = useState({ nodes: 0, edges: 0 })

  useEffect(() => {
    if (!containerRef.current || !graphData?.elements) return

    const rawNodes = graphData.elements.nodes || []
    const rawEdges = graphData.elements.edges || []

    const filteredNodes = rawNodes.filter((n) =>
      shouldKeepNode(n.data.type, viewMode)
    )
    const allowedIds = new Set(filteredNodes.map((n) => n.data.id))
    const filteredEdges = rawEdges.filter(
      (e) => allowedIds.has(e.data.source) && allowedIds.has(e.data.target)
    )

    setVisibleCounts({ nodes: filteredNodes.length, edges: filteredEdges.length })

    const cyElements = [
      ...filteredNodes.map((n) => ({
        group: 'nodes',
        data: {
          ...n.data,
          displayLabel: formatShortNodeLabel(n.data),
          computedSize: computeNodeSize(n.data),
          computedShape: getNodeShape(n.data.type),
        },
        classes: [
          n.data.type === 'Paper' ? 'paper-node' : 'entity-node',
          n.data.is_dimmed ? 'dimmed-node' : '',
          typeof n.data.relevance_score === 'number' && n.data.relevance_score >= 0.7
            ? 'active-node'
            : '',
        ]
          .filter(Boolean)
          .join(' '),
      })),
      ...filteredEdges.map((e) => ({
        group: 'edges',
        data: { ...e.data },
        classes: [
          e.data.type === 'CITES' ? 'cites-edge' : 'concept-edge',
          e.data.is_active ? 'active-edge' : '',
          e.data.is_dimmed ? 'dimmed-edge' : '',
        ]
          .filter(Boolean)
          .join(' '),
      })),
    ]

    if (cyRef.current) {
      cyRef.current.destroy()
    }

    const cy = cytoscape({
      container: containerRef.current,
      elements: cyElements,
      minZoom: 0.35,
      maxZoom: 2.5,
      wheelSensitivity: 0.25,
      style: [
        {
          selector: 'node',
          style: {
            label: 'data(displayLabel)',
            width: 'data(computedSize)',
            height: 'data(computedSize)',
            shape: 'data(computedShape)',
            'background-color': 'data(color)',
            'border-width': 2.5,
            'border-color': '#0f172a',
            color: '#f1f5f9',
            'font-size': '11px',
            'font-weight': 600,
            'text-valign': 'bottom',
            'text-halign': 'center',
            'text-margin-y': 7,
            'text-wrap': 'wrap',
            'text-max-width': '135px',
            'text-outline-width': 2.5,
            'text-outline-color': '#020617',
            'transition-property': 'width, height, opacity, border-width, border-color',
            'transition-duration': '250ms',
          },
        },
        {
          selector: 'node.paper-node',
          style: {
            'border-width': 3,
            'border-color': '#e0f2fe',
            'font-size': '12px',
            'font-weight': 700,
          },
        },
        {
          selector: 'node.active-node',
          style: {
            'border-width': 4.5,
            'border-color': '#facc15',
            'font-size': '12px',
            'z-index': 999,
          },
        },
        {
          selector: 'node.focused-node',
          style: {
            'border-width': 4,
            'border-color': '#38bdf8',
            'z-index': 999,
          },
        },
        {
          selector: 'node.dimmed-node',
          style: {
            opacity: 0.16,
          },
        },
        {
          selector: 'edge',
          style: {
            width: 1.5,
            'line-color': '#334155',
            'target-arrow-color': '#475569',
            'target-arrow-shape': 'triangle',
            'arrow-scale': 0.85,
            'curve-style': 'bezier',
            label: '',
            opacity: 0.65,
          },
        },
        {
          selector: 'edge.cites-edge',
          style: {
            width: 2.4,
            'line-color': '#0284c7',
            'target-arrow-color': '#38bdf8',
            'line-style': 'solid',
            opacity: 0.85,
          },
        },
        {
          selector: 'edge.active-edge',
          style: {
            width: 4,
            'line-color': '#facc15',
            'target-arrow-color': '#facc15',
            label: 'data(label)',
            color: '#fef08a',
            'font-size': '9px',
            'font-weight': 'bold',
            'text-rotation': 'autorotate',
            'text-background-opacity': 0.9,
            'text-background-color': '#020617',
            'text-background-padding': '3px',
            opacity: 1.0,
            'z-index': 999,
          },
        },
        {
          selector: 'edge.neighbor-edge',
          style: {
            width: 3,
            'line-color': '#38bdf8',
            'target-arrow-color': '#38bdf8',
            label: 'data(label)',
            color: '#bae6fd',
            'font-size': '9px',
            'font-weight': 600,
            'text-rotation': 'autorotate',
            'text-background-opacity': 0.9,
            'text-background-color': '#020617',
            'text-background-padding': '3px',
            opacity: 1.0,
            'z-index': 990,
          },
        },
        {
          selector: 'edge.dimmed-edge',
          style: {
            opacity: 0.12,
            label: '',
          },
        },
      ],
      layout: {
        name: 'cola',
        animate: true,
        maxSimulationTime: 2200,
        avoidOverlap: true,
        handleDisconnected: true,
        nodeSpacing: (node) => (node.data('type') === 'Paper' ? 68 : 48),
        edgeLength: (edge) => (edge.data('type') === 'CITES' ? 210 : 165),
        randomize: false,
        padding: 48,
      },
    })

    cy.on('tap', 'node', (evt) => {
      const clicked = evt.target
      setSelectedNode(clicked.data())

      const neighborhood = clicked.closedNeighborhood()
      cy.elements().removeClass('focused-node neighbor-edge dimmed-node dimmed-edge')
      cy.nodes().not(neighborhood.nodes()).addClass('dimmed-node')
      cy.edges().not(neighborhood.edges()).addClass('dimmed-edge')
      clicked.addClass('focused-node')
      neighborhood.edges().addClass('neighbor-edge')
    })

    cy.on('tap', (evt) => {
      if (evt.target === cy) {
        setSelectedNode(null)
        cy.elements().removeClass('focused-node neighbor-edge')
        cy.nodes().forEach((n) => {
          if (n.data('is_dimmed')) n.addClass('dimmed-node')
          else n.removeClass('dimmed-node')
        })
        cy.edges().forEach((e) => {
          if (e.data('is_dimmed')) e.addClass('dimmed-edge')
          else e.removeClass('dimmed-edge')
        })
      }
    })

    cyRef.current = cy

    return () => {
      if (cyRef.current) {
        cyRef.current.destroy()
        cyRef.current = null
      }
    }
  }, [graphData, viewMode])

  const handleZoom = (factor) => {
    if (!cyRef.current) return
    const currentZoom = cyRef.current.zoom()
    cyRef.current.zoom({
      level: currentZoom * factor,
      renderedPosition: {
        x: containerRef.current.clientWidth / 2,
        y: containerRef.current.clientHeight / 2,
      },
    })
  }

  const handleFit = () => {
    if (cyRef.current) {
      cyRef.current.fit(undefined, 45)
    }
  }

  const paperRelations = selectedNode?.metadata?.paper_relations || []

  return (
    <div className="flex flex-col h-full bg-slate-950 relative">
      {/* Graph Toolbar */}
      <div className="px-4 py-2.5 border-b border-slate-800 bg-slate-900/90 flex flex-wrap items-center justify-between gap-2 z-10">
        <div className="flex items-center gap-2">
          <Network className="w-4 h-4 text-emerald-400" />
          <span className="text-xs font-semibold text-slate-200">
            Knowledge Graph
          </span>
          <span className="text-[11px] px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700 font-mono">
            {visibleCounts.nodes} Nodes · {visibleCounts.edges} Edges
          </span>
        </div>

        <div className="flex items-center gap-2 flex-wrap">
          <select
            value={viewMode}
            onChange={(e) => {
              setSelectedNode(null)
              setViewMode(e.target.value)
            }}
            className="bg-slate-800 border border-slate-700 rounded-lg px-2.5 py-1 text-xs text-slate-100 focus:outline-none focus:border-sky-400"
          >
            {VIEW_MODES.map((m) => (
              <option key={m.id} value={m.id}>
                {m.label}
              </option>
            ))}
          </select>

          <div className="flex items-center gap-1 bg-slate-800 rounded-md px-1.5 py-1 border border-slate-700">
            <button
              type="button"
              onClick={() => handleZoom(1.25)}
              className="p-0.5 text-slate-300 hover:text-sky-400 cursor-pointer"
              title="Zoom In"
            >
              <ZoomIn className="w-4 h-4" />
            </button>
            <button
              type="button"
              onClick={() => handleZoom(0.8)}
              className="p-0.5 text-slate-300 hover:text-sky-400 cursor-pointer"
              title="Zoom Out"
            >
              <ZoomOut className="w-4 h-4" />
            </button>
            <button
              type="button"
              onClick={handleFit}
              className="p-0.5 text-slate-300 hover:text-sky-400 cursor-pointer"
              title="Fit Graph to Screen"
            >
              <Maximize2 className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>

      {/* Prompt-Activated Relevance Banner */}
      {activeQuery && (
        <div className="px-4 py-1.5 bg-amber-500/15 border-b border-amber-400/40 flex items-center justify-between text-xs text-amber-200 z-10">
          <div className="flex items-center gap-2 truncate">
            <Sparkles className="w-3.5 h-3.5 text-amber-300 shrink-0" />
            <span className="truncate">
              Active Prompt Path: Highlighting relevant nodes &amp; 4px paths for{' '}
              <strong>&ldquo;{activeQuery}&rdquo;</strong>
            </span>
          </div>
          {onResetHighlight && (
            <button
              type="button"
              onClick={onResetHighlight}
              className="ml-2 px-2 py-0.5 rounded bg-amber-400/20 hover:bg-amber-400/30 border border-amber-400/50 text-amber-100 flex items-center gap-1 shrink-0 cursor-pointer"
            >
              <RotateCcw className="w-3 h-3" />
              Reset
            </button>
          )}
        </div>
      )}

      {/* Cytoscape Canvas */}
      <div ref={containerRef} className="flex-1 w-full h-full bg-slate-950" />

      {/* Entity Legend Overlay (Bottom Left) */}
      <div className="absolute bottom-4 left-4 p-2.5 rounded-xl bg-slate-900/90 border border-slate-800 backdrop-blur-sm flex flex-wrap items-center gap-3 text-[11px] text-slate-300 pointer-events-none">
        {ENTITY_LEGEND.filter((item) => shouldKeepNode(item.type, viewMode)).map(
          (item) => (
            <div key={item.type} className="flex items-center gap-1.5">
              <span
                className="w-3 h-3 rounded-sm inline-block"
                style={{ backgroundColor: item.color }}
              />
              <span>
                <strong>{item.type}</strong>
              </span>
            </div>
          )
        )}
        <span className="text-slate-500">· Click any node to explain &amp; inspect</span>
      </div>

      {/* Detailed Node Explanation & Lineage Drawer (Right Overlay) */}
      {selectedNode && (
        <div className="absolute top-14 right-4 bottom-4 w-96 max-w-[92vw] p-4 rounded-xl bg-slate-900/95 border border-slate-700 shadow-2xl flex flex-col gap-3 z-20 overflow-hidden backdrop-blur-md">
          {/* Header */}
          <div className="flex items-center justify-between gap-2 shrink-0">
            <span
              className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded text-slate-950"
              style={{ backgroundColor: selectedNode.color }}
            >
              {selectedNode.type}
            </span>
            <div className="flex items-center gap-2">
              <span className="text-xs font-mono text-slate-400">
                {selectedNode.degree} Connection{selectedNode.degree === 1 ? '' : 's'}
              </span>
              <button
                type="button"
                onClick={() => setSelectedNode(null)}
                className="text-slate-400 hover:text-white cursor-pointer p-0.5"
                title="Close Inspector"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          </div>

          {/* Node Title */}
          <div className="shrink-0">
            <h4 className="text-base font-bold text-slate-100 leading-snug">
              {selectedNode.label}
            </h4>
            {selectedNode.type === 'Paper' && selectedNode.metadata?.authors && (
              <p className="text-xs text-slate-400 mt-0.5">
                {selectedNode.metadata.authors.slice(0, 4).join(', ')}
                {selectedNode.metadata.authors.length > 4 ? ' et al.' : ''} (
                {selectedNode.metadata.year || 'N/A'})
              </p>
            )}
          </div>

          {/* Scrollable Body: Definition + Per-Paper Relationship Explanations */}
          <div className="flex-1 overflow-y-auto space-y-3 pr-1">
            {/* What is this node? */}
            {selectedNode.metadata?.description && (
              <div className="p-3 rounded-lg bg-slate-800/80 border border-slate-700/70 space-y-1">
                <p className="text-[10px] font-semibold uppercase tracking-wider text-sky-400">
                  {selectedNode.type === 'Paper' ? 'Paper Abstract / Summary' : `What is ${selectedNode.label}?`}
                </p>
                <p className="text-xs text-slate-200 leading-relaxed">
                  {selectedNode.metadata.description}
                </p>
              </div>
            )}

            {/* For Paper nodes: show extracted Methods & Datasets badges */}
            {selectedNode.type === 'Paper' && selectedNode.metadata && (
              <div className="space-y-2">
                {selectedNode.metadata.methods?.length > 0 && (
                  <div className="p-2.5 rounded-lg bg-slate-800/50 border border-slate-700/60">
                    <p className="text-[10px] font-semibold uppercase tracking-wider text-emerald-400 mb-1.5">
                      Key Methods Used / Proposed
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
                  <div className="p-2.5 rounded-lg bg-slate-800/50 border border-slate-700/60">
                    <p className="text-[10px] font-semibold uppercase tracking-wider text-amber-400 mb-1.5">
                      Evaluated Datasets
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

            {/* Relationship to Each Connected Paper */}
            {paperRelations.length > 0 && (
              <div className="space-y-2">
                <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-400">
                  {selectedNode.type === 'Paper'
                    ? `Citation Lineage (${paperRelations.length})`
                    : `Relation to Connected Papers (${paperRelations.length})`}
                </p>
                {paperRelations.map((rel, idx) => {
                  const isOriginator =
                    rel.role === 'Introduces / Proposes' || rel.role === 'Cites Foundation'
                  return (
                    <div
                      key={`${rel.paper_id}-${idx}`}
                      className="p-2.5 rounded-lg bg-slate-800/60 border border-slate-700/80 space-y-1.5"
                    >
                      <div className="flex items-center justify-between gap-2">
                        <span
                          className={`text-[10px] font-bold uppercase px-1.5 py-0.5 rounded ${
                            isOriginator
                              ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40'
                              : 'bg-sky-500/20 text-sky-300 border border-sky-500/40'
                          }`}
                        >
                          {rel.role}
                        </span>
                        <button
                          type="button"
                          onClick={() =>
                            onOpenPaperInReader && onOpenPaperInReader(rel.paper_id, rel.page)
                          }
                          className="text-[11px] text-sky-400 hover:text-sky-300 flex items-center gap-1 font-medium cursor-pointer"
                          title="Open this paper in the PDF Reader"
                        >
                          <BookOpen className="w-3 h-3" />
                          p.{rel.page || 1}
                        </button>
                      </div>

                      <p className="text-xs font-semibold text-slate-100">
                        {rel.paper_title} {rel.year ? `(${rel.year})` : ''}
                      </p>

                      <p className="text-xs text-slate-300 italic leading-relaxed">
                        &ldquo;{rel.explanation}&rdquo;
                      </p>
                    </div>
                  )
                })}
              </div>
            )}
          </div>

          {/* Action Footer */}
          <div className="pt-2 border-t border-slate-800 flex flex-col gap-1.5 shrink-0">
            {onAskAboutNode && (
              <button
                type="button"
                onClick={() =>
                  onAskAboutNode(
                    selectedNode.type === 'Paper'
                      ? `What are the main contributions and experimental results of ${selectedNode.label}?`
                      : `Explain ${selectedNode.label} and compare how each paper in the corpus proposes, adapts, or evaluates it.`
                  )
                }
                className="w-full px-3 py-2 rounded-lg bg-emerald-500/20 hover:bg-emerald-500/30 border border-emerald-400/50 text-emerald-200 text-xs font-semibold flex items-center justify-center gap-1.5 transition cursor-pointer"
              >
                <MessageSquarePlus className="w-3.5 h-3.5" />
                Synthesize Full Explanation in Chat
              </button>
            )}

            {selectedNode.type === 'Paper' && selectedNode.metadata?.paper_id && (
              <button
                type="button"
                onClick={() =>
                  onOpenPaperInReader && onOpenPaperInReader(selectedNode.metadata.paper_id, 1)
                }
                className="w-full px-3 py-2 rounded-lg bg-sky-500/20 hover:bg-sky-500/30 border border-sky-400/50 text-sky-200 text-xs font-semibold flex items-center justify-center gap-1.5 transition cursor-pointer"
              >
                <ExternalLink className="w-3.5 h-3.5" />
                Open Paper in PDF Reader
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
