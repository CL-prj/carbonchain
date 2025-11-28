"""
CarbonChain - Lightning Network Layer (Preparation)
====================================================
Layer 2 payment channels per scaling.

Security Level: CRITICAL
Last Updated: 2025-11-27
Version: 0.1.0 (Experimental)

Features:
- Payment channels
- Hash Time-Locked Contracts (HTLC)
- Channel routing
- Off-chain transactions

Note: This is a preparation/prototype. Full Lightning Network
implementation requires extensive testing and security audits.
"""

from __future__ import annotations
from typing import Optional, List, Dict, Tuple
from dataclasses import dataclass, field
from enum import Enum
import hashlib
import secrets
import time

# Internal imports
from carbon_chain.domain.models import Transaction, TxInput, TxOutput
from carbon_chain.domain.crypto_core import sign_message, verify_signature
from carbon_chain.errors import ChannelError, ValidationError
from carbon_chain.logging_setup import get_logger
from carbon_chain.constants import TxType


# ============================================================================
# MODULE LOGGER
# ============================================================================

logger = get_logger("layer2.lightning")


# ============================================================================
# CHANNEL STATE
# ============================================================================

class ChannelState(Enum):
    """Stati payment channel"""
    OPENING = "opening"
    OPEN = "open"
    CLOSING = "closing"
    CLOSED = "closed"
    FORCE_CLOSED = "force_closed"


class HTLCState(Enum):
    """Stati HTLC"""
    PENDING = "pending"
    FULFILLED = "fulfilled"
    EXPIRED = "expired"


# ============================================================================
# PAYMENT CHANNEL
# ============================================================================

@dataclass
class PaymentChannel:
    """
    Payment channel bidirezionale.
    
    Permette transazioni off-chain istantanee tra due parti.
    
    Attributes:
        channel_id: ID univoco canale
        party_a: Address party A
        party_b: Address party B
        capacity: Capacità totale canale (Satoshi)
        balance_a: Balance party A
        balance_b: Balance party B
        state: Stato canale
        sequence: Sequence number (anti-replay)
        opening_tx: Transaction di apertura on-chain
        closing_tx: Transaction di chiusura (optional)
    
    Examples:
        >>> channel = PaymentChannel.create(
        ...     party_a="1Alice...",
        ...     party_b="1Bob...",
        ...     capacity=1000000
        ... )
        >>> channel.transfer(amount=100000, from_party="1Alice...")
    """
    
    channel_id: str
    party_a: str
    party_b: str
    capacity: int
    balance_a: int
    balance_b: int
    state: ChannelState = ChannelState.OPENING
    sequence: int = 0
    opening_tx: Optional[str] = None
    closing_tx: Optional[str] = None
    created_at: int = field(default_factory=lambda: int(time.time()))
    
    def __post_init__(self):
        """Validate channel"""
        if self.capacity != self.balance_a + self.balance_b:
            raise ValidationError(
                f"Invalid balances: {self.balance_a} + {self.balance_b} != {self.capacity}"
            )
    
    @classmethod
    def create(
        cls,
        party_a: str,
        party_b: str,
        capacity: int,
        initial_balance_a: Optional[int] = None
    ) -> PaymentChannel:
        """
        Crea nuovo payment channel.
        
        Args:
            party_a: Address party A
            party_b: Address party B
            capacity: Total capacity
            initial_balance_a: Initial balance A (default: capacity/2)
        
        Returns:
            PaymentChannel: Nuovo canale
        """
        if initial_balance_a is None:
            initial_balance_a = capacity // 2
        
        initial_balance_b = capacity - initial_balance_a
        
        # Generate channel ID
        channel_data = f"{party_a}{party_b}{capacity}{time.time()}"
        channel_id = hashlib.sha256(channel_data.encode()).hexdigest()
        
        return cls(
            channel_id=channel_id,
            party_a=party_a,
            party_b=party_b,
            capacity=capacity,
            balance_a=initial_balance_a,
            balance_b=initial_balance_b
        )
    
    def transfer(
        self,
        amount: int,
        from_party: str
    ) -> bool:
        """
        Trasferisci fondi nel canale (off-chain).
        
        Args:
            amount: Amount da trasferire
            from_party: Address mittente
        
        Returns:
            bool: True se trasferimento riuscito
        
        Raises:
            ChannelError: Se trasferimento invalido
        """
        if self.state != ChannelState.OPEN:
            raise ChannelError(f"Channel not open: {self.state}")
        
        # Determine direction
        if from_party == self.party_a:
            if self.balance_a < amount:
                raise ChannelError(f"Insufficient balance: {self.balance_a} < {amount}")
            
            self.balance_a -= amount
            self.balance_b += amount
        
        elif from_party == self.party_b:
            if self.balance_b < amount:
                raise ChannelError(f"Insufficient balance: {self.balance_b} < {amount}")
            
            self.balance_b -= amount
            self.balance_a += amount
        
        else:
            raise ChannelError(f"Invalid party: {from_party}")
        
        # Increment sequence
        self.sequence += 1
        
        logger.info(
            f"Channel {self.channel_id[:8]}... transfer: {amount} Satoshi",
            extra_data={"sequence": self.sequence}
        )
        
        return True
    
    def create_commitment_tx(
        self,
        for_party: str
    ) -> Transaction:
        """
        Crea commitment transaction.
        
        Commitment TX permette di chiudere canale unilateralmente.
        
        Args:
            for_party: Party per cui creare commitment
        
        Returns:
            Transaction: Commitment transaction
        """
        # Determine balances
        if for_party == self.party_a:
            my_balance = self.balance_a
            their_balance = self.balance_b
            my_address = self.party_a
            their_address = self.party_b
        else:
            my_balance = self.balance_b
            their_balance = self.balance_a
            my_address = self.party_b
            their_address = self.party_a
        
        # Create outputs
        outputs = []
        
        if my_balance > 0:
            outputs.append(TxOutput(amount=my_balance, address=my_address))
        
        if their_balance > 0:
            outputs.append(TxOutput(amount=their_balance, address=their_address))
        
        # Create transaction
        tx = Transaction(
            tx_type=TxType.TRANSFER,
            inputs=[],  # Will be filled with channel funding UTXO
            outputs=outputs,
            timestamp=int(time.time())
        )
        
        tx.metadata["channel_id"] = self.channel_id
        tx.metadata["sequence"] = self.sequence
        tx.metadata["commitment_type"] = "channel_close"
        
        return tx
    
    def open(self, opening_txid: str):
        """Apri canale dopo funding on-chain"""
        self.opening_tx = opening_txid
        self.state = ChannelState.OPEN
        logger.info(f"Channel {self.channel_id[:8]}... opened")
    
    def close(self, closing_txid: Optional[str] = None):
        """Chiudi canale cooperativamente"""
        self.state = ChannelState.CLOSING
        if closing_txid:
            self.closing_tx = closing_txid
            self.state = ChannelState.CLOSED
        
        logger.info(f"Channel {self.channel_id[:8]}... closed")
    
    def force_close(self):
        """Chiudi canale unilateralmente"""
        self.state = ChannelState.FORCE_CLOSED
        logger.warning(f"Channel {self.channel_id[:8]}... force closed")
    
    def to_dict(self) -> Dict:
        """Serializza canale"""
        return {
            "channel_id": self.channel_id,
            "party_a": self.party_a,
            "party_b": self.party_b,
            "capacity": self.capacity,
            "balance_a": self.balance_a,
            "balance_b": self.balance_b,
            "state": self.state.value,
            "sequence": self.sequence,
            "opening_tx": self.opening_tx,
            "closing_tx": self.closing_tx,
            "created_at": self.created_at
        }


# ============================================================================
# HTLC (Hash Time-Locked Contract)
# ============================================================================

@dataclass
class HTLC:
    """
    Hash Time-Locked Contract.
    
    Permette pagamenti condizionali con timeout.
    
    Attributes:
        htlc_id: ID univoco HTLC
        amount: Amount bloccato
        payment_hash: Hash del preimage
        preimage: Preimage segreto (rivelato per claim)
        expiry: Timestamp scadenza
        sender: Address mittente
        receiver: Address destinatario
        state: Stato HTLC
    
    Examples:
        >>> # Create HTLC
        >>> preimage = secrets.token_bytes(32)
        >>> payment_hash = hashlib.sha256(preimage).digest()
        >>> htlc = HTLC.create(
        ...     amount=100000,
        ...     payment_hash=payment_hash,
        ...     expiry=int(time.time()) + 3600,
        ...     sender="1Alice...",
        ...     receiver="1Bob..."
        ... )
        
        >>> # Fulfill HTLC
        >>> htlc.fulfill(preimage)
    """
    
    htlc_id: str
    amount: int
    payment_hash: bytes
    preimage: Optional[bytes]
    expiry: int
    sender: str
    receiver: str
    state: HTLCState = HTLCState.PENDING
    created_at: int = field(default_factory=lambda: int(time.time()))
    
    @classmethod
    def create(
        cls,
        amount: int,
        payment_hash: bytes,
        expiry: int,
        sender: str,
        receiver: str
    ) -> HTLC:
        """
        Crea nuovo HTLC.
        
        Args:
            amount: Amount da bloccare
            payment_hash: Hash del preimage
            expiry: Timestamp scadenza
            sender: Address mittente
            receiver: Address destinatario
        
        Returns:
            HTLC: Nuovo HTLC
        """
        # Generate HTLC ID
        htlc_data = f"{payment_hash.hex()}{amount}{expiry}"
        htlc_id = hashlib.sha256(htlc_data.encode()).hexdigest()
        
        return cls(
            htlc_id=htlc_id,
            amount=amount,
            payment_hash=payment_hash,
            preimage=None,
            expiry=expiry,
            sender=sender,
            receiver=receiver
        )
    
    def fulfill(self, preimage: bytes) -> bool:
        """
        Fulfill HTLC rivelando preimage.
        
        Args:
            preimage: Preimage segreto
        
        Returns:
            bool: True se preimage corretto
        
        Raises:
            ChannelError: Se preimage invalido o HTLC scaduto
        """
        # Check expiry
        if time.time() > self.expiry:
            self.state = HTLCState.EXPIRED
            raise ChannelError("HTLC expired")
        
        # Verify preimage
        computed_hash = hashlib.sha256(preimage).digest()
        if computed_hash != self.payment_hash:
            raise ChannelError("Invalid preimage")
        
        # Fulfill
        self.preimage = preimage
        self.state = HTLCState.FULFILLED
        
        logger.info(f"HTLC {self.htlc_id[:8]}... fulfilled")
        
        return True
    
    def check_expired(self) -> bool:
        """Check se HTLC scaduto"""
        if time.time() > self.expiry and self.state == HTLCState.PENDING:
            self.state = HTLCState.EXPIRED
            return True
        return False
    
    def to_dict(self) -> Dict:
        """Serializza HTLC"""
        return {
            "htlc_id": self.htlc_id,
            "amount": self.amount,
            "payment_hash": self.payment_hash.hex(),
            "preimage": self.preimage.hex() if self.preimage else None,
            "expiry": self.expiry,
            "sender": self.sender,
            "receiver": self.receiver,
            "state": self.state.value,
            "created_at": self.created_at
        }


# ============================================================================
# LIGHTNING PAYMENT
# ============================================================================

@dataclass
class LightningPayment:
    """
    Lightning Network payment.
    
    Pagamento multi-hop attraverso canali.
    
    Attributes:
        payment_id: ID pagamento
        amount: Amount da pagare
        sender: Mittente
        receiver: Destinatario
        route: Lista canali nel percorso
        htlcs: Lista HTLC lungo il percorso
        status: Stato pagamento
    """
    
    payment_id: str
    amount: int
    sender: str
    receiver: str
    route: List[str] = field(default_factory=list)
    htlcs: List[HTLC] = field(default_factory=list)
    status: str = "pending"
    created_at: int = field(default_factory=lambda: int(time.time()))
    
    @classmethod
    def create(
        cls,
        amount: int,
        sender: str,
        receiver: str
    ) -> LightningPayment:
        """Crea nuovo payment"""
        payment_data = f"{sender}{receiver}{amount}{time.time()}"
        payment_id = hashlib.sha256(payment_data.encode()).hexdigest()
        
        return cls(
            payment_id=payment_id,
            amount=amount,
            sender=sender,
            receiver=receiver
        )


# ============================================================================
# CHANNEL MANAGER
# ============================================================================

class ChannelManager:
    """
    Gestione payment channels.
    
    Attributes:
        channels: Canali attivi
        htlcs: HTLC attivi
    
    Examples:
        >>> manager = ChannelManager()
        >>> channel = manager.open_channel("1Alice...", "1Bob...", 1000000)
        >>> manager.transfer(channel.channel_id, 100000, "1Alice...")
    """
    
    def __init__(self):
        """Initialize channel manager"""
        self.channels: Dict[str, PaymentChannel] = {}
        self.htlcs: Dict[str, HTLC] = {}
    
    def open_channel(
        self,
        party_a: str,
        party_b: str,
        capacity: int,
        initial_balance_a: Optional[int] = None
    ) -> PaymentChannel:
        """
        Apri nuovo payment channel.
        
        Args:
            party_a: Address party A
            party_b: Address party B
            capacity: Total capacity
            initial_balance_a: Initial balance A
        
        Returns:
            PaymentChannel: Canale creato
        """
        channel = PaymentChannel.create(
            party_a=party_a,
            party_b=party_b,
            capacity=capacity,
            initial_balance_a=initial_balance_a
        )
        
        self.channels[channel.channel_id] = channel
        
        logger.info(
            f"Created payment channel {channel.channel_id[:8]}...",
            extra_data={"capacity": capacity}
        )
        
        return channel
    
    def get_channel(self, channel_id: str) -> Optional[PaymentChannel]:
        """Get channel by ID"""
        return self.channels.get(channel_id)
    
    def transfer(
        self,
        channel_id: str,
        amount: int,
        from_party: str
    ) -> bool:
        """
        Trasferisci fondi in canale.
        
        Args:
            channel_id: ID canale
            amount: Amount da trasferire
            from_party: Address mittente
        
        Returns:
            bool: True se successo
        """
        channel = self.get_channel(channel_id)
        
        if not channel:
            raise ChannelError(f"Channel not found: {channel_id}")
        
        return channel.transfer(amount, from_party)
    
    def create_htlc(
        self,
        channel_id: str,
        amount: int,
        payment_hash: bytes,
        expiry: int,
        sender: str,
        receiver: str
    ) -> HTLC:
        """
        Crea HTLC per pagamento condizionale.
        
        Args:
            channel_id: ID canale
            amount: Amount
            payment_hash: Hash preimage
            expiry: Timestamp scadenza
            sender: Mittente
            receiver: Destinatario
        
        Returns:
            HTLC: HTLC creato
        """
        htlc = HTLC.create(
            amount=amount,
            payment_hash=payment_hash,
            expiry=expiry,
            sender=sender,
            receiver=receiver
        )
        
        self.htlcs[htlc.htlc_id] = htlc
        
        logger.info(f"Created HTLC {htlc.htlc_id[:8]}...")
        
        return htlc
    
    def fulfill_htlc(
        self,
        htlc_id: str,
        preimage: bytes
    ) -> bool:
        """
        Fulfill HTLC.
        
        Args:
            htlc_id: ID HTLC
            preimage: Preimage segreto
        
        Returns:
            bool: True se fulfilled
        """
        htlc = self.htlcs.get(htlc_id)
        
        if not htlc:
            raise ChannelError(f"HTLC not found: {htlc_id}")
        
        return htlc.fulfill(preimage)
    
    def close_channel(
        self,
        channel_id: str,
        cooperative: bool = True
    ) -> Transaction:
        """
        Chiudi canale.
        
        Args:
            channel_id: ID canale
            cooperative: Se chiusura cooperativa
        
        Returns:
            Transaction: Closing transaction
        """
        channel = self.get_channel(channel_id)
        
        if not channel:
            raise ChannelError(f"Channel not found: {channel_id}")
        
        if cooperative:
            channel.close()
        else:
            channel.force_close()
        
        # Create final settlement transaction
        closing_tx = channel.create_commitment_tx(channel.party_a)
        
        return closing_tx
    
    def get_statistics(self) -> Dict:
        """Get channel statistics"""
        return {
            "total_channels": len(self.channels),
            "open_channels": sum(
                1 for c in self.channels.values()
                if c.state == ChannelState.OPEN
            ),
            "total_capacity": sum(
                c.capacity for c in self.channels.values()
            ),
            "active_htlcs": sum(
                1 for h in self.htlcs.values()
                if h.state == HTLCState.PENDING
            )
        }


# ============================================================================
# EXPORT
# ============================================================================

__all__ = [
    "ChannelState",
    "HTLCState",
    "PaymentChannel",
    "HTLC",
    "LightningPayment",
    "ChannelManager",
]
