"""
CarbonChain - Utilities Package
=================================
Common utility functions and helpers.
"""

from carbon_chain.utils.serialization import (
    serialize_to_json,
    deserialize_from_json,
    bytes_to_hex,
    hex_to_bytes,
)
from carbon_chain.utils.merkle import MerkleTree, compute_merkle_root
from carbon_chain.utils.base58 import (
    base58_encode,
    base58_decode,
    base58check_encode,
    base58check_decode,
)
from carbon_chain.utils.validators import (
    validate_address,
    validate_txid,
    validate_amount,
    validate_certificate_id,
)
from carbon_chain.utils.monitoring import (
    PerformanceMonitor,
    get_metrics,
)

__all__ = [
    # Serialization
    "serialize_to_json",
    "deserialize_from_json",
    "bytes_to_hex",
    "hex_to_bytes",
    
    # Merkle
    "MerkleTree",
    "compute_merkle_root",
    
    # Base58
    "base58_encode",
    "base58_decode",
    "base58check_encode",
    "base58check_decode",
    
    # Validators
    "validate_address",
    "validate_txid",
    "validate_amount",
    "validate_certificate_id",
    
    # Monitoring
    "PerformanceMonitor",
    "get_metrics",
]
