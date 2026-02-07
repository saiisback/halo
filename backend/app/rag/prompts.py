"""
Prompt Templates with RAG Context

Formats prompts to include retrieved documentation context.
"""

from typing import Optional


def format_rust_prompt(
    base_prompt: str,
    template_code: str,
    spec: dict,
    docs_context: list[str],
) -> str:
    """
    Format prompt for Rust code generation with documentation context.
    
    Args:
        base_prompt: Base instruction prompt
        template_code: The template code to customize
        spec: Contract specification
        docs_context: Retrieved Soroban documentation
    
    Returns:
        Formatted prompt string
    """
    
    docs_section = format_docs_context(docs_context, "Soroban SDK")
    
    return f"""{base_prompt}

## Template Code
```rust
{template_code}
```

## Specification
- Name: {spec.get('name', 'MyContract')}
- Description: {spec.get('description', 'A Soroban smart contract')}
- Functions: {', '.join(spec.get('functions', []))}
- Parameters: {spec.get('parameters', {})}

{docs_section}

Generate the customized contract code:"""


def format_react_prompt(
    base_prompt: str,
    contract_id: str,
    spec: dict,
    docs_context: list[str],
) -> str:
    """
    Format prompt for React code generation with documentation context.
    
    Args:
        base_prompt: Base instruction prompt
        contract_id: Deployed contract ID
        spec: Contract specification
        docs_context: Retrieved Stellar JS SDK documentation
    
    Returns:
        Formatted prompt string
    """
    
    docs_section = format_docs_context(docs_context, "Stellar SDK")
    
    return f"""{base_prompt}

## Contract ID
{contract_id}

## Specification
- Name: {spec.get('name', 'MyDApp')}
- Description: {spec.get('description', 'A Stellar DApp')}
- Functions: {', '.join(spec.get('functions', []))}
- UI Requirements: {', '.join(spec.get('ui_requirements', []))}

{docs_section}

Generate the React frontend code:"""


def format_docs_context(docs: list[str], doc_type: str = "Documentation") -> str:
    """
    Format documentation chunks for inclusion in prompt.
    
    Args:
        docs: List of documentation strings
        doc_type: Type label for the documentation
    
    Returns:
        Formatted documentation section
    """
    
    if not docs:
        return f"## {doc_type} Reference\nNo additional documentation available."
    
    # Limit total context size
    max_chars = 4000
    selected_docs = []
    current_chars = 0
    
    for doc in docs:
        if current_chars + len(doc) > max_chars:
            break
        selected_docs.append(doc)
        current_chars += len(doc)
    
    docs_text = "\n\n---\n\n".join(selected_docs)
    
    return f"""## {doc_type} Reference

Use the following documentation as reference. Follow these patterns and best practices:

{docs_text}"""


def format_analysis_prompt(user_prompt: str) -> str:
    """
    Format prompt for the architect agent to analyze user intent.
    
    Args:
        user_prompt: The user's natural language request
    
    Returns:
        Formatted analysis prompt
    """
    
    return f"""Analyze the following DApp request and determine:
1. Which template to use (token_transfer, crowdfunding, or nft_mint)
2. What customizations are needed
3. Key functions and parameters

Available templates:
- token_transfer: For sending XLM or custom tokens between addresses
- crowdfunding: For campaigns with funding goals, deadlines, and refunds
- nft_mint: For creating and managing NFT collections

User request: {user_prompt}

Respond with a JSON object:
{{
  "template_type": "token_transfer" | "crowdfunding" | "nft_mint",
  "spec": {{
    "name": "contract name",
    "description": "brief description",
    "functions": ["list of functions"],
    "parameters": {{ "key": "value" }},
    "ui_requirements": ["list of UI elements"]
  }}
}}"""
