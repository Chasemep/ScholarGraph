import React from 'react'
import { Send } from 'lucide-react'
import Button from '../../components/ui/Button'

export default function QueryInput({
  input,
  setInput,
  onSubmit,
  isLoading,
  selectedPaperIds = [],
}) {
  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      onSubmit(e)
    }
  }

  return (
    <form onSubmit={onSubmit} className="p-4 border-t border-[#27272a] bg-[#09090b]">
      <div className="rounded-2xl bg-[#18181b] border border-[#3f3f46]/80 focus-within:border-[#6366f1] focus-within:ring-2 focus-within:ring-[#6366f1]/25 shadow-[0_8px_30px_rgb(0,0,0,0.45)] transition p-3.5">
        <textarea
          rows={2}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask a question about your papers..."
          disabled={isLoading}
          className="w-full bg-transparent resize-none text-sm text-[#f4f4f5] placeholder-[#a1a1aa] leading-relaxed focus:outline-none min-h-[52px]"
        />
        <div className="flex items-center justify-between gap-2 pt-2 mt-1 border-t border-[#27272a]/80">
          <div className="text-[11px] text-[#a1a1aa] flex items-center gap-2">
            {selectedPaperIds && selectedPaperIds.length > 0 ? (
              <span className="px-2 py-0.5 rounded-md bg-[#6366f1]/15 text-[#818cf8] border border-[#6366f1]/30 font-medium">
                Searching {selectedPaperIds.length} selected paper(s)
              </span>
            ) : (
              <span>Press Enter to ask · Shift+Enter for new line</span>
            )}
          </div>
          <Button
            type="submit"
            disabled={isLoading || !input.trim()}
            variant="primary"
            size="sm"
            className="flex items-center gap-1.5"
          >
            <Send className="w-3.5 h-3.5" />
            <span>Ask</span>
          </Button>
        </div>
      </div>
    </form>
  )
}

