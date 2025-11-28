"""
CarbonChain - Base58 Encoding
===============================
Base58 and Base58Check encoding (Bitcoin-style).
"""

import hashlib
from typing import Union

from carbon_chain.errors import ValidationError
from carbon_chain.logging_setup import get_logger

logger = get_logger("utils.base58")


# ============================================================================
# BASE58 ALPHABET
# ============================================================================

# Bitcoin Base58 alphabet (no 0, O, I, l to avoid confusion)
BASE58_ALPHABET = '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'


# ============================================================================
# BASE58 ENCODING
# ============================================================================

def base58_encode(data: bytes) -> str:
    """
    Encode bytes to Base58 string.
    
    Args:
        data: Bytes to encode
    
    Returns:
        str: Base58 string
    
    Examples:
        >>> base58_encode(b"hello")
        'Cn8eVZg'
    """
    # Convert bytes to integer
    num = int.from_bytes(data, byteorder='big')
    
    # Encode to base58
    encoded = ''
    while num > 0:
        num, remainder = divmod(num, 58)
        encoded = BASE58_ALPHABET[remainder] + encoded
    
    # Preserve leading zeros
    for byte in data:
        if byte == 0:
            encoded = '1' + encoded
        else:
            break
    
    return encoded or '1'


def base58_decode(encoded: str) -> bytes:
    """
    Decode Base58 string to bytes.
    
    Args:
        encoded: Base58 string
    
    Returns:
        bytes: Decoded bytes
    
    Raises:
        ValidationError: If invalid Base58 string
    
    Examples:
        >>> base58_decode('Cn8eVZg')
        b'hello'
    """
    # Validate characters
    for char in encoded:
        if char not in BASE58_ALPHABET:
            raise ValidationError(f"Invalid Base58 character: {char}")
    
    # Decode from base58
    num = 0
    for char in encoded:
        num = num * 58 + BASE58_ALPHABET.index(char)
    
    # Convert to bytes
    decoded = num.to_bytes((num.bit_length() + 7) // 8, byteorder='big')
    
    # Restore leading zeros
    num_leading_zeros = len(encoded) - len(encoded.lstrip('1'))
    decoded = b'\x00' * num_leading_zeros + decoded
    
    return decoded


# ============================================================================
# BASE58CHECK ENCODING
# ============================================================================

def base58check_encode(version: bytes, payload: bytes) -> str:
    """
    Encode with Base58Check (includes checksum).
    
    Args:
        version: Version byte(s)
        payload: Payload bytes
    
    Returns:
        str: Base58Check string
    
    Examples:
        >>> base58check_encode(b'\\x00', b'\\x01' * 20)
        '1112k4VkZj...'
    """
    # Combine version and payload
    data = version + payload
    
    # Compute checksum (first 4 bytes of double SHA-256)
    checksum = hashlib.sha256(hashlib.sha256(data).digest()).digest()[:4]
    
    # Encode
    return base58_encode(data + checksum)


def base58check_decode(encoded: str) -> tuple[bytes, bytes]:
    """
    Decode Base58Check string.
    
    Args:
        encoded: Base58Check string
    
    Returns:
        tuple: (version, payload)
    
    Raises:
        ValidationError: If checksum invalid
    
    Examples:
        >>> version, payload = base58check_decode('1112k4VkZj...')
    """
    # Decode
    decoded = base58_decode(encoded)
    
    if len(decoded) < 5:
        raise ValidationError("Invalid Base58Check: too short")
    
    # Split data and checksum
    data = decoded[:-4]
    checksum = decoded[-4:]
    
    # Verify checksum
    expected_checksum = hashlib.sha256(hashlib.sha256(data).digest()).digest()[:4]
    
    if checksum != expected_checksum:
        raise ValidationError("Invalid Base58Check: checksum mismatch")
    
    # Split version and payload
    version = data[:1]
    payload = data[1:]
    
    return version, payload


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

def encode_address(version: int, pubkey_hash: bytes) -> str:
    """
    Encode address from public key hash.
    
    Args:
        version: Address version (0 for mainnet, 111 for testnet)
        pubkey_hash: Public key hash (20 bytes)
    
    Returns:
        str: Bitcoin-style address
    """
    return base58check_encode(bytes([version]), pubkey_hash)


def decode_address(address: str) -> tuple[int, bytes]:
    """
    Decode address to version and public key hash.
    
    Args:
        address: Bitcoin-style address
    
    Returns:
        tuple: (version, pubkey_hash)
    """
    version, payload = base58check_decode(address)
    return version[0], payload


# ============================================================================
# EXPORT
# ============================================================================

__all__ = [
    "base58_encode",
    "base58_decode",
    "base58check_encode",
    "base58check_decode",
    "encode_address",
    "decode_address",
]
