"""
CarbonChain - API Schemas
==========================
Pydantic models for API request/response validation.
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from enum import Enum


# ============================================================================
# ENUMS
# ============================================================================

class TransactionTypeEnum(str, Enum):
    """Transaction type enumeration"""
    COINBASE = "COINBASE"
    TRANSFER = "TRANSFER"
    CERTIFICATE = "CERTIFICATE"
    COMPENSATION = "COMPENSATION"


class CoinStateEnum(str, Enum):
    """Coin state enumeration"""
    SPENDABLE = "SPENDABLE"
    CERTIFIED = "CERTIFIED"
    COMPENSATED = "COMPENSATED"


class CertificateTypeEnum(str, Enum):
    """Certificate type enumeration"""
    RENEWABLE_ENERGY = "RENEWABLE_ENERGY"
    FOREST_CONSERVATION = "FOREST_CONSERVATION"
    CARBON_CAPTURE = "CARBON_CAPTURE"
    ENERGY_EFFICIENCY = "ENERGY_EFFICIENCY"
    METHANE_REDUCTION = "METHANE_REDUCTION"


# ============================================================================
# BASE SCHEMAS
# ============================================================================

class HealthResponse(BaseModel):
    """Health check response"""
    status: str = Field(..., description="Service status")
    version: str = Field(..., description="CarbonChain version")
    timestamp: int = Field(..., description="Current timestamp")


class ErrorResponse(BaseModel):
    """Error response"""
    error: str = Field(..., description="Error message")
    detail: Optional[Dict[str, Any]] = Field(None, description="Error details")


# ============================================================================
# BLOCKCHAIN SCHEMAS
# ============================================================================

class BlockHeaderSchema(BaseModel):
    """Block header schema"""
    height: int = Field(..., description="Block height")
    hash: str = Field(..., description="Block hash (hex)")
    prev_hash: str = Field(..., description="Previous block hash (hex)")
    merkle_root: str = Field(..., description="Merkle root (hex)")
    timestamp: int = Field(..., description="Block timestamp")
    difficulty: int = Field(..., description="Mining difficulty")
    nonce: int = Field(..., description="Nonce value")


class TransactionInputSchema(BaseModel):
    """Transaction input schema"""
    prev_txid: Optional[str] = Field(None, description="Previous transaction ID (hex)")
    prev_index: int = Field(..., description="Previous output index")
    signature: Optional[str] = Field(None, description="Signature (hex)")
    pubkey: Optional[str] = Field(None, description="Public key (hex)")


class TransactionOutputSchema(BaseModel):
    """Transaction output schema"""
    amount: int = Field(..., description="Amount in satoshi")
    address: str = Field(..., description="Recipient address")
    coin_state: CoinStateEnum = Field(..., description="Coin state")
    certificate_id: Optional[str] = Field(None, description="Certificate ID if certified")


class TransactionSchema(BaseModel):
    """Transaction schema"""
    txid: str = Field(..., description="Transaction ID (hex)")
    tx_type: TransactionTypeEnum = Field(..., description="Transaction type")
    version: int = Field(1, description="Transaction version")
    inputs: List[TransactionInputSchema] = Field(..., description="Transaction inputs")
    outputs: List[TransactionOutputSchema] = Field(..., description="Transaction outputs")
    timestamp: int = Field(..., description="Transaction timestamp")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class BlockSchema(BaseModel):
    """Block schema"""
    header: BlockHeaderSchema = Field(..., description="Block header")
    transactions: List[TransactionSchema] = Field(..., description="Block transactions")


class BlockchainInfoResponse(BaseModel):
    """Blockchain info response"""
    height: int = Field(..., description="Current blockchain height")
    best_block_hash: str = Field(..., description="Best block hash")
    difficulty: int = Field(..., description="Current difficulty")
    total_supply: int = Field(..., description="Total supply in satoshi")
    total_supply_cco2: float = Field(..., description="Total supply in CCO2")
    mempool_size: int = Field(..., description="Number of transactions in mempool")
    version: str = Field(..., description="CarbonChain version")


# ============================================================================
# ADDRESS SCHEMAS
# ============================================================================

class AddressBalanceResponse(BaseModel):
    """Address balance response"""
    address: str = Field(..., description="Blockchain address")
    balance: int = Field(..., description="Balance in satoshi")
    balance_cco2: float = Field(..., description="Balance in CCO2")
    received: int = Field(..., description="Total received in satoshi")
    sent: int = Field(..., description="Total sent in satoshi")
    tx_count: int = Field(..., description="Number of transactions")


class UTXOSchema(BaseModel):
    """UTXO schema"""
    txid: str = Field(..., description="Transaction ID")
    index: int = Field(..., description="Output index")
    amount: int = Field(..., description="Amount in satoshi")
    confirmations: int = Field(..., description="Number of confirmations")
    coin_state: CoinStateEnum = Field(..., description="Coin state")
    certificate_id: Optional[str] = Field(None, description="Certificate ID if certified")


class AddressUTXOsResponse(BaseModel):
    """Address UTXOs response"""
    address: str = Field(..., description="Blockchain address")
    utxos: List[UTXOSchema] = Field(..., description="Unspent outputs")
    total_amount: int = Field(..., description="Total amount in satoshi")
    count: int = Field(..., description="Number of UTXOs")


# ============================================================================
# CERTIFICATE SCHEMAS
# ============================================================================

class CertificateSchema(BaseModel):
    """Certificate schema"""
    certificate_id: str = Field(..., description="Certificate ID")
    project_id: str = Field(..., description="Project ID")
    vintage: int = Field(..., description="Vintage year")
    total_amount: int = Field(..., description="Total amount in satoshi")
    assigned_amount: int = Field(..., description="Assigned amount in satoshi")
    compensated_amount: int = Field(..., description="Compensated amount in satoshi")
    remaining: int = Field(..., description="Remaining amount in satoshi")
    status: str = Field(..., description="Certificate status")
    certificate_type: CertificateTypeEnum = Field(..., description="Certificate type")
    location: Optional[str] = Field(None, description="Project location")
    standard: Optional[str] = Field(None, description="Verification standard")
    issue_date: int = Field(..., description="Issue timestamp")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class CertificateListResponse(BaseModel):
    """Certificate list response"""
    certificates: List[CertificateSchema] = Field(..., description="List of certificates")
    count: int = Field(..., description="Number of certificates")
    offset: int = Field(0, description="Pagination offset")
    total: int = Field(..., description="Total number of certificates")


# ============================================================================
# TRANSACTION SUBMISSION
# ============================================================================

class CreateTransactionRequest(BaseModel):
    """Create transaction request"""
    tx_type: TransactionTypeEnum = Field(..., description="Transaction type")
    inputs: List[TransactionInputSchema] = Field(..., description="Transaction inputs")
    outputs: List[TransactionOutputSchema] = Field(..., description="Transaction outputs")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
    
    @validator('inputs')
    def validate_inputs(cls, v, values):
        """Validate inputs based on transaction type"""
        tx_type = values.get('tx_type')
        
        if tx_type == TransactionTypeEnum.COINBASE:
            if len(v) > 0:
                raise ValueError("Coinbase transactions cannot have inputs")
        else:
            if len(v) == 0:
                raise ValueError("Non-coinbase transactions must have inputs")
        
        return v


class SubmitTransactionResponse(BaseModel):
    """Submit transaction response"""
    txid: str = Field(..., description="Transaction ID")
    status: str = Field(..., description="Transaction status")
    message: str = Field(..., description="Status message")


# ============================================================================
# MEMPOOL SCHEMAS
# ============================================================================

class MempoolInfoResponse(BaseModel):
    """Mempool info response"""
    size: int = Field(..., description="Number of transactions in mempool")
    bytes: int = Field(..., description="Total size in bytes")
    usage: float = Field(..., description="Memory usage percentage")
    max_mempool: int = Field(..., description="Maximum mempool size")


# ============================================================================
# STATISTICS SCHEMAS
# ============================================================================

class NetworkStatsResponse(BaseModel):
    """Network statistics response"""
    height: int = Field(..., description="Blockchain height")
    difficulty: int = Field(..., description="Current difficulty")
    total_supply: float = Field(..., description="Total supply in CCO2")
    average_block_time: float = Field(..., description="Average block time in seconds")
    peers: int = Field(..., description="Number of connected peers")
    mempool_size: int = Field(..., description="Mempool size")


__all__ = [
    # Enums
    'TransactionTypeEnum',
    'CoinStateEnum',
    'CertificateTypeEnum',
    
    # Base
    'HealthResponse',
    'ErrorResponse',
    
    # Blockchain
    'BlockHeaderSchema',
    'TransactionInputSchema',
    'TransactionOutputSchema',
    'TransactionSchema',
    'BlockSchema',
    'BlockchainInfoResponse',
    
    # Address
    'AddressBalanceResponse',
    'UTXOSchema',
    'AddressUTXOsResponse',
    
    # Certificate
    'CertificateSchema',
    'CertificateListResponse',
    
    # Transaction submission
    'CreateTransactionRequest',
    'SubmitTransactionResponse',
    
    # Mempool
    'MempoolInfoResponse',
    
    # Statistics
    'NetworkStatsResponse',
]
