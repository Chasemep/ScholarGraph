import React from 'react'
import { renderMathSegment } from '../../utils/mathRenderer'

/**
 * Parses markdown into structured semantic blocks (Headings, Tables, Lists, Rules, Paragraphs)
 * while delegating inline math ($...$, $$...$$) and citation tokens to renderMathSegment and buttons.
 */
export function MarkdownBlockRenderer({
  content = '',
  citations = [],
  onSelectCitation,
  registerPaperId,
}) {
  if (!content) return null

  // Pre-split the text into raw line groups
  const lines = content.split('\n')
  const blocks = []
  let i = 0

  while (i < lines.length) {
    const line = lines[i]
    const trimmed = line.trim()

    // 1. Blank line -> skip
    if (!trimmed) {
      i++
      continue
    }

    // 2. Horizontal rule: --- or ***
    if (/^(\-{3,}|\*{3,})$/.test(trimmed)) {
      blocks.push({ type: 'hr' })
      i++
      continue
    }

    // 3. Headings: #, ##, ###, ####
    const headingMatch = line.match(/^(#{1,4})\s+(.+)$/)
    if (headingMatch) {
      blocks.push({
        type: 'heading',
        level: headingMatch[1].length,
        text: headingMatch[2].trim(),
      })
      i++
      continue
    }

    // 4. Markdown Table: starts with '|' and contains '|'
    if (line.includes('|') && trimmed.startsWith('|')) {
      const tableLines = []
      while (i < lines.length && lines[i].includes('|') && lines[i].trim().startsWith('|')) {
        tableLines.push(lines[i].trim())
        i++
      }
      if (tableLines.length >= 2) {
        const headerRow = tableLines[0]
          .slice(1, -1)
          .split('|')
          .map((c) => c.trim())
        const dataRows = tableLines
          .slice(2)
          .map((row) =>
            row
              .slice(1, -1)
              .split('|')
              .map((c) => c.trim())
          )
          .filter((row) => row.some((cell) => cell.length > 0))

        blocks.push({
          type: 'table',
          headers: headerRow,
          rows: dataRows,
        })
        continue
      }
    }

    // 5. Bullet List items: starts with * or - or •
    if (/^\s*([*\-•]|\d+\.)\s+/.test(line)) {
      const listItems = []
      while (i < lines.length && /^\s*([*\-•]|\d+\.)\s+/.test(lines[i])) {
        const rawItem = lines[i].replace(/^\s*([*\-•]|\d+\.)\s+/, '').trim()
        listItems.push(rawItem)
        i++
      }
      blocks.push({
        type: 'list',
        items: listItems,
      })
      continue
    }

    // 6. Regular Paragraph or display math block
    const paraLines = [line]
    i++
    while (
      i < lines.length &&
      lines[i].trim() &&
      !lines[i].trim().startsWith('|') &&
      !/^(#{1,4})\s+/.test(lines[i]) &&
      !/^(\-{3,}|\*{3,})$/.test(lines[i].trim()) &&
      !/^\s*([*\-•]|\d+\.)\s+/.test(lines[i])
    ) {
      paraLines.push(lines[i])
      i++
    }

    blocks.push({
      type: 'paragraph',
      text: paraLines.join('\n'),
    })
  }

  return (
    <div className="space-y-3.5 text-[13.5px] text-[#e4e4e7] leading-7">
      {blocks.map((block, bIdx) => {
        const key = `block-${bIdx}`

        if (block.type === 'hr') {
          return <hr key={key} className="my-4 border-[#27272a]" />
        }

        if (block.type === 'heading') {
          const contentEl = renderInlineSegmentWithCitations(
            block.text,
            citations,
            onSelectCitation,
            registerPaperId,
            `${key}-h`
          )
          if (block.level === 1) {
            return (
              <h1 key={key} className="text-lg font-bold text-[#f4f4f5] tracking-tight mt-5 mb-2">
                {contentEl}
              </h1>
            )
          }
          if (block.level === 2) {
            return (
              <h2 key={key} className="text-base font-semibold text-[#f4f4f5] tracking-tight mt-4 mb-2">
                {contentEl}
              </h2>
            )
          }
          if (block.level === 3) {
            return (
              <h3 key={key} className="text-sm font-semibold text-[#818cf8] tracking-tight mt-4 mb-1.5 flex items-center gap-1.5">
                <span className="w-1.5 h-1.5 rounded-full bg-[#6366f1]" />
                {contentEl}
              </h3>
            )
          }
          return (
            <h4 key={key} className="text-[13.5px] font-semibold text-[#e4e4e7] mt-3 mb-1">
              {contentEl}
            </h4>
          )
        }

        if (block.type === 'table') {
          return (
            <div key={key} className="my-4 overflow-x-auto rounded-xl border border-[#27272a] bg-[#18181b]/60 shadow-sm">
              <table className="w-full text-left text-xs border-collapse">
                <thead>
                  <tr className="border-b border-[#27272a] bg-[#18181b]">
                    {block.headers.map((h, hIdx) => (
                      <th
                        key={`${key}-th-${hIdx}`}
                        className="py-2.5 px-3.5 font-semibold text-[#f4f4f5] uppercase tracking-wider text-[11px] whitespace-nowrap"
                      >
                        {renderInlineSegmentWithCitations(
                          h,
                          citations,
                          onSelectCitation,
                          registerPaperId,
                          `${key}-th-${hIdx}`
                        )}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#27272a]/60">
                  {block.rows.map((row, rIdx) => (
                    <tr
                      key={`${key}-tr-${rIdx}`}
                      className="hover:bg-[#27272a]/20 transition-colors"
                    >
                      {row.map((cell, cIdx) => (
                        <td
                          key={`${key}-td-${rIdx}-${cIdx}`}
                          className="py-2 px-3.5 text-[#d4d4d8] leading-relaxed align-top"
                        >
                          {renderInlineSegmentWithCitations(
                            cell,
                            citations,
                            onSelectCitation,
                            registerPaperId,
                            `${key}-td-${rIdx}-${cIdx}`
                          )}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )
        }

        if (block.type === 'list') {
          return (
            <ul key={key} className="space-y-1.5 my-2 pl-2">
              {block.items.map((item, lIdx) => (
                <li key={`${key}-li-${lIdx}`} className="flex items-start gap-2">
                  <span className="text-[#818cf8] mt-1 shrink-0 text-xs">•</span>
                  <div className="flex-1 leading-relaxed">
                    {renderInlineSegmentWithCitations(
                      item,
                      citations,
                      onSelectCitation,
                      registerPaperId,
                      `${key}-li-${lIdx}`
                    )}
                  </div>
                </li>
              ))}
            </ul>
          )
        }

        // Paragraph
        return (
          <div key={key} className="leading-relaxed whitespace-pre-line">
            {renderInlineSegmentWithCitations(
              block.text,
              citations,
              onSelectCitation,
              registerPaperId,
              key
            )}
          </div>
        )
      })}
    </div>
  )
}

/**
 * Parses inline citations within an arbitrary block text slice, creating
 * clickable citation badges and running the remainder through renderMathSegment.
 */
function renderInlineSegmentWithCitations(
  textSlice,
  citations = [],
  onSelectCitation,
  registerPaperId,
  prefixKey
) {
  if (!textSlice) return null

  const CITATION_REGEX =
    /\[((?:[a-zA-Z0-9_-]+,\s*(?:Pages?|p\.?)\s*\d+(?:\s*[-–,]\s*(?:Pages?|p\.?)?\s*\d+)*\s*;?)+)\]|(?:\b(paper_[a-zA-Z0-9_-]+|[a-zA-Z0-9]+_[a-zA-Z0-9_-]+)\s*·\s*p\.?\s*(\d+))/gi

  const parts = []
  let lastIndex = 0
  let match

  const findMatchingCitationObj = (rawPaperId, pageNum) => {
    const normalized = rawPaperId.startsWith('paper_') ? rawPaperId : `paper_${rawPaperId}`
    const stripped = rawPaperId.replace(/^paper_/, '')
    return (
      citations.find(
        (c) =>
          (c.paper_id === rawPaperId ||
            c.paper_id === normalized ||
            c.paper_id?.replace(/^paper_/, '') === stripped) &&
          Number(c.page) === pageNum
      ) ||
      citations.find(
        (c) =>
          c.paper_id === rawPaperId ||
          c.paper_id === normalized ||
          c.paper_id?.replace(/^paper_/, '') === stripped
      ) ||
      citations[0]
    )
  }

  while ((match = CITATION_REGEX.exec(textSlice)) !== null) {
    if (match.index > lastIndex) {
      const slice = textSlice.slice(lastIndex, match.index)
      parts.push(
        <React.Fragment key={`${prefixKey}-seg-${lastIndex}`}>
          {renderMathSegment(slice, `${prefixKey}-seg-${lastIndex}`)}
        </React.Fragment>
      )
    }

    if (match[1]) {
      // Bracketed group: [paper_a, Page 1; paper_b, Page 2]
      const items = match[1]
        .split(';')
        .map((s) => s.trim())
        .filter(Boolean)

      items.forEach((item, itIdx) => {
        const m = item.match(/^([a-zA-Z0-9_-]+),\s*(.*)$/)
        if (!m) return
        const rawPaperId = m[1]
        const pagesStr = m[2]
        const refNum = registerPaperId(rawPaperId)
        let pageNums = (pagesStr.match(/\d+/g) || []).map((s) => parseInt(s, 10))
        const range = pagesStr.match(/(\d+)\s*[-–]\s*(?:Pages?|p\.?)?\s*(\d+)/i)
        if (range && pageNums.length === 2) {
          const [a, b] = [parseInt(range[1], 10), parseInt(range[2], 10)]
          if (b >= a && b - a <= 10) pageNums = Array.from({ length: b - a + 1 }, (_, i) => a + i)
        }

        pageNums.forEach((pageNum, pIdx) => {
          const matchedCitation = findMatchingCitationObj(rawPaperId, pageNum)
          const resolvedPaperId =
            matchedCitation?.paper_id ||
            (rawPaperId.startsWith('paper_') ? rawPaperId : `paper_${rawPaperId}`)

          const citationPayload = matchedCitation
            ? { ...matchedCitation, page: pageNum }
            : { paper_id: resolvedPaperId, paper_title: rawPaperId, page: pageNum, bbox: null }

          parts.push(
            <button
              key={`${prefixKey}-cit-${rawPaperId}-${pageNum}-${match.index}-${itIdx}-${pIdx}`}
              type="button"
              onClick={() => onSelectCitation(citationPayload)}
              className="inline-flex items-center mx-0.5 px-1.5 py-0.5 rounded text-[11px] font-mono font-medium bg-[#6366f1]/15 text-[#818cf8] border border-[#6366f1]/30 hover:bg-[#6366f1]/25 hover:text-[#a5b4fc] hover:border-[#6366f1]/60 transition cursor-pointer align-super leading-none"
              title={
                matchedCitation
                  ? `[${refNum}] ${matchedCitation.paper_title} — Page ${pageNum} (Click to open in PDF Reader)`
                  : `[${refNum}] ${rawPaperId} — Page ${pageNum}`
              }
            >
              [{refNum}, p.{pageNum}]
            </button>
          )
        })
      })
    } else {
      // Bare format: paper_a · p.2
      const rawPaperId = match[2]
      const pageNum = parseInt(match[3], 10)
      const refNum = registerPaperId(rawPaperId)
      const matchedCitation = findMatchingCitationObj(rawPaperId, pageNum)
      const resolvedPaperId =
        matchedCitation?.paper_id ||
        (rawPaperId.startsWith('paper_') ? rawPaperId : `paper_${rawPaperId}`)

      const citationPayload = matchedCitation
        ? { ...matchedCitation, page: pageNum }
        : { paper_id: resolvedPaperId, paper_title: rawPaperId, page: pageNum, bbox: null }

      parts.push(
        <button
          key={`${prefixKey}-cit-bare-${rawPaperId}-${pageNum}-${match.index}`}
          type="button"
          onClick={() => onSelectCitation(citationPayload)}
          className="inline-flex items-center mx-0.5 px-1.5 py-0.5 rounded text-[11px] font-mono font-medium bg-[#6366f1]/15 text-[#818cf8] border border-[#6366f1]/30 hover:bg-[#6366f1]/25 hover:text-[#a5b4fc] hover:border-[#6366f1]/60 transition cursor-pointer align-super leading-none"
        >
          [{refNum}, p.{pageNum}]
        </button>
      )
    }

    lastIndex = CITATION_REGEX.lastIndex
  }

  if (lastIndex < textSlice.length) {
    const tail = textSlice.slice(lastIndex)
    parts.push(
      <React.Fragment key={`${prefixKey}-tail-${lastIndex}`}>
        {renderMathSegment(tail, `${prefixKey}-tail-${lastIndex}`)}
      </React.Fragment>
    )
  }

  return parts
}

export default MarkdownBlockRenderer

