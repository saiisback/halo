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
        className="flex items-center gap-1.5 rounded-lg bg-neutral-800 px-3 py-1.5 text-xs text-neutral-400"
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
          className="flex items-center gap-1.5 rounded-lg bg-green-500/10 border border-green-500/20 px-3 py-1.5 text-xs text-green-400 hover:bg-green-500/20 transition-colors"
        >
          <div className="h-2 w-2 rounded-full bg-green-400" />
          <span className="font-mono">{truncateAddress(walletAddress)}</span>
          <ChevronDown className="h-3 w-3" />
        </button>

        {dropdownOpen && (
          <div className="absolute right-0 top-full mt-1 z-50 w-64 rounded-lg border border-neutral-700 bg-neutral-800 p-3 shadow-xl">
            <p className="text-xs text-neutral-400 mb-1">Connected Wallet</p>
            <div className="flex items-center gap-2 mb-3">
              <p className="text-xs font-mono text-white break-all flex-1">{walletAddress}</p>
              <button
                onClick={copyAddress}
                className="shrink-0 rounded p-1 hover:bg-neutral-700 transition-colors"
              >
                {copied ? (
                  <Check className="h-3.5 w-3.5 text-green-400" />
                ) : (
                  <Copy className="h-3.5 w-3.5 text-neutral-400" />
                )}
              </button>
            </div>
            <button
              onClick={() => { disconnectWallet(); setDropdownOpen(false) }}
              className="w-full rounded-md bg-neutral-700 px-3 py-1.5 text-xs text-neutral-300 hover:bg-neutral-600 transition-colors"
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
        className="flex items-center gap-1.5 rounded-lg bg-neutral-800 px-3 py-1.5 text-xs text-neutral-300 hover:bg-neutral-700 hover:text-white transition-colors"
      >
        <Wallet className="h-3.5 w-3.5" />
        <span>Connect</span>
      </button>
      {walletError && (
        <p className="mt-1 max-w-[200px] text-right text-[10px] text-red-400">{walletError}</p>
      )}
    </div>
  )
}
