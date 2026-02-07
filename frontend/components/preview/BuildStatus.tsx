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

const STEPS: { id: BuildStep; label: string; icon: typeof Brain; color: string }[] = [
  { id: 'analyzing', label: 'Analyzing', icon: Brain, color: 'nb-lilac' },
  { id: 'retrieving_docs', label: 'Fetching Docs', icon: BookOpen, color: 'nb-navy' },
  { id: 'generating_rust', label: 'Writing Contract', icon: Code, color: 'nb-teal' },
  { id: 'compiling', label: 'Compiling', icon: Hammer, color: 'nb-amber' },
  { id: 'deploying', label: 'Deploying', icon: Rocket, color: 'nb-gold' },
  { id: 'generating_react', label: 'Building UI', icon: Layout, color: 'nb-green' },
]

const COLOR_MAP: Record<string, { bg: string; text: string; border: string }> = {
  'nb-lilac': { bg: 'bg-nb-lilac', text: 'text-nb-lilac', border: 'border-nb-lilac/20' },
  'nb-navy': { bg: 'bg-nb-navy', text: 'text-nb-navy', border: 'border-nb-navy/20' },
  'nb-teal': { bg: 'bg-nb-teal', text: 'text-nb-teal', border: 'border-nb-teal/20' },
  'nb-amber': { bg: 'bg-nb-amber', text: 'text-nb-amber', border: 'border-nb-amber/20' },
  'nb-gold': { bg: 'bg-nb-gold', text: 'text-nb-gold', border: 'border-nb-gold/20' },
  'nb-green': { bg: 'bg-nb-green', text: 'text-nb-green', border: 'border-nb-green/20' },
}

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
          const colors = COLOR_MAP[step.color]

          const Icon = step.icon

          return (
            <div key={step.id} className="flex flex-col items-center">
              <div
                className={cn(
                  'flex h-8 w-8 items-center justify-center rounded-xl transition-all',
                  isComplete && `${colors.bg}/15 ${colors.text}`,
                  isActive && !isError && `${colors.bg}/10 ${colors.text}`,
                  isError && 'bg-nb-red/10 text-nb-red',
                  !isActive && !isComplete && !isError && 'bg-[var(--surface-2)] text-[var(--muted)]'
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
                  'mt-1.5 text-[10px] font-medium',
                  isActive && colors.text,
                  isComplete && colors.text,
                  !isActive && !isComplete && 'text-[var(--muted)]'
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
        <div className="mt-3 rounded-xl border border-[var(--border-color)] bg-[var(--surface-2)] p-2.5">
          <p className="text-xs text-[var(--muted)] font-mono truncate">
            {buildLogs[buildLogs.length - 1]}
          </p>
        </div>
      )}

      {/* Error message */}
      {error && (
        <div className="mt-3 rounded-xl border border-nb-red/20 bg-nb-red/5 p-2.5">
          <p className="text-xs font-medium text-nb-red">{error}</p>
        </div>
      )}
    </div>
  )
}

export function BuildStatusExpanded() {
  const { buildStatus, buildLogs, contractId, error } = useHaloStore()

  return (
    <div className="flex h-full flex-col bg-[var(--background)] bg-mesh-subtle">
      {/* Header */}
      <div className="border-b border-[var(--border-color)] px-4 py-3 bg-[var(--surface)]">
        <h3 className="text-sm font-medium gradient-text">Build Progress</h3>
      </div>

      {/* Steps */}
      <div className="border-b border-[var(--border-color)] p-4">
        <div className="space-y-3">
          {STEPS.map((step, index) => {
            const currentIndex = STEPS.findIndex((s) => s.id === buildStatus)
            const isActive = step.id === buildStatus
            const isComplete =
              buildStatus === 'complete' || index < currentIndex
            const Icon = step.icon
            const colors = COLOR_MAP[step.color]

            return (
              <div key={step.id} className="flex items-center gap-3">
                <div
                  className={cn(
                    'flex h-6 w-6 items-center justify-center rounded-lg',
                    isComplete && `${colors.bg}/15 ${colors.text}`,
                    isActive && `${colors.bg}/10 ${colors.text}`,
                    !isActive && !isComplete && 'bg-[var(--surface-2)] text-[var(--muted)]'
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
                    'text-sm font-medium',
                    isActive && colors.text,
                    isComplete && colors.text,
                    !isActive && !isComplete && 'text-[var(--muted)]'
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
        <div className="border-b border-[var(--border-color)] p-4">
          <p className="text-xs font-medium text-[var(--muted)] mb-1">Contract ID</p>
          <code className="text-xs font-mono text-nb-gold break-all">
            {contractId}
          </code>
        </div>
      )}

      {/* Logs */}
      <div className="flex-1 overflow-hidden">
        <div className="h-full overflow-y-auto p-4">
          <pre className="text-xs font-mono text-[var(--muted)] whitespace-pre-wrap">
            {buildLogs.join('\n')}
          </pre>
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="border-t border-nb-red/20 bg-nb-red/5 p-4">
          <p className="text-sm font-medium text-nb-red">{error}</p>
        </div>
      )}
    </div>
  )
}
