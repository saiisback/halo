"""Protocols endpoint - Browse and get AI suggestions for Stellar ecosystem protocols"""

import json
import re
import logging
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional

from app.protocols.registry import (
    get_all_protocols,
    get_protocol_by_id,
    get_protocols_by_category,
    get_categories,
    get_protocol_summary_for_llm,
)
from app.core.llm import generate_completion

logger = logging.getLogger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------

class ProtocolResponse(BaseModel):
    id: str
    name: str
    description: str
    category: str
    icon: str
    integration_prompt: str
    sdk_package: Optional[str] = None
    docs_url: Optional[str] = None


class SuggestRequest(BaseModel):
    """Request body for AI-powered protocol suggestions"""
    template_type: str  # e.g. "crowdfunding", "transfer", "custom"
    contract_spec: dict  # the spec produced by the architect agent
    current_protocols: list[str] = []  # IDs of already-integrated protocols


class SuggestedProtocol(BaseModel):
    id: str
    name: str
    description: str
    category: str
    icon: str
    reason: str  # AI-generated explanation of why this protocol is relevant


class SuggestResponse(BaseModel):
    suggestions: list[SuggestedProtocol]


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/protocols", response_model=list[ProtocolResponse])
async def list_protocols(category: Optional[str] = None):
    """
    Return the curated list of Stellar ecosystem protocols.

    Optionally filter by category (DEX, Lending, DeFi, Data, Payments,
    Token, Security, Infrastructure, Liquidity, Stablecoin).
    """
    if category:
        protocols = get_protocols_by_category(category)
    else:
        protocols = get_all_protocols()

    return protocols


@router.get("/protocols/categories", response_model=list[str])
async def list_categories():
    """Return all unique protocol categories"""
    return get_categories()


@router.post("/protocols/suggest", response_model=SuggestResponse)
async def suggest_protocols(request: SuggestRequest):
    """
    Use AI to suggest 2-3 protocols that would complement the user's
    current DApp.  The response includes a short reason for each suggestion.
    """
    logger.info(f"[PROTOCOLS] Suggesting protocols for template_type={request.template_type}")

    protocol_list = get_protocol_summary_for_llm()

    # Build the LLM prompt
    system_prompt = """You are a Stellar blockchain protocol advisor. Given a DApp specification, suggest 2-3 protocols from the available list that would meaningfully enhance the DApp.

Rules:
- Only suggest protocols from the provided list
- Do NOT suggest protocols the user has already integrated
- Provide a short (1-2 sentence) reason for each suggestion explaining how it complements the DApp
- Return ONLY a JSON array, no markdown, no explanation

Example response:
[
  {"id": "soroswap", "reason": "Adding token swap functionality would let users exchange campaign tokens directly within the app."},
  {"id": "mercury", "reason": "Real-time event indexing would enable a live feed of campaign contributions and milestones."}
]"""

    user_prompt = f"""DApp type: {request.template_type}
DApp spec: {json.dumps(request.contract_spec, indent=2)[:2000]}
Already integrated protocols: {', '.join(request.current_protocols) if request.current_protocols else 'None'}

{protocol_list}

Suggest 2-3 protocols from the list above. Return ONLY the JSON array:"""

    try:
        response = await generate_completion(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.3,
            max_tokens=2048,
        )

        # Parse LLM response
        json_match = re.search(r'\[[\s\S]*\]', response)
        if not json_match:
            logger.warning("[PROTOCOLS] Could not parse LLM suggestion response")
            return SuggestResponse(suggestions=[])

        raw_suggestions = json.loads(json_match.group())

        suggestions: list[SuggestedProtocol] = []
        for s in raw_suggestions:
            protocol = get_protocol_by_id(s.get("id", ""))
            if protocol and protocol["id"] not in request.current_protocols:
                suggestions.append(
                    SuggestedProtocol(
                        id=protocol["id"],
                        name=protocol["name"],
                        description=protocol["description"],
                        category=protocol["category"],
                        icon=protocol["icon"],
                        reason=s.get("reason", "Recommended for your DApp."),
                    )
                )

        logger.info(f"[PROTOCOLS] Suggested {len(suggestions)} protocols")
        return SuggestResponse(suggestions=suggestions)

    except Exception as e:
        logger.error(f"[PROTOCOLS] Suggestion failed: {e}")
        return SuggestResponse(suggestions=[])
