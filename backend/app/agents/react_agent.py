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


## Documentation is now fetched via Context7 and passed through the pipeline as docs_context.


class ReactGenerationResult(TypedDict):
    files: dict[str, str]


class ReactGenerationError(Exception):
    """Raised when React code generation fails after all retries"""
    pass


REACT_AGENT_SYSTEM_PROMPT = """You are a React frontend expert. You generate COMPLETE, WORKING App.jsx files for Stellar DApps.

## ABSOLUTE RULES:
1. Output ONLY valid JSX code — no markdown, no explanation, no code fences
2. ALL braces, parentheses, brackets MUST be balanced
3. MUST have `export default function App()`
4. MUST import useState from 'react' and useContract from './hooks/useContract'
5. MUST import './index.css' for styling
6. Do NOT truncate — output the COMPLETE component from first import to final closing brace
7. For any field representing a deadline, timestamp, or date: use `<input type="datetime-local">` (NOT `type="number"`).
   Set a default value via `new Date(Date.now() + 30*24*60*60*1000).toISOString().slice(0, 16)` (30 days from now).
   Convert to Unix timestamp (seconds) before passing to `invoke()`: `Math.floor(new Date(value).getTime() / 1000)`.
8. Keep it SIMPLE — one card per action, max 3-4 cards total
9. Every handler function must call `getPublicKey()` first for wallet address

## useContract HOOK API (import from './hooks/useContract'):
```js
const { invoke, query, loading, error, txStatus, checkWallet, getPublicKey, u64, i128 } = useContract();
// invoke(methodName, argsObject) — calls contract method that changes state, returns { success: true }
// query(methodName, argsObject) — read-only call, returns { value: '...' } or { success: true }
// loading — boolean, true during any call
// error — string or null
// txStatus — 'preparing' | 'signing' | 'submitting' | 'confirmed' | 'failed' | null
// checkWallet() — returns true if Freighter connected
// getPublicKey() — returns wallet address string
//
// TYPE HELPERS (CRITICAL — use these to avoid type mismatch errors!):
// u64(value)  — wraps value as u64 (for IDs, counts, timestamps, durations)
// i128(value) — wraps value as i128 (for token amounts, prices, balances)
//
// RULE: Address params → just pass the string (auto-detected from G.../C... format)
// RULE: u64 params (IDs, counts, timestamps) → wrap with u64()
// RULE: i128 params (amounts, prices) → wrap with i128()
// RULE: String params → just pass the string (auto-detected)
// RULE: bool params → just pass true/false
```

## AVAILABLE CSS CLASSES (from index.css — use className, not inline styles):
- `.container` — max-width centered layout
- `.card` — glassmorphism card with dark bg, blur, border
- `.card-header` — card title styling
- `.btn` — gradient button (blue→purple), full width
- `.btn:disabled` — gray disabled state
- `.btn-secondary` — subtle outline button
- `.input` — dark input field with border
- `.label` — form label
- `.status.success` / `.status.error` / `.status.loading` — status badges
- `.text-muted` — gray text
- `.text-small` — smaller font
- `.mb-1` `.mb-2` `.mb-3` `.mt-1` `.mt-2` — spacing utilities
- `.spinner` — CSS loading spinner

## WORKING EXAMPLE — NFT Minting DApp (follow this exact pattern):
```jsx
import { useState } from 'react';
import { useContract } from './hooks/useContract';
import './index.css';

export default function App() {
  const { invoke, query, loading, error, txStatus, getPublicKey, u64, i128 } = useContract();
  const [name, setName] = useState('');
  const [uri, setUri] = useState('');
  const [tokenId, setTokenId] = useState('');
  const [nftInfo, setNftInfo] = useState(null);
  const [result, setResult] = useState(null);

  const handleInitialize = async () => {
    const pubKey = await getPublicKey();
    if (!pubKey) return;
    const res = await invoke('initialize', { admin: pubKey });
    if (res) setResult('Contract initialized!');
  };

  const handleMint = async () => {
    const pubKey = await getPublicKey();
    if (!pubKey) return;
    const res = await invoke('mint', { to: pubKey, name: name, uri: uri });
    if (res) setResult('NFT minted successfully!');
  };

  const handleLookup = async () => {
    const res = await query('get_nft', { id: u64(tokenId) });
    if (res && res.value) setNftInfo(res.value);
  };

  return (
    <div className="container">
      <h1 style={{ fontSize: '2rem', fontWeight: 700, marginBottom: '0.5rem' }}>NFT Minting</h1>
      <p className="text-muted mb-3">Mint and manage NFTs on Stellar</p>

      <div className="card">
        <div className="card-header">Initialize</div>
        <button className="btn btn-secondary" onClick={handleInitialize} disabled={loading}>
          {loading ? 'Initializing...' : 'Initialize Contract'}
        </button>
      </div>

      <div className="card">
        <div className="card-header">Mint NFT</div>
        <label className="label">Name</label>
        <input className="input" placeholder="My NFT" value={name} onChange={e => setName(e.target.value)} />
        <label className="label">URI / Image URL</label>
        <input className="input" placeholder="https://..." value={uri} onChange={e => setUri(e.target.value)} />
        <button className="btn" onClick={handleMint} disabled={loading}>
          {loading ? <><span className="spinner" /> Minting...</> : 'Mint NFT'}
        </button>
        {error && <div className="status error mt-2">{error}</div>}
        {txStatus === 'confirmed' && <div className="status success mt-2">Transaction confirmed!</div>}
        {result && <div className="status success mt-2">{result}</div>}
      </div>

      <div className="card">
        <div className="card-header">Lookup NFT</div>
        <label className="label">Token ID</label>
        <input className="input" type="number" placeholder="1" value={tokenId} onChange={e => setTokenId(e.target.value)} />
        <button className="btn btn-secondary" onClick={handleLookup} disabled={loading}>
          {loading ? 'Loading...' : 'Look Up'}
        </button>
        {nftInfo && <div className="text-small mt-2">Owner: {JSON.stringify(nftInfo)}</div>}
      </div>
    </div>
  );
}
```

## WORKING EXAMPLE — Token Vault DApp:
```jsx
import { useState } from 'react';
import { useContract } from './hooks/useContract';
import './index.css';

export default function App() {
  const { invoke, query, loading, error, txStatus, getPublicKey, i128 } = useContract();
  const [amount, setAmount] = useState('');
  const [balance, setBalance] = useState(null);
  const [result, setResult] = useState(null);

  const handleDeposit = async () => {
    const pubKey = await getPublicKey();
    if (!pubKey) return;
    const res = await invoke('deposit', { from: pubKey, amount: i128(amount) });
    if (res) { setResult('Deposit successful!'); setAmount(''); }
  };

  const handleWithdraw = async () => {
    const pubKey = await getPublicKey();
    if (!pubKey) return;
    const res = await invoke('withdraw', { to: pubKey, amount: i128(amount) });
    if (res) { setResult('Withdrawal successful!'); setAmount(''); }
  };

  const handleGetBalance = async () => {
    const pubKey = await getPublicKey();
    if (!pubKey) return;
    const res = await query('get_balance', { user: pubKey });
    if (res) setBalance(res.value);
  };

  return (
    <div className="container">
      <h1 style={{ fontSize: '2rem', fontWeight: 700, marginBottom: '0.5rem' }}>Token Vault</h1>
      <p className="text-muted mb-3">Deposit and withdraw tokens securely</p>

      <div className="card">
        <div className="card-header">Deposit / Withdraw</div>
        <label className="label">Amount</label>
        <input className="input" type="number" placeholder="100" value={amount} onChange={e => setAmount(e.target.value)} />
        <div style={{ display: 'flex', gap: '0.5rem' }}>
          <button className="btn" onClick={handleDeposit} disabled={loading} style={{ flex: 1 }}>
            {loading ? <><span className="spinner" /> Processing...</> : 'Deposit'}
          </button>
          <button className="btn btn-secondary" onClick={handleWithdraw} disabled={loading} style={{ flex: 1 }}>
            Withdraw
          </button>
        </div>
        {error && <div className="status error mt-2">{error}</div>}
        {txStatus === 'confirmed' && <div className="status success mt-2">Transaction confirmed!</div>}
        {result && <div className="status success mt-2">{result}</div>}
      </div>

      <div className="card">
        <div className="card-header">Balance</div>
        <button className="btn btn-secondary" onClick={handleGetBalance} disabled={loading}>Check Balance</button>
        {balance !== null && <div className="text-small mt-2">Your balance: {balance}</div>}
      </div>
    </div>
  );
}
```

## CRITICAL TYPE RULES for invoke/query arguments:
- Address params (from, to, admin, voter, creator, etc.) → just pass the pubKey string directly
- u64 params (IDs like proposal_id, campaign_id, token_id, also counts, timestamps, durations) → wrap with u64()
- i128 params (amounts like amount, price, goal, balance) → wrap with i128()
- String params (name, title, uri, description) → just pass the string directly
- bool params (approve, active) → just pass true/false
- ALWAYS destructure u64 and i128 from useContract: `const { invoke, query, ..., u64, i128 } = useContract();`
- ONLY pass arguments that match the contract function signature — do NOT add extra args

Generate code that follows these EXACT patterns. Keep it simple: 2-4 cards, clear handlers, balanced braces."""


REACT_AGENT_USER_PROMPT = """Create App.jsx for this DApp. Follow the EXACT pattern from the system prompt examples.

## Contract: {name}
## Description: {description}
## Contract ID: {contract_id}

## CONTRACT FUNCTION SIGNATURES (AUTHORITATIVE — use ONLY these):
{functions_detail}

CRITICAL: The parameter count above is EXACT. Passing more or fewer params causes MismatchingParameterLen errors.
- env: Env is implicit — NEVER pass it from the frontend
- ONLY pass the parameters listed above — do NOT add extra parameters
- Do NOT guess or infer additional parameters not listed above

## Full contract source (for reference only — use signatures above for invoke/query calls):
{rust_code}
{docs_context_section}

## UI Requirements: {ui_requirements}

## MANDATORY RULES:
- Start with `import {{ useState }} from 'react';`
- Import useContract from './hooks/useContract' and './index.css'
- `export default function App()` — named export
- Destructure BOTH type helpers AND hook methods: `const {{ invoke, query, loading, error, txStatus, getPublicKey, u64, i128 }} = useContract();`
- Use `invoke('function_name', {{ param: value }})` for write functions (functions that change state)
- Use `query('function_name', {{ param: value }})` for read/get functions
- CRITICAL TYPE WRAPPING:
  * u64 params (any ID, count, timestamp, duration) → wrap with u64(): `{{ id: u64(value) }}`
  * i128 params (any amount, price, balance, goal) → wrap with i128(): `{{ amount: i128(value) }}`
  * Address params → just pass the string pubKey directly (auto-detected)
  * String params → just pass the string directly
  * bool params → just pass true/false
- ONLY pass arguments that EXACTLY match the contract function params — no extra args!
- ALWAYS call `getPublicKey()` first in every handler to get the wallet address
- Use CSS classes: container, card, card-header, btn, input, label, status, text-muted
- Add loading states with the spinner class
- Show error and txStatus feedback
- Keep it SIMPLE: 2-4 cards maximum, one per action group
- Output the COMPLETE code from first import to final closing brace `}}`
- NO markdown code fences, NO explanations — just the JSX code
- ALL braces MUST be balanced

Output ONLY the complete App.jsx code now:"""


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
                    param_hints.append(f"{pname}: wrap with u64()")
                elif ptype == 'i128':
                    param_hints.append(f"{pname}: wrap with i128()")
                elif ptype == 'bool':
                    param_hints.append(f"{pname}: pass true/false")
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
    # These are authoritative — they override the architect's spec
    parsed_signatures = extract_function_signatures(rust_code)

    if parsed_signatures:
        functions_detail = f"EXACT SIGNATURES FROM DEPLOYED CONTRACT (use ONLY these — parameter count MUST match):\n{parsed_signatures}"
        logger.info(f"[REACT_AGENT] Parsed function signatures from rust code:\n{parsed_signatures}")
    else:
        # Fallback to spec if rust code parsing fails
        functions = spec.get("functions", [])
        functions_detail_lines = []
        for f in functions:
            if isinstance(f, dict):
                name = f.get("name", "unknown")
                desc = f.get("description", "")
                params = f.get("params", [])
                returns = f.get("returns", "void")
                param_str = ", ".join(params) if params else "none"
                functions_detail_lines.append(f"- {name}({param_str}) → {returns}: {desc}")
            else:
                functions_detail_lines.append(f"- {f}")
        functions_detail = "\n".join(functions_detail_lines) if functions_detail_lines else "Not specified"

    # Format docs context from Context7
    docs_context_section = ""
    if docs_context:
        docs_text = "\n\n".join(docs_context[:3])
        if len(docs_text) > 2000:
            docs_text = docs_text[:2000]
        docs_context_section = f"\n## Stellar JS SDK Reference (from Context7):\n{docs_text}"

    user_prompt = REACT_AGENT_USER_PROMPT.format(
        contract_id=contract_id,
        name=spec.get("name", "MyDApp"),
        description=spec.get("description", "A Stellar DApp"),
        functions_detail=functions_detail,
        rust_code=rust_code or "Not available",
        docs_context_section=docs_context_section,
        ui_requirements=", ".join(spec.get("ui_requirements", [])) or "Standard DApp interface",
    )

    logger.info(f"[REACT_AGENT] User prompt length: {len(user_prompt)} chars")

    response = await generate_completion(
        system_prompt=REACT_AGENT_SYSTEM_PROMPT,
        user_prompt=user_prompt,
        temperature=0.0,  # Deterministic — nail it on first try
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
