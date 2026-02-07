"""
LangGraph Orchestrator for Halo DApp Generation Pipeline

This is the core state machine that manages the entire build process:
1. Analyze prompt → Create specification
2. Retrieve relevant Stellar docs (RAG)
3. Generate Rust contract from scratch
4. Compile contract via Docker
5. Deploy to Stellar Testnet
6. Retrieve JS SDK docs (RAG)
7. Generate React frontend
"""

import logging
from typing import TypedDict, Literal, AsyncGenerator, Optional
from langgraph.graph import StateGraph, END

from app.agents.architect import analyze_prompt
from app.agents.rust_agent import generate_rust_contract
from app.agents.react_agent import generate_react_frontend, ReactGenerationError
from app.services.compiler import compile_contract
from app.services.deployer import deploy_contract
from app.rag.retriever import retrieve_docs
from app.core.config import settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PipelineState(TypedDict):
    """State that flows through the pipeline"""
    # Input
    prompt: str
    network: str
    user_wallet: Optional[str]

    # Analysis results
    template_type: str
    contract_spec: dict

    # RAG context
    rust_docs: list[str]
    js_docs: list[str]

    # Generated code
    rust_code: str
    cargo_toml: str

    # Compilation
    wasm_binary: bytes
    compile_logs: list[str]
    compile_retry_count: int

    # Deployment
    contract_id: str
    deployment_retry_count: int
    deployment_error: Optional[str]

    # Frontend
    react_files: dict[str, str]

    # Status
    current_step: str
    error: Optional[str]
    events: list[dict]


# Maximum retry attempts — first generation should succeed; retries are safety net only
MAX_COMPILE_RETRIES = 3
MAX_DEPLOYMENT_RETRIES = 2


def create_pipeline() -> StateGraph:
    """Create the LangGraph pipeline"""
    workflow = StateGraph(PipelineState)

    workflow.add_node("analyze", analyze_node)
    workflow.add_node("retrieve_rust_docs", retrieve_rust_docs_node)
    workflow.add_node("generate_rust", generate_rust_node)
    workflow.add_node("compile", compile_node)
    workflow.add_node("deploy", deploy_node)
    workflow.add_node("retrieve_js_docs", retrieve_js_docs_node)
    workflow.add_node("generate_react", generate_react_node)

    workflow.set_entry_point("analyze")
    workflow.add_edge("analyze", "retrieve_rust_docs")
    workflow.add_edge("retrieve_rust_docs", "generate_rust")
    workflow.add_edge("generate_rust", "compile")

    workflow.add_conditional_edges(
        "compile",
        should_retry_compile,
        {
            "retry": "generate_rust",
            "continue": "deploy",
            "error": END,
        }
    )

    workflow.add_conditional_edges(
        "deploy",
        should_retry_deployment,
        {
            "retry": "generate_rust",
            "continue": "retrieve_js_docs",
            "error": END,
        }
    )

    workflow.add_edge("retrieve_js_docs", "generate_react")
    workflow.add_edge("generate_react", END)

    return workflow.compile()


# Node implementations

async def analyze_node(state: PipelineState) -> PipelineState:
    """Analyze the user prompt and create specification"""
    logger.info("=" * 60)
    logger.info("[ORCHESTRATOR] STEP 1: ANALYZING PROMPT")
    logger.info("=" * 60)
    logger.info(f"[ORCHESTRATOR] Prompt: {state['prompt'][:200]}...")
    
    state["current_step"] = "analyzing"
    state["events"].append({
        "step": "analyzing",
        "message": "Analyzing your request..."
    })
    
    try:
        result = await analyze_prompt(state["prompt"])
        
        state["template_type"] = result["template_type"]
        state["contract_spec"] = result["spec"]
        
        logger.info(f"[ORCHESTRATOR] Analysis complete:")
        logger.info(f"  - Type: {result['template_type']}")
        logger.info(f"  - Name: {result['spec'].get('name', 'Unknown')}")
        logger.info(f"  - Description: {result['spec'].get('description', 'N/A')[:100]}...")
        
        state["events"].append({
            "step": "analyzing",
            "message": f"Understood! Creating a {result['spec'].get('name', 'contract')} - {result['spec'].get('description', '')[:100]}"
        })
    except Exception as e:
        logger.error(f"[ORCHESTRATOR] Analysis failed: {e}")
        state["error"] = str(e)
        state["events"].append({
            "step": "error",
            "message": f"Analysis failed: {e}"
        })
    
    return state


async def retrieve_rust_docs_node(state: PipelineState) -> PipelineState:
    """Retrieve relevant Soroban SDK documentation"""
    logger.info("=" * 60)
    logger.info("[ORCHESTRATOR] STEP 2: RETRIEVING SOROBAN DOCUMENTATION")
    logger.info("=" * 60)
    
    state["current_step"] = "retrieving_docs"
    state["events"].append({
        "step": "retrieving_docs",
        "message": "Fetching Stellar/Soroban documentation..."
    })
    
    try:
        docs = await retrieve_docs(
            query=state["prompt"],
            doc_type="soroban-sdk",
            top_k=settings.rag_top_k
        )
        
        state["rust_docs"] = docs
        
        logger.info(f"[ORCHESTRATOR] Retrieved {len(docs)} documentation chunks")
        for i, doc in enumerate(docs[:3]):
            logger.info(f"  - Doc {i+1}: {doc[:100]}...")
        
        state["events"].append({
            "step": "retrieving_docs",
            "message": f"Found {len(docs)} relevant documentation sections"
        })
    except Exception as e:
        logger.warning(f"[ORCHESTRATOR] Doc retrieval failed (non-fatal): {e}")
        state["rust_docs"] = []
        state["events"].append({
            "step": "retrieving_docs",
            "message": "Proceeding without additional documentation"
        })
    
    return state


async def generate_rust_node(state: PipelineState) -> PipelineState:
    """Generate Rust contract code from scratch"""
    logger.info("=" * 60)
    logger.info("[ORCHESTRATOR] STEP 3: GENERATING SMART CONTRACT")
    logger.info("=" * 60)
    
    state["current_step"] = "generating_rust"

    deployment_error = state.get("deployment_error")
    compile_error = state.get("error") if state.get("compile_retry_count", 0) > 0 else None
    previous_code = state.get("rust_code")
    is_retry = bool(deployment_error or compile_error) and bool(previous_code)

    if is_retry:
        error_context = deployment_error or compile_error
        logger.info(f"[ORCHESTRATOR] Retry mode - fixing error: {error_context[:200]}...")
        state["events"].append({
            "step": "generating_rust",
            "message": f"Fixing contract based on error..."
        })
    else:
        logger.info(f"[ORCHESTRATOR] Fresh generation for: {state['contract_spec'].get('name', 'contract')}")
        state["events"].append({
            "step": "generating_rust",
            "message": "Writing smart contract code..."
        })

    try:
        result = await generate_rust_contract(
            template_type=state["template_type"],
            spec=state["contract_spec"],
            docs_context=state["rust_docs"],
            previous_code=previous_code if is_retry else None,
            error_context=deployment_error or compile_error if is_retry else None,
        )

        state["rust_code"] = result["lib_rs"]
        state["cargo_toml"] = result["cargo_toml"]
        state["deployment_error"] = None

        logger.info(f"[ORCHESTRATOR] Contract code generated: {len(result['lib_rs'])} chars")
        logger.info(f"[ORCHESTRATOR] Code preview:")
        for line in result["lib_rs"].split('\n')[:15]:
            logger.info(f"  {line}")

        state["events"].append({
            "step": "generating_rust",
            "message": "Smart contract code ready"
        })
    except Exception as e:
        logger.error(f"[ORCHESTRATOR] Code generation failed: {e}")
        state["error"] = str(e)
        state["events"].append({
            "step": "error",
            "message": f"Code generation failed: {e}"
        })

    return state


async def compile_node(state: PipelineState) -> PipelineState:
    """Compile the Rust contract to WASM"""
    logger.info("=" * 60)
    logger.info("[ORCHESTRATOR] STEP 4: COMPILING CONTRACT")
    logger.info("=" * 60)

    state["current_step"] = "compiling"
    state["events"].append({
        "step": "compiling",
        "message": "Compiling contract to WASM..."
    })

    try:
        result = await compile_contract(
            lib_rs=state["rust_code"],
            cargo_toml=state["cargo_toml"]
        )

        state["compile_logs"] = result.get("logs", [])

        # Log compilation output
        logger.info(f"[ORCHESTRATOR] Compilation result: {'SUCCESS' if result['success'] else 'FAILED'}")
        for log in state["compile_logs"]:
            logger.info(f"  [COMPILER] {log}")

        if result["success"]:
            state["wasm_binary"] = result["wasm"]
            state["error"] = None  # Clear any previous error
            logger.info(f"[ORCHESTRATOR] WASM binary size: {len(result['wasm'])} bytes")
            state["events"].append({
                "step": "compiling",
                "message": f"Compilation successful ({len(result['wasm'])} bytes)"
            })
        else:
            # Build comprehensive error context from logs + error message
            # This gives the rust agent maximum context to fix the issue
            error_parts = []
            if result.get("error"):
                error_parts.append(result["error"])
            # Include the last 30 log lines (most useful for error context)
            error_logs = [log for log in state["compile_logs"] if log.strip()]
            if error_logs:
                error_parts.append("COMPILER OUTPUT:\n" + "\n".join(error_logs[-30:]))

            full_error = "\n\n".join(error_parts) if error_parts else "Compilation failed"
            state["error"] = full_error
            logger.error(f"[ORCHESTRATOR] Compilation error: {full_error[:500]}")
            state["events"].append({
                "step": "compiling",
                "message": f"Compilation error: {result.get('error', 'failed')[:200]}"
            })

        # Stream logs as events
        for log in state["compile_logs"]:
            state["events"].append({
                "step": "compiling",
                "log": log
            })
    except Exception as e:
        logger.error(f"[ORCHESTRATOR] Compilation exception: {e}")
        state["error"] = str(e)
        state["events"].append({
            "step": "error",
            "message": f"Compilation failed: {e}"
        })

    return state


def should_retry_compile(state: PipelineState) -> Literal["retry", "continue", "error"]:
    """Decide whether to retry compilation or continue"""
    if state.get("error"):
        retry_count = state.get("compile_retry_count", 0)
        logger.info(f"[ORCHESTRATOR] Compile check: error present, retry count = {retry_count}")
        
        if retry_count < MAX_COMPILE_RETRIES:
            state["compile_retry_count"] = retry_count + 1
            logger.info(f"[ORCHESTRATOR] Will retry compilation (attempt {retry_count + 1}/{MAX_COMPILE_RETRIES})")
            return "retry"
        
        logger.error(f"[ORCHESTRATOR] Max compile retries exceeded")
        return "error"
    
    logger.info(f"[ORCHESTRATOR] Compilation successful, continuing to deploy")
    return "continue"


def should_retry_deployment(state: PipelineState) -> Literal["retry", "continue", "error"]:
    """Decide whether to retry deployment or continue"""
    if state.get("error") or state.get("deployment_error"):
        retry_count = state.get("deployment_retry_count", 0)
        error_msg = state.get("deployment_error") or state.get("error") or ""
        
        logger.info(f"[ORCHESTRATOR] Deploy check: error present, retry count = {retry_count}")
        logger.info(f"[ORCHESTRATOR] Error: {error_msg[:200]}")

        # Non-retryable errors
        non_retryable = ["unknown network", "failed to initialize hot wallet"]
        if any(nr in error_msg.lower() for nr in non_retryable):
            logger.error(f"[ORCHESTRATOR] Non-retryable error detected")
            return "error"

        if retry_count < MAX_DEPLOYMENT_RETRIES:
            state["deployment_retry_count"] = retry_count + 1
            state["error"] = None
            logger.info(f"[ORCHESTRATOR] Will retry deployment (attempt {retry_count + 1}/{MAX_DEPLOYMENT_RETRIES})")
            return "retry"
        
        logger.error(f"[ORCHESTRATOR] Max deployment retries exceeded")
        return "error"
    
    logger.info(f"[ORCHESTRATOR] Deployment successful, continuing to frontend")
    return "continue"


async def deploy_node(state: PipelineState) -> PipelineState:
    """Deploy the compiled WASM to Stellar Testnet"""
    logger.info("=" * 60)
    logger.info("[ORCHESTRATOR] STEP 5: DEPLOYING TO STELLAR")
    logger.info("=" * 60)
    
    retry_count = state.get("deployment_retry_count", 0)
    retry_msg = f" (attempt {retry_count + 1})" if retry_count > 0 else ""

    state["current_step"] = "deploying"
    state["events"].append({
        "step": "deploying",
        "message": f"Deploying to Stellar Testnet{retry_msg}..."
    })
    
    logger.info(f"[ORCHESTRATOR] Network: {state['network']}")
    logger.info(f"[ORCHESTRATOR] WASM size: {len(state.get('wasm_binary', b''))} bytes")

    try:
        result = await deploy_contract(
            wasm_binary=state["wasm_binary"],
            network=state["network"],
            user_wallet=state.get("user_wallet")
        )

        if result["success"]:
            state["contract_id"] = result["contract_id"]
            state["deployment_error"] = None
            
            logger.info(f"[ORCHESTRATOR] DEPLOYMENT SUCCESSFUL!")
            logger.info(f"[ORCHESTRATOR] Contract ID: {result['contract_id']}")
            
            state["events"].append({
                "step": "deployed",
                "message": "Contract deployed successfully!",
                "contract_id": result["contract_id"]
            })
        else:
            error_msg = result.get("error", "Deployment failed")
            state["error"] = error_msg
            state["deployment_error"] = error_msg
            
            logger.error(f"[ORCHESTRATOR] Deployment failed: {error_msg}")
            
            state["events"].append({
                "step": "deploying",
                "message": f"Deployment error: {error_msg[:200]}"
            })
    except Exception as e:
        logger.error(f"[ORCHESTRATOR] Deployment exception: {e}")
        state["error"] = str(e)
        state["deployment_error"] = str(e)
        state["events"].append({
            "step": "error",
            "message": f"Deployment failed: {e}"
        })

    return state


async def retrieve_js_docs_node(state: PipelineState) -> PipelineState:
    """Retrieve relevant Stellar JS SDK documentation"""
    logger.info("=" * 60)
    logger.info("[ORCHESTRATOR] STEP 6: RETRIEVING JS SDK DOCUMENTATION")
    logger.info("=" * 60)
    
    state["current_step"] = "retrieving_docs"
    state["events"].append({
        "step": "retrieving_docs",
        "message": "Fetching frontend SDK documentation..."
    })
    
    try:
        docs = await retrieve_docs(
            query=state["prompt"],
            doc_type="stellar-sdk-js",
            top_k=settings.rag_top_k
        )

        state["js_docs"] = docs
        
        logger.info(f"[ORCHESTRATOR] Retrieved {len(docs)} JS documentation chunks")
        
        state["events"].append({
            "step": "retrieving_docs",
            "message": f"Found {len(docs)} JS SDK documentation sections"
        })
    except Exception as e:
        logger.warning(f"[ORCHESTRATOR] JS doc retrieval failed (non-fatal): {e}")
        state["js_docs"] = []

    return state


async def generate_react_node(state: PipelineState) -> PipelineState:
    """Generate React frontend code"""
    logger.info("=" * 60)
    logger.info("[ORCHESTRATOR] STEP 7: GENERATING FRONTEND")
    logger.info("=" * 60)
    
    state["current_step"] = "generating_react"
    state["events"].append({
        "step": "generating_react",
        "message": "Building user interface..."
    })

    try:
        result = await generate_react_frontend(
            template_type=state["template_type"],
            spec=state["contract_spec"],
            contract_id=state["contract_id"],
            rust_code=state.get("rust_code", ""),
            docs_context=state["js_docs"]
        )

        state["react_files"] = result["files"]
        
        logger.info(f"[ORCHESTRATOR] Frontend generated successfully!")
        logger.info(f"[ORCHESTRATOR] Files created: {list(result['files'].keys())}")
        
        state["events"].append({
            "step": "complete",
            "message": "DApp ready!",
            "files": result["files"],
            "status": "ready"
        })
        
        logger.info("=" * 60)
        logger.info("[ORCHESTRATOR] PIPELINE COMPLETE - SUCCESS!")
        logger.info("=" * 60)
        
    except ReactGenerationError as e:
        logger.error(f"[ORCHESTRATOR] Frontend generation failed: {e}")
        state["error"] = str(e)
        state["events"].append({
            "step": "error",
            "message": f"Frontend generation failed: {e}",
            "status": "failed"
        })

    return state


# Main entry point

async def run_pipeline(
    prompt: str,
    network: str = "testnet",
    user_wallet: Optional[str] = None
) -> AsyncGenerator[dict, None]:
    """
    Run the full DApp generation pipeline.
    Yields events as the pipeline progresses.
    """
    logger.info("=" * 60)
    logger.info("[ORCHESTRATOR] STARTING HALO PIPELINE")
    logger.info("=" * 60)
    logger.info(f"[ORCHESTRATOR] Prompt: {prompt}")
    logger.info(f"[ORCHESTRATOR] Network: {network}")
    logger.info(f"[ORCHESTRATOR] User wallet: {user_wallet or 'None'}")

    # Initialize state
    state: PipelineState = {
        "prompt": prompt,
        "network": network,
        "user_wallet": user_wallet,
        "template_type": "",
        "contract_spec": {},
        "rust_docs": [],
        "js_docs": [],
        "rust_code": "",
        "cargo_toml": "",
        "wasm_binary": b"",
        "compile_logs": [],
        "compile_retry_count": 0,
        "contract_id": "",
        "deployment_retry_count": 0,
        "deployment_error": None,
        "react_files": {},
        "current_step": "idle",
        "error": None,
        "events": [],
    }

    try:
        # Phase 1: Analyze
        state = await analyze_node(state)
        for event in state["events"]:
            yield event
        state["events"] = []
        
        if state.get("error"):
            yield {"step": "error", "error": state["error"], "status": "failed"}
            return

        # Phase 2: Retrieve Rust docs
        state = await retrieve_rust_docs_node(state)
        for event in state["events"]:
            yield event
        state["events"] = []

        # Phase 3: Generate, Compile, Deploy loop with retries
        while True:
            # Generate Rust
            state = await generate_rust_node(state)
            for event in state["events"]:
                yield event
            state["events"] = []
            
            if state.get("error") and not state.get("rust_code"):
                yield {"step": "error", "error": state["error"], "status": "failed"}
                return

            # Compile
            state = await compile_node(state)
            for event in state["events"]:
                yield event
            state["events"] = []

            # Check compile result
            compile_decision = should_retry_compile(state)
            if compile_decision == "error":
                yield {"step": "error", "error": state["error"], "status": "failed"}
                return
            elif compile_decision == "retry":
                yield {
                    "step": "retrying",
                    "message": f"Fixing code and retrying (compile attempt {state['compile_retry_count']}/{MAX_COMPILE_RETRIES})..."
                }
                continue

            # Deploy
            state = await deploy_node(state)
            for event in state["events"]:
                yield event
            state["events"] = []

            # Check deploy result
            deploy_decision = should_retry_deployment(state)
            if deploy_decision == "error":
                yield {"step": "error", "error": state["error"], "status": "failed"}
                return
            elif deploy_decision == "retry":
                yield {
                    "step": "retrying",
                    "message": f"Fixing code and retrying (deploy attempt {state['deployment_retry_count']}/{MAX_DEPLOYMENT_RETRIES})..."
                }
                state["compile_retry_count"] = 0
                continue
            else:
                break

        # Phase 4: Retrieve JS docs
        state = await retrieve_js_docs_node(state)
        for event in state["events"]:
            yield event
        state["events"] = []

        # Phase 5: Generate React
        state = await generate_react_node(state)
        for event in state["events"]:
            yield event

        if state.get("error"):
            yield {"step": "error", "error": state["error"], "status": "failed"}
            return

    except Exception as e:
        logger.error(f"[ORCHESTRATOR] Pipeline exception: {e}")
        import traceback
        traceback.print_exc()
        yield {
            "step": "error",
            "error": str(e),
            "status": "failed"
        }
