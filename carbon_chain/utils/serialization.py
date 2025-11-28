"""
CarbonChain - Serialization Utilities
=======================================
JSON and binary serialization helpers.
"""

import json
from typing import Any, Dict, List, Optional
from datetime import datetime
import binascii

from carbon_chain.logging_setup import get_logger

logger = get_logger("utils.serialization")


# ============================================================================
# JSON SERIALIZATION
# ============================================================================

def serialize_to_json(obj: Any, indent: Optional[int] = None) -> str:
    """
    Serialize object to JSON string.
    
    Handles datetime, bytes, and custom objects.
    
    Args:
        obj: Object to serialize
        indent: JSON indentation (None = compact)
    
    Returns:
        str: JSON string
    
    Examples:
        >>> data = {"timestamp": datetime.now(), "hash": b"abc"}
        >>> json_str = serialize_to_json(data)
    """
    def default_handler(o):
        if isinstance(o, datetime):
            return o.isoformat()
        elif isinstance(o, bytes):
            return o.hex()
        elif hasattr(o, 'to_dict'):
            return o.to_dict()
        elif hasattr(o, '__dict__'):
            return o.__dict__
        else:
            return str(o)
    
    try:
        return json.dumps(obj, default=default_handler, indent=indent)
    except Exception as e:
        logger.error(f"Serialization failed: {e}")
        raise


def deserialize_from_json(json_str: str) -> Any:
    """
    Deserialize JSON string to Python object.
    
    Args:
        json_str: JSON string
    
    Returns:
        Any: Python object
    """
    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        logger.error(f"Deserialization failed: {e}")
        raise


# ============================================================================
# BYTES/HEX CONVERSION
# ============================================================================

def bytes_to_hex(data: bytes) -> str:
    """
    Convert bytes to hex string.
    
    Args:
        data: Bytes data
    
    Returns:
        str: Hex string
    
    Examples:
        >>> bytes_to_hex(b"\\x00\\x01\\x02")
        '000102'
    """
    return data.hex()


def hex_to_bytes(hex_str: str) -> bytes:
    """
    Convert hex string to bytes.
    
    Args:
        hex_str: Hex string
    
    Returns:
        bytes: Bytes data
    
    Raises:
        ValueError: If invalid hex string
    
    Examples:
        >>> hex_to_bytes('000102')
        b'\\x00\\x01\\x02'
    """
    try:
        return bytes.fromhex(hex_str)
    except ValueError as e:
        logger.error(f"Invalid hex string: {hex_str}")
        raise ValueError(f"Invalid hex string: {e}")


# ============================================================================
# BINARY SERIALIZATION
# ============================================================================

def int_to_bytes(value: int, length: int = 4, byteorder: str = 'big') -> bytes:
    """
    Convert integer to bytes.
    
    Args:
        value: Integer value
        length: Byte length
        byteorder: 'big' or 'little'
    
    Returns:
        bytes: Bytes representation
    """
    return value.to_bytes(length, byteorder=byteorder)


def bytes_to_int(data: bytes, byteorder: str = 'big') -> int:
    """
    Convert bytes to integer.
    
    Args:
        data: Bytes data
        byteorder: 'big' or 'little'
    
    Returns:
        int: Integer value
    """
    return int.from_bytes(data, byteorder=byteorder)


def compact_size(value: int) -> bytes:
    """
    Encode integer in Bitcoin compact size format.
    
    Used for variable-length integer encoding.
    
    Args:
        value: Integer to encode
    
    Returns:
        bytes: Compact size bytes
    """
    if value < 0xfd:
        return bytes([value])
    elif value <= 0xffff:
        return b'\xfd' + value.to_bytes(2, 'little')
    elif value <= 0xffffffff:
        return b'\xfe' + value.to_bytes(4, 'little')
    else:
        return b'\xff' + value.to_bytes(8, 'little')


def read_compact_size(data: bytes, offset: int = 0) -> tuple[int, int]:
    """
    Read compact size from bytes.
    
    Args:
        data: Bytes data
        offset: Start offset
    
    Returns:
        tuple: (value, bytes_read)
    """
    first = data[offset]
    
    if first < 0xfd:
        return first, 1
    elif first == 0xfd:
        return int.from_bytes(data[offset+1:offset+3], 'little'), 3
    elif first == 0xfe:
        return int.from_bytes(data[offset+1:offset+5], 'little'), 5
    else:  # 0xff
        return int.from_bytes(data[offset+1:offset+9], 'little'), 9


# ============================================================================
# EXPORT
# ============================================================================

__all__ = [
    "serialize_to_json",
    "deserialize_from_json",
    "bytes_to_hex",
    "hex_to_bytes",
    "int_to_bytes",
    "bytes_to_int",
    "compact_size",
    "read_compact_size",
]
