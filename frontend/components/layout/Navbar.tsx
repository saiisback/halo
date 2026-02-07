'use client'

import { useState } from 'react'
import { useHaloStore, type BuildStep } from '@/lib/store'
import { WalletButton } from '@/components/chat/WalletButton'
import Image from 'next/image'
import { cn } from '@/lib/utils'
import { publishToVercel } from '@/lib/api'
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
  const { buildStatus, theme, toggleTheme, generatedFiles, contractId, contractSpec } = useHaloStore()
  const [isPublishing, setIsPublishing] = useState(false)
  const [publishedUrl, setPublishedUrl] = useState<string | null>(null)
  const [publishError, setPublishError] = useState<string | null>(null)
  const [copied, setCopied] = useState(false)

  const category = getBuildCategory(buildStatus)
  const config = STATUS_CONFIG[category]
  const StatusIcon = config.icon

  const hasFiles = Object.keys(generatedFiles || {}).length > 0
  const canPublish = buildStatus === 'complete' && !!contractId && hasFiles && !isPublishing

  const handlePublish = async () => {
    if (!contractId || !hasFiles || isPublishing) return
    setIsPublishing(true)
    setPublishError(null)

    try {
      const name =
        (typeof (contractSpec as any)?.name === 'string' ? (contractSpec as any).name : null) ||
        'halo-dapp'

      const res = await publishToVercel({
        contract_id: contractId,
        files: generatedFiles,
        name,
        network: 'testnet',
      })

      const url = res.url ? (res.url.startsWith('http') ? res.url : `https://${res.url}`) : null
      if (!url) {
        throw new Error('Publish succeeded but no URL returned')
      }

      setPublishedUrl(url)
      // Open automatically for the “one click publish” experience
      window.open(url, '_blank', 'noopener,noreferrer')
    } catch (e) {
      const msg = e instanceof Error ? e.message : 'Failed to publish'
      setPublishError(msg)
    } finally {
      setIsPublishing(false)
    }
  }

  const copyUrl = async () => {
    if (!publishedUrl) return
    try {
      await navigator.clipboard.writeText(publishedUrl)
      setCopied(true)
      setTimeout(() => setCopied(false), 1500)
    } catch {
      // ignore
    }
  }

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

        <div className="flex items-center gap-1">
          <button
            onClick={handlePublish}
            disabled={!canPublish}
            title={
              publishError
                ? `Publish failed: ${publishError}`
                : !canPublish
                  ? 'Generate a DApp first (must be complete) to publish'
                  : 'Publish this DApp to Vercel'
            }
            className={cn(
              'flex items-center gap-1.5 rounded-xl border px-3.5 py-1.5 text-xs font-semibold transition-all btn-press',
              canPublish
                ? 'bg-nb-gold border-nb-gold text-black hover:bg-nb-amber hover:border-nb-amber glow-gold-sm'
                : 'bg-nb-gold/20 border-nb-gold/20 text-nb-gold/60 cursor-not-allowed'
            )}
          >
            {isPublishing ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
            ) : (
              <Rocket className="h-3.5 w-3.5" />
            )}
            <span>{isPublishing ? 'Publishing…' : publishedUrl ? 'Published' : 'Deploy'}</span>
          </button>

          {publishedUrl && (
            <button
              onClick={copyUrl}
              title={copied ? 'Copied!' : 'Copy published URL'}
              className={cn(
                'flex h-8 w-8 items-center justify-center rounded-xl border transition-all btn-press',
                'bg-nb-gold/10 border-nb-gold/20 text-nb-gold hover:bg-nb-gold/20'
              )}
            >
              {copied ? <Check className="h-4 w-4" /> : <Share2 className="h-4 w-4" />}
            </button>
          )}
        </div>

        <WalletButton />
      </div>
    </nav>
  )
}
