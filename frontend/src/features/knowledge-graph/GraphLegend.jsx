import React from 'react'

/**
 * Bottom-left legend overlay explaining node types, categories, and interactions.
 */
export default function GraphLegend({ layoutDirection = 'TB' }) {
  return (
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
        <span>Research Category</span>
      </div>
      <span className="text-[#a1a1aa]/70 hidden sm:inline">
        · Click any category, paper, or citation edge to inspect details
      </span>
    </div>
  )
}

