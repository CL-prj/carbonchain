"""
CarbonChain - Peer Manager
============================
Gestione pool di peer connections.

Security Level: HIGH
Last Updated: 2025-11-27
Version: 1.0.0

Features:
- Multiple peer connections
- Connection pool management
- Peer discovery
- Automatic reconnection
- Load balancing
"""

from typing import List, Dict, Optional, Set
import asyncio
from pathlib import Path
import json
import time

# Internal imports
from carbon_chain.network.peer import Peer, PeerInfo, PeerState
from carbon_chain.network.message import Message, MessageType
from carbon_chain.errors import NetworkError
from carbon_chain.logging_setup import get_logger
from carbon_chain.config import ChainSettings


# ============================================================================
# MODULE LOGGER
# ============================================================================

logger = get_logger("network.peer_manager")


# ============================================================================
# PEER MANAGER
# ============================================================================

class PeerManager:
    """
    Gestione pool peer connections.
    
    Features:
    - Maintain N active connections
    - Automatic peer discovery
    - Connection retry logic
    - Peer scoring/banning
    - Load balancing
    
    Attributes:
        config: Chain configuration
        peers: Active peer connections
        known_peers: Database peer conosciuti
        max_peers: Max peer simultanei
    
    Examples:
        >>> manager = PeerManager(config)
        >>> await manager.start()
        >>> await manager.connect_to_peers()
    """
    
    def __init__(
        self,
        config: ChainSettings,
        max_peers: int = 128,
        max_outbound: int = 8
    ):
        """
        Inizializza peer manager.
        
        Args:
            config: Chain configuration
            max_peers: Max peer connections
            max_outbound: Max outbound connections
        """
        self.config = config
        self.max_peers = max_peers
        self.max_outbound = max_outbound
        
        # Active peers
        self.peers: Dict[str, Peer] = {}
        
        # Known peers database
        self.known_peers: Dict[str, PeerInfo] = {}
        self.peers_file = config.data_dir / "peers.json"
        
        # Banned peers
        self.banned_peers: Set[str] = set()
        
        # Connection queue
        self.pending_connections: asyncio.Queue = asyncio.Queue()
        
        # Tasks
        self.tasks: List[asyncio.Task] = []
        
        # Load known peers
        self._load_known_peers()
    
    # ========================================================================
    # LIFECYCLE
    # ========================================================================
    
    async def start(self):
        """Start peer manager"""
        logger.info("Starting peer manager")
        
        # Start background tasks
        self.tasks.append(asyncio.create_task(self._connection_manager()))
        self.tasks.append(asyncio.create_task(self._keep_alive_loop()))
        self.tasks.append(asyncio.create_task(self._peer_maintenance_loop()))
        
        logger.info("Peer manager started")
    
    async def stop(self):
        """Stop peer manager"""
        logger.info("Stopping peer manager")
        
        # Cancel tasks
        for task in self.tasks:
            task.cancel()
        
        await asyncio.gather(*self.tasks, return_exceptions=True)
        
        # Disconnect all peers
        disconnect_tasks = [peer.disconnect() for peer in self.peers.values()]
        await asyncio.gather(*disconnect_tasks, return_exceptions=True)
        
        # Save known peers
        self._save_known_peers()
        
        logger.info("Peer manager stopped")
    
    # ========================================================================
    # PEER CONNECTIONS
    # ========================================================================
    
    async def connect_to_peer(self, address: str, port: int) -> Optional[Peer]:
        """
        Connetti a peer specifico.
        
        Args:
            address: Peer address
            port: Peer port
        
        Returns:
            Peer: Peer connesso, o None se fallito
        """
        peer_id = f"{address}:{port}"
        
        # Check if already connected
        if peer_id in self.peers:
            logger.debug(f"Already connected to {peer_id}")
            return self.peers[peer_id]
        
        # Check if banned
        if peer_id in self.banned_peers:
            logger.debug(f"Peer {peer_id} is banned")
            return None
        
        # Check max peers
        if len(self.peers) >= self.max_peers:
            logger.debug(f"Max peers reached ({self.max_peers})")
            return None
        
        try:
            # Create peer
            peer = Peer(
                address=address,
                port=port,
                user_agent=f"CarbonChain/{self.config.software_version}",
                start_height=0,  # TODO: Get from blockchain
                timeout=30
            )
            
            # Set callbacks
            peer.on_message = self._handle_peer_message
            peer.on_disconnect = self._handle_peer_disconnect
            
            # Connect
            await peer.connect()
            
            # Add to active peers
            self.peers[peer_id] = peer
            
            # Add to known peers
            self.known_peers[peer_id] = peer.info
            
            logger.info(f"Connected to peer {peer_id}")
            
            return peer
        
        except Exception as e:
            logger.error(f"Failed to connect to {peer_id}: {e}")
            return None
    
    async def connect_to_peers(self, count: int = 8):
        """
        Connetti a N peer da lista known peers.
        
        Args:
            count: Numero peer da connettere
        """
        connected = 0
        
        for peer_id, peer_info in self.known_peers.items():
            if connected >= count:
                break
            
            if peer_id not in self.peers:
                peer = await self.connect_to_peer(peer_info.address, peer_info.port)
                if peer:
                    connected += 1
        
        logger.info(f"Connected to {connected} peers")
    
    def disconnect_peer(self, peer_id: str):
        """Disconnetti peer specifico"""
        if peer_id in self.peers:
            peer = self.peers[peer_id]
            asyncio.create_task(peer.disconnect())
    
    # ========================================================================
    # MESSAGE HANDLING
    # ========================================================================
    
    def _handle_peer_message(self, message: Message):
        """Handle messaggio da peer"""
        logger.debug(f"Received {message.message_type.name} message")
        
        # Handle specific message types
        if message.message_type == MessageType.PING:
            # Auto-respond to PING
            # (handled in peer loop)
            pass
        
        elif message.message_type == MessageType.INV:
            # Inventory notification
            # TODO: Handle new blocks/transactions
            pass
        
        # TODO: Handle other message types
    
    def _handle_peer_disconnect(self, peer: Peer):
        """Handle peer disconnect"""
        peer_id = str(peer)
        
        if peer_id in self.peers:
            del self.peers[peer_id]
            logger.info(f"Peer {peer_id} disconnected")
    
    # ========================================================================
    # BACKGROUND TASKS
    # ========================================================================
    
    async def _connection_manager(self):
        """Mantieni N connessioni attive"""
        while True:
            try:
                # Check se sotto target
                if len(self.peers) < self.max_outbound:
                    await self.connect_to_peers(self.max_outbound - len(self.peers))
                
                await asyncio.sleep(30)
            
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Connection manager error: {e}")
                await asyncio.sleep(60)
    
    async def _keep_alive_loop(self):
        """Invia PING periodico a tutti i peer"""
        while True:
            try:
                for peer in list(self.peers.values()):
                    if peer.is_ready():
                        await peer.send_ping()
                
                await asyncio.sleep(60)
            
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Keep-alive error: {e}")
                await asyncio.sleep(60)
    
    async def _peer_maintenance_loop(self):
        """Manutenzione peer (cleanup, scoring, etc.)"""
        while True:
            try:
                # Remove stale peers
                current_time = time.time()
                stale_peers = []
                
                for peer_id, peer_info in self.known_peers.items():
                    age = current_time - peer_info.last_seen
                    if age > 86400 * 7:  # 7 days
                        stale_peers.append(peer_id)
                
                for peer_id in stale_peers:
                    del self.known_peers[peer_id]
                
                if stale_peers:
                    logger.info(f"Removed {len(stale_peers)} stale peers")
                
                # Save known peers
                self._save_known_peers()
                
                await asyncio.sleep(3600)  # 1 hour
            
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Peer maintenance error: {e}")
                await asyncio.sleep(3600)
    
    # ========================================================================
    # PEER DATABASE
    # ========================================================================
    
    def _load_known_peers(self):
        """Carica known peers da file"""
        if not self.peers_file.exists():
            # Load seed peers
            self._load_seed_peers()
            return
        
        try:
            data = json.loads(self.peers_file.read_text())
            self.known_peers = {
                peer_id: PeerInfo.from_dict(peer_data)
                for peer_id, peer_data in data.items()
            }
            logger.info(f"Loaded {len(self.known_peers)} known peers")
        
        except Exception as e:
            logger.error(f"Failed to load peers: {e}")
            self._load_seed_peers()
    
    def _save_known_peers(self):
        """Salva known peers su file"""
        try:
            data = {
                peer_id: peer_info.to_dict()
                for peer_id, peer_info in self.known_peers.items()
            }
            
            self.peers_file.parent.mkdir(parents=True, exist_ok=True)
            self.peers_file.write_text(json.dumps(data, indent=2))
            
            logger.debug(f"Saved {len(self.known_peers)} known peers")
        
        except Exception as e:
            logger.error(f"Failed to save peers: {e}")
    
    def _load_seed_peers(self):
        """Carica seed peers (bootstrap)"""
        # TODO: Add real seed nodes
        seed_peers = [
            # ("seed1.carbonchain.eco", 9333),
            # ("seed2.carbonchain.eco", 9333),
        ]
        
        for address, port in seed_peers:
            peer_id = f"{address}:{port}"
            self.known_peers[peer_id] = PeerInfo(address=address, port=port)
        
        logger.info(f"Loaded {len(seed_peers)} seed peers")
    
    # ========================================================================
    # UTILITIES
    # ========================================================================
    
    def get_peer_count(self) -> int:
        """Numero peer connessi"""
        return len(self.peers)
    
    def get_ready_peer_count(self) -> int:
        """Numero peer ready"""
        return sum(1 for peer in self.peers.values() if peer.is_ready())
    
    def get_statistics(self) -> Dict:
        """Statistiche peer manager"""
        return {
            "total_peers": len(self.peers),
            "ready_peers": self.get_ready_peer_count(),
            "known_peers": len(self.known_peers),
            "banned_peers": len(self.banned_peers),
            "max_peers": self.max_peers
        }


# ============================================================================
# EXPORT
# ============================================================================

__all__ = [
    "PeerManager",
]
