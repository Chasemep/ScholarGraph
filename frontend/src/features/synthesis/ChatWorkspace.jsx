import React, { useState } from 'react'
import { BookOpen } from 'lucide-react'
import MessageItem from './MessageItem'
import QueryInput from './QueryInput'

export default function ChatWorkspace({
  messages = [],
  onSendQuery,
  isLoading = false,
  onSelectCitation,
  activeCitation,
  selectedPaperIds = [],
}) {
  const [input, setInput] = useState('')

  const handleSubmit = (e) => {
    e.preventDefault()
    const trimmed = input.trim()
    if (!trimmed || isLoading) return
    onSendQuery(trimmed)
    setInput('')
  }

  return (
    <div className="flex flex-col h-full bg-[#09090b] border-r border-[#27272a]">
      {/* Conversation Stream */}
      <div className="flex-1 overflow-y-auto px-6 py-5 space-y-5">
        {messages.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-center px-4 py-12">
            <div className="w-10 h-10 rounded-xl bg-[#18181b] border border-[#27272a] flex items-center justify-center mb-3">
              <BookOpen className="w-4 h-4 text-[#6366f1]" />
            </div>
            <h2 className="text-sm font-semibold text-[#f4f4f5] tracking-tight">
              Ask a question about your papers
            </h2>
            <p className="text-xs text-[#a1a1aa] leading-relaxed max-w-sm mt-1.5">
              Get answers backed by direct citations from your uploaded PDFs. Click any citation badge to jump to that page in the PDF reader.
            </p>
          </div>
        ) : (
          messages.map((msg) => (
            <MessageItem
              key={msg.id}
              message={msg}
              activeCitation={activeCitation}
              onSelectCitation={onSelectCitation}
              onSendQuery={onSendQuery}
            />
          ))
        )}

        {isLoading && (
          <div className="py-4 space-y-2.5 animate-pulse">
            <div className="h-3 w-36 bg-[#18181b] rounded" />
            <div className="h-3 w-full bg-[#18181b] rounded" />
            <div className="h-3 w-5/6 bg-[#18181b] rounded" />
          </div>
        )}
      </div>

      {/* Prominent Prompt Composer */}
      <QueryInput
        input={input}
        setInput={setInput}
        onSubmit={handleSubmit}
        isLoading={isLoading}
        selectedPaperIds={selectedPaperIds}
      />
    </div>
  )
}

