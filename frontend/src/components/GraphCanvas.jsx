import React, { useEffect, useRef, useState, useMemo } from 'react'
import cytoscape from 'cytoscape'
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
  Layers,
  ArrowDownUp,
  ArrowLeftRight,
  ArrowRight,
  Quote,
  AlertTriangle,
} from 'lucide-react'
import { renderMathSegment } from '../utils/mathRenderer'

/**
 * Escape special XML characters for safe inline SVG generation.
 */
function escapeXml(str = '') {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&apos;')
}

/**
 * Wrap a title string into at most 2 lines of maxChars length.
 */
function wrapTwoLines(text = '', maxChars = 25) {
  const cleaned = String(text)
    .replace(/\s*\([^)]*\d{4}[^)]*\)\s*$/, '')
    .trim()
  const words = cleaned.split(/\s+/).filter(Boolean)
  if (words.length === 0) return ['Untitled Paper', '']

  let line1 = ''
  let line2 = ''
  let onSecondLine = false

  for (let i = 0; i < words.length; i += 1) {
    const word = words[i]
    if (!onSecondLine) {
      const candidate = line1 ? `${line1} ${word}` : word
      if (candidate.length <= maxChars || !line1) {
        line1 = candidate.slice(0, maxChars)
      } else {
        onSecondLine = true
        line2 = word
      }
    } else {
      const candidate = line2 ? `${line2} ${word}` : word
      if (candidate.length <= maxChars - 1) {
        line2 = candidate
      } else {
        line2 = `${line2.slice(0, Math.max(0, maxChars - 2)).trim()}…`
        break
      }
    }
  }

  return [line1, line2]
}

/**
 * Format author + year subtitle for a 160x60 Paper card.
 */
function formatAuthorYear(metadata = {}) {
  const authors = Array.isArray(metadata.authors) ? metadata.authors : []
  const year = metadata.year ? String(metadata.year) : ''
  let authorPart = 'Unknown author'
  if (authors.length > 0) {
    const first = String(authors[0]).trim()
    const surname = first.split(/\s+/).pop() || first
    authorPart = authors.length > 1 ? `${surname} et al.` : surname
  }
  return year ? `${authorPart} · ${year}` : authorPart
}

/**
 * Build a 160x60 SVG mini-card data URI for a Paper node showing:
 * - 2-line wrapped title
 * - Author & publication year
 * - Colored Method & Dataset tags inside the card
 */
function buildPaperCardSvg(nodeData, { isActive = false, isFocused = false } = {}) {
  const [line1, line2] = wrapTwoLines(nodeData.label, 25)
  const authorYear = formatAuthorYear(nodeData.metadata)

  const methods = (nodeData.metadata?.methods || []).slice(0, 2)
  const datasets = (nodeData.metadata?.datasets || []).slice(0, 1)
  const tags = [
    ...methods.map((m) => ({ label: m, kind: 'Method' })),
    ...datasets.map((d) => ({ label: d, kind: 'Dataset' })),
  ].slice(0, 2)

  const totalExtra = Math.max(
    0,
    (nodeData.metadata?.methods?.length || 0) +
      (nodeData.metadata?.datasets?.length || 0) -
      tags.length
  )

  const bgFill = isActive || isFocused ? '#1e1b4b' : '#18181b'
  const topAccent = isActive || isFocused ? '#6366f1' : '#27272a'

  let tagX = 8
  const tagElements = tags
    .map((t) => {
      const shortTag = t.label.length > 11 ? `${t.label.slice(0, 10).trim()}…` : t.label
      const tagWidth = Math.min(72, Math.max(34, shortTag.length * 4.7 + 10))
      if (tagX + tagWidth > 134) return ''
      const currentX = tagX
      tagX += tagWidth + 4

      const isMethod = t.kind === 'Method'
      const pillFill = isMethod ? 'rgba(16,185,129,0.16)' : 'rgba(245,158,11,0.16)'
      const pillStroke = isMethod ? 'rgba(52,211,153,0.45)' : 'rgba(251,191,36,0.45)'
      const textFill = isMethod ? '#6ee7b7' : '#fcd34d'

      return `
        <g transform="translate(${currentX}, 44)">
          <rect width="${tagWidth}" height="11.5" rx="3" fill="${pillFill}" stroke="${pillStroke}" stroke-width="0.7" />
          <text x="${tagWidth / 2}" y="8" text-anchor="middle" fill="${textFill}" font-family="Inter, system-ui, sans-serif" font-size="6.8" font-weight="600">${escapeXml(shortTag)}</text>
        </g>
      `
    })
    .join('')

  const extraBadge =
    totalExtra > 0 && tagX <= 140
      ? `<text x="${tagX + 2}" y="52" fill="#a1a1aa" font-family="Inter, system-ui, sans-serif" font-size="6.8" font-weight="600">+${totalExtra}</text>`
      : ''

  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="160" height="60" viewBox="0 0 160 60">
    <rect width="160" height="60" rx="8" fill="${bgFill}" />
    <rect x="0" y="0" width="160" height="2.5" rx="1" fill="${topAccent}" />
    <text x="8" y="14.5" fill="#f4f4f5" font-family="Inter, system-ui, sans-serif" font-size="8.8" font-weight="600">${escapeXml(line1)}</text>
    ${
      line2
        ? `<text x="8" y="25.5" fill="#f4f4f5" font-family="Inter, system-ui, sans-serif" font-size="8.8" font-weight="600">${escapeXml(line2)}</text>`
        : ''
    }
    <text x="8" y="${line2 ? '37.5' : '27.5'}" fill="#a1a1aa" font-family="Inter, system-ui, sans-serif" font-size="7.5" font-weight="500">${escapeXml(authorYear)}</text>
    ${tagElements}
    ${extraBadge}
  </svg>`

  return `data:image/svg+xml;utf8,${encodeURIComponent(svg)}`
}

/**
 * Build a compact 120x26 SVG pill for shared Method/Dataset bridge nodes.
 */
function buildBridgePillSvg(nodeData) {
  const isMethod = nodeData.type === 'Method'
  const dotColor = isMethod ? '#34d399' : '#fbbf24'
  const borderTint = isMethod ? 'rgba(52,211,153,0.45)' : 'rgba(251,191,36,0.45)'
  const rawLabel = String(nodeData.label || '')
  const shortLabel = rawLabel.length > 18 ? `${rawLabel.slice(0, 17).trim()}…` : rawLabel

  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="120" height="26" viewBox="0 0 120 26">
    <rect x="0.5" y="0.5" width="119" height="25" rx="12.5" fill="#18181b" stroke="${borderTint}" stroke-width="1" />
    <circle cx="12" cy="13" r="3.5" fill="${dotColor}" />
    <text x="21" y="16" fill="#e4e4e7" font-family="Inter, system-ui, sans-serif" font-size="8" font-weight="600">${escapeXml(shortLabel)}</text>
  </svg>`

  return `data:image/svg+xml;utf8,${encodeURIComponent(svg)}`
}

/**
 * Sample points along a quadratic Bezier curve (p1 -> cp -> p2) and check if any point
 * enters the padded bounding box [center.x ± halfW, center.y ± halfH] of an intermediate Paper card.
 */
function bezierIntersectsBox(p1, cp, p2, center, halfW = 92, halfH = 40) {
  const steps = 16
  for (let i = 1; i < steps; i += 1) {
    const t = i / steps
    const invT = 1 - t
    const x = invT * invT * p1.x + 2 * invT * t * cp.x + t * t * p2.x
    const y = invT * invT * p1.y + 2 * invT * t * cp.y + t * t * p2.y
    if (Math.abs(x - center.x) < halfW && Math.abs(y - center.y) < halfH) {
      return true
    }
  }
  return false
}

/**
 * Given source p1, target p2, and Cytoscape unbundled-bezier control-point distance `cpDist`
 * (perpendicular offset from midpoint of p1 -> p2), compute the world-space control point.
 */
function computeControlPoint(p1, p2, cpDist, cpWeight = 0.5) {
  const dx = p2.x - p1.x
  const dy = p2.y - p1.y
  const len = Math.hypot(dx, dy) || 1
  const baseX = p1.x + dx * cpWeight
  const baseY = p1.y + dy * cpWeight
  // Cytoscape perpendicular normal vector: (-dy / len, dx / len)
  const nx = -dy / len
  const ny = dx / len
  return {
    x: baseX + nx * cpDist,
    y: baseY + ny * cpDist,
  }
}

/**
 * Build a fallback strictly paper-derived topic summary from paper nodes if backend details aren't attached.
 */
function buildFallbackCategoryDetails(pNodes) {
  const sorted = [...pNodes].sort(
    (a, b) =>
      (Number(a.data.metadata?.year) || 9999) -
      (Number(b.data.metadata?.year) || 9999)
  )
  const methodsSet = new Set()
  const datasetsSet = new Set()
  const papers = []
  const overviewParts = []

  sorted.forEach((pNode) => {
    const meta = pNode.data.metadata || {}
    ;(meta.methods || []).forEach((m) => methodsSet.add(m))
    ;(meta.datasets || []).forEach((d) => datasetsSet.add(d))

    const rawDesc = String(meta.description || '').replace(/^\s*Abstract:\s*/i, '').trim()
    const firstSent = rawDesc.split(/(?<=[.!?])\s+/)[0] || rawDesc

    papers.push({
      paper_id: meta.paper_id || pNode.data.id.replace(/^node_/, ''),
      paper_title: pNode.data.label,
      year: meta.year,
      authors: meta.authors || [],
      excerpt: rawDesc,
      page: 1,
      section: 'Abstract / Introduction',
      bbox: null,
      methods: (meta.methods || []).slice(0, 5),
      datasets: (meta.datasets || []).slice(0, 4),
    })

    if (firstSent) {
      overviewParts.push(
        `• ${pNode.data.label}${meta.year ? ` (${meta.year})` : ''}: "${firstSent}"`
      )
    }
  })

  return {
    overview: overviewParts.join('\n\n'),
    methods: Array.from(methodsSet).slice(0, 8),
    datasets: Array.from(datasetsSet).slice(0, 6),
    papers,
  }
}

/**
 * Compute:
 * 1. Compressed-gap Timeline Axis ranks (one discrete rank per unique publication year).
 * 2. Side-by-side Group and nested Subgroup columns so all papers align on a strict grid
 *    and Group/Subgroup compound bounding boxes are clickable and never overlap.
 * 3. Obstacle-avoiding edge routing parameters (`sourceEndpoint`, `targetEndpoint`, `cpDistance`, `cpWeight`)
 *    so arrows never cut through Paper cards.
 */
function buildStructuredTimelineLayout(paperNodes, edges, direction = 'TB') {
  const positions = {}
  const timelineElements = []
  const groupCompoundNodes = []
  const nodeParentMap = {}

  if (paperNodes.length === 0) {
    return {
      positions,
      timelineElements,
      groupCompoundNodes,
      nodeParentMap,
      edgeRouting: {},
      yearTicks: [],
      groupCount: 0,
    }
  }

  // 1. Extract sorted unique years (Compressed-Gap Ordinal Axis)
  const uniqueYears = Array.from(
    new Set(
      paperNodes.map((n) => {
        const y = Number(n.data.metadata?.year)
        return Number.isFinite(y) && y > 1800 ? y : 9999
      })
    )
  ).sort((a, b) => a - b)

  const yearToRank = new Map(uniqueYears.map((y, idx) => [y, idx]))

  // 2. Organize papers into Macro-Groups and optional nested Subgroups
  const groupsMap = new Map()
  paperNodes.forEach((pNode) => {
    const meta = pNode.data.metadata || {}
    const gid = meta.group_id || 'group_1'
    const glabel = meta.group_label || 'Research Cluster'
    const gDetails = meta.group_details || null
    const subId = meta.subgroup_id || null
    const subLabel = meta.subgroup_label || null
    const subDetails = meta.subgroup_details || null

    if (!groupsMap.has(gid)) {
      groupsMap.set(gid, {
        id: gid,
        label: glabel,
        details: gDetails,
        papers: [],
        subgroupsMap: new Map(),
      })
    }
    const gEntry = groupsMap.get(gid)
    if (!gEntry.details && gDetails) gEntry.details = gDetails
    gEntry.papers.push(pNode)

    const effectiveSubKey = subId || '__default__'
    if (!gEntry.subgroupsMap.has(effectiveSubKey)) {
      gEntry.subgroupsMap.set(effectiveSubKey, {
        id: subId,
        label: subLabel,
        details: subDetails,
        papers: [],
      })
    }
    const sEntry = gEntry.subgroupsMap.get(effectiveSubKey)
    if (!sEntry.details && subDetails) sEntry.details = subDetails
    sEntry.papers.push(pNode)
  })

  // Sort Macro-Groups by paper count descending, then earliest year
  const sortedGroups = Array.from(groupsMap.values()).sort((a, b) => {
    if (b.papers.length !== a.papers.length) return b.papers.length - a.papers.length
    const minYearA = Math.min(...a.papers.map((p) => Number(p.data.metadata?.year) || 9999))
    const minYearB = Math.min(...b.papers.map((p) => Number(p.data.metadata?.year) || 9999))
    return minYearA - minYearB
  })

  // Spacing constants
  const RANK_STEP = direction === 'TB' ? 162 : 265
  const COL_STEP = direction === 'TB' ? 230 : 120
  const SUBGROUP_GAP = direction === 'TB' ? 50 : 40
  const GROUP_GAP = direction === 'TB' ? 95 : 75

  let currentCrossCoord = 0

  sortedGroups.forEach((group, gIdx) => {
    const parentGroupId = `compound_${group.id}`
    const resolvedGroupDetails =
      group.details || buildFallbackCategoryDetails(group.papers)

    const subEntries = Array.from(group.subgroupsMap.values())
    const hasRealSubgroups =
      subEntries.length >= 2 && subEntries.some((s) => s.id !== null)

    groupCompoundNodes.push({
      group: 'nodes',
      data: {
        id: parentGroupId,
        label: group.label,
        type: 'GroupBox',
        metadata: {
          categoryType: 'Category',
          label: group.label,
          parentLabel: null,
          paperNodeIds: group.papers.map((p) => p.data.id),
          subcategories: hasRealSubgroups
            ? subEntries.filter((s) => s.id).map((s) => s.label)
            : [],
          details: resolvedGroupDetails,
        },
      },
      selectable: true,
      grabbable: false,
      classes: 'macro-group-box',
    })

    subEntries.forEach((sub, sIdx) => {
      let parentIdForPapers = parentGroupId
      if (hasRealSubgroups && sub.id) {
        const subCompoundId = `compound_${sub.id}`
        const resolvedSubDetails =
          sub.details || buildFallbackCategoryDetails(sub.papers)

        groupCompoundNodes.push({
          group: 'nodes',
          data: {
            id: subCompoundId,
            parent: parentGroupId,
            label: sub.label,
            type: 'SubgroupBox',
            metadata: {
              categoryType: 'Subcategory',
              label: sub.label,
              parentLabel: group.label,
              paperNodeIds: sub.papers.map((p) => p.data.id),
              subcategories: [],
              details: resolvedSubDetails,
            },
          },
          selectable: true,
          grabbable: false,
          classes: 'sub-group-box',
        })
        parentIdForPapers = subCompoundId
      }

      // Group papers inside this subgroup by year rank
      const byRank = new Map()
      sub.papers.forEach((pNode) => {
        const y = Number(pNode.data.metadata?.year)
        const normY = Number.isFinite(y) && y > 1800 ? y : 9999
        const r = yearToRank.get(normY) ?? 0
        if (!byRank.has(r)) byRank.set(r, [])
        byRank.get(r).push(pNode)
      })

      // Max simultaneous papers in the same year inside this subgroup determines its track width
      let maxColsInSub = 1
      byRank.forEach((list) => {
        if (list.length > maxColsInSub) maxColsInSub = list.length
      })

      byRank.forEach((list, r) => {
        // Deterministic sort within the same year & subgroup
        list.sort((a, b) => (b.data.degree || 0) - (a.data.degree || 0))
        list.forEach((pNode, colOffset) => {
          const crossCoord = currentCrossCoord + colOffset * COL_STEP
          const mainCoord = r * RANK_STEP

          positions[pNode.data.id] =
            direction === 'TB'
              ? { x: Math.round(crossCoord), y: Math.round(mainCoord) }
              : { x: Math.round(mainCoord), y: Math.round(crossCoord) }

          nodeParentMap[pNode.data.id] = parentIdForPapers
        })
      })

      currentCrossCoord +=
        (maxColsInSub - 1) * COL_STEP +
        COL_STEP +
        (sIdx < subEntries.length - 1 ? SUBGROUP_GAP : 0)
    })

    if (gIdx < sortedGroups.length - 1) {
      currentCrossCoord += GROUP_GAP
    }
  })

  // 3. Build the Compressed-Gap Timeline Axis Ticks (for the Pinned Viewport Year Scale)
  //    plus subtle canvas swimlane guide lines spanning across all groups.
  const maxCrossExtent = Math.max(0, currentCrossCoord - COL_STEP)
  const yearTicks = []

  uniqueYears.forEach((yearVal, rIdx) => {
    const yearLabel = yearVal === 9999 ? 'N/A' : String(yearVal)
    const guideStartId = `timeline_guide_start_${rIdx}`
    const guideEndId = `timeline_guide_end_${rIdx}`
    const mainCoord = rIdx * RANK_STEP

    const prevYear = rIdx > 0 ? uniqueYears[rIdx - 1] : null
    const yearDiff =
      rIdx > 0 && yearVal !== 9999 && prevYear !== 9999 ? yearVal - prevYear : 1

    yearTicks.push({
      rankIndex: rIdx,
      year: yearVal,
      label: yearLabel,
      modelCoord: mainCoord,
      prevModelCoord: rIdx > 0 ? (rIdx - 1) * RANK_STEP : null,
      gapLabel: yearDiff > 1 ? `+${yearDiff}y` : null,
    })

    const guideStartPos =
      direction === 'TB'
        ? { x: -320, y: mainCoord }
        : { x: mainCoord, y: -220 }

    const guideEndPos =
      direction === 'TB'
        ? { x: maxCrossExtent + 320, y: mainCoord }
        : { x: mainCoord, y: maxCrossExtent + 220 }

    timelineElements.push({
      group: 'nodes',
      position: guideStartPos,
      data: {
        id: guideStartId,
        label: '',
        type: 'TimelineAnchor',
      },
      selectable: false,
      grabbable: false,
      classes: 'timeline-anchor-node',
    })

    timelineElements.push({
      group: 'nodes',
      position: guideEndPos,
      data: {
        id: guideEndId,
        label: '',
        type: 'TimelineAnchor',
      },
      selectable: false,
      grabbable: false,
      classes: 'timeline-anchor-node',
    })

    // Subtle horizontal (or vertical) guide line across the year swimlane
    timelineElements.push({
      group: 'edges',
      data: {
        id: `timeline_guide_edge_${rIdx}`,
        source: guideStartId,
        target: guideEndId,
        label: '',
      },
      selectable: false,
      classes: 'timeline-guide-edge',
    })
  })

  // 4. Obstacle-Avoiding Edge Routing with True Outer-Boundary Clipping ('outside-to-node')
  //    Ensures:
  //    - Arrow tips always terminate outside the target node's card border (never covered by the box).
  //    - Curved trajectories never cut through intermediate Paper cards.
  const edgeRouting = {}
  const paperRectCenters = paperNodes
    .map((n) => ({ id: n.data.id, pos: positions[n.data.id] }))
    .filter((item) => item.pos)

  let gutterLaneCounter = 0

  edges.forEach((e) => {
    const u = e.data.source
    const v = e.data.target
    const p1 = positions[u]
    const p2 = positions[v]

    if (!p1 || !p2) {
      edgeRouting[e.data.id] = {
        curveStyle: 'bezier',
        sourceEndpoint: 'outside-to-node',
        targetEndpoint: 'outside-to-node',
        cpDistance: 0,
        cpWeight: 0.5,
      }
      return
    }

    const dx = p2.x - p1.x
    const dy = p2.y - p1.y
    const sameCol = direction === 'TB' ? Math.abs(dx) < 12 : Math.abs(dy) < 12
    const otherCards = paperRectCenters.filter(
      (item) => item.id !== u && item.id !== v
    )

    const hitsAnyObstacle = (cpDist) => {
      const cp = computeControlPoint(p1, p2, cpDist, 0.5)
      return otherCards.some((obs) =>
        bezierIntersectsBox(p1, cp, p2, obs.pos, 94, 42)
      )
    }

    if (sameCol && !hitsAnyObstacle(0)) {
      // Direct adjacent edge in the same column: straight path clipped cleanly outside node border
      edgeRouting[e.data.id] = {
        curveStyle: 'unbundled-bezier',
        sourceEndpoint: 'outside-to-node',
        targetEndpoint: 'outside-to-node',
        cpDistance: 0,
        cpWeight: 0.5,
      }
    } else if (sameCol) {
      // Skip-layer edge in the same column: bow wide around the intermediate card(s) through the column gutter
      const lane = gutterLaneCounter % 3
      gutterLaneCounter += 1
      const goingUpOrLeft = direction === 'TB' ? dy < 0 : dx < 0
      const baseMag = 205 + lane * 34
      const primaryDist = goingUpOrLeft ? baseMag : -baseMag
      const chosenDist = !hitsAnyObstacle(primaryDist)
        ? primaryDist
        : !hitsAnyObstacle(-primaryDist)
        ? -primaryDist
        : primaryDist * 1.25

      edgeRouting[e.data.id] = {
        curveStyle: 'unbundled-bezier',
        sourceEndpoint: 'outside-to-node',
        targetEndpoint: 'outside-to-node',
        cpDistance: chosenDist,
        cpWeight: 0.5,
      }
    } else {
      // Cross-column or cross-group edge: pick the gentlest arc that avoids all intermediate Paper cards
      const lane = gutterLaneCounter % 3
      gutterLaneCounter += 1
      const preferredSign = direction === 'TB' ? (dx > 0 ? -1 : 1) : dy > 0 ? 1 : -1

      const candidateMagnitudes = [22 + lane * 10, 75 + lane * 18, 145 + lane * 22, 215 + lane * 26]
      let chosenDist = preferredSign * candidateMagnitudes[0]

      for (const mag of candidateMagnitudes) {
        const d1 = preferredSign * mag
        if (!hitsAnyObstacle(d1)) {
          chosenDist = d1
          break
        }
        const d2 = -preferredSign * mag
        if (!hitsAnyObstacle(d2)) {
          chosenDist = d2
          break
        }
      }

      edgeRouting[e.data.id] = {
        curveStyle: 'unbundled-bezier',
        sourceEndpoint: 'outside-to-node',
        targetEndpoint: 'outside-to-node',
        cpDistance: chosenDist,
        cpWeight: 0.5,
      }
    }
  })

  return {
    positions,
    timelineElements,
    groupCompoundNodes,
    nodeParentMap,
    edgeRouting,
    yearTicks,
    groupCount: sortedGroups.length,
  }
}

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

  const handleJumpToCitation = (occ) => {
    if (onSelectCitation && occ) {
      onSelectCitation({
        chunk_id: occ.chunk_id,
        paper_id: occ.paper_id,
        paper_title: occ.paper_title,
        page: occ.page || 1,
        section: occ.section || '',
        bbox: occ.bbox || null,
        snippet: occ.snippet || '',
      })
    } else if (onOpenPaperInReader && occ?.paper_id) {
      onOpenPaperInReader(occ.paper_id, occ.page || 1)
    }
  }

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
            ? `This ${sourceYear} paper cites a work dated ${targetYear}. In academic publishing, this occurs when a paper cites an earlier arXiv preprint or working paper before its formal conference/journal publication year, or when the citing paper was updated in a later arXiv revision (v2/v3) while keeping its initial year.`
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
      paperCount: paperNodes.length,
    }
  }, [graphData])

  useEffect(() => {
    if (!containerRef.current) return

    const { paperNodes, edges, paperCount } = processedGraph

    const {
      positions,
      timelineElements,
      groupCompoundNodes,
      nodeParentMap,
      edgeRouting,
      yearTicks: computedYearTicks,
      groupCount,
    } = buildStructuredTimelineLayout(
      paperNodes,
      edges,
      layoutDirection
    )

    setYearTicks(computedYearTicks || [])
    setStats({
      papers: paperCount,
      groups: groupCount || 0,
    })

    const cyElements = [
      ...timelineElements,
      ...groupCompoundNodes,
      ...paperNodes.map((n) => {
        const isQueryActive =
          typeof n.data.relevance_score === 'number' && n.data.relevance_score >= 0.7
        const isSelected =
          selectedNode?.id === n.data.id || comparedPaperIds.includes(n.data.id)

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
      style: [
        // Timeline Axis Year Badge Node
        {
          selector: 'node.timeline-year-node',
          style: {
            width: 64,
            height: 24,
            shape: 'round-rectangle',
            'background-opacity': 0,
            'background-image': 'data(badgeSvg)',
            'background-fit': 'contain',
            'border-width': 0,
            label: '',
            events: 'no',
            'z-index': 5,
          },
        },
        {
          selector: 'node.timeline-anchor-node',
          style: {
            width: 1,
            height: 1,
            'background-opacity': 0,
            'border-width': 0,
            label: '',
            events: 'no',
          },
        },
        // Timeline Axis Spine & Horizontal Swimlane Guides
        {
          selector: 'edge.timeline-guide-edge',
          style: {
            width: 1,
            'line-color': '#27272a',
            'line-style': 'dashed',
            'line-dash-pattern': [4, 6],
            'curve-style': 'straight',
            'target-arrow-shape': 'none',
            opacity: 0.55,
            events: 'no',
            'z-index': 1,
          },
        },
        {
          selector: 'edge.timeline-spine-edge',
          style: {
            width: 2,
            'line-color': '#3f3f46',
            'line-style': 'solid',
            'curve-style': 'straight',
            'target-arrow-shape': 'none',
            opacity: 0.8,
            events: 'no',
            'z-index': 2,
          },
        },
        {
          selector: 'edge.timeline-spine-gap-edge',
          style: {
            width: 2,
            'line-color': '#52525b',
            'line-style': 'dashed',
            'line-dash-pattern': [3, 4],
            'curve-style': 'straight',
            'target-arrow-shape': 'none',
            label: 'data(label)',
            color: '#a1a1aa',
            'font-size': '8px',
            'font-weight': 600,
            'text-background-color': '#09090b',
            'text-background-opacity': 0.9,
            'text-background-padding': '2px',
            opacity: 0.9,
            events: 'no',
            'z-index': 2,
          },
        },
        // Clickable Macro-Group Bounding Box (Compound Parent)
        {
          selector: 'node.macro-group-box',
          style: {
            shape: 'round-rectangle',
            'background-color': '#18181b',
            'background-opacity': 0.28,
            'border-width': 1.5,
            'border-color': '#3f3f46',
            'border-opacity': 0.9,
            padding: '28px',
            label: 'data(label)',
            'text-valign': 'top',
            'text-halign': 'center',
            'text-margin-y': -8,
            color: '#f4f4f5',
            'font-size': '11px',
            'font-weight': 700,
            'text-background-color': '#18181b',
            'text-background-opacity': 0.98,
            'text-background-padding': '5px',
            'text-border-width': 1,
            'text-border-color': '#52525b',
            'text-border-opacity': 1,
            events: 'yes',
            'text-events': 'yes',
            'z-index': 2,
          },
        },
        // Clickable Nested Subgroup Bounding Box (Compound Child of Macro-Group)
        {
          selector: 'node.sub-group-box',
          style: {
            shape: 'round-rectangle',
            'background-color': '#27272a',
            'background-opacity': 0.24,
            'border-width': 1.25,
            'border-style': 'dashed',
            'border-color': '#6366f1',
            'border-opacity': 0.55,
            padding: '18px',
            label: 'data(label)',
            'text-valign': 'top',
            'text-halign': 'center',
            'text-margin-y': -5,
            color: '#c7d2fe',
            'font-size': '9.5px',
            'font-weight': 600,
            'text-background-color': '#09090b',
            'text-background-opacity': 0.95,
            'text-background-padding': '3.5px',
            'text-border-width': 1,
            'text-border-color': '#6366f1',
            'text-border-opacity': 0.55,
            events: 'yes',
            'text-events': 'yes',
            'z-index': 3,
          },
        },
        {
          selector: 'node.focused-group-box',
          style: {
            'border-width': 2.2,
            'border-color': '#818cf8',
            'border-opacity': 1,
            'background-opacity': 0.36,
            'text-border-color': '#818cf8',
            'text-background-color': '#312e81',
            color: '#ffffff',
          },
        },
        // 160x60 Paper Card Node
        {
          selector: 'node.paper-card',
          style: {
            width: 160,
            height: 60,
            shape: 'round-rectangle',
            'background-color': '#18181b',
            'background-image': 'data(cardSvg)',
            'background-fit': 'contain',
            'background-clip': 'node',
            'border-width': 1.25,
            'border-color': '#27272a',
            label: '',
            'z-index': 10,
            'transition-property': 'opacity, border-color, border-width, underlay-opacity',
            'transition-duration': '220ms',
          },
        },
        {
          selector: 'node.active-node',
          style: {
            'border-width': 2.2,
            'border-color': '#6366f1',
            'underlay-color': '#6366f1',
            'underlay-padding': 6,
            'underlay-opacity': 0.28,
            'underlay-shape': 'round-rectangle',
            opacity: 1,
            'z-index': 999,
          },
        },
        {
          selector: 'node.focused-node',
          style: {
            'border-width': 2.2,
            'border-color': '#818cf8',
            'underlay-color': '#6366f1',
            'underlay-padding': 5,
            'underlay-opacity': 0.22,
            'underlay-shape': 'round-rectangle',
            opacity: 1,
            'z-index': 999,
          },
        },
        {
          selector: 'node.dimmed-node',
          style: {
            opacity: 0.15,
            'underlay-opacity': 0,
          },
        },
        // Obstacle-Avoiding Unbundled Bezier Citation Edges
        {
          selector: 'edge.cites-edge',
          style: {
            width: 2,
            'line-color': '#6366f1',
            'target-arrow-color': '#818cf8',
            'target-arrow-shape': 'triangle',
            'arrow-scale': 0.85,
            'curve-style': 'unbundled-bezier',
            'source-endpoint': 'outside-to-node',
            'target-endpoint': 'outside-to-node',
            'source-distance-from-node': 5,
            'target-distance-from-node': 6,
            'control-point-distances': 'data(cpDistance)',
            'control-point-weights': 'data(cpWeight)',
            label: 'data(label)',
            color: '#e0e7ff',
            'font-size': '8.5px',
            'font-weight': 600,
            'text-background-opacity': 0.92,
            'text-background-color': '#18181b',
            'text-background-padding': '3px',
            'text-border-width': 1,
            'text-border-color': '#3f3f46',
            'text-border-opacity': 1,
            opacity: 0.78,
            'text-events': 'yes',
            'z-index': 25,
            'transition-property': 'opacity, width, line-color, target-arrow-color',
            'transition-duration': '220ms',
          },
        },
        {
          selector: 'edge.cites-anomaly-edge',
          style: {
            width: 2.2,
            'line-color': '#f59e0b',
            'target-arrow-color': '#fbbf24',
            'line-style': 'dashed',
            'line-dash-pattern': [6, 3],
            label: 'data(label)',
            color: '#fef3c7',
            'text-background-color': '#451a03',
            'text-border-color': '#d97706',
            opacity: 0.88,
          },
        },
        {
          selector: 'edge.active-edge, edge.focused-edge, edge.neighbor-edge',
          style: {
            width: 2.8,
            'line-color': '#818cf8',
            'target-arrow-color': '#a5b4fc',
            'line-style': 'solid',
            label: 'data(label)',
            color: '#ffffff',
            'font-size': '9px',
            'font-weight': 700,
            'text-background-opacity': 1,
            'text-background-color': '#4f46e5',
            'text-background-padding': '3.5px',
            'text-border-width': 1,
            'text-border-color': '#818cf8',
            'text-border-opacity': 1,
            opacity: 1,
            'z-index': 995,
          },
        },
        {
          selector: 'edge.dimmed-edge',
          style: {
            opacity: 0.15,
            label: '',
          },
        },
      ],
      layout: {
        name: 'preset',
        fit: true,
        padding: 68,
      },
    })

    const syncViewport = () => {
      const p = cy.pan()
      const z = cy.zoom()
      setViewportTransform({ panX: p.x, panY: p.y, zoom: z })
    }
    syncViewport()
    cy.on('pan zoom resize', syncViewport)

    // Query-Linked Highlighting & Smooth Camera Zoom
    const activeNodes = cy.nodes('.active-node')
    if (activeQuery && activeNodes.length > 0) {
      cy.animate({
        fit: {
          eles: activeNodes.closedNeighborhood(),
          padding: 75,
        },
        duration: 550,
        easing: 'ease-in-out-cubic',
      })
    }

    // Category / Subcategory Box Click: Explain the topic discussed across the papers in this category
    cy.on('tap', 'node.macro-group-box, node.sub-group-box', (evt) => {
      const clickedBox = evt.target
      // Only handle direct click on the category/subcategory box itself (not bubbled from a child paper card)
      if (clickedBox !== evt.target) return
      const boxData = clickedBox.data()
      const memberNodeIds = new Set(boxData.metadata?.paperNodeIds || [])

      setSelectedNode(null)
      setSelectedEdge(null)
      setSelectedCategory(boxData)

      const interactiveNodes = cy.nodes('.paper-card')
      const interactiveEdges = cy.edges('.cites-edge')
      const memberNodes = interactiveNodes.filter((n) => memberNodeIds.has(n.id()))
      const memberEdges = interactiveEdges.filter(
        (e) =>
          memberNodeIds.has(e.data('source')) || memberNodeIds.has(e.data('target'))
      )

      cy.elements().removeClass(
        'focused-node focused-edge neighbor-edge dimmed-node dimmed-edge focused-group-box'
      )
      clickedBox.addClass('focused-group-box')
      interactiveNodes.not(memberNodes).addClass('dimmed-node')
      interactiveEdges.not(memberEdges).addClass('dimmed-edge')
      memberNodes.addClass('focused-node')
      memberEdges.addClass('neighbor-edge')
    })

    // Paper Card Click: Inspect paper
    cy.on('tap', 'node.paper-card', (evt) => {
      evt.stopPropagation()
      const clicked = evt.target
      const nodeData = clicked.data()
      const isShift = Boolean(evt.originalEvent?.shiftKey)

      if (isShift && nodeData.type === 'Paper') {
        setComparedPaperIds((prev) =>
          prev.includes(nodeData.id)
            ? prev.filter((id) => id !== nodeData.id)
            : [...prev, nodeData.id]
        )
      } else {
        setComparedPaperIds(nodeData.type === 'Paper' ? [nodeData.id] : [])
      }

      setSelectedEdge(null)
      setSelectedCategory(null)
      setSelectedNode(nodeData)

      const interactiveNodes = cy.nodes('.paper-card')
      const interactiveEdges = cy.edges('.cites-edge')
      const neighborhood = clicked.closedNeighborhood()

      cy.elements().removeClass(
        'focused-node focused-edge neighbor-edge dimmed-node dimmed-edge focused-group-box'
      )
      interactiveNodes.not(neighborhood.nodes()).addClass('dimmed-node')
      interactiveEdges.not(neighborhood.edges()).addClass('dimmed-edge')
      clicked.addClass('focused-node')
      neighborhood.edges('.cites-edge').addClass('neighbor-edge')
    })

    // Edge Click: Open Citation Link Inspector showing all exact citation occurrences in the citing paper
    cy.on('tap', 'edge.cites-edge', (evt) => {
      evt.stopPropagation()
      const clickedEdge = evt.target
      const edgeData = clickedEdge.data()
      setSelectedNode(null)
      setSelectedCategory(null)
      setSelectedEdge(edgeData)

      const interactiveNodes = cy.nodes('.paper-card')
      const interactiveEdges = cy.edges('.cites-edge')
      const endpoints = clickedEdge.connectedNodes()

      cy.elements().removeClass(
        'focused-node focused-edge neighbor-edge dimmed-node dimmed-edge focused-group-box'
      )
      interactiveNodes.not(endpoints).addClass('dimmed-node')
      interactiveEdges.not(clickedEdge).addClass('dimmed-edge')
      endpoints.addClass('focused-node')
      clickedEdge.addClass('focused-edge')
    })

    // Hovering a Paper node highlights its connected citation edges
    cy.on('mouseover', 'node.paper-card', (evt) => {
      const hovered = evt.target
      if (!selectedNode && !selectedEdge && !selectedCategory && !activeQuery) {
        hovered.connectedEdges('.cites-edge').addClass('neighbor-edge')
      }
    })

    cy.on('mouseout', 'node.paper-card', (evt) => {
      const hovered = evt.target
      if (!selectedNode && !selectedEdge && !selectedCategory && !activeQuery) {
        hovered.connectedEdges('.cites-edge').removeClass('neighbor-edge')
      }
    })

    // Clicking the canvas background restores 100% opacity to all nodes & edges
    cy.on('tap', (evt) => {
      if (evt.target === cy) {
        setSelectedNode(null)
        setSelectedEdge(null)
        setSelectedCategory(null)
        setComparedPaperIds([])
        cy.elements().removeClass(
          'focused-node focused-edge neighbor-edge dimmed-node dimmed-edge active-node active-edge focused-group-box'
        )
        cy.animate({
          fit: {
            eles: cy.elements(),
            padding: 68,
          },
          duration: 380,
          easing: 'ease-out-cubic',
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
  }, [processedGraph, layoutDirection, activeQuery])

  const handleZoom = (factor) => {
    if (!cyRef.current || !containerRef.current) return
    const currentZoom = cyRef.current.zoom()
    cyRef.current.animate({
      zoom: {
        level: currentZoom * factor,
        renderedPosition: {
          x: containerRef.current.clientWidth / 2,
          y: containerRef.current.clientHeight / 2,
        },
      },
      duration: 180,
    })
  }

  const handleFit = () => {
    if (cyRef.current) {
      cyRef.current.animate({
        fit: { eles: cyRef.current.elements(), padding: 68 },
        duration: 320,
      })
    }
  }

  const paperRelations = selectedNode?.metadata?.paper_relations || []
  const edgeCitations = selectedEdge?.metadata?.citations || []
  const categoryDetails = selectedCategory?.metadata?.details || null
  const categoryPapers = categoryDetails?.papers || []

  return (
    <div className="flex flex-col h-full bg-[#09090b] relative select-none">
      {/* Minimalist Graph Toolbar */}
      <div className="h-10 px-4 border-b border-[#27272a] bg-[#09090b] flex flex-wrap items-center justify-between gap-2 z-10 shrink-0">
        <div className="flex items-center gap-2">
          <Network className="w-3.5 h-3.5 text-[#6366f1]" />
          <span className="text-xs font-medium text-[#f4f4f5]">
            Topic &amp; Citation Timeline
          </span>
          <span className="text-[11px] px-2 py-0.5 rounded bg-[#18181b] text-[#a1a1aa] border border-[#27272a] font-mono">
            {stats.papers} Papers · {stats.groups} {stats.groups === 1 ? 'Category' : 'Categories'}
          </span>
        </div>

        <div className="flex items-center gap-2">
          {/* Toggle Top-to-Bottom vs Left-to-Right Chronological Flow */}
          <button
            type="button"
            onClick={() =>
              setLayoutDirection((prev) => (prev === 'TB' ? 'LR' : 'TB'))
            }
            className="px-2.5 py-1 rounded-md bg-[#18181b] hover:bg-[#27272a] border border-[#27272a] text-xs font-medium text-[#a1a1aa] hover:text-[#f4f4f5] flex items-center gap-1.5 transition cursor-pointer"
            title="Switch timeline orientation"
          >
            {layoutDirection === 'TB' ? (
              <>
                <ArrowDownUp className="w-3.5 h-3.5 text-[#6366f1]" />
                <span>Top → Bottom</span>
              </>
            ) : (
              <>
                <ArrowLeftRight className="w-3.5 h-3.5 text-[#6366f1]" />
                <span>Left → Right</span>
              </>
            )}
          </button>

          {/* Zoom & Fit Controls */}
          <div className="flex items-center gap-1 bg-[#18181b] rounded-md px-1.5 py-0.5 border border-[#27272a]">
            <button
              type="button"
              onClick={() => handleZoom(1.25)}
              className="p-0.5 text-[#a1a1aa] hover:text-[#f4f4f5] cursor-pointer"
              title="Zoom In"
            >
              <ZoomIn className="w-3.5 h-3.5" />
            </button>
            <button
              type="button"
              onClick={() => handleZoom(0.8)}
              className="p-0.5 text-[#a1a1aa] hover:text-[#f4f4f5] cursor-pointer"
              title="Zoom Out"
            >
              <ZoomOut className="w-3.5 h-3.5" />
            </button>
            <button
              type="button"
              onClick={handleFit}
              className="p-0.5 text-[#a1a1aa] hover:text-[#f4f4f5] cursor-pointer"
              title="Fit Graph to Screen"
            >
              <Maximize2 className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </div>

      {/* Query-Linked Highlight Banner */}
      {activeQuery && (
        <div className="px-4 py-1.5 bg-[#18181b] border-b border-[#27272a] flex items-center justify-between text-xs text-[#f4f4f5] z-10">
          <div className="flex items-center gap-2 truncate">
            <Sparkles className="w-3.5 h-3.5 text-[#6366f1] shrink-0" />
            <span className="truncate text-[#a1a1aa]">
              Highlighting cited papers for <strong className="text-[#f4f4f5]">&ldquo;{activeQuery}&rdquo;</strong>
              <span className="ml-1.5 text-[11px] text-[#a1a1aa]/80">
                (Click background to restore all)
              </span>
            </span>
          </div>
          {onResetHighlight && (
            <button
              type="button"
              onClick={onResetHighlight}
              className="ml-2 px-2 py-0.5 rounded bg-[#27272a] hover:bg-[#3f3f46] text-[#f4f4f5] text-[11px] flex items-center gap-1 shrink-0 cursor-pointer transition"
            >
              <RotateCcw className="w-3 h-3" />
              Reset
            </button>
          )}
        </div>
      )}

      {/* Cytoscape Canvas + Pinned Viewport Year Scale */}
      <div className="relative flex-1 w-full h-full overflow-hidden bg-[#09090b]">
        {/* Full-Viewport Year Alignment Hairlines (Track Pan & Zoom in Real Time) */}
        <div className="absolute inset-0 pointer-events-none overflow-hidden z-[1]">
          {yearTicks.map((tick) => {
            const screenCoord =
              layoutDirection === 'TB'
                ? tick.modelCoord * viewportTransform.zoom + viewportTransform.panY
                : tick.modelCoord * viewportTransform.zoom + viewportTransform.panX

            return layoutDirection === 'TB' ? (
              <div
                key={`hairline_${tick.rankIndex}`}
                className="absolute left-0 right-0 border-t border-dashed border-[#27272a]/80"
                style={{ top: `${screenCoord}px` }}
              />
            ) : (
              <div
                key={`hairline_${tick.rankIndex}`}
                className="absolute top-0 bottom-0 border-l border-dashed border-[#27272a]/80"
                style={{ left: `${screenCoord}px` }}
              />
            )
          })}
        </div>

        {/* Cytoscape Interactive Surface */}
        <div ref={containerRef} className="w-full h-full bg-transparent relative z-[2]" />

        {/* Pinned Viewport Year Scale (Attached to Viewer Left Edge in TB mode / Top Edge in LR mode) */}
        {yearTicks.length > 0 && layoutDirection === 'TB' && (
          <div className="absolute left-0 top-0 bottom-0 w-[76px] bg-[#09090b]/90 border-r border-[#27272a] backdrop-blur-md pointer-events-none z-10 overflow-hidden">
            {/* Fixed Scale Header */}
            <div className="absolute top-0 left-0 right-0 h-6 bg-[#18181b]/95 border-b border-[#27272a] flex items-center justify-center z-20">
              <span className="text-[9px] font-mono font-bold uppercase tracking-widest text-[#a1a1aa]">
                Year
              </span>
            </div>

            {/* Spine Segments & Compressed Multi-Year Gap Markers */}
            {yearTicks.map((tick) => {
              if (tick.prevModelCoord === null) return null
              const y1 =
                tick.prevModelCoord * viewportTransform.zoom + viewportTransform.panY
              const y2 =
                tick.modelCoord * viewportTransform.zoom + viewportTransform.panY
              const top = Math.min(y1, y2)
              const height = Math.max(0, Math.abs(y2 - y1))
              const midY = (y1 + y2) / 2

              return (
                <React.Fragment key={`spine_${tick.rankIndex}`}>
                  <div
                    className={`absolute left-[37px] -translate-x-1/2 w-0 ${
                      tick.gapLabel
                        ? 'border-l-2 border-dashed border-[#52525b]'
                        : 'border-l-2 border-solid border-[#3f3f46]'
                    }`}
                    style={{ top: `${top}px`, height: `${height}px` }}
                  />
                  {tick.gapLabel && height >= 44 && (
                    <div
                      className="absolute left-[37px] -translate-x-1/2 -translate-y-1/2 px-1.5 py-0.5 rounded bg-[#09090b] border border-[#27272a] text-[9px] font-mono font-semibold text-[#a1a1aa] whitespace-nowrap shadow-sm"
                      style={{ top: `${midY}px` }}
                    >
                      ⋮ {tick.gapLabel}
                    </div>
                  )}
                </React.Fragment>
              )
            })}

            {/* Pinned Year Badges & Right Alignment Ticks */}
            {yearTicks.map((tick) => {
              const screenY =
                tick.modelCoord * viewportTransform.zoom + viewportTransform.panY
              return (
                <div
                  key={`badge_${tick.rankIndex}`}
                  className="absolute left-0 right-0 flex items-center justify-between pl-2 pr-0 -translate-y-1/2"
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

        {yearTicks.length > 0 && layoutDirection === 'LR' && (
          <div className="absolute top-0 left-0 right-0 h-[38px] bg-[#09090b]/90 border-b border-[#27272a] backdrop-blur-md pointer-events-none z-10 overflow-hidden">
            {/* Fixed Left Header */}
            <div className="absolute left-0 top-0 bottom-0 px-2.5 bg-[#18181b]/95 border-r border-[#27272a] flex items-center justify-center z-20">
              <span className="text-[9px] font-mono font-bold uppercase tracking-widest text-[#a1a1aa]">
                Year
              </span>
            </div>

            {/* Horizontal Spine Segments & Compressed Gap Badges */}
            {yearTicks.map((tick) => {
              if (tick.prevModelCoord === null) return null
              const x1 =
                tick.prevModelCoord * viewportTransform.zoom + viewportTransform.panX
              const x2 =
                tick.modelCoord * viewportTransform.zoom + viewportTransform.panX
              const left = Math.min(x1, x2)
              const width = Math.max(0, Math.abs(x2 - x1))
              const midX = (x1 + x2) / 2

              return (
                <React.Fragment key={`hspine_${tick.rankIndex}`}>
                  <div
                    className={`absolute top-[19px] -translate-y-1/2 h-0 ${
                      tick.gapLabel
                        ? 'border-t-2 border-dashed border-[#52525b]'
                        : 'border-t-2 border-solid border-[#3f3f46]'
                    }`}
                    style={{ left: `${left}px`, width: `${width}px` }}
                  />
                  {tick.gapLabel && width >= 54 && (
                    <div
                      className="absolute top-[19px] -translate-x-1/2 -translate-y-1/2 px-1.5 py-0.5 rounded bg-[#09090b] border border-[#27272a] text-[9px] font-mono font-semibold text-[#a1a1aa] whitespace-nowrap"
                      style={{ left: `${midX}px` }}
                    >
                      ⋯ {tick.gapLabel}
                    </div>
                  )}
                </React.Fragment>
              )
            })}

            {/* Pinned Year Badges */}
            {yearTicks.map((tick) => {
              const screenX =
                tick.modelCoord * viewportTransform.zoom + viewportTransform.panX
              return (
                <div
                  key={`hbadge_${tick.rankIndex}`}
                  className="absolute top-0 bottom-0 flex flex-col items-center justify-between pt-1 pb-0 -translate-x-1/2"
                  style={{ left: `${screenX}px` }}
                >
                  <span className="px-2 py-0.5 rounded-md bg-[#18181b] border border-[#3f3f46] text-[11px] font-mono font-bold text-[#f4f4f5] shadow-md">
                    {tick.label}
                  </span>
                  <span className="h-1.5 w-[2px] bg-[#6366f1]/80" />
                </div>
              )
            })}
          </div>
        )}
      </div>

      {/* Minimalist Legend Overlay (Bottom Left, shifted right of the Pinned Year Scale in TB mode) */}
      <div
        className={`absolute bottom-4 ${
          layoutDirection === 'TB' ? 'left-[88px]' : 'left-4'
        } px-3 py-2 rounded-lg bg-[#18181b]/90 border border-[#27272a] backdrop-blur-sm flex flex-wrap items-center gap-3 text-[11px] text-[#a1a1aa] pointer-events-none z-10`}
      >
        <div className="flex items-center gap-1.5">
          <span className="w-3 h-2.5 rounded-[2px] bg-[#18181b] border border-[#6366f1] inline-block" />
          <span className="text-[#f4f4f5] font-medium">Paper Card</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="w-3 h-2.5 rounded-[2px] bg-[#18181b] border border-dashed border-[#6366f1]/70 inline-block" />
          <span>Clickable Topic Category / Subcategory</span>
        </div>
        <span className="text-[#a1a1aa]/70 hidden sm:inline">
          · Click any category, paper, or &ldquo;Cites&rdquo; arrow to inspect
        </span>
      </div>

      {/* Clickable Category / Subcategory Topic Inspector Drawer (Strictly Grounded in Provided Papers) */}
      {selectedCategory && (
        <div className="absolute top-14 right-4 bottom-4 max-h-[calc(100%-4.5rem)] w-96 max-w-[92vw] p-4 rounded-xl bg-[#18181b]/95 border border-[#27272a] shadow-2xl flex flex-col gap-3 z-20 overflow-hidden backdrop-blur-md">
          {/* Header */}
          <div className="flex items-center justify-between gap-2 shrink-0">
            <div className="flex items-center gap-1.5 flex-wrap">
              <span className="text-[10px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded bg-[#6366f1]/15 text-[#818cf8] border border-[#6366f1]/30">
                {selectedCategory.metadata?.categoryType || 'Category'} ({categoryPapers.length}{' '}
                {categoryPapers.length === 1 ? 'Paper' : 'Papers'})
              </span>
              {selectedCategory.metadata?.parentLabel && (
                <span className="text-[10px] font-medium px-2 py-0.5 rounded bg-[#27272a] text-[#e4e4e7]">
                  in {selectedCategory.metadata.parentLabel}
                </span>
              )}
            </div>
            <button
              type="button"
              onClick={() => setSelectedCategory(null)}
              className="text-[#a1a1aa] hover:text-[#f4f4f5] cursor-pointer p-0.5 shrink-0"
              title="Close"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          {/* Category Title & Subcategories */}
          <div className="shrink-0">
            <h4 className="text-sm font-semibold text-[#f4f4f5] leading-snug">
              {selectedCategory.label}
            </h4>
            {selectedCategory.metadata?.subcategories?.length > 0 && (
              <p className="text-[11px] text-[#a1a1aa] mt-1">
                Subcategories:{' '}
                <span className="text-[#e4e4e7]">
                  {selectedCategory.metadata.subcategories.join(' · ')}
                </span>
              </p>
            )}
          </div>

          {/* Scrollable Grounded Content */}
          <div className="flex-1 min-h-0 overflow-y-auto space-y-3 pr-1.5">
            {/* Topic Synthesis Strictly From Provided Papers */}
            {categoryDetails?.overview && (
              <div className="p-3 rounded-lg bg-[#09090b]/80 border border-[#27272a] space-y-2">
                <p className="text-[10px] font-medium uppercase tracking-wider text-[#a1a1aa]">
                  Topic Discussed in Provided Papers
                </p>
                <div className="space-y-2 text-xs text-[#e4e4e7] leading-relaxed">
                  {categoryDetails.overview.split('\n\n').map((para, pIdx) => (
                    <p key={pIdx}>
                      {renderMathSegment(para, `cat-ov-${selectedCategory.id}-${pIdx}`)}
                    </p>
                  ))}
                </div>
              </div>
            )}

            {/* Methods & Datasets Extracted From Papers in This Category */}
            {(categoryDetails?.methods?.length > 0 ||
              categoryDetails?.datasets?.length > 0) && (
              <div className="space-y-2">
                {categoryDetails.methods?.length > 0 && (
                  <div className="p-2.5 rounded-lg bg-[#09090b]/60 border border-[#27272a]">
                    <p className="text-[10px] font-medium uppercase tracking-wider text-emerald-400 mb-1.5">
                      Methods in This Group ({categoryDetails.methods.length})
                    </p>
                    <div className="flex flex-wrap gap-1">
                      {categoryDetails.methods.map((m) => (
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

                {categoryDetails.datasets?.length > 0 && (
                  <div className="p-2.5 rounded-lg bg-[#09090b]/60 border border-[#27272a]">
                    <p className="text-[10px] font-medium uppercase tracking-wider text-amber-400 mb-1.5">
                      Datasets Evaluated ({categoryDetails.datasets.length})
                    </p>
                    <div className="flex flex-wrap gap-1">
                      {categoryDetails.datasets.map((d) => (
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

            {/* Chronological Breakdown of Papers & Grounded Excerpts */}
            {categoryPapers.length > 0 && (
              <div className="space-y-2">
                <p className="text-[10px] font-medium uppercase tracking-wider text-[#a1a1aa]">
                  Papers &amp; Source Excerpts ({categoryPapers.length})
                </p>
                {categoryPapers.map((pItem, idx) => (
                  <div
                    key={`${pItem.paper_id}-${idx}`}
                    className="p-3 rounded-lg bg-[#09090b]/70 border border-[#27272a] space-y-2"
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div>
                        <p className="text-xs font-semibold text-[#f4f4f5] leading-snug">
                          {pItem.paper_title}
                        </p>
                        <p className="text-[11px] text-[#a1a1aa] mt-0.5">
                          {pItem.authors?.slice(0, 3).join(', ')}
                          {pItem.authors?.length > 3 ? ' et al.' : ''}
                          {pItem.year ? ` · ${pItem.year}` : ''}
                        </p>
                      </div>
                      <button
                        type="button"
                        onClick={() =>
                          handleJumpToCitation({
                            chunk_id: pItem.chunk_id,
                            paper_id: pItem.paper_id,
                            paper_title: pItem.paper_title,
                            page: pItem.page || 1,
                            section: pItem.section || 'Abstract',
                            bbox: pItem.bbox || null,
                            snippet: pItem.excerpt || '',
                          })
                        }
                        className="px-2 py-1 rounded bg-[#6366f1]/15 hover:bg-[#6366f1]/25 text-[#818cf8] border border-[#6366f1]/30 text-[10px] font-mono font-semibold flex items-center gap-1 shrink-0 cursor-pointer transition"
                        title="Open passage in PDF Reader"
                      >
                        <BookOpen className="w-3 h-3" />
                        p.{pItem.page || 1}
                      </button>
                    </div>

                    {pItem.excerpt && (
                      <p className="text-xs text-[#e4e4e7] leading-relaxed bg-[#18181b]/70 p-2 rounded border border-[#27272a]/70">
                        &ldquo;
                        {renderMathSegment(pItem.excerpt, `cat-p-${idx}`)}
                        &rdquo;
                      </p>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Action Footer */}
          {onAskAboutNode && (
            <div className="pt-2 border-t border-[#27272a] shrink-0">
              <button
                type="button"
                onClick={() =>
                  onAskAboutNode(
                    `Compare how the papers in the "${selectedCategory.label}" category (${categoryPapers
                      .map((p) => p.paper_title)
                      .join(', ')}) address this topic and build on one another.`
                  )
                }
                className="w-full px-3 py-2 rounded-lg bg-[#6366f1] hover:bg-[#4f46e5] text-white text-xs font-medium flex items-center justify-center gap-1.5 transition cursor-pointer"
              >
                <MessageSquarePlus className="w-3.5 h-3.5" />
                Ask About This Category in Chat
              </button>
            </div>
          )}
        </div>
      )}

      {/* Clickable Citation Edge Inspector Drawer (When user clicks a "Cites" arrow) */}
      {selectedEdge && (
        <div className="absolute top-14 right-4 bottom-4 max-h-[calc(100%-4.5rem)] w-96 max-w-[92vw] p-4 rounded-xl bg-[#18181b]/95 border border-[#27272a] shadow-2xl flex flex-col gap-3 z-20 overflow-hidden backdrop-blur-md">
          <div className="flex items-center justify-between gap-2 shrink-0">
            <span className="text-[10px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded bg-[#6366f1]/15 text-[#818cf8] border border-[#6366f1]/30">
              Citation Link ({edgeCitations.length || 1} Found)
            </span>
            <button
              type="button"
              onClick={() => setSelectedEdge(null)}
              className="text-[#a1a1aa] hover:text-[#f4f4f5] cursor-pointer p-0.5"
              title="Close"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          {/* Citing -> Cited Paper Header */}
          <div className="p-3 rounded-lg bg-[#09090b] border border-[#27272a] space-y-2 shrink-0">
            <div>
              <p className="text-[10px] font-medium uppercase tracking-wider text-[#a1a1aa]">
                Citing Paper ({selectedEdge.metadata?.citing_year || 'N/A'})
              </p>
              <p className="text-xs font-semibold text-[#f4f4f5] leading-snug mt-0.5">
                {selectedEdge.metadata?.citing_paper_title || selectedEdge.source}
              </p>
            </div>
            <div className="flex items-center gap-1.5 text-[11px] text-[#818cf8] font-medium">
              <ArrowRight className="w-3.5 h-3.5" />
              <span>cites</span>
            </div>
            <div>
              <p className="text-[10px] font-medium uppercase tracking-wider text-[#a1a1aa]">
                Cited Paper ({selectedEdge.metadata?.cited_year || 'N/A'})
              </p>
              <p className="text-xs font-semibold text-[#f4f4f5] leading-snug mt-0.5">
                {selectedEdge.metadata?.cited_paper_title || selectedEdge.target}
              </p>
            </div>
          </div>

          {/* Preprint / Revision Chronology Note when older-dated paper cites newer-dated paper */}
          {selectedEdge.metadata?.is_preprint_anomaly && (
            <div className="p-3 rounded-lg bg-amber-500/10 border border-amber-500/35 text-amber-200 text-xs space-y-1 shrink-0">
              <p className="font-semibold flex items-center gap-1.5 text-amber-300">
                <AlertTriangle className="w-3.5 h-3.5 shrink-0" />
                <span>Preprint / Revision Year Difference</span>
              </p>
              <p className="text-[11px] text-amber-200/90 leading-relaxed">
                {selectedEdge.metadata.anomaly_note}
              </p>
            </div>
          )}

          {/* All Exact Citation Locations in the Citing Paper */}
          <div className="flex-1 min-h-0 overflow-y-auto space-y-2 pr-1.5">
            <p className="text-[10px] font-medium uppercase tracking-wider text-[#a1a1aa]">
              Exact Citations in Paper (Click to View in PDF)
            </p>
            {edgeCitations.length === 0 ? (
              <p className="text-xs text-[#a1a1aa]">
                No passage details available for this link.
              </p>
            ) : (
              edgeCitations.map((occ, idx) => (
                <button
                  key={`${occ.chunk_id || idx}-${occ.page}`}
                  type="button"
                  onClick={() => handleJumpToCitation(occ)}
                  className="w-full text-left p-3 rounded-lg bg-[#09090b]/80 hover:bg-[#27272a]/50 border border-[#27272a] hover:border-[#6366f1]/60 transition space-y-1.5 group cursor-pointer"
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className="px-1.5 py-0.5 rounded bg-[#6366f1]/15 text-[#818cf8] border border-[#6366f1]/30 text-[10px] font-mono font-semibold">
                      Citation #{idx + 1} · Page {occ.page}
                    </span>
                    <span className="text-[11px] text-[#818cf8] group-hover:text-[#a5b4fc] flex items-center gap-1 font-medium">
                      <BookOpen className="w-3 h-3" />
                      View in PDF
                    </span>
                  </div>
                  {occ.section && (
                    <p className="text-[11px] text-[#a1a1aa] font-medium truncate">
                      Section: {occ.section}
                    </p>
                  )}
                  <p className="text-xs text-[#e4e4e7] leading-relaxed">
                    &ldquo;
                    {renderMathSegment(occ.snippet, `edge-occ-${idx}`)}
                    &rdquo;
                  </p>
                </button>
              ))
            )}
          </div>
        </div>
      )}

      {/* Node Inspector Drawer (Right Overlay) */}
      {selectedNode && (
        <div className="absolute top-14 right-4 bottom-4 max-h-[calc(100%-4.5rem)] w-96 max-w-[92vw] p-4 rounded-xl bg-[#18181b]/95 border border-[#27272a] shadow-2xl flex flex-col gap-3 z-20 overflow-hidden backdrop-blur-md">
          {/* Header */}
          <div className="flex items-center justify-between gap-2 shrink-0">
            <div className="flex items-center gap-1.5 flex-wrap">
              <span className="text-[10px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded bg-[#6366f1]/15 text-[#818cf8] border border-[#6366f1]/30">
                {selectedNode.type}
              </span>
              {selectedNode.metadata?.group_label && (
                <span className="text-[10px] font-medium px-2 py-0.5 rounded bg-[#27272a] text-[#e4e4e7]">
                  {selectedNode.metadata.group_label}
                  {selectedNode.metadata.subgroup_label
                    ? ` › ${selectedNode.metadata.subgroup_label}`
                    : ''}
                </span>
              )}
            </div>
            <div className="flex items-center gap-2 shrink-0">
              {selectedNode.metadata?.year && (
                <span className="text-xs font-mono text-[#a1a1aa]">
                  {selectedNode.metadata.year}
                </span>
              )}
              <button
                type="button"
                onClick={() => setSelectedNode(null)}
                className="text-[#a1a1aa] hover:text-[#f4f4f5] cursor-pointer p-0.5"
                title="Close"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          </div>

          {/* Node Title & Authors */}
          <div className="shrink-0">
            <h4 className="text-sm font-semibold text-[#f4f4f5] leading-snug">
              {selectedNode.label}
            </h4>
            {selectedNode.type === 'Paper' && selectedNode.metadata?.authors && (
              <p className="text-xs text-[#a1a1aa] mt-1">
                {selectedNode.metadata.authors.slice(0, 4).join(', ')}
                {selectedNode.metadata.authors.length > 4 ? ' et al.' : ''}
              </p>
            )}
          </div>

          {/* Scrollable Details */}
          <div className="flex-1 min-h-0 overflow-y-auto space-y-3 pr-1.5">
            {selectedNode.metadata?.description && (
              <div className="p-3 rounded-lg bg-[#09090b]/80 border border-[#27272a] space-y-1">
                <p className="text-[10px] font-medium uppercase tracking-wider text-[#a1a1aa]">
                  {selectedNode.type === 'Paper' ? 'Summary' : 'Overview'}
                </p>
                <p className="text-xs text-[#e4e4e7] leading-relaxed">
                  {renderMathSegment(
                    selectedNode.metadata.description,
                    `desc-${selectedNode.id}`
                  )}
                </p>
              </div>
            )}

            {/* Paper Methods & Datasets Tags */}
            {selectedNode.type === 'Paper' && selectedNode.metadata && (
              <div className="space-y-2">
                {selectedNode.metadata.methods?.length > 0 && (
                  <div className="p-2.5 rounded-lg bg-[#09090b]/60 border border-[#27272a]">
                    <p className="text-[10px] font-medium uppercase tracking-wider text-emerald-400 mb-1.5">
                      Methods ({selectedNode.metadata.methods.length})
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
                  <div className="p-2.5 rounded-lg bg-[#09090b]/60 border border-[#27272a]">
                    <p className="text-[10px] font-medium uppercase tracking-wider text-amber-400 mb-1.5">
                      Datasets ({selectedNode.metadata.datasets.length})
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

            {/* Connected Papers & All Citation Locations */}
            {paperRelations.length > 0 && (
              <div className="space-y-2">
                <p className="text-[10px] font-medium uppercase tracking-wider text-[#a1a1aa]">
                  Connected Papers ({paperRelations.length})
                </p>
                {paperRelations.map((rel, idx) => {
                  const occurrences = rel.citations || []
                  return (
                    <div
                      key={`${rel.paper_id}-${idx}`}
                      className="p-2.5 rounded-lg bg-[#09090b]/60 border border-[#27272a] space-y-2"
                    >
                      <div className="flex items-center justify-between gap-2">
                        <span className="text-[10px] font-medium px-1.5 py-0.5 rounded bg-[#6366f1]/15 text-[#818cf8] border border-[#6366f1]/30">
                          {rel.role}
                        </span>
                        {occurrences.length === 0 && (
                          <button
                            type="button"
                            onClick={() =>
                              handleJumpToCitation({
                                paper_id: rel.paper_id,
                                paper_title: rel.paper_title,
                                page: rel.page || 1,
                                bbox: rel.bbox || null,
                                section: rel.section || '',
                                snippet: rel.explanation || '',
                              })
                            }
                            className="text-[11px] text-[#818cf8] hover:text-[#a5b4fc] flex items-center gap-1 font-mono cursor-pointer"
                            title="Open in PDF Reader"
                          >
                            <BookOpen className="w-3 h-3" />
                            p.{rel.page || 1}
                          </button>
                        )}
                      </div>

                      <p className="text-xs font-medium text-[#f4f4f5]">
                        {rel.paper_title} {rel.year ? `(${rel.year})` : ''}
                      </p>

                      {occurrences.length > 0 ? (
                        <div className="space-y-1.5 pt-1">
                          {occurrences.map((occ, occIdx) => (
                            <button
                              key={`${occ.chunk_id || occIdx}-${occ.page}`}
                              type="button"
                              onClick={() => handleJumpToCitation(occ)}
                              className="w-full text-left p-2 rounded bg-[#18181b] hover:bg-[#27272a] border border-[#27272a] hover:border-[#6366f1]/50 transition space-y-1 cursor-pointer"
                            >
                              <div className="flex items-center justify-between text-[10px]">
                                <span className="font-mono font-semibold text-[#818cf8] flex items-center gap-1">
                                  <Quote className="w-2.5 h-2.5" />
                                  Page {occ.page}
                                  {occ.section ? ` · ${occ.section}` : ''}
                                </span>
                                <span className="text-[#a1a1aa] hover:text-[#f4f4f5]">
                                  Open PDF →
                                </span>
                              </div>
                              <p className="text-[11px] text-[#a1a1aa] line-clamp-2 leading-relaxed">
                                &ldquo;
                                {renderMathSegment(
                                  occ.snippet,
                                  `rel-occ-${idx}-${occIdx}`
                                )}
                                &rdquo;
                              </p>
                            </button>
                          ))}
                        </div>
                      ) : (
                        <p className="text-xs text-[#a1a1aa] leading-relaxed">
                          &ldquo;
                          {renderMathSegment(
                            rel.explanation,
                            `rel-${rel.paper_id}-${idx}`
                          )}
                          &rdquo;
                        </p>
                      )}
                    </div>
                  )
                })}
              </div>
            )}
          </div>

          {/* Action Footer */}
          <div className="pt-2 border-t border-[#27272a] flex flex-col gap-1.5 shrink-0">
            {onAskAboutNode && (
              <button
                type="button"
                onClick={() =>
                  onAskAboutNode(
                    selectedNode.type === 'Paper'
                      ? `What are the main contributions and results of ${selectedNode.label}?`
                      : `How is ${selectedNode.label} used across the uploaded papers?`
                  )
                }
                className="w-full px-3 py-2 rounded-lg bg-[#6366f1] hover:bg-[#4f46e5] text-white text-xs font-medium flex items-center justify-center gap-1.5 transition cursor-pointer"
              >
                <MessageSquarePlus className="w-3.5 h-3.5" />
                Ask About This in Chat
              </button>
            )}

            {selectedNode.type === 'Paper' && selectedNode.metadata?.paper_id && (
              <button
                type="button"
                onClick={() =>
                  onOpenPaperInReader &&
                  onOpenPaperInReader(selectedNode.metadata.paper_id, 1)
                }
                className="w-full px-3 py-2 rounded-lg bg-[#09090b] hover:bg-[#27272a] border border-[#27272a] text-[#f4f4f5] text-xs font-medium flex items-center justify-center gap-1.5 transition cursor-pointer"
              >
                <ExternalLink className="w-3.5 h-3.5 text-[#818cf8]" />
                Read Paper PDF
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
