"""
CarbonChain - Proof of Work
=============================
Sistema Proof of Work per mining blocchi.

Security Level: CRITICAL
Last Updated: 2025-11-27
Version: 1.0.0

Algorithm:
- Hash: Scrypt (ASIC-resistant, memory-hard)
- Difficulty: Leading zero bytes
- Target: Hash < 2^(256 - difficulty*8)

Performance:
- CPU-friendly (decentralizzazione)
- Memory-hard (no GPU/ASIC advantage)
"""

from typing import Optional, Tuple
import time

# Internal imports
from carbon_chain.domain.models import BlockHeader
from carbon_chain.domain.crypto_core import (
    compute_pow_hash_scrypt,
    check_pow_difficulty,
)
from carbon_chain.errors import (
    PoWError,
    InvalidPoWError,
)
from carbon_chain.logging_setup import get_logger, PerformanceLogger


# ============================================================================
# MODULE LOGGER
# ============================================================================

logger = get_logger("pow")


# ============================================================================
# DIFFICULTY CALCULATION
# ============================================================================

def calculate_next_difficulty(
    previous_difficulty: int,
    actual_time: int,
    target_time: int,
    min_difficulty: int = 1,
    max_difficulty: int = 32,
    max_adjustment_factor: float = 4.0
) -> int:
    """
    Calcola difficulty per prossimo blocco (difficulty adjustment).
    
    Algorithm:
        - Se blocchi troppo veloci → aumenta difficulty
        - Se blocchi troppo lenti → diminuisci difficulty
        - Max adjustment: 4x in una volta
    
    Args:
        previous_difficulty: Difficulty corrente
        actual_time: Tempo effettivo per N blocchi (secondi)
        target_time: Tempo target per N blocchi (secondi)
        min_difficulty: Difficulty minima
        max_difficulty: Difficulty massima
        max_adjustment_factor: Max fattore adjustment
    
    Returns:
        int: Nuova difficulty (1-32)
    
    Examples:
        >>> # Blocchi troppo veloci → aumenta difficulty
        >>> calculate_next_difficulty(4, 7200, 14400)  # Metà tempo
        5
        
        >>> # Blocchi troppo lenti → diminuisci difficulty
        >>> calculate_next_difficulty(4, 28800, 14400)  # Doppio tempo
        3
    """
    if actual_time <= 0 or target_time <= 0:
        logger.warning(
            f"Invalid times for difficulty calculation",
            extra_data={"actual": actual_time, "target": target_time}
        )
        return previous_difficulty
    
    # Calcola ratio tempo effettivo / tempo target
    ratio = actual_time / target_time
    
    # Limita adjustment (no cambio drastico)
    ratio = max(1.0 / max_adjustment_factor, min(ratio, max_adjustment_factor))
    
    # Calcola nuova difficulty
    # Se ratio > 1 (troppo lento) → diminuisci difficulty
    # Se ratio < 1 (troppo veloce) → aumenta difficulty
    if ratio > 1:
        # Troppo lento: diminuisci difficulty (più facile)
        new_difficulty = max(min_difficulty, previous_difficulty - 1)
    elif ratio < 1:
        # Troppo veloce: aumenta difficulty (più difficile)
        new_difficulty = min(max_difficulty, previous_difficulty + 1)
    else:
        # Perfetto: mantieni
        new_difficulty = previous_difficulty
    
    logger.info(
        f"Difficulty adjusted",
        extra_data={
            "previous": previous_difficulty,
            "new": new_difficulty,
            "ratio": round(ratio, 2),
            "actual_time": actual_time,
            "target_time": target_time
        }
    )
    
    return new_difficulty


# ============================================================================
# POW VERIFICATION
# ============================================================================

def verify_block_pow(block_header: BlockHeader) -> bool:
    """
    Verifica che block header soddisfi PoW.
    
    Checks:
    1. Calcola hash header
    2. Verifica hash < difficulty target
    
    Args:
        block_header: Header da verificare
    
    Returns:
        bool: True se PoW valido
    
    Security:
        - Verificazione veloce (single hash)
        - No re-mining necessario
    
    Examples:
        >>> # Header con PoW valido
        >>> header = BlockHeader(
        ...     version=1,
        ...     previous_hash="0"*64,
        ...     merkle_root=b'\\x01'*32,
        ...     timestamp=1700000000,
        ...     difficulty=1,
        ...     nonce=12345,
        ...     height=0
        ... )
        >>> # verify_block_pow(header)  # True se hash valido
    """
    try:
        # Serializza header
        header_bytes = _serialize_header_for_pow(block_header)
        
        # Calcola hash con nonce
        pow_hash = compute_pow_hash_scrypt(header_bytes, block_header.nonce)
        
        # Check difficulty
        is_valid = check_pow_difficulty(pow_hash, block_header.difficulty)
        
        if is_valid:
            logger.debug(
                f"PoW verification passed",
                extra_data={
                    "height": block_header.height,
                    "difficulty": block_header.difficulty,
                    "nonce": block_header.nonce,
                    "hash": pow_hash.hex()[:16] + "..."
                }
            )
        else:
            logger.warning(
                f"PoW verification failed",
                extra_data={
                    "height": block_header.height,
                    "difficulty": block_header.difficulty,
                    "hash": pow_hash.hex()[:16] + "..."
                }
            )
        
        return is_valid
    
    except Exception as e:
        logger.error(
            f"PoW verification error",
            extra_data={"error": str(e)}
        )
        return False


# ============================================================================
# MINING
# ============================================================================

def mine_block_header(
    header: BlockHeader,
    max_nonce: int = 2**32,
    timeout_seconds: Optional[int] = None
) -> Optional[BlockHeader]:
    """
    Mina block header (trova nonce valido).
    
    Algorithm:
        1. Serializza header
        2. Loop nonce da 0 a max_nonce
        3. Per ogni nonce: calcola hash, check difficulty
        4. Se valido: return header con nonce
        5. Se timeout: return None
    
    Args:
        header: Header da minare (con nonce=0)
        max_nonce: Max tentativi (default 2^32)
        timeout_seconds: Timeout (None = no timeout)
    
    Returns:
        BlockHeader: Header con nonce valido, o None se non trovato
    
    Performance:
        - Scrypt: ~1000-10000 hash/sec su CPU moderna
        - Difficulty 4: ~16M tentativi in media
        - Time: ~30 min - 3 ore (varia con CPU)
    
    Examples:
        >>> header = BlockHeader(
        ...     version=1,
        ...     previous_hash="0"*64,
        ...     merkle_root=b'\\x01'*32,
        ...     timestamp=int(time.time()),
        ...     difficulty=1,  # Facile per test
        ...     nonce=0,
        ...     height=0
        ... )
        >>> mined = mine_block_header(header, max_nonce=10000)
        >>> if mined:
        ...     print(f"Found nonce: {mined.nonce}")
    """
    start_time = time.time()
    
    # Serializza header base (senza nonce)
    header_bytes = _serialize_header_for_pow(header)
    
    logger.info(
        f"Mining started",
        extra_data={
            "height": header.height,
            "difficulty": header.difficulty,
            "max_nonce": max_nonce,
            "timeout": timeout_seconds
        }
    )
    
    # Loop nonce
    for nonce in range(max_nonce):
        # Check timeout
        if timeout_seconds:
            elapsed = time.time() - start_time
            if elapsed > timeout_seconds:
                logger.warning(
                    f"Mining timeout",
                    extra_data={
                        "nonces_tried": nonce,
                        "elapsed": round(elapsed, 2)
                    }
                )
                return None
        
        # Calcola hash
        pow_hash = compute_pow_hash_scrypt(header_bytes, nonce)
        
        # Check difficulty
        if check_pow_difficulty(pow_hash, header.difficulty):
            # ✅ FOUND VALID NONCE!
            elapsed = time.time() - start_time
            hashrate = nonce / elapsed if elapsed > 0 else 0
            
            logger.info(
                f"✅ Mining SUCCESS!",
                extra_data={
                    "height": header.height,
                    "nonce": nonce,
                    "difficulty": header.difficulty,
                    "hash": pow_hash.hex()[:16] + "...",
                    "nonces_tried": nonce,
                    "time_seconds": round(elapsed, 2),
                    "hashrate": round(hashrate, 2)
                }
            )
            
            # Create new header with valid nonce
            from dataclasses import replace
            return replace(header, nonce=nonce)
        
        # Log progress ogni 1000 nonce
        if nonce > 0 and nonce % 1000 == 0:
            elapsed = time.time() - start_time
            hashrate = nonce / elapsed if elapsed > 0 else 0
            
            logger.debug(
                f"Mining progress",
                extra_data={
                    "nonces_tried": nonce,
                    "hashrate": round(hashrate, 2),
                    "elapsed": round(elapsed, 2)
                }
            )
    
    # Max nonce raggiunto senza successo
    elapsed = time.time() - start_time
    logger.warning(
        f"Mining failed: max nonce reached",
        extra_data={
            "max_nonce": max_nonce,
            "time_seconds": round(elapsed, 2)
        }
    )
    
    return None


def estimate_mining_time(
    difficulty: int,
    hashrate: float
) -> float:
    """
    Stima tempo mining in secondi.
    
    Args:
        difficulty: Difficulty target (1-32)
        hashrate: Hash rate (hash/sec)
    
    Returns:
        float: Tempo stimato in secondi
    
    Formula:
        time = 2^(difficulty * 8) / hashrate
    
    Examples:
        >>> # Difficulty 4, hashrate 1000 hash/sec
        >>> estimate_mining_time(4, 1000)
        4294967.296  # ~50 giorni
        
        >>> # Difficulty 1, hashrate 1000 hash/sec
        >>> estimate_mining_time(1, 1000)
        256.0  # ~4 minuti
    """
    if hashrate <= 0:
        return float('inf')
    
    # Numero hash da provare in media (2^(difficulty*8))
    expected_hashes = 2 ** (difficulty * 8)
    
    # Tempo = hashes / hashrate
    time_seconds = expected_hashes / hashrate
    
    return time_seconds


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def _serialize_header_for_pow(header: BlockHeader) -> bytes:
    """
    Serializza header per PoW (senza nonce).
    
    Args:
        header: BlockHeader
    
    Returns:
        bytes: Serialized header
    """
    return (
        header.version.to_bytes(4, byteorder='big') +
        bytes.fromhex(header.previous_hash) +
        header.merkle_root +
        header.timestamp.to_bytes(8, byteorder='big') +
        header.difficulty.to_bytes(1, byteorder='big') +
        header.height.to_bytes(8, byteorder='big')
    )


def get_block_subsidy(height: int, halving_interval: int, initial_subsidy: int) -> int:
    """
    Calcola block subsidy per altezza (con halving).
    
    Args:
        height: Block height
        halving_interval: Blocchi tra halving
        initial_subsidy: Subsidy iniziale
    
    Returns:
        int: Subsidy in Satoshi
    
    Examples:
        >>> # Bitcoin-like: 50 coin iniziali, halving ogni 210k blocchi
        >>> get_block_subsidy(0, 210000, 5000000000)
        5000000000
        >>> get_block_subsidy(210000, 210000, 5000000000)
        2500000000
    """
    halvings = height // halving_interval
    
    # Max 64 halving (dopo subsidy = 0)
    if halvings >= 64:
        return 0
    
    # Subsidy = initial / (2^halvings)
    subsidy = initial_subsidy >> halvings
    
    return subsidy


# ============================================================================
# EXPORT
# ============================================================================

__all__ = [
    # Difficulty
    "calculate_next_difficulty",
    
    # Verification
    "verify_block_pow",
    
    # Mining
    "mine_block_header",
    "estimate_mining_time",
    
    # Helpers
    "get_block_subsidy",
]
