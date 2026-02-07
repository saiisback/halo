"""Generate endpoint - Main DApp generation pipeline"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
import json
import asyncio

from app.agents.orchestrator import run_pipeline

router = APIRouter()


class GenerateRequest(BaseModel):
    """Request body for /generate endpoint"""

    prompt: str
    network: str = "testnet"
    user_wallet: Optional[str] = None


class GenerateResponse(BaseModel):
    """Final response after generation complete"""

    status: str
    contract_id: Optional[str] = None
    files: Optional[dict] = None
    error: Optional[str] = None


async def event_generator(prompt: str, network: str, user_wallet: Optional[str]):
    """Generate SSE events as pipeline progresses"""
    try:
        async for event in run_pipeline(prompt, network, user_wallet):
            # Format as SSE
            event_data = json.dumps(event)
            yield f"data: {event_data}\n\n"
            
            # Small delay to prevent overwhelming the client
            await asyncio.sleep(0.1)
            
    except Exception as e:
        error_event = json.dumps({
            "step": "error",
            "message": str(e),
            "status": "failed"
        })
        yield f"data: {error_event}\n\n"


@router.post("/generate")
async def generate_dapp(request: GenerateRequest):
    """
    Generate a DApp from natural language prompt.
    
    Returns a Server-Sent Events stream with progress updates.
    
    Events:
    - status_update: Current step name + message
    - compilation_log: Real-time cargo output
    - deployment_success: Contract ID
    - files: Generated React code
    - complete: Final success/error
    """
    if not request.prompt.strip():
        raise HTTPException(status_code=400, detail="Prompt cannot be empty")

    return StreamingResponse(
        event_generator(request.prompt, request.network, request.user_wallet),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
