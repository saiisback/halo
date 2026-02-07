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
    <div className="h-full overflow-y-auto p-2 bg-neutral-900">
      <div className="mb-2 px-2">
        <h3 className="text-xs font-medium text-neutral-500 uppercase tracking-wider">
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
            'flex w-full items-center gap-1 rounded-lg px-2 py-1 text-sm',
            'text-neutral-400 hover:bg-neutral-800 hover:text-white'
          )}
          style={{ paddingLeft: `${depth * 12 + 8}px` }}
        >
          {isExpanded ? (
            <ChevronDown className="h-4 w-4 shrink-0" />
          ) : (
            <ChevronRight className="h-4 w-4 shrink-0" />
          )}
          <Folder className="h-4 w-4 shrink-0 text-yellow-500" />
          <span className="truncate">{node.name}</span>
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

  return (
    <div
      className={cn(
        'flex items-center gap-1 rounded-lg px-2 py-1 text-sm',
        'text-neutral-400 hover:bg-neutral-800 hover:text-white',
        'cursor-pointer'
      )}
      style={{ paddingLeft: `${depth * 12 + 24}px` }}
    >
      <FileIcon className="h-4 w-4 shrink-0" />
      <span className="truncate">{node.name}</span>
      {node.isGenerated && (
        <Sparkles className="h-3 w-3 shrink-0 text-blue-500 ml-auto" />
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

function isGeneratedFile(filename: string): boolean {
  // Mark App.jsx and any custom components as AI-generated
  const generatedFiles = ['App.jsx', 'App.js', 'ContractForm.jsx']
  return generatedFiles.includes(filename)
}
