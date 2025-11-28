"""
CarbonChain - Domain Package
==============================
Core domain logic della blockchain.
"""

# Models
from carbon_chain.domain.models import (
    Transaction,
    TxInput,
    TxOutput,
    Block,
    BlockHeader,
    UTXOKey,
)

# UTXO
from carbon_chain.domain.utxo import UTXOSet

# Validation
from carbon_chain.domain.validation import (
    TransactionValidator,
    BlockValidator,
    CertificateValidator,
)

# Blockchain
from carbon_chain.domain.blockchain import Blockchain

# Genesis
from carbon_chain.domain.genesis import (
    create_genesis_block,
    verify_genesis_block,
    get_expected_genesis_hash,
)

# PoW - ✅ CORRETTO: Nomi funzioni che ESISTONO
from carbon_chain.domain.pow import (
    verify_block_pow,
    mine_block_header,  # ✅ Nome corretto (non mine_block_pow)
    get_block_subsidy,
    calculate_next_difficulty,
    estimate_mining_time,
)

# Mempool
from carbon_chain.domain.mempool import Mempool

# Crypto
from carbon_chain.domain.crypto_core import get_crypto_provider

# Addressing
from carbon_chain.domain.addressing import (
    public_key_to_address,
    validate_address,
)

# Keypairs
from carbon_chain.domain.keypairs import KeyPair


__all__ = [
    # Models
    "Transaction",
    "TxInput",
    "TxOutput",
    "Block",
    "BlockHeader",
    "UTXOKey",
    
    # UTXO
    "UTXOSet",
    
    # Validation
    "TransactionValidator",
    "BlockValidator",
    "CertificateValidator",
    
    # Blockchain
    "Blockchain",
    
    # Genesis
    "create_genesis_block",
    "verify_genesis_block",
    "get_expected_genesis_hash",
    
    # PoW 
    "verify_block_pow",
    "mine_block_header", 
    "get_block_subsidy",
    "calculate_next_difficulty",
    "estimate_mining_time",
    
    # Mempool
    "Mempool",
    
    # Crypto
    "get_crypto_provider",
    
    # Addressing
    "public_key_to_address",
    "validate_address",
    
    # Keypairs
    "KeyPair",
]
