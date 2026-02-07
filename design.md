Here is the comprehensive **Design Document (`design.md`)** for **Halo**.

This file is intended to live in the root of your repository. It serves as the single source of truth for your architecture, data flow, and technical decisions.

---

# `design.md`

# 😇 Halo: The Text-to-DApp Engine

**Version:** 1.0.0
**Status:** Architecture Draft
**Target Network:** Stellar (Soroban)

## 1. Executive Summary

**Halo** is a web-based SaaS platform that enables users to build, deploy, and interact with Decentralized Applications (DApps) on the Stellar network using natural language.

Unlike standard code generators, Halo acts as a full-cycle **DevOps Engine**:

1. **Writes** secure Soroban (Rust) smart contracts.
2. **Compiles** them in a secure cloud sandbox.
3. **Deploys** them to the Stellar Testnet/Mainnet.
4. **Generates** a React frontend connected to that live contract.
5. **Previews** the result instantly in the browser.

---

## 2. System Architecture

Halo follows a **Hybrid Client-Server Architecture**. The browser handles the editor and preview, while the heavy lifting (compilation and deployment) is offloaded to a backend "Factory."

### 2.1 High-Level Diagram

```mermaid
graph TD
    subgraph "Halo Studio (Frontend)"
        UI[Chat Interface] -->|Prompt| API_GW[API Gateway]
        Sandbox[Sandpack Preview] <-->|RPC| Stellar[Stellar Network]
    end

    subgraph "Halo Engine (Backend)"
        API_GW -->|Job| Orchestrator[LangGraph Orchestrator]
        Orchestrator -->|Gen Rust| LLM[AI Model (Kimi-k2.5)]
        Orchestrator -->|Rust Code| Builder[Docker Compiler]
        Builder -->|WASM| Deployer[Tx Manager]
        Deployer -->|Upload| Stellar
        Deployer -->|Contract ID| Orchestrator
        Orchestrator -->|Gen React| LLM
    end

    subgraph "Output"
        Orchestrator -->|Contract ID + React Code| UI
        UI -->|Inject| Sandbox
    end

```

---

## 3. Core Components

### 3.1 The Frontend ("Halo Studio")

* **Framework:** Next.js 14 (App Router).
* **State Management:** Zustand (for managing the chat/build state).
* **Preview Engine:** **Sandpack (by CodeSandbox)**.
* *Role:* Renders the generated React code in an isolated iframe.
* *Config:* Pre-loaded with `@stellar/freighter-api` and `soroban-client`.


* **Wallet:** Integrated via `@creit.tech/stellar-wallets-kit`.

### 3.2 The Backend ("Halo Engine")

* **Framework:** Python (FastAPI).
* **Orchestration:** **LangGraph**.
* Manages the multi-step lifecycle (Clarify -> Code -> Compile -> Deploy -> UI).


* **Database:** PostgreSQL (optional, for saving projects) or Redis (for job queues).

### 3.3 The Build System ("The Forge")

* **Isolation:** Docker.
* **Image:** Custom image based on `stellar/soroban-build`.
* **Operation:**
1. Receives `lib.rs` string.
2. Mounts to ephemeral container.
3. Runs `cargo build --target wasm32-unknown-unknown --release`.
4. Extracts `.wasm` binary.



### 3.4 The Deployer

* **Identity:** A server-side "Hot Wallet" (funded via Friendbot for Testnet).
* **Function:**
1. Signs `uploadWasm` transaction.
2. Signs `createContract` transaction.
3. Returns the resulting `Contract ID`.



---

## 4. The "Fund Transfer" User Flow

**Scenario:** User types *"Make a transparent fund transfer app where I can send XLM to anyone."*

### Phase 1: Semantic Analysis (The Blueprint)

* **Architect Agent** analyzes the request.
* **Decision:** Needs a standard Soroban contract. No custom token needed (uses native XLM).
* **Output:** Spec `{ function: "transfer", args: [to, amount] }`.

### Phase 2: Contract Generation (The Backend)

* **Rust Agent** generates `lib.rs`:
```rust
// Simplified for brevity
pub fn transfer(env: Env, to: Address, amount: i128) {
    let from = env.require_auth();
    // ... Soroban token logic ...
}

```


* **Compiler Service** builds this into `transfer.wasm`.

### Phase 3: Deployment (The Chain)

* **Deployer Service** uploads `transfer.wasm` to Stellar Testnet.
* **Network** confirms and returns ID: `CA3...DAPP`.

### Phase 4: Frontend Synthesis (The UI)

* **React Agent** receives `CA3...DAPP`.
* **Constraint:** It *must* use the Halo `useContract` hook.
* **Generation:**
```javascript
// App.js
import { useContract } from './hooks/useContract';

export default function TransferApp() {
  const { invoke } = useContract("CA3...DAPP");

  const handleSend = () => {
    invoke('transfer', { to: address, amount: 100 });
  };

  return <button onClick={handleSend}>Send Funds</button>;
}

```



### Phase 5: Live Preview

* The JSON payload (React code + Contract ID) is sent to the browser.
* Sandpack hot-reloads.
* User sees the button, clicks it, and their Freighter wallet opens to sign the transaction.

---

## 5. API Interface Design

### `POST /api/v1/generate`

Initiates the build process.

**Request:**

```json
{
  "prompt": "Create a crowdfunding app",
  "network": "testnet",
  "user_wallet": "G..." // Optional, for ownership assignment
}

```

**Response (Streamed):**

```json
// Event: status_update
{ "step": "generating_rust", "message": "Drafting Smart Contract..." }

// Event: compilation_log
{ "step": "compiling", "log": "Compiling [=================>] 100%" }

// Event: deployment_success
{ "step": "deployed", "contract_id": "CA3..." }

// Event: complete
{ 
  "status": "ready",
  "files": {
    "/App.js": "...",
    "/components/Card.js": "..."
  }
}

```

---

## 6. Security & Limits

1. **Sandboxing:**
* Rust compilation happens in ephemeral Docker containers with no network access (except to download crates, which are cached).
* Containers are killed after 60 seconds (Time Limit).


2. **Wallet Safety:**
* The "Hot Wallet" on the server *only* pays for deployment fees. It has no control over the deployed contract logic.
* The User's contract ownership is assigned to the User's Public Key (if provided) during initialization.


3. **Rate Limiting:**
* 1 Build per minute per IP (to prevent server overload from `cargo build`).



---

## 7. Future Roadmap

* **V2:** Support for "Upgrade Contract" (using Soroban's `update_current_contract_wasm`).
* **V2:** One-click deployment to Vercel (publishing the generated frontend).
* **V3:** Multi-contract orchestration (e.g., DAO + Token + Treasury).