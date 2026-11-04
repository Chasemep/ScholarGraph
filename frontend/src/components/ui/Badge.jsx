import React from 'react'

/**
 * Atomic Badge component for status tags, entity types, and paper citations.
 */
export default function Badge({
  children,
  variant = 'default', // 'default' | 'primary' | 'success' | 'warning' | 'danger'
  size = 'sm',        // 'sm' | 'md'
  className = '',
  ...props
}) {
  const sizeStyles = size === 'sm' ? 'px-2 py-0.5 text-[10px]' : 'px-2.5 py-1 text-xs'

  const variantStyles = {
    default: 'bg-[#27272a]/70 text-[#d4d4d8] border border-[#3f3f46]/50',
    primary: 'bg-[#6366f1]/15 text-[#a5b4fc] border border-[#6366f1]/30',
    success: 'bg-emerald-500/15 text-emerald-300 border border-emerald-500/30',
    warning: 'bg-amber-500/15 text-amber-300 border border-amber-500/30',
    danger: 'bg-rose-500/15 text-rose-300 border border-rose-500/30',
  }[variant] || 'bg-[#27272a]/70 text-[#d4d4d8] border border-[#3f3f46]/50'

  return (
    <span
      className={`inline-flex items-center gap-1 font-medium rounded-md uppercase tracking-wider ${sizeStyles} ${variantStyles} ${className}`}
      {...props}
    >
      {children}
    </span>
  )
}

