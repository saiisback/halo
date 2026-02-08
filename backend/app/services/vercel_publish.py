"""
Vercel Publish Service

Turns the generated Sandpack React files (App.js, index.css, components/*)
into a deployable Vite React project and deploys it to Vercel using the
Deployments API (inlined files).
"""

from __future__ import annotations

import re
import uuid
from typing import Any, TypedDict

import httpx

from app.core.config import settings


class PublishResult(TypedDict):
    success: bool
    url: str | None
    deployment_id: str | None
    project_id: str | None
    vercel_status_code: int | None
    error: str | None


_NETWORKS: dict[str, dict[str, str]] = {
    "testnet": {
        "horizon_url": "https://horizon-testnet.stellar.org",
        "soroban_rpc_url": "https://soroban-testnet.stellar.org",
    },
    "futurenet": {
        "horizon_url": "https://horizon-futurenet.stellar.org",
        "soroban_rpc_url": "https://rpc-futurenet.stellar.org",
    },
}


# Guardrails — keep requests bounded
MAX_INPUT_FILES = 200
MAX_TOTAL_BYTES = 2_000_000  # 2 MB of UTF-8 text


def _sanitize_deployment_name(name: str) -> str:
    """
    Vercel deployment "name" becomes part of URL. Keep it short and safe.
    """
    name = (name or "").strip().lower()
    name = re.sub(r"[^a-z0-9-]+", "-", name)
    name = re.sub(r"-{2,}", "-", name).strip("-")
    return name[:48] or "halo-dapp"

def _unique_name(base: str) -> str:
    """
    Create a Vercel-safe name with a short unique suffix.
    Avoids claim-transfer failures when the target team already has the base name.
    """
    base = _sanitize_deployment_name(base)
    suffix = uuid.uuid4().hex[:6]
    # Leave room for suffix and dash
    trimmed = base[: max(0, 48 - (1 + len(suffix)))]
    trimmed = trimmed.rstrip("-") or "halo-dapp"
    return f"{trimmed}-{suffix}"


def _strip_leading_slash(path: str) -> str:
    return path[1:] if path.startswith("/") else path


def _estimate_total_bytes(file_map: dict[str, str]) -> int:
    total = 0
    for _, content in file_map.items():
        total += len(content.encode("utf-8", errors="ignore"))
    return total


def _build_stellar_constants(contract_id: str, network: str) -> str:
    net = _NETWORKS.get(network, _NETWORKS["testnet"])
    horizon = net["horizon_url"]
    rpc = net["soroban_rpc_url"]
    # Keep API compatible with the preview version (frontend/components/preview/SandpackPreview.tsx)
    return (
        f"export const STELLAR_NETWORK = '{network}';\n"
        f"export const CONTRACT_ID = '{contract_id}';\n"
        f"export const HORIZON_URL = '{horizon}';\n"
        f"export const SOROBAN_RPC_URL = '{rpc}';\n"
        "export const IS_LIVE_WALLET = true;\n"
        "export const WALLET_ADDRESS = '';\n"
    )


def _use_contract_hook_source() -> str:
    """
    Runtime Soroban hook used by published apps.

    This is adapted from frontend/hooks/useContract.ts (preview hook), but as
    a real JS module (not a template string).
    """
    return """import { useState, useCallback } from 'react';
import * as Stellar from '@stellar/stellar-sdk';
import { CONTRACT_ID, SOROBAN_RPC_URL, STELLAR_NETWORK } from '../lib/stellar';

const { Contract, TransactionBuilder, Networks, Address, nativeToScVal, scValToNative, xdr } = Stellar;
// Handle both old (v11 SorobanRpc) and new (v12+ rpc) SDK namespaces
const SorobanRpc = Stellar.rpc || Stellar.SorobanRpc;

const PASSPHRASE = STELLAR_NETWORK === 'testnet'
  ? Networks.TESTNET
  : 'Test SDF Future Network ; October 2022';

function u64(val) { return { __soroban_type: 'u64', value: val }; }
function i128(val) { return { __soroban_type: 'i128', value: val }; }
function u32(val) { return { __soroban_type: 'u32', value: val }; }
function sorobanSymbol(val) { return { __soroban_type: 'symbol', value: val }; }

function toScVal(value) {
  if (value === null || value === undefined) {
    return xdr.ScVal.scvVoid();
  }

  if (value && typeof value === 'object' && value.__soroban_type) {
    const raw = value.value;
    switch (value.__soroban_type) {
      case 'u64':
        return nativeToScVal(Number(raw), { type: 'u64' });
      case 'u32':
        return nativeToScVal(Number(raw), { type: 'u32' });
      case 'i128':
        return nativeToScVal(BigInt(String(raw).trim()), { type: 'i128' });
      case 'symbol':
        return xdr.ScVal.scvSymbol(String(raw));
      default:
        return nativeToScVal(raw);
    }
  }

  // Stellar public key (G...) or contract ID (C...)
  if (typeof value === 'string' && /^[GC][A-Z2-7]{55}$/.test(value)) {
    return new Address(value).toScVal();
  }
  if (typeof value === 'boolean') {
    return nativeToScVal(value);
  }
  if (typeof value === 'bigint') {
    return nativeToScVal(value, { type: 'i128' });
  }
  if (typeof value === 'number') {
    if (Number.isInteger(value) && value >= 0) {
      return nativeToScVal(value, { type: 'u64' });
    }
    return nativeToScVal(BigInt(Math.floor(value)), { type: 'i128' });
  }
  if (typeof value === 'string' && /^-?\\d+$/.test(value.trim())) {
    return nativeToScVal(BigInt(value.trim()), { type: 'i128' });
  }
  if (typeof value === 'string') {
    return nativeToScVal(value, { type: 'string' });
  }
  if (Array.isArray(value)) {
    return xdr.ScVal.scvVec(value.map(toScVal));
  }
  try {
    return nativeToScVal(value);
  } catch {
    return nativeToScVal(String(value), { type: 'string' });
  }
}

function fromScVal(val) {
  try {
    const native = scValToNative(val);
    if (typeof native === 'bigint') return native.toString();
    return native;
  } catch {
    return String(val);
  }
}

export function useContract(contractId = CONTRACT_ID) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [txStatus, setTxStatus] = useState(null);

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
    } catch {
      setError('Failed to connect to wallet');
      return false;
    }
  }, []);

  const getPublicKey = useCallback(async () => {
    if (!await checkWallet()) return null;
    try {
      return await window.freighter.getPublicKey();
    } catch {
      setError('Failed to get public key');
      return null;
    }
  }, [checkWallet]);

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

      const server = new SorobanRpc.Server(SOROBAN_RPC_URL);
      const account = await server.getAccount(publicKey);
      const contract = new Contract(contractId);

      const scArgs = Object.values(args).map(toScVal);

      let tx = new TransactionBuilder(account, {
        fee: '10000000',
        networkPassphrase: PASSPHRASE,
      })
        .addOperation(contract.call(method, ...scArgs))
        .setTimeout(30)
        .build();

      const sim = await server.simulateTransaction(tx);
      if (sim.error) throw new Error('Simulation failed: ' + sim.error);
      if (SorobanRpc.Api && SorobanRpc.Api.isSimulationError && SorobanRpc.Api.isSimulationError(sim)) {
        throw new Error('Simulation error: ' + JSON.stringify(sim.error));
      }

      const assembled = SorobanRpc.assembleTransaction ? SorobanRpc.assembleTransaction(tx, sim) : tx;
      const prepared = typeof assembled.build === 'function' ? assembled.build() : assembled;

      setTxStatus('signing');
      const signResult = await window.freighter.signTransaction(
        prepared.toXDR(),
        { networkPassphrase: PASSPHRASE }
      );
      const signedXdr = typeof signResult === 'object' && signResult !== null && signResult.signedTxXdr
        ? signResult.signedTxXdr
        : signResult;

      setTxStatus('submitting');
      const signedTx = TransactionBuilder.fromXDR(signedXdr, PASSPHRASE);
      const sent = await server.sendTransaction(signedTx);
      if (sent.status === 'ERROR') throw new Error('Transaction rejected by network');

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
      console.error('[useContract] invoke error:', err);
      setError(err?.message || 'Transaction failed');
      setTxStatus('failed');
      setLoading(false);
      return null;
    }
  }, [contractId, checkWallet]);

  const query = useCallback(async (method, args = {}) => {
    setLoading(true);
    setError(null);

    try {
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
      if (sim.error) throw new Error('Query failed: ' + sim.error);

      let retVal = null;
      if (sim.result && sim.result.retval) {
        retVal = fromScVal(sim.result.retval);
      }

      setLoading(false);
      return { success: true, value: retVal };
    } catch (err) {
      console.error('[useContract] query error:', err);
      setError(err?.message || 'Query failed');
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
    u64,
    i128,
    u32,
    sorobanSymbol,
  };
}

export default useContract;
export { u64, i128, u32, sorobanSymbol };
"""


def build_vite_project_files(
    *,
    generated_files: dict[str, str],
    contract_id: str,
    network: str = "testnet",
) -> dict[str, str]:
    """
    Convert Sandpack-style files to a Vite project file map.
    Returns {path: content} where path is relative (no leading slash).
    """
    if not isinstance(generated_files, dict):
        raise ValueError("files must be an object of {path: content}")

    if len(generated_files) > MAX_INPUT_FILES:
        raise ValueError(f"too many files (max {MAX_INPUT_FILES})")

    total_bytes = _estimate_total_bytes(generated_files)
    if total_bytes > MAX_TOTAL_BYTES:
        raise ValueError(f"files too large (max {MAX_TOTAL_BYTES} bytes)")

    # Normalize keys
    normalized: dict[str, str] = {}
    for k, v in generated_files.items():
        if not isinstance(k, str) or not isinstance(v, str):
            continue
        normalized[_strip_leading_slash(k)] = v

    app_src = normalized.get("App.js") or normalized.get("App.jsx")
    if not app_src:
        raise ValueError("missing App.js in generated files")

    index_css = normalized.get("index.css", "")

    # Map Sandpack root files to src/
    out: dict[str, str] = {}

    # Vite scaffolding
    out["package.json"] = (
        "{\n"
        f'  "name": "{_sanitize_deployment_name(contract_id)}",\n'
        '  "private": true,\n'
        '  "version": "0.0.0",\n'
        '  "type": "module",\n'
        '  "scripts": {\n'
        '    "dev": "vite",\n'
        '    "build": "vite build",\n'
        '    "preview": "vite preview --host 0.0.0.0 --port 4173"\n'
        "  },\n"
        '  "dependencies": {\n'
        '    "react": "^18.2.0",\n'
        '    "react-dom": "^18.2.0",\n'
        '    "@stellar/freighter-api": "^2.0.0",\n'
        '    "@stellar/stellar-sdk": "14.4.3"\n'
        "  },\n"
        '  "devDependencies": {\n'
        '    "@vitejs/plugin-react": "^4.3.1",\n'
        '    "vite": "^5.4.0"\n'
        "  }\n"
        "}\n"
    )

    out["vite.config.js"] = (
        "import { defineConfig } from 'vite';\n"
        "import react from '@vitejs/plugin-react';\n"
        "\n"
        "export default defineConfig({\n"
        "  plugins: [react()],\n"
        "});\n"
    )

    out["index.html"] = (
        "<!doctype html>\n"
        "<html lang=\"en\">\n"
        "  <head>\n"
        "    <meta charset=\"UTF-8\" />\n"
        "    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\" />\n"
        "    <title>Halo DApp</title>\n"
        "  </head>\n"
        "  <body>\n"
        "    <div id=\"root\"></div>\n"
        "    <script type=\"module\" src=\"/src/main.jsx\"></script>\n"
        "  </body>\n"
        "</html>\n"
    )

    out["src/main.jsx"] = (
        "import React from 'react';\n"
        "import ReactDOM from 'react-dom/client';\n"
        "import { WalletBar } from './components/WalletBar.jsx';\n"
        "import App from './App.jsx';\n"
        "import './index.css';\n"
        "\n"
        "ReactDOM.createRoot(document.getElementById('root')).render(\n"
        "  <React.StrictMode>\n"
        "    <>\n"
        "      <WalletBar />\n"
        "      <App />\n"
        "    </>\n"
        "  </React.StrictMode>\n"
        ");\n"
    )

    # Always include a wallet connect bar in published apps (preview had mock wallet).
    out["src/components/WalletBar.jsx"] = """import { useEffect, useState } from 'react';
import { isConnected, requestAccess, getPublicKey } from '@stellar/freighter-api';

function truncate(addr) {
  if (!addr) return '';
  return `${addr.slice(0, 4)}...${addr.slice(-4)}`;
}

export function WalletBar() {
  const [address, setAddress] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    (async () => {
      try {
        const ok = await isConnected();
        if (ok) {
          const pk = await getPublicKey();
          setAddress(pk);
        }
      } catch {
        // ignore
      }
    })();
  }, []);

  const connect = async () => {
    setLoading(true);
    setError(null);
    try {
      await requestAccess();
      const pk = await getPublicKey();
      setAddress(pk);
    } catch (e) {
      setError(e?.message || 'Failed to connect wallet');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{
      position: 'sticky',
      top: 0,
      zIndex: 50,
      width: '100%',
      padding: '10px 12px',
      background: 'rgba(10, 10, 10, 0.85)',
      borderBottom: '1px solid rgba(255,255,255,0.08)',
      backdropFilter: 'blur(8px)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      gap: 12,
      fontFamily: 'system-ui, -apple-system, Segoe UI, Roboto, sans-serif',
      color: 'rgba(255,255,255,0.92)'
    }}>
      <div style={{ fontSize: 12, opacity: 0.9 }}>Freighter Wallet</div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
        {error && <div style={{ fontSize: 12, color: '#fca5a5', maxWidth: 320, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{error}</div>}
        {address ? (
          <div style={{ fontSize: 12, fontFamily: 'ui-monospace, SFMono-Regular, Menlo, monospace', opacity: 0.95 }}>Connected: {truncate(address)}</div>
        ) : (
          <button
            onClick={connect}
            disabled={loading}
            style={{
              fontSize: 12,
              padding: '8px 10px',
              borderRadius: 10,
              border: '1px solid rgba(255,255,255,0.15)',
              background: 'rgba(255,255,255,0.06)',
              color: 'rgba(255,255,255,0.92)',
              cursor: loading ? 'not-allowed' : 'pointer'
            }}
          >
            {loading ? 'Connecting…' : 'Connect'}
          </button>
        )}
      </div>
    </div>
  );
}
"""

    out["src/App.jsx"] = app_src
    out["src/index.css"] = index_css
    out["src/hooks/useContract.js"] = _use_contract_hook_source()
    out["src/lib/stellar.js"] = _build_stellar_constants(contract_id, network)

    # Pass-through components (Sandpack uses /components/* at root)
    for path, content in normalized.items():
        if path.startswith("components/"):
            out[f"src/{path}"] = content

    return out


async def publish_to_vercel(
    *,
    name: str,
    generated_files: dict[str, str],
    contract_id: str,
    network: str = "testnet",
    access_token_override: str | None = None,
    unique_project_name: bool = False,
) -> PublishResult:
    """
    Deploy the given generated files to Vercel and return the deployment URL.
    """
    token = (access_token_override or "").strip() or settings.vercel_api_token
    if not token:
        return PublishResult(
            success=False,
            url=None,
            deployment_id=None,
            project_id=None,
            vercel_status_code=None,
            error="Missing Vercel access token (user not connected, and no VERCEL_API_TOKEN configured)",
        )

    safe_name = _unique_name(name) if unique_project_name else (_sanitize_deployment_name(name) if name else "halo-dapp")
    vite_files = build_vite_project_files(
        generated_files=generated_files,
        contract_id=contract_id,
        network=network,
    )

    # Vercel expects a list of {file, data}
    inlined_files: list[dict[str, Any]] = []
    for file_path, data in vite_files.items():
        inlined_files.append({"file": file_path, "data": data})

    params: dict[str, str] = {"skipAutoDetectionConfirmation": "1"}
    # If using platform token, optionally deploy under a team.
    # If using a user token (personal account flow), do not force a teamId.
    if not access_token_override and settings.vercel_team_id:
        params["teamId"] = settings.vercel_team_id

    body: dict[str, Any] = {
        "name": safe_name,
        "files": inlined_files,
        "projectSettings": {
            "framework": "vite",
            "installCommand": "npm install",
            "buildCommand": "npm run build",
            "outputDirectory": "dist",
        },
    }

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                "https://api.vercel.com/v13/deployments",
                params=params,
                headers=headers,
                json=body,
            )
    except Exception as e:
        return PublishResult(
            success=False,
            url=None,
            deployment_id=None,
            project_id=None,
            vercel_status_code=None,
            error=str(e),
        )

    if resp.status_code >= 400:
        return PublishResult(
            success=False,
            url=None,
            deployment_id=None,
            project_id=None,
            vercel_status_code=resp.status_code,
            error=f"Vercel API error ({resp.status_code}): {resp.text[:2000]}",
        )

    data = resp.json()
    return PublishResult(
        success=True,
        url=data.get("url"),
        deployment_id=data.get("id"),
        project_id=data.get("projectId") or (data.get("project", {}) or {}).get("id"),
        vercel_status_code=None,
        error=None,
    )


class TransferRequestResult(TypedDict):
    success: bool
    code: str | None
    vercel_status_code: int | None
    error: str | None


async def create_project_transfer_request(
    *,
    project_id_or_name: str,
    bearer_token: str,
) -> TransferRequestResult:
    """
    Create a project transfer request code (Claim Deployments flow).
    """
    params: dict[str, str] = {}
    if settings.vercel_team_id:
        params["teamId"] = settings.vercel_team_id

    headers = {"Authorization": f"Bearer {bearer_token}"}
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"https://api.vercel.com/projects/{project_id_or_name}/transfer-request",
                params=params,
                headers=headers,
                json={},
            )
    except Exception as e:
        return TransferRequestResult(success=False, code=None, vercel_status_code=None, error=str(e))

    if resp.status_code >= 400:
        return TransferRequestResult(
            success=False,
            code=None,
            vercel_status_code=resp.status_code,
            error=f"Vercel transfer-request error ({resp.status_code}): {resp.text[:2000]}",
        )

    data = resp.json()
    return TransferRequestResult(success=True, code=data.get("code"), vercel_status_code=None, error=None)


def build_claim_url(*, code: str, return_url: str) -> str:
    """
    Build a Vercel claim-deployment URL.
    """
    from urllib.parse import quote

    # Keep it simple: Vercel will handle validation and redirect to returnUrl if invalid/expired.
    return f"https://vercel.com/claim-deployment?code={quote(code, safe='')}&returnUrl={quote(return_url, safe='')}"

