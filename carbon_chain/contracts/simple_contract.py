"""
CarbonChain - Simple Smart Contracts
======================================
Limited smart contract system per CO2 operations.

Security Level: HIGH
Last Updated: 2025-11-27
Version: 1.0.0

Contract Types:
- Time-locked transfers
- Conditional compensations
- Automated certificate assignments
- Escrow contracts
"""

from __future__ import annotations
from typing import Optional, Dict, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
import time

# Internal imports
from carbon_chain.domain.models import Transaction, TxOutput
from carbon_chain.errors import ContractError, ValidationError
from carbon_chain.logging_setup import get_logger


# ============================================================================
# MODULE LOGGER
# ============================================================================

logger = get_logger("contracts")


# ============================================================================
# CONTRACT TYPES
# ============================================================================

class ContractType(Enum):
    """Tipi di smart contract"""
    TIMELOCK = "timelock"
    CONDITIONAL = "conditional"
    ESCROW = "escrow"
    RECURRING = "recurring"
    THRESHOLD = "threshold"


class ContractStatus(Enum):
    """Stati contratto"""
    PENDING = "pending"
    ACTIVE = "active"
    EXECUTED = "executed"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


# ============================================================================
# BASE CONTRACT
# ============================================================================

@dataclass
class SmartContract:
    """
    Smart contract base.
    
    Attributes:
        contract_id: ID univoco contratto
        contract_type: Tipo contratto
        creator: Address creatore
        status: Stato contratto
        creation_time: Timestamp creazione
        conditions: Condizioni esecuzione
        metadata: Metadati aggiuntivi
    """
    
    contract_id: str
    contract_type: ContractType
    creator: str
    status: ContractStatus = ContractStatus.PENDING
    creation_time: int = field(default_factory=lambda: int(time.time()))
    conditions: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def check_conditions(self, context: Dict[str, Any]) -> bool:
        """
        Verifica condizioni esecuzione.
        
        Args:
            context: Context con dati blockchain
        
        Returns:
            bool: True se condizioni soddisfatte
        """
        raise NotImplementedError("Subclass must implement check_conditions")
    
    def execute(self, context: Dict[str, Any]) -> Optional[Transaction]:
        """
        Esegui contratto.
        
        Args:
            context: Execution context
        
        Returns:
            Transaction: Transazione generata, o None
        """
        raise NotImplementedError("Subclass must implement execute")
    
    def to_dict(self) -> Dict:
        """Serializza contratto"""
        return {
            "contract_id": self.contract_id,
            "contract_type": self.contract_type.value,
            "creator": self.creator,
            "status": self.status.value,
            "creation_time": self.creation_time,
            "conditions": self.conditions,
            "metadata": self.metadata
        }


# ============================================================================
# TIMELOCK CONTRACT
# ============================================================================

@dataclass
class TimelockContract(SmartContract):
    """
    Time-locked transfer contract.
    
    Rilascia fondi dopo timestamp specifico.
    
    Conditions:
        - unlock_time: Timestamp di sblocco
        - recipient: Address destinatario
        - amount: Amount da trasferire
    
    Examples:
        >>> contract = TimelockContract(
        ...     contract_id="LOCK001",
        ...     creator="1Creator...",
        ...     conditions={
        ...         "unlock_time": 1735689600,  # 2025-01-01
        ...         "recipient": "1Recipient...",
        ...         "amount": 1000000
        ...     }
        ... )
    """
    
    def __post_init__(self):
        """Initialize timelock"""
        self.contract_type = ContractType.TIMELOCK
        
        # Validate conditions
        required = ["unlock_time", "recipient", "amount"]
        for key in required:
            if key not in self.conditions:
                raise ValidationError(f"Missing condition: {key}")
    
    def check_conditions(self, context: Dict[str, Any]) -> bool:
        """Check if unlock time reached"""
        current_time = context.get("current_time", int(time.time()))
        unlock_time = self.conditions["unlock_time"]
        
        return current_time >= unlock_time
    
    def execute(self, context: Dict[str, Any]) -> Optional[Transaction]:
        """Execute timelock release"""
        if not self.check_conditions(context):
            logger.debug(f"Timelock {self.contract_id} not yet unlocked")
            return None
        
        # Create transfer transaction
        from carbon_chain.constants import TxType
        
        tx = Transaction(
            tx_type=TxType.TRANSFER,
            inputs=[],  # Will be filled by wallet service
            outputs=[
                TxOutput(
                    amount=self.conditions["amount"],
                    address=self.conditions["recipient"]
                )
            ],
            timestamp=int(time.time())
        )
        
        tx.metadata["contract_id"] = self.contract_id
        tx.metadata["contract_type"] = "timelock"
        
        self.status = ContractStatus.EXECUTED
        
        logger.info(f"Executed timelock contract {self.contract_id}")
        
        return tx


# ============================================================================
# CONDITIONAL CONTRACT
# ============================================================================

@dataclass
class ConditionalContract(SmartContract):
    """
    Conditional execution contract.
    
    Esegue solo se condizioni specifiche soddisfatte.
    
    Conditions:
        - condition_type: Tipo condizione (balance, certificate, height)
        - condition_value: Valore target
        - action: Azione da eseguire
    
    Examples:
        >>> # Execute when balance reaches threshold
        >>> contract = ConditionalContract(
        ...     contract_id="COND001",
        ...     creator="1Creator...",
        ...     conditions={
        ...         "condition_type": "balance",
        ...         "address": "1Target...",
        ...         "threshold": 1000000,
        ...         "action": "transfer",
        ...         "recipient": "1Recipient...",
        ...         "amount": 500000
        ...     }
        ... )
    """
    
    def __post_init__(self):
        """Initialize conditional"""
        self.contract_type = ContractType.CONDITIONAL
    
    def check_conditions(self, context: Dict[str, Any]) -> bool:
        """Check custom conditions"""
        condition_type = self.conditions.get("condition_type")
        
        if condition_type == "balance":
            # Check address balance
            address = self.conditions["address"]
            threshold = self.conditions["threshold"]
            
            current_balance = context.get("balances", {}).get(address, 0)
            return current_balance >= threshold
        
        elif condition_type == "certificate":
            # Check certificate issued
            cert_id = self.conditions["certificate_id"]
            certificates = context.get("certificates", [])
            return cert_id in certificates
        
        elif condition_type == "height":
            # Check blockchain height
            target_height = self.conditions["height"]
            current_height = context.get("height", 0)
            return current_height >= target_height
        
        return False
    
    def execute(self, context: Dict[str, Any]) -> Optional[Transaction]:
        """Execute conditional action"""
        if not self.check_conditions(context):
            return None
        
        action = self.conditions.get("action")
        
        if action == "transfer":
            # Create transfer
            from carbon_chain.constants import TxType
            
            tx = Transaction(
                tx_type=TxType.TRANSFER,
                inputs=[],
                outputs=[
                    TxOutput(
                        amount=self.conditions["amount"],
                        address=self.conditions["recipient"]
                    )
                ],
                timestamp=int(time.time())
            )
            
            tx.metadata["contract_id"] = self.contract_id
            
            self.status = ContractStatus.EXECUTED
            
            return tx
        
        return None


# ============================================================================
# ESCROW CONTRACT
# ============================================================================

@dataclass
class EscrowContract(SmartContract):
    """
    Escrow contract per transazioni garantite.
    
    Trattiene fondi finché entrambe le parti confermano.
    
    Conditions:
        - buyer: Address compratore
        - seller: Address venditore
        - amount: Amount in escrow
        - buyer_confirmed: Conferma compratore
        - seller_confirmed: Conferma venditore
        - timeout: Timeout per conferme
    
    Examples:
        >>> contract = EscrowContract(
        ...     contract_id="ESC001",
        ...     creator="1Buyer...",
        ...     conditions={
        ...         "buyer": "1Buyer...",
        ...         "seller": "1Seller...",
        ...         "amount": 1000000,
        ...         "timeout": 1735689600
        ...     }
        ... )
    """
    
    def __post_init__(self):
        """Initialize escrow"""
        self.contract_type = ContractType.ESCROW
        self.conditions.setdefault("buyer_confirmed", False)
        self.conditions.setdefault("seller_confirmed", False)
    
    def confirm_buyer(self):
        """Buyer confirms transaction"""
        self.conditions["buyer_confirmed"] = True
        logger.info(f"Buyer confirmed escrow {self.contract_id}")
    
    def confirm_seller(self):
        """Seller confirms delivery"""
        self.conditions["seller_confirmed"] = True
        logger.info(f"Seller confirmed escrow {self.contract_id}")
    
    def check_conditions(self, context: Dict[str, Any]) -> bool:
        """Check if both parties confirmed"""
        return (
            self.conditions["buyer_confirmed"] and
            self.conditions["seller_confirmed"]
        )
    
    def execute(self, context: Dict[str, Any]) -> Optional[Transaction]:
        """Release escrow funds"""
        current_time = context.get("current_time", int(time.time()))
        timeout = self.conditions.get("timeout", 0)
        
        # Check timeout
        if current_time > timeout:
            # Refund to buyer
            recipient = self.conditions["buyer"]
            logger.info(f"Escrow {self.contract_id} timed out - refunding buyer")
        elif self.check_conditions(context):
            # Release to seller
            recipient = self.conditions["seller"]
            logger.info(f"Escrow {self.contract_id} confirmed - releasing to seller")
        else:
            return None
        
        # Create transaction
        from carbon_chain.constants import TxType
        
        tx = Transaction(
            tx_type=TxType.TRANSFER,
            inputs=[],
            outputs=[
                TxOutput(
                    amount=self.conditions["amount"],
                    address=recipient
                )
            ],
            timestamp=int(time.time())
        )
        
        tx.metadata["contract_id"] = self.contract_id
        tx.metadata["contract_type"] = "escrow"
        
        self.status = ContractStatus.EXECUTED
        
        return tx


# ============================================================================
# CONTRACT EXECUTOR
# ============================================================================

class ContractExecutor:
    """
    Executor per smart contracts.
    
    Esegue contracts quando condizioni soddisfatte.
    """
    
    def __init__(self, blockchain):
        """Initialize executor"""
        self.blockchain = blockchain
        self.active_contracts: Dict[str, SmartContract] = {}
    
    def register_contract(self, contract: SmartContract):
        """Register contract for execution"""
        self.active_contracts[contract.contract_id] = contract
        contract.status = ContractStatus.ACTIVE
        logger.info(f"Registered contract {contract.contract_id}")
    
    def execute_contracts(self) -> list[Transaction]:
        """
        Execute all eligible contracts.
        
        Returns:
            list: Transactions generated
        """
        context = self._build_context()
        executed_txs = []
        
        for contract_id, contract in list(self.active_contracts.items()):
            if contract.status != ContractStatus.ACTIVE:
                continue
            
            try:
                tx = contract.execute(context)
                if tx:
                    executed_txs.append(tx)
                    
                    # Remove executed contract
                    if contract.status == ContractStatus.EXECUTED:
                        del self.active_contracts[contract_id]
            
            except Exception as e:
                logger.error(f"Contract {contract_id} execution failed: {e}")
        
        return executed_txs
    
    def _build_context(self) -> Dict[str, Any]:
        """Build execution context"""
        return {
            "current_time": int(time.time()),
            "height": self.blockchain.get_height(),
            "balances": {},  # TODO: Get from blockchain
            "certificates": [],  # TODO: Get from blockchain
        }


# ============================================================================
# EXPORT
# ============================================================================

__all__ = [
    "ContractType",
    "ContractStatus",
    "SmartContract",
    "TimelockContract",
    "ConditionalContract",
    "EscrowContract",
    "ContractExecutor",
]
