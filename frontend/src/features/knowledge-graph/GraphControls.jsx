import React from 'react'
import {
  ZoomIn,
  ZoomOut,
  Maximize2,
  RotateCcw,
  ArrowDownUp,
  ArrowLeftRight,
  Sparkles,
} from 'lucide-react'

/**
 * Top-right floating controls toolbar for the Knowledge Graph canvas.
 */
export default function GraphControls({
  layoutDirection = 'TB',
  onToggleDirection,
  onZoomIn,
  onZoomOut,
  onFit,
  onResetLayout,
  hasActiveHighlight = false,
  onResetHighlight,
  stats = { papers: 0, groups: 0 },
}) {
  return (
    <div className="absolute top-4 right-4 z-20 flex items-center gap-2">
      {/* Active Filter Pill */}
      {hasActiveHighlight && (
        <button
          type="button"
          onClick={onResetHighlight}
          className="px-2.5 py-1.5 rounded-lg bg-[#6366f1]/20 hover:bg-[#6366f1]/30 border border-[#6366f1]/50 text-xs font-medium text-[#a5b4fc] flex items-center gap-1.5 transition shadow-lg cursor-pointer"
        >
          <Sparkles className="w-3.5 h-3.5 text-[#818cf8]" />
          Reset Filter
        </button>
      )}

      {/* Stats Indicator */}
      <div className="hidden sm:flex items-center gap-2 px-3 py-1.5 rounded-lg bg-[#18181b]/90 border border-[#27272a] text-[11px] font-mono text-[#a1a1aa] shadow-lg backdrop-blur-sm">
        <span><strong className="text-[#f4f4f5]">{stats.papers}</strong> papers</span>
        <span>·</span>
        <span><strong className="text-[#f4f4f5]">{stats.groups}</strong> clusters</span>
      </div>

      {/* Control Buttons Group */}
      <div className="flex items-center rounded-lg bg-[#18181b]/95 border border-[#27272a] shadow-xl overflow-hidden backdrop-blur-sm divide-x divide-[#27272a]">
        <button
          type="button"
          title={`Switch orientation (Current: ${layoutDirection === 'TB' ? 'Vertical Timeline' : 'Horizontal Timeline'})`}
          onClick={onToggleDirection}
          className="p-2 hover:bg-[#27272a] text-[#a1a1aa] hover:text-[#f4f4f5] transition cursor-pointer flex items-center gap-1 text-xs"
        >
          {layoutDirection === 'TB' ? (
            <ArrowDownUp className="w-3.5 h-3.5 text-[#818cf8]" />
          ) : (
            <ArrowLeftRight className="w-3.5 h-3.5 text-[#818cf8]" />
          )}
        </button>
        <button
          type="button"
          title="Zoom In"
          onClick={onZoomIn}
          className="p-2 hover:bg-[#27272a] text-[#a1a1aa] hover:text-[#f4f4f5] transition cursor-pointer"
        >
          <ZoomIn className="w-3.5 h-3.5" />
        </button>
        <button
          type="button"
          title="Zoom Out"
          onClick={onZoomOut}
          className="p-2 hover:bg-[#27272a] text-[#a1a1aa] hover:text-[#f4f4f5] transition cursor-pointer"
        >
          <ZoomOut className="w-3.5 h-3.5" />
        </button>
        <button
          type="button"
          title="Fit & Center Canvas"
          onClick={onFit}
          className="p-2 hover:bg-[#27272a] text-[#a1a1aa] hover:text-[#f4f4f5] transition cursor-pointer"
        >
          <Maximize2 className="w-3.5 h-3.5" />
        </button>
        <button
          type="button"
          title="Reset Layout"
          onClick={onResetLayout}
          className="p-2 hover:bg-[#27272a] text-[#a1a1aa] hover:text-[#f4f4f5] transition cursor-pointer"
        >
          <RotateCcw className="w-3.5 h-3.5" />
        </button>
      </div>
    </div>
  )
}

