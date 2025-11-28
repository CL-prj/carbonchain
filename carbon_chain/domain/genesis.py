"""
CarbonChain - Genesis Block Creation
======================================
Creazione blocco genesis (blocco 0).

Security Level: CRITICAL
Last Updated: 2025-11-27
Version: 1.0.0

Genesis Block:
- Height: 0
- Previous hash: "0" * 64
- Timestamp: GENESIS_TIMESTAMP (constant)
- COINBASE con initial subsidy
- No PoW required (nonce = 0)

IMPORTANTE: Genesis block DEVE essere identico su tutti i nodi.
"""

from carbon_chain.domain.models import (
    Block,
    BlockHeader,
    Transaction,
    TxOutput,
)
from carbon_chain.constants import (
    TxType,
    GENESIS_TIMESTAMP,
    GENESIS_MESSAGE,
)
from carbon_chain.config import ChainSettings
from carbon_chain.logging_setup import get_logger


# ============================================================================
# MODULE LOGGER
# ============================================================================

logger = get_logger("genesis")


# ============================================================================
# GENESIS CREATION
# ============================================================================

def create_genesis_block(config: ChainSettings) -> Block:
    """
    Crea genesis block (blocco 0).
    
    Genesis block è il primo blocco della blockchain.
    Caratteristiche:
    - Height: 0
    - Previous hash: "0" * 64 (no blocco precedente)
    - Timestamp: GENESIS_TIMESTAMP (fisso)
    - COINBASE con initial subsidy
    - No PoW (nonce = 0)
    - Merkle root calcolato da COINBASE
    
    Args:
        config: Chain configuration
    
    Returns:
        Block: Genesis block
    
    Security:
        - Genesis DEVE essere identico su tutti i nodi
        - Hash genesis è checkpoint iniziale
        - Modifica genesis = fork network
    
    Examples:
        >>> from carbon_chain.config import get_settings
        >>> config = get_settings()
        >>> genesis = create_genesis_block(config)
        >>> genesis.header.height
        0
        >>> genesis.header.previous_hash
        '0000000000000000000000000000000000000000000000000000000000000000'
    """
    
    logger.info("Creating genesis block")
    
    # Genesis address (creator o burn address)
    if config.genesis_address:
        genesis_address = config.genesis_address
    else:
        # Default: burn address
        genesis_address = "1CarbonChainGenesisXXXXXXXXXXXXXXXX"
    
    # COINBASE transaction
    coinbase_tx = Transaction(
        tx_type=TxType.COINBASE,
        inputs=[],
        outputs=[
            TxOutput(
                amount=config.initial_subsidy,
                address=genesis_address
            )
        ],
        timestamp=GENESIS_TIMESTAMP,
        nonce=0,
        metadata={
            "genesis": True,
            "message": GENESIS_MESSAGE,
            "version": "1.0.0",
            "coin_name": "CarbonChain",
            "coin_ticker": "CCO2"
        }
    )
    
    # Create temporary block per merkle root calculation
    temp_block = Block(
        header=BlockHeader(
            version=1,
            previous_hash="0" * 64,
            merkle_root=b'\x00' * 32,  # Temporaneo
            timestamp=GENESIS_TIMESTAMP,
            difficulty=config.pow_difficulty_initial,
            nonce=0,
            height=0
        ),
        transactions=[coinbase_tx]
    )
    
    # Calcola merkle root
    merkle_root = temp_block.compute_merkle_root()
    
    # Header finale
    genesis_header = BlockHeader(
        version=1,
        previous_hash="0" * 64,
        merkle_root=merkle_root,
        timestamp=GENESIS_TIMESTAMP,
        difficulty=config.pow_difficulty_initial,
        nonce=0,  # Genesis non richiede PoW
        height=0
    )
    
    # Blocco genesis finale
    genesis_block = Block(
        header=genesis_header,
        transactions=[coinbase_tx]
    )
    
    genesis_hash = genesis_block.compute_block_hash()
    
    logger.info(
        "Genesis block created",
        extra_data={
            "hash": genesis_hash[:16] + "...",
            "subsidy": config.initial_subsidy,
            "address": genesis_address[:16] + "...",
            "timestamp": GENESIS_TIMESTAMP,
            "merkle_root": merkle_root.hex()[:16] + "..."
        }
    )
    
    return genesis_block


def verify_genesis_block(block: Block, config: ChainSettings) -> bool:
    """
    Verifica che blocco sia genesis valido.
    
    Checks:
    - Height = 0
    - Previous hash = "0" * 64
    - 1 transazione COINBASE
    - Subsidy corretto
    - Merkle root corretto
    
    Args:
        block: Block da verificare
        config: Chain configuration
    
    Returns:
        bool: True se genesis valido
    
    Examples:
        >>> genesis = create_genesis_block(config)
        >>> verify_genesis_block(genesis, config)
        True
    """
    try:
        # Check height
        if block.header.height != 0:
            logger.error(f"Genesis height != 0: {block.header.height}")
            return False
        
        # Check previous hash
        if block.header.previous_hash != "0" * 64:
            logger.error("Genesis previous_hash invalid")
            return False
        
        # Check 1 tx COINBASE
        if len(block.transactions) != 1:
            logger.error(f"Genesis must have 1 tx, got {len(block.transactions)}")
            return False
        
        tx = block.transactions[0]
        if not tx.is_coinbase():
            logger.error("Genesis first tx must be COINBASE")
            return False
        
        # Check subsidy
        if tx.total_output_amount() != config.initial_subsidy:
            logger.error(
                f"Genesis subsidy mismatch: expected {config.initial_subsidy}, "
                f"got {tx.total_output_amount()}"
            )
            return False
        
        # Check merkle root
        computed_merkle = block.compute_merkle_root()
        if computed_merkle != block.header.merkle_root:
            logger.error("Genesis merkle root mismatch")
            return False
        
        logger.info("Genesis block verified successfully")
        return True
    
    except Exception as e:
        logger.error(f"Genesis verification error: {e}")
        return False


def get_expected_genesis_hash(config: ChainSettings) -> str:
    """
    Calcola hash genesis atteso per configurazione.
    
    Usato per checkpoint validation.
    
    Args:
        config: Chain configuration
    
    Returns:
        str: Genesis block hash (64 hex)
    
    Examples:
        >>> config = get_settings()
        >>> expected = get_expected_genesis_hash(config)
        >>> len(expected)
        64
    """
    genesis = create_genesis_block(config)
    return genesis.compute_block_hash()


# ============================================================================
# EXPORT
# ============================================================================

__all__ = [
    "create_genesis_block",
    "verify_genesis_block",
    "get_expected_genesis_hash",
]
