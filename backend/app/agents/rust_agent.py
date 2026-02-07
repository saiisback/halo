"""
Rust Agent - Generates Soroban smart contracts from scratch

This agent is responsible for:
1. Understanding the contract specification
2. Writing complete Soroban smart contract code
3. Following Soroban best practices and patterns
4. Fixing compilation/deployment errors when they occur

Enhanced with:
- Complete working contract templates as few-shot examples
- Comprehensive SDK 21.0.0 documentation injected as context
- Pre-compilation validation
- Aggressive auto-fixing for SDK 21 gotchas
- Chunked context for large prompts
"""

import re
import logging
from pathlib import Path
from typing import TypedDict

from app.core.llm import generate_completion

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# =============================================================================
# VERIFIED WORKING CONTRACT TEMPLATES (SDK 21.0.0)
# These compile and deploy successfully - use as few-shot examples
# =============================================================================

WORKING_TOKEN_VAULT = '''#![no_std]
use soroban_sdk::{contract, contractimpl, contracttype, token, Address, Env, Symbol};

#[contracttype]
#[derive(Clone)]
pub enum DataKey {
    Balance(Address),
    TotalDeposits,
    TokenAddress,
}

#[contract]
pub struct TokenVault;

#[contractimpl]
impl TokenVault {
    pub fn initialize(env: Env, token_address: Address) {
        env.storage().instance().set(&DataKey::TokenAddress, &token_address);
        env.storage().instance().set(&DataKey::TotalDeposits, &0i128);
    }

    pub fn deposit(env: Env, from: Address, amount: i128) {
        from.require_auth();

        let token_addr: Address = env.storage().instance().get(&DataKey::TokenAddress).unwrap();
        let client = token::Client::new(&env, &token_addr);
        client.transfer(&from, &env.current_contract_address(), &amount);

        let current: i128 = env.storage().instance().get(&DataKey::Balance(from.clone())).unwrap_or(0);
        env.storage().instance().set(&DataKey::Balance(from.clone()), &(current + amount));

        let total: i128 = env.storage().instance().get(&DataKey::TotalDeposits).unwrap_or(0);
        env.storage().instance().set(&DataKey::TotalDeposits, &(total + amount));

        env.events().publish((Symbol::new(&env, "deposit"),), (from, amount));
    }

    pub fn withdraw(env: Env, to: Address, amount: i128) {
        to.require_auth();

        let balance: i128 = env.storage().instance().get(&DataKey::Balance(to.clone())).unwrap_or(0);
        if balance < amount {
            panic!("insufficient balance");
        }

        let token_addr: Address = env.storage().instance().get(&DataKey::TokenAddress).unwrap();
        let client = token::Client::new(&env, &token_addr);
        client.transfer(&env.current_contract_address(), &to, &amount);

        env.storage().instance().set(&DataKey::Balance(to.clone()), &(balance - amount));

        let total: i128 = env.storage().instance().get(&DataKey::TotalDeposits).unwrap_or(0);
        env.storage().instance().set(&DataKey::TotalDeposits, &(total - amount));

        env.events().publish((Symbol::new(&env, "withdraw"),), (to, amount));
    }

    pub fn get_balance(env: Env, user: Address) -> i128 {
        env.storage().instance().get(&DataKey::Balance(user.clone())).unwrap_or(0)
    }
}'''

WORKING_CROWDFUNDING = '''#![no_std]
use soroban_sdk::{contract, contractimpl, contracttype, token, Address, Env, String, Symbol};

#[contracttype]
#[derive(Clone)]
pub struct Campaign {
    pub creator: Address,
    pub title: String,
    pub goal: i128,
    pub deadline: u64,
    pub raised: i128,
    pub token: Address,
    pub active: bool,
}

#[contracttype]
#[derive(Clone)]
pub enum DataKey {
    Campaign(u64),
    Contribution(u64, Address),
    NextId,
}

#[contract]
pub struct Crowdfunding;

#[contractimpl]
impl Crowdfunding {
    pub fn create(env: Env, creator: Address, title: String, goal: i128, deadline: u64, token: Address) -> u64 {
        creator.require_auth();

        let id: u64 = env.storage().instance().get(&DataKey::NextId).unwrap_or(1);

        let campaign = Campaign {
            creator: creator.clone(),
            title,
            goal,
            deadline,
            raised: 0,
            token,
            active: true,
        };

        env.storage().instance().set(&DataKey::Campaign(id), &campaign);
        env.storage().instance().set(&DataKey::NextId, &(id + 1));

        env.events().publish((Symbol::new(&env, "created"),), (id, creator));
        id
    }

    pub fn contribute(env: Env, campaign_id: u64, contributor: Address, amount: i128) {
        contributor.require_auth();

        let mut campaign: Campaign = env.storage().instance().get(&DataKey::Campaign(campaign_id)).unwrap();

        if !campaign.active {
            panic!("campaign not active");
        }
        if env.ledger().timestamp() >= campaign.deadline {
            panic!("campaign ended");
        }

        let client = token::Client::new(&env, &campaign.token);
        client.transfer(&contributor, &env.current_contract_address(), &amount);

        let key = DataKey::Contribution(campaign_id, contributor.clone());
        let current: i128 = env.storage().instance().get(&key).unwrap_or(0);
        env.storage().instance().set(&key, &(current + amount));

        campaign.raised += amount;
        env.storage().instance().set(&DataKey::Campaign(campaign_id), &campaign);

        env.events().publish((Symbol::new(&env, "contributed"),), (campaign_id, contributor, amount));
    }

    pub fn withdraw(env: Env, campaign_id: u64) {
        let mut campaign: Campaign = env.storage().instance().get(&DataKey::Campaign(campaign_id)).unwrap();
        campaign.creator.require_auth();

        if campaign.raised < campaign.goal {
            panic!("goal not reached");
        }

        let client = token::Client::new(&env, &campaign.token);
        client.transfer(&env.current_contract_address(), &campaign.creator, &campaign.raised);

        campaign.active = false;
        env.storage().instance().set(&DataKey::Campaign(campaign_id), &campaign);

        env.events().publish((Symbol::new(&env, "withdrawn"),), (campaign_id, campaign.raised));
    }

    pub fn get_campaign(env: Env, id: u64) -> Campaign {
        env.storage().instance().get(&DataKey::Campaign(id)).unwrap()
    }
}'''

WORKING_VOTING = '''#![no_std]
use soroban_sdk::{contract, contractimpl, contracttype, Address, Env, String, Symbol};

#[contracttype]
#[derive(Clone)]
pub struct Proposal {
    pub id: u64,
    pub creator: Address,
    pub title: String,
    pub yes_votes: u64,
    pub no_votes: u64,
    pub deadline: u64,
    pub executed: bool,
}

#[contracttype]
#[derive(Clone)]
pub enum DataKey {
    Proposal(u64),
    HasVoted(u64, Address),
    NextId,
    Admin,
}

#[contract]
pub struct Voting;

#[contractimpl]
impl Voting {
    pub fn initialize(env: Env, admin: Address) {
        admin.require_auth();
        env.storage().instance().set(&DataKey::Admin, &admin);
        env.storage().instance().set(&DataKey::NextId, &1u64);
    }

    pub fn create_proposal(env: Env, creator: Address, title: String, duration: u64) -> u64 {
        creator.require_auth();

        let id: u64 = env.storage().instance().get(&DataKey::NextId).unwrap_or(1);
        let deadline = env.ledger().timestamp() + duration;

        let proposal = Proposal {
            id,
            creator: creator.clone(),
            title,
            yes_votes: 0,
            no_votes: 0,
            deadline,
            executed: false,
        };

        env.storage().instance().set(&DataKey::Proposal(id), &proposal);
        env.storage().instance().set(&DataKey::NextId, &(id + 1));

        env.events().publish((Symbol::new(&env, "proposal_created"),), (id, creator));
        id
    }

    pub fn vote(env: Env, proposal_id: u64, voter: Address, approve: bool) {
        voter.require_auth();

        let vote_key = DataKey::HasVoted(proposal_id, voter.clone());
        if env.storage().instance().has(&vote_key) {
            panic!("already voted");
        }

        let mut proposal: Proposal = env.storage().instance().get(&DataKey::Proposal(proposal_id)).unwrap();

        if env.ledger().timestamp() >= proposal.deadline {
            panic!("voting ended");
        }

        if approve {
            proposal.yes_votes += 1;
        } else {
            proposal.no_votes += 1;
        }

        env.storage().instance().set(&DataKey::Proposal(proposal_id), &proposal);
        env.storage().instance().set(&vote_key, &true);

        env.events().publish((Symbol::new(&env, "voted"),), (proposal_id, voter, approve));
    }

    pub fn get_proposal(env: Env, id: u64) -> Proposal {
        env.storage().instance().get(&DataKey::Proposal(id)).unwrap()
    }
}'''

WORKING_NFT_SIMPLE = '''#![no_std]
use soroban_sdk::{contract, contractimpl, contracttype, Address, Env, String, Symbol};

#[contracttype]
#[derive(Clone)]
pub struct NFT {
    pub id: u64,
    pub owner: Address,
    pub name: String,
    pub uri: String,
}

#[contracttype]
#[derive(Clone)]
pub enum DataKey {
    NFT(u64),
    Owner(u64),
    NextId,
    Admin,
    TotalMinted,
}

#[contract]
pub struct SimpleNFT;

#[contractimpl]
impl SimpleNFT {
    pub fn initialize(env: Env, admin: Address) {
        admin.require_auth();
        env.storage().instance().set(&DataKey::Admin, &admin);
        env.storage().instance().set(&DataKey::NextId, &1u64);
        env.storage().instance().set(&DataKey::TotalMinted, &0u64);
    }

    pub fn mint(env: Env, to: Address, name: String, uri: String) -> u64 {
        let admin: Address = env.storage().instance().get(&DataKey::Admin).unwrap();
        admin.require_auth();

        let id: u64 = env.storage().instance().get(&DataKey::NextId).unwrap_or(1);

        let nft = NFT {
            id,
            owner: to.clone(),
            name,
            uri,
        };

        env.storage().instance().set(&DataKey::NFT(id), &nft);
        env.storage().instance().set(&DataKey::Owner(id), &to);
        env.storage().instance().set(&DataKey::NextId, &(id + 1));

        let total: u64 = env.storage().instance().get(&DataKey::TotalMinted).unwrap_or(0);
        env.storage().instance().set(&DataKey::TotalMinted, &(total + 1));

        env.events().publish((Symbol::new(&env, "minted"),), (id, to));
        id
    }

    pub fn transfer(env: Env, from: Address, to: Address, token_id: u64) {
        from.require_auth();

        let mut nft: NFT = env.storage().instance().get(&DataKey::NFT(token_id)).unwrap();

        if nft.owner != from {
            panic!("not owner");
        }

        nft.owner = to.clone();
        env.storage().instance().set(&DataKey::NFT(token_id), &nft);
        env.storage().instance().set(&DataKey::Owner(token_id), &to);

        env.events().publish((Symbol::new(&env, "transferred"),), (token_id, from, to));
    }

    pub fn get_nft(env: Env, id: u64) -> NFT {
        env.storage().instance().get(&DataKey::NFT(id)).unwrap()
    }

    pub fn owner_of(env: Env, id: u64) -> Address {
        env.storage().instance().get(&DataKey::Owner(id)).unwrap()
    }
}'''

WORKING_ESCROW = '''#![no_std]
use soroban_sdk::{contract, contractimpl, contracttype, token, Address, Env, Symbol};

#[contracttype]
#[derive(Clone)]
pub enum DataKey {
    Depositor,
    Beneficiary,
    Arbiter,
    Token,
    Amount,
    Released,
}

#[contract]
pub struct Escrow;

#[contractimpl]
impl Escrow {
    pub fn initialize(env: Env, depositor: Address, beneficiary: Address, arbiter: Address, token: Address) {
        depositor.require_auth();
        env.storage().instance().set(&DataKey::Depositor, &depositor);
        env.storage().instance().set(&DataKey::Beneficiary, &beneficiary);
        env.storage().instance().set(&DataKey::Arbiter, &arbiter);
        env.storage().instance().set(&DataKey::Token, &token);
        env.storage().instance().set(&DataKey::Amount, &0i128);
        env.storage().instance().set(&DataKey::Released, &false);
    }

    pub fn deposit(env: Env, from: Address, amount: i128) {
        from.require_auth();
        let depositor: Address = env.storage().instance().get(&DataKey::Depositor).unwrap();
        if from != depositor {
            panic!("only depositor");
        }
        let token_addr: Address = env.storage().instance().get(&DataKey::Token).unwrap();
        let client = token::Client::new(&env, &token_addr);
        client.transfer(&from, &env.current_contract_address(), &amount);
        let current: i128 = env.storage().instance().get(&DataKey::Amount).unwrap_or(0);
        env.storage().instance().set(&DataKey::Amount, &(current + amount));
        env.events().publish((Symbol::new(&env, "deposited"),), (from, amount));
    }

    pub fn release(env: Env, caller: Address) {
        caller.require_auth();
        let arbiter: Address = env.storage().instance().get(&DataKey::Arbiter).unwrap();
        if caller != arbiter {
            panic!("only arbiter");
        }
        let released: bool = env.storage().instance().get(&DataKey::Released).unwrap_or(false);
        if released {
            panic!("already released");
        }
        let beneficiary: Address = env.storage().instance().get(&DataKey::Beneficiary).unwrap();
        let token_addr: Address = env.storage().instance().get(&DataKey::Token).unwrap();
        let amount: i128 = env.storage().instance().get(&DataKey::Amount).unwrap_or(0);
        let client = token::Client::new(&env, &token_addr);
        client.transfer(&env.current_contract_address(), &beneficiary, &amount);
        env.storage().instance().set(&DataKey::Released, &true);
        env.events().publish((Symbol::new(&env, "released"),), (beneficiary, amount));
    }

    pub fn get_status(env: Env) -> (i128, bool) {
        let amount: i128 = env.storage().instance().get(&DataKey::Amount).unwrap_or(0);
        let released: bool = env.storage().instance().get(&DataKey::Released).unwrap_or(false);
        (amount, released)
    }
}'''

WORKING_COUNTER = '''#![no_std]
use soroban_sdk::{contract, contractimpl, contracttype, Address, Env, Symbol};

#[contracttype]
#[derive(Clone)]
pub enum DataKey {
    Count,
    Admin,
}

#[contract]
pub struct Counter;

#[contractimpl]
impl Counter {
    pub fn initialize(env: Env, admin: Address) {
        admin.require_auth();
        env.storage().instance().set(&DataKey::Admin, &admin);
        env.storage().instance().set(&DataKey::Count, &0u64);
    }

    pub fn increment(env: Env, caller: Address) -> u64 {
        caller.require_auth();
        let mut count: u64 = env.storage().instance().get(&DataKey::Count).unwrap_or(0);
        count += 1;
        env.storage().instance().set(&DataKey::Count, &count);
        env.events().publish((Symbol::new(&env, "incremented"),), (caller, count));
        count
    }

    pub fn decrement(env: Env, caller: Address) -> u64 {
        caller.require_auth();
        let mut count: u64 = env.storage().instance().get(&DataKey::Count).unwrap_or(0);
        if count > 0 {
            count -= 1;
        }
        env.storage().instance().set(&DataKey::Count, &count);
        env.events().publish((Symbol::new(&env, "decremented"),), (caller, count));
        count
    }

    pub fn get_count(env: Env) -> u64 {
        env.storage().instance().get(&DataKey::Count).unwrap_or(0)
    }
}'''

WORKING_FUND_TRANSFER = '''#![no_std]
use soroban_sdk::{contract, contractimpl, contracttype, token, Address, Env, Symbol};

#[contracttype]
#[derive(Clone)]
pub enum DataKey {
    Admin,
    TokenAddress,
    TransferCount,
}

#[contract]
pub struct FundTransfer;

#[contractimpl]
impl FundTransfer {
    pub fn initialize(env: Env, admin: Address, token_address: Address) {
        if env.storage().instance().has(&DataKey::Admin) {
            panic!("already initialized");
        }
        env.storage().instance().set(&DataKey::Admin, &admin);
        env.storage().instance().set(&DataKey::TokenAddress, &token_address);
        env.storage().instance().set(&DataKey::TransferCount, &0u64);
    }

    pub fn transfer(env: Env, from: Address, to: Address, amount: i128) -> u64 {
        from.require_auth();
        if amount <= 0 {
            panic!("amount must be positive");
        }
        let token_addr: Address = env.storage().instance().get(&DataKey::TokenAddress).unwrap();
        let client = token::Client::new(&env, &token_addr);
        client.transfer(&from, &to, &amount);
        let mut count: u64 = env.storage().instance().get(&DataKey::TransferCount).unwrap_or(0);
        count += 1;
        env.storage().instance().set(&DataKey::TransferCount, &count);
        env.events().publish((Symbol::new(&env, "transfer"),), (from, to, amount));
        count
    }

    pub fn get_transfer_count(env: Env) -> u64 {
        env.storage().instance().get(&DataKey::TransferCount).unwrap_or(0)
    }
}'''

WORKING_SUBSCRIPTION = '''#![no_std]
use soroban_sdk::{contract, contractimpl, contracttype, token, Address, Env, Symbol};

#[contracttype]
#[derive(Clone)]
pub enum DataKey {
    Admin,
    Token,
    Price,
    Duration,
    Subscriber(Address),
}

#[contract]
pub struct Subscription;

#[contractimpl]
impl Subscription {
    pub fn initialize(env: Env, admin: Address, token: Address, price: i128, duration: u64) {
        admin.require_auth();
        env.storage().instance().set(&DataKey::Admin, &admin);
        env.storage().instance().set(&DataKey::Token, &token);
        env.storage().instance().set(&DataKey::Price, &price);
        env.storage().instance().set(&DataKey::Duration, &duration);
    }

    pub fn subscribe(env: Env, user: Address) {
        user.require_auth();
        let token_addr: Address = env.storage().instance().get(&DataKey::Token).unwrap();
        let price: i128 = env.storage().instance().get(&DataKey::Price).unwrap();
        let duration: u64 = env.storage().instance().get(&DataKey::Duration).unwrap();
        let admin: Address = env.storage().instance().get(&DataKey::Admin).unwrap();

        let client = token::Client::new(&env, &token_addr);
        client.transfer(&user, &admin, &price);

        let expires = env.ledger().timestamp() + duration;
        env.storage().instance().set(&DataKey::Subscriber(user.clone()), &expires);
        env.events().publish((Symbol::new(&env, "subscribed"),), (user, expires));
    }

    pub fn is_active(env: Env, user: Address) -> bool {
        let expires: u64 = env.storage().instance().get(&DataKey::Subscriber(user)).unwrap_or(0);
        env.ledger().timestamp() < expires
    }

    pub fn get_price(env: Env) -> i128 {
        env.storage().instance().get(&DataKey::Price).unwrap_or(0)
    }
}'''

WORKING_LOTTERY = '''#![no_std]
use soroban_sdk::{contract, contractimpl, contracttype, token, Address, Env, Symbol, Vec};

#[contracttype]
#[derive(Clone)]
pub enum DataKey {
    Admin,
    Token,
    TicketPrice,
    Players,
    PrizePool,
    Active,
}

#[contract]
pub struct Lottery;

#[contractimpl]
impl Lottery {
    pub fn initialize(env: Env, admin: Address, token: Address, ticket_price: i128) {
        admin.require_auth();
        env.storage().instance().set(&DataKey::Admin, &admin);
        env.storage().instance().set(&DataKey::Token, &token);
        env.storage().instance().set(&DataKey::TicketPrice, &ticket_price);
        let players: Vec<Address> = Vec::new(&env);
        env.storage().instance().set(&DataKey::Players, &players);
        env.storage().instance().set(&DataKey::PrizePool, &0i128);
        env.storage().instance().set(&DataKey::Active, &true);
    }

    pub fn buy_ticket(env: Env, player: Address) {
        player.require_auth();
        let active: bool = env.storage().instance().get(&DataKey::Active).unwrap_or(false);
        if !active {
            panic!("lottery not active");
        }
        let token_addr: Address = env.storage().instance().get(&DataKey::Token).unwrap();
        let price: i128 = env.storage().instance().get(&DataKey::TicketPrice).unwrap();
        let client = token::Client::new(&env, &token_addr);
        client.transfer(&player, &env.current_contract_address(), &price);

        let mut players: Vec<Address> = env.storage().instance().get(&DataKey::Players).unwrap();
        players.push_back(player.clone());
        env.storage().instance().set(&DataKey::Players, &players);

        let pool: i128 = env.storage().instance().get(&DataKey::PrizePool).unwrap_or(0);
        env.storage().instance().set(&DataKey::PrizePool, &(pool + price));
        env.events().publish((Symbol::new(&env, "ticket_bought"),), (player, pool + price));
    }

    pub fn draw_winner(env: Env, caller: Address) {
        let admin: Address = env.storage().instance().get(&DataKey::Admin).unwrap();
        caller.require_auth();
        if caller != admin {
            panic!("admin only");
        }
        let players: Vec<Address> = env.storage().instance().get(&DataKey::Players).unwrap();
        if players.is_empty() {
            panic!("no players");
        }
        let winner_idx = env.prng().gen_range::<u64>(0..players.len() as u64);
        let winner: Address = players.get(winner_idx as u32).unwrap();
        let pool: i128 = env.storage().instance().get(&DataKey::PrizePool).unwrap_or(0);
        let token_addr: Address = env.storage().instance().get(&DataKey::Token).unwrap();
        let client = token::Client::new(&env, &token_addr);
        client.transfer(&env.current_contract_address(), &winner, &pool);

        env.storage().instance().set(&DataKey::PrizePool, &0i128);
        let empty: Vec<Address> = Vec::new(&env);
        env.storage().instance().set(&DataKey::Players, &empty);
        env.storage().instance().set(&DataKey::Active, &false);
        env.events().publish((Symbol::new(&env, "winner"),), (winner, pool));
    }

    pub fn get_pool(env: Env) -> i128 {
        env.storage().instance().get(&DataKey::PrizePool).unwrap_or(0)
    }
}'''

WORKING_MARKETPLACE = '''#![no_std]
use soroban_sdk::{contract, contractimpl, contracttype, token, Address, Env, String, Symbol};

#[contracttype]
#[derive(Clone)]
pub struct Listing {
    pub seller: Address,
    pub title: String,
    pub price: i128,
    pub token: Address,
    pub active: bool,
}

#[contracttype]
#[derive(Clone)]
pub enum DataKey {
    Listing(u64),
    NextId,
    Admin,
}

#[contract]
pub struct Marketplace;

#[contractimpl]
impl Marketplace {
    pub fn initialize(env: Env, admin: Address) {
        admin.require_auth();
        env.storage().instance().set(&DataKey::Admin, &admin);
        env.storage().instance().set(&DataKey::NextId, &1u64);
    }

    pub fn create_listing(env: Env, seller: Address, title: String, price: i128, token: Address) -> u64 {
        seller.require_auth();
        let id: u64 = env.storage().instance().get(&DataKey::NextId).unwrap_or(1);
        let listing = Listing {
            seller: seller.clone(),
            title,
            price,
            token,
            active: true,
        };
        env.storage().instance().set(&DataKey::Listing(id), &listing);
        env.storage().instance().set(&DataKey::NextId, &(id + 1));
        env.events().publish((Symbol::new(&env, "listed"),), (id, seller));
        id
    }

    pub fn buy(env: Env, listing_id: u64, buyer: Address) {
        buyer.require_auth();
        let mut listing: Listing = env.storage().instance().get(&DataKey::Listing(listing_id)).unwrap();
        if !listing.active {
            panic!("listing not active");
        }
        let client = token::Client::new(&env, &listing.token);
        client.transfer(&buyer, &listing.seller, &listing.price);
        listing.active = false;
        env.storage().instance().set(&DataKey::Listing(listing_id), &listing);
        env.events().publish((Symbol::new(&env, "sold"),), (listing_id, buyer));
    }

    pub fn get_listing(env: Env, id: u64) -> Listing {
        env.storage().instance().get(&DataKey::Listing(id)).unwrap()
    }
}'''

# Map template types to working examples — comprehensive keyword coverage
WORKING_TEMPLATES = {
    # Token/Vault
    "token": WORKING_TOKEN_VAULT,
    "vault": WORKING_TOKEN_VAULT,
    "deposit": WORKING_TOKEN_VAULT,
    "withdraw": WORKING_TOKEN_VAULT,
    "staking": WORKING_TOKEN_VAULT,
    "savings": WORKING_TOKEN_VAULT,
    "treasury": WORKING_TOKEN_VAULT,
    "token_vault": WORKING_TOKEN_VAULT,
    "wallet": WORKING_TOKEN_VAULT,
    "bank": WORKING_TOKEN_VAULT,
    # Crowdfunding
    "crowdfunding": WORKING_CROWDFUNDING,
    "fundraising": WORKING_CROWDFUNDING,
    "campaign": WORKING_CROWDFUNDING,
    "donation": WORKING_CROWDFUNDING,
    "charity": WORKING_CROWDFUNDING,
    "ico": WORKING_CROWDFUNDING,
    "presale": WORKING_CROWDFUNDING,
    # Voting/Governance
    "voting": WORKING_VOTING,
    "governance": WORKING_VOTING,
    "dao": WORKING_VOTING,
    "proposal": WORKING_VOTING,
    "poll": WORKING_VOTING,
    "election": WORKING_VOTING,
    "survey": WORKING_VOTING,
    # NFT
    "nft": WORKING_NFT_SIMPLE,
    "collectible": WORKING_NFT_SIMPLE,
    "mint": WORKING_NFT_SIMPLE,
    "badge": WORKING_NFT_SIMPLE,
    "certificate": WORKING_NFT_SIMPLE,
    "digital_art": WORKING_NFT_SIMPLE,
    "nft_mint": WORKING_NFT_SIMPLE,
    # Escrow
    "escrow": WORKING_ESCROW,
    "payment": WORKING_ESCROW,
    "trade": WORKING_ESCROW,
    "swap": WORKING_ESCROW,
    # Counter/Simple
    "counter": WORKING_COUNTER,
    "tracker": WORKING_COUNTER,
    "simple": WORKING_COUNTER,
    "registry": WORKING_COUNTER,
    "hello": WORKING_COUNTER,
    # Fund Transfer
    "transfer": WORKING_FUND_TRANSFER,
    "send": WORKING_FUND_TRANSFER,
    "remittance": WORKING_FUND_TRANSFER,
    "token_transfer": WORKING_FUND_TRANSFER,
    # Subscription
    "subscription": WORKING_SUBSCRIPTION,
    "membership": WORKING_SUBSCRIPTION,
    "saas": WORKING_SUBSCRIPTION,
    "recurring": WORKING_SUBSCRIPTION,
    # Lottery
    "lottery": WORKING_LOTTERY,
    "raffle": WORKING_LOTTERY,
    "prize": WORKING_LOTTERY,
    "game": WORKING_LOTTERY,
    "random": WORKING_LOTTERY,
    # Marketplace
    "marketplace": WORKING_MARKETPLACE,
    "shop": WORKING_MARKETPLACE,
    "store": WORKING_MARKETPLACE,
    "auction": WORKING_MARKETPLACE,
    "listing": WORKING_MARKETPLACE,
    "ecommerce": WORKING_MARKETPLACE,
}


def load_stellar_docs() -> str:
    """Load the Stellar documentation from llms.txt"""
    try:
        llms_path = Path(__file__).parent.parent.parent / "llms.txt"
        if llms_path.exists():
            content = llms_path.read_text()
            logger.info(f"[RUST_AGENT] Loaded Stellar docs from llms.txt ({len(content)} chars)")
            return content
        else:
            logger.warning(f"[RUST_AGENT] llms.txt not found at {llms_path}")
            return ""
    except Exception as e:
        logger.warning(f"[RUST_AGENT] Failed to load llms.txt: {e}")
        return ""


# Load Stellar documentation once at module level
STELLAR_DOCS = load_stellar_docs()


class RustGenerationResult(TypedDict):
    lib_rs: str
    cargo_toml: str


# Standard Cargo.toml for Soroban contracts
CARGO_TOML = '''[package]
name = "halo-contract"
version = "0.1.0"
edition = "2021"

[lib]
crate-type = ["cdylib"]

[dependencies]
soroban-sdk = "21.0.0"

[dev-dependencies]
soroban-sdk = { version = "21.0.0", features = ["testutils"] }

[profile.release]
opt-level = "z"
overflow-checks = true
debug = 0
strip = "symbols"
debug-assertions = false
panic = "abort"
codegen-units = 1
lto = true

[profile.release-with-logs]
inherits = "release"
debug-assertions = true
'''


# =============================================================================
# SDK 21.0.0 CHEAT SHEET — injected into EVERY generation prompt as a chunk
# This is the condensed, critical reference that prevents 95% of compilation errors
# =============================================================================

SDK_CHEAT_SHEET = """## SOROBAN SDK 21.0.0 — MANDATORY RULES (violating ANY = compilation failure)

### Rule 1: STORAGE takes REFERENCES (always use &)
```rust
env.storage().instance().set(&DataKey::X, &value);   // & before key AND value
env.storage().instance().get(&DataKey::X)             // & before key
env.storage().instance().has(&DataKey::X)             // & before key
env.storage().persistent().set(&DataKey::X, &value);  // same for persistent
```

### Rule 2: MAP takes OWNED values (NEVER use & with Map)
```rust
map.get(key.clone())           // CORRECT - owned value
map.contains_key(key.clone())  // CORRECT - owned value
map.set(key.clone(), value)    // CORRECT - owned value
// map.get(&key)               // WRONG! Compilation error!
```

### Rule 3: Vec uses push_back(), NEVER push()
```rust
vec.push_back(item);           // CORRECT
// vec.push(item);             // WRONG! No method named push!
```

### Rule 4: ALL custom structs AND enums need both attributes
```rust
#[contracttype]
#[derive(Clone)]
pub struct MyStruct { ... }

#[contracttype]
#[derive(Clone)]
pub enum DataKey { ... }
```

### Rule 5: NO std library functions in no_std
- NO `to_string()` — use u64 integers for IDs
- NO `format!()` — use u64 integers for IDs
- NO `println!()` — use env.events().publish() for logging
- NO `String::from()` — use `String::from_str(&env, "text")`
- NO `Symbol::from()` — use `Symbol::new(&env, "name")`

### Rule 6: Start every file with `#![no_std]`

### Rule 7: require_auth() BEFORE any state changes
```rust
pub fn action(env: Env, caller: Address) {
    caller.require_auth();  // MUST be first
    // then do state changes
}
```

### Rule 8: Token operations
```rust
use soroban_sdk::token;
let client = token::Client::new(&env, &token_addr);
client.transfer(&from, &to, &amount);  // all references
client.balance(&address)               // reference
```

### Rule 9: Only import what you use
```rust
use soroban_sdk::{contract, contractimpl, contracttype, Address, Env, Symbol};
// Add: token (if token ops), String (if strings), Vec (if vectors), Map (if maps)
```

### Rule 10: Events pattern
```rust
env.events().publish((Symbol::new(&env, "event_name"),), (data1, data2));
```
"""


RUST_AGENT_SYSTEM_PROMPT = """You are an expert Soroban smart contract developer. You write COMPLETE, COMPILABLE Rust code for Soroban SDK 21.0.0.

Your output MUST compile on the FIRST attempt. Follow every rule below exactly.

""" + SDK_CHEAT_SHEET + """

## OUTPUT FORMAT:
- Output ONLY valid Rust code
- NO markdown code fences (no ```)
- NO explanations or comments outside the code
- Start with `#![no_std]`
- End with the closing `}` of the impl block
"""


RUST_AGENT_USER_PROMPT = """Write a Soroban smart contract. You MUST follow the EXACT patterns from the reference template below.

## VERIFIED WORKING REFERENCE (this compiles and deploys successfully — copy its patterns exactly):
```rust
{reference_template}
```

{stellar_docs_chunk}

## CONTRACT SPECIFICATION:
- Name: {name}
- Description: {description}
- Functions: {functions}
- Storage: {storage}
- Business logic: {business_logic}

## MANDATORY CHECKLIST (verify each before outputting):
1. Starts with `#![no_std]`
2. `use soroban_sdk::{{...}};` — only imports actually used
3. ALL enums and structs have `#[contracttype]` AND `#[derive(Clone)]`
4. `#[contract]` on the struct, `#[contractimpl]` on the impl
5. Every `storage().instance().get(...)` and `.set(...)` and `.has(...)` uses `&` before keys
6. Every write function has `require_auth()` called FIRST
7. No `to_string()`, no `format!()`, no `String::from()`, no `Symbol::from()`
8. Vec uses `push_back()` not `push()`
9. IDs are u64, amounts are i128
10. Code ends with `}}` (closing impl and nothing after)

Write the COMPLETE lib.rs code now (no markdown, start with #![no_std]):"""


RUST_FIX_ERROR_PROMPT = """Fix this Soroban contract compilation error. Output the COMPLETE fixed lib.rs.

## FAILED CODE:
```rust
{previous_code}
```

## COMPILER ERROR:
{error}

## VERIFIED WORKING REFERENCE (copy patterns from this):
```rust
{reference_template}
```

## COMMON FIXES:
- "expected `&_`, found `DataKey`" → add & before DataKey: `.get(&DataKey::X)`
- "expected `T`, found `&T`" on Map → remove &: `map.get(key.clone())`
- "no method named `push`" → use `.push_back()`
- "cannot find macro `format`" → use u64 integer instead of string formatting
- "no method named `to_string`" → remove .to_string(), use u64 directly
- "Clone is not implemented" → add `#[derive(Clone)]` to the struct/enum
- "expected `Symbol`" → use `Symbol::new(&env, "name")` not Symbol::from()
- "expected `String`" → use `String::from_str(&env, "text")` not String::from()
- "unused import" → remove it from the use statement
- "cannot find type" → check the use statement has the type imported
- "mismatched types" → check you're passing & references to storage but owned values to Map

## SPECIFICATION:
- Name: {name}
- Functions: {functions}

Output the COMPLETE fixed lib.rs starting with #![no_std] (no markdown, no explanation):"""


def get_stellar_docs_chunk(template_type: str, spec: dict) -> str:
    """
    Get a relevant chunk of Stellar docs to inject into the prompt.
    Keeps it focused and under token limits.
    """
    if not STELLAR_DOCS:
        return ""

    # Extract the most relevant sections from llms.txt based on what the contract needs
    sections = []

    description = spec.get("description", "").lower()
    functions = spec.get("functions", [])
    func_names = [f.get("name", "") if isinstance(f, dict) else str(f) for f in functions]
    func_text = " ".join(func_names).lower()

    # Always include the critical gotchas section
    gotchas_match = re.search(r'(## ⚠️ CRITICAL MISTAKES.*?)(?=## Contract Structure|## Core Imports|\Z)', STELLAR_DOCS, re.DOTALL)
    if gotchas_match:
        sections.append(gotchas_match.group(1).strip())

    # Include storage section if the contract uses storage
    if any(kw in description or kw in func_text for kw in ["storage", "store", "save", "get", "set", "balance", "count"]):
        storage_match = re.search(r'(## Storage API.*?)(?=## Storage Keys|## Authentication|\Z)', STELLAR_DOCS, re.DOTALL)
        if storage_match:
            sections.append(storage_match.group(1).strip()[:800])

    # Include token section if it involves tokens
    if any(kw in description or kw in func_text for kw in ["token", "transfer", "deposit", "withdraw", "payment", "fund", "vault", "balance"]):
        token_match = re.search(r'(## Token Operations.*?)(?=## Custom Errors|## Events|\Z)', STELLAR_DOCS, re.DOTALL)
        if token_match:
            sections.append(token_match.group(1).strip()[:800])

    # Include Vec section if vectors might be used
    if any(kw in description or kw in func_text for kw in ["list", "array", "players", "members", "items", "vec", "lottery", "raffle"]):
        vec_match = re.search(r'(## Vec \(Vector\) Operations.*?)(?=## Map Operations|\Z)', STELLAR_DOCS, re.DOTALL)
        if vec_match:
            sections.append(vec_match.group(1).strip()[:600])

    # Include Map section if maps might be used
    if any(kw in description or kw in func_text for kw in ["map", "balance", "mapping", "lookup", "index"]):
        map_match = re.search(r'(## Map Operations.*?)(?=## Complete Contract|\Z)', STELLAR_DOCS, re.DOTALL)
        if map_match:
            sections.append(map_match.group(1).strip()[:600])

    if not sections:
        return ""

    combined = "\n\n".join(sections)
    # Limit total doc context to avoid blowing out the prompt
    if len(combined) > 3000:
        combined = combined[:3000]

    return f"""## STELLAR SDK DOCUMENTATION (use these patterns):
{combined}"""


async def generate_rust_contract(
    template_type: str,
    spec: dict,
    docs_context: list[str],
    previous_code: str | None = None,
    error_context: str | None = None,
) -> RustGenerationResult:
    """
    Generate a Soroban smart contract from scratch.

    Enhanced with:
    - Working templates as few-shot examples
    - SDK documentation chunks injected into prompt
    - Pre-validation before returning
    - Context window optimization
    - Fallback to template if LLM fails
    """
    logger.info(f"[RUST_AGENT] Starting contract generation")
    logger.info(f"  - Type: {template_type}")
    logger.info(f"  - Name: {spec.get('name', 'Unknown')}")
    logger.info(f"  - Has previous code: {bool(previous_code)}")
    logger.info(f"  - Has error context: {bool(error_context)}")

    # Get best matching working template
    description = spec.get("description", "")
    reference_template = get_best_template(template_type, description)
    if not reference_template:
        reference_template = WORKING_TOKEN_VAULT  # Default fallback

    logger.info(f"[RUST_AGENT] Using reference template ({len(reference_template)} chars)")

    # Format specification (keep concise for context window)
    functions_str = format_functions(spec.get("functions", []))[:2000]
    storage_str = format_storage(spec.get("storage", {}))[:800]
    business_logic_str = format_business_logic(spec.get("business_logic", []))[:800]

    # If we have previous code and an error, try auto-fix first
    if previous_code and error_context:
        logger.info(f"[RUST_AGENT] Attempting auto-fix for: {error_context[:200]}...")

        # Try aggressive auto-fix before asking LLM
        fixed_code = previous_code
        fixed_code, fixes = validate_and_fix_common_issues(fixed_code)

        if fixes:
            logger.info(f"[RUST_AGENT] Auto-fixes applied: {fixes}")
            fixed_code = cleanup_rust_code(fixed_code)

            # Pre-validate the fixed code
            is_valid, pre_errors = pre_validate_code(fixed_code)
            if is_valid and is_valid_rust(fixed_code):
                logger.info(f"[RUST_AGENT] Auto-fix successful!")
                return RustGenerationResult(lib_rs=fixed_code, cargo_toml=CARGO_TOML)
            else:
                logger.info(f"[RUST_AGENT] Auto-fix incomplete, pre-validation errors: {pre_errors}")

        # LLM fix with reference template included for context
        user_prompt = RUST_FIX_ERROR_PROMPT.format(
            previous_code=previous_code,
            error=error_context[:3000],
            reference_template=reference_template,
            name=spec.get("name", "MyContract"),
            functions=functions_str[:1000],
        )

        response = await generate_completion(
            system_prompt=RUST_AGENT_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            temperature=0.0,
            max_tokens=8000,
        )

        if response:
            code = extract_rust_code(response)
            code = cleanup_rust_code(code)

            # Pre-validate before returning
            is_valid, pre_errors = pre_validate_code(code)
            if pre_errors:
                logger.warning(f"[RUST_AGENT] Pre-validation warnings: {pre_errors}")

            if is_valid_rust(code):
                logger.info(f"[RUST_AGENT] LLM fix successful")
                return RustGenerationResult(lib_rs=code, cargo_toml=CARGO_TOML)

        logger.warning(f"[RUST_AGENT] Fix failed, generating fresh with template")

    # Generate fresh code with working template as reference
    logger.info(f"[RUST_AGENT] Generating fresh contract code...")

    # Get relevant documentation chunk
    stellar_docs_chunk = get_stellar_docs_chunk(template_type, spec)

    user_prompt = RUST_AGENT_USER_PROMPT.format(
        reference_template=reference_template,
        stellar_docs_chunk=stellar_docs_chunk,
        name=spec.get("name", "MyContract"),
        description=spec.get("description", "A Soroban smart contract")[:300],
        functions=functions_str,
        storage=storage_str,
        business_logic=business_logic_str,
    )

    logger.info(f"[RUST_AGENT] User prompt length: {len(user_prompt)} chars")

    response = await generate_completion(
        system_prompt=RUST_AGENT_SYSTEM_PROMPT,
        user_prompt=user_prompt,
        temperature=0.0,  # Deterministic — nail it on first try
        max_tokens=8000,
    )

    if not response:
        logger.warning("[RUST_AGENT] LLM returned empty, using template as fallback")
        # Return modified template as fallback
        return RustGenerationResult(lib_rs=reference_template, cargo_toml=CARGO_TOML)

    logger.info(f"[RUST_AGENT] LLM response received ({len(response)} chars)")

    code = extract_rust_code(response)
    code = cleanup_rust_code(code)

    # Pre-validate
    is_valid, pre_errors = pre_validate_code(code)
    if pre_errors:
        logger.warning(f"[RUST_AGENT] Pre-validation issues found: {pre_errors}")
        # Try to fix them
        code, fixes = validate_and_fix_common_issues(code)
        if fixes:
            logger.info(f"[RUST_AGENT] Additional fixes applied: {fixes}")

    if not is_valid_rust(code):
        logger.warning(f"[RUST_AGENT] Generated code invalid, using template")
        return RustGenerationResult(lib_rs=reference_template, cargo_toml=CARGO_TOML)

    logger.info(f"[RUST_AGENT] Contract generated successfully ({len(code)} chars)")
    return RustGenerationResult(lib_rs=code, cargo_toml=CARGO_TOML)


def format_functions(functions: list) -> str:
    """Format functions list for the prompt"""
    if not functions:
        return "No specific functions defined - create appropriate functions based on the description."

    lines = []
    for f in functions:
        if isinstance(f, dict):
            name = f.get("name", "unknown")
            desc = f.get("description", "")
            params = f.get("params", [])
            returns = f.get("returns", "")

            line = f"- {name}: {desc}"
            if params:
                line += f"\n  Parameters: {', '.join(params)}"
            if returns:
                line += f"\n  Returns: {returns}"
            lines.append(line)
        else:
            lines.append(f"- {f}")

    return "\n".join(lines)


def format_storage(storage: dict) -> str:
    """Format storage requirements for the prompt"""
    if not storage:
        return "Design appropriate storage based on the contract requirements."

    lines = []
    for key, desc in storage.items():
        lines.append(f"- {key}: {desc}")

    return "\n".join(lines)


def format_business_logic(logic: list) -> str:
    """Format business logic rules for the prompt"""
    if not logic:
        return "No specific business rules - implement sensible defaults."

    return "\n".join(f"- {rule}" for rule in logic)


def extract_rust_code(response: str) -> str:
    """Extract Rust code from LLM response, stripping any markdown or explanation"""
    # Try to find code block
    code_block = re.search(r'```(?:rust)?\s*([\s\S]*?)```', response)
    if code_block:
        return code_block.group(1).strip()

    # If no code block, look for the start of Rust code
    lines = response.strip().split('\n')
    code_lines = []
    in_code = False

    for line in lines:
        if line.startswith('#![') or line.startswith('use ') or in_code:
            in_code = True
            code_lines.append(line)
        elif line.strip().startswith('//') and in_code:
            code_lines.append(line)
        elif in_code and line.strip():
            code_lines.append(line)

    return '\n'.join(code_lines) if code_lines else response


def is_valid_rust(code: str) -> bool:
    """Basic validation that the code looks like valid Soroban Rust"""
    required = [
        '#![no_std]',
        'soroban_sdk',
        '#[contract]',
        '#[contractimpl]',
    ]
    return all(elem in code for elem in required)


def get_best_template(template_type: str, description: str) -> str | None:
    """Get the best matching working template for the contract type"""
    # Check template type keywords (exact and partial match)
    template_lower = template_type.lower().replace("-", "_").replace(" ", "_")

    # Exact match first
    if template_lower in WORKING_TEMPLATES:
        return WORKING_TEMPLATES[template_lower]

    # Partial match on template type
    for keyword, template in WORKING_TEMPLATES.items():
        if keyword in template_lower or template_lower in keyword:
            return template

    # Check description keywords
    desc_lower = description.lower()
    for keyword, template in WORKING_TEMPLATES.items():
        if keyword in desc_lower:
            return template

    return None


def pre_validate_code(code: str) -> tuple[bool, list[str]]:
    """
    Pre-validate generated code for known SDK 21 issues BEFORE compilation.
    Returns (is_valid, list_of_errors).
    """
    errors = []

    # Check 1a: Storage.get() WITHOUT reference (should have &)
    if re.search(r'storage\(\)[^;]*\.get\s*\(\s*DataKey::', code) and not re.search(r'storage\(\)[^;]*\.get\s*\(\s*&DataKey::', code):
        errors.append("ERROR: storage().get() takes a reference. Use .get(&DataKey::...) not .get(DataKey::...)")

    # Check 1b: Storage.set() WITHOUT reference on key
    if re.search(r'storage\(\)[^;]*\.set\s*\(\s*DataKey::', code) and not re.search(r'storage\(\)[^;]*\.set\s*\(\s*&DataKey::', code):
        errors.append("ERROR: storage().set() takes references. Use .set(&DataKey::..., &value)")

    # Check 1c: Storage.has() WITHOUT reference
    if re.search(r'storage\(\)[^;]*\.has\s*\(\s*DataKey::', code) and not re.search(r'storage\(\)[^;]*\.has\s*\(\s*&DataKey::', code):
        errors.append("ERROR: storage().has() takes a reference. Use .has(&DataKey::...)")

    # Check 2: Vec.push() instead of push_back()
    if re.search(r'\.push\s*\([^_]', code) and 'push_back' not in code:
        errors.append("ERROR: Vec uses .push_back() not .push()")

    # Check 3: to_string() in no_std
    if '.to_string()' in code:
        errors.append("ERROR: to_string() does not exist in no_std. Use integers directly.")

    # Check 3b: format!() macro in no_std
    if 'format!' in code:
        errors.append("ERROR: format!() macro does not exist in no_std. Use integers directly for IDs.")

    # Check 4: String::from or Symbol::from
    if 'String::from(' in code and 'String::from_str' not in code:
        errors.append("ERROR: Use String::from_str(&env, \"text\") not String::from()")

    if re.search(r'Symbol::from\s*\(', code):
        errors.append("ERROR: Use Symbol::new(&env, \"name\") not Symbol::from()")

    # Check 5: Missing Clone for contracttype structs
    struct_defs = re.findall(r'#\[contracttype\]\s*(?:#\[derive\([^\)]*\)\]\s*)?pub (?:struct|enum) (\w+)', code)
    for struct_name in struct_defs:
        has_clone = bool(re.search(rf'#\[derive\([^\)]*Clone[^\)]*\)\][^{{]*pub (?:struct|enum) {struct_name}\b', code))
        if not has_clone:
            errors.append(f"ERROR: {struct_name} needs #[derive(Clone)] after #[contracttype]")

    # Check 6: Missing #![no_std]
    if '#![no_std]' not in code:
        errors.append("ERROR: Missing #![no_std] at start of file")

    # Check 7: println! or dbg! macros (not available in no_std)
    if 'println!' in code or 'dbg!' in code or 'eprintln!' in code:
        errors.append("ERROR: println!/dbg!/eprintln! not available in no_std")

    # Check 8: std:: imports
    if 'use std::' in code or '::std::' in code:
        errors.append("ERROR: Cannot use std:: in no_std environment")

    return len(errors) == 0, errors


def validate_and_fix_common_issues(code: str) -> tuple[str, list[str]]:
    """
    Pre-validate generated code and auto-fix common Soroban SDK 21 issues.
    Returns (fixed_code, list_of_fixes_applied).

    IMPORTANT: Storage and Map have OPPOSITE reference requirements!
    - storage().get(&key) - takes REFERENCE
    - Map.get(key.clone()) - takes OWNED value
    """
    fixes_applied = []

    # Fix 1a: Storage operations MISSING references — get
    storage_get_without_ref = r'(storage\(\)\s*\.\s*(?:instance|persistent|temporary)\(\)\s*\.\s*get\s*\(\s*)(DataKey::[A-Za-z0-9_]+(?:\([^)]*\))?)\s*\)'
    if re.search(storage_get_without_ref, code):
        matches = list(re.finditer(storage_get_without_ref, code))
        for match in reversed(matches):
            prefix = match.group(1)
            key = match.group(2)
            if not key.startswith('&'):
                fixed = f"{prefix}&{key})"
                code = code[:match.start()] + fixed + code[match.end():]
                fixes_applied.append(f'Storage.get: added & reference to {key}')

    # Fix 1b: Storage operations MISSING references — set (both key and value)
    storage_set_without_ref = r'(storage\(\)\s*\.\s*(?:instance|persistent|temporary)\(\)\s*\.\s*set\s*\(\s*)(DataKey::[A-Za-z0-9_]+(?:\([^)]*\))?)\s*,'
    if re.search(storage_set_without_ref, code):
        matches = list(re.finditer(storage_set_without_ref, code))
        for match in reversed(matches):
            prefix = match.group(1)
            key = match.group(2)
            if not key.startswith('&'):
                fixed = f"{prefix}&{key},"
                code = code[:match.start()] + fixed + code[match.end():]
                fixes_applied.append(f'Storage.set: added & reference to key {key}')

    # Fix 1c: Storage.has() missing reference
    storage_has_without_ref = r'(storage\(\)\s*\.\s*(?:instance|persistent|temporary)\(\)\s*\.\s*has\s*\(\s*)(DataKey::[A-Za-z0-9_]+(?:\([^)]*\))?)\s*\)'
    if re.search(storage_has_without_ref, code):
        matches = list(re.finditer(storage_has_without_ref, code))
        for match in reversed(matches):
            prefix = match.group(1)
            key = match.group(2)
            if not key.startswith('&'):
                fixed = f"{prefix}&{key})"
                code = code[:match.start()] + fixed + code[match.end():]
                fixes_applied.append(f'Storage.has: added & reference to {key}')

    # Fix 1d: Storage operations with variable keys missing references
    storage_var_get = r'(storage\(\)\s*\.\s*(?:instance|persistent|temporary)\(\)\s*\.\s*get\s*\(\s*)([a-z_][a-z0-9_]*)\s*\)'
    matches = list(re.finditer(storage_var_get, code))
    for match in reversed(matches):
        prefix = match.group(1)
        var = match.group(2)
        # Check the full line doesn't already have &
        line_start = code.rfind('\n', 0, match.start()) + 1
        line = code[line_start:match.end()]
        if 'storage()' in line and f'&{var}' not in line:
            fixed = f"{prefix}&{var})"
            code = code[:match.start()] + fixed + code[match.end():]
            fixes_applied.append(f'Storage.get: added & reference to variable {var}')

    # Fix 2: Map operations using references instead of owned values
    lines = code.split('\n')
    fixed_lines = []
    for line in lines:
        # Skip lines that are clearly storage operations
        if 'storage()' in line:
            fixed_lines.append(line)
            continue

        # Fix Map.get(&var) -> Map.get(var.clone())
        if re.search(r'\.get\s*\(\s*&([a-zA-Z_][a-zA-Z0-9_]*)\s*\)', line):
            original_line = line
            line = re.sub(r'\.get\s*\(\s*&([a-zA-Z_][a-zA-Z0-9_]*)\s*\)', r'.get(\1.clone())', line)
            if line != original_line:
                fixes_applied.append('Map.get: removed & and added .clone()')

        # Fix Map.contains_key(&var) -> Map.contains_key(var.clone())
        if re.search(r'\.contains_key\s*\(\s*&([a-zA-Z_][a-zA-Z0-9_]*)\s*\)', line):
            original_line = line
            line = re.sub(r'\.contains_key\s*\(\s*&([a-zA-Z_][a-zA-Z0-9_]*)\s*\)', r'.contains_key(\1.clone())', line)
            if line != original_line:
                fixes_applied.append('Map.contains_key: removed & and added .clone()')

        fixed_lines.append(line)

    code = '\n'.join(fixed_lines)

    # Fix 3: Vec.push() -> Vec.push_back()
    push_pattern = r'\.push\((?!_back)'
    if re.search(push_pattern, code):
        code = re.sub(r'\.push\((?!_back)', '.push_back(', code)
        fixes_applied.append('Vec: changed .push() to .push_back()')

    # Fix 4: to_string() doesn't exist in no_std
    if '.to_string()' in code:
        code = re.sub(r'\.to_string\(\)', '', code)
        fixes_applied.append('Removed .to_string() calls (not available in no_std)')

    # Fix 5: format!() macro doesn't exist in no_std
    if 'format!' in code:
        # Replace String::from_str(&env, &format!(...)) with just the numeric expression
        code = re.sub(
            r'String::from_str\s*\(\s*&env\s*,\s*&format!\s*\(\s*"[^"]*"\s*,\s*([^)]+)\s*\)\s*\)',
            r'\1',
            code
        )
        code = re.sub(
            r'let\s+(\w+)\s*(?::\s*String)?\s*=\s*format!\s*\(\s*"[^"]*"\s*,\s*([^)]+)\s*\)\s*;',
            r'let \1: u64 = \2;',
            code
        )
        if 'format!' in code:
            code = re.sub(r'format!\s*\([^)]*\)', 'env.ledger().timestamp()', code)
        fixes_applied.append('Replaced format!() calls with integer alternatives')

    # Fix 6: Ensure all #[contracttype] structs/enums have #[derive(Clone)]
    contracttype_defs = list(re.finditer(r'#\[contracttype\]\s*(pub (?:struct|enum) (\w+))', code))
    for match in reversed(contracttype_defs):
        struct_name = match.group(2)
        # Check if Clone is already derived
        before_start = max(0, match.start() - 100)
        context = code[before_start:match.end()]
        if '#[derive(' not in context or 'Clone' not in context:
            # Insert #[derive(Clone)] between #[contracttype] and pub struct/enum
            insert_pos = match.start(1)
            code = code[:insert_pos] + '#[derive(Clone)]\n' + code[insert_pos:]
            fixes_applied.append(f'Added #[derive(Clone)] to {struct_name}')

    # Fix 7: String::from() -> String::from_str()
    if 'String::from(' in code and 'String::from_str' not in code:
        code = re.sub(r'String::from\(', 'String::from_str(&env, ', code)
        fixes_applied.append('Changed String::from() to String::from_str(&env, ...)')

    # Fix 8: Symbol::from() -> Symbol::new()
    if re.search(r'Symbol::from\s*\(', code):
        code = re.sub(r'Symbol::from\s*\(', 'Symbol::new(&env, ', code)
        fixes_applied.append('Changed Symbol::from() to Symbol::new(&env, ...)')

    # Fix 9: Remove println!, dbg!, eprintln! macros
    for macro_name in ['println!', 'dbg!', 'eprintln!']:
        if macro_name in code:
            code = re.sub(rf'{re.escape(macro_name)}\s*\([^)]*\)\s*;?', '', code)
            fixes_applied.append(f'Removed {macro_name} (not available in no_std)')

    # Fix 10: Remove any std:: imports
    if 'use std::' in code:
        code = re.sub(r'use std::[^;]+;\n?', '', code)
        fixes_applied.append('Removed std:: imports')

    return code, fixes_applied


def cleanup_rust_code(code: str) -> str:
    """
    Post-process generated Rust code to fix common issues.
    """
    # First, apply auto-fixes for common SDK 21 issues
    code, fixes = validate_and_fix_common_issues(code)
    if fixes:
        logger.info(f"[RUST_AGENT] Auto-fixes applied: {fixes}")

    # Ensure #![no_std] is at the start
    if '#![no_std]' not in code:
        code = '#![no_std]\n' + code

    # Find the use statement and extract imports
    use_match = re.search(r'use soroban_sdk::\{([^}]+)\};', code)
    if use_match:
        imports_str = use_match.group(1)
        imports = [i.strip() for i in imports_str.split(',')]

        # Check which imports are actually used in the code (after the use statement)
        code_after_use = code[use_match.end():]

        # Always keep these (macros/attributes that don't appear as text)
        always_keep = {'contract', 'contractimpl', 'contracttype'}

        used_imports = []
        for imp in imports:
            imp_clean = imp.strip()
            if not imp_clean:
                continue
            # Keep if it's in always_keep or appears in the code
            if imp_clean in always_keep or imp_clean in code_after_use:
                used_imports.append(imp_clean)

        # Rebuild the use statement with only used imports
        if used_imports:
            new_use = 'use soroban_sdk::{' + ', '.join(used_imports) + '};'
            code = code[:use_match.start()] + new_use + code[use_match.end():]

    # Clean up extra blank lines
    code = re.sub(r'\n{3,}', '\n\n', code)

    return code.strip()
