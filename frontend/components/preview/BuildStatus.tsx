'use client'

import { useHaloStore, type BuildStep } from '@/lib/store'
import { cn } from '@/lib/utils'
import {
  Brain,
  BookOpen,
  Code,
  Hammer,
  Rocket,
  Layout,
  Check,
  AlertCircle,
  Loader2,
} from 'lucide-react'

const STEPS: { id: BuildStep; label: string; icon: typeof Brain }[] = [
  { id: 'analyzing', label: 'Analyzing', icon: Brain },
  { id: 'retrieving_docs', label: 'Fetching Docs', icon: BookOpen },
  { id: 'generating_rust', label: 'Writing Contract', icon: Code },
  { id: 'compiling', label: 'Compiling', icon: Hammer },
  { id: 'deploying', label: 'Deploying', icon: Rocket },
  { id: 'generating_react', label: 'Building UI', icon: Layout },
]

export function BuildStatus() {
  const { buildStatus, buildLogs, error } = useHaloStore()

  const currentStepIndex = STEPS.findIndex((s) => s.id === buildStatus)

  return (
    <div className="p-4">
      {/* Step indicators */}
      <div className="flex items-center justify-between">
        {STEPS.map((step, index) => {
          const isActive = step.id === buildStatus
          const isComplete =
            buildStatus === 'complete' || index < currentStepIndex
          const isError = buildStatus === 'error' && index === currentStepIndex

          const Icon = step.icon

          return (
            <div key={step.id} className="flex flex-col items-center">
              <div
                className={cn(
                  'flex h-8 w-8 items-center justify-center rounded-full transition-colors',
                  isComplete && 'bg-green-500/20 text-green-500',
                  isActive && !isError && 'bg-blue-500/20 text-blue-500',
                  isError && 'bg-red-500/20 text-red-500',
                  !isActive && !isComplete && !isError && 'bg-neutral-800 text-neutral-500'
                )}
              >
                {isComplete ? (
                  <Check className="h-4 w-4" />
                ) : isActive && !isError ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : isError ? (
                  <AlertCircle className="h-4 w-4" />
                ) : (
                  <Icon className="h-4 w-4" />
                )}
              </div>
              <span
                className={cn(
                  'mt-1 text-[10px]',
                  isActive && 'text-blue-500 font-medium',
                  !isActive && 'text-neutral-500'
                )}
              >
                {step.label}
              </span>
            </div>
          )
        })}
      </div>

      {/* Latest log */}
      {buildLogs.length > 0 && (
        <div className="mt-3 rounded-lg bg-neutral-800 p-2">
          <p className="text-xs text-neutral-400 font-mono truncate">
            {buildLogs[buildLogs.length - 1]}
          </p>
        </div>
      )}

      {/* Error message */}
      {error && (
        <div className="mt-3 rounded-lg bg-red-900/30 p-2">
          <p className="text-xs text-red-400">{error}</p>
        </div>
      )}
    </div>
  )
}

export function BuildStatusExpanded() {
  const { buildStatus, buildLogs, contractId, error } = useHaloStore()

  return (
    <div className="flex h-full flex-col bg-neutral-900">
      {/* Header */}
      <div className="border-b border-neutral-800 px-4 py-2">
        <h3 className="text-sm font-medium text-white">Build Progress</h3>
      </div>

      {/* Steps */}
      <div className="border-b border-neutral-800 p-4">
        <div className="space-y-3">
          {STEPS.map((step, index) => {
            const currentIndex = STEPS.findIndex((s) => s.id === buildStatus)
            const isActive = step.id === buildStatus
            const isComplete =
              buildStatus === 'complete' || index < currentIndex
            const Icon = step.icon

            return (
              <div key={step.id} className="flex items-center gap-3">
                <div
                  className={cn(
                    'flex h-6 w-6 items-center justify-center rounded-full',
                    isComplete && 'bg-green-500/20 text-green-500',
                    isActive && 'bg-blue-500/20 text-blue-500',
                    !isActive && !isComplete && 'bg-neutral-800 text-neutral-500'
                  )}
                >
                  {isComplete ? (
                    <Check className="h-3 w-3" />
                  ) : isActive ? (
                    <Loader2 className="h-3 w-3 animate-spin" />
                  ) : (
                    <Icon className="h-3 w-3" />
                  )}
                </div>
                <span
                  className={cn(
                    'text-sm',
                    isActive && 'text-white font-medium',
                    !isActive && 'text-neutral-500'
                  )}
                >
                  {step.label}
                </span>
              </div>
            )
          })}
        </div>
      </div>

      {/* Contract ID */}
      {contractId && (
        <div className="border-b border-neutral-800 p-4">
          <p className="text-xs text-neutral-500 mb-1">Contract ID</p>
          <code className="text-xs font-mono text-green-500 break-all">
            {contractId}
          </code>
        </div>
      )}

      {/* Logs */}
      <div className="flex-1 overflow-hidden">
        <div className="h-full overflow-y-auto p-4">
          <pre className="text-xs font-mono text-neutral-400 whitespace-pre-wrap">
            {buildLogs.join('\n')}
          </pre>
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="border-t border-neutral-800 bg-red-900/30 p-4">
          <p className="text-sm text-red-400">{error}</p>
        </div>
      )}
    </div>
  )
}
