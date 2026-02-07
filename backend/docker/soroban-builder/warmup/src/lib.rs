//! Minimal warmup contract to pre-compile Soroban dependencies.
//! This contract is built during Docker image creation to cache all crates.

#![no_std]
use soroban_sdk::{contract, contractimpl, Env, Symbol, String};

#[contract]
pub struct WarmupContract;

#[contractimpl]
impl WarmupContract {
    /// Simple function to ensure all SDK features are compiled
    pub fn hello(env: Env, name: String) -> String {
        let greeting = Symbol::new(&env, "Hello");
        name
    }
}

mod test {
    #![cfg(test)]
    use super::*;
    use soroban_sdk::Env;

    #[test]
    fn test_warmup() {
        let env = Env::default();
        let contract_id = env.register_contract(None, WarmupContract);
    }
}
