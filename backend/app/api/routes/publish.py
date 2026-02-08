"""Publish endpoint - deploy generated DApp frontend to Vercel"""

from typing import Optional

from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel, Field

from app.core.config import settings
from app.services.vercel_publish import (
    publish_to_vercel,
    create_project_transfer_request,
    build_claim_url,
)

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
    claim_url: Optional[str] = None
    transfer_code: Optional[str] = None
    error: Optional[str] = None


@router.post("/publish", response_model=PublishResponse)
async def publish(
    request: PublishRequest,
    x_vercel_access_token: Optional[str] = Header(default=None),
) -> PublishResponse:
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
        access_token_override=x_vercel_access_token,
    )

    if not result["success"]:
        vercel_status = result.get("vercel_status_code")
        detail = result.get("error") or "Publish failed"
        if vercel_status in (401, 403):
            raise HTTPException(status_code=403, detail=detail)
        if vercel_status == 429:
            raise HTTPException(status_code=429, detail=detail)
        raise HTTPException(status_code=500, detail=detail)

    return PublishResponse(
        success=True,
        url=result.get("url"),
        deployment_id=result.get("deployment_id"),
        error=None,
    )


class ClaimPublishRequest(PublishRequest):
    """Request body for /publish/claim endpoint"""

    return_url: str = "http://localhost:3000"


@router.post("/publish/claim", response_model=PublishResponse)
async def publish_claimable(request: ClaimPublishRequest) -> PublishResponse:
    """
    Publish using the PLATFORM Vercel token, then return a claim URL so the user
    can transfer ownership into their own Vercel account.

    This avoids relying on user OAuth tokens having deployment permissions.
    """
    if not request.contract_id.strip():
        raise HTTPException(status_code=400, detail="contract_id cannot be empty")
    if not request.files:
        raise HTTPException(status_code=400, detail="files cannot be empty")

    # Force platform-token publishing only (no user token override here)
    result = await publish_to_vercel(
        name=request.name or "halo-dapp",
        generated_files=request.files,
        contract_id=request.contract_id.strip(),
        network=request.network or "testnet",
        access_token_override=None,
        unique_project_name=True,
    )

    if not result["success"]:
        vercel_status = result.get("vercel_status_code")
        detail = result.get("error") or "Publish failed"
        if vercel_status in (401, 403):
            raise HTTPException(status_code=403, detail=detail)
        if vercel_status == 429:
            raise HTTPException(status_code=429, detail=detail)
        raise HTTPException(status_code=500, detail=detail)

    project_id = result.get("project_id")
    if not project_id:
        raise HTTPException(status_code=500, detail="Vercel deployment created but projectId missing")

    # Create transfer-request code
    token = settings.vercel_api_token
    if not token:
        raise HTTPException(status_code=500, detail="Missing VERCEL_API_TOKEN on backend")

    transfer = await create_project_transfer_request(project_id_or_name=project_id, bearer_token=token)
    if not transfer["success"] or not transfer.get("code"):
        code_status = transfer.get("vercel_status_code")
        detail = transfer.get("error") or "Failed to create transfer request"
        if code_status in (401, 403):
            raise HTTPException(status_code=403, detail=detail)
        raise HTTPException(status_code=500, detail=detail)

    code = transfer["code"]
    claim_url = build_claim_url(code=code, return_url=request.return_url)

    url = result.get("url")
    return PublishResponse(
        success=True,
        url=url if (url and url.startswith("http")) else (f"https://{url}" if url else None),
        deployment_id=result.get("deployment_id"),
        claim_url=claim_url,
        transfer_code=code,
        error=None,
    )

