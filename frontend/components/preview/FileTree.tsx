'use client'

import { useState } from 'react'
import { cn } from '@/lib/utils'
import {
  ChevronRight,
  ChevronDown,
  File,
  Folder,
  FileCode,
  FileJson,
  Sparkles,
} from 'lucide-react'

interface FileTreeProps {
  files: Record<string, string>
}

interface TreeNode {
  name: string
  path: string
  type: 'file' | 'folder'
  children?: TreeNode[]
  isGenerated?: boolean
}

export function FileTree({ files }: FileTreeProps) {
  const tree = buildTree(files)

  return (
    <div className="h-full overflow-y-auto p-2 bg-[var(--background)]">
      <div className="mb-2 px-2">
        <h3 className="text-[10px] font-medium text-nb-gold uppercase tracking-wider">
          Project Files
        </h3>
      </div>
      <div className="space-y-0.5">
        {tree.map((node) => (
          <TreeNodeComponent key={node.path} node={node} depth={0} />
        ))}
      </div>
    </div>
  )
}

function TreeNodeComponent({ node, depth }: { node: TreeNode; depth: number }) {
  const [isExpanded, setIsExpanded] = useState(true)

  if (node.type === 'folder') {
    return (
      <div>
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className={cn(
            'flex w-full items-center gap-1.5 rounded-lg px-2 py-1 text-sm',
            'text-[var(--foreground)] hover:bg-[var(--surface-2)] transition-colors'
          )}
          style={{ paddingLeft: `${depth * 12 + 8}px` }}
        >
          {isExpanded ? (
            <ChevronDown className="h-3.5 w-3.5 shrink-0 text-[var(--muted)]" />
          ) : (
            <ChevronRight className="h-3.5 w-3.5 shrink-0 text-[var(--muted)]" />
          )}
          <Folder className="h-3.5 w-3.5 shrink-0 text-nb-amber" />
          <span className="truncate text-xs">{node.name}</span>
        </button>
        {isExpanded && node.children && (
          <div>
            {node.children.map((child) => (
              <TreeNodeComponent
                key={child.path}
                node={child}
                depth={depth + 1}
              />
            ))}
          </div>
        )}
      </div>
    )
  }

  const FileIcon = getFileIcon(node.name)
  const fileColor = getFileColor(node.name)

  return (
    <div
      className={cn(
        'flex items-center gap-1.5 rounded-lg px-2 py-1 text-xs',
        'text-[var(--muted)] hover:bg-[var(--surface-2)] hover:text-[var(--foreground)]',
        'cursor-pointer transition-colors'
      )}
      style={{ paddingLeft: `${depth * 12 + 24}px` }}
    >
      <FileIcon className={cn('h-3.5 w-3.5 shrink-0', fileColor)} />
      <span className="truncate">{node.name}</span>
      {node.isGenerated && (
        <Sparkles className="h-3 w-3 shrink-0 text-nb-gold ml-auto" />
      )}
    </div>
  )
}

function buildTree(files: Record<string, string>): TreeNode[] {
  const root: TreeNode[] = []

  // Sort files by path
  const sortedPaths = Object.keys(files).sort()

  for (const path of sortedPaths) {
    const parts = path.split('/').filter(Boolean)
    let current = root

    for (let i = 0; i < parts.length; i++) {
      const part = parts[i]
      const isFile = i === parts.length - 1
      const currentPath = '/' + parts.slice(0, i + 1).join('/')

      let node = current.find((n) => n.name === part)

      if (!node) {
        node = {
          name: part,
          path: currentPath,
          type: isFile ? 'file' : 'folder',
          children: isFile ? undefined : [],
          isGenerated: isFile && isGeneratedFile(part),
        }
        current.push(node)
      }

      if (!isFile && node.children) {
        current = node.children
      }
    }
  }

  return root
}

function getFileIcon(filename: string) {
  const ext = filename.split('.').pop()?.toLowerCase()

  switch (ext) {
    case 'js':
    case 'jsx':
    case 'ts':
    case 'tsx':
      return FileCode
    case 'json':
      return FileJson
    default:
      return File
  }
}

function getFileColor(filename: string): string {
  const ext = filename.split('.').pop()?.toLowerCase()

  switch (ext) {
    case 'js':
    case 'jsx':
      return 'text-nb-gold'
    case 'ts':
    case 'tsx':
      return 'text-nb-navy'
    case 'json':
      return 'text-nb-green'
    case 'css':
    case 'scss':
      return 'text-nb-teal'
    default:
      return 'text-[var(--muted)]'
  }
}

function isGeneratedFile(filename: string): boolean {
  const generatedFiles = ['App.jsx', 'App.js', 'ContractForm.jsx']
  return generatedFiles.includes(filename)
}
