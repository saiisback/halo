'use client'

import { useState, useRef, useEffect } from 'react'
import { useHaloStore } from '@/lib/store'
import { Wallet, Loader2, Copy, Check, ChevronDown } from 'lucide-react'

function truncateAddress(address: string) {
  return `${address.slice(0, 4)}...${address.slice(-4)}`
}

export function WalletButton() {
  const { walletAddress, walletConnecting, walletError, connectWallet, disconnectWallet } = useHaloStore()
  const [dropdownOpen, setDropdownOpen] = useState(false)
  const [copied, setCopied] = useState(false)
  const dropdownRef = useRef<HTMLDivElement>(null)

  // Close dropdown on outside click
  useEffect(() => {
    const handleClick = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setDropdownOpen(false)
      }
    }
    if (dropdownOpen) {
      document.addEventListener('mousedown', handleClick)
      return () => document.removeEventListener('mousedown', handleClick)
    }
  }, [dropdownOpen])

  const copyAddress = () => {
    if (walletAddress) {
      navigator.clipboard.writeText(walletAddress)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    }
  }

  // Connecting state
  if (walletConnecting) {
    return (
      <button
        disabled
        className="flex items-center gap-1.5 rounded-lg border border-[var(--border-color)] px-3 py-1.5 text-xs font-medium text-[var(--muted)] opacity-60"
      >
        <Loader2 className="h-3.5 w-3.5 animate-spin" />
        <span>Connecting...</span>
      </button>
    )
  }

  // Connected state
  if (walletAddress) {
    return (
      <div className="relative" ref={dropdownRef}>
        <button
          onClick={() => setDropdownOpen(!dropdownOpen)}
          className="flex items-center gap-1.5 rounded-lg border border-nb-green/20 bg-nb-green/5 px-3 py-1.5 text-xs font-medium text-nb-green transition-all hover:bg-nb-green/10 btn-press"
        >
          <div className="h-2 w-2 rounded-full bg-nb-green animate-pulse" />
          <span className="font-mono">{truncateAddress(walletAddress)}</span>
          <ChevronDown className="h-3 w-3" />
        </button>

        {dropdownOpen && (
          <div className="absolute right-0 top-full mt-2 z-50 w-64 rounded-xl border border-[var(--border-color)] bg-[var(--surface)] p-3 shadow-soft">
            <p className="text-xs font-medium text-[var(--muted)] mb-1">Connected Wallet</p>
            <div className="flex items-center gap-2 mb-3">
              <p className="text-xs font-mono text-[var(--foreground)] break-all flex-1">{walletAddress}</p>
              <button
                onClick={copyAddress}
                className="shrink-0 rounded-lg border border-[var(--border-color)] p-1.5 transition-all hover:bg-nb-gold/10 hover:text-nb-gold hover:border-nb-gold/30"
              >
                {copied ? (
                  <Check className="h-3.5 w-3.5 text-nb-green" />
                ) : (
                  <Copy className="h-3.5 w-3.5" />
                )}
              </button>
            </div>
            <button
              onClick={() => { disconnectWallet(); setDropdownOpen(false) }}
              className="w-full rounded-lg border border-[var(--border-color)] px-3 py-1.5 text-xs font-medium text-[var(--foreground)] transition-all hover:bg-nb-red/10 hover:text-nb-red hover:border-nb-red/30"
            >
              Disconnect
            </button>
          </div>
        )}
      </div>
    )
  }

  // Disconnected state
  return (
    <div className="flex flex-col items-end">
      <button
        onClick={connectWallet}
        className="flex items-center gap-1.5 rounded-xl bg-nb-gold border border-nb-gold px-3.5 py-1.5 text-xs font-semibold text-black transition-all hover:bg-nb-amber hover:border-nb-amber btn-press glow-gold-sm"
      >
        <Wallet className="h-3.5 w-3.5" />
        <span>Connect</span>
      </button>
      {walletError && (
        <p className="mt-1 max-w-[200px] text-right text-[10px] font-medium text-nb-red">{walletError}</p>
      )}
    </div>
  )
}
