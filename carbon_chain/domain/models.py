"""
CarbonChain - Core Domain Models
==================================
Strutture dati fondamentali della blockchain.

Security Level: CRITICAL
Last Updated: 2025-11-27
Version: 1.0.0

Models:
- Transaction: Transazione con input/output
- TxInput: Input transazione (riferimento UTXO)
- TxOutput: Output transazione (amount + address + metadata)
- BlockHeader: Header blocco
- Block: Blocco completo
- UTXOKey: Chiave UTXO (txid + index)

Tutte le strutture sono immutabili (frozen) per thread-safety.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime
import json

# Internal imports
from carbon_chain.constants import (
    TxType,
    TxStatus,
    coin_to_satoshi,
    satoshi_to_coin,
    format_amount,
    validate_amount,
)
from carbon_chain.domain.crypto_core import (
    compute_sha256,
    compute_blake2b,
)
from carbon_chain.errors import (
    ValidationError,
    InvalidTransactionError,
)
from carbon_chain.logging_setup import get_logger


# ============================================================================
# MODULE LOGGER
# ============================================================================

logger = get_logger("models")


# ============================================================================
# TRANSACTION OUTPUT
# ============================================================================

@dataclass(frozen=True)
class TxOutput:
    """
    Output di transazione (UTXO).
    
    Rappresenta:
    - Quantità coin (in Satoshi)
    - Indirizzo destinatario
    - Metadata certificato CO2 (opzionale)
    - Metadata compensazione (opzionale)
    
    Attributes:
        amount (int): Quantità in Satoshi (1 Satoshi = 1 kg CO2)
        address (str): Indirizzo destinatario
        is_certified (bool): Se output ha certificato CO2 associato
        is_compensated (bool): Se output è stato compensato
        is_burned (bool): Se output è stato bruciato
        certificate_id (Optional[str]): ID certificato CO2
        certificate_hash (Optional[bytes]): Hash univoco certificato
        certificate_total_kg (Optional[int]): Capacità totale certificato
        certificate_metadata (Optional[dict]): Metadata certificato
        compensation_project_id (Optional[str]): ID progetto compensazione
        compensation_metadata (Optional[dict]): Metadata progetto
    
    Security:
        - Immutabile (frozen)
        - Validazione amount
        - Hash certificato univoco
    
    Examples:
        >>> # Output semplice
        >>> output = TxOutput(amount=50000, address="1A1zP...")
        >>> output.amount
        50000
        
        >>> # Output certificato
        >>> cert_output = TxOutput(
        ...     amount=100000,
        ...     address="1A1zP...",
        ...     is_certified=True,
        ...     certificate_id="CERT-001",
        ...     certificate_hash=b'\\x01\\x02...',
        ...     certificate_total_kg=100000,
        ...     certificate_metadata={"location": "Portugal"}
        ... )
    """
    
    # Amount (Satoshi)
    amount: int
    
    # Destination address
    address: str
    
    # Certificate flags
    is_certified: bool = False
    is_compensated: bool = False
    is_burned: bool = False
    
    # Certificate data (se is_certified=True)
    certificate_id: Optional[str] = None
    certificate_hash: Optional[bytes] = None
    certificate_total_kg: Optional[int] = None
    certificate_metadata: Optional[Dict[str, Any]] = None
    
    # Compensation data (se is_compensated=True)
    compensation_project_id: Optional[str] = None
    compensation_metadata: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        """Validazione post-init"""
        # Validazione amount
        if not validate_amount(self.amount):
            raise ValidationError(
                f"Invalid amount: {self.amount}. Must be positive and within limits.",
                code="INVALID_OUTPUT_AMOUNT",
                details={"amount": self.amount}
            )
        
        # Validazione address non vuoto
        if not self.address or not isinstance(self.address, str):
            raise ValidationError(
                "Address must be non-empty string",
                code="INVALID_OUTPUT_ADDRESS"
            )
        
        # Validazione certificato
        if self.is_certified:
            if not self.certificate_id:
                raise ValidationError(
                    "Certified output requires certificate_id",
                    code="MISSING_CERTIFICATE_ID"
                )
            
            if not self.certificate_hash:
                raise ValidationError(
                    "Certified output requires certificate_hash",
                    code="MISSING_CERTIFICATE_HASH"
                )
            
            if not self.certificate_total_kg or self.certificate_total_kg <= 0:
                raise ValidationError(
                    "Certified output requires valid certificate_total_kg",
                    code="INVALID_CERTIFICATE_TOTAL_KG"
                )
        
        # Validazione compensazione
        if self.is_compensated:
            if not self.compensation_project_id:
                raise ValidationError(
                    "Compensated output requires compensation_project_id",
                    code="MISSING_PROJECT_ID"
                )
            
            # Compensated DEVE essere anche certified
            if not self.is_certified:
                raise ValidationError(
                    "Compensated output must also be certified",
                    code="COMPENSATION_WITHOUT_CERTIFICATE"
                )
    
    def is_spendable(self) -> bool:
        """
        Check se output è spendibile.
        
        Output NON spendibile se:
        - Già compensato (no riuso)
        - Bruciato
        
        Returns:
            bool: True se spendibile
        
        Examples:
            >>> output = TxOutput(amount=100, address="addr1")
            >>> output.is_spendable()
            True
            
            >>> compensated = TxOutput(
            ...     amount=100, address="addr1",
            ...     is_certified=True, certificate_id="C1",
            ...     certificate_hash=b'hash',
            ...     certificate_total_kg=100,
            ...     is_compensated=True,
            ...     compensation_project_id="P1"
            ... )
            >>> compensated.is_spendable()
            False
        """
        if self.is_compensated:
            return False
        
        if self.is_burned:
            return False
        
        return True
    
    def get_amount_coin(self) -> float:
        """
        Ottieni amount in CCO2 coin.
        
        Returns:
            float: Amount in CCO2
        
        Examples:
            >>> output = TxOutput(amount=100000000, address="addr")
            >>> output.get_amount_coin()
            1.0
        """
        return satoshi_to_coin(self.amount)
    
    def format_amount(self, unit: str = "CCO2") -> str:
        """
        Formatta amount per display.
        
        Args:
            unit: Unità ("CCO2", "kg", "t", "Mt")
        
        Returns:
            str: Amount formattato
        
        Examples:
            >>> output = TxOutput(amount=150000000, address="addr")
            >>> output.format_amount("CCO2")
            '1.50000000 CCO2'
            >>> output.format_amount("kg")
            '150,000,000 kg CO2'
        """
        return format_amount(self.amount, unit)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Serializza output in dict.
        
        Returns:
            dict: Output serializzato
        
        Examples:
            >>> output = TxOutput(amount=100, address="addr1")
            >>> data = output.to_dict()
            >>> data["amount"]
            100
        """
        data = {
            "amount": self.amount,
            "address": self.address,
            "is_certified": self.is_certified,
            "is_compensated": self.is_compensated,
            "is_burned": self.is_burned,
        }
        
        # Add certificate data se presente
        if self.is_certified:
            data["certificate_id"] = self.certificate_id
            data["certificate_hash"] = self.certificate_hash.hex() if self.certificate_hash else None
            data["certificate_total_kg"] = self.certificate_total_kg
            data["certificate_metadata"] = self.certificate_metadata
        
        # Add compensation data se presente
        if self.is_compensated:
            data["compensation_project_id"] = self.compensation_project_id
            data["compensation_metadata"] = self.compensation_metadata
        
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> TxOutput:
        """
        Deserializza output da dict.
        
        Args:
            data: Dict serializzato
        
        Returns:
            TxOutput: Instance deserializzata
        
        Examples:
            >>> data = {"amount": 100, "address": "addr1"}
            >>> output = TxOutput.from_dict(data)
            >>> output.amount
            100
        """
        # Convert hex strings back to bytes
        cert_hash = None
        if "certificate_hash" in data and data["certificate_hash"]:
            cert_hash = bytes.fromhex(data["certificate_hash"])
        
        return cls(
            amount=data["amount"],
            address=data["address"],
            is_certified=data.get("is_certified", False),
            is_compensated=data.get("is_compensated", False),
            is_burned=data.get("is_burned", False),
            certificate_id=data.get("certificate_id"),
            certificate_hash=cert_hash,
            certificate_total_kg=data.get("certificate_total_kg"),
            certificate_metadata=data.get("certificate_metadata"),
            compensation_project_id=data.get("compensation_project_id"),
            compensation_metadata=data.get("compensation_metadata"),
        )
    
    def __repr__(self) -> str:
        """Safe repr"""
        flags = []
        if self.is_certified:
            flags.append("CERT")
        if self.is_compensated:
            flags.append("COMP")
        if self.is_burned:
            flags.append("BURN")
        
        flags_str = f" [{','.join(flags)}]" if flags else ""
        
        return (
            f"TxOutput(amount={self.amount} sat, "
            f"address={self.address[:16]}...{flags_str})"
        )


# ============================================================================
# TRANSACTION INPUT
# ============================================================================

@dataclass(frozen=True)
class TxInput:
    """
    Input di transazione (riferimento UTXO precedente).
    
    Rappresenta:
    - UTXO da spendere (prev_txid + prev_output_index)
    - Firma autorizzazione
    - Public key per verifica
    
    Attributes:
        prev_txid (str): TXID transazione precedente
        prev_output_index (int): Indice output da spendere
        signature (Optional[bytes]): Firma digitale
        public_key (Optional[bytes]): Public key per verifica firma
    
    Security:
        - Firma DEVE essere valida
        - Public key DEVE corrispondere all'address dell'UTXO
    
    Examples:
        >>> # Input base (da firmare)
        >>> inp = TxInput(prev_txid="abc123...", prev_output_index=0)
        
        >>> # Input firmato
        >>> signed_inp = TxInput(
        ...     prev_txid="abc123...",
        ...     prev_output_index=0,
        ...     signature=b'\\x01\\x02...',
        ...     public_key=b'-----BEGIN PUBLIC KEY-----...'
        ... )
    """
    
    prev_txid: str
    prev_output_index: int
    signature: Optional[bytes] = None
    public_key: Optional[bytes] = None
    
    def __post_init__(self):
        """Validazione post-init"""
        # Validazione txid
        if not self.prev_txid or not isinstance(self.prev_txid, str):
            raise ValidationError(
                "prev_txid must be non-empty string",
                code="INVALID_PREV_TXID"
            )
        
        # Validazione index
        if self.prev_output_index < 0:
            raise ValidationError(
                f"prev_output_index must be non-negative, got {self.prev_output_index}",
                code="INVALID_OUTPUT_INDEX"
            )
        
        # Se firma presente, public_key DEVE essere presente
        if self.signature and not self.public_key:
            raise ValidationError(
                "signature requires public_key",
                code="MISSING_PUBLIC_KEY"
            )
    
    def is_signed(self) -> bool:
        """
        Check se input è firmato.
        
        Returns:
            bool: True se ha signature e public_key
        
        Examples:
            >>> inp = TxInput("txid", 0)
            >>> inp.is_signed()
            False
            
            >>> signed = TxInput("txid", 0, signature=b'sig', public_key=b'pub')
            >>> signed.is_signed()
            True
        """
        return self.signature is not None and self.public_key is not None
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Serializza input in dict.
        
        Returns:
            dict: Input serializzato
        
        Examples:
            >>> inp = TxInput("txid123", 0)
            >>> data = inp.to_dict()
            >>> data["prev_txid"]
            'txid123'
        """
        return {
            "prev_txid": self.prev_txid,
            "prev_output_index": self.prev_output_index,
            "signature": self.signature.hex() if self.signature else None,
            "public_key": self.public_key.hex() if self.public_key else None,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> TxInput:
        """
        Deserializza input da dict.
        
        Args:
            data: Dict serializzato
        
        Returns:
            TxInput: Instance deserializzata
        
        Examples:
            >>> data = {"prev_txid": "txid", "prev_output_index": 0}
            >>> inp = TxInput.from_dict(data)
            >>> inp.prev_txid
            'txid'
        """
        signature = None
        if data.get("signature"):
            signature = bytes.fromhex(data["signature"])
        
        public_key = None
        if data.get("public_key"):
            public_key = bytes.fromhex(data["public_key"])
        
        return cls(
            prev_txid=data["prev_txid"],
            prev_output_index=data["prev_output_index"],
            signature=signature,
            public_key=public_key,
        )
    
    def __repr__(self) -> str:
        """Safe repr"""
        signed = " [SIGNED]" if self.is_signed() else ""
        return (
            f"TxInput(prev_txid={self.prev_txid[:16]}..., "
            f"index={self.prev_output_index}{signed})"
        )


# ============================================================================
# TRANSACTION
# ============================================================================

@dataclass(frozen=True)
class Transaction:
    """
    Transazione blockchain.
    
    Rappresenta:
    - Tipo transazione (COINBASE, TRANSFER, ASSIGN_CERT, etc.)
    - Input (UTXO da spendere)
    - Output (nuovi UTXO)
    - Timestamp
    - Metadata aggiuntivi
    
    Attributes:
        tx_type (TxType): Tipo transazione
        inputs (List[TxInput]): Lista input
        outputs (List[TxOutput]): Lista output
        timestamp (int): Unix timestamp creazione
        nonce (int): Nonce opzionale (per unicità)
        metadata (Optional[dict]): Metadata aggiuntivi
    
    Security:
        - TXID calcolato da hash della transazione
        - Immutabile dopo creazione
        - Validazione input/output
    
    Examples:
        >>> # COINBASE transaction
        >>> coinbase = Transaction(
        ...     tx_type=TxType.COINBASE,
        ...     inputs=[],
        ...     outputs=[TxOutput(amount=5000000000, address="miner_addr")],
        ...     timestamp=1700000000
        ... )
        
        >>> # TRANSFER transaction
        >>> transfer = Transaction(
        ...     tx_type=TxType.TRANSFER,
        ...     inputs=[TxInput("prev_txid", 0)],
        ...     outputs=[TxOutput(amount=100, address="addr1")],
        ...     timestamp=1700000000
        ... )
    """
    
    tx_type: TxType
    inputs: List[TxInput]
    outputs: List[TxOutput]
    timestamp: int
    nonce: int = 0
    metadata: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        """Validazione post-init"""
        # Validazione timestamp
        if self.timestamp <= 0:
            raise ValidationError(
                f"Invalid timestamp: {self.timestamp}",
                code="INVALID_TIMESTAMP"
            )
        
        # Validazione tipo-specifica
        if self.tx_type == TxType.COINBASE:
            # COINBASE: no input, almeno 1 output
            if self.inputs:
                raise ValidationError(
                    "COINBASE transaction must have no inputs",
                    code="COINBASE_WITH_INPUTS"
                )
            
            if not self.outputs:
                raise ValidationError(
                    "COINBASE transaction must have at least one output",
                    code="COINBASE_NO_OUTPUTS"
                )
        
        else:
            # Altre transazioni: almeno 1 input
            if not self.inputs:
                raise ValidationError(
                    f"{self.tx_type.name} transaction must have at least one input",
                    code="NO_INPUTS"
                )
        
        # Validazione output
        if self.tx_type != TxType.BURN:
            # BURN può avere 0 output (coin distrutte)
            if not self.outputs:
                raise ValidationError(
                    f"{self.tx_type.name} transaction must have outputs",
                    code="NO_OUTPUTS"
                )
    
    def compute_txid(self) -> str:
        """
        Calcola Transaction ID (hash univoco).
        
        TXID è hash SHA-256 della transazione serializzata.
        
        Returns:
            str: TXID (64 caratteri hex)
        
        Security:
            - Deterministico: stessa tx → stesso TXID
            - Collision-resistant
            - Firme NON incluse nel calcolo (per permettere signing)
        
        Examples:
            >>> tx = Transaction(
            ...     tx_type=TxType.TRANSFER,
            ...     inputs=[TxInput("prev", 0)],
            ...     outputs=[TxOutput(100, "addr")],
            ...     timestamp=1700000000
            ... )
            >>> txid = tx.compute_txid()
            >>> len(txid)
            64
        """
        # Serializza tx senza firme (per determinismo)
        tx_dict = self.to_dict(include_signatures=False)
        
        # Canonical JSON (sorted keys)
        canonical_json = json.dumps(tx_dict, sort_keys=True, separators=(',', ':'))
        
        # SHA-256 hash
        txid_hash = compute_sha256(canonical_json.encode('utf-8'))
        
        return txid_hash.hex()
    
    def total_input_amount(self) -> int:
        """
        Calcola somma amount input (richiede UTXO set per lookup).
        
        Note:
            Questa funzione NON può calcolare amount direttamente.
            Serve UTXO set per lookup prev_txid:prev_output_index.
        
        Returns:
            int: 0 (placeholder, usa UTXOSet per calcolo reale)
        """
        # Placeholder: calcolo reale richiede UTXO set
        return 0
    
    def total_output_amount(self) -> int:
        """
        Calcola somma amount output.
        
        Returns:
            int: Somma output in Satoshi
        
        Examples:
            >>> tx = Transaction(
            ...     tx_type=TxType.TRANSFER,
            ...     inputs=[TxInput("prev", 0)],
            ...     outputs=[
            ...         TxOutput(100, "addr1"),
            ...         TxOutput(50, "addr2")
            ...     ],
            ...     timestamp=1700000000
            ... )
            >>> tx.total_output_amount()
            150
        """
        return sum(output.amount for output in self.outputs)
    
    def is_coinbase(self) -> bool:
        """Check se tx è COINBASE"""
        return self.tx_type == TxType.COINBASE
    
    def is_transfer(self) -> bool:
        """Check se tx è TRANSFER"""
        return self.tx_type == TxType.TRANSFER
    
    def is_certificate_assignment(self) -> bool:
        """Check se tx è ASSIGN_CERT"""
        return self.tx_type == TxType.ASSIGN_CERT
    
    def is_compensation(self) -> bool:
        """Check se tx è ASSIGN_COMPENSATION"""
        return self.tx_type == TxType.ASSIGN_COMPENSATION
    
    def is_burn(self) -> bool:
        """Check se tx è BURN"""
        return self.tx_type == TxType.BURN
    
    def to_dict(
        self,
        include_signatures: bool = True,
        include_txid: bool = False
    ) -> Dict[str, Any]:
        """
        Serializza transaction in dict.
        
        Args:
            include_signatures: Se True, include firme input
            include_txid: Se True, include TXID calcolato
        
        Returns:
            dict: Transaction serializzata
        
        Examples:
            >>> tx = Transaction(
            ...     tx_type=TxType.TRANSFER,
            ...     inputs=[TxInput("prev", 0)],
            ...     outputs=[TxOutput(100, "addr")],
            ...     timestamp=1700000000
            ... )
            >>> data = tx.to_dict()
            >>> data["tx_type"]
            1
        """
        data = {
            "tx_type": self.tx_type.value,
            "inputs": [
                inp.to_dict() if include_signatures else {
                    "prev_txid": inp.prev_txid,
                    "prev_output_index": inp.prev_output_index,
                    "signature": None,
                    "public_key": None,
                }
                for inp in self.inputs
            ],
            "outputs": [output.to_dict() for output in self.outputs],
            "timestamp": self.timestamp,
            "nonce": self.nonce,
        }
        
        if self.metadata:
            data["metadata"] = self.metadata
        
        if include_txid:
            data["txid"] = self.compute_txid()
        
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Transaction:
        """
        Deserializza transaction da dict.
        
        Args:
            data: Dict serializzato
        
        Returns:
            Transaction: Instance deserializzata
        
        Examples:
            >>> data = {
            ...     "tx_type": 1,
            ...     "inputs": [{"prev_txid": "prev", "prev_output_index": 0}],
            ...     "outputs": [{"amount": 100, "address": "addr"}],
            ...     "timestamp": 1700000000
            ... }
            >>> tx = Transaction.from_dict(data)
            >>> tx.tx_type
            <TxType.TRANSFER: 1>
        """
        return cls(
            tx_type=TxType(data["tx_type"]),
            inputs=[TxInput.from_dict(inp) for inp in data["inputs"]],
            outputs=[TxOutput.from_dict(out) for out in data["outputs"]],
            timestamp=data["timestamp"],
            nonce=data.get("nonce", 0),
            metadata=data.get("metadata"),
        )
    
    def __repr__(self) -> str:
        """Safe repr"""
        txid = self.compute_txid()[:16]
        return (
            f"Transaction(type={self.tx_type.name}, "
            f"txid={txid}..., "
            f"inputs={len(self.inputs)}, "
            f"outputs={len(self.outputs)})"
        )


# ============================================================================
# BLOCK HEADER
# ============================================================================

@dataclass(frozen=True)
class BlockHeader:
    """
    Header blocco blockchain.
    
    Contiene:
    - Metadata blocco (version, height, timestamp)
    - Link blocco precedente (previous_hash)
    - Merkle root transazioni
    - Proof of Work (difficulty, nonce)
    
    Attributes:
        version (int): Versione protocollo
        previous_hash (str): Hash blocco precedente (64 hex)
        merkle_root (bytes): Root Merkle tree transazioni
        timestamp (int): Unix timestamp creazione
        difficulty (int): Difficulty target (byte zero richiesti)
        nonce (int): Nonce per PoW
        height (int): Altezza blocco (0 = genesis)
    
    Security:
        - Block hash include tutto l'header
        - PoW valida tramite difficulty check
        - Previous hash crea chain immutabile
    
    Examples:
        >>> header = BlockHeader(
        ...     version=1,
        ...     previous_hash="0" * 64,
        ...     merkle_root=b'\\x01' * 32,
        ...     timestamp=1700000000,
        ...     difficulty=4,
        ...     nonce=12345,
        ...     height=0
        ... )
    """
    
    version: int
    previous_hash: str
    merkle_root: bytes
    timestamp: int
    difficulty: int
    nonce: int
    height: int
    
    def __post_init__(self):
        """Validazione post-init"""
        # Validazione version
        if self.version <= 0:
            raise ValidationError(
                f"Invalid version: {self.version}",
                code="INVALID_VERSION"
            )
        
        # Validazione previous_hash
        if not self.previous_hash or len(self.previous_hash) != 64:
            raise ValidationError(
                "previous_hash must be 64 hex characters",
                code="INVALID_PREVIOUS_HASH"
            )
        
        # Validazione merkle_root
        if not self.merkle_root or len(self.merkle_root) != 32:
            raise ValidationError(
                "merkle_root must be 32 bytes",
                code="INVALID_MERKLE_ROOT"
            )
        
        # Validazione timestamp
        if self.timestamp <= 0:
            raise ValidationError(
                f"Invalid timestamp: {self.timestamp}",
                code="INVALID_TIMESTAMP"
            )
        
        # Validazione difficulty
        if not (1 <= self.difficulty <= 32):
            raise ValidationError(
                f"difficulty must be 1-32, got {self.difficulty}",
                code="INVALID_DIFFICULTY"
            )
        
        # Validazione height
        if self.height < 0:
            raise ValidationError(
                f"Invalid height: {self.height}",
                code="INVALID_HEIGHT"
            )
    
    @staticmethod
    def compute_header_hash(header: BlockHeader) -> str:
        """
        Calcola hash header (block hash).
        
        Args:
            header: BlockHeader instance
        
        Returns:
            str: Block hash (64 hex)
        
        Security:
            - Hash include tutti i campi header
            - Deterministico
            - PoW valida se hash < difficulty target
        
        Examples:
            >>> header = BlockHeader(1, "0"*64, b'\\x01'*32, 1700000000, 4, 0, 0)
            >>> block_hash = BlockHeader.compute_header_hash(header)
            >>> len(block_hash)
            64
        """
        # Serializza header in formato canonico
        header_data = (
            header.version.to_bytes(4, byteorder='big') +
            bytes.fromhex(header.previous_hash) +
            header.merkle_root +
            header.timestamp.to_bytes(8, byteorder='big') +
            header.difficulty.to_bytes(1, byteorder='big') +
            header.nonce.to_bytes(8, byteorder='big') +
            header.height.to_bytes(8, byteorder='big')
        )
        
        # SHA-256 hash
        block_hash = compute_sha256(header_data)
        
        return block_hash.hex()
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Serializza header in dict.
        
        Returns:
            dict: Header serializzato
        """
        return {
            "version": self.version,
            "previous_hash": self.previous_hash,
            "merkle_root": self.merkle_root.hex(),
            "timestamp": self.timestamp,
            "difficulty": self.difficulty,
            "nonce": self.nonce,
            "height": self.height,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> BlockHeader:
        """
        Deserializza header da dict.
        
        Args:
            data: Dict serializzato
        
        Returns:
            BlockHeader: Instance deserializzata
        """
        return cls(
            version=data["version"],
            previous_hash=data["previous_hash"],
            merkle_root=bytes.fromhex(data["merkle_root"]),
            timestamp=data["timestamp"],
            difficulty=data["difficulty"],
            nonce=data["nonce"],
            height=data["height"],
        )
    
    def __repr__(self) -> str:
        """Safe repr"""
        return (
            f"BlockHeader(height={self.height}, "
            f"prev={self.previous_hash[:16]}..., "
            f"difficulty={self.difficulty}, "
            f"nonce={self.nonce})"
        )


# ============================================================================
# BLOCK
# ============================================================================

@dataclass(frozen=True)
class Block:
    """
    Blocco blockchain completo.
    
    Contiene:
    - Header (metadata + PoW)
    - Lista transazioni
    
    Attributes:
        header (BlockHeader): Header blocco
        transactions (List[Transaction]): Lista transazioni
    
    Security:
        - Merkle root valida tutte le transazioni
        - Block hash include header
        - PoW rende block immutabile (costo ricomputo)
    
    Examples:
        >>> # Genesis block
        >>> coinbase = Transaction(
        ...     tx_type=TxType.COINBASE,
        ...     inputs=[],
        ...     outputs=[TxOutput(5000000000, "genesis_addr")],
        ...     timestamp=1700000000
        ... )
        >>> header = BlockHeader(1, "0"*64, b'\\x01'*32, 1700000000, 4, 0, 0)
        >>> block = Block(header=header, transactions=[coinbase])
    """
    
    header: BlockHeader
    transactions: List[Transaction]
    
    def __post_init__(self):
        """Validazione post-init"""
        # Validazione: almeno 1 tx (COINBASE)
        if not self.transactions:
            raise ValidationError(
                "Block must have at least one transaction (COINBASE)",
                code="BLOCK_NO_TRANSACTIONS"
            )
        
        # Prima tx DEVE essere COINBASE
        if not self.transactions[0].is_coinbase():
            raise ValidationError(
                "First transaction must be COINBASE",
                code="MISSING_COINBASE"
            )
        
        # Solo una COINBASE per blocco
        coinbase_count = sum(1 for tx in self.transactions if tx.is_coinbase())
        if coinbase_count != 1:
            raise ValidationError(
                f"Block must have exactly one COINBASE, found {coinbase_count}",
                code="MULTIPLE_COINBASE"
            )
    
    def compute_merkle_root(self) -> bytes:
        """
        Calcola Merkle root delle transazioni.
        
        Merkle Tree:
        - Leaf nodes: hash TXID di ogni transazione
        - Parent nodes: hash(left_child + right_child)
        - Root: hash finale
        
        Returns:
            bytes: 32-byte Merkle root
        
        Algorithm:
            1. Hash TXID di ogni tx (leaf level)
            2. Pair-wise hash fino a root
            3. Se odd number, duplica ultimo
        
        Examples:
            >>> coinbase = Transaction(
            ...     TxType.COINBASE, [], [TxOutput(50, "addr")], 1700000000
            ... )
            >>> header = BlockHeader(1, "0"*64, b'\\x00'*32, 1700000000, 4, 0, 0)
            >>> block = Block(header, [coinbase])
            >>> merkle = block.compute_merkle_root()
            >>> len(merkle)
            32
        """
        if not self.transactions:
            # Empty block (shouldn't happen, but handle)
            return b'\x00' * 32
        
        # Level 0: hash TXID di ogni transazione
        hashes = [
            compute_sha256(tx.compute_txid().encode('utf-8'))
            for tx in self.transactions
        ]
        
        # Costruisci tree bottom-up
        while len(hashes) > 1:
            next_level = []
            
            # Process pairs
            for i in range(0, len(hashes), 2):
                if i + 1 < len(hashes):
                    # Pair exists
                    combined = hashes[i] + hashes[i + 1]
                else:
                    # Odd number: duplicate last
                    combined = hashes[i] + hashes[i]
                
                # Hash combined
                parent_hash = compute_sha256(combined)
                next_level.append(parent_hash)
            
            hashes = next_level
        
        # Root
        return hashes[0]
    
    def compute_block_hash(self) -> str:
        """
        Calcola block hash (hash dell'header).
        
        Returns:
            str: Block hash (64 hex)
        
        Examples:
            >>> block = Block(header, [coinbase])
            >>> block_hash = block.compute_block_hash()
            >>> len(block_hash)
            64
        """
        return BlockHeader.compute_header_hash(self.header)
    
    def compute_hash(self) -> str:
        """Alias per compute_block_hash"""
        return self.compute_block_hash()
    
    def get_transaction_by_txid(self, txid: str) -> Optional[Transaction]:
        """
        Trova transazione per TXID in questo blocco.
        
        Args:
            txid: Transaction ID
        
        Returns:
            Transaction se trovata, None altrimenti
        """
        for tx in self.transactions:
            if tx.compute_txid() == txid:
                return tx
        return None
    
    def get_size_bytes(self) -> int:
        """
        Calcola dimensione blocco in bytes.
        
        Returns:
            int: Size approssimato in bytes
        """
        import json
        return len(json.dumps(self.to_dict()).encode('utf-8'))
    
    def get_coinbase_transaction(self) -> Transaction:
        """
        Ottieni COINBASE transaction.
        
        Returns:
            Transaction: Prima transazione (COINBASE)
        
        Examples:
            >>> block = Block(header, [coinbase])
            >>> coinbase_tx = block.get_coinbase_transaction()
            >>> coinbase_tx.is_coinbase()
            True
        """
        return self.transactions[0]
    
    def get_transaction_count(self) -> int:
        """Numero transazioni nel blocco"""
        return len(self.transactions)
    
    def contains_transaction(self, txid: str) -> bool:
        """
        Check se blocco contiene transazione.
        
        Args:
            txid: Transaction ID da cercare
        
        Returns:
            bool: True se presente
        """
        return any(tx.compute_txid() == txid for tx in self.transactions)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Serializza block in dict.
        
        Returns:
            dict: Block serializzato
        """
        return {
            "header": self.header.to_dict(),
            "transactions": [tx.to_dict(include_txid=True) for tx in self.transactions],
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Block:
        """
        Deserializza block da dict.
        
        Args:
            data: Dict serializzato
        
        Returns:
            Block: Instance deserializzata
        """
        return cls(
            header=BlockHeader.from_dict(data["header"]),
            transactions=[
                Transaction.from_dict(tx_data)
                for tx_data in data["transactions"]
            ],
        )
    
    def __repr__(self) -> str:
        """Safe repr"""
        block_hash = self.compute_block_hash()[:16]
        return (
            f"Block(height={self.header.height}, "
            f"hash={block_hash}..., "
            f"txs={len(self.transactions)})"
        )


# ============================================================================
# UTXO KEY
# ============================================================================

@dataclass(frozen=True, order=True)
class UTXOKey:
    """
    Chiave univoca per identificare UTXO.
    
    UTXO è identificato da:
    - TXID transazione che lo crea
    - Index output nella transazione
    
    Attributes:
        txid (str): Transaction ID (64 hex)
        output_index (int): Indice output (0, 1, 2, ...)
    
    Examples:
        >>> utxo_key = UTXOKey("abc123...", 0)
        >>> utxo_key.txid
        'abc123...'
        >>> utxo_key.output_index
        0
    """
    
    txid: str
    output_index: int
    
    def __post_init__(self):
        """Validazione"""
        if not self.txid or len(self.txid) != 64:
            raise ValidationError(
                "txid must be 64 hex characters",
                code="INVALID_UTXO_TXID"
            )
        
        if self.output_index < 0:
            raise ValidationError(
                f"output_index must be non-negative, got {self.output_index}",
                code="INVALID_OUTPUT_INDEX"
            )
    
    def __str__(self) -> str:
        """String representation"""
        return f"{self.txid}:{self.output_index}"
    
    def __repr__(self) -> str:
        """Repr"""
        return f"UTXOKey({self.txid[:16]}...:{self.output_index})"


# ============================================================================
# EXPORT
# ============================================================================

__all__ = [
    # Transaction components
    "TxInput",
    "TxOutput",
    "Transaction",
    
    # Block components
    "BlockHeader",
    "Block",
    
    # UTXO
    "UTXOKey",
]
