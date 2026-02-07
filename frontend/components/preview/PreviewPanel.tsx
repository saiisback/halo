'use client'

import { useState } from 'react'
import { useHaloStore } from '@/lib/store'
import { SandpackPreview } from './SandpackPreview'
import { FileTree } from './FileTree'
import { BuildStatusExpanded } from './BuildStatus'
import { BuildAnimation } from './BuildAnimation'
import { cn } from '@/lib/utils'
import Image from 'next/image'
import {
  Code,
  Eye,
  Terminal,
  FolderTree,
  Loader2,
  ChevronLeft,
  ChevronRight,
  RotateCw,
  Monitor,
  Tablet,
  Smartphone,
  ExternalLink,
  MoreHorizontal,
} from 'lucide-react'

type Tab = 'preview' | 'code' | 'console' | 'status'

export function PreviewPanel() {
  const [activeTab, setActiveTab] = useState<Tab>('preview')
  const [showFileTree, setShowFileTree] = useState(false)
  const { generatedFiles, buildStatus, contractId, walletAddress } = useHaloStore()

  const hasFiles = Object.keys(generatedFiles).length > 0
  const isBuilding = buildStatus !== 'idle' && buildStatus !== 'complete' && buildStatus !== 'error'

  const displayUrl = contractId
    ? `stellar://testnet/${contractId}`
    : 'localhost:3000'

  return (
    <div className="flex flex-1 flex-col bg-[var(--background)] overflow-hidden">
      {/* Browser-like Toolbar */}
      <div className="flex h-11 shrink-0 items-center gap-1.5 border-b border-[var(--border-color)] px-2 bg-[var(--surface)]">
        {/* Left: View Toggle Buttons */}
        <div className="flex items-center gap-0.5 border-r border-[var(--border-color)] pr-2 mr-1">
          <ToolbarButton
            active={activeTab === 'preview'}
            onClick={() => setActiveTab('preview')}
            icon={<Eye className="h-4 w-4" />}
            title="Preview"
          />
          <ToolbarButton
            active={activeTab === 'code'}
            onClick={() => setActiveTab('code')}
            icon={<Code className="h-4 w-4" />}
            title="Code"
          />
          <ToolbarButton
            active={activeTab === 'console'}
            onClick={() => setActiveTab('console')}
            icon={<Terminal className="h-4 w-4" />}
            title="Console"
          />
          {isBuilding && (
            <ToolbarButton
              active={activeTab === 'status'}
              onClick={() => setActiveTab('status')}
              icon={<Loader2 className="h-4 w-4 animate-spin" />}
              title="Building"
              highlight
            />
          )}
        </div>

        {/* Navigation Buttons */}
        <div className="flex items-center gap-0.5 border-r border-[var(--border-color)] pr-2 mr-1">
          <ToolbarButton
            icon={<ChevronLeft className="h-4 w-4" />}
            title="Back"
            disabled
          />
          <ToolbarButton
            icon={<ChevronRight className="h-4 w-4" />}
            title="Forward"
            disabled
          />
          <ToolbarButton
            icon={<RotateCw className="h-3.5 w-3.5" />}
            title="Reload"
          />
        </div>

        {/* URL Bar */}
        <div className="flex flex-1 items-center min-w-0">
          <div className="flex h-7 flex-1 items-center rounded-lg border border-[var(--border-color)] bg-[var(--background)] px-3 min-w-0">
            <span className="truncate text-xs text-[var(--muted)] font-mono">
              {displayUrl}
            </span>
          </div>
        </div>

        {/* Right: Responsive Toggles + Actions */}
        <div className="flex items-center gap-0.5 border-l border-[var(--border-color)] pl-2 ml-1">
          <ToolbarButton
            icon={<Monitor className="h-4 w-4" />}
            title="Desktop"
          />
          <ToolbarButton
            icon={<Tablet className="h-4 w-4" />}
            title="Tablet"
          />
          <ToolbarButton
            icon={<Smartphone className="h-4 w-4" />}
            title="Mobile"
          />
        </div>

        <div className="flex items-center gap-0.5 border-l border-[var(--border-color)] pl-2 ml-1">
          <ToolbarButton
            active={showFileTree}
            onClick={() => setShowFileTree(!showFileTree)}
            icon={<FolderTree className="h-4 w-4" />}
            title="Files"
          />
          <ToolbarButton
            icon={<ExternalLink className="h-3.5 w-3.5" />}
            title="Open in new tab"
          />
          <ToolbarButton
            icon={<MoreHorizontal className="h-4 w-4" />}
            title="More"
          />
        </div>
      </div>

      {/* Content Area */}
      <div className="flex flex-1 overflow-hidden">
        {/* File Tree (conditional) */}
        {showFileTree && hasFiles && (
          <div className="w-56 border-r border-[var(--border-color)] bg-[var(--surface)]">
            <FileTree files={generatedFiles} />
          </div>
        )}

        {/* Main Content */}
        <div className="flex-1 overflow-hidden">
          {activeTab === 'preview' && (
            isBuilding && !hasFiles ? (
              <BuildAnimation />
            ) : hasFiles ? (
              <SandpackPreview
                files={generatedFiles}
                contractId={contractId}
                walletAddress={walletAddress}
              />
            ) : (
              <EmptyState />
            )
          )}
          {activeTab === 'code' && (
            isBuilding && !hasFiles ? (
              <BuildAnimation />
            ) : hasFiles ? (
              <SandpackPreview
                files={generatedFiles}
                contractId={contractId}
                walletAddress={walletAddress}
                showCode
              />
            ) : (
              <EmptyState />
            )
          )}
          {activeTab === 'console' && (
            isBuilding && !hasFiles ? (
              <BuildAnimation />
            ) : (
              <SandpackPreview
                files={generatedFiles}
                contractId={contractId}
                walletAddress={walletAddress}
                showConsole
              />
            )
          )}
          {activeTab === 'status' && <BuildStatusExpanded />}
        </div>
      </div>
    </div>
  )
}

function ToolbarButton({
  active,
  onClick,
  icon,
  title,
  highlight,
  disabled,
}: {
  active?: boolean
  onClick?: () => void
  icon: React.ReactNode
  title: string
  highlight?: boolean
  disabled?: boolean
  activeColor?: string
}) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      title={title}
      className={cn(
        'flex h-7 w-7 items-center justify-center rounded-lg text-sm transition-all',
        active
          ? 'bg-nb-gold/10 text-nb-gold'
          : 'text-[var(--muted)] hover:bg-[var(--surface-2)] hover:text-[var(--foreground)]',
        highlight && !active && 'text-nb-gold animate-gentle-pulse',
        disabled && 'opacity-30 cursor-default hover:bg-transparent hover:text-[var(--muted)]'
      )}
    >
      {icon}
    </button>
  )
}

function EmptyState() {
  return (
    <div className="flex h-full flex-col items-center justify-center text-center bg-[var(--surface)] bg-mesh-subtle">
      <div className="rounded-2xl border border-nb-gold/20 p-6 mb-5 bg-nb-gold/5 glow-gold">
        <Image src="/logo.svg" alt="Halo" width={40} height={40} className="opacity-90" />
      </div>
      <h3 className="font-serif text-2xl italic text-nb-gold mb-2">No Preview Yet</h3>
      <p className="text-sm text-[var(--muted)] max-w-md mb-6 leading-relaxed">
        Describe your DApp in the chat and I&apos;ll generate a live preview here.
        Your app will be deployed to Stellar Testnet.
      </p>
    </div>
  )
}
