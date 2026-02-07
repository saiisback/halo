'use client'

import { useHaloStore, type BuildStep } from '@/lib/store'
import { WalletButton } from '@/components/chat/WalletButton'
import Image from 'next/image'
import { cn } from '@/lib/utils'
import {
  Share2,
  Rocket,
  Loader2,
  Check,
  AlertCircle,
  Circle,
  Sun,
  Moon,
} from 'lucide-react'

const STATUS_CONFIG: Record<
  string,
  { label: string; icon: typeof Circle; color: string; bg: string }
> = {
  idle: {
    label: 'Ready',
    icon: Circle,
    color: 'text-[var(--muted)]',
    bg: 'border-[var(--border-color)]',
  },
  building: {
    label: 'Building...',
    icon: Loader2,
    color: 'text-nb-gold',
    bg: 'bg-nb-gold/5 border-nb-gold/20',
  },
  complete: {
    label: 'Complete',
    icon: Check,
    color: 'text-nb-green',
    bg: 'bg-nb-green/5 border-nb-green/20',
  },
  error: {
    label: 'Error',
    icon: AlertCircle,
    color: 'text-nb-red',
    bg: 'bg-nb-red/5 border-nb-red/20',
  },
}

function getBuildCategory(status: BuildStep): string {
  if (status === 'idle') return 'idle'
  if (status === 'complete') return 'complete'
  if (status === 'error') return 'error'
  return 'building'
}

export function Navbar() {
  const { buildStatus, theme, toggleTheme } = useHaloStore()

  const category = getBuildCategory(buildStatus)
  const config = STATUS_CONFIG[category]
  const StatusIcon = config.icon

  return (
    <nav className="flex h-12 shrink-0 items-center border-b border-[var(--border-color)] bg-[var(--surface)] px-4">
      {/* Left: Logo + Brand */}
      <div className="flex items-center gap-2.5">
        <div className="flex h-8 w-8 items-center justify-center">
          <Image src="/logo.svg" alt="Halo" width={32} height={32} />
        </div>
        <span className="font-serif text-lg tracking-wide text-nb-gold">
          HALO STUDIO
        </span>
      </div>

      {/* Center: Build Status */}
      <div className="flex flex-1 items-center justify-center">
        <div
          className={cn(
            'flex items-center gap-1.5 border rounded-full px-3 py-1 text-xs font-medium',
            config.color,
            config.bg
          )}
        >
          <StatusIcon
            className={cn(
              'h-3 w-3',
              category === 'building' && 'animate-spin'
            )}
          />
          <span>{config.label}</span>
        </div>
      </div>

      {/* Right: Actions */}
      <div className="flex items-center gap-2">
        {/* Theme Toggle */}
        <button
          onClick={toggleTheme}
          className="flex h-8 w-8 items-center justify-center rounded-xl bg-nb-gold/10 border border-nb-gold/20 text-nb-gold transition-all hover:bg-nb-gold/20 btn-press"
        >
          {theme === 'dark' ? (
            <Sun className="h-4 w-4" />
          ) : (
            <Moon className="h-4 w-4" />
          )}
        </button>

        <button className="flex items-center gap-1.5 rounded-xl bg-nb-gold/10 border border-nb-gold/20 px-3.5 py-1.5 text-xs font-semibold text-nb-gold transition-all hover:bg-nb-gold hover:text-black btn-press">
          <Share2 className="h-3.5 w-3.5" />
          <span>Share</span>
        </button>

        <button className="flex items-center gap-1.5 rounded-xl bg-nb-gold border border-nb-gold px-3.5 py-1.5 text-xs font-semibold text-black transition-all hover:bg-nb-amber hover:border-nb-amber btn-press glow-gold-sm">
          <Rocket className="h-3.5 w-3.5" />
          <span>Deploy</span>
        </button>

        <WalletButton />
      </div>
    </nav>
  )
}
