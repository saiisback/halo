// Wallet Bridge - PostMessage-based proxy for real Freighter wallet inside Sandpack iframe
// Replaces window.freighter with a bridge that forwards requests to the parent window

const walletBridgeTemplate = `
// ===== WALLET BRIDGE (LIVE MODE) =====
// Proxies wallet calls from Sandpack iframe to parent window's real Freighter extension

const WALLET_ADDRESS = '__WALLET_ADDRESS__';
let _requestId = 0;
const _pending = new Map();

// Listen for responses from parent
window.addEventListener('message', (event) => {
  if (event.data && event.data.type === 'HALO_WALLET_RESPONSE') {
    const { id, result, error } = event.data;
    const handler = _pending.get(id);
    if (handler) {
      _pending.delete(id);
      if (error) {
        handler.reject(new Error(error));
      } else {
        handler.resolve(result);
      }
    }
  }
});

function sendRequest(method, args) {
  return new Promise((resolve, reject) => {
    const id = ++_requestId;
    const timeout = method === 'signTransaction' || method === 'signAuthEntry' ? 120000 : 15000;

    const timer = setTimeout(() => {
      _pending.delete(id);
      reject(new Error('Wallet request timed out (' + method + ')'));
    }, timeout);

    _pending.set(id, {
      resolve: (val) => { clearTimeout(timer); resolve(val); },
      reject: (err) => { clearTimeout(timer); reject(err); },
    });

    window.parent.postMessage({
      type: 'HALO_WALLET_REQUEST',
      id,
      method,
      args: args || [],
    }, '*');
  });
}

if (typeof window !== 'undefined') {
  window.freighter = {
    isConnected: () => sendRequest('isConnected', []),
    setAllowed: () => sendRequest('setAllowed', []),
    getPublicKey: () => sendRequest('getPublicKey', []),
    getNetwork: () => sendRequest('getNetwork', []),
    getNetworkPassphrase: () => sendRequest('getNetworkPassphrase', []),
    signTransaction: (xdr, opts) => sendRequest('signTransaction', [xdr, opts]),
    signAuthEntry: (entry, opts) => sendRequest('signAuthEntry', [entry, opts]),
    _disconnect: () => sendRequest('_disconnect', []),
    _isMock: false,
    _isBridge: true,
  };

  window.freighterApi = window.freighter;

  console.log('%c[Live Wallet] Bridge active — connected to ' + WALLET_ADDRESS.slice(0, 4) + '...' + WALLET_ADDRESS.slice(-4), 'color: #4ade80; font-weight: bold');
}

export default {};
`;

export function getWalletBridgeScript(walletAddress: string): string {
  return walletBridgeTemplate.replace('__WALLET_ADDRESS__', walletAddress)
}
