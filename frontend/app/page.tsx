'use client'

import { useEffect } from 'react'
import { Navbar } from '@/components/layout/Navbar'
import { ChatSidebar } from '@/components/chat/ChatSidebar'
import { PreviewPanel } from '@/components/preview/PreviewPanel'
import { useHaloStore } from '@/lib/store'

function ThemeSync() {
  const theme = useHaloStore((s) => s.theme)

  useEffect(() => {
    const root = document.documentElement
    if (theme === 'dark') {
      root.classList.add('dark')
    } else {
      root.classList.remove('dark')
    }
  }, [theme])

  return null
}

export default function Home() {
  return (
    <main className="flex h-screen flex-col bg-[var(--background)]">
      <ThemeSync />

      {/* Top Navbar */}
      <Navbar />

      {/* Chat + Preview */}
      <div className="flex flex-1 min-h-0">
        <ChatSidebar />
        <PreviewPanel />
      </div>
    </main>
  )
}
