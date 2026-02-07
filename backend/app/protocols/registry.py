"""
Curated registry of Stellar ecosystem protocols.

Each protocol entry contains metadata + an integration_prompt that gives the AI
enough context to integrate the protocol into a generated DApp.
"""

from typing import TypedDict, Optional


class Protocol(TypedDict):
    id: str
    name: str
    description: str
    category: str  # DEX, Lending, DeFi, Data, Payments, Token, Security, Infrastructure
    icon: str  # lucide-react icon name (e.g. "candlestick-chart")
    integration_prompt: str  # detailed AI prompt context for integration
    sdk_package: Optional[str]  # npm package name if applicable
    docs_url: Optional[str]  # documentation URL


PROTOCOLS: list[Protocol] = [
    {
        "id": "stellar-dex",
        "name": "Stellar DEX",
        "description": "Built-in decentralized exchange on Stellar with order book trading, path payments, and manage offers.",
        "category": "DEX",
        "icon": "candlestick-chart",
        "sdk_package": "@stellar/stellar-sdk",
        "docs_url": "https://developers.stellar.org/docs/encyclopedia/liquidity-on-stellar-sdex-liquidity-pools",
        "integration_prompt": """Integrate Stellar DEX (SDEX) functionality using the Stellar SDK.

Key capabilities to add:
- **Manage Buy/Sell Offers**: Use `Operation.manageSellOffer()` and `Operation.manageBuyOffer()` to place limit orders on the SDEX order book.
- **Path Payments**: Use `Operation.pathPaymentStrictSend()` or `Operation.pathPaymentStrictReceive()` for cross-asset swaps that automatically find the best path through the order book.
- **Order Book Queries**: Use the Horizon API `server.orderbook(selling, buying).call()` to fetch current bids/asks for an asset pair.
- **Trade Aggregations**: Use `server.tradeAggregations()` to get OHLCV candle data for price charts.

SDK patterns:
```javascript
import { Asset, Operation, TransactionBuilder } from '@stellar/stellar-sdk';

// Create a sell offer
const tx = new TransactionBuilder(account, { fee, networkPassphrase })
  .addOperation(Operation.manageSellOffer({
    selling: new Asset('USDC', issuer),
    buying: Asset.native(),
    amount: '100',
    price: '0.5',
    offerId: '0' // 0 = new offer
  }))
  .setTimeout(30)
  .build();

// Path payment (auto-routed swap)
Operation.pathPaymentStrictSend({
  sendAsset: Asset.native(),
  sendAmount: '10',
  destination: destAddress,
  destAsset: new Asset('USDC', issuer),
  destMin: '4.5',
  path: [] // empty = auto-find path
});
```

UI components to add: Asset pair selector, order book display, swap form with slippage, open orders list, trade history.""",
    },
    {
        "id": "soroswap",
        "name": "Soroswap",
        "description": "Automated Market Maker (AMM) DEX built on Soroban with liquidity pools and token swaps.",
        "category": "DEX",
        "icon": "arrow-left-right",
        "sdk_package": "soroswap-router-sdk",
        "docs_url": "https://docs.soroswap.finance",
        "integration_prompt": """Integrate Soroswap AMM DEX for token swaps and liquidity provision on Soroban.

Key capabilities:
- **Token Swaps**: Call the Soroswap Router contract to swap between any two tokens with auto-routing through liquidity pools.
- **Add Liquidity**: Provide token pairs to liquidity pools and receive LP tokens.
- **Remove Liquidity**: Burn LP tokens to withdraw underlying token pairs.
- **Price Quotes**: Query the router for expected output amounts before swapping.

Soroswap Router contract interaction pattern:
```javascript
import { Contract, nativeToScVal, Address } from '@stellar/stellar-sdk';

// Soroswap Router contract (Testnet)
const ROUTER_CONTRACT = 'ROUTER_CONTRACT_ID_HERE';
const router = new Contract(ROUTER_CONTRACT);

// Swap exact tokens for tokens
const swapCall = router.call(
  'swap_exact_tokens_for_tokens',
  nativeToScVal(amountIn, { type: 'i128' }),
  nativeToScVal(amountOutMin, { type: 'i128' }),
  nativeToScVal(path, { type: 'Vec<Address>' }), // [tokenA, tokenB]
  new Address(userAddress).toScVal(),
  nativeToScVal(deadline, { type: 'u64' })
);
```

UI components to add: Token swap form with amount inputs, price impact display, liquidity pool list, add/remove liquidity forms, LP token balance display.""",
    },
    {
        "id": "blend-protocol",
        "name": "Blend Protocol",
        "description": "Decentralized lending and borrowing protocol on Soroban with variable interest rates and collateral management.",
        "category": "Lending",
        "icon": "landmark",
        "sdk_package": "@blend-capital/blend-sdk",
        "docs_url": "https://docs.blend.capital",
        "integration_prompt": """Integrate Blend Protocol for lending and borrowing on Soroban.

Key capabilities:
- **Supply Assets**: Deposit tokens into lending pools to earn yield.
- **Borrow Assets**: Borrow tokens against collateral with variable interest rates.
- **Repay Loans**: Repay borrowed assets to reduce debt position.
- **Manage Collateral**: Add/remove collateral to manage health factor.
- **Query Positions**: Check user positions, interest rates, and pool stats.

Blend Pool contract interaction:
```javascript
import { Contract, nativeToScVal, Address } from '@stellar/stellar-sdk';

const BLEND_POOL = 'POOL_CONTRACT_ID';
const pool = new Contract(BLEND_POOL);

// Supply tokens to earn yield
const supplyCall = pool.call(
  'supply',
  new Address(userAddress).toScVal(),
  nativeToScVal(reserveIndex, { type: 'u32' }),
  nativeToScVal(amount, { type: 'i128' })
);

// Borrow tokens against collateral
const borrowCall = pool.call(
  'borrow',
  new Address(userAddress).toScVal(),
  nativeToScVal(reserveIndex, { type: 'u32' }),
  nativeToScVal(amount, { type: 'i128' })
);
```

UI components to add: Supply/borrow forms, position overview dashboard, interest rate display, health factor indicator, market overview table with TVL and rates.""",
    },
    {
        "id": "phoenix-protocol",
        "name": "Phoenix Protocol",
        "description": "DeFi hub on Soroban offering AMM liquidity pools, staking, and multi-hop swaps.",
        "category": "DeFi",
        "icon": "flame",
        "sdk_package": None,
        "docs_url": "https://docs.phoenix-hub.io",
        "integration_prompt": """Integrate Phoenix Protocol DeFi hub for AMM swaps, staking, and liquidity on Soroban.

Key capabilities:
- **Multi-hop Swaps**: Swap tokens through multiple pools for best price routing.
- **Liquidity Provision**: Provide liquidity to Phoenix AMM pools.
- **Staking**: Stake PHO tokens or LP tokens for rewards.
- **Pool Queries**: Get pool reserves, swap rates, and TVL.

Phoenix Factory/Pool contract interaction:
```javascript
import { Contract, nativeToScVal, Address } from '@stellar/stellar-sdk';

const PHOENIX_FACTORY = 'FACTORY_CONTRACT_ID';
const factory = new Contract(PHOENIX_FACTORY);

// Query available pools
const poolsCall = factory.call('query_pools');

// Swap via a specific pool
const pool = new Contract(poolContractId);
const swapCall = pool.call(
  'swap',
  new Address(sender).toScVal(),
  nativeToScVal(offerAmount, { type: 'i128' }),
  nativeToScVal(askAssetMinAmount, { type: 'i128' }),
  nativeToScVal(maxSpread, { type: 'i64' })
);
```

UI components to add: Multi-hop swap interface, pool explorer, stake/unstake forms, rewards dashboard, portfolio overview.""",
    },
    {
        "id": "aquarius",
        "name": "Aquarius",
        "description": "Liquidity management protocol for Stellar with voting-based reward distribution and liquidity incentives.",
        "category": "Liquidity",
        "icon": "waves",
        "sdk_package": None,
        "docs_url": "https://aqua.network/",
        "integration_prompt": """Integrate Aquarius liquidity management for reward voting and liquidity incentives.

Key capabilities:
- **AQUA Voting**: Vote for market pairs to receive AQUA liquidity rewards.
- **Reward Claims**: Claim accrued AQUA rewards from liquidity provision.
- **Liquidity Incentives**: Display which pools are currently incentivized with AQUA rewards.
- **Market Pair Discovery**: Query which trading pairs have active AQUA reward campaigns.

Integration via Stellar SDK + Aquarius API:
```javascript
// Query active voting campaigns
const response = await fetch('https://voting-tracker.aqua.network/api/voting-snapshot/');
const campaigns = await response.json();

// Vote for a market pair using AQUA tokens
import { Asset, Operation } from '@stellar/stellar-sdk';
const AQUA = new Asset('AQUA', 'GBNZILSTVQZ4R7IKQDGHYGY2QXL5QOFJYQMXPKWRRM5PAV7Y4M67TQ2');

// Lock AQUA to vote
const lockOp = Operation.changeTrust({ asset: voteLockAsset });
```

UI components to add: Voting interface for market pairs, reward tracking dashboard, incentivized pools list, AQUA balance display.""",
    },
    {
        "id": "mercury",
        "name": "Mercury",
        "description": "Soroban data indexer providing real-time event streaming, contract state queries, and historical data subscriptions.",
        "category": "Data",
        "icon": "satellite",
        "sdk_package": "@mercury-protocol/sdk",
        "docs_url": "https://docs.mercurydata.app",
        "integration_prompt": """Integrate Mercury indexer for real-time Soroban contract data and event streaming.

Key capabilities:
- **Event Subscriptions**: Subscribe to contract events in real-time via WebSocket or polling.
- **Contract State Queries**: Query current contract storage without invoking the contract.
- **Historical Data**: Fetch historical events and state changes for analytics.
- **Custom Indexing**: Set up custom data subscriptions for specific contract entries.

Mercury API integration:
```javascript
// Subscribe to contract events via Mercury REST API
const MERCURY_URL = 'https://api.mercurydata.app/v1';
const API_KEY = 'your-mercury-api-key';

// Get contract events
const events = await fetch(
  `${MERCURY_URL}/events?contract_id=${contractId}&start_ledger=${startLedger}`,
  { headers: { 'Authorization': `Bearer ${API_KEY}` } }
).then(r => r.json());

// Subscribe to real-time updates
const ws = new WebSocket(`wss://api.mercurydata.app/ws?token=${API_KEY}`);
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  // Handle contract events in real-time
};
```

UI components to add: Real-time event feed, contract state viewer, historical event timeline, data subscription manager.""",
    },
    {
        "id": "fxdao",
        "name": "FxDAO",
        "description": "Decentralized stablecoin protocol on Soroban for minting and managing collateral-backed stablecoins.",
        "category": "Stablecoin",
        "icon": "banknote",
        "sdk_package": None,
        "docs_url": "https://fxdao.io",
        "integration_prompt": """Integrate FxDAO stablecoin protocol for minting and managing stablecoins on Soroban.

Key capabilities:
- **Mint Stablecoins**: Lock collateral (XLM or other assets) to mint fxUSD stablecoins.
- **Manage Vaults**: Monitor and adjust collateral ratios in user vaults.
- **Repay Debt**: Repay fxUSD to unlock collateral from vaults.
- **Liquidation Monitoring**: Track vault health and liquidation thresholds.

FxDAO contract interaction:
```javascript
import { Contract, nativeToScVal, Address } from '@stellar/stellar-sdk';

const FXDAO_VAULT = 'VAULT_CONTRACT_ID';
const vault = new Contract(FXDAO_VAULT);

// Open a vault and mint stablecoins
const mintCall = vault.call(
  'open_vault',
  new Address(userAddress).toScVal(),
  nativeToScVal(collateralAmount, { type: 'i128' }),
  nativeToScVal(mintAmount, { type: 'i128' })
);

// Check vault health
const healthCall = vault.call(
  'get_vault',
  new Address(userAddress).toScVal()
);
```

UI components to add: Vault creation form, collateral ratio gauge, mint/repay interface, vault health dashboard, liquidation alerts.""",
    },
    {
        "id": "sep24-anchor",
        "name": "Stellar Anchors (SEP-24)",
        "description": "Fiat on/off ramp integration using SEP-24 interactive deposit and withdrawal with anchor services.",
        "category": "Infrastructure",
        "icon": "building-2",
        "sdk_package": "@stellar/stellar-sdk",
        "docs_url": "https://developers.stellar.org/docs/anchoring-assets/enabling-deposit-and-withdrawal/",
        "integration_prompt": """Integrate SEP-24 anchor services for fiat on/off ramps (deposit and withdraw).

Key capabilities:
- **Interactive Deposit**: Allow users to deposit fiat (USD, EUR, etc.) and receive Stellar tokens via an anchor's hosted UI.
- **Interactive Withdrawal**: Allow users to send Stellar tokens and receive fiat via bank transfer or other methods.
- **Anchor Discovery**: Query the stellar.toml file and SEP-24 info endpoint to discover supported assets and transfer methods.
- **Transaction Status**: Monitor deposit/withdrawal transaction status.

SEP-24 flow:
```javascript
import { StellarTomlResolver } from '@stellar/stellar-sdk';

// 1. Discover anchor capabilities
const toml = await StellarTomlResolver.resolve('anchor-domain.com');
const transferServer = toml.TRANSFER_SERVER_SEP0024;

// 2. Get supported assets
const info = await fetch(`${transferServer}/info`).then(r => r.json());

// 3. Start interactive deposit
const depositResponse = await fetch(`${transferServer}/transactions/deposit/interactive`, {
  method: 'POST',
  headers: { 'Authorization': `Bearer ${authToken}` },
  body: JSON.stringify({
    asset_code: 'USDC',
    account: userPublicKey,
  })
}).then(r => r.json());

// 4. Open the interactive URL in an iframe or popup
window.open(depositResponse.url, 'anchor-deposit', 'width=500,height=700');

// 5. Poll for transaction completion
const txStatus = await fetch(
  `${transferServer}/transaction?id=${depositResponse.id}`,
  { headers: { 'Authorization': `Bearer ${authToken}` } }
).then(r => r.json());
```

UI components to add: Deposit/withdraw buttons, anchor selection dropdown, fiat amount input, transaction status tracker, supported assets list.""",
    },
    {
        "id": "sep31-payments",
        "name": "Cross-Border Payments (SEP-31)",
        "description": "Send cross-border payments via Stellar anchors using the SEP-31 direct payment protocol.",
        "category": "Payments",
        "icon": "globe",
        "sdk_package": "@stellar/stellar-sdk",
        "docs_url": "https://developers.stellar.org/docs/anchoring-assets/enabling-cross-border-payments/",
        "integration_prompt": """Integrate SEP-31 cross-border payment protocol for sending payments to recipients in different countries.

Key capabilities:
- **Direct Payments**: Send payments directly to a receiving anchor that handles last-mile delivery.
- **Recipient KYC**: Collect recipient information required by the receiving anchor.
- **Fee Quotes**: Get fee quotes for cross-border transfers before sending.
- **Transaction Tracking**: Monitor payment status from initiation to completion.

SEP-31 flow:
```javascript
// 1. Discover receiving anchor
const toml = await StellarTomlResolver.resolve('receiving-anchor.com');
const directPaymentServer = toml.DIRECT_PAYMENT_SERVER;

// 2. Get info about supported assets and required fields
const info = await fetch(`${directPaymentServer}/info`).then(r => r.json());

// 3. Create a transaction (register recipient)
const txResponse = await fetch(`${directPaymentServer}/transactions`, {
  method: 'POST',
  headers: { 'Authorization': `Bearer ${authToken}`, 'Content-Type': 'application/json' },
  body: JSON.stringify({
    amount: '100.00',
    asset_code: 'USDC',
    fields: {
      transaction: { receiver_routing_number: '...', receiver_account_number: '...' },
      receiver: { first_name: 'John', last_name: 'Doe' }
    }
  })
}).then(r => r.json());

// 4. Send the Stellar payment to the anchor's receiving address
// 5. Poll for completion
```

UI components to add: Payment form with recipient details, country/currency selector, fee breakdown display, payment status timeline.""",
    },
    {
        "id": "soroban-token-sac",
        "name": "Soroban Token (SAC)",
        "description": "Stellar Asset Contract for wrapping classic Stellar assets into Soroban-compatible tokens with standard token interface.",
        "category": "Token",
        "icon": "coins",
        "sdk_package": "@stellar/stellar-sdk",
        "docs_url": "https://soroban.stellar.org/docs/advanced-tutorials/stellar-asset-contract",
        "integration_prompt": """Integrate Stellar Asset Contract (SAC) for wrapping and interacting with classic Stellar assets in Soroban.

Key capabilities:
- **Wrap Classic Assets**: Wrap XLM or any Stellar asset (USDC, yXLM, etc.) into a Soroban token contract.
- **Standard Token Interface**: Use the standard Soroban token interface (balance, transfer, approve, allowance) for wrapped assets.
- **Cross-boundary Transfers**: Move tokens between classic Stellar trustlines and Soroban contract balances.

SAC interaction patterns:
```javascript
import { Contract, nativeToScVal, Address, Asset } from '@stellar/stellar-sdk';

// Get the SAC contract ID for a classic asset
const asset = new Asset('USDC', 'GA5ZSEJYB37JRC5AVCIA5MOP4RHTM335X2KGX3IHOJAPP5RE34K4KZVN');
const sacContractId = asset.contractId(networkPassphrase);

const sacContract = new Contract(sacContractId);

// Query balance
const balanceCall = sacContract.call(
  'balance',
  new Address(userAddress).toScVal()
);

// Transfer tokens
const transferCall = sacContract.call(
  'transfer',
  new Address(fromAddress).toScVal(),
  new Address(toAddress).toScVal(),
  nativeToScVal(amount, { type: 'i128' })
);

// Approve spending allowance
const approveCall = sacContract.call(
  'approve',
  new Address(owner).toScVal(),
  new Address(spender).toScVal(),
  nativeToScVal(amount, { type: 'i128' }),
  nativeToScVal(expirationLedger, { type: 'u32' })
);
```

UI components to add: Token balance display, transfer form, approval management, asset wrapping interface, token info card.""",
    },
    {
        "id": "timelock-multisig",
        "name": "Timelock & Multisig",
        "description": "Multi-signature authorization and time-locked transactions for secure Soroban contract governance.",
        "category": "Security",
        "icon": "shield-check",
        "sdk_package": "@stellar/stellar-sdk",
        "docs_url": "https://soroban.stellar.org/docs/how-to-guides/auth",
        "integration_prompt": """Integrate timelock and multi-signature patterns for secure Soroban contract operations.

Key capabilities:
- **Multi-sig Authorization**: Require multiple parties to approve a transaction before execution.
- **Time-locked Operations**: Schedule contract calls that can only execute after a specified ledger/timestamp.
- **Proposal System**: Create proposals that need N-of-M approvals before execution.
- **Emergency Controls**: Admin emergency pause/unpause functionality.

Soroban multisig/timelock patterns:
```rust
// In the Soroban contract (Rust):
#[contracttype]
pub enum DataKey {
    Signers,       // Vec<Address> of authorized signers
    Threshold,     // u32 minimum signatures required
    Proposal(u64), // Proposal by ID
}

#[contracttype]
pub struct Proposal {
    pub proposer: Address,
    pub action: Symbol,
    pub approvals: Vec<Address>,
    pub execute_after: u64, // ledger number
    pub executed: bool,
}

// Frontend interaction:
const proposeCall = contract.call(
  'propose',
  new Address(proposer).toScVal(),
  nativeToScVal('transfer_funds', { type: 'symbol' }),
  nativeToScVal(executionDelay, { type: 'u64' })
);

const approveCall = contract.call(
  'approve_proposal',
  nativeToScVal(proposalId, { type: 'u64' }),
  new Address(signer).toScVal()
);
```

UI components to add: Proposal creation form, approval status display with signer list, timelock countdown, governance dashboard, emergency action buttons.""",
    },
]


def get_all_protocols() -> list[Protocol]:
    """Return all curated protocols"""
    return PROTOCOLS


def get_protocol_by_id(protocol_id: str) -> Protocol | None:
    """Find a protocol by its ID"""
    for p in PROTOCOLS:
        if p["id"] == protocol_id:
            return p
    return None


def get_protocols_by_category(category: str) -> list[Protocol]:
    """Filter protocols by category (case-insensitive)"""
    return [p for p in PROTOCOLS if p["category"].lower() == category.lower()]


def get_categories() -> list[str]:
    """Return all unique protocol categories"""
    return sorted(set(p["category"] for p in PROTOCOLS))


def get_protocol_summary_for_llm() -> str:
    """Format a compact summary of all protocols for LLM context"""
    lines = ["Available Stellar ecosystem protocols:"]
    for p in PROTOCOLS:
        lines.append(f"- {p['name']} ({p['category']}): {p['description']}")
    return "\n".join(lines)
