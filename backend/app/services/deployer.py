"""
Stellar Deployment Service

Deploys compiled WASM contracts to Stellar Testnet.
Handles:
- Hot wallet management (funded via Friendbot)
- WASM upload
- Contract instantiation
- Contract ID retrieval
"""

import asyncio
from typing import TypedDict, Optional
import httpx

from stellar_sdk import (
    Keypair,
    Network,
    Server,
    TransactionBuilder,
    Asset,
)
from stellar_sdk import xdr as stellar_xdr
from stellar_sdk.soroban_server import SorobanServer
from stellar_sdk.soroban_rpc import GetTransactionStatus

from app.core.config import settings


class DeploymentResult(TypedDict):
    success: bool
    contract_id: str | None
    wasm_hash: str | None
    error: str | None


# Network configurations
NETWORKS = {
    "testnet": {
        "horizon_url": "https://horizon-testnet.stellar.org",
        "soroban_rpc_url": "https://soroban-testnet.stellar.org",
        "network_passphrase": Network.TESTNET_NETWORK_PASSPHRASE,
        "friendbot_url": "https://friendbot.stellar.org",
    },
    "futurenet": {
        "horizon_url": "https://horizon-futurenet.stellar.org",
        "soroban_rpc_url": "https://rpc-futurenet.stellar.org",
        "network_passphrase": Network.FUTURENET_NETWORK_PASSPHRASE,
        "friendbot_url": "https://friendbot-futurenet.stellar.org",
    },
}


async def deploy_contract(
    wasm_binary: bytes,
    network: str = "testnet",
    user_wallet: Optional[str] = None,
) -> DeploymentResult:
    """
    Deploy a compiled WASM contract to Stellar.
    
    Args:
        wasm_binary: Compiled WASM bytes
        network: Network to deploy to (testnet, futurenet)
        user_wallet: Optional user's public key for ownership
    
    Returns:
        DeploymentResult with contract ID or error
    """
    
    if network not in NETWORKS:
        return DeploymentResult(
            success=False,
            contract_id=None,
            wasm_hash=None,
            error=f"Unknown network: {network}"
        )
    
    network_config = NETWORKS[network]
    
    try:
        # Get or create hot wallet
        hot_wallet = await get_hot_wallet(network)
        
        if not hot_wallet:
            return DeploymentResult(
                success=False,
                contract_id=None,
                wasm_hash=None,
                error="Failed to initialize hot wallet"
            )
        
        # Deploy using Soroban RPC
        result = await _deploy_to_soroban(
            wasm_binary=wasm_binary,
            hot_wallet=hot_wallet,
            network_config=network_config,
            user_wallet=user_wallet,
        )
        
        return result
        
    except Exception as e:
        return DeploymentResult(
            success=False,
            contract_id=None,
            wasm_hash=None,
            error=str(e)
        )


async def get_hot_wallet(network: str) -> Keypair | None:
    """
    Get the hot wallet for deployments.
    
    If no secret is configured, generates a new keypair and funds via Friendbot.
    """
    
    # Check if we have a configured secret
    if settings.stellar_hot_wallet_secret:
        try:
            return Keypair.from_secret(settings.stellar_hot_wallet_secret)
        except Exception:
            pass
    
    # Generate new keypair and fund via Friendbot
    keypair = Keypair.random()
    
    network_config = NETWORKS.get(network, NETWORKS["testnet"])
    funded = await fund_via_friendbot(keypair.public_key, network_config["friendbot_url"])
    
    if not funded:
        return None
    
    return keypair


async def fund_via_friendbot(public_key: str, friendbot_url: str) -> bool:
    """Fund an account using Stellar Friendbot"""
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                friendbot_url,
                params={"addr": public_key},
                timeout=30.0,
            )
            return response.status_code == 200
    except Exception as e:
        print(f"Friendbot funding failed: {e}")
        return False


async def _deploy_to_soroban(
    wasm_binary: bytes,
    hot_wallet: Keypair,
    network_config: dict,
    user_wallet: Optional[str],
) -> DeploymentResult:
    """
    Deploy contract using Soroban RPC.

    Steps:
    1. Upload WASM to get hash
    2. Create contract instance
    3. Return contract ID
    """
    import hashlib
    import os

    try:
        soroban_server = SorobanServer(network_config["soroban_rpc_url"])

        # Get account info for sequence number
        account = soroban_server.load_account(hot_wallet.public_key)

        # Step 1: Upload WASM
        upload_tx = (
            TransactionBuilder(
                source_account=account,
                network_passphrase=network_config["network_passphrase"],
                base_fee=100000,
            )
            .append_upload_contract_wasm_op(wasm_binary)
            .set_timeout(300)
            .build()
        )

        # Prepare (simulate) the transaction
        try:
            prepared_upload = soroban_server.prepare_transaction(upload_tx)
        except Exception as sim_err:
            # Capture detailed simulation error for debugging
            error_detail = str(sim_err)
            print(f"Upload simulation failed: {error_detail}")

            # Try to extract more details from the exception
            if hasattr(sim_err, 'result'):
                print(f"Simulation result: {sim_err.result}")
            if hasattr(sim_err, 'response'):
                print(f"Simulation response: {sim_err.response}")
            if hasattr(sim_err, '__dict__'):
                print(f"Exception details: {sim_err.__dict__}")

            return DeploymentResult(
                success=False,
                contract_id=None,
                wasm_hash=None,
                error=f"Upload simulation failed: {error_detail}"
            )
        prepared_upload.sign(hot_wallet)

        # Submit upload transaction
        upload_response = soroban_server.send_transaction(prepared_upload)
        print(f"Upload TX submitted: {upload_response.hash}, status: {upload_response.status}")

        # Check if transaction was rejected immediately
        if upload_response.status == "ERROR":
            return DeploymentResult(
                success=False,
                contract_id=None,
                wasm_hash=None,
                error=f"Upload TX rejected: {upload_response.error}"
            )

        # Wait for upload confirmation
        wasm_hash = None
        for i in range(30):  # 30 second timeout
            await asyncio.sleep(1)
            tx_status = soroban_server.get_transaction(upload_response.hash)
            print(f"Upload TX poll {i+1}: status={tx_status.status}")
            if tx_status.status == GetTransactionStatus.SUCCESS:
                # Extract WASM hash from result
                wasm_hash = hashlib.sha256(wasm_binary).digest()
                break
            elif tx_status.status == GetTransactionStatus.FAILED:
                return DeploymentResult(
                    success=False,
                    contract_id=None,
                    wasm_hash=None,
                    error="WASM upload transaction failed"
                )

        if not wasm_hash:
            return DeploymentResult(
                success=False,
                contract_id=None,
                wasm_hash=None,
                error="WASM upload timed out"
            )

        # Step 2: Create contract instance
        # Refresh account for new sequence
        account = soroban_server.load_account(hot_wallet.public_key)

        # Generate random salt
        salt = os.urandom(32)

        create_tx = (
            TransactionBuilder(
                source_account=account,
                network_passphrase=network_config["network_passphrase"],
                base_fee=100000,
            )
            .append_create_contract_op(
                wasm_id=wasm_hash,
                address=hot_wallet.public_key,
                salt=salt,
            )
            .set_timeout(300)
            .build()
        )

        # Prepare and sign
        try:
            prepared_create = soroban_server.prepare_transaction(create_tx)
        except Exception as sim_err:
            # Capture detailed simulation error for debugging
            error_detail = str(sim_err)
            print(f"Create contract simulation failed: {error_detail}")
            return DeploymentResult(
                success=False,
                contract_id=None,
                wasm_hash=wasm_hash.hex() if wasm_hash else None,
                error=f"Contract creation simulation failed: {error_detail}"
            )
        prepared_create.sign(hot_wallet)

        # Submit create transaction
        create_response = soroban_server.send_transaction(prepared_create)
        print(f"Create TX submitted: {create_response.hash}, status: {create_response.status}")

        # Check if transaction was rejected immediately
        if create_response.status == "ERROR":
            return DeploymentResult(
                success=False,
                contract_id=None,
                wasm_hash=wasm_hash.hex() if wasm_hash else None,
                error=f"Create TX rejected: {create_response.error}"
            )

        # Wait for create confirmation and extract contract ID
        contract_id = None
        for i in range(30):
            await asyncio.sleep(1)
            tx_status = soroban_server.get_transaction(create_response.hash)
            print(f"Create TX poll {i+1}: status={tx_status.status}")
            if tx_status.status == GetTransactionStatus.SUCCESS:
                # Extract contract ID from the transaction result
                try:
                    from stellar_sdk import StrKey, scval, Address
                    from stellar_sdk.xdr import SCValType, SCAddressType

                    # Debug: print all available attributes on tx_status
                    print(f"tx_status attributes: {[a for a in dir(tx_status) if not a.startswith('_')]}")
                    print(f"tx_status type: {type(tx_status)}")

                    # Method 1: Try direct return_value if available (newer SDK)
                    if hasattr(tx_status, 'return_value') and tx_status.return_value:
                        rv = tx_status.return_value
                        print(f"Direct return_value found, type: {type(rv)}")
                        # return_value might already be SCVal XDR
                        if isinstance(rv, str):
                            # It's XDR string, decode it
                            rv = stellar_xdr.SCVal.from_xdr(rv)
                        print(f"return_value SCVal type: {rv.type}")

                        if rv.type == SCValType.SCV_ADDRESS:
                            addr = rv.address
                            if addr.type == SCAddressType.SC_ADDRESS_TYPE_CONTRACT:
                                contract_id = StrKey.encode_contract(bytes(addr.contract_id.hash))
                                print(f"Contract ID from return_value: {contract_id}")

                    # Method 2: Parse from result_meta_xdr
                    if not contract_id and tx_status.result_meta_xdr:
                        result_meta = stellar_xdr.TransactionMeta.from_xdr(tx_status.result_meta_xdr)
                        print(f"Meta version: v={result_meta.v}")

                        soroban_meta = None
                        if result_meta.v == 3 and result_meta.v3:
                            soroban_meta = result_meta.v3.soroban_meta
                        elif result_meta.v == 4 and result_meta.v4:
                            soroban_meta = result_meta.v4.soroban_meta

                        print(f"Found soroban_meta: {soroban_meta is not None}")

                        if soroban_meta and soroban_meta.return_value:
                            rv = soroban_meta.return_value
                            print(f"soroban_meta return_value type: {rv.type}")

                            if rv.type == SCValType.SCV_ADDRESS:
                                addr = rv.address
                                if addr.type == SCAddressType.SC_ADDRESS_TYPE_CONTRACT:
                                    # contract_id is Hash XDR type
                                    contract_id_xdr = addr.contract_id
                                    print(f"contract_id type: {type(contract_id_xdr)}")
                                    print(f"contract_id dir: {[a for a in dir(contract_id_xdr) if not a.startswith('_')]}")

                                    # Hash XDR has hash attribute containing Uint256
                                    if hasattr(contract_id_xdr, 'hash'):
                                        raw_bytes = bytes(contract_id_xdr.hash)
                                    elif hasattr(contract_id_xdr, 'to_xdr_bytes'):
                                        raw_bytes = contract_id_xdr.to_xdr_bytes()
                                    else:
                                        # Try direct conversion
                                        raw_bytes = contract_id_xdr

                                    contract_id = StrKey.encode_contract(raw_bytes)
                                    print(f"Contract ID from meta: {contract_id}")

                except Exception as parse_err:
                    import traceback
                    traceback.print_exc()
                    return DeploymentResult(
                        success=False,
                        contract_id=None,
                        wasm_hash=wasm_hash.hex() if wasm_hash else None,
                        error=f"Failed to parse contract ID: {parse_err}"
                    )

                if not contract_id:
                    return DeploymentResult(
                        success=False,
                        contract_id=None,
                        wasm_hash=wasm_hash.hex() if wasm_hash else None,
                        error="Contract created but could not extract contract ID from result"
                    )

                break
            elif tx_status.status == GetTransactionStatus.FAILED:
                return DeploymentResult(
                    success=False,
                    contract_id=None,
                    wasm_hash=wasm_hash.hex() if wasm_hash else None,
                    error="Contract creation transaction failed"
                )

        if not contract_id:
            return DeploymentResult(
                success=False,
                contract_id=None,
                wasm_hash=wasm_hash.hex() if wasm_hash else None,
                error="Contract creation timed out"
            )

        return DeploymentResult(
            success=True,
            contract_id=contract_id,
            wasm_hash=wasm_hash.hex() if isinstance(wasm_hash, bytes) else wasm_hash,
            error=None
        )

    except Exception as e:
        return DeploymentResult(
            success=False,
            contract_id=None,
            wasm_hash=None,
            error=f"Deployment failed: {str(e)}"
        )


async def check_stellar_connection(network: str = "testnet") -> bool:
    """Check if Stellar network is reachable"""
    
    network_config = NETWORKS.get(network, NETWORKS["testnet"])
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{network_config['horizon_url']}/",
                timeout=5.0,
            )
            return response.status_code == 200
    except Exception:
        return False


async def get_account_info(public_key: str, network: str = "testnet") -> dict | None:
    """Get account information from Stellar"""
    
    network_config = NETWORKS.get(network, NETWORKS["testnet"])
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{network_config['horizon_url']}/accounts/{public_key}",
                timeout=10.0,
            )
            if response.status_code == 200:
                return response.json()
            return None
    except Exception:
        return None
