/**
 * Knowledge Graph visualization configuration, SVG mini-card builders,
 * timeline ordinal rank algorithms, and obstacle-avoiding edge routing.
 */

export function escapeXml(str = '') {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&apos;')
}

export function wrapTwoLines(text = '', maxChars = 25) {
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

export function formatAuthorYear(metadata = {}) {
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

export function buildPaperCardSvg(nodeData, { isActive = false, isFocused = false } = {}) {
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

export function bezierIntersectsBox(p1, cp, p2, center, halfW = 92, halfH = 40) {
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

export function computeControlPoint(p1, p2, cpDist, cpWeight = 0.5) {
  const dx = p2.x - p1.x
  const dy = p2.y - p1.y
  const len = Math.hypot(dx, dy) || 1
  const baseX = p1.x + dx * cpWeight
  const baseY = p1.y + dy * cpWeight
  const nx = -dy / len
  const ny = dx / len
  return {
    x: baseX + nx * cpDist,
    y: baseY + ny * cpDist,
  }
}

export function buildFallbackCategoryDetails(pNodes) {
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

export function buildStructuredTimelineLayout(paperNodes, edges, direction = 'TB') {
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

  // 1. Extract sorted unique years
  const uniqueYears = Array.from(
    new Set(
      paperNodes.map((n) => {
        const y = Number(n.data.metadata?.year)
        return Number.isFinite(y) && y > 1800 ? y : 9999
      })
    )
  ).sort((a, b) => a - b)

  const yearToRank = new Map(uniqueYears.map((y, idx) => [y, idx]))

  // 2. Organize papers into Groups and Subgroups
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

  const sortedGroups = Array.from(groupsMap.values()).sort((a, b) => {
    if (b.papers.length !== a.papers.length) return b.papers.length - a.papers.length
    const minYearA = Math.min(...a.papers.map((p) => Number(p.data.metadata?.year) || 9999))
    const minYearB = Math.min(...b.papers.map((p) => Number(p.data.metadata?.year) || 9999))
    return minYearA - minYearB
  })

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

      const byRank = new Map()
      sub.papers.forEach((pNode) => {
        const y = Number(pNode.data.metadata?.year)
        const normY = Number.isFinite(y) && y > 1800 ? y : 9999
        const r = yearToRank.get(normY) ?? 0
        if (!byRank.has(r)) byRank.set(r, [])
        byRank.get(r).push(pNode)
      })

      let maxColsInSub = 1
      byRank.forEach((list) => {
        if (list.length > maxColsInSub) maxColsInSub = list.length
      })

      byRank.forEach((list, r) => {
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
      data: { id: guideStartId, label: '', type: 'TimelineAnchor' },
      selectable: false,
      grabbable: false,
      classes: 'timeline-anchor-node',
    })

    timelineElements.push({
      group: 'nodes',
      position: guideEndPos,
      data: { id: guideEndId, label: '', type: 'TimelineAnchor' },
      selectable: false,
      grabbable: false,
      classes: 'timeline-anchor-node',
    })

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
    const otherCards = paperRectCenters.filter((item) => item.id !== u && item.id !== v)

    const hitsAnyObstacle = (cpDist) => {
      const cp = computeControlPoint(p1, p2, cpDist, 0.5)
      return otherCards.some((obs) => bezierIntersectsBox(p1, cp, p2, obs.pos, 94, 42))
    }

    if (sameCol && !hitsAnyObstacle(0)) {
      edgeRouting[e.data.id] = {
        curveStyle: 'unbundled-bezier',
        sourceEndpoint: 'outside-to-node',
        targetEndpoint: 'outside-to-node',
        cpDistance: 0,
        cpWeight: 0.5,
      }
    } else if (sameCol) {
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

export function buildCytoscapeStylesheet() {
  return [
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
  ]
}
