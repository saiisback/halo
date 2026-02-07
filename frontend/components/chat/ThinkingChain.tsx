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
  Bot,
} from 'lucide-react'

const STEPS: { id: BuildStep; label: string; thought: string; icon: typeof Brain }[] = [
  { id: 'analyzing', label: 'Analyzing', thought: 'Understanding your requirements...', icon: Brain },
  { id: 'retrieving_docs', label: 'Researching', thought: 'Fetching Stellar/Soroban documentation...', icon: BookOpen },
  { id: 'generating_rust', label: 'Writing Contract', thought: 'Generating Soroban smart contract...', icon: Code },
  { id: 'compiling', label: 'Compiling', thought: 'Building and compiling contract...', icon: Hammer },
  { id: 'deploying', label: 'Deploying', thought: 'Deploying to Stellar testnet...', icon: Rocket },
  { id: 'generating_react', label: 'Building UI', thought: 'Creating React frontend...', icon: Layout },
]

export function ThinkingChain() {
  const { buildStatus, buildLogs, error, isBuilding } = useHaloStore()

  const currentStepIndex = STEPS.findIndex((s) => s.id === buildStatus)
  const isComplete = buildStatus === 'complete'
  const isError = buildStatus === 'error'

  // Don't render if idle
  if (buildStatus === 'idle') return null

  return (
    <div className="flex gap-3">
      {/* Bot Avatar */}
      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-neutral-700 text-neutral-300">
        <Bot className="h-4 w-4" />
      </div>

      {/* Thinking Chain */}
      <div className="flex-1 min-w-0">
        <div className="rounded-xl bg-neutral-800/50 border border-neutral-700/50 overflow-hidden">
          {/* Header */}
          <div className="px-3 py-2 border-b border-neutral-700/50 bg-neutral-800/80">
            <div className="flex items-center gap-2">
              {!isComplete && !isError && (
                <Loader2 className="h-3 w-3 animate-spin text-blue-400" />
              )}
              {isComplete && (
                <Check className="h-3 w-3 text-green-400" />
              )}
              {isError && (
                <AlertCircle className="h-3 w-3 text-red-400" />
              )}
              <span className="text-xs font-medium text-neutral-300">
                {isComplete ? 'Build Complete' : isError ? 'Build Failed' : 'Thinking...'}
              </span>
            </div>
          </div>

          {/* Steps */}
          <div className="p-3 space-y-1">
            {STEPS.map((step, index) => {
              const isActive = step.id === buildStatus
              const isStepComplete = isComplete || index < currentStepIndex
              const isStepError = isError && index === currentStepIndex
              const shouldShow = index <= currentStepIndex || isComplete

              if (!shouldShow && !isComplete) return null

              const Icon = step.icon

              return (
                <div
                  key={step.id}
                  className={cn(
                    'flex items-start gap-2 py-1.5 transition-all duration-300',
                    isActive && 'animate-in fade-in slide-in-from-top-1'
                  )}
                >
                  {/* Step Icon */}
                  <div
                    className={cn(
                      'flex h-5 w-5 shrink-0 items-center justify-center rounded-full mt-0.5',
                      isStepComplete && 'bg-green-500/20 text-green-400',
                      isActive && !isStepError && 'bg-blue-500/20 text-blue-400',
                      isStepError && 'bg-red-500/20 text-red-400',
                      !isActive && !isStepComplete && !isStepError && 'bg-neutral-700 text-neutral-500'
                    )}
                  >
                    {isStepComplete ? (
                      <Check className="h-3 w-3" />
                    ) : isActive && !isStepError ? (
                      <Loader2 className="h-3 w-3 animate-spin" />
                    ) : isStepError ? (
                      <AlertCircle className="h-3 w-3" />
                    ) : (
                      <Icon className="h-3 w-3" />
                    )}
                  </div>

                  {/* Step Content */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span
                        className={cn(
                          'text-xs font-medium',
                          isStepComplete && 'text-green-400',
                          isActive && !isStepError && 'text-blue-400',
                          isStepError && 'text-red-400',
                          !isActive && !isStepComplete && !isStepError && 'text-neutral-500'
                        )}
                      >
                        {step.label}
                      </span>
                    </div>
                    {isActive && !isStepError && (
                      <p className="text-[11px] text-neutral-500 mt-0.5">
                        {step.thought}
                      </p>
                    )}
                  </div>
                </div>
              )
            })}
          </div>

          {/* Latest Log */}
          {buildLogs.length > 0 && isBuilding && (
            <div className="px-3 pb-3">
              <div className="rounded-md bg-neutral-900/50 px-2 py-1.5">
                <p className="text-[10px] text-neutral-500 font-mono truncate">
                  {buildLogs[buildLogs.length - 1]}
                </p>
              </div>
            </div>
          )}

          {/* Error Message */}
          {error && (
            <div className="px-3 pb-3">
              <div className="rounded-md bg-red-900/30 px-2 py-1.5">
                <p className="text-[11px] text-red-400">{error}</p>
              </div>
            </div>
          )}
        </div>

        {/* Timestamp */}
        <span className="mt-1 text-xs text-neutral-500 block">
          {new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
        </span>
      </div>
    </div>
  )
}
