"""
CarbonChain - REST API
=======================
API REST per interazione con blockchain.

Security Level: MEDIUM
Last Updated: 2025-11-27
Version: 1.0.0

Endpoints:
- /blockchain/* - Blockchain queries
- /wallet/* - Wallet operations
- /certificate/* - Certificate management
- /compensation/* - Compensation operations
- /mining/* - Mining control
- /network/* - P2P network operations (Phase 2)
"""

from typing import Optional, List, Dict, Any
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import time

# Internal imports
from carbon_chain.domain.blockchain import Blockchain
from carbon_chain.domain.mempool import Mempool
from carbon_chain.wallet.hd_wallet import HDWallet
from carbon_chain.services.wallet_service import WalletService
from carbon_chain.services.certificate_service import CertificateService
from carbon_chain.services.compensation_service import CompensationService
from carbon_chain.services.project_service import ProjectService
from carbon_chain.services.mining_service import MiningService
from carbon_chain.constants import satoshi_to_coin, coin_to_satoshi
from carbon_chain.logging_setup import get_logger
from carbon_chain.config import ChainSettings


# ============================================================================
# MODULE LOGGER
# ============================================================================

logger = get_logger("api")


# ============================================================================
# PYDANTIC MODELS (Request/Response)
# ============================================================================

class BlockResponse(BaseModel):
    """Block response model"""
    height: int
    hash: str
    previous_hash: str
    timestamp: int
    difficulty: int
    nonce: int
    tx_count: int
    transactions: List[Dict]


class TransactionResponse(BaseModel):
    """Transaction response model"""
    txid: str
    type: str
    timestamp: int
    inputs: List[Dict]
    outputs: List[Dict]


class BalanceResponse(BaseModel):
    """Balance response model"""
    address: str
    balance_satoshi: int
    balance_coin: float
    certified_satoshi: int
    compensated_satoshi: int
    utxo_count: int


class CreateTransferRequest(BaseModel):
    """Transfer creation request"""
    from_address_index: int = Field(..., ge=0)
    to_address: str
    amount_coin: float = Field(..., gt=0)
    change_address_index: Optional[int] = None


class CreateCertificateRequest(BaseModel):
    """Certificate assignment request"""
    from_address_index: int = Field(..., ge=0)
    certificate_data: Dict
    amount_kg: int = Field(..., gt=0)
    change_address_index: Optional[int] = None


class CreateCompensationRequest(BaseModel):
    """Compensation creation request"""
    from_address_index: int = Field(..., ge=0)
    project_data: Dict
    amount_kg: int = Field(..., gt=0)
    certificate_filter: Optional[str] = None
    change_address_index: Optional[int] = None


class CreateWalletRequest(BaseModel):
    """Wallet creation request"""
    strength: int = Field(default=128, ge=128, le=256)
    passphrase: str = Field(default="")


class RecoverWalletRequest(BaseModel):
    """Wallet recovery request"""
    mnemonic: str
    passphrase: str = Field(default="")


# ============================================================================
# API STATE
# ============================================================================

class APIState:
    """Global API state"""
    blockchain: Optional[Blockchain] = None
    mempool: Optional[Mempool] = None
    config: Optional[ChainSettings] = None
    wallet_service: Optional[WalletService] = None
    certificate_service: Optional[CertificateService] = None
    compensation_service: Optional[CompensationService] = None
    project_service: Optional[ProjectService] = None
    mining_service: Optional[MiningService] = None
    
    # Active wallets (in-memory, per session)
    active_wallets: Dict[str, HDWallet] = {}
    
    # Network node (Phase 2)
    network_node: Optional[Any] = None  # NetworkNode instance


state = APIState()


# ============================================================================
# FASTAPI APP
# ============================================================================

app = FastAPI(
    title="CarbonChain API",
    description="REST API for CarbonChain blockchain",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production: specify allowed origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# DEPENDENCIES
# ============================================================================

def get_blockchain() -> Blockchain:
    """Dependency: get blockchain"""
    if state.blockchain is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Blockchain not initialized"
        )
    return state.blockchain


def get_mempool() -> Mempool:
    """Dependency: get mempool"""
    if state.mempool is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Mempool not initialized"
        )
    return state.mempool


def get_wallet_service() -> WalletService:
    """Dependency: get wallet service"""
    if state.wallet_service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Wallet service not initialized"
        )
    return state.wallet_service


# ============================================================================
# BLOCKCHAIN ENDPOINTS
# ============================================================================

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": "CarbonChain API",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/blockchain/info")
async def get_blockchain_info(blockchain: Blockchain = Depends(get_blockchain)):
    """Get blockchain info"""
    stats = blockchain.get_statistics()
    
    return {
        "network": blockchain.config.network,
        "height": blockchain.get_height(),
        "difficulty": blockchain.current_difficulty,
        "supply": {
            "total_satoshi": stats["supply"]["total"],
            "total_coin": satoshi_to_coin(stats["supply"]["total"]),
            "certified_satoshi": stats["supply"]["certified"],
            "compensated_satoshi": stats["supply"]["compensated"]
        },
        "utxos": stats["utxo_count"],
        "addresses": stats["address_count"],
        "certificates": stats["certificates_count"],
        "projects": stats["projects_count"]
    }


@app.get("/blockchain/block/{height}", response_model=BlockResponse)
async def get_block(
    height: int,
    blockchain: Blockchain = Depends(get_blockchain)
):
    """Get block by height"""
    block = blockchain.get_block(height)
    
    if not block:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Block at height {height} not found"
        )
    
    return BlockResponse(
        height=block.header.height,
        hash=block.compute_block_hash(),
        previous_hash=block.header.previous_hash,
        timestamp=block.header.timestamp,
        difficulty=block.header.difficulty,
        nonce=block.header.nonce,
        tx_count=len(block.transactions),
        transactions=[tx.to_dict(include_txid=True) for tx in block.transactions]
    )


@app.get("/blockchain/latest")
async def get_latest_block(blockchain: Blockchain = Depends(get_blockchain)):
    """Get latest block"""
    block = blockchain.get_latest_block()
    
    if not block:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No blocks found"
        )
    
    return BlockResponse(
        height=block.header.height,
        hash=block.compute_block_hash(),
        previous_hash=block.header.previous_hash,
        timestamp=block.header.timestamp,
        difficulty=block.header.difficulty,
        nonce=block.header.nonce,
        tx_count=len(block.transactions),
        transactions=[tx.to_dict(include_txid=True) for tx in block.transactions]
    )


# ============================================================================
# WALLET ENDPOINTS
# ============================================================================

@app.post("/wallet/create")
async def create_wallet(
    request: CreateWalletRequest,
    wallet_service: WalletService = Depends(get_wallet_service)
):
    """Create new wallet"""
    try:
        wallet = wallet_service.create_wallet(
            strength=request.strength,
            passphrase=request.passphrase
        )
        
        # Store in active wallets
        wallet_id = wallet.get_address(0)
        state.active_wallets[wallet_id] = wallet
        
        return {
            "wallet_id": wallet_id,
            "mnemonic": wallet.get_mnemonic(),  # ⚠️ BACKUP THIS!
            "addresses": wallet.get_addresses(5),
            "warning": "BACKUP YOUR MNEMONIC PHRASE!"
        }
    
    except Exception as e:
        logger.error(f"Wallet creation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@app.post("/wallet/recover")
async def recover_wallet(
    request: RecoverWalletRequest,
    wallet_service: WalletService = Depends(get_wallet_service)
):
    """Recover wallet from mnemonic"""
    try:
        wallet = wallet_service.recover_wallet(
            mnemonic=request.mnemonic,
            passphrase=request.passphrase
        )
        
        # Store in active wallets
        wallet_id = wallet.get_address(0)
        state.active_wallets[wallet_id] = wallet
        
        return {
            "wallet_id": wallet_id,
            "addresses": wallet.get_addresses(5)
        }
    
    except Exception as e:
        logger.error(f"Wallet recovery failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@app.get("/wallet/{wallet_id}/balance/{address_index}", response_model=BalanceResponse)
async def get_wallet_balance(
    wallet_id: str,
    address_index: int,
    wallet_service: WalletService = Depends(get_wallet_service)
):
    """Get wallet address balance"""
    wallet = state.active_wallets.get(wallet_id)
    
    if not wallet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Wallet not found. Create or recover wallet first."
        )
    
    try:
        address = wallet.get_address(address_index)
        balance_detailed = wallet_service.get_balance_detailed(wallet, address_index)
        utxos = wallet_service.list_utxos(wallet, address_index)
        
        return BalanceResponse(
            address=address,
            balance_satoshi=balance_detailed["total"],
            balance_coin=satoshi_to_coin(balance_detailed["total"]),
            certified_satoshi=balance_detailed["certified"],
            compensated_satoshi=balance_detailed["compensated"],
            utxo_count=len(utxos)
        )
    
    except Exception as e:
        logger.error(f"Balance query failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@app.post("/wallet/{wallet_id}/transfer")
async def create_transfer(
    wallet_id: str,
    request: CreateTransferRequest,
    wallet_service: WalletService = Depends(get_wallet_service),
    mempool: Mempool = Depends(get_mempool)
):
    """Create transfer transaction"""
    wallet = state.active_wallets.get(wallet_id)
    
    if not wallet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Wallet not found"
        )
    
    try:
        # Create transaction
        tx = wallet_service.create_transfer_coin(
            wallet=wallet,
            from_address_index=request.from_address_index,
            to_address=request.to_address,
            amount_coin=request.amount_coin,
            change_address_index=request.change_address_index
        )
        
        # Add to mempool
        mempool.add_transaction(tx)
        
        txid = tx.compute_txid()
        
        logger.info(
            f"Transfer created",
            extra_data={
                "txid": txid[:16] + "...",
                "amount": request.amount_coin
            }
        )
        
        return {
            "txid": txid,
            "status": "pending",
            "message": "Transaction added to mempool"
        }
    
    except Exception as e:
        logger.error(f"Transfer creation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


# ============================================================================
# CERTIFICATE ENDPOINTS
# ============================================================================

@app.post("/certificate/assign")
async def assign_certificate(
    wallet_id: str,
    request: CreateCertificateRequest,
    mempool: Mempool = Depends(get_mempool)
):
    """Assign certificate to coins"""
    wallet = state.active_wallets.get(wallet_id)
    
    if not wallet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Wallet not found"
        )
    
    try:
        # Create certificate assignment
        tx = state.certificate_service.create_certificate_assignment(
            wallet=wallet,
            from_address_index=request.from_address_index,
            certificate_data=request.certificate_data,
            amount_kg=request.amount_kg,
            change_address_index=request.change_address_index
        )
        
        # Add to mempool
        mempool.add_transaction(tx)
        
        txid = tx.compute_txid()
        
        return {
            "txid": txid,
            "certificate_id": request.certificate_data["certificate_id"],
            "status": "pending"
        }
    
    except Exception as e:
        logger.error(f"Certificate assignment failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@app.get("/certificate/{cert_id}")
async def get_certificate(
    cert_id: str,
    blockchain: Blockchain = Depends(get_blockchain)
):
    """Get certificate info"""
    cert_info = state.certificate_service.get_certificate_info(cert_id)
    
    if not cert_info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Certificate {cert_id} not found"
        )
    
    return cert_info


@app.get("/certificate/list")
async def list_certificates(blockchain: Blockchain = Depends(get_blockchain)):
    """List all certificates"""
    certificates = state.certificate_service.list_certificates()
    return {"certificates": certificates, "count": len(certificates)}


# ============================================================================
# COMPENSATION ENDPOINTS
# ============================================================================

@app.post("/compensation/create")
async def create_compensation(
    wallet_id: str,
    request: CreateCompensationRequest,
    mempool: Mempool = Depends(get_mempool)
):
    """Create compensation transaction"""
    wallet = state.active_wallets.get(wallet_id)
    
    if not wallet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Wallet not found"
        )
    
    try:
        # Create compensation
        tx = state.compensation_service.create_compensation_transaction(
            wallet=wallet,
            from_address_index=request.from_address_index,
            project_data=request.project_data,
            amount_kg=request.amount_kg,
            certificate_filter=request.certificate_filter,
            change_address_index=request.change_address_index
        )
        
        # Add to mempool
        mempool.add_transaction(tx)
        
        txid = tx.compute_txid()
        
        return {
            "txid": txid,
            "project_id": request.project_data["project_id"],
            "status": "pending"
        }
    
    except Exception as e:
        logger.error(f"Compensation creation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@app.get("/project/{project_id}")
async def get_project(
    project_id: str,
    blockchain: Blockchain = Depends(get_blockchain)
):
    """Get project info"""
    proj_info = state.project_service.get_project_info(project_id)
    
    if not proj_info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {project_id} not found"
        )
    
    return proj_info


@app.get("/project/list")
async def list_projects(
    project_type: Optional[str] = None,
    blockchain: Blockchain = Depends(get_blockchain)
):
    """List projects"""
    projects = state.project_service.list_projects(filter_type=project_type)
    return {"projects": projects, "count": len(projects)}


# ============================================================================
# MINING ENDPOINTS
# ============================================================================

@app.post("/mining/start")
async def start_mining(miner_address: str):
    """Start mining"""
    if state.mining_service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Mining service not initialized"
        )
    
    try:
        # Update miner address
        state.mining_service.miner_address = miner_address
        state.mining_service.start_mining(background=True)
        
        return {
            "status": "mining_started",
            "miner_address": miner_address
        }
    
    except Exception as e:
        logger.error(f"Mining start failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@app.post("/mining/stop")
async def stop_mining():
    """Stop mining"""
    if state.mining_service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Mining service not initialized"
        )
    
    state.mining_service.stop_mining()
    
    return {"status": "mining_stopped"}


@app.get("/mining/stats")
async def get_mining_stats():
    """Get mining statistics"""
    if state.mining_service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Mining service not initialized"
        )
    
    stats = state.mining_service.get_mining_statistics()
    return stats


# ============================================================================
# MEMPOOL ENDPOINTS
# ============================================================================

@app.get("/mempool/info")
async def get_mempool_info(mempool: Mempool = Depends(get_mempool)):
    """Get mempool info"""
    stats = mempool.get_statistics()
    return stats


@app.get("/mempool/transactions")
async def get_mempool_transactions(
    limit: int = 100,
    mempool: Mempool = Depends(get_mempool)
):
    """Get pending transactions"""
    all_tx = mempool.get_all_transactions()
    
    return {
        "transactions": [tx.to_dict(include_txid=True) for tx in all_tx[:limit]],
        "total": len(all_tx)
    }


# ============================================================================
# NETWORK ENDPOINTS (Phase 2)
# ============================================================================

@app.get("/network/info")
async def get_network_info():
    """Get network node information"""
    if state.network_node is None:
        return {
            "p2p_enabled": False,
            "message": "P2P network not initialized"
        }
    
    try:
        network_info = state.network_node.get_network_info()
        return network_info
    except Exception as e:
        logger.error(f"Failed to get network info: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@app.get("/network/peers")
async def list_peers():
    """List connected peers"""
    if state.network_node is None:
        return {
            "peers": [],
            "count": 0,
            "message": "P2P network not initialized"
        }
    
    try:
        peer_manager = state.network_node.peer_manager
        peers_list = []
        
        for peer_id, peer in peer_manager.peers.items():
            peers_list.append({
                "peer_id": peer_id,
                "address": peer.info.address,
                "port": peer.info.port,
                "state": peer.state.value,
                "height": peer.info.start_height,
                "version": peer.info.version,
                "user_agent": peer.info.user_agent
            })
        
        return {
            "peers": peers_list,
            "count": len(peers_list),
            "max_peers": peer_manager.max_peers
        }
    except Exception as e:
        logger.error(f"Failed to list peers: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@app.get("/network/sync/status")
async def get_sync_status():
    """Get blockchain sync status"""
    if state.network_node is None:
        return {
            "is_syncing": False,
            "message": "P2P network not initialized"
        }
    
    try:
        sync_state = state.network_node.synchronizer.get_sync_state()
        return sync_state
    except Exception as e:
        logger.error(f"Failed to get sync status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@app.post("/network/sync/start")
async def start_sync():
    """Start blockchain synchronization"""
    if state.network_node is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="P2P network not initialized"
        )
    
    try:
        # Trigger sync in background
        import asyncio
        asyncio.create_task(state.network_node.sync_blockchain())
        
        return {
            "status": "sync_started",
            "message": "Blockchain synchronization started"
        }
    except Exception as e:
        logger.error(f"Failed to start sync: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


# ============================================================================
# MULTISIG ENDPOINTS (Phase 3)
# ============================================================================

class CreateMultiSigRequest(BaseModel):
    """MultiSig wallet creation request"""
    m: int = Field(..., ge=1, description="Required signatures")
    n: int = Field(..., ge=1, description="Total participants")
    my_index: int = Field(..., ge=0, description="My participant index")
    other_public_keys: List[str] = Field(..., description="Other public keys (hex)")
    wallet_name: str = Field(..., description="Wallet name")


class SignPSBTRequest(BaseModel):
    """PSBT signing request"""
    wallet_name: str
    psbt_data: Dict


@app.post("/multisig/create")
async def create_multisig_wallet(
    request: CreateMultiSigRequest,
    blockchain: Blockchain = Depends(get_blockchain)
):
    """Create multi-signature wallet"""
    try:
        from carbon_chain.services.multisig_service import MultiSigService
        
        service = MultiSigService(blockchain, state.config)
        
        # Convert hex public keys to bytes
        other_pks = [bytes.fromhex(pk) for pk in request.other_public_keys]
        
        wallet = service.create_multisig_wallet(
            m=request.m,
            n=request.n,
            my_index=request.my_index,
            other_public_keys=other_pks,
            wallet_name=request.wallet_name
        )
        
        return {
            "wallet_name": request.wallet_name,
            "address": wallet.get_address(),
            "config": wallet.config.to_dict(),
            "my_index": wallet.my_index,
            "my_public_key": wallet.my_public_key.hex()
        }
    
    except Exception as e:
        logger.error(f"MultiSig creation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@app.get("/multisig/list")
async def list_multisig_wallets(blockchain: Blockchain = Depends(get_blockchain)):
    """List multisig wallets"""
    try:
        from carbon_chain.services.multisig_service import MultiSigService
        
        service = MultiSigService(blockchain, state.config)
        wallets = service.list_wallets()
        
        return {"wallets": wallets, "count": len(wallets)}
    
    except Exception as e:
        logger.error(f"List multisig failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@app.get("/multisig/{wallet_name}/balance")
async def get_multisig_balance(
    wallet_name: str,
    blockchain: Blockchain = Depends(get_blockchain)
):
    """Get multisig wallet balance"""
    try:
        from carbon_chain.services.multisig_service import MultiSigService
        
        service = MultiSigService(blockchain, state.config)
        wallet = service.load_wallet(wallet_name)
        balance = service.get_balance(wallet)
        utxos = service.get_utxos(wallet)
        
        return {
            "wallet_name": wallet_name,
            "address": wallet.get_address(),
            "type": f"{wallet.config.m}-of-{wallet.config.n}",
            "balance_satoshi": balance,
            "balance_coin": satoshi_to_coin(balance),
            "utxo_count": len(utxos)
        }
    
    except Exception as e:
        logger.error(f"Get multisig balance failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@app.post("/multisig/{wallet_name}/sign")
async def sign_multisig_psbt(
    wallet_name: str,
    request: SignPSBTRequest,
    blockchain: Blockchain = Depends(get_blockchain)
):
    """Sign PSBT with multisig wallet"""
    try:
        from carbon_chain.services.multisig_service import MultiSigService
        from carbon_chain.wallet.multisig import PSBT
        
        service = MultiSigService(blockchain, state.config)
        wallet = service.load_wallet(wallet_name)
        
        # Reconstruct PSBT
        psbt = PSBT.from_dict(request.psbt_data)
        
        # Sign
        success = service.sign_psbt(wallet, psbt)
        
        return {
            "success": success,
            "signatures_collected": len(psbt.partial_signatures),
            "signatures_required": psbt.multisig_config.m,
            "is_finalized": psbt.is_finalized,
            "psbt": psbt.to_dict()
        }
    
    except Exception as e:
        logger.error(f"PSBT signing failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


# ============================================================================
# STEALTH ADDRESS ENDPOINTS (Phase 3)
# ============================================================================

class CreateStealthWalletRequest(BaseModel):
    """Stealth wallet creation request"""
    wallet_name: str


class CreateStealthPaymentRequest(BaseModel):
    """Stealth payment creation request"""
    receiver_address: str
    amount_satoshi: int


@app.post("/stealth/create")
async def create_stealth_wallet(
    request: CreateStealthWalletRequest,
    blockchain: Blockchain = Depends(get_blockchain)
):
    """Create stealth address wallet"""
    try:
        from carbon_chain.services.stealth_service import StealthService
        
        service = StealthService(blockchain, state.config)
        wallet = service.create_stealth_wallet(request.wallet_name)
        
        return {
            "wallet_name": request.wallet_name,
            "stealth_address": wallet.get_address(),
            "scan_public_key": wallet.stealth_address.scan_public_key.hex(),
            "spend_public_key": wallet.stealth_address.spend_public_key.hex(),
            "warning": "Keep private keys secure!"
        }
    
    except Exception as e:
        logger.error(f"Stealth wallet creation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@app.get("/stealth/list")
async def list_stealth_wallets(blockchain: Blockchain = Depends(get_blockchain)):
    """List stealth wallets"""
    try:
        from carbon_chain.services.stealth_service import StealthService
        
        service = StealthService(blockchain, state.config)
        wallets = service.list_wallets()
        
        return {"wallets": wallets, "count": len(wallets)}
    
    except Exception as e:
        logger.error(f"List stealth failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@app.get("/stealth/{wallet_name}/payments")
async def get_stealth_payments(
    wallet_name: str,
    blockchain: Blockchain = Depends(get_blockchain)
):
    """Get received stealth payments"""
    try:
        from carbon_chain.services.stealth_service import StealthService
        
        service = StealthService(blockchain, state.config)
        wallet = service.load_wallet(wallet_name)
        
        payments = service.get_received_payments(wallet)
        
        total = sum(p["amount"] for p in payments)
        
        return {
            "wallet_name": wallet_name,
            "payments": payments,
            "count": len(payments),
            "total_amount_satoshi": total,
            "total_amount_coin": satoshi_to_coin(total)
        }
    
    except Exception as e:
        logger.error(f"Get stealth payments failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@app.post("/stealth/payment/create")
async def create_stealth_payment(
    request: CreateStealthPaymentRequest,
    blockchain: Blockchain = Depends(get_blockchain)
):
    """Create stealth payment"""
    try:
        from carbon_chain.services.stealth_service import StealthService
        from carbon_chain.wallet.stealth_address import StealthAddress
        
        service = StealthService(blockchain, state.config)
        
        # Parse receiver stealth address
        # (In production: implement proper address parsing)
        # For now, assume it's passed correctly
        
        # This is simplified - in production need proper address parsing
        logger.info(f"Creating stealth payment to {request.receiver_address}")
        
        return {
            "message": "Stealth payment creation requires proper address format",
            "status": "not_implemented"
        }
    
    except Exception as e:
        logger.error(f"Stealth payment creation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


# ============================================================================
# MULTISIG ENDPOINTS (Phase 3)
# ============================================================================

class CreateMultiSigRequest(BaseModel):
    """MultiSig wallet creation request"""
    m: int = Field(..., ge=1, description="Required signatures")
    n: int = Field(..., ge=1, description="Total signatures")
    my_index: int = Field(..., ge=0, description="My participant index")
    other_public_keys: List[str] = Field(..., description="Other participants public keys (hex)")
    wallet_name: Optional[str] = None


class PSBTSignRequest(BaseModel):
    """PSBT signing request"""
    psbt_data: str = Field(..., description="PSBT JSON data")
    wallet_name: str = Field(..., description="MultiSig wallet name")


@app.post("/multisig/create")
async def create_multisig_wallet(
    request: CreateMultiSigRequest,
    blockchain: Blockchain = Depends(get_blockchain)
):
    """Create multi-signature wallet"""
    try:
        from carbon_chain.services.multisig_service import MultiSigService
        
        service = MultiSigService(blockchain, state.config)
        
        # Convert hex public keys to bytes
        other_pks = [bytes.fromhex(pk) for pk in request.other_public_keys]
        
        wallet = service.create_multisig_wallet(
            m=request.m,
            n=request.n,
            my_index=request.my_index,
            other_public_keys=other_pks,
            wallet_name=request.wallet_name
        )
        
        return {
            "wallet_info": wallet.get_info(),
            "address": wallet.get_address(),
            "public_key": wallet.my_public_key.hex()
        }
    
    except Exception as e:
        logger.error(f"MultiSig creation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@app.get("/multisig/list")
async def list_multisig_wallets(
    blockchain: Blockchain = Depends(get_blockchain)
):
    """List multi-signature wallets"""
    try:
        from carbon_chain.services.multisig_service import MultiSigService
        
        service = MultiSigService(blockchain, state.config)
        wallets = service.list_wallets()
        
        return {
            "wallets": wallets,
            "count": len(wallets)
        }
    
    except Exception as e:
        logger.error(f"Failed to list multisig wallets: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@app.post("/multisig/psbt/sign")
async def sign_psbt(
    request: PSBTSignRequest,
    blockchain: Blockchain = Depends(get_blockchain)
):
    """Sign PSBT with multi-signature wallet"""
    try:
        from carbon_chain.services.multisig_service import MultiSigService
        from carbon_chain.wallet.multisig import PSBT
        
        service = MultiSigService(blockchain, state.config)
        
        # Load wallet
        wallet = service.load_wallet(request.wallet_name)
        
        # Deserialize PSBT
        import json
        psbt_dict = json.loads(request.psbt_data)
        psbt = PSBT.from_dict(psbt_dict)
        
        # Sign
        success = service.sign_psbt(wallet, psbt)
        
        return {
            "success": success,
            "signatures_collected": len(psbt.partial_signatures),
            "required_signatures": psbt.multisig_config.m,
            "is_finalized": psbt.is_finalized,
            "psbt": psbt.to_dict()
        }
    
    except Exception as e:
        logger.error(f"PSBT signing failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


# ============================================================================
# STEALTH ADDRESS ENDPOINTS (Phase 3)
# ============================================================================

class CreateStealthWalletRequest(BaseModel):
    """Stealth wallet creation request"""
    wallet_name: Optional[str] = None


class CreateStealthPaymentRequest(BaseModel):
    """Stealth payment creation request"""
    receiver_address: str = Field(..., description="Receiver stealth address")
    amount_coin: float = Field(..., gt=0, description="Amount in CCO2")
    sender_wallet_id: str = Field(..., description="Sender wallet ID")
    from_address_index: int = Field(default=0, ge=0, description="Sender address index")


@app.post("/stealth/create")
async def create_stealth_wallet(
    request: CreateStealthWalletRequest,
    blockchain: Blockchain = Depends(get_blockchain)
):
    """Create stealth address wallet"""
    try:
        from carbon_chain.services.stealth_service import StealthService
        
        service = StealthService(blockchain, state.config)
        wallet = service.create_stealth_wallet(request.wallet_name)
        
        return {
            "stealth_address": wallet.get_address(),
            "wallet_name": request.wallet_name,
            "message": "Share stealth address for private payments"
        }
    
    except Exception as e:
        logger.error(f"Stealth wallet creation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@app.post("/stealth/payment")
async def create_stealth_payment(
    request: CreateStealthPaymentRequest,
    blockchain: Blockchain = Depends(get_blockchain),
    mempool: Mempool = Depends(get_mempool)
):
    """Create stealth payment"""
    try:
        from carbon_chain.services.stealth_service import StealthService
        from carbon_chain.wallet.stealth_address import StealthAddress
        
        # Get sender wallet
        sender_wallet = state.active_wallets.get(request.sender_wallet_id)
        if not sender_wallet:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Sender wallet not found"
            )
        
        service = StealthService(blockchain, state.config)
        
        # Parse receiver stealth address
        # (In production, implement proper parsing)
        # For now, assume it's properly formatted
        
        # TODO: Create stealth transaction
        # This requires integration with wallet service
        
        return {
            "status": "payment_created",
            "message": "Stealth payment functionality requires full integration"
        }
    
    except Exception as e:
        logger.error(f"Stealth payment creation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@app.get("/stealth/{wallet_name}/scan")
async def scan_stealth_payments(
    wallet_name: str,
    start_height: int = 0,
    blockchain: Blockchain = Depends(get_blockchain)
):
    """Scan blockchain for stealth payments"""
    try:
        from carbon_chain.services.stealth_service import StealthService
        
        service = StealthService(blockchain, state.config)
        wallet = service.load_wallet(wallet_name)
        
        # Scan blockchain
        payments = service.scan_for_payments(wallet, start_height)
        
        return {
            "wallet_name": wallet_name,
            "payments_found": len(payments),
            "payments": [
                {
                    "txid": tx.compute_txid(),
                    "one_time_address": payment.one_time_address
                }
                for tx, payment in payments
            ]
        }
    
    except Exception as e:
        logger.error(f"Stealth scan failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


# ============================================================================
# SMART CONTRACT ENDPOINTS (Phase 3)
# ============================================================================

class CreateTimelockRequest(BaseModel):
    """Timelock contract creation request"""
    recipient: str
    amount_coin: float = Field(..., gt=0)
    unlock_time: int = Field(..., description="Unix timestamp")


class CreateEscrowRequest(BaseModel):
    """Escrow contract creation request"""
    seller: str
    amount_coin: float = Field(..., gt=0)
    timeout: int = Field(..., description="Unix timestamp")


@app.post("/contract/timelock")
async def create_timelock_contract(
    request: CreateTimelockRequest,
    blockchain: Blockchain = Depends(get_blockchain)
):
    """Create timelock contract"""
    try:
        from carbon_chain.contracts.simple_contract import TimelockContract
        from carbon_chain.constants import coin_to_satoshi
        import hashlib
        import time
        
        amount_sat = coin_to_satoshi(request.amount_coin)
        
        # Generate contract ID
        contract_data = f"{request.recipient}{amount_sat}{request.unlock_time}{time.time()}"
        contract_id = hashlib.sha256(contract_data.encode()).hexdigest()[:16]
        
        contract = TimelockContract(
            contract_id=contract_id,
            creator="api_user",  # TODO: Get from auth
            conditions={
                "unlock_time": request.unlock_time,
                "recipient": request.recipient,
                "amount": amount_sat
            }
        )
        
        return {
            "contract_id": contract_id,
            "type": "timelock",
            "status": contract.status.value,
            "conditions": contract.conditions
        }
    
    except Exception as e:
        logger.error(f"Timelock creation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@app.post("/contract/escrow")
async def create_escrow_contract(
    request: CreateEscrowRequest,
    blockchain: Blockchain = Depends(get_blockchain)
):
    """Create escrow contract"""
    try:
        from carbon_chain.contracts.simple_contract import EscrowContract
        from carbon_chain.constants import coin_to_satoshi
        import hashlib
        import time
        
        buyer = "api_user"  # TODO: Get from auth
        amount_sat = coin_to_satoshi(request.amount_coin)
        
        # Generate contract ID
        contract_data = f"{buyer}{request.seller}{amount_sat}{request.timeout}{time.time()}"
        contract_id = hashlib.sha256(contract_data.encode()).hexdigest()[:16]
        
        contract = EscrowContract(
            contract_id=contract_id,
            creator=buyer,
            conditions={
                "buyer": buyer,
                "seller": request.seller,
                "amount": amount_sat,
                "timeout": request.timeout
            }
        )
        
        return {
            "contract_id": contract_id,
            "type": "escrow",
            "status": contract.status.value,
            "conditions": contract.conditions
        }
    
    except Exception as e:
        logger.error(f"Escrow creation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@app.post("/contract/{contract_id}/escrow/confirm")
async def confirm_escrow(
    contract_id: str,
    party: str = Field(..., description="buyer or seller")
):
    """Confirm escrow contract"""
    try:
        # TODO: Implement contract storage and retrieval
        return {
            "contract_id": contract_id,
            "party": party,
            "status": "confirmed",
            "message": "Contract confirmation requires full contract executor integration"
        }
    
    except Exception as e:
        logger.error(f"Escrow confirmation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


# ============================================================================
# POST-QUANTUM ENDPOINTS (Phase 3)
# ============================================================================

@app.get("/crypto/pq/status")
async def get_pq_status():
    """Get post-quantum cryptography status"""
    from carbon_chain.crypto.post_quantum import (
        is_post_quantum_available,
        get_available_algorithms
    )
    
    available = is_post_quantum_available()
    
    if available:
        algorithms = get_available_algorithms()
        return {
            "available": True,
            "algorithms": algorithms
        }
    else:
        return {
            "available": False,
            "message": "liboqs not installed - install liboqs-python for PQ crypto"
        }


@app.post("/crypto/pq/benchmark")
async def benchmark_pq_algorithm(
    algorithm: str = "dilithium3",
    iterations: int = 100
):
    """Benchmark post-quantum algorithm"""
    try:
        from carbon_chain.crypto.post_quantum import benchmark_algorithm
        
        results = benchmark_algorithm(algorithm, iterations)
        
        return {
            "algorithm": algorithm,
            "iterations": iterations,
            "results": results
        }
    
    except Exception as e:
        logger.error(f"PQ benchmark failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


# ============================================================================
# LIGHTNING NETWORK ENDPOINTS (Phase 3)
# ============================================================================

class OpenChannelRequest(BaseModel):
    """Payment channel opening request"""
    party_b: str = Field(..., description="Counterparty address")
    capacity: int = Field(..., gt=0, description="Channel capacity (Satoshi)")
    initial_balance: Optional[int] = None


@app.post("/lightning/channel/open")
async def open_payment_channel(
    request: OpenChannelRequest
):
    """Open Lightning payment channel"""
    try:
        from carbon_chain.layer2.lightning import ChannelManager
        
        # TODO: Integrate with global channel manager
        manager = ChannelManager()
        
        channel = manager.open_channel(
            party_a="api_user",  # TODO: Get from auth
            party_b=request.party_b,
            capacity=request.capacity,
            initial_balance_a=request.initial_balance
        )
        
        return {
            "channel_id": channel.channel_id,
            "state": channel.state.value,
            "capacity": channel.capacity,
            "balance_a": channel.balance_a,
            "balance_b": channel.balance_b
        }
    
    except Exception as e:
        logger.error(f"Channel opening failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@app.post("/lightning/channel/{channel_id}/transfer")
async def lightning_transfer(
    channel_id: str,
    amount: int = Field(..., gt=0, description="Amount (Satoshi)")
):
    """Transfer funds in Lightning channel"""
    try:
        # TODO: Integrate with global channel manager
        return {
            "channel_id": channel_id,
            "amount": amount,
            "status": "transferred",
            "message": "Lightning transfers require full channel manager integration"
        }
    
    except Exception as e:
        logger.error(f"Lightning transfer failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@app.get("/lightning/channels")
async def list_lightning_channels():
    """List Lightning payment channels"""
    try:
        # TODO: Integrate with global channel manager
        return {
            "channels": [],
            "count": 0,
            "message": "Lightning channel listing requires full channel manager integration"
        }
    
    except Exception as e:
        logger.error(f"Failed to list channels: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


# ============================================================================
# INITIALIZATION
# ============================================================================

def initialize_api(
    blockchain: Blockchain,
    mempool: Mempool,
    config: ChainSettings,
    network_node: Optional[Any] = None
) -> FastAPI:
    """
    Initialize API with services.
    
    Args:
        blockchain: Blockchain instance
        mempool: Mempool instance
        config: Chain configuration
        network_node: NetworkNode instance (optional, Phase 2)
    
    Returns:
        FastAPI: Initialized app
    
    Examples:
        >>> app = initialize_api(blockchain, mempool, config)
        >>> # Run with: uvicorn carbon_chain.api.rest_api:app
    """
    state.blockchain = blockchain
    state.mempool = mempool
    state.config = config
    state.network_node = network_node
    
    # Initialize services
    state.wallet_service = WalletService(blockchain, config)
    state.certificate_service = CertificateService(blockchain, config)
    state.compensation_service = CompensationService(blockchain, config)
    state.project_service = ProjectService(blockchain, config)
    state.mining_service = MiningService(
        blockchain,
        mempool,
        miner_address="",  # Will be set on mining start
        config=config
    )
    
    logger.info("API initialized and ready")
    
    return app


# ============================================================================
# EXPORT
# ============================================================================

__all__ = [
    "app",
    "initialize_api",
]
