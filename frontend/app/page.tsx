'use client'

import { ChatSidebar } from '@/components/chat/ChatSidebar'
import { PreviewPanel } from '@/components/preview/PreviewPanel'

export default function Home() {
  return (
    <main className="flex h-screen p-4 gap-4 bg-neutral-950">
      {/* Chat Panel */}
      <ChatSidebar />

      {/* Preview Panel */}
      <PreviewPanel />
    </main>
  )
}
