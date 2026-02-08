# Halo - Text-to-DApp Engine

Halo is an AI-powered platform that lets anyone build, deploy, and interact with decentralized applications on the **Stellar blockchain** using plain English. Describe your DApp idea in natural language, and Halo handles the entire pipeline from generating Soroban smart contracts in Rust, compiling to WebAssembly, deploying to Stellar Testnet, and creating a live React frontend with wallet integration all in one seamless flow.

## Contract Address

Halo dynamically generates and deploys smart contracts to the **Stellar Soroban Testnet** for each user request. There is no single fixed contract address  every generation produces a new on-chain contract.

| Detail | Value |
|--------|-------|
| **Network** | Stellar Testnet |
| **Contract Platform** | Soroban (Rust compiled to WebAssembly) |
| **Soroban SDK Version** | 21.0.0 |
| **RPC Endpoint** | `https://soroban-testnet.stellar.org` |
| **Horizon URL** | `https://horizon-testnet.stellar.org` |

Each deployed contract returns a unique contract ID (e.g., `CA3D...`) displayed in the UI after successful deployment. Contracts can be verified on [Stellar Expert (Testnet)](https://stellar.expert/explorer/testnet).

## Problem Statement

### The Problem

Building blockchain DApps today requires expertise across multiple domains:

- **Smart contract development** — Writing production-grade Rust/Soroban code
- **DevOps & compilation** — Setting up Docker environments, compiling Rust to WASM, managing toolchains
- **Blockchain deployment** — Understanding transaction signing, RPC endpoints, and network configuration
- **Frontend development** — Building React UIs with wallet integration and contract interaction hooks
- **Ecosystem knowledge** — Navigating protocols, SDKs, and best practices for Stellar/Soroban

This creates an enormous barrier to entry. Even experienced developers spend days or weeks wiring together the full stack for a single DApp.

### How Halo Solves It

Halo abstracts away the entire complexity into a single natural language prompt:

1. **Analyze** — An AI architect agent parses your prompt to extract a detailed contract specification
2. **Generate** — A specialized Rust agent writes production-ready Soroban smart contracts using RAG-enhanced context from indexed Stellar SDK documentation
3. **Compile** — A sandboxed Docker environment compiles Rust to WebAssembly with automatic retry on errors
4. **Deploy** — The compiled WASM is uploaded and deployed to Stellar Testnet with automatic contract ID retrieval
5. **Build Frontend** — A React agent generates a working frontend with Freighter wallet integration and live contract interaction
6. **Preview & Publish** — Instantly preview the DApp in-browser via Sandpack, and optionally publish to Vercel with one click

What previously took days now takes minutes.

## Features

- **Natural Language to DApp** — Describe your idea in plain English and get a working DApp with contract + frontend
- **Real-time Build Streaming** — Watch the entire pipeline (analysis, compilation, deployment, frontend) via Server-Sent Events with live logs
- **Live In-Browser Preview** — Sandpack-powered code sandbox with hot-reload and instant preview
- **Wallet Integration** — Connect Freighter wallet for real transaction signing, or use mock wallet for testing
- **Smart Contract Compilation** — Dockerized Soroban builder with pre-warmed cargo cache for fast WASM compilation
- **Automatic Deployment** — Server-side hot wallet deploys contracts to Stellar Testnet with retry logic
- **RAG-Enhanced Generation** — ChromaDB vector store with indexed Soroban SDK and Stellar JS SDK documentation for context-aware code generation
- **Protocol Suggestions** — Curated registry of Stellar ecosystem protocols (Soroswap, Blend, Phoenix, etc.) with AI-powered integration recommendations
- **One-Click Vercel Publishing** — Deploy your generated frontend to Vercel using OAuth or a claimable platform deployment
- **Error Memory & Auto-Retry** — Tracks compilation errors and successful patterns to improve generation quality over time
- **Multi-Agent Orchestration** — LangGraph state machine coordinates architect, Rust, and React agents through the pipeline

## Architecture Overview

### System Diagram

```
┌─────────────────────────────────────┐         ┌──────────────────────────────┐
│         Halo Studio (Frontend)      │   SSE   │       Halo Engine (Backend)  │
│                                     │◄────────┤                              │
│  Next.js 14 · Tailwind · Zustand   │         │  FastAPI · LangGraph · Claude│
│  Sandpack Preview · Freighter       │         │  ChromaDB · Sentence-BERT    │
└─────────────────────────────────────┘         └──────────────┬───────────────┘
                                                               │
                                        ┌──────────────────────┼──────────────────────┐
                                        │                      │                      │
                                ┌───────▼───────┐    ┌────────▼────────┐    ┌────────▼────────┐
                                │   Compiler    │    │    Deployer     │    │   ChromaDB      │
                                │   (Docker)    │    │  (Stellar RPC)  │    │  (Vector DB)    │
                                │  Rust → WASM  │    │  WASM → Chain   │    │  SDK Docs RAG   │
                                └───────────────┘    └────────┬────────┘    └─────────────────┘
                                                              │
                                                   ┌──────────┼──────────┐
                                                   │                     │
                                            ┌──────▼──────┐     ┌───────▼───────┐
                                            │ PostgreSQL  │     │  Vercel API   │
                                            │  Projects   │     │  Publishing   │
                                            └─────────────┘     └───────────────┘
```

### Pipeline Flow

```
User Prompt
    │
    ▼
┌─────────────┐    ┌──────────────┐    ┌─────────────┐    ┌────────────┐
│  Architect   │───▶│  Rust Agent  │───▶│  Compiler   │───▶│  Deployer  │
│  (Analyze)   │    │  (Generate)  │    │  (Docker)   │    │ (Stellar)  │
└─────────────┘    └──────────────┘    └─────────────┘    └──────┬─────┘
                                                                  │
                                        ┌──────────────┐    ┌────▼───────┐
                                        │ React Agent  │───▶│  Preview   │
                                        │ (Frontend)   │    │ (Sandpack) │
                                        └──────────────┘    └────────────┘
```

### Tech Stack

| Layer | Technology |
|-------|-----------|
| **Frontend** | Next.js 14, Tailwind CSS, Zustand, Sandpack, Framer Motion, shadcn/ui |
| **Backend** | FastAPI, LangGraph, Uvicorn, Python 3.11+ |
| **AI/LLM** | Claude (Anthropic), Sentence-Transformers (all-MiniLM-L6-v2) |
| **Vector DB** | ChromaDB (local, persistent) |
| **Database** | PostgreSQL 15 |
| **Blockchain** | Stellar Soroban Testnet, Soroban SDK 21.0.0 |
| **Wallet** | Freighter, Stellar Wallets Kit |
| **Compilation** | Docker (custom Soroban builder image) |
| **Hosting** | Vercel (optional one-click publish) |

### Project Structure

```
halo/
├── frontend/                    # Next.js 14 Frontend (Halo Studio)
│   ├── app/                     # App Router pages & API routes
│   ├── components/
│   │   ├── chat/                # Chat interface, wallet button, protocols panel
│   │   ├── preview/             # Sandpack preview & build status visualization
│   │   └── layout/              # Navbar
│   ├── hooks/                   # useContract, wallet bridge
│   └── lib/                     # Zustand store, API client, utilities
│
├── backend/                     # FastAPI Backend (Halo Engine)
│   ├── app/
│   │   ├── agents/              # LangGraph orchestrator, architect, Rust & React agents
│   │   ├── services/            # Compiler (Docker), deployer (Stellar), Vercel publisher
│   │   ├── rag/                 # ChromaDB retriever, embeddings, system prompts
│   │   ├── protocols/           # Stellar ecosystem protocol registry
│   │   ├── api/routes/          # REST endpoints (generate, publish, protocols)
│   │   └── db/                  # SQLAlchemy models & session management
│   ├── knowledge/               # ChromaDB vector store & agent memory
│   └── docker/soroban-builder/  # Custom Docker image for WASM compilation
│
└── docker-compose.yml           # Local development setup
```

## Screenshots

> Screenshots of the Halo dApp will be added here.

<!--
Add screenshots to a `docs/screenshots/` directory and update the paths below:

![Chat Interface](docs/screenshots/chat.png)
*Natural language chat interface with protocol suggestions*

![Build Pipeline](docs/screenshots/build-pipeline.png)
*Real-time build streaming showing compilation and deployment progress*

![Live Preview](docs/screenshots/preview.png)
*In-browser Sandpack preview with wallet integration*

![Deployed DApp](docs/screenshots/deployed.png)
*Successfully deployed coin flip game on Stellar Testnet*
-->

## Deployed Link

> _Deployment link will be added once the app is live in production._

<!-- Replace with your deployed URL when available -->

## Getting Started

### Prerequisites

- Node.js 18+
- Python 3.11+
- Docker & Docker Compose
- PostgreSQL 15
- [Anthropic API Key](https://console.anthropic.com/)
- [Freighter Wallet](https://www.freighter.app/) (browser extension, for testing)

### Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/your-username/halo.git
   cd halo
   ```

2. **Configure environment variables**
   ```bash
   cp .env.example .env
   # Edit .env and add your ANTHROPIC_API_KEY and STELLAR_HOT_WALLET_SECRET
   ```

3. **Start infrastructure**
   ```bash
   docker-compose up -d
   ```

4. **Build the Soroban builder image**
   ```bash
   cd backend/docker/soroban-builder
   docker build -t halo-soroban-builder:latest .
   ```

5. **Run the backend**
   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   uvicorn app.main:app --reload --port 8000
   ```

6. **Run the frontend**
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

7. **Open the app** at [http://localhost:3000](http://localhost:3000)

### Usage

1. Open Halo Studio in your browser
2. Type a prompt like *"Create a coin flip game with betting"*
3. Watch as Halo analyzes, generates, compiles, and deploys your DApp in real time
4. Interact with the live preview in the Sandpack panel
5. Connect your Freighter wallet to sign real transactions on Stellar Testnet
6. Optionally publish your DApp to Vercel with one click

## Future Scope

- **Mainnet Deployment** — Support deploying contracts to Stellar Mainnet with production-grade key management
- **Multi-Chain Support** — Extend beyond Stellar to support Ethereum (Solidity), Solana (Anchor), and other chains
- **Contract Templates Library** — Pre-built, audited contract templates (DeFi, NFTs, DAOs, governance) users can customize via prompts
- **Collaborative Editing** — Multi-user workspaces for teams to build and iterate on DApps together
- **Contract Verification & Auditing** — Automated security analysis and formal verification of generated contracts
- **On-Chain Analytics Dashboard** — Post-deployment monitoring with transaction history, user metrics, and contract state visualization
- **Mobile Support** — Responsive UI and mobile wallet integration for building and interacting with DApps on the go
- **Plugin Ecosystem** — Community-contributed agents, protocols, and frontend component templates
- **Version Control & Iteration** — Prompt history with the ability to iterate on, fork, and version generated DApps

## License

MIT

## Acknowledgments

- [Stellar Development Foundation](https://stellar.org/)
- [Soroban Smart Contracts](https://soroban.stellar.org/)
- [Anthropic Claude](https://www.anthropic.com/)
- [CodeSandbox Sandpack](https://sandpack.codesandbox.io/)
- [LangGraph](https://github.com/langchain-ai/langgraph)
