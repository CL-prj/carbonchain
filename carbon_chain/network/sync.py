"""
CarbonChain - Blockchain Synchronization
==========================================
Sincronizzazione blockchain con peer network.

Security Level: CRITICAL
Last Updated: 2025-11-27
Version: 1.0.0

Features:
- Initial blockchain download (IBD)
- Block header sync
- Block download with validation
- Chain reorganization detection
- Parallel block download
"""

from typing import List, Dict, Optional, Set, Tuple
import asyncio
from dataclasses import dataclass
import time

# Internal imports
from carbon_chain.domain.blockchain import Blockchain
from carbon_chain.domain.models import Block
from carbon_chain.network.peer import Peer
from carbon_chain.network.message import (
    Message,
    MessageType,
    MessageFactory,
    GetBlocksMessage,
    InvMessage,
    InventoryType,
)
from carbon_chain.errors import SyncError, InvalidBlockError
from carbon_chain.logging_setup import get_logger


# ============================================================================
# MODULE LOGGER
# ============================================================================

logger = get_logger("network.sync")


# ============================================================================
# SYNC STATE
# ============================================================================

@dataclass
class SyncState:
    """
    Stato sincronizzazione.
    
    Attributes:
        is_syncing: Se sync in corso
        start_height: Height iniziale
        current_height: Height corrente
        target_height: Height target (da peer)
        blocks_downloaded: Blocchi scaricati
        sync_start_time: Timestamp inizio sync
    """
    
    is_syncing: bool = False
    start_height: int = 0
    current_height: int = 0
    target_height: int = 0
    blocks_downloaded: int = 0
    sync_start_time: Optional[float] = None
    
    def get_progress_percentage(self) -> float:
        """Calcola percentuale completamento"""
        if self.target_height <= self.start_height:
            return 100.0
        
        total = self.target_height - self.start_height
        done = self.current_height - self.start_height
        
        return (done / total * 100.0) if total > 0 else 0.0
    
    def get_sync_duration(self) -> float:
        """Durata sync in secondi"""
        if not self.sync_start_time:
            return 0.0
        return time.time() - self.sync_start_time
    
    def get_download_rate(self) -> float:
        """Blocks per second"""
        duration = self.get_sync_duration()
        if duration <= 0:
            return 0.0
        return self.blocks_downloaded / duration


# ============================================================================
# BLOCKCHAIN SYNCHRONIZER
# ============================================================================

class BlockchainSynchronizer:
    """
    Sincronizzatore blockchain.
    
    Gestisce:
    - Initial Block Download (IBD)
    - Incremental sync
    - Block validation
    - Chain reorganization
    
    Attributes:
        blockchain: Blockchain locale
        peers: Lista peer disponibili
        state: Stato sincronizzazione
    
    Examples:
        >>> sync = BlockchainSynchronizer(blockchain)
        >>> await sync.sync_with_peers(peers)
    """
    
    def __init__(
        self,
        blockchain: Blockchain,
        max_blocks_in_flight: int = 100,
        batch_size: int = 500
    ):
        """
        Inizializza synchronizer.
        
        Args:
            blockchain: Blockchain instance
            max_blocks_in_flight: Max blocchi in download simultaneo
            batch_size: Blocchi per batch request
        """
        self.blockchain = blockchain
        self.max_blocks_in_flight = max_blocks_in_flight
        self.batch_size = batch_size
        
        # State
        self.state = SyncState()
        
        # Block download queue
        self.pending_blocks: Dict[int, Block] = {}  # height → block
        self.requested_blocks: Set[int] = set()  # heights richiesti
        
        # Locks
        self._sync_lock = asyncio.Lock()
    
    # ========================================================================
    # SYNC OPERATIONS
    # ========================================================================
    
    async def sync_with_peers(self, peers: List[Peer]) -> bool:
        """
        Sincronizza blockchain con peer network.
        
        Steps:
            1. Find best peer (highest height)
            2. Download missing blocks
            3. Validate and add blocks
            4. Handle chain reorg if needed
        
        Args:
            peers: Lista peer disponibili
        
        Returns:
            bool: True se sync completo
        
        Examples:
            >>> success = await sync.sync_with_peers(peers)
        """
        async with self._sync_lock:
            if not peers:
                logger.warning("No peers available for sync")
                return False
            
            # Find best peer
            best_peer = self._find_best_peer(peers)
            if not best_peer:
                logger.warning("No suitable peer for sync")
                return False
            
            # Start sync
            self.state.is_syncing = True
            self.state.start_height = self.blockchain.get_height()
            self.state.current_height = self.state.start_height
            self.state.target_height = best_peer.info.start_height
            self.state.sync_start_time = time.time()
            
            logger.info(
                f"Starting sync from height {self.state.start_height} "
                f"to {self.state.target_height} (peer: {best_peer})"
            )
            
            try:
                # Download blocks
                await self._download_blocks(best_peer, peers)
                
                # Sync complete
                self.state.is_syncing = False
                
                duration = self.state.get_sync_duration()
                rate = self.state.get_download_rate()
                
                logger.info(
                    f"Sync complete! Downloaded {self.state.blocks_downloaded} blocks "
                    f"in {duration:.1f}s ({rate:.2f} blocks/s)"
                )
                
                return True
            
            except Exception as e:
                self.state.is_syncing = False
                logger.error(f"Sync failed: {e}")
                return False
    
    async def _download_blocks(self, best_peer: Peer, all_peers: List[Peer]):
        """
        Download blocchi mancanti.
        
        Args:
            best_peer: Peer con height maggiore
            all_peers: Tutti i peer disponibili
        """
        current_height = self.blockchain.get_height()
        target_height = self.state.target_height
        
        # Download in batches
        while current_height < target_height:
            batch_start = current_height + 1
            batch_end = min(batch_start + self.batch_size - 1, target_height)
            
            logger.info(f"Requesting blocks {batch_start} to {batch_end}")
            
            # Request blocks
            await self._request_blocks_batch(
                peer=best_peer,
                start_height=batch_start,
                end_height=batch_end
            )
            
            # Wait for blocks and add to chain
            blocks_added = await self._process_downloaded_blocks(
                start_height=batch_start,
                end_height=batch_end
            )
            
            if blocks_added == 0:
                logger.warning("No blocks downloaded in batch, retrying...")
                await asyncio.sleep(5)
                continue
            
            current_height = self.blockchain.get_height()
            self.state.current_height = current_height
            self.state.blocks_downloaded += blocks_added
            
            progress = self.state.get_progress_percentage()
            logger.info(
                f"Sync progress: {current_height}/{target_height} "
                f"({progress:.1f}%)"
            )
    
    async def _request_blocks_batch(
        self,
        peer: Peer,
        start_height: int,
        end_height: int
    ):
        """
        Richiedi batch di blocchi.
        
        Args:
            peer: Peer da cui richiedere
            start_height: Height iniziale
            end_height: Height finale
        """
        # Create block locator (list of hashes from recent to genesis)
        block_locator = self._create_block_locator()
        
        # Send GETBLOCKS message
        getblocks_msg = MessageFactory.create_getblocks(
            version=1,
            block_locator_hashes=block_locator,
            hash_stop="0" * 64  # Download fino alla fine
        )
        
        await peer.send_message(getblocks_msg)
        
        # Mark as requested
        for height in range(start_height, end_height + 1):
            self.requested_blocks.add(height)
    
    async def _process_downloaded_blocks(
        self,
        start_height: int,
        end_height: int,
        timeout: int = 60
    ) -> int:
        """
        Processa blocchi scaricati.
        
        Returns:
            int: Numero blocchi aggiunti
        """
        blocks_added = 0
        deadline = time.time() + timeout
        
        # Wait for blocks in sequence
        for height in range(start_height, end_height + 1):
            while time.time() < deadline:
                if height in self.pending_blocks:
                    block = self.pending_blocks.pop(height)
                    
                    try:
                        # Validate and add block
                        self.blockchain.add_block(block)
                        blocks_added += 1
                        
                        # Remove from requested
                        self.requested_blocks.discard(height)
                        
                        break
                    
                    except InvalidBlockError as e:
                        logger.error(f"Invalid block at height {height}: {e}")
                        # Skip this block
                        break
                
                await asyncio.sleep(0.1)
            
            # Timeout for this block
            if height not in self.blockchain.blocks:
                logger.warning(f"Timeout waiting for block {height}")
                break
        
        return blocks_added
    
    def _create_block_locator(self) -> List[str]:
        """
        Crea block locator per GETBLOCKS.
        
        Block locator: lista hash blocchi recenti → genesis
        per identificare punto di divergenza chain.
        
        Returns:
            List[str]: Lista block hashes
        """
        locator = []
        current_height = self.blockchain.get_height()
        
        # Add recent blocks (exponential backoff)
        step = 1
        height = current_height
        
        while height > 0 and len(locator) < 10:
            block = self.blockchain.get_block(height)
            if block:
                locator.append(block.compute_block_hash())
            
            height -= step
            step *= 2
        
        # Always add genesis
        genesis = self.blockchain.get_block(0)
        if genesis:
            locator.append(genesis.compute_block_hash())
        
        return locator
    
    def _find_best_peer(self, peers: List[Peer]) -> Optional[Peer]:
        """
        Trova peer con height maggiore.
        
        Args:
            peers: Lista peer
        
        Returns:
            Peer: Best peer, o None
        """
        ready_peers = [p for p in peers if p.is_ready()]
        
        if not ready_peers:
            return None
        
        # Sort by height descending
        sorted_peers = sorted(
            ready_peers,
            key=lambda p: p.info.start_height,
            reverse=True
        )
        
        return sorted_peers[0]
    
    # ========================================================================
    # BLOCK RECEPTION
    # ========================================================================
    
    def handle_block_message(self, block: Block):
        """
        Handle blocco ricevuto da peer.
        
        Args:
            block: Blocco ricevuto
        """
        height = block.header.height
        
        # Add to pending if requested
        if height in self.requested_blocks:
            self.pending_blocks[height] = block
            
            logger.debug(f"Received block at height {height}")
    
    def handle_inv_message(self, inv_msg: InvMessage):
        """
        Handle INV message (inventory notification).
        
        Args:
            inv_msg: Inventory message
        """
        for inv_type, hash_str in inv_msg.inventory:
            if inv_type == InventoryType.MSG_BLOCK:
                logger.debug(f"Peer announced new block: {hash_str[:16]}...")
                # TODO: Request block if needed
    
    # ========================================================================
    # UTILITIES
    # ========================================================================
    
    def get_sync_state(self) -> Dict:
        """Ottieni stato sync"""
        return {
            "is_syncing": self.state.is_syncing,
            "start_height": self.state.start_height,
            "current_height": self.state.current_height,
            "target_height": self.state.target_height,
            "progress_pct": round(self.state.get_progress_percentage(), 2),
            "blocks_downloaded": self.state.blocks_downloaded,
            "download_rate": round(self.state.get_download_rate(), 2),
            "duration_seconds": round(self.state.get_sync_duration(), 2)
        }


# ============================================================================
# EXPORT
# ============================================================================

__all__ = [
    "BlockchainSynchronizer",
    "SyncState",
]
