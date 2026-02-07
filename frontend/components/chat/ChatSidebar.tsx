'use client'

import { MessageList } from './MessageList'
import { PromptInput } from './PromptInput'
import { useHaloStore } from '@/lib/store'

export function ChatSidebar() {
  const { messages, isBuilding, sendPrompt } = useHaloStore()

  return (
    <div className="flex w-[380px] shrink-0 flex-col border-r border-[var(--border-color)] bg-[var(--background)] overflow-hidden">
      {/* Messages with inline Chain of Thoughts */}
      <div className="flex-1 overflow-hidden">
        <MessageList messages={messages} />
      </div>

      {/* Prompt Input */}
      <div className="border-t border-[var(--border-color)] p-4 bg-[var(--surface)]/30">
        <PromptInput
          onSubmit={sendPrompt}
          disabled={isBuilding}
          placeholder="Ask a follow-up..."
        />
      </div>
    </div>
  )
}
