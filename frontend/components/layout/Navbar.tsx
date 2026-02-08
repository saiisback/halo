'use client'

import { useEffect, useState } from 'react'
import { useHaloStore, type BuildStep } from '@/lib/store'
import { WalletButton } from '@/components/chat/WalletButton'
import Image from 'next/image'
import { cn } from '@/lib/utils'
import { publishClaimableToVercel } from '@/lib/api'
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
  const [vercelConnected, setVercelConnected] = useState(false)
  const [isConnectingVercel, setIsConnectingVercel] = useState(false)
  const [vercelUser, setVercelUser] = useState<{ username?: string | null; name?: string | null; id?: string | null } | null>(null)
  const [isPublishing, setIsPublishing] = useState(false)
  const [publishedUrl, setPublishedUrl] = useState<string | null>(null)
  const [claimUrl, setClaimUrl] = useState<string | null>(null)
  const [publishError, setPublishError] = useState<string | null>(null)
  const [copied, setCopied] = useState(false)

  const category = getBuildCategory(buildStatus)
  const config = STATUS_CONFIG[category]
  const StatusIcon = config.icon

  const hasFiles = Object.keys(generatedFiles || {}).length > 0
  const canPublish =
    buildStatus === 'complete' && !!contractId && hasFiles && !isPublishing

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      try {
        const res = await fetch('/api/vercel/status')
        if (!res.ok) return
        const data = await res.json()
        if (!cancelled) setVercelConnected(!!data?.connected)
      } catch {
        // ignore
      }
    })()
    return () => {
      cancelled = true
    }
  }, [])

  useEffect(() => {
    let cancelled = false
    if (!vercelConnected) {
      setVercelUser(null)
      return
    }
    ;(async () => {
      try {
        const res = await fetch('/api/vercel/user', { cache: 'no-store' })
        if (!res.ok) return
        const data = await res.json()
        if (cancelled) return
        setVercelUser({
          username: data?.username ?? null,
          name: data?.name ?? null,
          id: data?.id ?? null,
        })
      } catch {
        // ignore
      }
    })()
    return () => {
      cancelled = true
    }
  }, [vercelConnected])

  const connectVercel = async () => {
    if (isConnectingVercel || vercelConnected) return
    setIsConnectingVercel(true)
    setPublishError(null)

    try {
      const popup = window.open(
        '/api/vercel/authorize',
        'vercel-oauth',
        'popup=yes,width=520,height=720'
      )
      if (!popup) throw new Error('Popup blocked. Please allow popups and try again.')

      await new Promise<void>((resolve, reject) => {
        const startedAt = Date.now()
        const maxMs = 2 * 60 * 1000

        const cleanup = () => {
          window.removeEventListener('message', onMessage)
          window.clearInterval(poll)
          window.clearTimeout(timeout)
        }

        const timeout = window.setTimeout(() => {
          cleanup()
          reject(new Error('Vercel connect timed out'))
        }, maxMs)

        const onMessage = (event: MessageEvent) => {
          // If opener messaging works, resolve immediately.
          if (event.origin !== window.location.origin) return
          const data = event.data as any
          if (data?.type === 'vercel_oauth_complete') {
            cleanup()
            if (data?.success) resolve()
            else reject(new Error(data?.error || 'Failed to connect Vercel'))
          }
        }
        window.addEventListener('message', onMessage)

        const poll = window.setInterval(async () => {
          try {
            // Even if the popup cannot message the opener (some browsers open a tab without opener),
            // we can detect success because the server stored the access token in an httpOnly cookie.
            const res = await fetch('/api/vercel/status', { cache: 'no-store' })
            if (res.ok) {
              const data = await res.json().catch(() => null)
              if (data?.connected) {
                cleanup()
                resolve()
                return
              }
            }
          } catch {
            // ignore
          }

          // If popup was closed and we still aren't connected, fail fast.
          const elapsed = Date.now() - startedAt
          if (elapsed > 3000 && popup.closed) {
            // Give a short grace period in case cookie propagation is delayed.
            // We'll keep polling until timeout unless closed very early and still disconnected.
          }
        }, 750)
      })

      setVercelConnected(true)
      // Fetch Vercel profile for display
      try {
        const u = await fetch('/api/vercel/user', { cache: 'no-store' })
        if (u.ok) {
          const data = await u.json()
          setVercelUser({
            username: data?.username ?? null,
            name: data?.name ?? null,
            id: data?.id ?? null,
          })
        }
      } catch {
        // ignore
      }
      try {
        popup.close()
      } catch {
        // ignore
      }
    } catch (e) {
      const msg = e instanceof Error ? e.message : 'Failed to connect Vercel'
      setPublishError(msg)
    } finally {
      setIsConnectingVercel(false)
    }
  }

  const handlePublish = async () => {
    if (!contractId || !hasFiles || isPublishing) return
    setIsPublishing(true)
    setPublishError(null)
    setClaimUrl(null)

    try {
      const name =
        (typeof (contractSpec as any)?.name === 'string' ? (contractSpec as any).name : null) ||
        'halo-dapp'

      // Claim Deployments flow: deploy with platform token, then user claims ownership.
      const res = await publishClaimableToVercel({
        contract_id: contractId,
        files: generatedFiles,
        name,
        network: 'testnet',
        return_url: window.location.href,
      })

      const url = res.url ? (res.url.startsWith('http') ? res.url : `https://${res.url}`) : null
      if (!url) {
        throw new Error('Publish succeeded but no URL returned')
      }

      setPublishedUrl(url)
      if (res.claim_url) {
        setClaimUrl(res.claim_url)
        // Open claim URL so user takes ownership immediately
        window.open(res.claim_url, '_blank', 'noopener,noreferrer')
      } else {
        // If claim URL missing, still open the deployment
        window.open(url, '_blank', 'noopener,noreferrer')
      }
    } catch (e) {
      const msg = e instanceof Error ? e.message : 'Failed to publish'
      setPublishError(msg)
    } finally {
      setIsPublishing(false)
    }
  }

  const disconnectVercel = async () => {
    setPublishError(null)
    try {
      await fetch('/api/vercel/logout', { method: 'POST' })
    } catch {
      // ignore
    }
    setVercelConnected(false)
    setVercelUser(null)
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

  const openClaim = () => {
    if (claimUrl) window.open(claimUrl, '_blank', 'noopener,noreferrer')
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

       
        {vercelConnected && (
          <div
            title={
              vercelUser?.username
                ? `Connected as ${vercelUser.username}`
                : vercelUser?.id
                  ? `Connected (user id: ${vercelUser.id})`
                  : 'Connected to Vercel'
            }
            className="hidden sm:flex items-center gap-1.5 rounded-xl bg-nb-gold/10 border border-nb-gold/20 px-3 py-1.5 text-xs font-semibold text-nb-gold"
          >
            <span className="max-w-[140px] truncate">
              {vercelUser?.username || vercelUser?.name || (vercelUser?.id ? `id:${vercelUser.id.slice(0, 8)}` : 'Vercel')}
            </span>
          </div>
        )}

        <div className="flex items-center gap-1">
          {!vercelConnected && (
            <button
              onClick={connectVercel}
              disabled={isConnectingVercel}
              title="Connect your Vercel account"
              className={cn(
                'flex items-center gap-1.5 rounded-xl border px-3.5 py-1.5 text-xs font-semibold transition-all btn-press',
                isConnectingVercel
                  ? 'bg-nb-gold/20 border-nb-gold/20 text-nb-gold/70 cursor-not-allowed'
                  : 'bg-nb-gold/10 border-nb-gold/20 text-nb-gold hover:bg-nb-gold/20'
              )}
            >
              {isConnectingVercel ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
              ) : (
                <Share2 className="h-3.5 w-3.5" />
              )}
              <span>{isConnectingVercel ? 'Connecting…' : 'Connect Vercel'}</span>
            </button>
          )}

          {vercelConnected && (
            <button
              onClick={disconnectVercel}
              title="Disconnect Vercel"
              className={cn(
                'flex items-center gap-1.5 rounded-xl border px-3.5 py-1.5 text-xs font-semibold transition-all btn-press',
                'bg-nb-gold/10 border-nb-gold/20 text-nb-gold hover:bg-nb-gold/20'
              )}
            >
              <span>Disconnect</span>
            </button>
          )}

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

          {claimUrl && (
            <button
              onClick={openClaim}
              title="Claim this deployment in your Vercel account"
              className={cn(
                'flex items-center gap-1.5 rounded-xl border px-3.5 py-1.5 text-xs font-semibold transition-all btn-press',
                'bg-nb-gold/10 border-nb-gold/20 text-nb-gold hover:bg-nb-gold/20'
              )}
            >
              <span>Claim</span>
            </button>
          )}

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
