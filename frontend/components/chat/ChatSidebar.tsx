'use client'

import { MessageList } from './MessageList'
import { PromptInput } from './PromptInput'
import { WalletButton } from './WalletButton'
import { useHaloStore } from '@/lib/store'
import { Sparkles } from 'lucide-react'

export function ChatSidebar() {
  const { messages, isBuilding, sendPrompt } = useHaloStore()

  return (
    <div className="flex w-[380px] flex-col rounded-2xl border border-neutral-800 bg-neutral-900 overflow-hidden">
      {/* Header */}
      <div className="flex items-center gap-2 border-b border-neutral-800 px-4 py-3">
        <Sparkles className="h-5 w-5 text-blue-500" />
        <h1 className="text-lg font-semibold text-white">Halo Studio</h1>
        <div className="ml-auto">
          <WalletButton />
        </div>
      </div>

      {/* Messages with inline Chain of Thoughts */}
      <div className="flex-1 overflow-hidden">
        <MessageList messages={messages} />
      </div>

      {/* Prompt Input */}
      <div className="border-t border-neutral-800 p-4">
        <PromptInput
          onSubmit={sendPrompt}
          disabled={isBuilding}
          placeholder="Describe your DApp..."
        />
      </div>
    </div>
  )
}
