"""
CarbonChain - KeyPair Management
==================================
Gestione coppie chiavi crittografiche per transazioni.

Security Level: CRITICAL
Last Updated: 2025-11-27
Version: 1.0.0

Features:
- KeyPair wrapper immutabile
- Firma/verifica transazioni
- Serializzazione sicura
- Encryption chiavi private
- Multi-signature support (future)
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, Dict, Any
import json

# Internal imports
from carbon_chain.domain.crypto_core import (
    get_crypto_provider,
    CryptoProvider,
    encrypt_data_aes_gcm,
    decrypt_data_aes_gcm,
    derive_key_pbkdf2,
    generate_random_bytes,
)
from carbon_chain.errors import (
    InvalidKeyError,
    InvalidSignatureError,
    EncryptionError,
    DecryptionError,
    CryptoError,
)
from carbon_chain.logging_setup import get_logger
from carbon_chain.constants import SIGNATURE_TYPE


# ============================================================================
# MODULE LOGGER
# ============================================================================

logger = get_logger("keypairs")


# ============================================================================
# KEYPAIR CLASS
# ============================================================================

@dataclass(frozen=True)
class KeyPair:
    """
    Coppia chiavi crittografiche immutabile.
    
    Rappresenta chiavi per:
    - Firmare transazioni
    - Ricevere coin (public key → address)
    - Autenticazione
    
    Attributes:
        private_key (bytes): Chiave privata (PEM format)
        public_key (bytes): Chiave pubblica (PEM format)
        _provider (CryptoProvider): Provider crittografico interno
    
    Security:
        - Immutabile (frozen dataclass)
        - Private key NON deve essere esposta
        - Provider nascosto (_private)
    
    Examples:
        >>> keypair = generate_keypair()
        >>> message = b"transaction_data"
        >>> signature = keypair.sign(message)
        >>> keypair.verify(message, signature)
        True
    """
    
    private_key: bytes
    public_key: bytes
    _provider: CryptoProvider = field(repr=False, compare=False)
    
    def __post_init__(self):
        """Validazione post-init"""
        if not self.private_key or not isinstance(self.private_key, bytes):
            raise InvalidKeyError(
                "Invalid private_key: must be non-empty bytes",
                code="INVALID_PRIVATE_KEY"
            )
        
        if not self.public_key or not isinstance(self.public_key, bytes):
            raise InvalidKeyError(
                "Invalid public_key: must be non-empty bytes",
                code="INVALID_PUBLIC_KEY"
            )
        
        # Validazione formato PEM
        if not self.private_key.startswith(b'-----BEGIN'):
            raise InvalidKeyError(
                "private_key must be in PEM format",
                code="INVALID_KEY_FORMAT"
            )
        
        if not self.public_key.startswith(b'-----BEGIN'):
            raise InvalidKeyError(
                "public_key must be in PEM format",
                code="INVALID_KEY_FORMAT"
            )
        
        logger.debug("KeyPair created and validated")
    
    def sign(self, message: bytes) -> bytes:
        """
        Firma messaggio con chiave privata.
        
        Args:
            message: Dati da firmare (hash tx, challenge, etc.)
        
        Returns:
            bytes: Firma digitale
        
        Raises:
            InvalidKeyError: Se firma fallisce
        
        Security:
            - Usa chiave privata (MANTIENI SEGRETA)
            - Firma è deterministica per stesso message
        
        Examples:
            >>> keypair = generate_keypair()
            >>> signature = keypair.sign(b"test_message")
            >>> len(signature) > 0
            True
        """
        if not isinstance(message, bytes):
            raise CryptoError(
                f"Message must be bytes, got {type(message).__name__}",
                code="INVALID_MESSAGE_TYPE"
            )
        
        if len(message) == 0:
            raise CryptoError("Message cannot be empty", code="EMPTY_MESSAGE")
        
        try:
            signature = self._provider.sign(message, self.private_key)
            
            logger.debug(
                "Message signed",
                extra_data={
                    "message_size": len(message),
                    "signature_size": len(signature)
                }
            )
            
            return signature
        
        except Exception as e:
            logger.error(f"Signing failed", extra_data={"error": str(e)})
            raise InvalidKeyError(
                f"Failed to sign message: {e}",
                code="SIGN_FAILED"
            )
    
    def verify(self, message: bytes, signature: bytes) -> bool:
        """
        Verifica firma con chiave pubblica.
        
        Args:
            message: Messaggio originale
            signature: Firma da verificare
        
        Returns:
            bool: True se firma valida, False altrimenti
        
        Note:
            - NON raise exception se firma invalida (return False)
            - Usa per validare transazioni
        
        Examples:
            >>> keypair = generate_keypair()
            >>> msg = b"test"
            >>> sig = keypair.sign(msg)
            >>> keypair.verify(msg, sig)
            True
            >>> keypair.verify(b"wrong", sig)
            False
        """
        if not isinstance(message, bytes) or not isinstance(signature, bytes):
            return False
        
        try:
            is_valid = self._provider.verify(message, signature, self.public_key)
            
            logger.debug(
                "Signature verification",
                extra_data={"valid": is_valid}
            )
            
            return is_valid
        
        except Exception as e:
            logger.warning(
                f"Signature verification failed",
                extra_data={"error": str(e)}
            )
            return False
    
    def get_public_key_hex(self) -> str:
        """
        Ottieni chiave pubblica in formato hex.
        
        Returns:
            str: Public key hex-encoded
        
        Examples:
            >>> keypair = generate_keypair()
            >>> pub_hex = keypair.get_public_key_hex()
            >>> len(pub_hex) > 0
            True
        """
        return self.public_key.hex()
    
    def get_public_key_bytes(self) -> bytes:
        """
        Ottieni chiave pubblica raw bytes.
        
        Returns:
            bytes: Public key
        """
        return self.public_key
    
    def to_dict(self, include_private: bool = False) -> Dict[str, Any]:
        """
        Serializza keypair in dict.
        
        Args:
            include_private: Se True, include chiave privata (DANGEROUS!)
        
        Returns:
            dict: Serialized keypair
        
        Warning:
            - include_private=True espone chiave privata
            - Usa SOLO per backup criptato
        
        Examples:
            >>> keypair = generate_keypair()
            >>> data = keypair.to_dict(include_private=False)
            >>> 'private_key' in data
            False
            >>> 'public_key' in data
            True
        """
        data = {
            "public_key": self.public_key.hex(),
            "algorithm": SIGNATURE_TYPE,
        }
        
        if include_private:
            logger.warning(
                "⚠️ Exporting private key - ENSURE SECURE STORAGE",
                extra_data={"include_private": True}
            )
            data["private_key"] = self.private_key.hex()
        
        return data
    
    @classmethod
    def from_dict(
        cls,
        data: Dict[str, Any],
        algorithm: str = SIGNATURE_TYPE
    ) -> KeyPair:
        """
        Deserializza keypair da dict.
        
        Args:
            data: Dict con chiavi private/public (hex)
            algorithm: Algoritmo crypto (default da constants)
        
        Returns:
            KeyPair: Instance deserializzata
        
        Raises:
            InvalidKeyError: Se dati invalidi
        
        Examples:
            >>> keypair1 = generate_keypair()
            >>> data = keypair1.to_dict(include_private=True)
            >>> keypair2 = KeyPair.from_dict(data)
            >>> keypair1.public_key == keypair2.public_key
            True
        """
        if "public_key" not in data:
            raise InvalidKeyError(
                "Missing 'public_key' in data",
                code="MISSING_PUBLIC_KEY"
            )
        
        if "private_key" not in data:
            raise InvalidKeyError(
                "Missing 'private_key' in data",
                code="MISSING_PRIVATE_KEY"
            )
        
        try:
            private_key = bytes.fromhex(data["private_key"])
            public_key = bytes.fromhex(data["public_key"])
            
            # Get provider
            provider = get_crypto_provider(algorithm)
            
            return cls(
                private_key=private_key,
                public_key=public_key,
                _provider=provider
            )
        
        except (ValueError, KeyError) as e:
            raise InvalidKeyError(
                f"Failed to deserialize keypair: {e}",
                code="DESERIALIZATION_ERROR"
            )
    
    def __repr__(self) -> str:
        """Safe repr (non espone private key)"""
        pub_key_preview = self.public_key.hex()[:32] + "..."
        return f"KeyPair(public_key={pub_key_preview})"


# ============================================================================
# KEYPAIR GENERATION
# ============================================================================

def generate_keypair(algorithm: str = SIGNATURE_TYPE) -> KeyPair:
    """
    Genera nuova coppia chiavi.
    
    Args:
        algorithm: Algoritmo crypto ("ecdsa", "dilithium", "hybrid")
    
    Returns:
        KeyPair: Nuova keypair
    
    Security:
        - Usa CSPRNG per generazione
        - Chiavi crittograficamente sicure
    
    Examples:
        >>> keypair = generate_keypair()
        >>> isinstance(keypair, KeyPair)
        True
        >>> len(keypair.private_key) > 0
        True
    """
    try:
        # Get crypto provider
        provider = get_crypto_provider(algorithm)
        
        # Generate keypair
        private_key, public_key = provider.generate_keypair()
        
        logger.info(
            "KeyPair generated",
            extra_data={"algorithm": algorithm}
        )
        
        return KeyPair(
            private_key=private_key,
            public_key=public_key,
            _provider=provider
        )
    
    except Exception as e:
        logger.error(
            f"KeyPair generation failed",
            extra_data={"error": str(e), "algorithm": algorithm}
        )
        raise InvalidKeyError(
            f"Failed to generate keypair: {e}",
            code="KEYGEN_FAILED"
        )


def generate_keypair_from_seed(
    seed: bytes,
    algorithm: str = SIGNATURE_TYPE
) -> KeyPair:
    """
    Genera keypair deterministica da seed.
    
    Usato per:
    - HD wallets (derivazione chiavi)
    - Recovery da mnemonic
    
    Args:
        seed: Seed (min 32 bytes)
        algorithm: Algoritmo crypto
    
    Returns:
        KeyPair: Keypair deterministica
    
    Security:
        - Stesso seed → stessa keypair (deterministico)
        - Seed DEVE essere random e segreto
    
    Examples:
        >>> seed = generate_random_bytes(32)
        >>> kp1 = generate_keypair_from_seed(seed)
        >>> kp2 = generate_keypair_from_seed(seed)
        >>> kp1.public_key == kp2.public_key
        True
    """
    if len(seed) < 32:
        raise InvalidKeyError(
            f"Seed too short: {len(seed)} bytes. Minimum: 32 bytes",
            code="SEED_TOO_SHORT"
        )
    
    try:
        # Deriva private key da seed usando PBKDF2
        # (più semplice di BIP32 full implementation)
        private_key_bytes = derive_key_pbkdf2(
            password=seed,
            salt=b"CarbonChain-KeyDerivation",
            iterations=10_000,  # Meno iterazioni (già da seed sicuro)
            key_length=32
        )
        
        # Genera keypair da private key bytes
        # (dipende da algoritmo - ECDSA usa ec.derive_private_key)
        provider = get_crypto_provider(algorithm)
        
        if algorithm == "ecdsa":
            # Import for ECDSA key derivation
            from cryptography.hazmat.primitives.asymmetric import ec
            from cryptography.hazmat.primitives import serialization
            from cryptography.hazmat.backends import default_backend
            
            # Convert bytes to integer
            private_value = int.from_bytes(private_key_bytes, 'big')
            
            # Derive ECDSA private key
            private_key_obj = ec.derive_private_key(
                private_value,
                ec.SECP256K1(),
                default_backend()
            )
            
            # Serialize keys
            private_pem = private_key_obj.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            )
            
            public_key_obj = private_key_obj.public_key()
            public_pem = public_key_obj.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            )
            
            logger.debug("Deterministic keypair generated from seed")
            
            return KeyPair(
                private_key=private_pem,
                public_key=public_pem,
                _provider=provider
            )
        
        else:
            raise NotImplementedError(
                f"Seed-based generation not implemented for {algorithm}"
            )
    
    except Exception as e:
        logger.error(f"Seed-based keygen failed", extra_data={"error": str(e)})
        raise InvalidKeyError(
            f"Failed to generate keypair from seed: {e}",
            code="SEED_KEYGEN_FAILED"
        )


# ============================================================================
# KEYPAIR ENCRYPTION/DECRYPTION
# ============================================================================

def encrypt_keypair(keypair: KeyPair, password: str) -> Dict[str, str]:
    """
    Cripta keypair con password.
    
    Usato per:
    - Wallet storage
    - Backup sicuro
    
    Args:
        keypair: KeyPair da criptare
        password: Password (string)
    
    Returns:
        dict: {
            "encrypted_private": hex,
            "encrypted_public": hex,
            "salt": hex,
            "nonce_private": hex,
            "nonce_public": hex,
            "algorithm": str
        }
    
    Security:
        - Password → key derivation con PBKDF2
        - Encryption con AES-256-GCM
        - Salt random per ogni encryption
    
    Examples:
        >>> keypair = generate_keypair()
        >>> encrypted = encrypt_keypair(keypair, "strong_password")
        >>> 'encrypted_private' in encrypted
        True
    """
    if not password or len(password) < 8:
        raise EncryptionError(
            "Password too weak. Minimum 8 characters.",
            code="WEAK_PASSWORD"
        )
    
    try:
        # Generate random salt
        salt = generate_random_bytes(16)
        
        # Derive encryption key from password
        password_bytes = password.encode('utf-8')
        encryption_key = derive_key_pbkdf2(
            password=password_bytes,
            salt=salt,
            iterations=100_000,  # Strong protection
            key_length=32
        )
        
        # Encrypt private key
        encrypted_private, nonce_private = encrypt_data_aes_gcm(
            plaintext=keypair.private_key,
            key=encryption_key
        )
        
        # Encrypt public key (for consistency, though not secret)
        encrypted_public, nonce_public = encrypt_data_aes_gcm(
            plaintext=keypair.public_key,
            key=encryption_key
        )
        
        logger.info("KeyPair encrypted successfully")
        
        return {
            "encrypted_private": encrypted_private.hex(),
            "encrypted_public": encrypted_public.hex(),
            "salt": salt.hex(),
            "nonce_private": nonce_private.hex(),
            "nonce_public": nonce_public.hex(),
            "algorithm": SIGNATURE_TYPE,
        }
    
    except Exception as e:
        logger.error(f"KeyPair encryption failed", extra_data={"error": str(e)})
        raise EncryptionError(
            f"Failed to encrypt keypair: {e}",
            code="ENCRYPTION_FAILED"
        )


def decrypt_keypair(
    encrypted_data: Dict[str, str],
    password: str,
    algorithm: str = SIGNATURE_TYPE
) -> KeyPair:
    """
    Decripta keypair da dati criptati.
    
    Args:
        encrypted_data: Dict da encrypt_keypair()
        password: Password originale
        algorithm: Algoritmo crypto
    
    Returns:
        KeyPair: Keypair decriptata
    
    Raises:
        DecryptionError: Se password errata o dati corrotti
    
    Examples:
        >>> keypair1 = generate_keypair()
        >>> encrypted = encrypt_keypair(keypair1, "password")
        >>> keypair2 = decrypt_keypair(encrypted, "password")
        >>> keypair1.public_key == keypair2.public_key
        True
    """
    try:
        # Extract data
        encrypted_private = bytes.fromhex(encrypted_data["encrypted_private"])
        encrypted_public = bytes.fromhex(encrypted_data["encrypted_public"])
        salt = bytes.fromhex(encrypted_data["salt"])
        nonce_private = bytes.fromhex(encrypted_data["nonce_private"])
        nonce_public = bytes.fromhex(encrypted_data["nonce_public"])
        
        # Derive key from password
        password_bytes = password.encode('utf-8')
        encryption_key = derive_key_pbkdf2(
            password=password_bytes,
            salt=salt,
            iterations=100_000,
            key_length=32
        )
        
        # Decrypt private key
        private_key = decrypt_data_aes_gcm(
            ciphertext=encrypted_private,
            key=encryption_key,
            nonce=nonce_private
        )
        
        # Decrypt public key
        public_key = decrypt_data_aes_gcm(
            ciphertext=encrypted_public,
            key=encryption_key,
            nonce=nonce_public
        )
        
        # Create keypair
        provider = get_crypto_provider(algorithm)
        
        logger.info("KeyPair decrypted successfully")
        
        return KeyPair(
            private_key=private_key,
            public_key=public_key,
            _provider=provider
        )
    
    except DecryptionError:
        # Re-raise with clearer message
        raise DecryptionError(
            "Failed to decrypt keypair. Wrong password or corrupted data.",
            code="DECRYPTION_FAILED"
        )
    
    except (KeyError, ValueError) as e:
        raise DecryptionError(
            f"Invalid encrypted data format: {e}",
            code="INVALID_ENCRYPTED_FORMAT"
        )
    
    except Exception as e:
        logger.error(f"KeyPair decryption failed", extra_data={"error": str(e)})
        raise DecryptionError(
            f"Unexpected error during decryption: {e}",
            code="DECRYPTION_ERROR"
        )


# ============================================================================
# KEYPAIR VALIDATION
# ============================================================================

def validate_keypair(keypair: KeyPair) -> bool:
    """
    Valida che keypair sia funzionante.
    
    Test:
    1. Sign test message
    2. Verify signature
    3. Check keys non corrotti
    
    Args:
        keypair: KeyPair da validare
    
    Returns:
        bool: True se keypair valida
    
    Examples:
        >>> keypair = generate_keypair()
        >>> validate_keypair(keypair)
        True
    """
    try:
        # Test message
        test_message = b"CarbonChain-KeyPair-Validation-Test"
        
        # Sign
        signature = keypair.sign(test_message)
        
        # Verify
        is_valid = keypair.verify(test_message, signature)
        
        if not is_valid:
            logger.error("KeyPair validation failed: signature verification failed")
            return False
        
        logger.debug("KeyPair validation successful")
        return True
    
    except Exception as e:
        logger.error(
            f"KeyPair validation failed",
            extra_data={"error": str(e)}
        )
        return False


def keypair_matches_public_key(keypair: KeyPair, public_key: bytes) -> bool:
    """
    Verifica che keypair corrisponda a public key.
    
    Args:
        keypair: KeyPair da verificare
        public_key: Public key attesa
    
    Returns:
        bool: True se corrisponde
    
    Examples:
        >>> keypair = generate_keypair()
        >>> keypair_matches_public_key(keypair, keypair.public_key)
        True
    """
    return keypair.public_key == public_key


# ============================================================================
# MULTI-SIGNATURE SUPPORT (Future)
# ============================================================================

@dataclass(frozen=True)
class MultiSigKeyPair:
    """
    Multi-signature keypair (M-of-N).
    
    PLACEHOLDER: Implementazione futura per transazioni multi-firma.
    
    Features (future):
    - M-of-N signatures required
    - Threshold signatures
    - Aggregate signatures (BLS)
    """
    
    keypairs: tuple[KeyPair, ...]
    threshold: int  # M signatures required
    
    def __post_init__(self):
        if self.threshold > len(self.keypairs):
            raise InvalidKeyError(
                f"Threshold {self.threshold} exceeds keypairs count {len(self.keypairs)}"
            )
        
        if self.threshold < 1:
            raise InvalidKeyError("Threshold must be at least 1")
    
    def sign(self, message: bytes, keypair_indices: list[int]) -> list[bytes]:
        """
        Firma con subset di chiavi.
        
        Args:
            message: Message da firmare
            keypair_indices: Indici keypairs da usare (almeno M)
        
        Returns:
            list[bytes]: Lista signatures
        """
        if len(keypair_indices) < self.threshold:
            raise InvalidSignatureError(
                f"Need at least {self.threshold} signatures, got {len(keypair_indices)}"
            )
        
        signatures = []
        for idx in keypair_indices:
            if idx >= len(self.keypairs):
                raise IndexError(f"Invalid keypair index: {idx}")
            
            signature = self.keypairs[idx].sign(message)
            signatures.append(signature)
        
        return signatures
    
    def verify(
        self,
        message: bytes,
        signatures: list[bytes],
        keypair_indices: list[int]
    ) -> bool:
        """Verifica M-of-N signatures"""
        if len(signatures) < self.threshold:
            return False
        
        valid_count = 0
        for idx, signature in zip(keypair_indices, signatures):
            if idx >= len(self.keypairs):
                continue
            
            if self.keypairs[idx].verify(message, signature):
                valid_count += 1
        
        return valid_count >= self.threshold


# ============================================================================
# EXPORT
# ============================================================================

__all__ = [
    # Main class
    "KeyPair",
    
    # Generation
    "generate_keypair",
    "generate_keypair_from_seed",
    
    # Encryption
    "encrypt_keypair",
    "decrypt_keypair",
    
    # Validation
    "validate_keypair",
    "keypair_matches_public_key",
    
    # Multi-sig (future)
    "MultiSigKeyPair",
]
