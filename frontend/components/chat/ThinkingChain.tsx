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

const STEPS: { id: BuildStep; label: string; thought: string; icon: typeof Brain; color: string }[] = [
  { id: 'analyzing', label: 'Analyzing', thought: 'Understanding your requirements...', icon: Brain, color: 'nb-lilac' },
  { id: 'retrieving_docs', label: 'Researching', thought: 'Fetching Stellar/Soroban documentation...', icon: BookOpen, color: 'nb-navy' },
  { id: 'generating_rust', label: 'Writing Contract', thought: 'Generating Soroban smart contract...', icon: Code, color: 'nb-teal' },
  { id: 'compiling', label: 'Compiling', thought: 'Building and compiling contract...', icon: Hammer, color: 'nb-amber' },
  { id: 'deploying', label: 'Deploying', thought: 'Deploying to Stellar testnet...', icon: Rocket, color: 'nb-gold' },
  { id: 'generating_react', label: 'Building UI', thought: 'Creating React frontend...', icon: Layout, color: 'nb-green' },
]

const COLOR_MAP: Record<string, { bg: string; text: string; border: string }> = {
  'nb-lilac': { bg: 'bg-nb-lilac', text: 'text-nb-lilac', border: 'border-nb-lilac/30' },
  'nb-navy': { bg: 'bg-nb-navy', text: 'text-nb-navy', border: 'border-nb-navy/30' },
  'nb-teal': { bg: 'bg-nb-teal', text: 'text-nb-teal', border: 'border-nb-teal/30' },
  'nb-amber': { bg: 'bg-nb-amber', text: 'text-nb-amber', border: 'border-nb-amber/30' },
  'nb-gold': { bg: 'bg-nb-gold', text: 'text-nb-gold', border: 'border-nb-gold/30' },
  'nb-green': { bg: 'bg-nb-green', text: 'text-nb-green', border: 'border-nb-green/30' },
}

export function ThinkingChain() {
  const { buildStatus, buildLogs, error, isBuilding } = useHaloStore()

  const currentStepIndex = STEPS.findIndex((s) => s.id === buildStatus)
  const isComplete = buildStatus === 'complete'
  const isError = buildStatus === 'error'

  // Don't render if idle
  if (buildStatus === 'idle') return null

  return (
    <div className="flex gap-3 animate-fade-in-up">
      {/* Bot Avatar */}
      <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-nb-gold/10 text-nb-gold">
        <Bot className="h-3.5 w-3.5" />
      </div>

      {/* Thinking Chain */}
      <div className="flex-1 min-w-0">
        <div className="rounded-2xl rounded-bl-md overflow-hidden bg-[var(--surface-2)] border border-[var(--border-color)]">
          {/* Header */}
          <div className="px-4 py-2.5 border-b border-[var(--border-color)]">
            <div className="flex items-center gap-2">
              {!isComplete && !isError && (
                <Loader2 className="h-3 w-3 animate-spin text-nb-gold" />
              )}
              {isComplete && (
                <Check className="h-3 w-3 text-nb-green" />
              )}
              {isError && (
                <AlertCircle className="h-3 w-3 text-nb-red" />
              )}
              <span className="text-xs font-medium text-[var(--foreground)]">
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
              const colors = COLOR_MAP[step.color]

              return (
                <div
                  key={step.id}
                  className={cn(
                    'flex items-start gap-2 py-1.5 transition-all duration-300',
                    isActive && 'animate-fade-in-up'
                  )}
                >
                  {/* Step Icon */}
                  <div
                    className={cn(
                      'flex h-5 w-5 shrink-0 items-center justify-center rounded-md mt-0.5',
                      isStepComplete && `${colors.bg}/20 ${colors.text}`,
                      isActive && !isStepError && `${colors.bg}/10 ${colors.text}`,
                      isStepError && 'bg-nb-red/10 text-nb-red',
                      !isActive && !isStepComplete && !isStepError && 'text-[var(--muted)]'
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
                          isStepComplete && colors.text,
                          isActive && !isStepError && colors.text,
                          isStepError && 'text-nb-red',
                          !isActive && !isStepComplete && !isStepError && 'text-[var(--muted)]'
                        )}
                      >
                        {step.label}
                      </span>
                    </div>
                    {isActive && !isStepError && (
                      <p className="text-[11px] text-[var(--muted)] mt-0.5">
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
              <div className="rounded-lg border border-[var(--border-color)] bg-[var(--surface)] px-2.5 py-1.5">
                <p className="text-[10px] text-[var(--muted)] font-mono truncate">
                  {buildLogs[buildLogs.length - 1]}
                </p>
              </div>
            </div>
          )}

          {/* Error Message */}
          {error && (
            <div className="px-3 pb-3">
              <div className="rounded-lg border border-nb-red/20 bg-nb-red/5 px-2.5 py-1.5">
                <p className="text-[11px] font-medium text-nb-red">{error}</p>
              </div>
            </div>
          )}
        </div>

        {/* Timestamp */}
        <span className="mt-1.5 text-[10px] text-[var(--muted)] block">
          {new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
        </span>
      </div>
    </div>
  )
}
