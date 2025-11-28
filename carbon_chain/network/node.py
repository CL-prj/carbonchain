"""
CarbonChain - Network Node
============================
Nodo completo P2P con sync e propagazione.

Security Level: HIGH
Last Updated: 2025-11-27
Version: 1.0.0

Features:
- P2P networking
- Blockchain sync
- Transaction propagation
- Block relay
- Peer management
"""

from typing import Optional, List
import asyncio

# Internal imports
from carbon_chain.domain.blockchain import Blockchain
from carbon_chain.domain.mempool import Mempool
from carbon_chain.network.peer_manager import PeerManager
from carbon_chain.network.sync import BlockchainSynchronizer
from carbon_chain.network.message import Message, MessageType
from carbon_chain.config import ChainSettings
from carbon_chain.logging_setup import get_logger


# ============================================================================
# MODULE LOGGER
# ============================================================================

logger = get_logger("network.node")


# ============================================================================
# NETWORK NODE
# ============================================================================

class NetworkNode:
    """
    Nodo network completo.
    
    Integra:
    - Blockchain
    - Mempool
    - Peer manager
    - Synchronizer
    - Message handling
    
    Attributes:
        blockchain: Blockchain instance
        mempool: Mempool instance
        peer_manager: Peer manager
        synchronizer: Blockchain synchronizer
        config: Chain configuration
    
    Examples:
        >>> node = NetworkNode(blockchain, mempool, config)
        >>> await node.start()
        >>> await node.sync_blockchain()
    """
    
    def __init__(
        self,
        blockchain: Blockchain,
        mempool: Mempool,
        config: ChainSettings
    ):
        """
        Inizializza network node.
        
        Args:
            blockchain: Blockchain instance
            mempool: Mempool instance
            config: Chain configuration
        """
        self.blockchain = blockchain
        self.mempool = mempool
        self.config = config
        
        # Network components
        self.peer_manager = PeerManager(
            config=config,
            max_peers=config.p2p_max_peers,
            max_outbound=8
        )
        
        self.synchronizer = BlockchainSynchronizer(
            blockchain=blockchain,
            max_blocks_in_flight=100,
            batch_size=500
        )
        
        # Tasks
        self.tasks: List[asyncio.Task] = []
        
        # Running flag
        self.is_running = False
    
    # ========================================================================
    # LIFECYCLE
    # ========================================================================
    
    async def start(self):
        """Start network node"""
        if self.is_running:
            logger.warning("Node already running")
            return
        
        logger.info("Starting network node")
        
        # Start peer manager
        await self.peer_manager.start()
        
        # Connect to initial peers
        await self.peer_manager.connect_to_peers(count=8)
        
        # Start background tasks
        self.tasks.append(asyncio.create_task(self._message_handler_loop()))
        self.tasks.append(asyncio.create_task(self._sync_loop()))
        self.tasks.append(asyncio.create_task(self._relay_loop()))
        
        self.is_running = True
        
        logger.info("Network node started")
    
    async def stop(self):
        """Stop network node"""
        if not self.is_running:
            return
        
        logger.info("Stopping network node")
        
        self.is_running = False
        
        # Cancel tasks
        for task in self.tasks:
            task.cancel()
        
        await asyncio.gather(*self.tasks, return_exceptions=True)
        
        # Stop peer manager
        await self.peer_manager.stop()
        
        logger.info("Network node stopped")
    
    # ========================================================================
    # SYNCHRONIZATION
    # ========================================================================
    
    async def sync_blockchain(self) -> bool:
        """
        Sincronizza blockchain con network.
        
        Returns:
            bool: True se sync completo
        
        Examples:
            >>> success = await node.sync_blockchain()
        """
        peers = list(self.peer_manager.peers.values())
        
        if not peers:
            logger.warning("No peers available for sync")
            return False
        
        return await self.synchronizer.sync_with_peers(peers)
    
    async def _sync_loop(self):
        """Background sync loop"""
        while self.is_running:
            try:
                # Check se serve sync
                peers = list(self.peer_manager.peers.values())
                ready_peers = [p for p in peers if p.is_ready()]
                
                if ready_peers:
                    # Check se peer hanno height maggiore
                    max_peer_height = max(p.info.start_height for p in ready_peers)
                    our_height = self.blockchain.get_height()
                    
                    if max_peer_height > our_height + 10:
                        logger.info(
                            f"Starting sync: our height {our_height}, "
                            f"peer height {max_peer_height}"
                        )
                        await self.sync_blockchain()
                
                # Sleep between checks
                await asyncio.sleep(60)
            
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Sync loop error: {e}")
                await asyncio.sleep(60)
    
    # ========================================================================
    # MESSAGE HANDLING
    # ========================================================================
    
    async def _message_handler_loop(self):
        """Handle messaggi da tutti i peer"""
        while self.is_running:
            try:
                for peer in list(self.peer_manager.peers.values()):
                    if not peer.is_ready():
                        continue
                    
                    try:
                        # Non-blocking receive
                        msg = await asyncio.wait_for(
                            peer.receive_message(),
                            timeout=0.1
                        )
                        
                        await self._handle_message(msg, peer)
                    
                    except asyncio.TimeoutError:
                        continue
                    except Exception as e:
                        logger.debug(f"Error receiving from {peer}: {e}")
                
                await asyncio.sleep(0.1)
            
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Message handler error: {e}")
                await asyncio.sleep(1)
    
    async def _handle_message(self, message: Message, peer):
        """Handle singolo messaggio"""
        msg_type = message.message_type
        
        if msg_type == MessageType.PING:
            # Respond with PONG
            from carbon_chain.network.message import PingMessage
            ping = PingMessage.deserialize(message.payload)
            await peer.send_pong(ping.nonce)
        
        elif msg_type == MessageType.INV:
            # Inventory notification
            from carbon_chain.network.message import InvMessage
            inv = InvMessage.deserialize(message.payload)
            self.synchronizer.handle_inv_message(inv)
        
        elif msg_type == MessageType.BLOCKS:
            # Block data
            # TODO: Parse and handle block
            pass
        
        elif msg_type == MessageType.TX:
            # Transaction
            # TODO: Parse and add to mempool
            pass
    
    # ========================================================================
    # RELAY/PROPAGATION
    # ========================================================================
    
    async def _relay_loop(self):
        """Propaga nuovi blocchi e transazioni"""
        while self.is_running:
            try:
                # TODO: Implement relay logic
                await asyncio.sleep(10)
            
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Relay loop error: {e}")
                await asyncio.sleep(10)
    
    async def broadcast_transaction(self, tx):
        """
        Broadcast transazione a tutti i peer.
        
        Args:
            tx: Transaction da broadcast
        """
        # TODO: Implement transaction broadcast
        logger.info(f"Broadcasting transaction {tx.compute_txid()[:16]}...")
    
    async def broadcast_block(self, block):
        """
        Broadcast blocco a tutti i peer.
        
        Args:
            block: Block da broadcast
        """
        # TODO: Implement block broadcast
        logger.info(f"Broadcasting block at height {block.header.height}")
    
    # ========================================================================
    # UTILITIES
    # ========================================================================
    
    def get_network_info(self) -> dict:
        """Ottieni info network node"""
        return {
            "is_running": self.is_running,
            "peer_manager": self.peer_manager.get_statistics(),
            "sync_state": self.synchronizer.get_sync_state(),
            "blockchain_height": self.blockchain.get_height(),
            "mempool_size": self.mempool.size()
        }


# ============================================================================
# EXPORT
# ============================================================================

__all__ = [
    "NetworkNode",
]
