"""
React Agent - Generates frontend code for DApps

This agent is responsible for:
1. Generating React code based on contract spec
2. Self-validating the generated code
3. Retrying with corrections if validation fails
"""

import re
import subprocess
import tempfile
import logging
from typing import TypedDict

from app.core.llm import generate_completion
from app.templates import get_frontend_template, get_frontend_components

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


## Documentation is fetched via RAG and passed through the pipeline as docs_context.


class ReactGenerationResult(TypedDict):
    files: dict[str, str]


class ReactGenerationError(Exception):
    """Raised when React code generation fails after all retries"""
    pass


REACT_AGENT_SYSTEM_PROMPT = """You generate COMPLETE App.jsx for Stellar DApps. Output ONLY JSX code, no markdown.

RULES:
- `export default function App()` with `import { useState } from 'react'`, `import { useContract } from './hooks/useContract'`, `import './index.css'`
- Destructure: `const { invoke, query, loading, error, txStatus, getPublicKey, u64, i128, u32, sorobanSymbol } = useContract();`
- invoke('method', {args}) for writes, query('method', {args}) for reads
- CRITICAL — FUNCTION NAME MATCHING: The method name string passed to invoke() or query() MUST be the EXACT Rust fn name from CONTRACT FUNCTIONS below. Do NOT rename, alias, or invent method names. If the Rust function is called "flip", you MUST write invoke('flip', ...). NEVER write invoke('place_bet', ...) or any other name.
- Every handler: `const pubKey = await getPublicKey(); if (!pubKey) return;`
- Type wrapping: Address→pass pubKey string directly, u64 params→u64(number), i128 params→i128(amount), u32→u32(number), Symbol→sorobanSymbol('value'), String→pass string directly, bool→true/false
- CRITICAL — u64 PARAMS: u64 parameters MUST use the u64() wrapper with a NUMBER, never a raw string. For enum-like choices (e.g., heads=0, tails=1), use a <select> dropdown where the option values are numbers, then pass u64(Number(selectedValue)). NEVER pass a string like "heads" to a u64 param.

EXAMPLES of correct calls:
  invoke('flip', { player: pubKey, choice: u64(Number(choice)), bet_amount: i128(amount) })
  query('get_balance', { addr: pubKey })
  invoke('initialize', { admin: pubKey })
WRONG — never do this:
  invoke('place_bet', { choice: "heads" })  // wrong name AND wrong type

- CRITICAL — RETURN VALUES: invoke() returns { success, hash, value } and query() returns { success, value }. To display results, use result.value (NOT result directly). If value could be an object/struct, use JSON.stringify(result.value). Example:
  const result = await invoke('flip', { ... });
  if (result) setMessage(`Won: ${result.value}`);  // CORRECT
  // WRONG: setMessage(`Result: ${result}`)  ← shows [object Object]
  For structs returned by query, access fields: result.value.field_name or display with JSON.stringify(result.value)

- CSS classes: container, card, card-header, btn, btn-secondary, input, label, status success/error, text-muted, spinner
- Dates: use `<input type="datetime-local">`, convert with `Math.floor(new Date(val).getTime()/1000)`
- Keep simple: 2-4 cards, balanced braces, complete code from first import to final `}`"""


REACT_AGENT_USER_PROMPT = """Create App.jsx for: {name} — {description}

CONTRACT FUNCTIONS (use ONLY these, param count must be exact):
{functions_detail}

UI: {ui_requirements}

Output COMPLETE App.jsx (no markdown, no explanation):"""


FIX_CODE_SYSTEM_PROMPT = """You are a React code fixer. You will be given React code that has issues and need to fix them.

Your job is to output the COMPLETE fixed code. Do not explain, just output the fixed code.

CRITICAL: Output the ENTIRE fixed code, not just the fix. The output must be a complete, working React component."""


FIX_CODE_USER_PROMPT = """The following React code has this issue: {issue}

Original code:
```jsx
{code}
```

Output the COMPLETE fixed code (the entire component, not just the fix):"""


MAX_RETRIES = 2


def validate_js_syntax(code: str) -> tuple[bool, str | None]:
    """
    Validate JavaScript/JSX syntax using Node.js.
    """
    import os

    try:
        with tempfile.NamedTemporaryFile(
            mode='w',
            suffix='.jsx',
            delete=False
        ) as f:
            f.write(code)
            f.flush()
            temp_path = f.name

            try:
                validate_script = '''
const fs = require("fs");
const code = fs.readFileSync(process.argv[2], "utf8");

let jsCode = code;
jsCode = jsCode.replace(/<[A-Za-z][^>]*\\/>/g, "null");
jsCode = jsCode.replace(/<[A-Za-z][^>]*>[\\s\\S]*?<\\/[A-Za-z]+>/g, "null");
jsCode = jsCode.replace(/<[A-Za-z][^>]*>/g, "null");
jsCode = jsCode.replace(/<\\/[A-Za-z]+>/g, "");
jsCode = jsCode.replace(/<>/g, "(");
jsCode = jsCode.replace(/<\\/>/g, ")");

try {
    new Function(jsCode);
    process.exit(0);
} catch (e) {
    console.error(e.message);
    process.exit(1);
}
'''
                result = subprocess.run(
                    ['node', '-e', validate_script, temp_path],
                    capture_output=True,
                    text=True,
                    timeout=5
                )

                if result.returncode == 0:
                    return True, None

                error = result.stderr.strip()
                if error:
                    return False, error[:200]
                return False, "Unknown syntax error"

            except subprocess.TimeoutExpired:
                return False, "Syntax check timed out"
            except FileNotFoundError:
                return True, None
            finally:
                try:
                    os.unlink(temp_path)
                except Exception:
                    pass

    except Exception as e:
        return True, None


def _extract_rust_fn_names(rust_code: str) -> list[str]:
    """Extract public function names from Rust contract code."""
    if not rust_code:
        return []
    pattern = r'pub\s+fn\s+(\w+)\s*\('
    return re.findall(pattern, rust_code)


def _extract_rust_u64_params(rust_code: str) -> set[str]:
    """Return set of (fn_name, param_name) pairs where param type is u64."""
    results = set()
    if not rust_code:
        return results
    fn_pattern = r'pub\s+fn\s+(\w+)\s*\((.*?)\)(?:\s*->\s*[\w:<>\s]+)?\s*\{'
    for match in re.finditer(fn_pattern, rust_code, re.DOTALL):
        fn_name = match.group(1)
        params_str = match.group(2)
        for param in params_str.split(','):
            param = param.strip()
            if ':' in param:
                pname, ptype = param.split(':', 1)
                if ptype.strip() == 'u64':
                    results.add((fn_name, pname.strip()))
    return results


def validate_and_fix_contract_calls(app_code: str, rust_code: str) -> str:
    """
    Post-generation validation: fix mismatched invoke/query method names
    and ensure u64 params use u64() wrapper instead of raw strings.
    Returns corrected code.
    """
    if not rust_code:
        return app_code

    rust_fns = _extract_rust_fn_names(rust_code)
    if not rust_fns:
        return app_code

    # Skip env-internal names
    rust_fns = [fn for fn in rust_fns if fn != 'new' and not fn.startswith('__')]

    # Find all invoke('xxx') and query('xxx') calls in the generated JSX
    call_pattern = r"""(invoke|query)\s*\(\s*['"](\w+)['"]\s*"""
    used_names = set()
    for match in re.finditer(call_pattern, app_code):
        used_names.add(match.group(2))

    if not used_names:
        return app_code

    # Build replacement map: for each used name not in rust_fns, find the best match
    replacements: dict[str, str] = {}
    for used_name in used_names:
        if used_name not in rust_fns:
            best = _best_match(used_name, rust_fns)
            if best:
                replacements[used_name] = best
                logger.warning(f"[REACT_AGENT] Fixing method name: '{used_name}' → '{best}'")

    # Apply name replacements
    for wrong, correct in replacements.items():
        # Replace in invoke('wrong') and query('wrong') patterns
        app_code = re.sub(
            rf"""(invoke|query)\s*\(\s*['"]{re.escape(wrong)}['"]""",
            rf"\1('{correct}'",
            app_code,
        )

    # Fix u64 params passed as raw strings instead of u64() wrappers
    u64_params = _extract_rust_u64_params(rust_code)
    if u64_params:
        # Find patterns like: paramName: "someString" or paramName: 'someString'
        # inside invoke/query arg objects, and replace with u64(number)
        for fn_name, param_name in u64_params:
            # Match: param_name: "string" or param_name: 'string' in invoke/query calls
            string_val_pattern = rf"""({re.escape(param_name)}\s*:\s*)(['"])([^'"]*)\2"""
            def _fix_u64_string(m):
                prefix = m.group(1)
                val = m.group(3)
                # Try to convert to number, fallback to 0
                try:
                    num = int(val)
                except (ValueError, TypeError):
                    # Map common string values to numbers
                    val_lower = val.lower()
                    if val_lower in ('heads', 'head', 'yes', 'true', 'a', 'option_a'):
                        num = 0
                    elif val_lower in ('tails', 'tail', 'no', 'false', 'b', 'option_b'):
                        num = 1
                    else:
                        num = 0
                logger.warning(f"[REACT_AGENT] Fixing u64 param: {param_name}: \"{val}\" → u64({num})")
                return f"{prefix}u64({num})"

            app_code = re.sub(string_val_pattern, _fix_u64_string, app_code)

    # Fix [object Object] bug: replace ${result} with ${result.value} in template literals
    # when result comes from invoke/query calls
    # Match patterns like: `...${someVar}...` where someVar was assigned from invoke/query
    invoke_query_vars = set()
    assign_pattern = r'(?:const|let|var)\s+(\w+)\s*=\s*await\s+(?:invoke|query)\s*\('
    for m in re.finditer(assign_pattern, app_code):
        invoke_query_vars.add(m.group(1))

    for var in invoke_query_vars:
        # Fix: ${var} → ${var?.value} in template literals (but not ${var.something} which is already accessing a field)
        # Only replace bare ${var} not ${var.field} or ${var?.field}
        bare_pattern = rf'\$\{{{re.escape(var)}\}}'
        if re.search(bare_pattern, app_code):
            app_code = re.sub(bare_pattern, f'${{{var}?.value}}', app_code)
            logger.warning(f"[REACT_AGENT] Fixing [object Object]: ${{{var}}} → ${{{var}?.value}}")

        # Also fix: ${JSON.stringify(var)} → ${JSON.stringify(var?.value)}
        json_pattern = rf'JSON\.stringify\(\s*{re.escape(var)}\s*\)'
        if re.search(json_pattern, app_code):
            app_code = re.sub(json_pattern, f'JSON.stringify({var}?.value)', app_code)
            logger.warning(f"[REACT_AGENT] Fixing JSON.stringify: {var} → {var}?.value")

    return app_code


def _best_match(wrong_name: str, candidates: list[str]) -> str | None:
    """Find the best matching function name from candidates using simple heuristics."""
    wrong_lower = wrong_name.lower()
    wrong_parts = set(re.split(r'[_\s]+', wrong_lower))

    best = None
    best_score = 0
    for candidate in candidates:
        cand_lower = candidate.lower()
        cand_parts = set(re.split(r'[_\s]+', cand_lower))

        # Exact substring match scores highest
        if wrong_lower in cand_lower or cand_lower in wrong_lower:
            score = 3
        else:
            # Score by overlapping word parts
            overlap = wrong_parts & cand_parts
            score = len(overlap)

        if score > best_score:
            best_score = score
            best = candidate

    # Only return if there's some meaningful overlap
    return best if best_score > 0 else (candidates[0] if len(candidates) == 1 else None)


async def generate_react_frontend(
    template_type: str,
    spec: dict,
    contract_id: str,
    rust_code: str,
    docs_context: list[str],
) -> ReactGenerationResult:
    """
    Generate React frontend code for the DApp.
    """
    logger.info(f"[REACT_AGENT] Starting frontend generation")
    logger.info(f"  - Type: {template_type}")
    logger.info(f"  - Contract ID: {contract_id}")
    logger.info(f"  - Spec name: {spec.get('name', 'Unknown')}")

    # Get base template and components
    base_template = get_frontend_template()
    components = get_frontend_components()

    # Generate initial code
    logger.info(f"[REACT_AGENT] Generating App.jsx...")

    app_code = await llm_generate_app(
        spec=spec,
        contract_id=contract_id,
        rust_code=rust_code,
        docs_context=docs_context,
    )

    if not app_code:
        logger.error("[REACT_AGENT] LLM returned empty response")
        raise ReactGenerationError("LLM returned empty response")

    logger.info(f"[REACT_AGENT] Initial code generated ({len(app_code)} chars)")

    # Post-generation validation: fix method names and u64 param types
    app_code = validate_and_fix_contract_calls(app_code, rust_code)

    # Validation with retries
    for attempt in range(MAX_RETRIES + 1):
        logger.info(f"[REACT_AGENT] Validation attempt {attempt + 1}/{MAX_RETRIES + 1}")

        structural_issues = check_structural_validity(app_code)

        if structural_issues is None:
            logger.info(f"[REACT_AGENT] Code validated successfully")
            return build_file_structure(
                app_code=app_code,
                base_template=base_template,
                components=components,
                spec=spec,
            )

        logger.warning(f"[REACT_AGENT] Structural issue found: {structural_issues}")

        if attempt < MAX_RETRIES:
            logger.info(f"[REACT_AGENT] Attempting to fix code...")
            fixed_code = await fix_code(app_code, structural_issues)

            if fixed_code:
                app_code = fixed_code
                logger.info(f"[REACT_AGENT] Code fixed ({len(app_code)} chars)")
            else:
                logger.error(f"[REACT_AGENT] Fix attempt returned empty")
                raise ReactGenerationError(f"Failed to fix: {structural_issues}")
        else:
            logger.warning(f"[REACT_AGENT] Max retries reached, returning code with potential issues")

    return build_file_structure(
        app_code=app_code,
        base_template=base_template,
        components=components,
        spec=spec,
    )


def extract_function_signatures(rust_code: str) -> str:
    """
    Parse public function signatures from Rust contract code.
    Returns a formatted string showing each function with its frontend-facing
    parameters (excluding env: Env) and type wrapping instructions.
    """
    if not rust_code:
        return ""

    pattern = r'pub\s+fn\s+(\w+)\s*\((.*?)\)(?:\s*->\s*([\w:<>\s]+))?\s*\{'
    matches = re.findall(pattern, rust_code, re.DOTALL)

    if not matches:
        return ""

    lines = []
    for name, params_str, return_type in matches:
        # Parse individual parameters
        params = [p.strip() for p in params_str.split(',') if p.strip()]

        # Remove env: Env (always first, implicit from frontend)
        frontend_params = []
        for p in params:
            if p.strip().startswith('env') and 'Env' in p:
                continue
            frontend_params.append(p.strip())

        ret = return_type.strip() if return_type else "void"

        # Determine if this is a read or write function
        is_query = name.startswith('get_') or name.startswith('is_') or name.startswith('has_')
        method_type = "query" if is_query else "invoke"

        # Format params with type wrapping hints
        param_hints = []
        for fp in frontend_params:
            parts = fp.split(':')
            if len(parts) == 2:
                pname = parts[0].strip()
                ptype = parts[1].strip()
                if 'Address' in ptype:
                    param_hints.append(f"{pname}: pass pubKey string directly")
                elif ptype == 'u64':
                    param_hints.append(f"{pname}: wrap with u64(number)")
                elif ptype == 'u32':
                    param_hints.append(f"{pname}: wrap with u32(number)")
                elif ptype == 'i128':
                    param_hints.append(f"{pname}: wrap with i128(amount)")
                elif ptype == 'bool':
                    param_hints.append(f"{pname}: pass true/false")
                elif ptype == 'Symbol':
                    param_hints.append(f"{pname}: wrap with sorobanSymbol('value')")
                elif ptype == 'String':
                    param_hints.append(f"{pname}: pass string directly")
                else:
                    param_hints.append(f"{pname}: {ptype}")

        param_count = len(param_hints)
        param_detail = ", ".join(param_hints) if param_hints else "no params"
        lines.append(f"- {method_type}('{name}', {{ {param_detail} }}) → {ret}  [{param_count} param(s)]")

    return "\n".join(lines)


async def llm_generate_app(
    spec: dict,
    contract_id: str,
    rust_code: str,
    docs_context: list[str],
) -> str | None:
    """Use LLM to generate custom App.jsx"""

    # Extract REAL function signatures from the compiled contract code
    parsed_signatures = extract_function_signatures(rust_code)

    if parsed_signatures:
        functions_detail = parsed_signatures
        logger.info(f"[REACT_AGENT] Parsed function signatures from rust code:\n{parsed_signatures}")
    else:
        # Fallback to spec if rust code parsing fails
        functions = spec.get("functions", [])
        functions_detail_lines = []
        for f in functions:
            if isinstance(f, dict):
                name = f.get("name", "unknown")
                params = f.get("params", [])
                returns = f.get("returns", "void")
                param_str = ", ".join(params) if params else "none"
                functions_detail_lines.append(f"- {name}({param_str}) → {returns}")
            else:
                functions_detail_lines.append(f"- {f}")
        functions_detail = "\n".join(functions_detail_lines) if functions_detail_lines else "Not specified"

    user_prompt = REACT_AGENT_USER_PROMPT.format(
        name=spec.get("name", "MyDApp"),
        description=spec.get("description", "A Stellar DApp")[:150],
        functions_detail=functions_detail,
        ui_requirements=", ".join(spec.get("ui_requirements", [])) or "Standard DApp interface",
    )

    logger.info(f"[REACT_AGENT] User prompt length: {len(user_prompt)} chars")

    response = await generate_completion(
        system_prompt=REACT_AGENT_SYSTEM_PROMPT,
        user_prompt=user_prompt,
        temperature=0.0,
        max_tokens=16384,
    )

    if not response:
        return None

    return extract_react_code(response)


async def fix_code(code: str, issue: str) -> str | None:
    """Use LLM to fix the code based on the identified issue"""
    
    logger.info(f"[REACT_AGENT] Fixing issue: {issue}")

    user_prompt = FIX_CODE_USER_PROMPT.format(code=code, issue=issue)

    response = await generate_completion(
        system_prompt=FIX_CODE_SYSTEM_PROMPT,
        user_prompt=user_prompt,
        temperature=0,
        max_tokens=16384,
    )

    if not response:
        return None

    return extract_react_code(response)


def check_structural_validity(code: str) -> str | None:
    """
    Check basic structural validity of the code.
    Returns None if valid, or a string describing the issue.
    """
    if not code or len(code.strip()) < 50:
        return "Code is too short or empty"

    if 'export default' not in code:
        return "Missing 'export default' statement"

    if 'function' not in code and '=>' not in code:
        return "Missing function definition"

    if 'return' not in code:
        return "Missing return statement"

    # Check for balanced braces
    open_braces = code.count('{')
    close_braces = code.count('}')
    if open_braces != close_braces:
        return f"Unbalanced braces: {open_braces} opening, {close_braces} closing"

    # Check for balanced parentheses
    open_parens = code.count('(')
    close_parens = code.count(')')
    if open_parens != close_parens:
        return f"Unbalanced parentheses: {open_parens} opening, {close_parens} closing"

    # Check for balanced brackets
    open_brackets = code.count('[')
    close_brackets = code.count(']')
    if open_brackets != close_brackets:
        return f"Unbalanced brackets: {open_brackets} opening, {close_brackets} closing"

    # Must end with closing brace
    stripped = code.rstrip()
    if not stripped.endswith('}'):
        return "Code does not end with closing brace - likely truncated"

    # Node.js syntax validation
    is_valid, js_error = validate_js_syntax(code)
    if not is_valid:
        return f"JavaScript syntax error: {js_error}"

    return None


def extract_react_code(response: str) -> str:
    """Extract React code from LLM response"""
    import re

    code_block = re.search(r'```(?:jsx?|javascript|react)?\s*([\s\S]*?)```', response)
    if code_block:
        return code_block.group(1).strip()

    if 'export default' in response or 'function App' in response or 'import' in response:
        lines = response.split('\n')
        code_lines = []
        in_code = False

        for line in lines:
            if line.strip().startswith('import ') or line.strip().startswith("'use client'") or in_code:
                in_code = True
                code_lines.append(line)

        return '\n'.join(code_lines) if code_lines else response

    return response


def build_file_structure(
    app_code: str,
    base_template: dict[str, str],
    components: dict[str, str],
    spec: dict,
) -> ReactGenerationResult:
    """Build the complete file structure"""
    
    logger.info(f"[REACT_AGENT] Building file structure")

    files = {
        "/App.js": app_code,
        "/index.css": base_template.get("index_css", DEFAULT_CSS),
    }

    # Add relevant components based on what's used in the code
    if "WalletConnect" in app_code and "WalletConnect" in components:
        files["/components/WalletConnect.jsx"] = components["WalletConnect"]
        logger.info(f"[REACT_AGENT] Added WalletConnect component")

    if "TxStatus" in app_code and "TxStatus" in components:
        files["/components/TxStatus.jsx"] = components["TxStatus"]
        logger.info(f"[REACT_AGENT] Added TxStatus component")

    if "BalanceDisplay" in app_code and "BalanceDisplay" in components:
        files["/components/BalanceDisplay.jsx"] = components["BalanceDisplay"]
        logger.info(f"[REACT_AGENT] Added BalanceDisplay component")

    logger.info(f"[REACT_AGENT] Total files generated: {len(files)}")
    
    return ReactGenerationResult(files=files)


DEFAULT_CSS = """
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  background: linear-gradient(135deg, #0a0a0a 0%, #1a1a2e 100%);
  color: #fafafa;
  min-height: 100vh;
}

.container {
  max-width: 600px;
  margin: 0 auto;
  padding: 2rem;
}

.card {
  background: rgba(26, 26, 46, 0.8);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 16px;
  padding: 1.5rem;
  margin-bottom: 1rem;
}

.btn {
  background: linear-gradient(135deg, #3b82f6 0%, #8b5cf6 100%);
  color: white;
  border: none;
  padding: 0.875rem 1.75rem;
  border-radius: 10px;
  font-size: 1rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
  width: 100%;
}

.btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 20px rgba(59, 130, 246, 0.4);
}

.btn:disabled {
  background: #404040;
  cursor: not-allowed;
  transform: none;
}

.input {
  width: 100%;
  background: rgba(0, 0, 0, 0.3);
  border: 1px solid rgba(255, 255, 255, 0.15);
  color: white;
  padding: 0.875rem 1rem;
  border-radius: 10px;
  font-size: 1rem;
  margin-bottom: 1rem;
}

.input:focus {
  outline: none;
  border-color: #3b82f6;
}

.status {
  padding: 0.75rem 1rem;
  border-radius: 10px;
  font-size: 0.875rem;
  margin-top: 1rem;
}

.status.success {
  background: rgba(22, 163, 74, 0.2);
  border: 1px solid rgba(22, 163, 74, 0.3);
  color: #86efac;
}

.status.error {
  background: rgba(220, 38, 38, 0.2);
  border: 1px solid rgba(220, 38, 38, 0.3);
  color: #fca5a5;
}

.status.loading {
  background: rgba(59, 130, 246, 0.2);
  border: 1px solid rgba(59, 130, 246, 0.3);
  color: #93c5fd;
}
"""
