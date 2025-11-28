"""
CarbonChain - Mining Service
==============================
Servizio orchestrazione mining.

Security Level: MEDIUM
Last Updated: 2025-11-27
Version: 1.0.0

Features:
- Mining loop
- Transaction selection
- Block broadcasting
- Mining statistics
"""

from typing import Optional, List
import threading
import time

# Internal imports
from carbon_chain.domain.blockchain import Blockchain
from carbon_chain.domain.mempool import Mempool
from carbon_chain.domain.models import Block
from carbon_chain.logging_setup import get_logger
from carbon_chain.config import ChainSettings


# ============================================================================
# MODULE LOGGER
# ============================================================================

logger = get_logger("mining_service")


# ============================================================================
# MINING SERVICE
# ============================================================================

class MiningService:
    """
    Servizio orchestrazione mining.
    
    Gestisce:
    - Mining loop continuo
    - Transaction selection da mempool
    - Block broadcasting
    - Statistics
    
    Attributes:
        blockchain: Blockchain instance
        mempool: Mempool instance
        miner_address: Address per rewards
        config: Chain configuration
        is_mining: Flag mining attivo
    
    Examples:
        >>> service = MiningService(blockchain, mempool, "miner_addr", config)
        >>> service.start_mining()
        >>> # Mining in background thread
        >>> service.stop_mining()
    """
    
    def __init__(
        self,
        blockchain: Blockchain,
        mempool: Mempool,
        miner_address: str,
        config: ChainSettings
    ):
        self.blockchain = blockchain
        self.mempool = mempool
        self.miner_address = miner_address
        self.config = config
        
        # Mining state
        self.is_mining = False
        self._mining_thread: Optional[threading.Thread] = None
        
        # Statistics
        self.blocks_mined = 0
        self.total_hashes = 0
        self.start_time: Optional[float] = None
    
    # ========================================================================
    # MINING CONTROL
    # ========================================================================
    
    def start_mining(self, background: bool = True) -> None:
        """
        Avvia mining.
        
        Args:
            background: Se True, mining in thread separato
        
        Examples:
            >>> service.start_mining(background=True)
            >>> # Mining attivo in background
        """
        if self.is_mining:
            logger.warning("Mining already running")
            return
        
        self.is_mining = True
        self.start_time = time.time()
        
        logger.info(
            "Mining started",
            extra_data={
                "miner_address": self.miner_address[:16] + "...",
                "difficulty": self.blockchain.current_difficulty
            }
        )
        
        if background:
            self._mining_thread = threading.Thread(
                target=self._mining_loop,
                daemon=True
            )
            self._mining_thread.start()
        else:
            self._mining_loop()
    
    def stop_mining(self) -> None:
        """
        Ferma mining.
        
        Examples:
            >>> service.stop_mining()
        """
        if not self.is_mining:
            logger.warning("Mining not running")
            return
        
        self.is_mining = False
        
        if self._mining_thread:
            self._mining_thread.join(timeout=5)
        
        logger.info(
            "Mining stopped",
            extra_data={
                "blocks_mined": self.blocks_mined,
                "duration_seconds": self.get_mining_duration()
            }
        )
    
    def _mining_loop(self) -> None:
        """Mining loop principale"""
        while self.is_mining:
            try:
                # Mine singolo blocco
                block = self._mine_single_block()
                
                if block:
                    # Add to blockchain
                    self.blockchain.add_block(block)
                    
                    # Remove tx da mempool
                    self.mempool.remove_transactions_in_block(block)
                    
                    # Update stats
                    self.blocks_mined += 1
                    
                    logger.info(
                        f"✅ Block mined and added!",
                        extra_data={
                            "height": block.header.height,
                            "hash": block.compute_block_hash()[:16] + "...",
                            "tx_count": len(block.transactions),
                            "blocks_mined": self.blocks_mined
                        }
                    )
                
                # Breve pausa (per non saturare CPU)
                time.sleep(0.1)
            
            except Exception as e:
                logger.error(
                    f"Mining error: {e}",
                    extra_data={"error": str(e)}
                )
                time.sleep(1)
    
    def _mine_single_block(self) -> Optional[Block]:
        """
        Mina singolo blocco.
        
        Returns:
            Block: Blocco minato, o None se fallito
        """
        # Select transactions da mempool
        transactions = self.mempool.get_transactions_for_mining(
            max_count=1000,
            max_size=1_000_000  # 1 MB
        )
        
        # Mine block
        block = self.blockchain.mine_block(
            miner_address=self.miner_address,
            transactions=transactions,
            timeout_seconds=30 if self.config.dev_mode else None
        )
        
        return block
    
    # ========================================================================
    # STATISTICS
    # ========================================================================
    
    def get_mining_duration(self) -> float:
        """
        Ottieni durata mining in secondi.
        
        Returns:
            float: Secondi
        """
        if self.start_time is None:
            return 0.0
        
        return time.time() - self.start_time
    
    def get_mining_statistics(self) -> dict:
        """
        Ottieni statistiche mining.
        
        Returns:
            dict: {
                "is_mining": bool,
                "blocks_mined": int,
                "duration_seconds": float,
                "avg_block_time": float,
                "current_difficulty": int
            }
        """
        duration = self.get_mining_duration()
        avg_time = duration / self.blocks_mined if self.blocks_mined > 0 else 0
        
        return {
            "is_mining": self.is_mining,
            "blocks_mined": self.blocks_mined,
            "duration_seconds": round(duration, 2),
            "avg_block_time": round(avg_time, 2),
            "current_difficulty": self.blockchain.current_difficulty,
            "miner_address": self.miner_address[:16] + "..."
        }
    
    def get_miner_balance(self) -> int:
        """
        Ottieni balance miner.
        
        Returns:
            int: Balance in Satoshi
        """
        return self.blockchain.get_balance(self.miner_address)


# ============================================================================
# EXPORT
# ============================================================================

__all__ = [
    "MiningService",
]
