"""
Architect Agent - Analyzes user prompts and creates contract specifications

This agent is responsible for:
1. Understanding user intent from natural language
2. Creating a detailed specification for the smart contract
3. Identifying required functions and parameters
4. Specifying UI requirements for the frontend
"""

import json
import re
import logging
from typing import TypedDict

from app.core.llm import generate_completion

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AnalysisResult(TypedDict):
    template_type: str  # Kept for compatibility, but now just descriptive
    spec: dict


ARCHITECT_SYSTEM_PROMPT = """You are the Architect Agent for Halo, a text-to-DApp engine for Stellar/Soroban blockchain.

Your job is to analyze user requests and create a SIMPLE, FOCUSED specification for a smart contract.

## CRITICAL CONSTRAINTS — Soroban SDK 21 Limitations:
- Keep contracts SMALL: 3-5 public functions maximum (initialize + 2-3 core actions + 1 getter)
- Only use these Soroban types: i128, u64, bool, Address, String, Symbol, Vec, Map
- NO floating point. Use i128 for amounts (stroops: 1 XLM = 10_000_000 stroops)
- NO string formatting or concatenation — use u64 integers for all IDs
- All state changes require `require_auth()` from the caller
- Storage is key-value only via `env.storage().instance()` with a DataKey enum
- NO complex nested data structures. Keep structs flat (max 6 fields)
- First parameter of every function is ALWAYS `env: Env`
- Write functions need an `Address` parameter for the caller (for require_auth)

## Design Philosophy:
- Prefer FEWER functions that work correctly over many functions that might fail
- Every function should map directly to a user action in the UI
- Include an `initialize` function for setup and at least one `get_*` query function
- Keep business logic simple — one clear responsibility per function

## IMPORTANT RULES for type/category naming:
Use ONE of these exact categories: token_vault, crowdfunding, voting, nft, escrow, marketplace, subscription, lottery, counter, transfer, game, custom
- Use "custom" for any DApp that doesn't fit the other categories (e.g., prediction markets, social apps, registries, time-locks, etc.)
This helps select the right reference template for code generation.

## EXAMPLE GOOD SPEC (for "Create a crowdfunding app"):
{
  "template_type": "crowdfunding",
  "spec": {
    "name": "Crowdfunding",
    "description": "A crowdfunding contract where users can create campaigns and contribute funds",
    "functions": [
      {"name": "create", "description": "Create a new campaign", "params": ["creator: Address", "title: String", "goal: i128", "deadline: u64", "token: Address"], "returns": "u64"},
      {"name": "contribute", "description": "Contribute to a campaign", "params": ["campaign_id: u64", "contributor: Address", "amount: i128"], "returns": "void"},
      {"name": "withdraw", "description": "Withdraw funds if goal reached", "params": ["campaign_id: u64"], "returns": "void"},
      {"name": "get_campaign", "description": "Get campaign details", "params": ["id: u64"], "returns": "Campaign"}
    ],
    "storage": {"Campaign(u64)": "Campaign struct with creator, title, goal, deadline, raised, token, active", "Contribution(u64, Address)": "i128 contribution amount", "NextId": "u64 auto-increment counter"},
    "parameters": {},
    "ui_requirements": ["Form to create campaign with title, goal, deadline", "Contribute form with amount", "Campaign details display", "Withdraw button"],
    "business_logic": ["Only creator can withdraw", "Cannot contribute after deadline", "Cannot withdraw unless goal reached"]
  }
}

Respond with ONLY a JSON object (no markdown, no explanation):
{
  "template_type": "category_name",
  "spec": {
    "name": "ContractName",
    "description": "One sentence describing what this contract does",
    "functions": [
      {
        "name": "function_name",
        "description": "What this function does",
        "params": ["param_name: SorobanType"],
        "returns": "return_type or void"
      }
    ],
    "storage": {
      "key_name": "what it stores and its type"
    },
    "parameters": {},
    "ui_requirements": [
      "Brief UI element description"
    ],
    "business_logic": [
      "Key constraint (max 3 rules)"
    ]
  }
}"""


ARCHITECT_USER_PROMPT = """User request: {prompt}

Create a SIMPLE contract spec. Remember:
- Maximum 5 public functions (initialize + 2-3 actions + 1 getter)
- Use only: i128, u64, bool, Address, String, Symbol
- All IDs must be u64 (no string IDs)
- Every write function needs an Address param for require_auth()
- First param is always env: Env (don't include in params list — it's implicit)
- template_type MUST be one of: token_vault, crowdfunding, voting, nft, escrow, marketplace, subscription, lottery, counter, transfer, game, custom

Respond with ONLY the JSON object:"""


async def analyze_prompt(prompt: str) -> AnalysisResult:
    """
    Analyze user prompt and return a detailed specification.
    
    Always uses LLM - no fallbacks, no templates.
    """
    logger.info(f"[ARCHITECT] Starting analysis of prompt: {prompt[:100]}...")
    
    response = await generate_completion(
        system_prompt=ARCHITECT_SYSTEM_PROMPT,
        user_prompt=ARCHITECT_USER_PROMPT.format(prompt=prompt),
        temperature=0.1,
        max_tokens=16384,
    )
    
    if not response:
        logger.error("[ARCHITECT] LLM returned empty response")
        raise RuntimeError("Failed to analyze prompt - LLM returned empty response")
    
    logger.info(f"[ARCHITECT] LLM response received ({len(response)} chars)")
    logger.debug(f"[ARCHITECT] Raw response: {response[:500]}...")
    
    # Parse JSON from response
    try:
        json_match = re.search(r'\{[\s\S]*\}', response)
        if json_match:
            data = json.loads(json_match.group())
            
            # Validate required fields
            if "template_type" not in data or "spec" not in data:
                logger.error("[ARCHITECT] Missing required fields in response")
                raise ValueError("Missing template_type or spec in response")
            
            result = AnalysisResult(
                template_type=data["template_type"],
                spec=data["spec"]
            )
            
            logger.info(f"[ARCHITECT] Analysis complete:")
            logger.info(f"  - Type: {result['template_type']}")
            logger.info(f"  - Name: {result['spec'].get('name', 'Unknown')}")
            logger.info(f"  - Description: {result['spec'].get('description', 'N/A')[:100]}...")
            logger.info(f"  - Functions: {[f.get('name', f) if isinstance(f, dict) else f for f in result['spec'].get('functions', [])]}")
            
            return result
            
    except json.JSONDecodeError as e:
        logger.error(f"[ARCHITECT] JSON parse error: {e}")
        logger.error(f"[ARCHITECT] Response was: {response[:500]}...")
        raise RuntimeError(f"Failed to parse LLM response as JSON: {e}")
    
    logger.error("[ARCHITECT] Could not extract JSON from response")
    raise RuntimeError("Failed to extract specification from LLM response")
