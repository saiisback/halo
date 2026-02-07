import { useEffect } from 'react'

/**
 * Parent-side message handler for the wallet bridge.
 * Listens for HALO_WALLET_REQUEST messages from the Sandpack iframe
 * and routes them to the real Freighter extension.
 */
export function useWalletBridge(walletAddress: string | null) {
  useEffect(() => {
    if (!walletAddress) return

    const handler = async (event: MessageEvent) => {
      if (!event.data || event.data.type !== 'HALO_WALLET_REQUEST') return

      const { id, method, args } = event.data
      const source = event.source as Window | null
      if (!source) return

      try {
        let result: unknown

        switch (method) {
          case 'isConnected': {
            result = !!walletAddress
            break
          }
          case 'setAllowed': {
            result = true
            break
          }
          case 'getPublicKey': {
            result = walletAddress
            break
          }
          case 'getNetwork': {
            result = 'TESTNET'
            break
          }
          case 'getNetworkPassphrase': {
            result = 'Test SDF Network ; September 2015'
            break
          }
          case 'signTransaction': {
            const freighterApi = await import('@stellar/freighter-api')
            const signed = await freighterApi.signTransaction(args[0], args[1] || {})
            // Freighter v2 returns { signedTxXdr, signerAddress }; v1 returns plain string
            result = typeof signed === 'string' ? signed : signed.signedTxXdr ?? signed
            break
          }
          case 'signAuthEntry': {
            const freighterApi = await import('@stellar/freighter-api')
            const signed = await freighterApi.signAuthEntry(args[0], args[1] || {})
            // Freighter v2 returns { signedAuthEntry, signerAddress }; v1 returns plain string
            result = typeof signed === 'string' ? signed : signed.signedAuthEntry ?? signed
            break
          }
          default: {
            throw new Error(`Unknown wallet method: ${method}`)
          }
        }

        source.postMessage({
          type: 'HALO_WALLET_RESPONSE',
          id,
          result,
        }, '*')
      } catch (error) {
        source.postMessage({
          type: 'HALO_WALLET_RESPONSE',
          id,
          error: error instanceof Error ? error.message : 'Unknown wallet error',
        }, '*')
      }
    }

    window.addEventListener('message', handler)
    return () => window.removeEventListener('message', handler)
  }, [walletAddress])
}
