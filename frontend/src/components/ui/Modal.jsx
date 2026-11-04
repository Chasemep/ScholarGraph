import React, { useEffect } from 'react'
import { X } from 'lucide-react'

/**
 * Atomic Modal container with backdrop blur and escape key listener.
 */
export default function Modal({
  isOpen,
  onClose,
  title,
  icon: Icon,
  children,
  maxWidth = 'max-w-xl',
  className = '',
}) {
  useEffect(() => {
    if (!isOpen) return
    const handleKeyDown = (e) => {
      if (e.key === 'Escape') onClose?.()
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [isOpen, onClose])

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
      <div className={`w-full ${maxWidth} rounded-xl bg-[#18181b] border border-[#27272a] shadow-2xl overflow-hidden flex flex-col ${className}`}>
        {/* Header */}
        <div className="px-5 py-3.5 border-b border-[#27272a] bg-[#09090b]/50 flex items-center justify-between">
          <div className="flex items-center gap-2">
            {Icon && <Icon className="w-4 h-4 text-[#6366f1]" />}
            <h3 className="text-sm font-semibold text-[#f4f4f5]">{title}</h3>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="text-[#a1a1aa] hover:text-[#f4f4f5] cursor-pointer p-1 rounded hover:bg-[#27272a] transition"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Body */}
        {children}
      </div>
    </div>
  )
}

