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
} from 'lucide-react'

// Register force-directed cola layout once
if (!cytoscape.prototype.hasInitialColaRegistered) {
  cytoscape.use(cola)
  cytoscape.prototype.hasInitialColaRegistered = true
}

const ENTITY_LEGEND = [
  { type: 'Paper', color: '#38BDF8', shape: 'Round Rect' },
  { type: 'Method', color: '#34D399', shape: 'Hexagon' },
  { type: 'Dataset', color: '#FBBF24', shape: 'Diamond' },
  { type: 'Metric', color: '#F472B6', shape: 'Octagon' },
  { type: 'Author', color: '#A78BFA', shape: 'Circle' },
]

function computeNodeSize(data) {
  // Dual-Mode Sizing:
  // 1. Query-Active Mode: scale prominently by relevance_score [0.0 - 1.0]
  if (typeof data.relevance_score === 'number' && data.relevance_score !== null) {
    if (data.relevance_score >= 0.7) {
      return Math.round(34 + data.relevance_score * 28)
    }
    return 24
  }
  // 2. Idle Topology Mode: scale by connection degree
  const deg = Number(data.degree || 1)
  const base = data.type === 'Paper' ? 34 : 24
  return Math.min(62, base + Math.round(Math.sqrt(deg) * 6))
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

export default function GraphCanvas({
  graphData,
  activeQuery,
  onResetHighlight,
  onOpenPaperInReader,
}) {
  const containerRef = useRef(null)
  const cyRef = useRef(null)

  const [selectedNode, setSelectedNode] = useState(null)
  const [typeFilter, setTypeFilter] = useState('ALL')

  useEffect(() => {
    if (!containerRef.current || !graphData?.elements) return

    const rawNodes = graphData.elements.nodes || []
    const rawEdges = graphData.elements.edges || []

    const filteredNodes =
      typeFilter === 'ALL'
        ? rawNodes
        : rawNodes.filter(
            (n) => n.data.type === typeFilter || n.data.type === 'Paper'
          )
    const allowedIds = new Set(filteredNodes.map((n) => n.data.id))
    const filteredEdges = rawEdges.filter(
      (e) => allowedIds.has(e.data.source) && allowedIds.has(e.data.target)
    )

    const cyElements = [
      ...filteredNodes.map((n) => ({
        group: 'nodes',
        data: {
          ...n.data,
          computedSize: computeNodeSize(n.data),
          computedShape: getNodeShape(n.data.type),
        },
        classes: [
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
      style: [
        {
          selector: 'node',
          style: {
            label: 'data(label)',
            width: 'data(computedSize)',
            height: 'data(computedSize)',
            shape: 'data(computedShape)',
            'background-color': 'data(color)',
            'border-width': 2,
            'border-color': '#0f172a',
            color: '#f8fafc',
            'font-size': '10px',
            'font-weight': 600,
            'text-valign': 'bottom',
            'text-halign': 'center',
            'text-margin-y': 5,
            'text-wrap': 'wrap',
            'text-max-width': '110px',
            'text-outline-width': 2,
            'text-outline-color': '#020617',
            'transition-property': 'width, height, opacity, border-width, border-color',
            'transition-duration': '300ms',
          },
        },
        {
          selector: 'node.active-node',
          style: {
            'border-width': 4,
            'border-color': '#facc15',
            'font-size': '11px',
            'z-index': 999,
          },
        },
        {
          selector: 'node.dimmed-node',
          style: {
            opacity: 0.2,
          },
        },
        {
          selector: 'edge',
          style: {
            width: 1.6,
            'line-color': '#475569',
            'target-arrow-color': '#475569',
            'target-arrow-shape': 'triangle',
            'curve-style': 'bezier',
            label: 'data(label)',
            'font-size': '8px',
            color: '#94a3b8',
            'text-rotation': 'autorotate',
            'text-background-opacity': 0.85,
            'text-background-color': '#020617',
            'text-background-padding': '2px',
            opacity: 0.85,
          },
        },
        {
          selector: 'edge.active-edge',
          style: {
            width: 4,
            'line-color': '#facc15',
            'target-arrow-color': '#facc15',
            color: '#fef08a',
            'font-size': '9px',
            'font-weight': 'bold',
            opacity: 1.0,
            'z-index': 999,
          },
        },
        {
          selector: 'edge.dimmed-edge',
          style: {
            opacity: 0.2,
          },
        },
      ],
      layout: {
        name: 'cola',
        animate: true,
        maxSimulationTime: 1800,
        nodeSpacing: 28,
        edgeLengthVal: 95,
        randomize: false,
      },
    })

    cy.on('tap', 'node', (evt) => {
      const nodeData = evt.target.data()
      setSelectedNode(nodeData)
    })

    cy.on('tap', (evt) => {
      if (evt.target === cy) {
        setSelectedNode(null)
      }
    })

    cyRef.current = cy

    return () => {
      if (cyRef.current) {
        cyRef.current.destroy()
        cyRef.current = null
      }
    }
  }, [graphData, typeFilter])

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
      cyRef.current.fit(undefined, 36)
    }
  }

  return (
    <div className="flex flex-col h-full bg-slate-950 relative">
      {/* Graph Toolbar */}
      <div className="px-4 py-2.5 border-b border-slate-800 bg-slate-900/90 flex flex-wrap items-center justify-between gap-2 z-10">
        <div className="flex items-center gap-2">
          <Network className="w-4 h-4 text-emerald-400" />
          <span className="text-xs font-semibold text-slate-200">
            2D Scientific Knowledge Graph
          </span>
          <span className="text-[11px] px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700 font-mono">
            {graphData?.total_nodes || 0} Nodes · {graphData?.total_edges || 0} Edges
          </span>
        </div>

        {/* Entity Filter Pills & Camera Controls */}
        <div className="flex items-center gap-2 flex-wrap">
          <div className="flex items-center gap-1 bg-slate-800/90 p-0.5 rounded-lg border border-slate-700 text-[11px]">
            {['ALL', 'Paper', 'Method', 'Dataset', 'Metric', 'Author'].map((type) => (
              <button
                key={type}
                type="button"
                onClick={() => setTypeFilter(type)}
                className={`px-2 py-1 rounded-md font-medium transition cursor-pointer ${
                  typeFilter === type
                    ? 'bg-sky-500 text-slate-950 font-semibold'
                    : 'text-slate-300 hover:text-white'
                }`}
              >
                {type}
              </button>
            ))}
          </div>

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
              Prompt-Active Graph Mode: Scaling relevant entities &amp; illuminating 4px paths for{' '}
              <strong>&ldquo;{activeQuery}&rdquo;</strong> (peripheral nodes dimmed to 20%)
            </span>
          </div>
          {onResetHighlight && (
            <button
              type="button"
              onClick={onResetHighlight}
              className="ml-2 px-2 py-0.5 rounded bg-amber-400/20 hover:bg-amber-400/30 border border-amber-400/50 text-amber-100 flex items-center gap-1 shrink-0 cursor-pointer"
            >
              <RotateCcw className="w-3 h-3" />
              Reset View
            </button>
          )}
        </div>
      )}

      {/* Cytoscape Canvas */}
      <div ref={containerRef} className="flex-1 w-full h-full bg-slate-950" />

      {/* Entity Legend Overlay (Bottom Left) */}
      <div className="absolute bottom-4 left-4 p-2.5 rounded-xl bg-slate-900/90 border border-slate-800 backdrop-blur-sm flex flex-wrap items-center gap-3 text-[11px] text-slate-300 pointer-events-none">
        {ENTITY_LEGEND.map((item) => (
          <div key={item.type} className="flex items-center gap-1.5">
            <span
              className="w-3 h-3 rounded-sm inline-block"
              style={{ backgroundColor: item.color }}
            />
            <span>
              <strong>{item.type}</strong> ({item.shape})
            </span>
          </div>
        ))}
      </div>

      {/* Node Inspector Card (Bottom Right) */}
      {selectedNode && (
        <div className="absolute bottom-4 right-4 w-80 p-3.5 rounded-xl bg-slate-900/95 border border-slate-700 shadow-2xl space-y-2 z-20">
          <div className="flex items-center justify-between gap-2">
            <span
              className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded text-slate-950"
              style={{ backgroundColor: selectedNode.color }}
            >
              {selectedNode.type}
            </span>
            <span className="text-xs font-mono text-slate-400">
              Degree: {selectedNode.degree}
              {typeof selectedNode.relevance_score === 'number' &&
                ` · Rel: ${(selectedNode.relevance_score * 100).toFixed(0)}%`}
            </span>
          </div>
          <h4 className="text-sm font-semibold text-slate-100 leading-snug">
            {selectedNode.label}
          </h4>

          {selectedNode.type === 'Paper' && selectedNode.metadata?.paper_id && (
            <button
              type="button"
              onClick={() =>
                onOpenPaperInReader && onOpenPaperInReader(selectedNode.metadata.paper_id)
              }
              className="w-full mt-1 px-3 py-1.5 rounded-lg bg-sky-500/20 hover:bg-sky-500/30 border border-sky-400/50 text-sky-200 text-xs font-semibold flex items-center justify-center gap-1.5 transition cursor-pointer"
            >
              <ExternalLink className="w-3.5 h-3.5" />
              Open Paper in PDF Reader
            </button>
          )}
        </div>
      )}
    </div>
  )
}

