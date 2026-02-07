"""
RAG Retriever - Query ChromaDB for relevant Stellar documentation

Retrieves relevant documentation chunks to provide context for code generation.
Uses Context7 as the primary documentation source, with static fallback docs as backup.
"""

import chromadb
import logging
from chromadb.config import Settings as ChromaSettings
from typing import Optional
from pathlib import Path

from app.core.config import settings
from app.rag.embeddings import get_embedding

logger = logging.getLogger(__name__)


# ChromaDB collections
COLLECTIONS = {
    "soroban-sdk": "soroban_sdk_docs",
    "stellar-sdk-js": "stellar_js_sdk_docs",
    "soroban-examples": "soroban_examples_docs",
}

# Mapping from doc_type to Context7 library names to try
CONTEXT7_LIBRARY_MAP = {
    "soroban-sdk": ["stellar/soroban-sdk", "stellar/rs-soroban-sdk"],
    "stellar-sdk-js": ["stellar/js-stellar-sdk"],
}

# Global ChromaDB client
_chroma_client: Optional[chromadb.PersistentClient] = None


def get_chroma_client() -> chromadb.PersistentClient:
    """Get or create ChromaDB client"""
    global _chroma_client

    if _chroma_client is None:
        persist_dir = Path(settings.chroma_persist_dir)
        persist_dir.mkdir(parents=True, exist_ok=True)

        _chroma_client = chromadb.PersistentClient(
            path=str(persist_dir),
            settings=ChromaSettings(anonymized_telemetry=False),
        )

    return _chroma_client


async def retrieve_context7_docs(query: str, doc_type: str) -> list[str]:
    """
    Fetch supplementary docs from Context7 for a given doc type.

    Returns a list of documentation strings, or an empty list on failure.
    This is non-fatal — errors are logged and silently ignored.
    """
    library_names = CONTEXT7_LIBRARY_MAP.get(doc_type)
    if not library_names:
        return []

    try:
        from app.services.context7 import search_library, get_library_docs
    except ImportError:
        logger.debug("Context7 service not available")
        return []

    docs: list[str] = []
    for lib_name in library_names:
        try:
            libraries = await search_library(lib_name)
            if not libraries:
                continue

            # Use the first matching library
            lib = libraries[0]
            lib_id = lib.get("id") or lib.get("library_id") or lib_name

            content = await get_library_docs(str(lib_id), topic=query)
            if content and content.strip():
                docs.append(content.strip())
                break  # Got docs from one library, no need to try alternatives
        except Exception as e:
            logger.debug(f"Context7 lookup failed for {lib_name}: {e}")
            continue

    return docs


async def retrieve_docs(
    query: str,
    doc_type: str = "soroban-sdk",
    top_k: int = None,
) -> list[str]:
    """
    Retrieve relevant documentation chunks for a query.
    
    IMPORTANT: For smart contract generation, we ALWAYS include the high-quality
    fallback docs first, then supplement with RAG results if relevant.
    
    Args:
        query: Search query (user prompt or specific question)
        doc_type: Type of docs to search (soroban-sdk, stellar-sdk-js, soroban-examples)
        top_k: Number of results to return (default from settings)
    
    Returns:
        List of relevant document chunks
    """
    
    top_k = top_k or settings.rag_top_k
    collection_name = COLLECTIONS.get(doc_type, COLLECTIONS["soroban-sdk"])
    
    # Context7 is the primary documentation source
    base_docs = []
    try:
        c7_docs = await retrieve_context7_docs(query, doc_type)
        if c7_docs:
            logger.info(f"Context7 returned {len(c7_docs)} doc(s) for {doc_type}")
            base_docs = c7_docs
    except Exception as e:
        logger.debug(f"Context7 retrieval failed: {e}")

    # Fall back to static docs only if Context7 returned nothing
    if not base_docs:
        base_docs = get_fallback_docs(doc_type)

    try:
        client = get_chroma_client()
        
        # Get collection
        try:
            collection = client.get_collection(collection_name)
        except Exception:
            # Collection doesn't exist, return just fallback docs
            return base_docs if base_docs else get_fallback_docs(doc_type)
        
        # Get query embedding
        query_embedding = await get_embedding(query)
        
        if not query_embedding:
            return base_docs if base_docs else get_fallback_docs(doc_type)
        
        # Query collection
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            include=["documents", "metadatas"],
        )
        
        # Extract documents
        docs = results.get("documents", [[]])[0]
        
        if docs:
            # Filter out irrelevant docs (iOS, Android, mobile apps, tutorials not about Rust)
            irrelevant_keywords = [
                "SwiftBasicPay", "iOS", "Android", "mobile app", "iPhone", "iPad",
                "Kotlin", "Java", "Swift", "flutter", "react native",
            ]
            
            filtered_docs = []
            for doc in docs:
                # Skip if contains irrelevant keywords
                is_irrelevant = any(kw.lower() in doc.lower() for kw in irrelevant_keywords)
                # Skip if it's a duplicate of fallback docs
                is_duplicate = any(doc[:100] in base_doc for base_doc in base_docs)
                
                if not is_irrelevant and not is_duplicate:
                    filtered_docs.append(doc)
            
            # Combine: fallback docs first (guaranteed quality), then filtered RAG docs
            return base_docs + filtered_docs[:3]  # Limit RAG additions
        
        return base_docs if base_docs else get_fallback_docs(doc_type)
        
    except Exception as e:
        print(f"RAG retrieval error: {e}")
        return base_docs if base_docs else get_fallback_docs(doc_type)


def get_fallback_docs(doc_type: str) -> list[str]:
    """
    Return fallback documentation when RAG is unavailable.
    
    These are essential snippets that should always be available.
    """
    
    if doc_type == "soroban-sdk":
        return SOROBAN_FALLBACK_DOCS
    elif doc_type == "stellar-sdk-js":
        return STELLAR_JS_FALLBACK_DOCS
    else:
        return SOROBAN_FALLBACK_DOCS


# Fallback documentation

SOROBAN_FALLBACK_DOCS = [
    """
# Soroban Contract Structure (SDK 21.0.0)

Every Soroban contract must:
1. Use `#![no_std]` - contracts run in a WASM environment
2. Import from `soroban_sdk`
3. Use `#[contract]` attribute on the contract struct
4. Use `#[contractimpl]` attribute on the impl block

```rust
#![no_std]
use soroban_sdk::{contract, contractimpl, Env, String};

#[contract]
pub struct MyContract;

#[contractimpl]
impl MyContract {
    pub fn hello(env: Env) -> String {
        // IMPORTANT: Use String::from_str with env reference
        String::from_str(&env, "Hello")
    }
}
```
""",
    """
# CRITICAL SDK 21.0.0 GOTCHAS - READ BEFORE CODING!

## 1. Map takes OWNED values, NOT references!
```rust
// WRONG - causes compilation error!
balances.get(&user)           // ERROR: expected Address, found &Address
balances.contains_key(&key)   // ERROR!

// CORRECT - use .clone() for owned values
balances.get(user.clone())
balances.contains_key(key.clone())
balances.set(user.clone(), amount)
```

## 2. Vec uses push_back(), NOT push()!
```rust
// WRONG
items.push(value);  // ERROR: no method named `push`

// CORRECT
items.push_back(value);
```

## 3. Custom structs in Vec need #[derive(Clone)]!
```rust
#[contracttype]
#[derive(Clone)]  // REQUIRED for .iter() to work!
pub struct MyStruct { ... }
```

## 4. No to_string() in no_std!
```rust
// WRONG - to_string() doesn't exist
let id = num.to_string();  // ERROR!

// CORRECT - use integers directly
let id: u64 = counter;
```
""",
    """
# Symbol and String Creation in SDK 21.0.0

## Symbol - ALWAYS use Symbol::new()
```rust
use soroban_sdk::{Symbol, Env};

// CORRECT - always pass env reference
let sym = Symbol::new(&env, "my_key");

// For short symbols (9 chars or less)
use soroban_sdk::symbol_short;
let short = symbol_short!("short");

// WRONG - does NOT exist in SDK 21
// Symbol::from("key")  // COMPILATION ERROR!
```

## String - ALWAYS use String::from_str()
```rust
use soroban_sdk::{String, Env};

// CORRECT - always pass env reference
let s = String::from_str(&env, "hello world");

// WRONG - does NOT exist in SDK 21
// String::from("hello")  // COMPILATION ERROR!
```
""",
    """
# Authentication in Soroban

Use `require_auth()` to verify that an address has authorized an action.
This MUST be called BEFORE any state changes.

```rust
use soroban_sdk::{contract, contractimpl, Address, Env};

#[contract]
pub struct MyContract;

#[contractimpl]
impl MyContract {
    pub fn transfer(env: Env, from: Address, to: Address, amount: i128) {
        // MUST verify auth FIRST, before any state changes
        from.require_auth();
        
        // Now safe to proceed with transfer logic...
    }
    
    pub fn admin_action(env: Env, caller: Address) {
        caller.require_auth();
        
        // Verify caller is admin
        let admin: Address = env.storage().instance().get(&DataKey::Admin).unwrap();
        if caller != admin {
            panic!("unauthorized");
        }
    }
}
```
""",
    """
# Soroban Storage Patterns

Use contracttype enum for storage keys:

```rust
use soroban_sdk::{contracttype, Address, Env};

#[contracttype]
#[derive(Clone)]
pub enum DataKey {
    Admin,                      // Simple key
    Counter,                    // Simple key  
    Balance(Address),           // Parameterized key
    Allowance(Address, Address), // Multi-param key
}

// Write to storage
env.storage().instance().set(&DataKey::Admin, &admin_address);
env.storage().instance().set(&DataKey::Counter, &count);

// Read with default value
let count: u64 = env.storage().instance().get(&DataKey::Counter).unwrap_or(0);

// Read required value (panics if missing)
let admin: Address = env.storage().instance().get(&DataKey::Admin).unwrap();

// Check if key exists
let exists: bool = env.storage().instance().has(&DataKey::Admin);

// Persistent storage for user data (longer TTL)
env.storage().persistent().set(&DataKey::Balance(user.clone()), &amount);
let bal: i128 = env.storage().persistent().get(&DataKey::Balance(user)).unwrap_or(0);
```
""",
    """
# Token Operations in Soroban

Use the `token` module to interact with Stellar assets:

```rust
use soroban_sdk::{contract, contractimpl, token, Address, Env, Symbol};

#[contract]
pub struct TokenVault;

#[contractimpl]
impl TokenVault {
    pub fn deposit(env: Env, from: Address, token_addr: Address, amount: i128) {
        from.require_auth();
        
        let client = token::Client::new(&env, &token_addr);
        
        // Transfer from user to this contract
        client.transfer(&from, &env.current_contract_address(), &amount);
        
        // Emit event
        env.events().publish((Symbol::new(&env, "deposit"),), (from, amount));
    }

    pub fn withdraw(env: Env, to: Address, token_addr: Address, amount: i128) {
        to.require_auth();
        
        let client = token::Client::new(&env, &token_addr);
        
        // Transfer from contract to user
        client.transfer(&env.current_contract_address(), &to, &amount);
        
        env.events().publish((Symbol::new(&env, "withdraw"),), (to, amount));
    }

    pub fn get_balance(env: Env, user: Address, token_addr: Address) -> i128 {
        let client = token::Client::new(&env, &token_addr);
        client.balance(&user)
    }
}
```
""",
    """
# Events and Custom Errors

## Publishing Events
```rust
use soroban_sdk::{Symbol, Env};

// Publish event with topics and data
env.events().publish(
    (Symbol::new(&env, "transfer"),),  // Topics tuple
    (from.clone(), to.clone(), amount)  // Data tuple
);

// Multiple topics
env.events().publish(
    (Symbol::new(&env, "action"), Symbol::new(&env, "completed")),
    (user, value)
);
```

## Custom Errors
```rust
use soroban_sdk::contracterror;

#[contracterror]
#[derive(Copy, Clone, Debug, Eq, PartialEq, PartialOrd, Ord)]
#[repr(u32)]
pub enum ContractError {
    NotInitialized = 1,
    AlreadyInitialized = 2,
    Unauthorized = 3,
    InsufficientBalance = 4,
    InvalidAmount = 5,
}

// Usage
pub fn withdraw(env: Env, amount: i128) -> Result<(), ContractError> {
    if amount <= 0 {
        return Err(ContractError::InvalidAmount);
    }
    // Or simply panic
    // panic!("invalid amount");
    Ok(())
}
```
""",
]


STELLAR_JS_FALLBACK_DOCS = [
    """
# Connecting to Freighter Wallet

Freighter is the recommended wallet for Stellar/Soroban:

```javascript
import freighter from '@stellar/freighter-api';

// Check if Freighter is installed
const isInstalled = await freighter.isConnected();

// Request access
await freighter.setAllowed();

// Get user's public key
const publicKey = await freighter.getPublicKey();

// Get network
const network = await freighter.getNetwork();
```
""",
    """
# Using Stellar SDK with Soroban

```javascript
import { SorobanRpc, Contract, TransactionBuilder } from '@stellar/stellar-sdk';

const server = new SorobanRpc.Server('https://soroban-testnet.stellar.org');

// Create contract client
const contract = new Contract(contractId);

// Build transaction
const tx = new TransactionBuilder(account, {
    fee: '100',
    networkPassphrase: Networks.TESTNET,
})
    .addOperation(contract.call('method_name', ...args))
    .setTimeout(30)
    .build();

// Simulate first
const simResult = await server.simulateTransaction(tx);

// Prepare (adds auth & resource info)
const preparedTx = await server.prepareTransaction(tx);

// Sign with Freighter
const signedXdr = await freighter.signTransaction(preparedTx.toXDR());

// Submit
const result = await server.sendTransaction(TransactionBuilder.fromXDR(signedXdr));
```
""",
    """
# Handling Transaction Results

```javascript
// Wait for transaction confirmation
async function waitForTx(hash, server) {
    let response;
    do {
        response = await server.getTransaction(hash);
        if (response.status === 'NOT_FOUND') {
            await new Promise(r => setTimeout(r, 1000));
        }
    } while (response.status === 'NOT_FOUND');
    
    if (response.status === 'SUCCESS') {
        return response.returnValue;
    } else {
        throw new Error(`Transaction failed: ${response.status}`);
    }
}
```
""",
]


async def search_all_docs(
    query: str,
    top_k: int = 5,
) -> dict[str, list[str]]:
    """
    Search all documentation collections.
    
    Returns results grouped by doc type.
    """
    results = {}
    
    for doc_type in COLLECTIONS.keys():
        docs = await retrieve_docs(query, doc_type, top_k)
        results[doc_type] = docs
    
    return results
