# Halo - Text-to-DApp Engine

> Build, deploy, and interact with DApps on Stellar using natural language.

Halo is a web-based platform that enables users to create Decentralized Applications (DApps) on the Stellar network using natural language prompts. Unlike standard code generators, Halo acts as a full-cycle DevOps Engine.

## Features

- **Natural Language to DApp**: Describe your app, get a working DApp
- **Soroban Smart Contracts**: Generates secure Rust contracts for Stellar
- **Real Compilation**: Docker-based compilation to WASM
- **Testnet Deployment**: Automatic deployment to Stellar Testnet
- **Live Preview**: Sandpack-powered preview with wallet integration
- **RAG-Enhanced**: Stellar documentation context for accurate code

## Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Halo Studio   │────▶│   Halo Engine   │────▶│ Stellar Testnet │
│   (Next.js)     │     │   (FastAPI)     │     │                 │
└─────────────────┘     └─────────────────┘     └─────────────────┘
        │                       │
        │                       ▼
        │               ┌─────────────────┐
        │               │   Ollama LLM    │
        │               │   (Local)       │
        │               └─────────────────┘
        │
        ▼
┌─────────────────┐
│    Sandpack     │
│    Preview      │
└─────────────────┘
```

## Quick Start

### Prerequisites

- Node.js 18+
- Python 3.11+
- Docker
- Ollama (with kimi-k2.5 or compatible model)
- PostgreSQL

### Setup

1. **Clone the repository**
   ```bash
   git clone <repo-url>
   cd halo
   ```

2. **Start Ollama**
   ```bash
   ollama pull kimi-k2.5
   ollama pull nomic-embed-text
   ollama serve
   ```

3. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your settings
   ```

4. **Start with Docker Compose**
   ```bash
   docker-compose up -d
   ```

   Or run services individually:

   **Backend:**
   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   uvicorn app.main:app --reload
   ```

   **Frontend:**
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

5. **Open the app**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Docs: http://localhost:8000/docs

## Usage

1. Open Halo Studio in your browser
2. Type a prompt like "Create a fund transfer app"
3. Watch as Halo:
   - Analyzes your request
   - Generates a Soroban smart contract
   - Compiles it to WASM
   - Deploys to Stellar Testnet
   - Creates a React frontend
4. Interact with your live DApp in the preview panel
5. Connect your Freighter wallet to test transactions

## Project Templates

Halo includes pre-built templates for common DApp patterns:

- **Token Transfer**: Send XLM or custom tokens
- **Crowdfunding**: Campaigns with goals and deadlines
- **NFT Minting**: Create and manage NFT collections

## Project Structure

```
halo/
├── frontend/           # Next.js 14 frontend (Halo Studio)
│   ├── app/           # App router pages
│   ├── components/    # React components
│   └── lib/           # Utilities and store
│
├── backend/           # FastAPI backend (Halo Engine)
│   ├── app/
│   │   ├── agents/    # LangGraph agents
│   │   ├── api/       # API routes
│   │   ├── core/      # Configuration
│   │   ├── db/        # Database models
│   │   ├── rag/       # RAG system
│   │   ├── services/  # Compiler & Deployer
│   │   └── templates/ # Contract & UI templates
│   └── scripts/       # Utility scripts
│
├── docker-compose.yml # Local development
└── design.md          # Architecture document
```

## API Endpoints

### `POST /api/v1/generate`

Generate a DApp from a prompt. Returns Server-Sent Events (SSE) stream.

**Request:**
```json
{
  "prompt": "Create a crowdfunding app",
  "network": "testnet",
  "user_wallet": "G..."
}
```

**Events:**
- `status_update` - Current step
- `compilation_log` - Build output
- `deployment_success` - Contract ID
- `files` - Generated React code
- `complete` - Final status

## Technology Stack

- **Frontend**: Next.js 14, React, Tailwind CSS, shadcn/ui, Sandpack, Zustand
- **Backend**: FastAPI, LangGraph, Python
- **LLM**: Ollama (local, free)
- **Vector DB**: ChromaDB
- **Database**: PostgreSQL
- **Blockchain**: Stellar/Soroban

## Development

### Index Documentation (RAG)

```bash
cd backend
python -m scripts.index_docs
```

### Build Soroban Builder Image

```bash
cd backend/docker/soroban-builder
docker build -t halo-soroban-builder:latest .
```

## License

MIT

## Acknowledgments

- Stellar Development Foundation
- Soroban SDK
- CodeSandbox (Sandpack)
- Ollama
