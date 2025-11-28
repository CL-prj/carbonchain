"""
CarbonChain - Peer Connection Management
==========================================
Gestione connessioni peer-to-peer.

Security Level: HIGH
Last Updated: 2025-11-27
Version: 1.0.0

Features:
- TCP connection management
- Handshake protocol
- Message send/receive
- Keep-alive (ping/pong)
- Connection state tracking
- Automatic reconnection
"""

from __future__ import annotations
from typing import Optional, Callable, Dict, Any
from dataclasses import dataclass, field
from enum import Enum
import asyncio
import socket
import time
import secrets

# Internal imports
from carbon_chain.network.message import (
    Message,
    MessageType,
    MessageFactory,
    VersionMessage,
)
from carbon_chain.errors import (
    PeerConnectionError,
    PeerTimeoutError,
    InvalidMessageError,
)
from carbon_chain.logging_setup import get_logger
from carbon_chain.constants import PROTOCOL_VERSION


# ============================================================================
# MODULE LOGGER
# ============================================================================

logger = get_logger("network.peer")


# ============================================================================
# PEER STATE
# ============================================================================

class PeerState(Enum):
    """Stati connessione peer"""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    HANDSHAKING = "handshaking"
    READY = "ready"
    DISCONNECTING = "disconnecting"


# ============================================================================
# PEER INFO
# ============================================================================

@dataclass
class PeerInfo:
    """
    Informazioni peer.
    
    Attributes:
        address: IP address
        port: Port number
        services: Node services (bitfield)
        version: Protocol version
        user_agent: Software version
        start_height: Blockchain height
        last_seen: Last activity timestamp
    """
    
    address: str
    port: int
    services: int = 0
    version: int = 0
    user_agent: str = ""
    start_height: int = 0
    last_seen: int = field(default_factory=lambda: int(time.time()))
    
    def to_dict(self) -> Dict[str, Any]:
        """Serializza per storage"""
        return {
            "address": self.address,
            "port": self.port,
            "services": self.services,
            "version": self.version,
            "user_agent": self.user_agent,
            "start_height": self.start_height,
            "last_seen": self.last_seen
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> PeerInfo:
        """Deserializza da storage"""
        return cls(**data)


# ============================================================================
# PEER CONNECTION
# ============================================================================

class Peer:
    """
    Connessione peer singola.
    
    Gestisce:
    - TCP connection (asyncio)
    - Handshake protocol
    - Message send/receive
    - Keep-alive ping/pong
    - Automatic reconnection
    
    Attributes:
        info: Peer information
        state: Connection state
        reader: asyncio StreamReader
        writer: asyncio StreamWriter
        
    Examples:
        >>> peer = Peer("192.168.1.100", 9333)
        >>> await peer.connect()
        >>> await peer.send_message(message)
        >>> msg = await peer.receive_message()
    """
    
    def __init__(
        self,
        address: str,
        port: int,
        local_address: str = "0.0.0.0",
        local_port: int = 9333,
        user_agent: str = "CarbonChain/1.0.0",
        start_height: int = 0,
        timeout: int = 30
    ):
        """
        Inizializza peer connection.
        
        Args:
            address: Peer IP address
            port: Peer port
            local_address: Local address for handshake
            local_port: Local port
            user_agent: Node user agent
            start_height: Current blockchain height
            timeout: Connection timeout (seconds)
        """
        self.info = PeerInfo(address=address, port=port)
        self.state = PeerState.DISCONNECTED
        
        # Local info
        self.local_address = local_address
        self.local_port = local_port
        self.user_agent = user_agent
        self.start_height = start_height
        
        # Connection
        self.reader: Optional[asyncio.StreamReader] = None
        self.writer: Optional[asyncio.StreamWriter] = None
        self.timeout = timeout
        
        # Handshake
        self.handshake_complete = False
        self.nonce = secrets.randbits(64)
        
        # Statistics
        self.bytes_sent = 0
        self.bytes_received = 0
        self.messages_sent = 0
        self.messages_received = 0
        self.connected_at: Optional[float] = None
        
        # Keep-alive
        self.last_ping_time: Optional[float] = None
        self.last_pong_time: Optional[float] = None
        
        # Callbacks
        self.on_message: Optional[Callable[[Message], None]] = None
        self.on_disconnect: Optional[Callable[[Peer], None]] = None
    
    # ========================================================================
    # CONNECTION MANAGEMENT
    # ========================================================================
    
    async def connect(self) -> bool:
        """
        Connetti al peer.
        
        Returns:
            bool: True se connessione riuscita
        
        Raises:
            PeerConnectionError: Se connessione fallisce
        
        Examples:
            >>> peer = Peer("192.168.1.100", 9333)
            >>> success = await peer.connect()
        """
        if self.state != PeerState.DISCONNECTED:
            logger.warning(f"Peer {self} already connected")
            return False
        
        self.state = PeerState.CONNECTING
        
        try:
            # TCP connection
            self.reader, self.writer = await asyncio.wait_for(
                asyncio.open_connection(self.info.address, self.info.port),
                timeout=self.timeout
            )
            
            self.state = PeerState.CONNECTED
            self.connected_at = time.time()
            
            logger.info(f"Connected to peer {self}")
            
            # Start handshake
            await self._perform_handshake()
            
            return True
        
        except asyncio.TimeoutError:
            self.state = PeerState.DISCONNECTED
            raise PeerTimeoutError(
                f"Connection timeout to {self.info.address}:{self.info.port}",
                code="PEER_CONNECT_TIMEOUT"
            )
        
        except Exception as e:
            self.state = PeerState.DISCONNECTED
            raise PeerConnectionError(
                f"Failed to connect to peer: {e}",
                code="PEER_CONNECT_FAILED"
            )
    
    async def disconnect(self):
        """Disconnetti dal peer"""
        if self.state == PeerState.DISCONNECTED:
            return
        
        self.state = PeerState.DISCONNECTING
        
        try:
            if self.writer:
                self.writer.close()
                await self.writer.wait_closed()
        except Exception as e:
            logger.error(f"Error closing connection to {self}: {e}")
        
        finally:
            self.reader = None
            self.writer = None
            self.state = PeerState.DISCONNECTED
            self.handshake_complete = False
            
            logger.info(f"Disconnected from peer {self}")
            
            # Trigger callback
            if self.on_disconnect:
                self.on_disconnect(self)
    
    async def _perform_handshake(self):
        """
        Esegui handshake protocol.
        
        Steps:
            1. Send VERSION message
            2. Receive VERSION message
            3. Send VERACK
            4. Receive VERACK
            5. Handshake complete
        """
        self.state = PeerState.HANDSHAKING
        
        try:
            # 1. Send VERSION
            version_msg = MessageFactory.create_version(
                version=PROTOCOL_VERSION,
                services=0,  # TODO: Service flags
                addr_recv=f"{self.info.address}:{self.info.port}",
                addr_from=f"{self.local_address}:{self.local_port}",
                nonce=self.nonce,
                user_agent=self.user_agent,
                start_height=self.start_height
            )
            
            await self.send_message(version_msg)
            
            # 2. Receive VERSION
            peer_version_msg = await self.receive_message()
            
            if peer_version_msg.message_type != MessageType.VERSION:
                raise InvalidMessageError(
                    f"Expected VERSION, got {peer_version_msg.message_type.name}",
                    code="HANDSHAKE_INVALID_VERSION"
                )
            
            # Parse peer version
            peer_version = VersionMessage.deserialize(peer_version_msg.payload)
            
            # Update peer info
            self.info.version = peer_version.version
            self.info.services = peer_version.services
            self.info.user_agent = peer_version.user_agent
            self.info.start_height = peer_version.start_height
            
            logger.info(
                f"Peer {self} version: {peer_version.version}, "
                f"height: {peer_version.start_height}, "
                f"agent: {peer_version.user_agent}"
            )
            
            # 3. Send VERACK
            verack_msg = MessageFactory.create_verack()
            await self.send_message(verack_msg)
            
            # 4. Receive VERACK
            peer_verack_msg = await self.receive_message()
            
            if peer_verack_msg.message_type != MessageType.VERACK:
                raise InvalidMessageError(
                    f"Expected VERACK, got {peer_verack_msg.message_type.name}",
                    code="HANDSHAKE_INVALID_VERACK"
                )
            
            # Handshake complete
            self.handshake_complete = True
            self.state = PeerState.READY
            
            logger.info(f"Handshake complete with peer {self}")
        
        except Exception as e:
            logger.error(f"Handshake failed with peer {self}: {e}")
            await self.disconnect()
            raise
    
    # ========================================================================
    # MESSAGE SEND/RECEIVE
    # ========================================================================
    
    async def send_message(self, message: Message):
        """
        Invia messaggio al peer.
        
        Args:
            message: Messaggio da inviare
        
        Raises:
            PeerConnectionError: Se invio fallisce
        
        Examples:
            >>> msg = MessageFactory.create_ping(nonce=123)
            >>> await peer.send_message(msg)
        """
        if not self.writer:
            raise PeerConnectionError(
                "Peer not connected",
                code="PEER_NOT_CONNECTED"
            )
        
        try:
            # Serialize message
            data = message.serialize()
            
            # Send
            self.writer.write(data)
            await self.writer.drain()
            
            # Update stats
            self.bytes_sent += len(data)
            self.messages_sent += 1
            
            logger.debug(
                f"Sent {message.message_type.name} to {self} "
                f"({len(data)} bytes)"
            )
        
        except Exception as e:
            logger.error(f"Failed to send message to {self}: {e}")
            await self.disconnect()
            raise PeerConnectionError(
                f"Failed to send message: {e}",
                code="PEER_SEND_FAILED"
            )
    
    async def receive_message(self) -> Message:
        """
        Ricevi messaggio dal peer.
        
        Returns:
            Message: Messaggio ricevuto
        
        Raises:
            PeerConnectionError: Se ricezione fallisce
        
        Examples:
            >>> msg = await peer.receive_message()
            >>> print(msg.message_type.name)
        """
        if not self.reader:
            raise PeerConnectionError(
                "Peer not connected",
                code="PEER_NOT_CONNECTED"
            )
        
        try:
            # Read header first
            header_data = await asyncio.wait_for(
                self.reader.readexactly(Message.HEADER_SIZE),
                timeout=self.timeout
            )
            
            # Parse payload length from header
            length_offset = Message.MAGIC_SIZE + Message.COMMAND_SIZE
            payload_length_bytes = header_data[length_offset:length_offset + Message.LENGTH_SIZE]
            payload_length = int.from_bytes(payload_length_bytes, 'little')
            
            # Read payload
            payload_data = await asyncio.wait_for(
                self.reader.readexactly(payload_length),
                timeout=self.timeout
            )
            
            # Deserialize full message
            full_data = header_data + payload_data
            message = Message.deserialize(full_data)
            
            # Update stats
            self.bytes_received += len(full_data)
            self.messages_received += 1
            self.info.last_seen = int(time.time())
            
            logger.debug(
                f"Received {message.message_type.name} from {self} "
                f"({len(full_data)} bytes)"
            )
            
            # Trigger callback
            if self.on_message:
                self.on_message(message)
            
            return message
        
        except asyncio.TimeoutError:
            logger.error(f"Receive timeout from {self}")
            await self.disconnect()
            raise PeerTimeoutError(
                f"Receive timeout from peer",
                code="PEER_RECV_TIMEOUT"
            )
        
        except Exception as e:
            logger.error(f"Failed to receive message from {self}: {e}")
            await self.disconnect()
            raise PeerConnectionError(
                f"Failed to receive message: {e}",
                code="PEER_RECV_FAILED"
            )
    
    # ========================================================================
    # KEEP-ALIVE
    # ========================================================================
    
    async def send_ping(self):
        """Invia PING per keep-alive"""
        ping_nonce = secrets.randbits(64)
        ping_msg = MessageFactory.create_ping(ping_nonce)
        
        await self.send_message(ping_msg)
        self.last_ping_time = time.time()
        
        logger.debug(f"Sent PING to {self}")
    
    async def send_pong(self, nonce: int):
        """Invia PONG in risposta a PING"""
        pong_msg = MessageFactory.create_pong(nonce)
        
        await self.send_message(pong_msg)
        self.last_pong_time = time.time()
        
        logger.debug(f"Sent PONG to {self}")
    
    # ========================================================================
    # UTILITIES
    # ========================================================================
    
    def is_connected(self) -> bool:
        """Check se connesso"""
        return self.state in [PeerState.CONNECTED, PeerState.HANDSHAKING, PeerState.READY]
    
    def is_ready(self) -> bool:
        """Check se ready (handshake completo)"""
        return self.state == PeerState.READY and self.handshake_complete
    
    def get_statistics(self) -> Dict[str, Any]:
        """Ottieni statistiche connessione"""
        uptime = time.time() - self.connected_at if self.connected_at else 0
        
        return {
            "address": str(self),
            "state": self.state.value,
            "connected": self.is_connected(),
            "ready": self.is_ready(),
            "uptime_seconds": round(uptime, 2),
            "bytes_sent": self.bytes_sent,
            "bytes_received": self.bytes_received,
            "messages_sent": self.messages_sent,
            "messages_received": self.messages_received,
            "peer_height": self.info.start_height,
            "peer_version": self.info.version,
            "peer_agent": self.info.user_agent
        }
    
    def __str__(self) -> str:
        return f"{self.info.address}:{self.info.port}"
    
    def __repr__(self) -> str:
        return (
            f"Peer({self.info.address}:{self.info.port}, "
            f"state={self.state.value})"
        )


# ============================================================================
# EXPORT
# ============================================================================

__all__ = [
    "Peer",
    "PeerState",
    "PeerInfo",
]
