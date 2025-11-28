"""
CarbonChain - Multi-Signature Wallet
======================================
Wallet con firme multiple (M-of-N).

Security Level: CRITICAL
Last Updated: 2025-11-27
Version: 1.0.0

Features:
- M-of-N signature schemes (e.g., 2-of-3, 3-of-5)
- P2SH addresses
- Partial signature collection
- BIP-174 PSBT support (Partially Signed Bitcoin Transactions)
"""

from __future__ import annotations
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
import hashlib
import time

# Internal imports
from carbon_chain.domain.crypto_core import (
    generate_keypair,
    sign_message,
    verify_signature,
    hash_sha256
)
from carbon_chain.domain.addressing import (
    public_key_to_address,
    validate_address
)
from carbon_chain.errors import (
    WalletError,
    InvalidSignatureError,
    ValidationError
)
from carbon_chain.logging_setup import get_logger
from carbon_chain.config import ChainSettings


# ============================================================================
# MODULE LOGGER
# ============================================================================

logger = get_logger("wallet.multisig")


# ============================================================================
# MULTISIG CONFIGURATION
# ============================================================================

@dataclass
class MultiSigConfig:
    """
    Configurazione multi-signature.
    
    Attributes:
        m: Firme richieste (M)
        n: Firme totali (N)
        public_keys: Lista public keys (len = N)
        script_hash: Hash dello script (per P2SH address)
        
    Examples:
        >>> config = MultiSigConfig(m=2, n=3, public_keys=[pk1, pk2, pk3])
        >>> # 2-of-3 multisig
    """
    
    m: int  # Required signatures
    n: int  # Total signatures
    public_keys: List[bytes]
    script_hash: Optional[str] = None
    
    def __post_init__(self):
        """Validate configuration"""
        if self.m <= 0 or self.n <= 0:
            raise ValidationError("M and N must be positive")
        
        if self.m > self.n:
            raise ValidationError(f"M ({self.m}) cannot exceed N ({self.n})")
        
        if len(self.public_keys) != self.n:
            raise ValidationError(
                f"Expected {self.n} public keys, got {len(self.public_keys)}"
            )
        
        # Generate script hash if not provided
        if self.script_hash is None:
            self.script_hash = self._generate_script_hash()
    
    def _generate_script_hash(self) -> str:
        """Generate P2SH script hash"""
        # Create redeem script: OP_M <pubkey1> <pubkey2> ... <pubkeyN> OP_N OP_CHECKMULTISIG
        script = b''
        
        # OP_M (push M)
        script += bytes([0x50 + self.m])  # OP_1 = 0x51, OP_2 = 0x52, etc.
        
        # Push public keys
        for pk in self.public_keys:
            script += bytes([len(pk)]) + pk
        
        # OP_N (push N)
        script += bytes([0x50 + self.n])
        
        # OP_CHECKMULTISIG
        script += bytes([0xae])
        
        # Hash script (SHA-256)
        script_hash = hash_sha256(script)
        
        return script_hash
    
    def get_address(self, version: bytes = b'\x05') -> str:
        """
        Get P2SH address for multisig.
        
        Args:
            version: Address version (0x05 for P2SH mainnet)
        
        Returns:
            str: P2SH address
        """
        # For simplicity, use script_hash as base
        # In production, implement full Base58Check encoding
        return f"3{self.script_hash[:40]}"  # P2SH addresses start with '3'
    
    def to_dict(self) -> Dict:
        """Serialize to dict"""
        return {
            "m": self.m,
            "n": self.n,
            "public_keys": [pk.hex() for pk in self.public_keys],
            "script_hash": self.script_hash,
            "address": self.get_address()
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> MultiSigConfig:
        """Deserialize from dict"""
        return cls(
            m=data["m"],
            n=data["n"],
            public_keys=[bytes.fromhex(pk) for pk in data["public_keys"]],
            script_hash=data.get("script_hash")
        )


# ============================================================================
# PARTIAL SIGNATURE
# ============================================================================

@dataclass
class PartialSignature:
    """
    Firma parziale per transazione multisig.
    
    Attributes:
        signer_index: Indice del firmatario (0 to N-1)
        public_key: Public key del firmatario
        signature: Firma digitale
        timestamp: Timestamp firma
    """
    
    signer_index: int
    public_key: bytes
    signature: bytes
    timestamp: int = field(default_factory=lambda: int(time.time()))
    
    def to_dict(self) -> Dict:
        """Serialize"""
        return {
            "signer_index": self.signer_index,
            "public_key": self.public_key.hex(),
            "signature": self.signature.hex(),
            "timestamp": self.timestamp
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> PartialSignature:
        """Deserialize"""
        return cls(
            signer_index=data["signer_index"],
            public_key=bytes.fromhex(data["public_key"]),
            signature=bytes.fromhex(data["signature"]),
            timestamp=data["timestamp"]
        )


# ============================================================================
# PSBT (Partially Signed Bitcoin Transaction)
# ============================================================================

@dataclass
class PSBT:
    """
    Partially Signed Bitcoin Transaction (BIP-174 inspired).
    
    Gestisce raccolta firme incrementale per transazioni multisig.
    
    Attributes:
        transaction_data: Dati transazione (serializzati)
        multisig_config: Configurazione multisig
        partial_signatures: Firme parziali raccolte
        is_finalized: Se tutte le firme sono state raccolte
    """
    
    transaction_data: bytes
    multisig_config: MultiSigConfig
    partial_signatures: List[PartialSignature] = field(default_factory=list)
    is_finalized: bool = False
    
    def add_signature(
        self,
        signer_index: int,
        private_key: bytes,
        public_key: bytes
    ) -> bool:
        """
        Aggiungi firma parziale.
        
        Args:
            signer_index: Indice firmatario (0 to N-1)
            private_key: Private key per firma
            public_key: Public key corrispondente
        
        Returns:
            bool: True se firma aggiunta con successo
        
        Raises:
            ValidationError: Se signer_index invalido
            InvalidSignatureError: Se firma invalida
        """
        # Validate signer index
        if signer_index < 0 or signer_index >= self.multisig_config.n:
            raise ValidationError(
                f"Invalid signer_index: {signer_index}. Must be 0 to {self.multisig_config.n - 1}"
            )
        
        # Check if already signed
        if any(sig.signer_index == signer_index for sig in self.partial_signatures):
            logger.warning(f"Signer {signer_index} already signed")
            return False
        
        # Verify public key matches config
        expected_pk = self.multisig_config.public_keys[signer_index]
        if public_key != expected_pk:
            raise InvalidSignatureError(
                f"Public key mismatch for signer {signer_index}"
            )
        
        # Sign transaction data
        signature = sign_message(self.transaction_data, private_key)
        
        # Verify signature
        if not verify_signature(self.transaction_data, signature, public_key):
            raise InvalidSignatureError("Signature verification failed")
        
        # Add partial signature
        partial_sig = PartialSignature(
            signer_index=signer_index,
            public_key=public_key,
            signature=signature
        )
        
        self.partial_signatures.append(partial_sig)
        
        logger.info(
            f"Added signature from signer {signer_index}. "
            f"Total: {len(self.partial_signatures)}/{self.multisig_config.m}"
        )
        
        # Check if finalized
        if len(self.partial_signatures) >= self.multisig_config.m:
            self.is_finalized = True
            logger.info("PSBT finalized - all required signatures collected")
        
        return True
    
    def verify_signatures(self) -> bool:
        """
        Verifica tutte le firme parziali.
        
        Returns:
            bool: True se tutte valide
        """
        for partial_sig in self.partial_signatures:
            if not verify_signature(
                self.transaction_data,
                partial_sig.signature,
                partial_sig.public_key
            ):
                logger.error(f"Invalid signature from signer {partial_sig.signer_index}")
                return False
        
        return True
    
    def get_finalized_signatures(self) -> Optional[List[bytes]]:
        """
        Ottieni firme finali per broadcast.
        
        Returns:
            List[bytes]: Lista firme, o None se non finalized
        """
        if not self.is_finalized:
            return None
        
        # Sort by signer_index
        sorted_sigs = sorted(self.partial_signatures, key=lambda s: s.signer_index)
        
        return [sig.signature for sig in sorted_sigs[:self.multisig_config.m]]
    
    def to_dict(self) -> Dict:
        """Serialize PSBT"""
        return {
            "transaction_data": self.transaction_data.hex(),
            "multisig_config": self.multisig_config.to_dict(),
            "partial_signatures": [sig.to_dict() for sig in self.partial_signatures],
            "is_finalized": self.is_finalized
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> PSBT:
        """Deserialize PSBT"""
        return cls(
            transaction_data=bytes.fromhex(data["transaction_data"]),
            multisig_config=MultiSigConfig.from_dict(data["multisig_config"]),
            partial_signatures=[
                PartialSignature.from_dict(sig) for sig in data["partial_signatures"]
            ],
            is_finalized=data["is_finalized"]
        )


# ============================================================================
# MULTISIG WALLET
# ============================================================================

class MultiSigWallet:
    """
    Multi-signature wallet.
    
    Gestisce wallet con M-of-N firme richieste.
    
    Attributes:
        config: MultiSigConfig
        my_index: Indice di questo wallet (0 to N-1)
        my_private_key: Private key di questo wallet
        my_public_key: Public key di questo wallet
    
    Examples:
        >>> # Create 2-of-3 multisig
        >>> wallet = MultiSigWallet.create(m=2, n=3, my_index=0)
        >>> address = wallet.get_address()
        >>> # Sign transaction
        >>> psbt = wallet.create_psbt(tx_data)
        >>> wallet.sign_psbt(psbt)
    """
    
    def __init__(
        self,
        config: MultiSigConfig,
        my_index: int,
        my_private_key: bytes,
        my_public_key: bytes
    ):
        """
        Inizializza multisig wallet.
        
        Args:
            config: MultiSig configuration
            my_index: Index di questo wallet (0 to N-1)
            my_private_key: Private key
            my_public_key: Public key
        """
        self.config = config
        self.my_index = my_index
        self.my_private_key = my_private_key
        self.my_public_key = my_public_key
        
        # Validate
        if my_index < 0 or my_index >= config.n:
            raise ValidationError(f"Invalid my_index: {my_index}")
        
        if config.public_keys[my_index] != my_public_key:
            raise ValidationError("Public key mismatch")
    
    @classmethod
    def create(
        cls,
        m: int,
        n: int,
        my_index: int,
        other_public_keys: List[bytes],
        config: Optional[ChainSettings] = None
    ) -> MultiSigWallet:
        """
        Crea nuovo multisig wallet.
        
        Args:
            m: Firme richieste
            n: Firme totali
            my_index: Indice di questo wallet
            other_public_keys: Public keys degli altri partecipanti
            config: Chain settings
        
        Returns:
            MultiSigWallet: Nuovo wallet
        
        Examples:
            >>> wallet = MultiSigWallet.create(
            ...     m=2, n=3, my_index=0,
            ...     other_public_keys=[pk2, pk3]
            ... )
        """
        # Generate keypair for this wallet
        private_key, public_key = generate_keypair()
        
        # Build complete public keys list
        all_public_keys = []
        
        for i in range(n):
            if i == my_index:
                all_public_keys.append(public_key)
            else:
                # Get from other_public_keys (adjust index)
                other_idx = i if i < my_index else i - 1
                all_public_keys.append(other_public_keys[other_idx])
        
        # Create config
        multisig_config = MultiSigConfig(m=m, n=n, public_keys=all_public_keys)
        
        return cls(
            config=multisig_config,
            my_index=my_index,
            my_private_key=private_key,
            my_public_key=public_key
        )
    
    def get_address(self) -> str:
        """Get P2SH address"""
        return self.config.get_address()
    
    def create_psbt(self, transaction_data: bytes) -> PSBT:
        """
        Crea PSBT per transazione.
        
        Args:
            transaction_data: Transaction data da firmare
        
        Returns:
            PSBT: PSBT instance
        """
        return PSBT(
            transaction_data=transaction_data,
            multisig_config=self.config
        )
    
    def sign_psbt(self, psbt: PSBT) -> bool:
        """
        Firma PSBT con chiave di questo wallet.
        
        Args:
            psbt: PSBT da firmare
        
        Returns:
            bool: True se firma aggiunta
        """
        return psbt.add_signature(
            signer_index=self.my_index,
            private_key=self.my_private_key,
            public_key=self.my_public_key
        )
    
    def export_public_key(self) -> bytes:
        """Export public key per condivisione"""
        return self.my_public_key
    
    def get_info(self) -> Dict:
        """Get wallet info"""
        return {
            "type": "multisig",
            "m": self.config.m,
            "n": self.config.n,
            "my_index": self.my_index,
            "address": self.get_address(),
            "script_hash": self.config.script_hash
        }


# ============================================================================
# EXPORT
# ============================================================================

__all__ = [
    "MultiSigConfig",
    "PartialSignature",
    "PSBT",
    "MultiSigWallet",
]
