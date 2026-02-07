'use client'

import { Component, type ReactNode, useState } from 'react'
import {
  SandpackProvider,
  SandpackPreview as SandpackPreviewComponent,
  SandpackCodeEditor,
  SandpackConsole,
  SandpackLayout,
} from '@codesandbox/sandpack-react'
import { useContractHook } from '@/hooks/useContract'
import { mockWalletScript } from '@/hooks/mockWallet'
import { getWalletBridgeScript } from '@/hooks/walletBridge'
import { useWalletBridge } from '@/hooks/useWalletBridge'
import { Wallet, ExternalLink, Globe, Copy, Check } from 'lucide-react'

interface SandpackPreviewProps {
  files: Record<string, string>
  contractId: string | null
  walletAddress?: string | null
  showCode?: boolean
  showConsole?: boolean
}

interface ErrorBoundaryState {
  hasError: boolean
  error: Error | null
}

class SandpackErrorBoundary extends Component<
  { children: ReactNode; files: Record<string, string> },
  ErrorBoundaryState
> {
  constructor(props: { children: ReactNode; files: Record<string, string> }) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error }
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error('Sandpack error:', error, errorInfo)
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="flex h-full flex-col items-center justify-center p-6 text-center bg-neutral-900">
          <div className="rounded-xl bg-red-900/30 border border-red-500/30 p-6 max-w-lg">
            <h3 className="text-lg font-semibold text-red-400 mb-2">
              Syntax Error in Generated Code
            </h3>
            <p className="text-sm text-red-300/80 mb-4">
              The generated code has a syntax error. This can happen occasionally with AI-generated code.
            </p>
            <div className="text-left bg-neutral-950 rounded-lg p-3 text-xs font-mono text-red-300 overflow-auto max-h-32">
              {this.state.error?.message || 'Unknown error'}
            </div>
            <p className="text-xs text-neutral-500 mt-4">
              Try regenerating with a different prompt, or check the Code tab to manually fix the error.
            </p>
          </div>
        </div>
      )
    }
    return this.props.children
  }
}

const getDefaultFiles = (contractId: string | null, walletAddress?: string | null) => ({
  '/hooks/useContract.js': useContractHook,
  '/lib/stellar.js': `export const STELLAR_NETWORK = 'testnet';
export const CONTRACT_ID = '${contractId || 'NOT_DEPLOYED'}';
export const HORIZON_URL = 'https://horizon-testnet.stellar.org';
export const SOROBAN_RPC_URL = 'https://soroban-testnet.stellar.org';
export const IS_LIVE_WALLET = ${!!walletAddress};
export const WALLET_ADDRESS = '${walletAddress || ''}';
`,
  '/lib/mockWallet.js': walletAddress
    ? getWalletBridgeScript(walletAddress)
    : mockWalletScript,
  '/index.js': `import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';

// Initialize wallet for preview${walletAddress ? ' (bridge to real Freighter)' : ' (simulates Freighter)'}
import './lib/mockWallet.js';

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(<App />);
`,
})

const dependencies = {
  '@stellar/freighter-api': '^2.0.0',
  '@stellar/stellar-sdk': '14.4.3',
}

const customTheme = {
  colors: {
    surface1: '#171717', // neutral-900
    surface2: '#262626', // neutral-800
    surface3: '#404040', // neutral-700
    clickable: '#737373', // neutral-500
    base: '#e5e5e5', // neutral-200
    disabled: '#525252', // neutral-600
    hover: '#3b82f6', // blue-500
    accent: '#3b82f6', // blue-500
    error: '#ef4444', // red-500
    errorSurface: '#7f1d1d', // red-900
  },
  syntax: {
    plain: '#e5e5e5',
    comment: { color: '#737373', fontStyle: 'italic' as const },
    keyword: '#a78bfa', // violet-400
    tag: '#f472b6', // pink-400
    punctuation: '#e5e5e5',
    definition: '#22d3ee', // cyan-400
    property: '#fb923c', // orange-400
    static: '#22d3ee',
    string: '#4ade80', // green-400
  },
  font: {
    body: 'var(--font-sans)',
    mono: 'var(--font-mono)',
    size: '13px',
    lineHeight: '1.5',
  },
}

const defaultAppCode = [
  'export default function App() {',
  '  return (',
  '    <div style={{',
  '      padding: "2rem",',
  '      fontFamily: "system-ui, sans-serif",',
  '      color: "#fff",',
  '      background: "#0a0a0a",',
  '      minHeight: "100vh"',
  '    }}>',
  '      <h1>Welcome to Halo</h1>',
  '      <p>Your DApp will appear here once generated.</p>',
  '    </div>',
  '  );',
  '}',
].join('\n')

// Preview Header Bar - Shows wallet/contract status
function PreviewHeader({ contractId, walletAddress }: { contractId: string | null; walletAddress?: string | null }) {
  const [copied, setCopied] = useState(false)
  const isLive = !!walletAddress
  const displayAddress = walletAddress
    ? `${walletAddress.slice(0, 4)}...${walletAddress.slice(-4)}`
    : 'GDEMO7...Q7HAL'

  const copyContractId = () => {
    if (contractId) {
      navigator.clipboard.writeText(contractId)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    }
  }

  return (
    <div className="flex items-center justify-between px-3 py-2 bg-neutral-800/50 border-b border-neutral-700/50 text-xs">
      {/* Left: Mode Badge */}
      <div className="flex items-center gap-3">
        {isLive ? (
          <div className="flex items-center gap-1.5 px-2 py-1 rounded-full bg-green-500/10 border border-green-500/20">
            <div className="w-1.5 h-1.5 rounded-full bg-green-400" />
            <span className="text-green-400 font-medium">Live Mode</span>
          </div>
        ) : (
          <div className="flex items-center gap-1.5 px-2 py-1 rounded-full bg-amber-500/10 border border-amber-500/20">
            <div className="w-1.5 h-1.5 rounded-full bg-amber-400 animate-pulse" />
            <span className="text-amber-400 font-medium">Demo Mode</span>
          </div>
        )}

        {/* Network */}
        <div className="flex items-center gap-1.5 text-neutral-400">
          <Globe className="w-3 h-3" />
          <span>Testnet</span>
        </div>
      </div>

      {/* Right: Wallet & Contract */}
      <div className="flex items-center gap-3">
        {/* Wallet */}
        <div className={`flex items-center gap-1.5 px-2 py-1 rounded-lg ${
          isLive
            ? 'bg-green-500/10 border border-green-500/20'
            : 'bg-neutral-700/50 border border-neutral-600/30'
        }`}>
          <Wallet className={`w-3 h-3 ${isLive ? 'text-green-400' : 'text-neutral-400'}`} />
          <span className={`font-mono ${isLive ? 'text-green-400' : 'text-neutral-400'}`}>{displayAddress}</span>
        </div>

        {/* Contract ID */}
        {contractId && contractId !== 'NOT_DEPLOYED' && (
          <button
            onClick={copyContractId}
            className="flex items-center gap-1.5 px-2 py-1 rounded-lg bg-blue-500/10 border border-blue-500/20 hover:bg-blue-500/20 transition-colors"
          >
            <span className="text-blue-400 font-mono">
              {contractId.slice(0, 8)}...{contractId.slice(-4)}
            </span>
            {copied ? (
              <Check className="w-3 h-3 text-green-400" />
            ) : (
              <Copy className="w-3 h-3 text-blue-400" />
            )}
          </button>
        )}
      </div>
    </div>
  )
}

export function SandpackPreview(props: SandpackPreviewProps) {
  const { files, contractId, walletAddress, showCode = false, showConsole = false } = props

  // Activate parent-side bridge listener when wallet is connected
  useWalletBridge(walletAddress ?? null)

  const allFiles: Record<string, string> = {
    ...getDefaultFiles(contractId, walletAddress),
    ...files,
  }

  if (!allFiles['/App.js']) {
    allFiles['/App.js'] = allFiles['/App.jsx'] || defaultAppCode
    delete allFiles['/App.jsx']
  }

  return (
    <SandpackErrorBoundary files={allFiles}>
      <div className="h-full w-full flex flex-col">
        {/* Preview Header - Shows demo mode & wallet info */}
        {!showCode && !showConsole && (
          <PreviewHeader contractId={contractId} walletAddress={walletAddress} />
        )}

        <div className="flex-1 min-h-0">
          <SandpackProvider
            template="react"
            theme={customTheme}
            files={allFiles}
            customSetup={{
              dependencies,
            }}
            options={{
              recompileMode: 'delayed',
              recompileDelay: 500,
              externalResources: [],
            }}
          >
            <SandpackLayout
              className="!h-full !min-h-full !flex-1"
              style={{ height: '100%', display: 'flex', flexDirection: 'column' }}
            >
              {showCode && (
                <SandpackCodeEditor
                  showTabs
                  showLineNumbers
                  showInlineErrors
                  wrapContent
                  style={{ height: '100%', minWidth: showConsole ? '50%' : '100%' }}
                />
              )}
              {!showCode && !showConsole && (
                <SandpackPreviewComponent
                  showOpenInCodeSandbox={false}
                  showRefreshButton
                  style={{ height: '100%', flex: 1, minHeight: 0 }}
                />
              )}
              {showConsole && (
                <SandpackConsole
                  style={{ height: '100%', minWidth: '50%' }}
                  showHeader
                />
              )}
            </SandpackLayout>
          </SandpackProvider>
        </div>
      </div>
    </SandpackErrorBoundary>
  )
}
