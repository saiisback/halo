// useContract hook — injected as a string into Sandpack preview
// Handles both demo mode (mock wallet) and live mode (real Freighter via bridge)

export const useContractHook = `
import { useState, useCallback } from 'react';
import * as Stellar from '@stellar/stellar-sdk';
import { CONTRACT_ID, SOROBAN_RPC_URL, STELLAR_NETWORK } from '../lib/stellar';

const { Contract, TransactionBuilder, Networks, Address, nativeToScVal, scValToNative, xdr } = Stellar;
// Handle both old (v11 SorobanRpc) and new (v12+ rpc) SDK namespaces
const SorobanRpc = Stellar.rpc || Stellar.SorobanRpc;
console.log('[useContract] SDK loaded, rpc namespace:', SorobanRpc ? 'found' : 'MISSING');

const PASSPHRASE = STELLAR_NETWORK === 'testnet'
  ? Networks.TESTNET
  : 'Test SDF Future Network ; October 2022';

/**
 * Type wrapper helpers — use these in invoke/query calls to specify exact Soroban types.
 * This prevents type mismatches (e.g., sending i128 when contract expects u64).
 *
 * Usage:
 *   invoke('vote', { proposal_id: u64(1), voter: pubKey, approve: true })
 *   invoke('deposit', { from: pubKey, amount: i128(amount) })
 */
function u64(val) { return { __soroban_type: 'u64', value: val }; }
function i128(val) { return { __soroban_type: 'i128', value: val }; }
function u32(val) { return { __soroban_type: 'u32', value: val }; }
function sorobanString(val) { return { __soroban_type: 'string', value: val }; }
function sorobanBool(val) { return { __soroban_type: 'bool', value: val }; }
function sorobanSymbol(val) { return { __soroban_type: 'symbol', value: val }; }

// #region agent log
function _dbg(loc, msg, data, hId) { try { var p = {location:loc,message:msg,data:data,timestamp:Date.now(),hypothesisId:hId}; var s = JSON.stringify(p); console.warn('[DBG]', s); try{window.top.postMessage({type:'__dbg_log',payload:p},'*')}catch(e2){try{window.parent.postMessage({type:'__dbg_log',payload:p},'*')}catch(e3){}} } catch(e){ console.warn('[DBG-ERR]', loc, msg, e.message); } }
// #endregion

/**
 * Convert a JS value to a Soroban ScVal.
 * Handles typed wrappers (u64, i128, etc.) and uses smart heuristics for unwrapped values.
 */
function toScVal(value) {
  // #region agent log
  _dbg('toScVal','entry',{valueType:typeof value,isSymbol:typeof value==='symbol',repr:typeof value==='symbol'?('SYM:'+String(value.description)):(typeof value==='object'?(value?(value.__soroban_type||'obj:'+Object.keys(value).join(',')):'null'):String(value).substring(0,100))},'H1');
  // #endregion
  if (value === null || value === undefined) {
    return xdr.ScVal.scvVoid();
  }

  // Handle typed wrappers from u64(), i128(), sorobanSymbol(), etc.
  if (value && typeof value === 'object' && value.__soroban_type) {
    const raw = value.value;
    switch (value.__soroban_type) {
      case 'u64':
        return nativeToScVal(Number(raw), { type: 'u64' });
      case 'u32':
        return nativeToScVal(Number(raw), { type: 'u32' });
      case 'i128':
        return nativeToScVal(BigInt(String(raw).trim()), { type: 'i128' });
      case 'string':
        return nativeToScVal(String(raw), { type: 'string' });
      case 'symbol':
        return xdr.ScVal.scvSymbol(String(raw));
      case 'bool':
        return nativeToScVal(Boolean(raw));
      default:
        return nativeToScVal(raw);
    }
  }

  // Stellar public key (G...) or contract ID (C...)
  if (typeof value === 'string' && /^[GC][A-Z2-7]{55}$/.test(value)) {
    return new Address(value).toScVal();
  }
  // Boolean
  if (typeof value === 'boolean') {
    return nativeToScVal(value);
  }
  // JavaScript Symbol → Soroban Symbol (e.g., Symbol('Heads') → scvSymbol('Heads'))
  if (typeof value === 'symbol') {
    return xdr.ScVal.scvSymbol(value.description || '');
  }
  // BigInt → i128
  if (typeof value === 'bigint') {
    return nativeToScVal(value, { type: 'i128' });
  }
  // Number (typeof number) → u64 (most contract IDs, counts, timestamps are u64)
  if (typeof value === 'number') {
    if (Number.isInteger(value) && value >= 0) {
      return nativeToScVal(value, { type: 'u64' });
    }
    return nativeToScVal(BigInt(Math.floor(value)), { type: 'i128' });
  }
  // Numeric string → i128 (these come from input fields, likely amounts)
  if (typeof value === 'string' && /^-?\\d+$/.test(value.trim())) {
    return nativeToScVal(BigInt(value.trim()), { type: 'i128' });
  }
  // Any other string → Soroban String
  if (typeof value === 'string') {
    return nativeToScVal(value, { type: 'string' });
  }
  // Array → Soroban Vec
  if (Array.isArray(value)) {
    return xdr.ScVal.scvVec(value.map(toScVal));
  }
  // Fallback — graceful: try nativeToScVal, fall back to string conversion
  // #region agent log
  _dbg('toScVal','FALLBACK-HIT',{valueType:typeof value,ctorName:value&&value.constructor?value.constructor.name:'N/A'},'H1');
  // #endregion
  try {
    return nativeToScVal(value);
  } catch (e) {
    // Last resort: convert to string to avoid crash
    return nativeToScVal(String(value), { type: 'string' });
  }
}

/**
 * Convert a Soroban ScVal back to a JS-friendly value.
 */
function fromScVal(val) {
  try {
    const native = scValToNative(val);
    // BigInt → string for display
    if (typeof native === 'bigint') return native.toString();
    return native;
  } catch {
    return String(val);
  }
}

/**
 * Custom hook for interacting with deployed Soroban contracts.
 * Auto-detects demo mode (mock wallet) vs live mode (real Freighter).
 */
export function useContract(contractId = CONTRACT_ID) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [txStatus, setTxStatus] = useState(null);

  const isMock = () => window.freighter && window.freighter._isMock === true;

  const checkWallet = useCallback(async () => {
    if (typeof window === 'undefined') return false;
    if (!window.freighter) {
      setError('Please install Freighter wallet');
      return false;
    }
    try {
      const connected = await window.freighter.isConnected();
      if (!connected) {
        setError('Please connect your Freighter wallet');
        return false;
      }
      return true;
    } catch (err) {
      setError('Failed to connect to wallet');
      return false;
    }
  }, []);

  const getPublicKey = useCallback(async () => {
    if (!await checkWallet()) return null;
    try {
      return await window.freighter.getPublicKey();
    } catch (err) {
      setError('Failed to get public key');
      return null;
    }
  }, [checkWallet]);

  /**
   * Invoke a contract method (write operation — builds tx, signs via Freighter, submits).
   */
  const invoke = useCallback(async (method, args = {}) => {
    setLoading(true);
    setError(null);
    setTxStatus('preparing');

    try {
      if (!await checkWallet()) {
        setLoading(false);
        setTxStatus(null);
        return null;
      }

      const publicKey = await window.freighter.getPublicKey();
      if (!publicKey) {
        setLoading(false);
        setTxStatus(null);
        return null;
      }

      // ── Demo mode: simulate everything ──
      if (isMock()) {
        console.log('%c[Demo] invoke:', 'color: #60a5fa', method, args);
        setTxStatus('signing');
        await new Promise(r => setTimeout(r, 800));
        setTxStatus('submitting');
        await new Promise(r => setTimeout(r, 700));
        setTxStatus('confirmed');
        setLoading(false);
        return { success: true, method, args };
      }

      // ── Live mode: real Soroban transaction ──
      console.log('%c[Live] invoke:', 'color: #4ade80', method, args);
      // #region agent log
      var _ai = {}; try{Object.keys(args).forEach(function(k){var v=args[k]; _ai[k]={type:typeof v,isSymbol:typeof v==='symbol',repr:typeof v==='symbol'?('SYM:'+String(v.description)):(typeof v==='object'?(v?JSON.stringify(v).substring(0,100):'null'):String(v).substring(0,80))};})}catch(ex){_ai._err=ex.message;}
      _dbg('invoke','called',{method:method,argKeys:Object.keys(args),argDetails:_ai},'H5');
      // #endregion

      const server = new SorobanRpc.Server(SOROBAN_RPC_URL);
      const account = await server.getAccount(publicKey);
      const contract = new Contract(contractId);

      // Convert args to ScVal (positional, in insertion order)
      const scArgs = Object.values(args).map(toScVal);

      // Build transaction
      let tx = new TransactionBuilder(account, {
        fee: '10000000',
        networkPassphrase: PASSPHRASE,
      })
        .addOperation(contract.call(method, ...scArgs))
        .setTimeout(30)
        .build();

      // Simulate to get auth + resource estimates
      const sim = await server.simulateTransaction(tx);
      if (sim.error) {
        throw new Error('Simulation failed: ' + sim.error);
      }
      if (SorobanRpc.Api.isSimulationError(sim)) {
        throw new Error('Simulation error: ' + JSON.stringify(sim.error));
      }

      // Assemble with auth entries from simulation
      const assembled = SorobanRpc.assembleTransaction(tx, sim);
      const prepared = typeof assembled.build === 'function' ? assembled.build() : assembled;

      // Sign via Freighter (or bridge to real Freighter)
      setTxStatus('signing');
      const signResult = await window.freighter.signTransaction(
        prepared.toXDR(),
        { networkPassphrase: PASSPHRASE }
      );
      // Freighter v2 returns { signedTxXdr, signerAddress }; v1/bridge returns plain string
      const signedXdr = typeof signResult === 'object' && signResult !== null && signResult.signedTxXdr
        ? signResult.signedTxXdr
        : signResult;

      // Submit to network
      setTxStatus('submitting');
      const signedTx = TransactionBuilder.fromXDR(signedXdr, PASSPHRASE);
      const sent = await server.sendTransaction(signedTx);

      if (sent.status === 'ERROR') {
        throw new Error('Transaction rejected by network');
      }

      // Poll for confirmation (up to 30s)
      let result;
      for (let i = 0; i < 30; i++) {
        await new Promise(r => setTimeout(r, 1000));
        result = await server.getTransaction(sent.hash);
        if (result.status !== 'NOT_FOUND') break;
      }

      if (result && result.status === 'SUCCESS') {
        setTxStatus('confirmed');
        setLoading(false);
        const retVal = result.returnValue ? fromScVal(result.returnValue) : null;
        return { success: true, hash: sent.hash, value: retVal };
      }

      throw new Error('Transaction ' + (result ? result.status : 'timed out'));
    } catch (err) {
      // #region agent log
      _dbg('invoke','ERROR',{method:method,errMsg:err.message,errName:err.name,errStack:err.stack?err.stack.substring(0,500):'none'},'H4');
      console.error('[useContract] invoke FAILED — method:', method, '| error:', err.message, '| args:', JSON.stringify(Object.keys(args)), '| stack:', err.stack);
      // #endregion
      setError(err.message || 'Transaction failed');
      setTxStatus('failed');
      setLoading(false);
      return null;
    }
  }, [contractId, checkWallet]);

  /**
   * Query contract state (read-only — simulate only, no signing needed).
   */
  const query = useCallback(async (method, args = {}) => {
    setLoading(true);
    setError(null);

    try {
      // ── Demo mode: return mock data ──
      if (isMock()) {
        console.log('%c[Demo] query:', 'color: #60a5fa', method, args);
        await new Promise(r => setTimeout(r, 400));
        setLoading(false);
        if (method.toLowerCase().includes('balance') || method.toLowerCase().includes('amount')) {
          return { value: '1000' };
        }
        if (method.toLowerCase().includes('count')) {
          return { value: '42' };
        }
        if (method.toLowerCase().includes('campaign') || method.toLowerCase().includes('proposal')) {
          return { value: { id: 1, active: true } };
        }
        return { success: true, value: '0' };
      }

      // ── Live mode: simulate to read state ──
      console.log('%c[Live] query:', 'color: #4ade80', method, args);

      let sourceKey;
      try {
        sourceKey = await window.freighter.getPublicKey();
      } catch {
        sourceKey = null;
      }

      if (!sourceKey) {
        setLoading(false);
        setError('Connect wallet to query contract state');
        return null;
      }

      const server = new SorobanRpc.Server(SOROBAN_RPC_URL);
      const account = await server.getAccount(sourceKey);
      const contract = new Contract(contractId);

      const scArgs = Object.values(args).map(toScVal);
      const tx = new TransactionBuilder(account, {
        fee: '100',
        networkPassphrase: PASSPHRASE,
      })
        .addOperation(contract.call(method, ...scArgs))
        .setTimeout(30)
        .build();

      const sim = await server.simulateTransaction(tx);
      if (sim.error) {
        throw new Error('Query failed: ' + sim.error);
      }

      // Extract return value from simulation
      let retVal = null;
      if (sim.result && sim.result.retval) {
        retVal = fromScVal(sim.result.retval);
      }

      setLoading(false);
      return { success: true, value: retVal };
    } catch (err) {
      console.error('[useContract] query error:', err);
      setError(err.message || 'Query failed');
      setLoading(false);
      return null;
    }
  }, [contractId]);

  return {
    invoke,
    query,
    loading,
    error,
    txStatus,
    contractId,
    checkWallet,
    getPublicKey,
    // Type helpers for explicit Soroban type conversion
    u64,
    i128,
    u32,
    sorobanSymbol,
  };
}

// Also export type helpers at module level for direct import
export { u64, i128, u32, sorobanString, sorobanBool, sorobanSymbol };
export default useContract;
`;
