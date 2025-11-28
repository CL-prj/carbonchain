"""
CarbonChain - API Dependencies
================================
FastAPI dependency injection utilities.
"""

from typing import Generator, Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from carbon_chain.domain.blockchain import Blockchain
from carbon_chain.config import ChainSettings
from carbon_chain.logging_setup import get_logger

logger = get_logger("api.deps")

# Global instances (set at startup)
_blockchain: Optional[Blockchain] = None
_config: Optional[ChainSettings] = None

# Security
security = HTTPBearer(auto_error=False)


def set_blockchain(blockchain: Blockchain):
    """Set global blockchain instance"""
    global _blockchain
    _blockchain = blockchain


def set_config(config: ChainSettings):
    """Set global config instance"""
    global _config
    _config = config


def get_blockchain() -> Blockchain:
    """
    Get blockchain instance.
    
    Dependency for FastAPI routes.
    """
    if _blockchain is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Blockchain not initialized"
        )
    return _blockchain


def get_config() -> ChainSettings:
    """
    Get configuration instance.
    
    Dependency for FastAPI routes.
    """
    if _config is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Configuration not initialized"
        )
    return _config


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[str]:
    """
    Get current authenticated user.
    
    Returns None if no authentication required.
    For future implementation of API keys/JWT.
    """
    if credentials is None:
        return None
    
    # TODO: Implement JWT/API key validation
    token = credentials.credentials
    
    # For now, just return token as username
    # In production, validate token and return user info
    return token


def require_auth(
    current_user: Optional[str] = Depends(get_current_user)
) -> str:
    """
    Require authentication.
    
    Raises 401 if not authenticated.
    """
    if current_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return current_user


def check_rate_limit(
    remote_addr: str,
    endpoint: str,
    limit: int = 100,
    window: int = 60
) -> bool:
    """
    Check if request is within rate limit.
    
    Args:
        remote_addr: Client IP address
        endpoint: API endpoint
        limit: Max requests per window
        window: Time window in seconds
    
    Returns:
        True if within limit, raises HTTPException otherwise
    """
    # TODO: Implement Redis-based rate limiting
    # For now, always return True
    return True


def validate_address(address: str) -> str:
    """
    Validate blockchain address format.
    
    Args:
        address: Blockchain address to validate
    
    Returns:
        Validated address
    
    Raises:
        HTTPException: If address is invalid
    """
    from carbon_chain.crypto.addressing import is_valid_address
    
    if not is_valid_address(address):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid address format: {address}"
        )
    
    return address


def validate_txid(txid: str) -> bytes:
    """
    Validate and convert transaction ID.
    
    Args:
        txid: Transaction ID as hex string
    
    Returns:
        Transaction ID as bytes
    
    Raises:
        HTTPException: If txid is invalid
    """
    try:
        if len(txid) != 64:
            raise ValueError("TXID must be 64 hex characters")
        
        txid_bytes = bytes.fromhex(txid)
        
        if len(txid_bytes) != 32:
            raise ValueError("TXID must be 32 bytes")
        
        return txid_bytes
    
    except (ValueError, TypeError) as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid transaction ID: {str(e)}"
        )


def validate_block_identifier(identifier: str) -> tuple[str, int | str]:
    """
    Validate block identifier (height or hash).
    
    Args:
        identifier: Block height (int) or hash (hex string)
    
    Returns:
        Tuple of (type, value) where type is 'height' or 'hash'
    
    Raises:
        HTTPException: If identifier is invalid
    """
    # Try as height first
    try:
        height = int(identifier)
        if height < 0:
            raise ValueError("Height must be non-negative")
        return ('height', height)
    except ValueError:
        pass
    
    # Try as hash
    try:
        if len(identifier) != 64:
            raise ValueError("Block hash must be 64 hex characters")
        
        bytes.fromhex(identifier)
        return ('hash', identifier)
    
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid block identifier. Must be height (int) or hash (64 hex chars)"
        )


__all__ = [
    'get_blockchain',
    'get_config',
    'get_current_user',
    'require_auth',
    'check_rate_limit',
    'validate_address',
    'validate_txid',
    'validate_block_identifier',
    'set_blockchain',
    'set_config',
]
