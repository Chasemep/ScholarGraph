import React, { useEffect, useRef, useState, useMemo } from 'react'
import cytoscape from 'cytoscape'
import { Network } from 'lucide-react'
import GraphControls from './GraphControls'
import GraphLegend from './GraphLegend'
import NodeDetailDrawer from './NodeDetailDrawer'
import {
  buildStructuredTimelineLayout,
  buildPaperCardSvg,
  buildCytoscapeStylesheet,
} from './graphConfig'

/**
 * Knowledge Graph visualizer rendering hierarchical research clusters,
 * timeline ordinal ranks, and obstacle-avoiding citation pathways.
 */
export default function GraphCanvas({
  graphData,
  activeQuery,
  onResetHighlight,
  onOpenPaperInReader,
  onSelectCitation,
  onAskAboutNode,
}) {
  const containerRef = useRef(null)
  const cyRef = useRef(null)

  const [selectedNode, setSelectedNode] = useState(null)
  const [selectedEdge, setSelectedEdge] = useState(null)
  const [selectedCategory, setSelectedCategory] = useState(null)
  const [comparedPaperIds, setComparedPaperIds] = useState([])
  const [layoutDirection, setLayoutDirection] = useState('TB')
  const [stats, setStats] = useState({ papers: 0, groups: 0 })
  const [yearTicks, setYearTicks] = useState([])
  const [viewportTransform, setViewportTransform] = useState({
    panX: 0,
    panY: 0,
    zoom: 1,
  })

  // Compute the visible hierarchical graph elements (Papers + Clickable Categories + CITES Edges)
  const processedGraph = useMemo(() => {
    const rawNodes = graphData?.elements?.nodes || []
    const rawEdges = graphData?.elements?.edges || []

    const paperNodes = rawNodes.filter((n) => n.data.type === 'Paper')
    const paperIdSet = new Set(paperNodes.map((n) => n.data.id))
    const paperById = new Map(paperNodes.map((n) => [n.data.id, n]))

    // Directed CITES edges: citing paper -> cited paper
    const citationEdges = []
    rawEdges.forEach((e) => {
      if (
        e.data.type === 'CITES' &&
        paperIdSet.has(e.data.source) &&
        paperIdSet.has(e.data.target)
      ) {
        const sourceNode = paperById.get(e.data.source)
        const targetNode = paperById.get(e.data.target)
        const sourceYear = Number(sourceNode?.data.metadata?.year) || 0
        const targetYear = Number(targetNode?.data.metadata?.year) || 0

        const isAnomaly =
          Boolean(e.data.metadata?.is_preprint_anomaly) ||
          (sourceYear > 0 && targetYear > 0 && sourceYear < targetYear)

        const citationList = e.data.metadata?.citations || []
        const count = citationList.length || e.data.metadata?.citation_count || 1
        const baseLabel = count > 1 ? `Cites (${count})` : 'Cites'
        const edgeLabel = isAnomaly ? `${baseLabel} ⚠` : baseLabel

        const anomalyNote =
          e.data.metadata?.anomaly_note ||
          (isAnomaly
            ? `This ${sourceYear} paper cites a work dated ${targetYear}. In academic publishing, this occurs when an older preprint was updated in a later arXiv revision or cited before formal conference proceedings.`
            : null)

        citationEdges.push({
          group: 'edges',
          data: {
            ...e.data,
            label: edgeLabel,
            is_anomaly: isAnomaly,
            metadata: {
              citing_paper_id:
                e.data.metadata?.citing_paper_id ||
                sourceNode?.data.metadata?.paper_id,
              citing_paper_title:
                e.data.metadata?.citing_paper_title || sourceNode?.data.label,
              citing_year:
                e.data.metadata?.citing_year || sourceNode?.data.metadata?.year,
              cited_paper_id:
                e.data.metadata?.cited_paper_id ||
                targetNode?.data.metadata?.paper_id,
              cited_paper_title:
                e.data.metadata?.cited_paper_title || targetNode?.data.label,
              cited_year:
                e.data.metadata?.cited_year || targetNode?.data.metadata?.year,
              citation_count: count,
              is_preprint_anomaly: isAnomaly,
              anomaly_note: anomalyNote,
              citations: citationList,
            },
          },
        })
      }
    })

    return {
      paperNodes,
      edges: citationEdges,
    }
  }, [graphData])

  // Initialize Cytoscape Instance
  useEffect(() => {
    if (!containerRef.current) return

    const { paperNodes, edges } = processedGraph

    if (paperNodes.length === 0) {
      if (cyRef.current) {
        cyRef.current.destroy()
        cyRef.current = null
      }
      setStats({ papers: 0, groups: 0 })
      setYearTicks([])
      return
    }

    const {
      positions,
      timelineElements,
      groupCompoundNodes,
      nodeParentMap,
      edgeRouting,
      yearTicks: computedYearTicks,
      groupCount,
    } = buildStructuredTimelineLayout(paperNodes, edges, layoutDirection)

    setStats({
      papers: paperNodes.length,
      groups: groupCount,
    })
    setYearTicks(computedYearTicks)

    const cyElements = [
      ...timelineElements,
      ...groupCompoundNodes,
      ...paperNodes.map((n) => {
        const isQueryActive = Boolean(n.data.is_active)
        const isSelected = selectedNode?.id === n.data.id
        return {
          group: 'nodes',
          position: positions[n.data.id] || { x: 0, y: 0 },
          data: {
            ...n.data,
            parent: nodeParentMap[n.data.id],
            cardSvg: buildPaperCardSvg(n.data, {
              isActive: isQueryActive,
              isFocused: isSelected,
            }),
          },
          classes: [
            'paper-card',
            n.data.is_dimmed ? 'dimmed-node' : '',
            isQueryActive ? 'active-node' : '',
            isSelected ? 'focused-node' : '',
          ]
            .filter(Boolean)
            .join(' '),
        }
      }),
      ...edges.map((e) => {
        const route = edgeRouting[e.data.id] || {
          curveStyle: 'unbundled-bezier',
          sourceEndpoint: 'outside-to-node',
          targetEndpoint: 'outside-to-node',
          cpDistance: 0,
          cpWeight: 0.5,
        }
        return {
          group: 'edges',
          data: {
            ...e.data,
            sourceEndpoint: route.sourceEndpoint,
            targetEndpoint: route.targetEndpoint,
            cpDistance: route.cpDistance,
            cpWeight: route.cpWeight,
          },
          classes: [
            'cites-edge',
            e.data.is_anomaly ? 'cites-anomaly-edge' : '',
            e.data.is_active ? 'active-edge' : '',
            e.data.is_dimmed ? 'dimmed-edge' : '',
            selectedEdge?.id === e.data.id ? 'focused-edge' : '',
          ]
            .filter(Boolean)
            .join(' '),
        }
      }),
    ]

    if (cyRef.current) {
      cyRef.current.destroy()
    }

    const cy = cytoscape({
      container: containerRef.current,
      elements: cyElements,
      minZoom: 0.3,
      maxZoom: 2.4,
      wheelSensitivity: 0.22,
      style: buildCytoscapeStylesheet(),
      layout: {
        name: 'preset',
        fit: true,
        padding: 68,
      },
    })

    const syncViewport = () => {
      const p = cy.pan()
      setViewportTransform({
        panX: p.x,
        panY: p.y,
        zoom: cy.zoom(),
      })
    }

    cy.on('pan zoom', syncViewport)
    syncViewport()

    // Event Listeners
    cy.on('tap', 'node.paper-card', (evt) => {
      const node = evt.target
      setSelectedNode({
        id: node.data('id'),
        label: node.data('label'),
        type: node.data('type'),
        metadata: node.data('metadata') || {},
      })
      setSelectedEdge(null)
      setSelectedCategory(null)
    })

    cy.on('tap', 'node.macro-group-box, node.sub-group-box', (evt) => {
      const gNode = evt.target
      setSelectedCategory({
        id: gNode.data('id'),
        label: gNode.data('label'),
        metadata: gNode.data('metadata') || {},
      })
      setSelectedNode(null)
      setSelectedEdge(null)
    })

    cy.on('tap', 'edge.cites-edge', (evt) => {
      const edge = evt.target
      setSelectedEdge({
        id: edge.data('id'),
        source: edge.data('source'),
        target: edge.data('target'),
        metadata: edge.data('metadata') || {},
      })
      setSelectedNode(null)
      setSelectedCategory(null)
    })

    cy.on('tap', (evt) => {
      if (evt.target === cy) {
        setSelectedNode(null)
        setSelectedEdge(null)
        setSelectedCategory(null)
      }
    })

    cyRef.current = cy

    return () => {
      if (cyRef.current) {
        cyRef.current.destroy()
        cyRef.current = null
      }
    }
  }, [processedGraph, layoutDirection])

  const handleZoomIn = () => {
    if (!cyRef.current) return
    cyRef.current.zoom({
      level: cyRef.current.zoom() * 1.25,
      renderedPosition: {
        x: containerRef.current.clientWidth / 2,
        y: containerRef.current.clientHeight / 2,
      },
    })
  }

  const handleZoomOut = () => {
    if (!cyRef.current) return
    cyRef.current.zoom({
      level: cyRef.current.zoom() * 0.8,
      renderedPosition: {
        x: containerRef.current.clientWidth / 2,
        y: containerRef.current.clientHeight / 2,
      },
    })
  }

  const handleFit = () => {
    if (!cyRef.current) return
    cyRef.current.fit(undefined, 68)
  }

  const handleResetLayout = () => {
    if (!cyRef.current) return
    cyRef.current.reset()
    cyRef.current.fit(undefined, 68)
  }

  const hasActiveHighlight = useMemo(() => {
    const rawNodes = graphData?.elements?.nodes || []
    return rawNodes.some((n) => n.data.is_active || n.data.is_dimmed)
  }, [graphData])

  return (
    <div className="relative w-full h-full bg-[#09090b] overflow-hidden select-none">
      {/* Cytoscape Canvas Mount */}
      <div ref={containerRef} className="w-full h-full" />

      {/* Empty State */}
      {processedGraph.paperNodes.length === 0 && (
        <div className="absolute inset-0 flex flex-col items-center justify-center p-6 text-center pointer-events-none">
          <div className="w-12 h-12 rounded-xl bg-[#18181b] border border-[#27272a] flex items-center justify-center mb-3 text-[#6366f1]">
            <Network className="w-6 h-6" />
          </div>
          <p className="text-sm font-semibold text-[#f4f4f5]">Knowledge Graph Empty</p>
          <p className="text-xs text-[#a1a1aa] mt-1 max-w-sm">
            Upload PDF papers to automatically extract entities, research clusters, and cross-paper citations.
          </p>
        </div>
      )}

      {/* Top Floating Controls */}
      <GraphControls
        layoutDirection={layoutDirection}
        onToggleDirection={() => setLayoutDirection((prev) => (prev === 'TB' ? 'LR' : 'TB'))}
        onZoomIn={handleZoomIn}
        onZoomOut={handleZoomOut}
        onFit={handleFit}
        onResetLayout={handleResetLayout}
        hasActiveHighlight={hasActiveHighlight}
        onResetHighlight={onResetHighlight}
        stats={stats}
      />

      {/* Pinned Timeline Year Scale (Overlay) */}
      {yearTicks.length > 0 && layoutDirection === 'TB' && (
        <div className="absolute top-0 bottom-0 left-0 w-[78px] bg-[#09090b]/85 border-r border-[#27272a] backdrop-blur-md pointer-events-none z-10 overflow-hidden">
          <div className="px-2 py-3 border-b border-[#27272a] bg-[#18181b]/90 text-center">
            <span className="text-[9px] font-mono font-bold uppercase tracking-widest text-[#a1a1aa]">
              Year
            </span>
          </div>
          {yearTicks.map((tick) => {
            const screenY = tick.modelCoord * viewportTransform.zoom + viewportTransform.panY
            return (
              <div
                key={`badge_${tick.rankIndex}`}
                className="absolute left-0 right-0 flex items-center justify-between px-2 -translate-y-1/2"
                style={{ top: `${screenY}px` }}
              >
                <span className="px-2 py-0.5 rounded-md bg-[#18181b] border border-[#3f3f46] text-[11px] font-mono font-bold text-[#f4f4f5] shadow-md">
                  {tick.label}
                </span>
                <span className="w-2.5 h-[2px] bg-[#6366f1]/80" />
              </div>
            )
          })}
        </div>
      )}

      {/* Bottom Legend Overlay */}
      <GraphLegend layoutDirection={layoutDirection} />

      {/* Detail Inspection Drawers */}
      <NodeDetailDrawer
        selectedNode={selectedNode}
        selectedEdge={selectedEdge}
        selectedCategory={selectedCategory}
        onClose={() => {
          setSelectedNode(null)
          setSelectedEdge(null)
          setSelectedCategory(null)
        }}
        onSelectCitation={onSelectCitation}
        onOpenPaperInReader={onOpenPaperInReader}
        onAskAboutNode={onAskAboutNode}
      />
    </div>
  )
}

