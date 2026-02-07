'use client'

import { useState } from 'react'
import { useHaloStore } from '@/lib/store'
import { SandpackPreview } from './SandpackPreview'
import { FileTree } from './FileTree'
import { BuildStatusExpanded } from './BuildStatus'
import { cn } from '@/lib/utils'
import { Code, Eye, Terminal, FolderTree, Sparkles } from 'lucide-react'

type Tab = 'preview' | 'code' | 'console' | 'status'

export function PreviewPanel() {
  const [activeTab, setActiveTab] = useState<Tab>('preview')
  const [showFileTree, setShowFileTree] = useState(false)
  const { generatedFiles, buildStatus, contractId, walletAddress } = useHaloStore()

  const hasFiles = Object.keys(generatedFiles).length > 0
  const isBuilding = buildStatus !== 'idle' && buildStatus !== 'complete' && buildStatus !== 'error'

  return (
    <div className="flex flex-1 flex-col rounded-2xl border border-neutral-800 bg-neutral-900 overflow-hidden">
      {/* Tab Bar */}
      <div className="flex items-center justify-between border-b border-neutral-800 px-4">
        <div className="flex items-center gap-1">
          <TabButton
            active={activeTab === 'preview'}
            onClick={() => setActiveTab('preview')}
            icon={<Eye className="h-4 w-4" />}
            label="Preview"
          />
          <TabButton
            active={activeTab === 'code'}
            onClick={() => setActiveTab('code')}
            icon={<Code className="h-4 w-4" />}
            label="Code"
          />
          <TabButton
            active={activeTab === 'console'}
            onClick={() => setActiveTab('console')}
            icon={<Terminal className="h-4 w-4" />}
            label="Console"
          />
          {isBuilding && (
            <TabButton
              active={activeTab === 'status'}
              onClick={() => setActiveTab('status')}
              icon={<Sparkles className="h-4 w-4" />}
              label="Building..."
              highlight
            />
          )}
        </div>

        {/* File Tree Toggle */}
        <button
          onClick={() => setShowFileTree(!showFileTree)}
          className={cn(
            'flex items-center gap-2 rounded-md px-3 py-1.5 text-sm transition-colors',
            showFileTree
              ? 'bg-neutral-800 text-white'
              : 'text-neutral-400 hover:bg-neutral-800 hover:text-white'
          )}
        >
          <FolderTree className="h-4 w-4" />
          <span className="hidden sm:inline">Files</span>
        </button>
      </div>

      {/* Content Area */}
      <div className="flex flex-1 overflow-hidden">
        {/* File Tree (conditional) */}
        {showFileTree && hasFiles && (
          <div className="w-56 border-r border-neutral-800">
            <FileTree files={generatedFiles} />
          </div>
        )}

        {/* Main Content */}
        <div className="flex-1 overflow-hidden">
          {activeTab === 'preview' && (
            hasFiles ? (
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
            hasFiles ? (
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
            <SandpackPreview
              files={generatedFiles}
              contractId={contractId}
              walletAddress={walletAddress}
              showConsole
            />
          )}
          {activeTab === 'status' && <BuildStatusExpanded />}
        </div>
      </div>
    </div>
  )
}

function TabButton({
  active,
  onClick,
  icon,
  label,
  highlight,
}: {
  active: boolean
  onClick: () => void
  icon: React.ReactNode
  label: string
  highlight?: boolean
}) {
  return (
    <button
      onClick={onClick}
      className={cn(
        'flex items-center gap-2 border-b-2 px-4 py-3 text-sm transition-colors',
        active
          ? 'border-blue-500 text-white'
          : 'border-transparent text-neutral-400 hover:text-white',
        highlight && !active && 'text-yellow-500 animate-pulse'
      )}
    >
      {icon}
      {label}
    </button>
  )
}

function EmptyState() {
  const { loadTestFiles } = useHaloStore()

  return (
    <div className="flex h-full flex-col items-center justify-center text-center bg-neutral-900">
      <div className="rounded-full bg-neutral-800 p-6 mb-4">
        <Sparkles className="h-10 w-10 text-neutral-500" />
      </div>
      <h3 className="text-lg font-medium text-white mb-2">No Preview Yet</h3>
      <p className="text-sm text-neutral-400 max-w-md mb-4">
        Describe your DApp in the chat and I'll generate a live preview here.
        Your app will be deployed to Stellar Testnet.
      </p>
      <button
        onClick={loadTestFiles}
        className="text-xs text-neutral-500 hover:text-white underline"
      >
        Test Sandpack Preview
      </button>
    </div>
  )
}
