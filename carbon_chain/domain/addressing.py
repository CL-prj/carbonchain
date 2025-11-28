"""
CarbonChain - Address Generation & Validation
===============================================
Sistema address compatibile Bitcoin (Base58Check).

Security Level: HIGH
Last Updated: 2025-11-27
Version: 1.0.0

Address Format:
- Version byte (1 byte): 0x00 mainnet, 0x6f testnet
- Hash payload (20 bytes): RIPEMD160(SHA256(pubkey))
- Checksum (4 bytes): first 4 bytes of SHA256(SHA256(version+payload))
- Base58 encoding: risultato human-readable

Example Address: 1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa
"""

import re
from typing import Optional

# Internal imports
from carbon_chain.domain.crypto_core import (
    compute_sha256,
    compute_double_sha256,
    compute_ripemd160,
)
from carbon_chain.errors import (
    InvalidAddressError,
    CryptoError,
)
from carbon_chain.logging_setup import get_logger
from carbon_chain.constants import (
    ADDRESS_VERSION_MAINNET,
)


# ============================================================================
# MODULE LOGGER
# ============================================================================

logger = get_logger("addressing")


# ============================================================================
# BASE58 ENCODING/DECODING
# ============================================================================

# Base58 alphabet (no 0, O, I, l per evitare confusione)
BASE58_ALPHABET = '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'


def encode_base58(data: bytes) -> str:
    """
    Encode bytes in Base58.
    
    Base58 è usato per address human-readable senza caratteri ambigui.
    
    Args:
        data: Bytes da encodare
    
    Returns:
        str: Base58 string
    
    Algorithm:
        1. Converti bytes in integer
        2. Dividi per 58 ripetutamente
        3. Mappa remainder su alphabet
        4. Preserva leading zeros come '1'
    
    Examples:
        >>> encode_base58(b'hello')
        'Cn8eVZg'
        >>> encode_base58(b'\\x00\\x00test')
        '11LxG...'  # Leading zeros preserved
    """
    if not data:
        return ''
    
    # Count leading zeros
    leading_zeros = len(data) - len(data.lstrip(b'\x00'))
    
    # Convert bytes to integer
    num = int.from_bytes(data, byteorder='big')
    
    # Convert to base58
    encoded = ''
    while num > 0:
        num, remainder = divmod(num, 58)
        encoded = BASE58_ALPHABET[remainder] + encoded
    
    # Add leading '1' for each leading zero byte
    encoded = '1' * leading_zeros + encoded
    
    return encoded


def decode_base58(encoded: str) -> bytes:
    """
    Decode Base58 string to bytes.
    
    Args:
        encoded: Base58 string
    
    Returns:
        bytes: Decoded bytes
    
    Raises:
        CryptoError: Se caratteri invalidi in string
    
    Examples:
        >>> decode_base58('Cn8eVZg')
        b'hello'
    """
    if not encoded:
        return b''
    
    # Count leading '1's
    leading_ones = len(encoded) - len(encoded.lstrip('1'))
    
    # Convert from base58 to integer
    num = 0
    for char in encoded:
        if char not in BASE58_ALPHABET:
            raise CryptoError(
                f"Invalid Base58 character: {char}",
                code="INVALID_BASE58_CHAR"
            )
        num = num * 58 + BASE58_ALPHABET.index(char)
    
    # Convert integer to bytes
    if num == 0:
        decoded = b'\x00'
    else:
        decoded = num.to_bytes((num.bit_length() + 7) // 8, byteorder='big')
    
    # Add leading zero bytes
    decoded = b'\x00' * leading_ones + decoded
    
    return decoded


def encode_base58_check(payload: bytes) -> str:
    """
    Encode con Base58Check (include checksum).
    
    Base58Check aggiunge checksum per detect errori.
    
    Args:
        payload: Data da encodare (version + hash)
    
    Returns:
        str: Base58Check string
    
    Algorithm:
        1. Compute checksum = SHA256(SHA256(payload))[:4]
        2. Append checksum to payload
        3. Encode in Base58
    
    Examples:
        >>> payload = b'\\x00' + b'\\x01' * 20  # version + hash
        >>> address = encode_base58_check(payload)
        >>> len(address) >= 26  # Typical address length
        True
    """
    # Compute checksum (first 4 bytes of double SHA256)
    checksum = compute_double_sha256(payload)[:4]
    
    # Concatenate payload + checksum
    data_with_checksum = payload + checksum
    
    # Encode in Base58
    return encode_base58(data_with_checksum)


def decode_base58_check(encoded: str) -> bytes:
    """
    Decode Base58Check e verifica checksum.
    
    Args:
        encoded: Base58Check string
    
    Returns:
        bytes: Payload (senza checksum)
    
    Raises:
        CryptoError: Se checksum invalido
    
    Examples:
        >>> payload = b'\\x00' + b'\\x01' * 20
        >>> encoded = encode_base58_check(payload)
        >>> decoded = decode_base58_check(encoded)
        >>> decoded == payload
        True
    """
    # Decode Base58
    decoded = decode_base58(encoded)
    
    if len(decoded) < 5:  # Min: 1 byte version + 4 bytes checksum
        raise CryptoError(
            "Decoded data too short for Base58Check",
            code="INVALID_BASE58CHECK"
        )
    
    # Split payload and checksum
    payload = decoded[:-4]
    checksum = decoded[-4:]
    
    # Verify checksum
    expected_checksum = compute_double_sha256(payload)[:4]
    
    if checksum != expected_checksum:
        raise CryptoError(
            "Base58Check checksum verification failed",
            code="CHECKSUM_MISMATCH",
            details={
                "expected": expected_checksum.hex(),
                "got": checksum.hex()
            }
        )
    
    return payload


# ============================================================================
# ADDRESS GENERATION
# ============================================================================

def public_key_to_address(
    public_key: bytes,
    version: bytes = ADDRESS_VERSION_MAINNET,
    testnet: bool = False
) -> str:
    """
    Genera address blockchain da public key.
    
    Algorithm (Bitcoin-compatible):
        1. SHA-256 hash of public key
        2. RIPEMD-160 hash of result
        3. Add version byte
        4. Base58Check encoding
    
    Args:
        public_key: Public key in PEM or raw format
        version: Version byte (0x00=mainnet, 0x6f=testnet)
        testnet: Se True, usa testnet version
    
    Returns:
        str: Address (26-35 caratteri Base58)
    
    Security:
        - Hash double-layer: SHA-256 → RIPEMD-160
        - Collision-resistant
        - Checksum integrato
    
    Examples:
        >>> from carbon_chain.domain.keypairs import generate_keypair
        >>> keypair = generate_keypair()
        >>> address = public_key_to_address(keypair.public_key)
        >>> len(address) >= 26
        True
        >>> address[0] == '1'  # Mainnet addresses start with '1'
        True
    """
    if not public_key or not isinstance(public_key, bytes):
        raise InvalidAddressError(
            "Invalid public_key: must be non-empty bytes",
            code="INVALID_PUBLIC_KEY"
        )
    
    try:
        # Override version if testnet
        if testnet:
            version = b'\x6f'
        
        # Step 1: SHA-256 hash of public key
        sha256_hash = compute_sha256(public_key)
        
        # Step 2: RIPEMD-160 hash
        ripemd160_hash = compute_ripemd160(sha256_hash)
        
        # Step 3: Add version byte
        versioned_payload = version + ripemd160_hash
        
        # Step 4: Base58Check encoding
        address = encode_base58_check(versioned_payload)
        
        logger.debug(
            "Address generated from public key",
            extra_data={
                "address": address[:16] + "...",
                "version": version.hex()
            }
        )
        
        return address
    
    except Exception as e:
        logger.error(
            f"Address generation failed",
            extra_data={"error": str(e)}
        )
        raise InvalidAddressError(
            f"Failed to generate address: {e}",
            code="ADDRESS_GENERATION_FAILED"
        )


def hash160_to_address(
    hash160: bytes,
    version: bytes = ADDRESS_VERSION_MAINNET
) -> str:
    """
    Genera address da hash160 (RIPEMD160(SHA256(pubkey))).
    
    Args:
        hash160: 20-byte hash
        version: Version byte
    
    Returns:
        str: Address
    
    Examples:
        >>> hash160 = b'\\x01' * 20
        >>> address = hash160_to_address(hash160)
        >>> len(address) >= 26
        True
    """
    if len(hash160) != 20:
        raise InvalidAddressError(
            f"hash160 must be 20 bytes, got {len(hash160)}",
            code="INVALID_HASH160_LENGTH"
        )
    
    versioned_payload = version + hash160
    return encode_base58_check(versioned_payload)


# ============================================================================
# ADDRESS VALIDATION
# ============================================================================

def validate_address(address: str, version: Optional[bytes] = None) -> bool:
    """
    Valida address blockchain.
    
    Checks:
    1. Length (26-35 caratteri)
    2. Base58 valid
    3. Checksum correct
    4. Version byte valid (se specificato)
    
    Args:
        address: Address da validare
        version: Expected version byte (None = accetta tutti)
    
    Returns:
        bool: True se address valido
    
    Examples:
        >>> from carbon_chain.domain.keypairs import generate_keypair
        >>> keypair = generate_keypair()
        >>> addr = public_key_to_address(keypair.public_key)
        >>> validate_address(addr)
        True
        >>> validate_address("invalid")
        False
    """
    try:
        # Check length
        if not (26 <= len(address) <= 35):
            logger.debug(
                f"Address validation failed: invalid length {len(address)}"
            )
            return False
        
        # Check Base58 characters
        if not all(c in BASE58_ALPHABET for c in address):
            logger.debug("Address validation failed: invalid Base58 characters")
            return False
        
        # Decode and verify checksum
        try:
            payload = decode_base58_check(address)
        except CryptoError as e:
            logger.debug(f"Address validation failed: {e}")
            return False
        
        # Check payload length (1 byte version + 20 bytes hash)
        if len(payload) != 21:
            logger.debug(
                f"Address validation failed: invalid payload length {len(payload)}"
            )
            return False
        
        # Check version if specified
        if version is not None:
            address_version = payload[:1]
            if address_version != version:
                logger.debug(
                    f"Address validation failed: version mismatch "
                    f"(expected {version.hex()}, got {address_version.hex()})"
                )
                return False
        
        logger.debug(f"Address validated successfully: {address[:16]}...")
        return True
    
    except Exception as e:
        logger.warning(
            f"Address validation error",
            extra_data={"error": str(e), "address": address[:16]}
        )
        return False


def is_valid_address_format(address: str) -> bool:
    """
    Check rapido formato address (senza decode completo).
    
    Args:
        address: Address da verificare
    
    Returns:
        bool: True se formato plausibile
    
    Examples:
        >>> is_valid_address_format("1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa")
        True
        >>> is_valid_address_format("invalid_address")
        False
    """
    # Regex pattern per address Base58
    pattern = r'^[1-9A-HJ-NP-Za-km-z]{26,35}$'
    return bool(re.match(pattern, address))


def get_address_version(address: str) -> Optional[bytes]:
    """
    Estrai version byte da address.
    
    Args:
        address: Address valido
    
    Returns:
        bytes: Version byte, o None se address invalido
    
    Examples:
        >>> addr = "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"
        >>> version = get_address_version(addr)
        >>> version == b'\\x00'  # Mainnet
        True
    """
    try:
        payload = decode_base58_check(address)
        return payload[:1]
    except:
        return None


def is_mainnet_address(address: str) -> bool:
    """
    Check se address è mainnet.
    
    Args:
        address: Address da verificare
    
    Returns:
        bool: True se mainnet
    
    Examples:
        >>> is_mainnet_address("1...")  # Mainnet addresses start with '1'
        True
    """
    version = get_address_version(address)
    return version == ADDRESS_VERSION_MAINNET if version else False


def is_testnet_address(address: str) -> bool:
    """
    Check se address è testnet.
    
    Args:
        address: Address da verificare
    
    Returns:
        bool: True se testnet
    """
    version = get_address_version(address)
    return version == b'\x6f' if version else False


# ============================================================================
# ADDRESS UTILITIES
# ============================================================================

def normalize_address(address: str) -> str:
    """
    Normalizza address (trim, lowercase check).
    
    Args:
        address: Address da normalizzare
    
    Returns:
        str: Address normalizzato
    
    Note:
        Base58 è case-sensitive, questa funzione solo trim whitespace
    """
    return address.strip()


def compare_addresses(addr1: str, addr2: str) -> bool:
    """
    Confronta due address (case-sensitive).
    
    Args:
        addr1, addr2: Address da confrontare
    
    Returns:
        bool: True se uguali
    
    Examples:
        >>> addr = "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"
        >>> compare_addresses(addr, addr)
        True
    """
    return normalize_address(addr1) == normalize_address(addr2)


# ============================================================================
# EXPORT
# ============================================================================

__all__ = [
    # Base58
    "encode_base58",
    "decode_base58",
    "encode_base58_check",
    "decode_base58_check",
    
    # Address generation
    "public_key_to_address",
    "hash160_to_address",
    
    # Validation
    "validate_address",
    "is_valid_address_format",
    "get_address_version",
    "is_mainnet_address",
    "is_testnet_address",
    
    # Utilities
    "normalize_address",
    "compare_addresses",
]
