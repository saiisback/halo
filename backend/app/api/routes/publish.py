"""Publish endpoint - deploy generated DApp frontend to Vercel"""

from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.vercel_publish import publish_to_vercel

router = APIRouter()


class PublishRequest(BaseModel):
    """Request body for /publish endpoint"""

    contract_id: str = Field(..., min_length=1)
    files: dict[str, str] = Field(..., description="Generated Sandpack files")
    name: Optional[str] = None
    network: str = "testnet"


class PublishResponse(BaseModel):
    success: bool
    url: Optional[str] = None
    deployment_id: Optional[str] = None
    error: Optional[str] = None


@router.post("/publish", response_model=PublishResponse)
async def publish(request: PublishRequest) -> PublishResponse:
    """
    Publish the generated frontend to Vercel.

    The caller must provide:
    - contract_id: deployed Soroban contract ID
    - files: Sandpack-style generated React files
    """
    if not request.contract_id.strip():
        raise HTTPException(status_code=400, detail="contract_id cannot be empty")
    if not request.files:
        raise HTTPException(status_code=400, detail="files cannot be empty")

    result = await publish_to_vercel(
        name=request.name or "halo-dapp",
        generated_files=request.files,
        contract_id=request.contract_id.strip(),
        network=request.network or "testnet",
    )

    if not result["success"]:
        raise HTTPException(status_code=500, detail=result.get("error") or "Publish failed")

    return PublishResponse(
        success=True,
        url=result.get("url"),
        deployment_id=result.get("deployment_id"),
        error=None,
    )

