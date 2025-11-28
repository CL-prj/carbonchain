"""
CarbonChain - P2P Message Protocol
====================================
Protocol di messaggistica peer-to-peer.

Security Level: HIGH
Last Updated: 2025-11-27
Version: 1.0.0

Message Types:
- VERSION: Handshake iniziale
- VERACK: Conferma versione
- PING/PONG: Keep-alive
- GETBLOCKS: Richiesta blocchi
- BLOCKS: Invio blocchi
- INV: Inventory (nuovi blocchi/tx)
- GETDATA: Richiesta dati
- TX: Transazione
- MEMPOOL: Richiesta mempool
"""

from __future__ import annotations
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from enum import IntEnum
import struct
import hashlib
import time

# Internal imports
from carbon_chain.errors import (
    NetworkError,
    MessageValidationError,
    InvalidMessageError,
)
from carbon_chain.logging_setup import get_logger
from carbon_chain.constants import NETWORK_MAGIC, PROTOCOL_VERSION


# ============================================================================
# MODULE LOGGER
# ============================================================================

logger = get_logger("network.message")


# ============================================================================
# MESSAGE TYPES
# ============================================================================

class MessageType(IntEnum):
    """Tipi di messaggio P2P"""
    VERSION = 0
    VERACK = 1
    PING = 2
    PONG = 3
    GETBLOCKS = 4
    BLOCKS = 5
    INV = 6
    GETDATA = 7
    TX = 8
    MEMPOOL = 9
    ADDR = 10
    REJECT = 11


class InventoryType(IntEnum):
    """Tipi di inventory"""
    ERROR = 0
    MSG_TX = 1
    MSG_BLOCK = 2


# ============================================================================
# MESSAGE BASE CLASS
# ============================================================================

@dataclass
class Message:
    """
    Messaggio P2P base.
    
    Formato wire protocol:
    - Magic bytes (4): Network identifier
    - Command (12): Message type
    - Payload length (4): Size in bytes
    - Checksum (4): First 4 bytes of double-SHA256
    - Payload (variable): Message data
    
    Attributes:
        message_type: Tipo messaggio
        payload: Dati messaggio
        timestamp: Timestamp creazione
    """
    
    message_type: MessageType
    payload: bytes = field(default=b'')
    timestamp: int = field(default_factory=lambda: int(time.time()))
    
    # Wire protocol constants
    MAGIC_SIZE = 4
    COMMAND_SIZE = 12
    LENGTH_SIZE = 4
    CHECKSUM_SIZE = 4
    HEADER_SIZE = MAGIC_SIZE + COMMAND_SIZE + LENGTH_SIZE + CHECKSUM_SIZE
    
    def serialize(self) -> bytes:
        """
        Serializza messaggio in formato wire protocol.
        
        Returns:
            bytes: Messaggio serializzato
        
        Examples:
            >>> msg = Message(MessageType.PING, b'test')
            >>> data = msg.serialize()
            >>> len(data) >= Message.HEADER_SIZE
            True
        """
        # Magic bytes
        magic = NETWORK_MAGIC
        
        # Command (padded to 12 bytes)
        command = self.message_type.name.encode('ascii')
        command = command.ljust(self.COMMAND_SIZE, b'\x00')
        
        # Payload length
        payload_length = len(self.payload)
        length_bytes = struct.pack('<I', payload_length)
        
        # Checksum (first 4 bytes of double-SHA256)
        checksum = self._calculate_checksum(self.payload)
        
        # Assemble header + payload
        header = magic + command + length_bytes + checksum
        
        return header + self.payload
    
    @classmethod
    def deserialize(cls, data: bytes) -> Message:
        """
        Deserializza messaggio da wire protocol.
        
        Args:
            data: Dati serializzati
        
        Returns:
            Message: Messaggio deserializzato
        
        Raises:
            InvalidMessageError: Se formato invalido
        
        Examples:
            >>> msg = Message(MessageType.PING, b'test')
            >>> data = msg.serialize()
            >>> msg2 = Message.deserialize(data)
            >>> msg.message_type == msg2.message_type
            True
        """
        if len(data) < cls.HEADER_SIZE:
            raise InvalidMessageError(
                f"Message too short: {len(data)} bytes",
                code="MSG_TOO_SHORT"
            )
        
        # Parse header
        magic = data[:cls.MAGIC_SIZE]
        command = data[cls.MAGIC_SIZE:cls.MAGIC_SIZE + cls.COMMAND_SIZE]
        length_bytes = data[cls.MAGIC_SIZE + cls.COMMAND_SIZE:
                           cls.MAGIC_SIZE + cls.COMMAND_SIZE + cls.LENGTH_SIZE]
        checksum = data[cls.MAGIC_SIZE + cls.COMMAND_SIZE + cls.LENGTH_SIZE:
                       cls.HEADER_SIZE]
        
        # Validate magic
        if magic != NETWORK_MAGIC:
            raise InvalidMessageError(
                f"Invalid magic bytes: {magic.hex()}",
                code="INVALID_MAGIC"
            )
        
        # Parse command
        command_str = command.rstrip(b'\x00').decode('ascii')
        try:
            message_type = MessageType[command_str]
        except KeyError:
            raise InvalidMessageError(
                f"Unknown command: {command_str}",
                code="UNKNOWN_COMMAND"
            )
        
        # Parse length
        payload_length = struct.unpack('<I', length_bytes)[0]
        
        # Extract payload
        payload = data[cls.HEADER_SIZE:cls.HEADER_SIZE + payload_length]
        
        if len(payload) != payload_length:
            raise InvalidMessageError(
                f"Payload length mismatch: expected {payload_length}, got {len(payload)}",
                code="PAYLOAD_LENGTH_MISMATCH"
            )
        
        # Validate checksum
        expected_checksum = cls._calculate_checksum(payload)
        if checksum != expected_checksum:
            raise InvalidMessageError(
                "Checksum mismatch",
                code="CHECKSUM_MISMATCH"
            )
        
        return cls(
            message_type=message_type,
            payload=payload,
            timestamp=int(time.time())
        )
    
    @staticmethod
    def _calculate_checksum(data: bytes) -> bytes:
        """Calcola checksum (first 4 bytes of double-SHA256)"""
        hash1 = hashlib.sha256(data).digest()
        hash2 = hashlib.sha256(hash1).digest()
        return hash2[:4]
    
    def __repr__(self) -> str:
        return f"Message(type={self.message_type.name}, size={len(self.payload)})"


# ============================================================================
# SPECIFIC MESSAGE CLASSES
# ============================================================================

@dataclass
class VersionMessage:
    """
    VERSION message per handshake.
    
    Attributes:
        version: Protocol version
        services: Node services (bitfield)
        timestamp: Current timestamp
        addr_recv: Receiver address
        addr_from: Sender address
        nonce: Random nonce (anti-replay)
        user_agent: Node software version
        start_height: Current blockchain height
    """
    
    version: int
    services: int
    timestamp: int
    addr_recv: str
    addr_from: str
    nonce: int
    user_agent: str
    start_height: int
    
    def serialize(self) -> bytes:
        """Serializza VERSION payload"""
        import json
        data = {
            "version": self.version,
            "services": self.services,
            "timestamp": self.timestamp,
            "addr_recv": self.addr_recv,
            "addr_from": self.addr_from,
            "nonce": self.nonce,
            "user_agent": self.user_agent,
            "start_height": self.start_height
        }
        return json.dumps(data).encode('utf-8')
    
    @classmethod
    def deserialize(cls, payload: bytes) -> VersionMessage:
        """Deserializza VERSION payload"""
        import json
        data = json.loads(payload.decode('utf-8'))
        return cls(**data)
    
    def to_message(self) -> Message:
        """Converti in Message"""
        return Message(
            message_type=MessageType.VERSION,
            payload=self.serialize()
        )


@dataclass
class PingMessage:
    """PING message per keep-alive"""
    nonce: int
    
    def serialize(self) -> bytes:
        return struct.pack('<Q', self.nonce)
    
    @classmethod
    def deserialize(cls, payload: bytes) -> PingMessage:
        nonce = struct.unpack('<Q', payload)[0]
        return cls(nonce=nonce)
    
    def to_message(self) -> Message:
        return Message(
            message_type=MessageType.PING,
            payload=self.serialize()
        )


@dataclass
class PongMessage:
    """PONG response"""
    nonce: int
    
    def serialize(self) -> bytes:
        return struct.pack('<Q', self.nonce)
    
    @classmethod
    def deserialize(cls, payload: bytes) -> PongMessage:
        nonce = struct.unpack('<Q', payload)[0]
        return cls(nonce=nonce)
    
    def to_message(self) -> Message:
        return Message(
            message_type=MessageType.PONG,
            payload=self.serialize()
        )


@dataclass
class InvMessage:
    """
    INV (inventory) message.
    
    Annuncia disponibilità di nuovi blocchi o transazioni.
    """
    
    inventory: List[tuple[InventoryType, str]]  # (type, hash)
    
    def serialize(self) -> bytes:
        import json
        data = [
            {"type": inv_type.value, "hash": hash_str}
            for inv_type, hash_str in self.inventory
        ]
        return json.dumps(data).encode('utf-8')
    
    @classmethod
    def deserialize(cls, payload: bytes) -> InvMessage:
        import json
        data = json.loads(payload.decode('utf-8'))
        inventory = [
            (InventoryType(item["type"]), item["hash"])
            for item in data
        ]
        return cls(inventory=inventory)
    
    def to_message(self) -> Message:
        return Message(
            message_type=MessageType.INV,
            payload=self.serialize()
        )


@dataclass
class GetBlocksMessage:
    """
    GETBLOCKS message.
    
    Richiede blocchi da un peer.
    """
    
    version: int
    block_locator_hashes: List[str]
    hash_stop: str
    
    def serialize(self) -> bytes:
        import json
        data = {
            "version": self.version,
            "block_locator_hashes": self.block_locator_hashes,
            "hash_stop": self.hash_stop
        }
        return json.dumps(data).encode('utf-8')
    
    @classmethod
    def deserialize(cls, payload: bytes) -> GetBlocksMessage:
        import json
        data = json.loads(payload.decode('utf-8'))
        return cls(**data)
    
    def to_message(self) -> Message:
        return Message(
            message_type=MessageType.GETBLOCKS,
            payload=self.serialize()
        )


@dataclass
class GetDataMessage:
    """GETDATA message - richiede dati specifici"""
    inventory: List[tuple[InventoryType, str]]
    
    def serialize(self) -> bytes:
        import json
        data = [
            {"type": inv_type.value, "hash": hash_str}
            for inv_type, hash_str in self.inventory
        ]
        return json.dumps(data).encode('utf-8')
    
    @classmethod
    def deserialize(cls, payload: bytes) -> GetDataMessage:
        import json
        data = json.loads(payload.decode('utf-8'))
        inventory = [
            (InventoryType(item["type"]), item["hash"])
            for item in data
        ]
        return cls(inventory=inventory)
    
    def to_message(self) -> Message:
        return Message(
            message_type=MessageType.GETDATA,
            payload=self.serialize()
        )


# ============================================================================
# MESSAGE FACTORY
# ============================================================================

class MessageFactory:
    """Factory per creare messaggi tipizzati"""
    
    @staticmethod
    def create_version(
        version: int,
        services: int,
        addr_recv: str,
        addr_from: str,
        nonce: int,
        user_agent: str,
        start_height: int
    ) -> Message:
        """Crea VERSION message"""
        version_msg = VersionMessage(
            version=version,
            services=services,
            timestamp=int(time.time()),
            addr_recv=addr_recv,
            addr_from=addr_from,
            nonce=nonce,
            user_agent=user_agent,
            start_height=start_height
        )
        return version_msg.to_message()
    
    @staticmethod
    def create_verack() -> Message:
        """Crea VERACK message"""
        return Message(message_type=MessageType.VERACK, payload=b'')
    
    @staticmethod
    def create_ping(nonce: int) -> Message:
        """Crea PING message"""
        ping_msg = PingMessage(nonce=nonce)
        return ping_msg.to_message()
    
    @staticmethod
    def create_pong(nonce: int) -> Message:
        """Crea PONG message"""
        pong_msg = PongMessage(nonce=nonce)
        return pong_msg.to_message()
    
    @staticmethod
    def create_inv(inventory: List[tuple[InventoryType, str]]) -> Message:
        """Crea INV message"""
        inv_msg = InvMessage(inventory=inventory)
        return inv_msg.to_message()
    
    @staticmethod
    def create_getblocks(
        version: int,
        block_locator_hashes: List[str],
        hash_stop: str = "0" * 64
    ) -> Message:
        """Crea GETBLOCKS message"""
        getblocks_msg = GetBlocksMessage(
            version=version,
            block_locator_hashes=block_locator_hashes,
            hash_stop=hash_stop
        )
        return getblocks_msg.to_message()
    
    @staticmethod
    def create_getdata(inventory: List[tuple[InventoryType, str]]) -> Message:
        """Crea GETDATA message"""
        getdata_msg = GetDataMessage(inventory=inventory)
        return getdata_msg.to_message()


# ============================================================================
# EXPORT
# ============================================================================

__all__ = [
    "Message",
    "MessageType",
    "InventoryType",
    "VersionMessage",
    "PingMessage",
    "PongMessage",
    "InvMessage",
    "GetBlocksMessage",
    "GetDataMessage",
    "MessageFactory",
]
