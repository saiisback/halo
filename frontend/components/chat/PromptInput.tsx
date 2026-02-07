'use client'

import { useState, useRef, useEffect } from 'react'
import { cn } from '@/lib/utils'
import { Send, Loader2 } from 'lucide-react'

interface PromptInputProps {
  onSubmit: (prompt: string) => void
  disabled?: boolean
  placeholder?: string
}

export function PromptInput({
  onSubmit,
  disabled = false,
  placeholder = 'Type a message...',
}: PromptInputProps) {
  const [value, setValue] = useState('')
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  // Auto-resize textarea
  useEffect(() => {
    const textarea = textareaRef.current
    if (textarea) {
      textarea.style.height = 'auto'
      textarea.style.height = `${Math.min(textarea.scrollHeight, 150)}px`
    }
  }, [value])

  const handleSubmit = () => {
    if (!value.trim() || disabled) return
    onSubmit(value.trim())
    setValue('')
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit()
    }
  }

  return (
    <div className="flex items-end gap-2">
      <textarea
        ref={textareaRef}
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder={placeholder}
        disabled={disabled}
        rows={1}
        className={cn(
          'flex-1 resize-none rounded-2xl border border-[var(--border-color)] bg-[var(--surface-2)] px-4 py-3',
          'text-sm text-[var(--foreground)] placeholder:text-[var(--muted)]',
          'focus:outline-none focus:ring-1 focus:ring-nb-gold/30 focus:border-nb-gold/40',
          'disabled:cursor-not-allowed disabled:opacity-50',
          'transition-all'
        )}
      />
      <button
        onClick={handleSubmit}
        disabled={disabled || !value.trim()}
        style={{ backgroundColor: '#fdda24', borderColor: '#fdda24', color: '#000000' }}
        className={cn(
          'flex h-10 w-10 shrink-0 items-center justify-center rounded-xl',
          'hover:brightness-110 disabled:opacity-50 disabled:cursor-not-allowed',
          'transition-all btn-press'
        )}
      >
        {disabled ? (
          <Loader2 className="h-5 w-5 animate-spin" />
        ) : (
          <Send className="h-5 w-5" />
        )}
      </button>
    </div>
  )
}
