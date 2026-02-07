"""
Frontend React Component Templates

Pre-built components that can be composed by the React Agent.
These are injected into the Sandpack preview.
"""


def get_frontend_template() -> dict[str, str]:
    """Get base frontend template files"""
    return {
        "index_css": DEFAULT_CSS,
    }


def get_frontend_components() -> dict[str, str]:
    """Get pre-built React components"""
    return {
        "WalletConnect": WALLET_CONNECT_COMPONENT,
        "TxStatus": TX_STATUS_COMPONENT,
        "ContractForm": CONTRACT_FORM_COMPONENT,
        "BalanceDisplay": BALANCE_DISPLAY_COMPONENT,
    }


DEFAULT_CSS = """
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
  background: linear-gradient(135deg, #0a0a0a 0%, #1a1a2e 100%);
  color: #fafafa;
  min-height: 100vh;
}

.container {
  max-width: 640px;
  margin: 0 auto;
  padding: 2rem 1rem;
}

.card {
  background: rgba(26, 26, 46, 0.8);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 16px;
  padding: 1.5rem;
  margin-bottom: 1.5rem;
  box-shadow: 0 4px 30px rgba(0, 0, 0, 0.3);
}

.card-header {
  font-size: 1.25rem;
  font-weight: 600;
  margin-bottom: 1rem;
  color: #fff;
}

.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  background: linear-gradient(135deg, #3b82f6 0%, #8b5cf6 100%);
  color: white;
  border: none;
  padding: 0.875rem 1.75rem;
  border-radius: 10px;
  font-size: 1rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
  width: 100%;
}

.btn:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 4px 20px rgba(59, 130, 246, 0.4);
}

.btn:disabled {
  background: #404040;
  cursor: not-allowed;
  transform: none;
}

.btn-secondary {
  background: rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.2);
}

.btn-secondary:hover:not(:disabled) {
  background: rgba(255, 255, 255, 0.15);
  box-shadow: none;
}

.input {
  width: 100%;
  background: rgba(0, 0, 0, 0.3);
  border: 1px solid rgba(255, 255, 255, 0.15);
  color: white;
  padding: 0.875rem 1rem;
  border-radius: 10px;
  font-size: 1rem;
  margin-bottom: 1rem;
  transition: border-color 0.2s;
}

.input:focus {
  outline: none;
  border-color: #3b82f6;
}

.input::placeholder {
  color: rgba(255, 255, 255, 0.4);
}

.label {
  display: block;
  font-size: 0.875rem;
  color: rgba(255, 255, 255, 0.7);
  margin-bottom: 0.5rem;
}

.status {
  padding: 0.75rem 1rem;
  border-radius: 10px;
  font-size: 0.875rem;
  margin-top: 1rem;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.status.success {
  background: rgba(22, 163, 74, 0.2);
  border: 1px solid rgba(22, 163, 74, 0.3);
  color: #86efac;
}

.status.error {
  background: rgba(220, 38, 38, 0.2);
  border: 1px solid rgba(220, 38, 38, 0.3);
  color: #fca5a5;
}

.status.loading {
  background: rgba(59, 130, 246, 0.2);
  border: 1px solid rgba(59, 130, 246, 0.3);
  color: #93c5fd;
}

.text-muted {
  color: rgba(255, 255, 255, 0.5);
}

.text-small {
  font-size: 0.875rem;
}

.mb-1 { margin-bottom: 0.5rem; }
.mb-2 { margin-bottom: 1rem; }
.mb-3 { margin-bottom: 1.5rem; }
.mt-1 { margin-top: 0.5rem; }
.mt-2 { margin-top: 1rem; }

@keyframes spin {
  to { transform: rotate(360deg); }
}

.spinner {
  width: 16px;
  height: 16px;
  border: 2px solid transparent;
  border-top-color: currentColor;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}
"""


WALLET_CONNECT_COMPONENT = """
import { useState, useEffect } from 'react';

/**
 * WalletConnect - Freighter wallet connection button
 *
 * Shows connect button when disconnected, shows truncated address when connected.
 * Works with both real Freighter and the demo mock wallet.
 */
export function WalletConnect({ onConnect, onDisconnect }) {
  const [address, setAddress] = useState(null);
  const [isConnecting, setIsConnecting] = useState(false);
  const [error, setError] = useState(null);
  const [isDemoMode, setIsDemoMode] = useState(false);

  useEffect(() => {
    // Check if already connected
    checkConnection();
    // Check if this is demo mode
    setIsDemoMode(window.freighter?._isMock === true);
  }, []);

  const checkConnection = async () => {
    if (typeof window === 'undefined' || !window.freighter) return;

    try {
      const isConnected = await window.freighter.isConnected();
      if (isConnected) {
        const publicKey = await window.freighter.getPublicKey();
        setAddress(publicKey);
        onConnect?.(publicKey);
      }
    } catch (err) {
      console.error('Connection check failed:', err);
    }
  };

  const connect = async () => {
    if (!window.freighter) {
      setError('Wallet not available');
      return;
    }

    setIsConnecting(true);
    setError(null);

    try {
      await window.freighter.setAllowed();
      const publicKey = await window.freighter.getPublicKey();
      setAddress(publicKey);
      onConnect?.(publicKey);
    } catch (err) {
      setError(err.message || 'Connection failed');
    } finally {
      setIsConnecting(false);
    }
  };

  const disconnect = () => {
    setAddress(null);
    if (window.freighter?._disconnect) {
      window.freighter._disconnect();
    }
    onDisconnect?.();
  };

  const truncateAddress = (addr) => {
    if (!addr) return '';
    return addr.slice(0, 6) + '...' + addr.slice(-4);
  };

  if (address) {
    return (
      <div className="card" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '1rem' }}>
        <div style={{ minWidth: 0 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.25rem' }}>
            <span style={{
              width: '8px',
              height: '8px',
              borderRadius: '50%',
              background: '#4ade80',
              boxShadow: '0 0 8px rgba(74, 222, 128, 0.5)'
            }} />
            <span className="text-muted text-small">
              {isDemoMode ? 'Demo Wallet' : 'Connected'}
            </span>
          </div>
          <p style={{ fontFamily: 'monospace', fontSize: '0.9rem', margin: 0 }}>
            {truncateAddress(address)}
          </p>
        </div>
        <button className="btn btn-secondary" onClick={disconnect} style={{ width: 'auto', padding: '0.5rem 1rem' }}>
          Disconnect
        </button>
      </div>
    );
  }

  return (
    <div className="card">
      {isDemoMode && (
        <p className="text-muted text-small mb-2" style={{ textAlign: 'center' }}>
          Demo mode - wallet interactions are simulated
        </p>
      )}
      <button className="btn" onClick={connect} disabled={isConnecting}>
        {isConnecting ? (
          <>
            <span className="spinner" />
            Connecting...
          </>
        ) : (
          <>
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M21 12V7H5a2 2 0 0 1 0-4h14v4"/>
              <path d="M3 5v14a2 2 0 0 0 2 2h16v-5"/>
              <path d="M18 12a2 2 0 0 0 0 4h4v-4Z"/>
            </svg>
            Connect Wallet
          </>
        )}
      </button>
      {error && <p className="status error mt-1">{error}</p>}
    </div>
  );
}

export default WalletConnect;
"""


TX_STATUS_COMPONENT = """
import { useEffect, useState } from 'react';

/**
 * TxStatus - Transaction status toast notification
 * 
 * Shows the current status of a blockchain transaction.
 */
export function TxStatus({ status, txHash, onClose }) {
  const [visible, setVisible] = useState(true);

  useEffect(() => {
    if (status === 'confirmed' || status === 'failed') {
      const timer = setTimeout(() => {
        setVisible(false);
        onClose?.();
      }, 5000);
      return () => clearTimeout(timer);
    }
  }, [status, onClose]);

  if (!visible || !status) return null;

  const statusConfig = {
    preparing: { label: 'Preparing transaction...', className: 'loading' },
    signing: { label: 'Waiting for signature...', className: 'loading' },
    submitting: { label: 'Submitting to network...', className: 'loading' },
    confirmed: { label: 'Transaction confirmed!', className: 'success' },
    failed: { label: 'Transaction failed', className: 'error' },
  };

  const config = statusConfig[status] || { label: status, className: 'loading' };

  return (
    <div 
      className={`status ${config.className}`}
      style={{
        position: 'fixed',
        bottom: '1rem',
        right: '1rem',
        maxWidth: '300px',
        zIndex: 1000,
      }}
    >
      {config.label}
      {txHash && (
        <a 
          href={`https://stellar.expert/explorer/testnet/tx/${txHash}`}
          target="_blank"
          rel="noopener noreferrer"
          style={{ marginLeft: '0.5rem', color: 'inherit', textDecoration: 'underline' }}
        >
          View
        </a>
      )}
    </div>
  );
}

export default TxStatus;
"""


CONTRACT_FORM_COMPONENT = """
import { useState } from 'react';

/**
 * ContractForm - Dynamic form for contract interactions
 * 
 * Generates form fields based on the provided schema.
 */
export function ContractForm({ 
  fields, 
  onSubmit, 
  submitLabel = 'Submit',
  loading = false,
}) {
  const [values, setValues] = useState(
    fields.reduce((acc, field) => ({ ...acc, [field.name]: field.default || '' }), {})
  );

  const handleChange = (name, value) => {
    setValues(prev => ({ ...prev, [name]: value }));
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    onSubmit?.(values);
  };

  return (
    <form onSubmit={handleSubmit}>
      {fields.map((field) => (
        <div key={field.name} style={{ marginBottom: '1rem' }}>
          <label className="label">
            {field.label || field.name}
            {field.required && <span style={{ color: '#ef4444' }}> *</span>}
          </label>
          
          {field.type === 'textarea' ? (
            <textarea
              className="input"
              value={values[field.name]}
              onChange={(e) => handleChange(field.name, e.target.value)}
              placeholder={field.placeholder}
              required={field.required}
              rows={3}
              style={{ resize: 'vertical', minHeight: '80px' }}
            />
          ) : (
            <input
              className="input"
              type={field.type || 'text'}
              value={values[field.name]}
              onChange={(e) => handleChange(field.name, e.target.value)}
              placeholder={field.placeholder}
              required={field.required}
              min={field.min}
              max={field.max}
              step={field.step}
            />
          )}
          
          {field.hint && (
            <p className="text-muted text-small" style={{ marginTop: '0.25rem' }}>
              {field.hint}
            </p>
          )}
        </div>
      ))}
      
      <button className="btn" type="submit" disabled={loading}>
        {loading ? (
          <>
            <span className="spinner" />
            Processing...
          </>
        ) : (
          submitLabel
        )}
      </button>
    </form>
  );
}

export default ContractForm;
"""


BALANCE_DISPLAY_COMPONENT = """
import { useState, useEffect } from 'react';

/**
 * BalanceDisplay - Shows account balance with auto-refresh
 */
export function BalanceDisplay({ 
  address, 
  tokenSymbol = 'XLM',
  refreshInterval = 30000,
  onBalanceChange,
}) {
  const [balance, setBalance] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!address) {
      setBalance(null);
      setLoading(false);
      return;
    }

    const fetchBalance = async () => {
      try {
        setLoading(true);
        // In production, this would call the Stellar Horizon API
        // For demo, we simulate a balance
        await new Promise(resolve => setTimeout(resolve, 500));
        const mockBalance = (Math.random() * 1000).toFixed(2);
        setBalance(mockBalance);
        onBalanceChange?.(mockBalance);
        setError(null);
      } catch (err) {
        setError('Failed to fetch balance');
      } finally {
        setLoading(false);
      }
    };

    fetchBalance();
    
    if (refreshInterval > 0) {
      const interval = setInterval(fetchBalance, refreshInterval);
      return () => clearInterval(interval);
    }
  }, [address, refreshInterval, onBalanceChange]);

  if (!address) {
    return (
      <div className="card">
        <p className="text-muted">Connect wallet to see balance</p>
      </div>
    );
  }

  return (
    <div className="card">
      <p className="text-muted text-small mb-1">Balance</p>
      {loading ? (
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <span className="spinner" />
          <span>Loading...</span>
        </div>
      ) : error ? (
        <p style={{ color: '#fca5a5' }}>{error}</p>
      ) : (
        <p style={{ fontSize: '1.5rem', fontWeight: '600' }}>
          {balance} <span className="text-muted">{tokenSymbol}</span>
        </p>
      )}
    </div>
  );
}

export default BalanceDisplay;
"""
