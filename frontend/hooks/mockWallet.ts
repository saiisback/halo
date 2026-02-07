// Mock Wallet - Simulates Freighter wallet for Sandpack preview
// This allows the preview to demonstrate wallet interactions without actual browser extension

export const mockWalletScript = `
// ===== MOCK FREIGHTER WALLET =====
// This simulates the Freighter browser extension API for preview purposes

// Demo wallet address (valid Stellar testnet format)
const DEMO_PUBLIC_KEY = 'GDEMO7ZJVTF6TVHREEUX4TQUJGFI57MNSEO2FGCXYFGDGUBXPIOQ7HAL';

// Mock wallet state
let isAllowed = false;
let isConnectedState = false;

// Create mock freighter object
if (typeof window !== 'undefined') {
  window.freighter = {
    // Check if user has allowed this site
    isConnected: async () => {
      return isConnectedState;
    },

    // Request permission to connect
    setAllowed: async () => {
      // Simulate user clicking "Allow" after a short delay
      await new Promise(resolve => setTimeout(resolve, 800));
      isAllowed = true;
      isConnectedState = true;
      console.log('%c[Demo Wallet] Connected!', 'color: #4ade80; font-weight: bold');
      return true;
    },

    // Get the public key
    getPublicKey: async () => {
      if (!isConnectedState) {
        throw new Error('Wallet not connected');
      }
      return DEMO_PUBLIC_KEY;
    },

    // Get network details
    getNetwork: async () => {
      return 'TESTNET';
    },

    // Get network passphrase
    getNetworkPassphrase: async () => {
      return 'Test SDF Network ; September 2015';
    },

    // Sign a transaction (mock)
    signTransaction: async (xdr, opts = {}) => {
      if (!isConnectedState) {
        throw new Error('Wallet not connected');
      }

      console.log('%c[Demo Wallet] Signing transaction...', 'color: #60a5fa');

      // Simulate signing delay
      await new Promise(resolve => setTimeout(resolve, 1000));

      console.log('%c[Demo Wallet] Transaction signed (simulated)', 'color: #4ade80');
      return xdr;
    },

    // Sign an authorization entry (mock)
    signAuthEntry: async (authEntry, opts = {}) => {
      if (!isConnectedState) {
        throw new Error('Wallet not connected');
      }

      console.log('%c[Demo Wallet] Signing auth entry...', 'color: #60a5fa');
      await new Promise(resolve => setTimeout(resolve, 500));
      return authEntry;
    },

    // Disconnect (for testing)
    _disconnect: () => {
      isConnectedState = false;
      isAllowed = false;
      console.log('%c[Demo Wallet] Disconnected', 'color: #fbbf24');
    },

    // Check if this is a mock wallet
    _isMock: true,
  };

  // Also set up freighterApi for newer SDK versions
  window.freighterApi = window.freighter;

  console.log('%c[Demo Wallet] Initialized - Click "Connect Wallet" to try it!', 'color: #a78bfa; font-weight: bold');
  console.log('%c[Demo Wallet] Address: ' + DEMO_PUBLIC_KEY, 'color: #737373');
}

export default {};
`;

// Helper to check if mock wallet is active
export const isMockWallet = `
export function isMockWallet() {
  return typeof window !== 'undefined' && window.freighter?._isMock === true;
}
`;
