import { create } from 'zustand'
import { generateDApp, type BuildEvent } from './api'

export type BuildStep =
  | 'idle'
  | 'analyzing'
  | 'retrieving_docs'
  | 'generating_rust'
  | 'compiling'
  | 'deploying'
  | 'generating_react'
  | 'complete'
  | 'error'

export interface Message {
  id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  timestamp: Date
}

interface HaloStore {
  // State
  messages: Message[]
  buildStatus: BuildStep
  buildLogs: string[]
  generatedFiles: Record<string, string>
  contractId: string | null
  isBuilding: boolean
  error: string | null

  // Wallet state
  walletAddress: string | null
  walletConnecting: boolean
  walletError: string | null

  // Actions
  sendPrompt: (prompt: string) => Promise<void>
  reset: () => void
  addMessage: (role: Message['role'], content: string) => void
  setBuildStatus: (status: BuildStep) => void
  addBuildLog: (log: string) => void
  setGeneratedFiles: (files: Record<string, string>) => void
  setContractId: (id: string) => void
  setError: (error: string | null) => void
  loadTestFiles: () => void
  connectWallet: () => Promise<void>
  disconnectWallet: () => void
}

export const useHaloStore = create<HaloStore>((set, get) => ({
  // Initial state
  messages: [],
  buildStatus: 'idle',
  buildLogs: [],
  generatedFiles: {},
  contractId: null,
  isBuilding: false,
  error: null,

  // Wallet state
  walletAddress: null,
  walletConnecting: false,
  walletError: null,

  // Actions
  addMessage: (role, content) => {
    const message: Message = {
      id: crypto.randomUUID(),
      role,
      content,
      timestamp: new Date(),
    }
    set((state) => ({
      messages: [...state.messages, message],
    }))
  },

  setBuildStatus: (status) => {
    set({ buildStatus: status })
  },

  addBuildLog: (log) => {
    set((state) => ({
      buildLogs: [...state.buildLogs, log],
    }))
  },

  setGeneratedFiles: (files) => {
    set({ generatedFiles: files })
  },

  setContractId: (id) => {
    set({ contractId: id })
  },

  setError: (error) => {
    set({ error, buildStatus: error ? 'error' : get().buildStatus })
  },

  sendPrompt: async (prompt) => {
    const { addMessage, setBuildStatus, addBuildLog, setGeneratedFiles, setContractId, setError } = get()

    // Reset state for new build
    set({
      isBuilding: true,
      buildStatus: 'analyzing',
      buildLogs: [],
      error: null,
    })

    // Add user message
    addMessage('user', prompt)

    try {
      // Stream build events
      for await (const event of generateDApp({ prompt, user_wallet: get().walletAddress || undefined })) {
        handleBuildEvent(event, {
          setBuildStatus,
          addBuildLog,
          setGeneratedFiles,
          setContractId,
          setError,
          addMessage,
        })
      }

      // Build complete
      set({ isBuilding: false })
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error'
      setError(errorMessage)
      addMessage('system', `Error: ${errorMessage}`)
      set({ isBuilding: false })
    }
  },

  reset: () => {
    set({
      messages: [],
      buildStatus: 'idle',
      buildLogs: [],
      generatedFiles: {},
      contractId: null,
      isBuilding: false,
      error: null,
      // Wallet state intentionally preserved across reset
    })
  },

  connectWallet: async () => {
    set({ walletConnecting: true, walletError: null })
    try {
      const freighterApi = await import('@stellar/freighter-api')
      const connected = await freighterApi.isConnected()
      if (!connected) {
        throw new Error('Freighter extension not found. Please install it from freighter.app')
      }
      await freighterApi.requestAccess()
      const publicKey = await freighterApi.getPublicKey()
      set({ walletAddress: publicKey, walletConnecting: false })
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to connect wallet'
      set({ walletError: message, walletConnecting: false })
    }
  },

  disconnectWallet: () => {
    set({ walletAddress: null, walletError: null })
  },

  loadTestFiles: () => {
    set({
      generatedFiles: {
        '/App.js': `import { useState } from 'react';

export default function App() {
  const [count, setCount] = useState(0);

  return (
    <div style={{
      minHeight: '100vh',
      background: '#0a0a0a',
      color: '#fff',
      padding: '2rem',
      fontFamily: 'system-ui, sans-serif'
    }}>
      <h1 style={{ marginBottom: '1rem' }}>Halo Preview Test</h1>
      <p style={{ marginBottom: '1rem' }}>If you see this, Sandpack is working!</p>
      <button
        onClick={() => setCount(c => c + 1)}
        style={{
          background: '#3b82f6',
          color: 'white',
          border: 'none',
          padding: '0.75rem 1.5rem',
          borderRadius: '8px',
          cursor: 'pointer',
          fontSize: '1rem'
        }}
      >
        Count: {count}
      </button>
    </div>
  );
}`,
      },
      contractId: 'TEST_CONTRACT_ID',
      buildStatus: 'complete',
    })
  },
}))

// Helper to handle build events
function handleBuildEvent(
  event: BuildEvent,
  actions: {
    setBuildStatus: (status: BuildStep) => void
    addBuildLog: (log: string) => void
    setGeneratedFiles: (files: Record<string, string>) => void
    setContractId: (id: string) => void
    setError: (error: string | null) => void
    addMessage: (role: Message['role'], content: string) => void
  }
) {
  const { setBuildStatus, addBuildLog, setGeneratedFiles, setContractId, setError, addMessage } = actions

  switch (event.step) {
    case 'analyzing':
      setBuildStatus('analyzing')
      if (event.message) addBuildLog(event.message)
      break

    case 'retrieving_docs':
      setBuildStatus('retrieving_docs')
      if (event.message) addBuildLog(event.message)
      break

    case 'generating_rust':
      setBuildStatus('generating_rust')
      if (event.message) addBuildLog(event.message)
      break

    case 'compiling':
      setBuildStatus('compiling')
      if (event.log) addBuildLog(event.log)
      break

    case 'deploying':
      setBuildStatus('deploying')
      if (event.message) addBuildLog(event.message)
      break

    case 'deployed':
      if (event.contract_id) {
        setContractId(event.contract_id)
        addBuildLog(`Contract deployed: ${event.contract_id}`)
      }
      break

    case 'generating_react':
      setBuildStatus('generating_react')
      if (event.message) addBuildLog(event.message)
      break

    case 'complete':
      setBuildStatus('complete')
      if (event.files) {
        setGeneratedFiles(event.files)
      }
      addMessage('assistant', 'Your DApp is ready! Check the preview panel.')
      break

    case 'error':
      setError(event.error || event.message || 'Unknown error')
      addMessage('system', `Error: ${event.error || event.message}`)
      break

    default:
      if (event.message) addBuildLog(event.message)
  }
}
