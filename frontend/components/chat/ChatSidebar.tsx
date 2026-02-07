'use client'

import { MessageSquare, Puzzle } from 'lucide-react'
import { MessageList } from './MessageList'
import { PromptInput } from './PromptInput'
import { ProtocolsPanel } from './ProtocolsPanel'
import { useHaloStore } from '@/lib/store'

export function ChatSidebar() {
  const { messages, isBuilding, sendPrompt, sidebarTab, setSidebarTab } = useHaloStore()

  return (
    <div className="flex w-[380px] shrink-0 flex-col border-r border-[var(--border-color)] bg-[var(--background)] overflow-hidden">
      {/* Tab switcher */}
      <div className="flex border-b border-[var(--border-color)] bg-[var(--surface)]/30">
        <button
          onClick={() => setSidebarTab('chat')}
          className={`flex items-center justify-center gap-1.5 flex-1 py-2.5 text-xs font-medium transition-all relative
            ${
              sidebarTab === 'chat'
                ? 'text-[var(--foreground)]'
                : 'text-[var(--muted)] hover:text-[var(--foreground)]'
            }`}
        >
          <MessageSquare className="w-3.5 h-3.5" />
          Chat
          {sidebarTab === 'chat' && (
            <span className="absolute bottom-0 left-1/4 right-1/4 h-[2px] bg-[var(--nb-gold)] rounded-full" />
          )}
        </button>
        <button
          onClick={() => setSidebarTab('protocols')}
          className={`flex items-center justify-center gap-1.5 flex-1 py-2.5 text-xs font-medium transition-all relative
            ${
              sidebarTab === 'protocols'
                ? 'text-[var(--foreground)]'
                : 'text-[var(--muted)] hover:text-[var(--foreground)]'
            }`}
        >
          <Puzzle className="w-3.5 h-3.5" />
          Protocols
          {sidebarTab === 'protocols' && (
            <span className="absolute bottom-0 left-1/4 right-1/4 h-[2px] bg-[var(--nb-gold)] rounded-full" />
          )}
        </button>
      </div>

      {/* Tab content */}
      {sidebarTab === 'chat' ? (
        <>
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
        </>
      ) : (
        <ProtocolsPanel />
      )}
    </div>
  )
}
