'use client'

import { useEffect, useRef } from 'react'
import { cn } from '@/lib/utils'
import { User, Bot, AlertCircle } from 'lucide-react'
import Image from 'next/image'
import type { Message } from '@/lib/store'
import { useHaloStore } from '@/lib/store'
import { ThinkingChain } from './ThinkingChain'

interface MessageListProps {
  messages: Message[]
}

export function MessageList({ messages }: MessageListProps) {
  const scrollRef = useRef<HTMLDivElement>(null)
  const { buildStatus } = useHaloStore()

  // Auto-scroll to bottom on new messages or build status changes
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [messages, buildStatus])

  if (messages.length === 0) {
    return (
      <div className="flex h-full flex-col items-center justify-center px-6 text-center">
        <div className="rounded-2xl border border-nb-gold/20 p-5 mb-5 bg-nb-gold/5 glow-gold">
          <Image src="/logo.svg" alt="Halo" width={40} height={40} className="opacity-90" />
        </div>
        <h2 className="mb-2 font-serif text-2xl italic text-nb-gold">
          Welcome to Halo Studio
        </h2>
        <p className="text-sm text-[var(--muted)] max-w-[260px] leading-relaxed">
          Describe the DApp you want to build and I&apos;ll create it for you on Stellar.
        </p>
        <div className="mt-8 space-y-2.5 text-left text-sm w-full max-w-[280px]">
          <p className="text-[var(--muted)] text-xs font-medium uppercase tracking-wider mb-3">Try something like:</p>
          <SuggestionItem color="gold">Create a fund transfer app</SuggestionItem>
          <SuggestionItem color="gold">Build a crowdfunding campaign</SuggestionItem>
          <SuggestionItem color="gold">Make an NFT minting page</SuggestionItem>
        </div>
      </div>
    )
  }

  // Show thinking chain when building (including errors to show which step failed)
  const showThinking = buildStatus !== 'idle' && buildStatus !== 'complete'

  return (
    <div ref={scrollRef} className="h-full overflow-y-auto p-4">
      <div className="space-y-4">
        {messages.map((message) => (
          <MessageBubble key={message.id} message={message} />
        ))}
        {/* Chain of Thoughts - shows inline while building */}
        {showThinking && <ThinkingChain />}
      </div>
    </div>
  )
}

function SuggestionItem({ children, color }: { children: React.ReactNode; color: string }) {
  return (
    <div className="group rounded-xl border border-nb-gold/15 bg-[var(--surface)] px-4 py-2.5 text-[var(--foreground)] text-sm cursor-pointer transition-all hover:border-nb-gold/30 hover:bg-nb-gold/5 animate-fade-in-up">
      <span className="text-nb-gold/60 mr-2 group-hover:text-nb-gold transition-colors">&#9679;</span>
      {children}
    </div>
  )
}

function MessageBubble({ message }: { message: Message }) {
  const isUser = message.role === 'user'
  const isSystem = message.role === 'system'

  return (
    <div
      className={cn(
        'flex gap-3 animate-fade-in-up',
        isUser && 'flex-row-reverse'
      )}
    >
      {/* Avatar */}
      <div
        className={cn(
          'flex h-7 w-7 shrink-0 items-center justify-center rounded-full',
          isUser && 'bg-[var(--surface-2)] text-[var(--foreground)]',
          !isUser && !isSystem && 'bg-nb-gold/10 text-nb-gold',
          isSystem && 'bg-nb-red/10 text-nb-red'
        )}
      >
        {isUser ? (
          <User className="h-3.5 w-3.5" />
        ) : isSystem ? (
          <AlertCircle className="h-3.5 w-3.5" />
        ) : (
          <Bot className="h-3.5 w-3.5" />
        )}
      </div>

      {/* Message Content */}
      <div
        className={cn(
          'flex max-w-[85%] flex-col',
          isUser && 'items-end'
        )}
      >
        <div
          className={cn(
            'rounded-2xl px-4 py-2.5 text-sm leading-relaxed',
            isUser && 'bg-nb-gold text-black rounded-br-md',
            !isUser && !isSystem && 'bg-[var(--surface-2)] text-[var(--foreground)] rounded-bl-md',
            isSystem && 'bg-nb-red/10 text-nb-red border border-nb-red/20 rounded-bl-md'
          )}
        >
          {message.content}
        </div>
        <span className="mt-1.5 text-[10px] text-[var(--muted)]">
          {formatTime(message.timestamp)}
        </span>
      </div>
    </div>
  )
}

function formatTime(date: Date): string {
  return date.toLocaleTimeString([], {
    hour: '2-digit',
    minute: '2-digit',
  })
}
