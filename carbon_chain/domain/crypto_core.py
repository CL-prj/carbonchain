"""
CarbonChain - Cryptographic Core Layer
========================================
Layer crittografico di basso livello per blockchain.

Security Level: CRITICAL
Last Updated: 2025-11-26
Version: 1.0.0

SECURITY NOTICE:
Questo modulo implementa primitive crittografiche critiche.
Ogni modifica deve essere sottoposta a security audit.

Algorithms:
- Hash: SHA-256, BLAKE2b, RIPEMD-160
- Signature: ECDSA (secp256k1), Dilithium (future)
- KDF: PBKDF2, scrypt
- Encryption: AES-256-GCM

Dependencies:
- cryptography (>=41.0.0)
- hashlib (stdlib)
"""

import hashlib
import hmac
import secrets
from typing import Optional, Tuple, Protocol
from abc import ABC, abstractmethod
from dataclasses import dataclass

# Cryptography library (production-grade)
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend
from cryptography.exceptions import InvalidSignature as CryptoInvalidSignature

# Internal imports
from carbon_chain.errors import (
    CryptoError,
    InvalidKeyError,
    InvalidSignatureError,
    EncryptionError,
    DecryptionError,
    HashMismatchError
)
from carbon_chain.logging_setup import get_logger


# ============================================================================
# MODULE LOGGER
# ============================================================================

logger = get_logger("crypto")


# ============================================================================
# HASH FUNCTIONS
# ============================================================================

def compute_sha256(data: bytes) -> bytes:
    """
    Compute SHA-256 hash.
    
    SHA-256 è l'hash primario per:
    - Block hashes
    - Transaction IDs
    - Merkle trees
    
    Args:
        data: Input data da hashare
    
    Returns:
        bytes: 32-byte hash digest
    
    Security:
        - Collision-resistant
        - Pre-image resistant
        - Second pre-image resistant
    
    Examples:
        >>> compute_sha256(b"CarbonChain")
        b'\\x8a\\x9f...'  # 32 bytes
        >>> compute_sha256(b"").hex()
        'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'
    """
    if not isinstance(data, bytes):
        raise CryptoError(
            f"compute_sha256 requires bytes, got {type(data).__name__}",
            code="INVALID_INPUT_TYPE"
        )
    
    try:
        return hashlib.sha256(data).digest()
    except Exception as e:
        logger.error(f"SHA-256 computation failed", extra_data={"error": str(e)})
        raise CryptoError(f"SHA-256 hash failed: {e}", code="HASH_ERROR")


def compute_double_sha256(data: bytes) -> bytes:
    """
    Compute double SHA-256 (SHA256(SHA256(data))).
    
    Usato per:
    - Address checksums (compatibilità Bitcoin)
    - Extra security layer
    
    Args:
        data: Input data
    
    Returns:
        bytes: 32-byte double hash
    
    Examples:
        >>> compute_double_sha256(b"test")
        b'\\x95\\x4d...'
    """
    return compute_sha256(compute_sha256(data))


def compute_blake2b(
    data: bytes,
    digest_size: int = 32,
    key: Optional[bytes] = None,
    salt: Optional[bytes] = None
) -> bytes:
    """
    Compute BLAKE2b hash.
    
    BLAKE2b è più veloce di SHA-256 e usato per:
    - Certificate hashes (deterministic, no collisions)
    - Internal hashing non-consensus
    
    Args:
        data: Input data
        digest_size: Output size in bytes (1-64, default 32)
        key: Optional key per keyed hashing
        salt: Optional salt per personalizzazione
    
    Returns:
        bytes: Hash digest
    
    Security:
        - Più veloce di SHA-256 (~2x)
        - Stesso livello sicurezza
        - Keyed mode per HMAC-like
    
    Examples:
        >>> compute_blake2b(b"CarbonChain")
        b'\\x1a\\x2b...'  # 32 bytes default
        >>> compute_blake2b(b"data", digest_size=16)
        b'\\xfe\\x8c...'  # 16 bytes
    """
    if not isinstance(data, bytes):
        raise CryptoError("compute_blake2b requires bytes input")
    
    if not (1 <= digest_size <= 64):
        raise CryptoError(
            f"Invalid digest_size: {digest_size}. Must be 1-64",
            code="INVALID_DIGEST_SIZE"
        )
    
    try:
        return hashlib.blake2b(
            data,
            digest_size=digest_size,
            key=key or b'',
            salt=salt or b''
        ).digest()
    except Exception as e:
        logger.error(f"BLAKE2b computation failed", extra_data={"error": str(e)})
        raise CryptoError(f"BLAKE2b hash failed: {e}", code="HASH_ERROR")


def compute_ripemd160(data: bytes) -> bytes:
    """
    Compute RIPEMD-160 hash.
    
    Usato per:
    - Address generation (compatibilità Bitcoin: SHA256 → RIPEMD160)
    
    Args:
        data: Input data
    
    Returns:
        bytes: 20-byte hash
    
    Note:
        RIPEMD-160 non disponibile su tutte le piattaforme.
        Fallback a SHA-256 troncato se non disponibile.
    
    Examples:
        >>> compute_ripemd160(b"CarbonChain")
        b'\\x9a\\x8c...'  # 20 bytes
    """
    if not isinstance(data, bytes):
        raise CryptoError("compute_ripemd160 requires bytes input")
    
    try:
        # Try native ripemd160
        return hashlib.new('ripemd160', data).digest()
    except ValueError:
        # Fallback: SHA-256 truncated to 20 bytes
        logger.warning(
            "RIPEMD-160 not available, using SHA-256 truncated fallback",
            extra_data={"platform": "unsupported"}
        )
        return compute_sha256(data)[:20]


def compute_certificate_hash(
    cert_id: str,
    total_kg: int,
    location: str,
    description: str,
    timestamp: int,
    issuer: str = "",
    extra_data: Optional[dict] = None
) -> bytes:
    """
    Compute deterministic hash per certificato CO2.
    
    Questo hash è CRITICO per prevenire certificati duplicati.
    DEVE essere deterministico: stesso input → stesso hash.
    
    Args:
        cert_id: ID certificato
        total_kg: Capacità totale kg CO2
        location: Località progetto
        description: Descrizione progetto
        timestamp: Timestamp emissione
        issuer: Ente emettitore
        extra_data: Metadata addizionali (opzionale)
    
    Returns:
        bytes: 32-byte deterministic hash
    
    Algorithm:
        1. Crea stringa canonica ordinata
        2. Hash con BLAKE2b (veloce + sicuro)
    
    Security:
        - Deterministico
        - Collision-resistant
        - Immutabile
    
    Examples:
        >>> compute_certificate_hash(
        ...     "CERT-001", 1000, "Portugal", "Solar Farm", 1700000000
        ... )
        b'\\xa1\\xb2...'
        
        # Stesso input → stesso hash
        >>> h1 = compute_certificate_hash("C1", 100, "PT", "Test", 123)
        >>> h2 = compute_certificate_hash("C1", 100, "PT", "Test", 123)
        >>> h1 == h2
        True
    """
    # Validazione input
    if not cert_id or not isinstance(cert_id, str):
        raise CryptoError("Invalid cert_id", code="INVALID_CERT_ID")
    
    if total_kg <= 0:
        raise CryptoError("total_kg must be positive", code="INVALID_TOTAL_KG")
    
    if timestamp <= 0:
        raise CryptoError("Invalid timestamp", code="INVALID_TIMESTAMP")
    
    # Costruisci stringa canonica
    # Ordine DEVE essere fisso per determinismo
    canonical_parts = [
        f"cert_id:{cert_id}",
        f"total_kg:{total_kg}",
        f"location:{location}",
        f"description:{description}",
        f"timestamp:{timestamp}",
        f"issuer:{issuer}",
    ]
    
    # Aggiungi extra_data ordinato
    if extra_data:
        # Sort keys per determinismo
        sorted_extra = sorted(extra_data.items())
        for key, value in sorted_extra:
            canonical_parts.append(f"{key}:{value}")
    
    # Join con separatore
    canonical_string = "|".join(canonical_parts)
    
    # Hash con BLAKE2b (più veloce di SHA-256)
    cert_hash = compute_blake2b(canonical_string.encode('utf-8'), digest_size=32)
    
    logger.debug(
        "Certificate hash computed",
        extra_data={
            "cert_id": cert_id,
            "hash": cert_hash.hex()[:16] + "...",
            "canonical_length": len(canonical_string)
        }
    )
    
    return cert_hash


def verify_certificate_hash(
    cert_hash: bytes,
    cert_id: str,
    total_kg: int,
    location: str,
    description: str,
    timestamp: int,
    issuer: str = "",
    extra_data: Optional[dict] = None
) -> bool:
    """
    Verifica che certificate hash corrisponda ai dati.
    
    Args:
        cert_hash: Hash da verificare
        ...: Parametri certificato
    
    Returns:
        bool: True se hash valido
    
    Raises:
        HashMismatchError: Se hash non corrisponde
    
    Examples:
        >>> cert_hash = compute_certificate_hash("C1", 100, "PT", "Test", 123)
        >>> verify_certificate_hash(cert_hash, "C1", 100, "PT", "Test", 123)
        True
    """
    computed = compute_certificate_hash(
        cert_id, total_kg, location, description, timestamp, issuer, extra_data
    )
    
    if computed != cert_hash:
        raise HashMismatchError(
            "Certificate hash mismatch",
            code="CERT_HASH_MISMATCH",
            details={
                "provided_hash": cert_hash.hex()[:16],
                "computed_hash": computed.hex()[:16]
            }
        )
    
    return True


# ============================================================================
# KEY DERIVATION FUNCTIONS
# ============================================================================

def derive_key_pbkdf2(
    password: bytes,
    salt: bytes,
    iterations: int = 100_000,
    key_length: int = 32
) -> bytes:
    """
    Deriva chiave da password usando PBKDF2-HMAC-SHA256.
    
    Usato per:
    - Wallet encryption
    - Key stretching
    
    Args:
        password: Password in bytes
        salt: Salt casuale (min 16 bytes)
        iterations: Numero iterazioni (default 100k)
        key_length: Lunghezza chiave output (bytes)
    
    Returns:
        bytes: Derived key
    
    Security:
        - 100k iterations = ~100ms su CPU moderne
        - Salt DEVE essere casuale e unico
        - Non riusare salt
    
    Examples:
        >>> salt = secrets.token_bytes(16)
        >>> key = derive_key_pbkdf2(b"password123", salt)
        >>> len(key)
        32
    """
    if len(salt) < 16:
        raise CryptoError("Salt must be at least 16 bytes", code="SALT_TOO_SHORT")
    
    if iterations < 10_000:
        logger.warning(
            f"Low PBKDF2 iterations: {iterations}. Recommended: 100k+",
            extra_data={"iterations": iterations}
        )
    
    try:
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=key_length,
            salt=salt,
            iterations=iterations,
            backend=default_backend()
        )
        return kdf.derive(password)
    except Exception as e:
        raise CryptoError(f"PBKDF2 derivation failed: {e}", code="KDF_ERROR")


def derive_key_scrypt(
    password: bytes,
    salt: bytes,
    n: int = 2**15,
    r: int = 8,
    p: int = 1,
    key_length: int = 32
) -> bytes:
    """
    Deriva chiave usando scrypt (memory-hard KDF).
    
    Scrypt è più sicuro di PBKDF2 contro hardware specializzato.
    
    Args:
        password: Password
        salt: Salt (min 16 bytes)
        n: CPU/memory cost parameter (2^15 = 32768)
        r: Block size
        p: Parallelization
        key_length: Output key length
    
    Returns:
        bytes: Derived key
    
    Security:
        - Memory-hard: resiste a GPU/ASIC
        - Più lento di PBKDF2 (intenzionale)
    
    Examples:
        >>> salt = secrets.token_bytes(16)
        >>> key = derive_key_scrypt(b"password", salt)
        >>> len(key)
        32
    """
    if len(salt) < 16:
        raise CryptoError("Salt must be at least 16 bytes")
    
    try:
        import scrypt as scrypt_lib
        
        return scrypt_lib.hash(
            password=password,
            salt=salt,
            N=n,
            r=r,
            p=p,
            buflen=key_length
        )
    except ImportError:
        logger.error("scrypt library not available, falling back to PBKDF2")
        return derive_key_pbkdf2(password, salt, iterations=100_000, key_length=key_length)
    except Exception as e:
        raise CryptoError(f"Scrypt derivation failed: {e}", code="KDF_ERROR")


# ============================================================================
# SYMMETRIC ENCRYPTION (AES-256-GCM)
# ============================================================================

def encrypt_data_aes_gcm(
    plaintext: bytes,
    key: bytes,
    associated_data: Optional[bytes] = None
) -> Tuple[bytes, bytes]:
    """
    Encrypta data con AES-256-GCM (authenticated encryption).
    
    AES-GCM fornisce:
    - Confidentiality (encryption)
    - Authenticity (MAC integrato)
    - Associated data support
    
    Args:
        plaintext: Dati da criptare
        key: Chiave 256-bit (32 bytes)
        associated_data: Dati addizionali autenticati ma non criptati
    
    Returns:
        tuple: (ciphertext, nonce)
            - ciphertext include authentication tag (16 bytes extra)
            - nonce: 12 bytes (salvare per decrypt)
    
    Security:
        - Nonce DEVE essere unico per ogni encryption con stessa chiave
        - Key DEVE essere random (32 bytes)
        - GCM autentica ciphertext (detect tampering)
    
    Examples:
        >>> key = secrets.token_bytes(32)
        >>> ciphertext, nonce = encrypt_data_aes_gcm(b"secret", key)
        >>> len(nonce)
        12
    """
    if len(key) != 32:
        raise CryptoError(
            f"AES-256 requires 32-byte key, got {len(key)}",
            code="INVALID_KEY_LENGTH"
        )
    
    try:
        # Generate random nonce (96 bits = 12 bytes for GCM)
        nonce = secrets.token_bytes(12)
        
        # Create cipher
        aesgcm = AESGCM(key)
        
        # Encrypt (returns ciphertext + 16-byte auth tag)
        ciphertext = aesgcm.encrypt(
            nonce,
            plaintext,
            associated_data
        )
        
        logger.debug(
            "Data encrypted with AES-GCM",
            extra_data={
                "plaintext_size": len(plaintext),
                "ciphertext_size": len(ciphertext)
            }
        )
        
        return (ciphertext, nonce)
    
    except Exception as e:
        raise EncryptionError(f"AES-GCM encryption failed: {e}", code="ENCRYPT_ERROR")


def decrypt_data_aes_gcm(
    ciphertext: bytes,
    key: bytes,
    nonce: bytes,
    associated_data: Optional[bytes] = None
) -> bytes:
    """
    Decrypta data AES-256-GCM.
    
    Args:
        ciphertext: Ciphertext da decrypt (include auth tag)
        key: Chiave 256-bit (32 bytes)
        nonce: Nonce usato per encrypt (12 bytes)
        associated_data: Associated data (se usato in encrypt)
    
    Returns:
        bytes: Plaintext decriptato
    
    Raises:
        DecryptionError: Se decrypt fallisce o auth tag invalido
    
    Security:
        - Verifica automatica auth tag
        - Se tag invalido = data corrotta/manomessa
    
    Examples:
        >>> key = secrets.token_bytes(32)
        >>> ciphertext, nonce = encrypt_data_aes_gcm(b"secret", key)
        >>> plaintext = decrypt_data_aes_gcm(ciphertext, key, nonce)
        >>> plaintext
        b'secret'
    """
    if len(key) != 32:
        raise CryptoError(f"AES-256 requires 32-byte key, got {len(key)}")
    
    if len(nonce) != 12:
        raise CryptoError(f"GCM requires 12-byte nonce, got {len(nonce)}")
    
    try:
        aesgcm = AESGCM(key)
        
        # Decrypt + verify auth tag
        plaintext = aesgcm.decrypt(
            nonce,
            ciphertext,
            associated_data
        )
        
        logger.debug(
            "Data decrypted with AES-GCM",
            extra_data={"plaintext_size": len(plaintext)}
        )
        
        return plaintext
    
    except CryptoInvalidSignature:
        raise DecryptionError(
            "Authentication tag verification failed. Data may be corrupted or tampered.",
            code="AUTH_TAG_INVALID"
        )
    except Exception as e:
        raise DecryptionError(f"AES-GCM decryption failed: {e}", code="DECRYPT_ERROR")


# ============================================================================
# CRYPTO PROVIDER PROTOCOL
# ============================================================================

class CryptoProvider(Protocol):
    """
    Protocol per provider crittografici.
    
    Permette supporto multi-algorithm:
    - ECDSA (attuale)
    - Dilithium (post-quantum, futuro)
    - Hybrid (doppia firma)
    """
    
    @abstractmethod
    def generate_keypair(self) -> Tuple[bytes, bytes]:
        """
        Genera coppia chiavi.
        
        Returns:
            tuple: (private_key, public_key) in formato serializzato
        """
        pass
    
    @abstractmethod
    def sign(self, message: bytes, private_key: bytes) -> bytes:
        """
        Firma messaggio.
        
        Args:
            message: Messaggio da firmare
            private_key: Chiave privata
        
        Returns:
            bytes: Firma
        """
        pass
    
    @abstractmethod
    def verify(self, message: bytes, signature: bytes, public_key: bytes) -> bool:
        """
        Verifica firma.
        
        Args:
            message: Messaggio originale
            signature: Firma da verificare
            public_key: Chiave pubblica
        
        Returns:
            bool: True se firma valida
        """
        pass


# ============================================================================
# ECDSA PROVIDER (secp256k1)
# ============================================================================

class ECDSAProvider:
    """
    Provider ECDSA con curva secp256k1 (compatibile Bitcoin).
    
    Features:
    - Curve: secp256k1 (standard Bitcoin)
    - Hash: SHA-256
    - Signature: DER encoded
    - Key format: PEM
    
    Security:
        - 256-bit security level
        - Widely audited
        - Hardware acceleration support
    """
    
    def __init__(self):
        self.curve = ec.SECP256K1()
        self.hash_algo = hashes.SHA256()
    
    def generate_keypair(self) -> Tuple[bytes, bytes]:
        """
        Genera keypair ECDSA.
        
        Returns:
            tuple: (private_key_pem, public_key_pem)
        
        Security:
            - Private key: 256-bit random
            - Usa CSPRNG (Cryptographically Secure Pseudo-Random Number Generator)
        
        Examples:
            >>> provider = ECDSAProvider()
            >>> private_key, public_key = provider.generate_keypair()
            >>> len(private_key) > 0
            True
        """
        try:
            # Generate private key
            private_key_obj = ec.generate_private_key(
                self.curve,
                backend=default_backend()
            )
            
            # Serialize private key (PEM format)
            private_pem = private_key_obj.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            )
            
            # Get public key
            public_key_obj = private_key_obj.public_key()
            
            # Serialize public key (PEM format)
            public_pem = public_key_obj.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            )
            
            logger.debug("ECDSA keypair generated")
            
            return (private_pem, public_pem)
        
        except Exception as e:
            raise CryptoError(f"ECDSA keypair generation failed: {e}", code="KEYGEN_ERROR")
    
    def sign(self, message: bytes, private_key: bytes) -> bytes:
        """
        Firma messaggio con ECDSA.
        
        Args:
            message: Messaggio da firmare
            private_key: Private key in formato PEM
        
        Returns:
            bytes: Firma DER-encoded
        
        Examples:
            >>> provider = ECDSAProvider()
            >>> priv, pub = provider.generate_keypair()
            >>> signature = provider.sign(b"message", priv)
            >>> len(signature) > 0
            True
        """
        try:
            # Load private key
            private_key_obj = serialization.load_pem_private_key(
                private_key,
                password=None,
                backend=default_backend()
            )
            
            # Sign
            signature = private_key_obj.sign(
                message,
                ec.ECDSA(self.hash_algo)
            )
            
            logger.debug(
                "Message signed with ECDSA",
                extra_data={"message_size": len(message), "signature_size": len(signature)}
            )
            
            return signature
        
        except Exception as e:
            raise InvalidKeyError(f"ECDSA signing failed: {e}", code="SIGN_ERROR")
    
    def verify(self, message: bytes, signature: bytes, public_key: bytes) -> bool:
        """
        Verifica firma ECDSA.
        
        Args:
            message: Messaggio originale
            signature: Firma da verificare
            public_key: Public key in formato PEM
        
        Returns:
            bool: True se firma valida, False altrimenti
        
        Examples:
            >>> provider = ECDSAProvider()
            >>> priv, pub = provider.generate_keypair()
            >>> sig = provider.sign(b"test", priv)
            >>> provider.verify(b"test", sig, pub)
            True
            >>> provider.verify(b"wrong", sig, pub)
            False
        """
        try:
            # Load public key
            public_key_obj = serialization.load_pem_public_key(
                public_key,
                backend=default_backend()
            )
            
            # Verify
            public_key_obj.verify(
                signature,
                message,
                ec.ECDSA(self.hash_algo)
            )
            
            logger.debug("ECDSA signature verified successfully")
            return True
        
        except CryptoInvalidSignature:
            logger.debug("ECDSA signature verification failed: invalid signature")
            return False
        
        except Exception as e:
            logger.error(f"ECDSA verification error: {e}")
            return False


# ============================================================================
# POST-QUANTUM PROVIDER (Dilithium - Placeholder)
# ============================================================================

class DilithiumProvider:
    """
    Provider Dilithium (post-quantum signature).
    
    PLACEHOLDER: Implementazione futura quando liboqs-python sarà stabile su ARM.
    
    Dilithium:
    - NIST PQC Standard (2024)
    - Lattice-based signature
    - Quantum-resistant
    """
    
    def generate_keypair(self) -> Tuple[bytes, bytes]:
        raise NotImplementedError(
            "Dilithium support coming in v2.0. "
            "Install liboqs-python when available for ARM64."
        )
    
    def sign(self, message: bytes, private_key: bytes) -> bytes:
        raise NotImplementedError("Dilithium not yet implemented")
    
    def verify(self, message: bytes, signature: bytes, public_key: bytes) -> bool:
        raise NotImplementedError("Dilithium not yet implemented")


# ============================================================================
# PROVIDER FACTORY
# ============================================================================

def get_crypto_provider(algorithm: str = "ecdsa") -> CryptoProvider:
    """
    Factory per ottenere crypto provider.
    
    Args:
        algorithm: Algoritmo ("ecdsa", "dilithium", "hybrid")
    
    Returns:
        CryptoProvider: Provider instance
    
    Raises:
        CryptoError: Se algorithm non supportato
    
    Examples:
        >>> provider = get_crypto_provider("ecdsa")
        >>> isinstance(provider, ECDSAProvider)
        True
    """
    algorithm = algorithm.lower()
    
    if algorithm == "ecdsa":
        return ECDSAProvider()
    
    elif algorithm == "dilithium":
        return DilithiumProvider()
    
    elif algorithm == "hybrid":
        raise NotImplementedError("Hybrid signatures coming in v2.0")
    
    else:
        raise CryptoError(
            f"Unsupported crypto algorithm: {algorithm}",
            code="UNSUPPORTED_ALGORITHM",
            details={"supported": ["ecdsa", "dilithium", "hybrid"]}
        )


# ============================================================================
# RANDOM NUMBER GENERATION
# ============================================================================

def generate_random_bytes(length: int) -> bytes:
    """
    Genera bytes casuali crittograficamente sicuri.
    
    Usa secrets module (CSPRNG).
    
    Args:
        length: Numero bytes da generare
    
    Returns:
        bytes: Random bytes
    
    Security:
        - Usa CSPRNG del sistema operativo
        - Adatto per chiavi, nonce, salt
    
    Examples:
        >>> random_bytes = generate_random_bytes(32)
        >>> len(random_bytes)
        32
    """
    if length <= 0:
        raise CryptoError("Length must be positive")
    
    return secrets.token_bytes(length)


def generate_random_int(min_value: int, max_value: int) -> int:
    """
    Genera intero casuale sicuro.
    
    Args:
        min_value: Valore minimo (inclusive)
        max_value: Valore massimo (inclusive)
    
    Returns:
        int: Random integer
    
    Examples:
        >>> num = generate_random_int(1, 100)
        >>> 1 <= num <= 100
        True
    """
    return secrets.randbelow(max_value - min_value + 1) + min_value


# ============================================================================
# PROOF OF WORK HASH
# ============================================================================

def compute_pow_hash_scrypt(header_bytes: bytes, nonce: int) -> bytes:
    """
    Compute PoW hash usando Scrypt.
    
    Usato per mining: trova nonce tale che hash < target difficulty.
    
    Args:
        header_bytes: Serialized block header
        nonce: Nonce da testare
    
    Returns:
        bytes: 32-byte hash
    
    Algorithm:
        1. Concatena header + nonce (8 byte big-endian)
        2. Hash con Scrypt (N=32768, r=8, p=1)
        3. Return digest
    
    Security:
        - Memory-hard: resiste a ASIC
        - CPU-friendly: mining decentralizzato
    
    Examples:
        >>> header = b"block_header_data"
        >>> digest = compute_pow_hash_scrypt(header, 12345)
        >>> len(digest)
        32
    """
    # Concatena header + nonce
    nonce_bytes = nonce.to_bytes(8, byteorder='big')
    data = header_bytes + nonce_bytes
    
    # Scrypt parameters (ASIC-resistant)
    N = 2**15  # 32768 (memory cost)
    r = 8      # Block size
    p = 1      # Parallelization
    
    try:
        # Use scrypt as KDF (data = password, salt = data stesso)
        pow_hash = derive_key_scrypt(
            password=data,
            salt=data,  # Self-salted
            n=N,
            r=r,
            p=p,
            key_length=32
        )
        
        return pow_hash
    
    except Exception as e:
        logger.error(f"PoW hash computation failed", extra_data={"error": str(e)})
        raise CryptoError(f"PoW hash failed: {e}", code="POW_HASH_ERROR")


def check_pow_difficulty(digest: bytes, difficulty: int) -> bool:
    """
    Verifica che hash soddisfi difficulty target.
    
    Difficulty = numero di byte zero iniziali richiesti.
    
    Args:
        digest: Hash da verificare
        difficulty: Numero byte zero richiesti (1-32)
    
    Returns:
        bool: True se hash valido per difficulty
    
    Algorithm:
        - Difficulty 1: primo byte = 0x00
        - Difficulty 2: primi 2 byte = 0x00
        - Difficulty 4: primi 4 byte = 0x00
        - ...
    
    Examples:
        >>> # Hash con 2 byte zero iniziali
        >>> digest = bytes([0, 0, 123, 45])
        >>> check_pow_difficulty(digest, 1)
        True
        >>> check_pow_difficulty(digest, 2)
        True
        >>> check_pow_difficulty(digest, 3)
        False
    """
    if difficulty <= 0 or difficulty > 32:
        raise CryptoError(
            f"Invalid difficulty: {difficulty}. Must be 1-32",
            code="INVALID_DIFFICULTY"
        )
    
    # Check primi N byte siano zero
    for i in range(difficulty):
        if digest[i] != 0:
            return False
    
    return True


# ============================================================================
# HMAC
# ============================================================================

def compute_hmac_sha256(key: bytes, message: bytes) -> bytes:
    """
    Compute HMAC-SHA256.
    
    Usato per:
    - Message authentication
    - Key derivation
    
    Args:
        key: HMAC key
        message: Message da autenticare
    
    Returns:
        bytes: 32-byte HMAC
    
    Security:
        - Key DEVE essere random
        - HMAC previene length extension attacks
    
    Examples:
        >>> key = secrets.token_bytes(32)
        >>> mac = compute_hmac_sha256(key, b"message")
        >>> len(mac)
        32
    """
    if not key:
        raise CryptoError("HMAC key cannot be empty")
    
    try:
        return hmac.new(key, message, hashlib.sha256).digest()
    except Exception as e:
        raise CryptoError(f"HMAC computation failed: {e}")


def verify_hmac(key: bytes, message: bytes, expected_hmac: bytes) -> bool:
    """
    Verifica HMAC (constant-time comparison).
    
    Args:
        key: HMAC key
        message: Message
        expected_hmac: HMAC da verificare
    
    Returns:
        bool: True se HMAC valido
    """
    computed = compute_hmac_sha256(key, message)
    
    # Constant-time comparison (prevent timing attacks)
    return hmac.compare_digest(computed, expected_hmac)

def generate_keypair(algorithm: str = "ecdsa") -> Tuple[bytes, bytes]:
    """
    Genera keypair usando provider specificato.
    
    Convenience function per generazione keypair senza dover creare provider.
    
    Args:
        algorithm: Algoritmo ("ecdsa", "dilithium", "hybrid")
    
    Returns:
        tuple: (private_key, public_key) in formato serializzato
    
    Examples:
        >>> private_key, public_key = generate_keypair()
        >>> len(private_key) > 0
        True
        >>> len(public_key) > 0
        True
    """
    provider = get_crypto_provider(algorithm)
    return provider.generate_keypair()


def sign_message(
    message: bytes,
    private_key: bytes,
    algorithm: str = "ecdsa"
) -> bytes:
    """
    Firma messaggio usando provider specificato.
    
    Args:
        message: Messaggio da firmare
        private_key: Chiave privata
        algorithm: Algoritmo
    
    Returns:
        bytes: Firma
    
    Examples:
        >>> priv, pub = generate_keypair()
        >>> signature = sign_message(b"test", priv)
        >>> len(signature) > 0
        True
    """
    provider = get_crypto_provider(algorithm)
    return provider.sign(message, private_key)


def verify_signature(
    message: bytes,
    signature: bytes,
    public_key: bytes,
    algorithm: str = "ecdsa"
) -> bool:
    """
    Verifica firma usando provider specificato.
    
    Args:
        message: Messaggio originale
        signature: Firma da verificare
        public_key: Chiave pubblica
        algorithm: Algoritmo
    
    Returns:
        bool: True se firma valida
    
    Examples:
        >>> priv, pub = generate_keypair()
        >>> sig = sign_message(b"test", priv)
        >>> verify_signature(b"test", sig, pub)
        True
    """
    provider = get_crypto_provider(algorithm)
    return provider.verify(message, signature, public_key)

# ============================================================================
# ALIASES (Per compatibilità)
# ============================================================================

# Alias per nomi alternativi
hash_sha256 = compute_sha256
hash_blake2b = compute_blake2b
hash_ripemd160 = compute_ripemd160

# ============================================================================
# EXPORT
# ============================================================================


__all__ = [
    # Hash functions
    "compute_sha256",
    "compute_double_sha256",
    "compute_blake2b",
    "compute_ripemd160",
    "compute_certificate_hash",
    "verify_certificate_hash",
    
    # Hash aliases (per compatibilità)
    "hash_sha256",      
    "hash_blake2b",      
    "hash_ripemd160", 

    # KDF
    "derive_key_pbkdf2",
    "derive_key_scrypt",
    
    # Symmetric encryption
    "encrypt_data_aes_gcm",
    "decrypt_data_aes_gcm",
    
    # Crypto providers
    "CryptoProvider",
    "ECDSAProvider",
    "DilithiumProvider",
    "get_crypto_provider",
    
    # Convenience functions 
    "generate_keypair",
    "sign_message",
    "verify_signature",
    
    # Random
    "generate_random_bytes",
    "generate_random_int",
    
    # PoW
    "compute_pow_hash_scrypt",
    "check_pow_difficulty",
    
    # HMAC
    "compute_hmac_sha256",
    "verify_hmac",
]
