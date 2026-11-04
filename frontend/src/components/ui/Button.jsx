import React from 'react'

/**
 * Atomic reusable Button component with variant styles.
 */
export default function Button({
  children,
  onClick,
  disabled = false,
  variant = 'primary', // 'primary' | 'secondary' | 'ghost' | 'danger'
  size = 'md',        // 'sm' | 'md' | 'lg'
  className = '',
  type = 'button',
  ...props
}) {
  const baseStyles = 'inline-flex items-center justify-center font-medium transition cursor-pointer select-none rounded-lg'

  const sizeStyles = {
    sm: 'px-2.5 py-1 text-xs gap-1.5',
    md: 'px-3.5 py-1.5 text-xs gap-2',
    lg: 'px-4 py-2 text-sm gap-2',
  }[size] || 'px-3.5 py-1.5 text-xs gap-2'

  const variantStyles = {
    primary: 'bg-[#6366f1] hover:bg-[#4f46e5] text-white disabled:bg-[#27272a] disabled:text-[#71717a] disabled:cursor-not-allowed',
    secondary: 'bg-[#18181b] hover:bg-[#27272a] border border-[#27272a] text-[#f4f4f5] disabled:opacity-50 disabled:cursor-not-allowed',
    ghost: 'hover:bg-[#27272a] text-[#a1a1aa] hover:text-[#f4f4f5] disabled:opacity-50 disabled:cursor-not-allowed',
    danger: 'bg-rose-600 hover:bg-rose-500 text-white disabled:opacity-50 disabled:cursor-not-allowed',
  }[variant] || 'bg-[#6366f1] hover:bg-[#4f46e5] text-white'

  return (
    <button
      type={type}
      onClick={onClick}
      disabled={disabled}
      className={`${baseStyles} ${sizeStyles} ${variantStyles} ${className}`}
      {...props}
    >
      {children}
    </button>
  )
}

