"""
CarbonChain - Input Validators
================================
Validation functions for various input types.
"""

import re
from typing import Optional

from carbon_chain.errors import ValidationError
from carbon_chain.logging_setup import get_logger

logger = get_logger("utils.validators")


# ============================================================================
# ADDRESS VALIDATION
# ============================================================================

def validate_address(address: str) -> bool:
    """
    Validate CarbonChain address.
    
    Args:
        address: Address string
    
    Returns:
        bool: True if valid
    
    Raises:
        ValidationError: If invalid
    
    Examples:
        >>> validate_address("1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa")
        True
    """
    # Check length
    if not address or len(address) < 26 or len(address) > 35:
        raise ValidationError(f"Invalid address length: {len(address)}")
    
    # Check starts with valid prefix
    if not address[0] in ['1', '3', 'bc1', 'm', 'n', '2', 'tb1']:
        raise ValidationError(f"Invalid address prefix: {address[0]}")
    
    # Check Base58 characters (basic check)
    if not all(c in '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz' 
               for c in address if not address.startswith('bc1')):
        raise ValidationError("Invalid Base58 characters in address")
    
    return True


def validate_txid(txid: str) -> bool:
    """
    Validate transaction ID.
    
    Args:
        txid: Transaction ID (hex string)
    
    Returns:
        bool: True if valid
    
    Raises:
        ValidationError: If invalid
    """
    if not txid:
        raise ValidationError("Empty transaction ID")
    
    if len(txid) != 64:
        raise ValidationError(f"Invalid txid length: {len(txid)} (expected 64)")
    
    if not all(c in '0123456789abcdefABCDEF' for c in txid):
        raise ValidationError("Invalid hex characters in txid")
    
    return True


# ============================================================================
# AMOUNT VALIDATION
# ============================================================================

def validate_amount(amount: int, allow_zero: bool = False) -> bool:
    """
    Validate amount (Satoshi).
    
    Args:
        amount: Amount in Satoshi
        allow_zero: Allow zero amount
    
    Returns:
        bool: True if valid
    
    Raises:
        ValidationError: If invalid
    """
    if not isinstance(amount, int):
        raise ValidationError(f"Amount must be integer, got {type(amount)}")
    
    if amount < 0:
        raise ValidationError(f"Amount cannot be negative: {amount}")
    
    if not allow_zero and amount == 0:
        raise ValidationError("Amount cannot be zero")
    
    # Max supply check (21 million CCO2)
    MAX_SUPPLY_SATOSHI = 21_000_000 * 100_000_000
    if amount > MAX_SUPPLY_SATOSHI:
        raise ValidationError(f"Amount exceeds max supply: {amount}")
    
    return True


# ============================================================================
# CERTIFICATE VALIDATION
# ============================================================================

def validate_certificate_id(cert_id: str) -> bool:
    """
    Validate certificate ID format.
    
    Format: CERT-YYYY-NNNN (e.g., CERT-2025-0001)
    
    Args:
        cert_id: Certificate ID
    
    Returns:
        bool: True if valid
    
    Raises:
        ValidationError: If invalid
    """
    pattern = r'^CERT-\d{4}-\d{4,}$'
    
    if not re.match(pattern, cert_id):
        raise ValidationError(
            f"Invalid certificate ID format: {cert_id}. "
            "Expected format: CERT-YYYY-NNNN"
        )
    
    return True


def validate_project_id(project_id: str) -> bool:
    """
    Validate project ID format.
    
    Format: PROJ-YYYY-NNNN
    
    Args:
        project_id: Project ID
    
    Returns:
        bool: True if valid
    
    Raises:
        ValidationError: If invalid
    """
    pattern = r'^PROJ-\d{4}-\d{4,}$'
    
    if not re.match(pattern, project_id):
        raise ValidationError(
            f"Invalid project ID format: {project_id}. "
            "Expected format: PROJ-YYYY-NNNN"
        )
    
    return True


# ============================================================================
# STRING VALIDATION
# ============================================================================

def validate_string(
    value: str,
    min_length: int = 1,
    max_length: int = 1000,
    name: str = "string"
) -> bool:
    """
    Validate string length and content.
    
    Args:
        value: String to validate
        min_length: Minimum length
        max_length: Maximum length
        name: Field name (for error messages)
    
    Returns:
        bool: True if valid
    
    Raises:
        ValidationError: If invalid
    """
    if not isinstance(value, str):
        raise ValidationError(f"{name} must be string, got {type(value)}")
    
    if len(value) < min_length:
        raise ValidationError(
            f"{name} too short: {len(value)} < {min_length}"
        )
    
    if len(value) > max_length:
        raise ValidationError(
            f"{name} too long: {len(value)} > {max_length}"
        )
    
    return True


def validate_url(url: str) -> bool:
    """
    Validate URL format.
    
    Args:
        url: URL string
    
    Returns:
        bool: True if valid
    
    Raises:
        ValidationError: If invalid
    """
    pattern = r'^https?:\/\/(www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_\+.~#?&//=]*)$'
    
    if not re.match(pattern, url):
        raise ValidationError(f"Invalid URL format: {url}")
    
    return True


# ============================================================================
# NUMERIC VALIDATION
# ============================================================================

def validate_integer_range(
    value: int,
    min_value: Optional[int] = None,
    max_value: Optional[int] = None,
    name: str = "value"
) -> bool:
    """
    Validate integer is within range.
    
    Args:
        value: Integer value
        min_value: Minimum value (inclusive)
        max_value: Maximum value (inclusive)
        name: Field name
    
    Returns:
        bool: True if valid
    
    Raises:
        ValidationError: If invalid
    """
    if not isinstance(value, int):
        raise ValidationError(f"{name} must be integer, got {type(value)}")
    
    if min_value is not None and value < min_value:
        raise ValidationError(f"{name} too small: {value} < {min_value}")
    
    if max_value is not None and value > max_value:
        raise ValidationError(f"{name} too large: {value} > {max_value}")
    
    return True


# ============================================================================
# EXPORT
# ============================================================================

__all__ = [
    "validate_address",
    "validate_txid",
    "validate_amount",
    "validate_certificate_id",
    "validate_project_id",
    "validate_string",
    "validate_url",
    "validate_integer_range",
]
