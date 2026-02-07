'use client'

import { useEffect, useRef } from 'react'
import { cn } from '@/lib/utils'
import { User, Bot, AlertCircle } from 'lucide-react'
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
      <div className="flex h-full flex-col items-center justify-center px-4 text-center">
        <Bot className="mb-4 h-12 w-12 text-neutral-600" />
        <h2 className="mb-2 text-lg font-medium text-neutral-300">
          Welcome to Halo Studio
        </h2>
        <p className="text-sm text-neutral-500">
          Describe the DApp you want to build and I'll create it for you on Stellar.
        </p>
        <div className="mt-6 space-y-2 text-left text-sm">
          <p className="text-neutral-500">Try something like:</p>
          <ul className="space-y-1 text-neutral-400">
            <li>• Create a fund transfer app</li>
            <li>• Build a crowdfunding campaign</li>
            <li>• Make an NFT minting page</li>
          </ul>
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

function MessageBubble({ message }: { message: Message }) {
  const isUser = message.role === 'user'
  const isSystem = message.role === 'system'

  return (
    <div
      className={cn(
        'flex gap-3',
        isUser && 'flex-row-reverse'
      )}
    >
      {/* Avatar */}
      <div
        className={cn(
          'flex h-8 w-8 shrink-0 items-center justify-center rounded-full',
          isUser && 'bg-blue-600 text-white',
          !isUser && !isSystem && 'bg-neutral-700 text-neutral-300',
          isSystem && 'bg-red-900/50 text-red-400'
        )}
      >
        {isUser ? (
          <User className="h-4 w-4" />
        ) : isSystem ? (
          <AlertCircle className="h-4 w-4" />
        ) : (
          <Bot className="h-4 w-4" />
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
            'rounded-xl px-3 py-2 text-sm',
            isUser && 'bg-blue-600 text-white',
            !isUser && !isSystem && 'bg-neutral-800 text-neutral-200',
            isSystem && 'bg-red-900/30 text-red-400'
          )}
        >
          {message.content}
        </div>
        <span className="mt-1 text-xs text-neutral-500">
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
