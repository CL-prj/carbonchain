"""
CarbonChain - Transaction & Block Validation
==============================================
Sistema validazione completo per transazioni e blocchi.

Security Level: CRITICAL
Last Updated: 2025-11-27
Version: 1.0.0

Validation Rules:
- Transaction: firma, balance, double-spend, size
- Block: PoW, merkle root, timestamp, tx validity
- Certificate: uniqueness, capacity, metadata
- Compensation: certificate requirement, non-reusability

IMPORTANTE: Ogni modifica alle rules richiede security audit.
"""

from typing import Optional, List, Dict, Set, Any
import time

# Internal imports
from carbon_chain.domain.models import (
    Transaction,
    TxInput,
    TxOutput,
    Block,
    BlockHeader,
    UTXOKey,
)
from carbon_chain.domain.utxo import UTXOSet
from carbon_chain.domain.pow import verify_block_pow, get_block_subsidy
from carbon_chain.domain.crypto_core import verify_certificate_hash
from carbon_chain.domain.addressing import validate_address
from carbon_chain.constants import (
    TxType,
    MAX_BLOCK_SIZE,
    MAX_TX_SIZE,
    MAX_TXS_PER_BLOCK,
    validate_amount,
    MAX_FUTURE_BLOCK_TIME,
    REQUIRED_CERT_FIELDS,
)
from carbon_chain.errors import (
    ValidationError,
    InvalidTransactionError,
    InvalidBlockError,
    InsufficientFundsError,
    DoubleSpendError,
    InvalidSignatureError,
    TxSizeExceededError,
    BlockSizeExceededError,
    InvalidPoWError,
    CertificateError,
    CertificateDuplicateError,
    CompensationError,
    CompensationNotCertifiedError,
    CompensationAlreadyUsedError,
)
from carbon_chain.logging_setup import get_logger, PerformanceLogger
from carbon_chain.config import ChainSettings


# ============================================================================
# MODULE LOGGER
# ============================================================================

logger = get_logger("validation")


# ============================================================================
# TRANSACTION VALIDATION
# ============================================================================

class TransactionValidator:
    """
    Validatore transazioni.
    
    Valida:
    - Firma digitale
    - Balance sufficiente
    - No double-spend
    - Limiti size
    - Rules tipo-specifiche
    
    Attributes:
        config: Chain configuration
        utxo_set: UTXO set per balance check
    """
    
    def __init__(self, config: ChainSettings, utxo_set: UTXOSet):
        self.config = config
        self.utxo_set = utxo_set
    
    def validate_transaction(
        self,
        tx: Transaction,
        check_signatures: bool = True,
        check_utxos: bool = True,
        mempool_utxos: Optional[Set[UTXOKey]] = None
    ) -> None:
        """
        Validazione completa transazione.
        
        Args:
            tx: Transaction da validare
            check_signatures: Se True, verifica firme
            check_utxos: Se True, verifica UTXO disponibili
            mempool_utxos: UTXO già spesi in mempool (double-spend check)
        
        Raises:
            InvalidTransactionError: Se validazione fallisce
        
        Validation Steps:
            1. Struttura base
            2. Dimensione
            3. Amount validi
            4. Tipo-specifiche rules
            5. Firme (opzionale)
            6. UTXO disponibili (opzionale)
            7. Balance
        
        Examples:
            >>> from carbon_chain.domain.utxo import UTXOSet
            >>> from carbon_chain.config import get_settings
            >>> 
            >>> config = get_settings()
            >>> utxo_set = UTXOSet()
            >>> validator = TransactionValidator(config, utxo_set)
            >>> 
            >>> # Valida COINBASE
            >>> coinbase = Transaction(
            ...     tx_type=TxType.COINBASE,
            ...     inputs=[],
            ...     outputs=[TxOutput(50, "addr1")],
            ...     timestamp=int(time.time())
            ... )
            >>> validator.validate_transaction(coinbase, check_utxos=False)
        """
        with PerformanceLogger(logger, f"validate_transaction({tx.tx_type.name})"):
            
            # 1. Validazione struttura base
            self._validate_structure(tx)
            
            # 2. Validazione dimensione
            self._validate_size(tx)
            
            # 3. Validazione amount
            self._validate_amounts(tx)
            
            # 4. Validazione tipo-specifica
            self._validate_by_type(tx)
            
            # 5. Validazione firme (se richiesto)
            if check_signatures and self.config.verify_signatures:
                self._validate_signatures(tx)
            
            # 6. Validazione UTXO (se richiesto)
            if check_utxos:
                self._validate_utxo_availability(tx, mempool_utxos)
            
            # 7. Validazione balance
            if check_utxos and not tx.is_coinbase():
                self._validate_balance(tx)
            
            logger.debug(
                f"Transaction validated successfully",
                extra_data={
                    "txid": tx.compute_txid()[:16] + "...",
                    "type": tx.tx_type.name
                }
            )
    
    def _validate_structure(self, tx: Transaction) -> None:
        """Validazione struttura base"""
        # Timestamp non nel futuro
        current_time = int(time.time())
        max_future = current_time + MAX_FUTURE_BLOCK_TIME
        
        if tx.timestamp > max_future:
            raise InvalidTransactionError(
                f"Transaction timestamp too far in future: {tx.timestamp}",
                code="TIMESTAMP_FUTURE"
            )
        
        # COINBASE: no inputs
        if tx.is_coinbase():
            if tx.inputs:
                raise InvalidTransactionError(
                    "COINBASE transaction must have no inputs",
                    code="COINBASE_HAS_INPUTS"
                )
        
        # Non-COINBASE: almeno 1 input
        else:
            if not tx.inputs:
                raise InvalidTransactionError(
                    f"{tx.tx_type.name} transaction must have inputs",
                    code="NO_INPUTS"
                )
        
        # BURN può avere 0 outputs
        if not tx.is_burn():
            if not tx.outputs:
                raise InvalidTransactionError(
                    f"{tx.tx_type.name} transaction must have outputs",
                    code="NO_OUTPUTS"
                )
    
    def _validate_size(self, tx: Transaction) -> None:
        """Validazione dimensione"""
        import json
        tx_size = len(json.dumps(tx.to_dict()).encode('utf-8'))
        
        if tx_size > MAX_TX_SIZE:
            raise TxSizeExceededError(
                f"Transaction size {tx_size} exceeds max {MAX_TX_SIZE}",
                code="TX_TOO_LARGE",
                details={"size": tx_size, "max": MAX_TX_SIZE}
            )
    
    def _validate_amounts(self, tx: Transaction) -> None:
        """Validazione amount output"""
        for idx, output in enumerate(tx.outputs):
            if not validate_amount(output.amount):
                raise InvalidTransactionError(
                    f"Invalid output amount at index {idx}: {output.amount}",
                    code="INVALID_OUTPUT_AMOUNT",
                    details={"index": idx, "amount": output.amount}
                )
            
            # Validazione address
            if not validate_address(output.address):
                raise InvalidTransactionError(
                    f"Invalid output address at index {idx}: {output.address}",
                    code="INVALID_OUTPUT_ADDRESS",
                    details={"index": idx, "address": output.address[:16]}
                )
    
    def _validate_by_type(self, tx: Transaction) -> None:
        """Validazione tipo-specifica"""
        if tx.is_coinbase():
            self._validate_coinbase(tx)
        
        elif tx.is_transfer():
            self._validate_transfer(tx)
        
        elif tx.is_certificate_assignment():
            self._validate_certificate_assignment(tx)
        
        elif tx.is_compensation():
            self._validate_compensation(tx)
        
        elif tx.is_burn():
            self._validate_burn(tx)
    
    def _validate_coinbase(self, tx: Transaction) -> None:
        """Validazione COINBASE"""
        # Esattamente 1 output
        if len(tx.outputs) != 1:
            raise InvalidTransactionError(
                f"COINBASE must have exactly 1 output, got {len(tx.outputs)}",
                code="COINBASE_INVALID_OUTPUTS"
            )
        
        # Amount sarà verificato dal block validator (subsidy)
    
    def _validate_transfer(self, tx: Transaction) -> None:
        """Validazione TRANSFER"""
        # Almeno 1 input, 1 output
        if not tx.inputs or not tx.outputs:
            raise InvalidTransactionError(
                "TRANSFER must have inputs and outputs",
                code="TRANSFER_INCOMPLETE"
            )
    
    def _validate_certificate_assignment(self, tx: Transaction) -> None:
        """Validazione ASSIGN_CERT"""
        # Almeno 1 output certificato
        certified_outputs = [out for out in tx.outputs if out.is_certified]
        
        if not certified_outputs:
            raise CertificateError(
                "ASSIGN_CERT must have at least one certified output",
                code="NO_CERTIFIED_OUTPUT"
            )
        
        # Valida ogni output certificato
        for idx, output in enumerate(certified_outputs):
            # Check campi required
            if not output.certificate_id:
                raise CertificateError(
                    f"Certified output {idx} missing certificate_id",
                    code="MISSING_CERT_ID"
                )
            
            if not output.certificate_hash:
                raise CertificateError(
                    f"Certified output {idx} missing certificate_hash",
                    code="MISSING_CERT_HASH"
                )
            
            if not output.certificate_total_kg:
                raise CertificateError(
                    f"Certified output {idx} missing certificate_total_kg",
                    code="MISSING_TOTAL_KG"
                )
            
            # Amount non deve superare total_kg
            if output.amount > output.certificate_total_kg:
                raise CertificateError(
                    f"Output amount {output.amount} exceeds certificate total_kg {output.certificate_total_kg}",
                    code="AMOUNT_EXCEEDS_CERT_CAPACITY"
                )
            
            # Valida metadata
            if output.certificate_metadata:
                for field in REQUIRED_CERT_FIELDS:
                    if field not in output.certificate_metadata:
                        raise CertificateError(
                            f"Missing required certificate field: {field}",
                            code="MISSING_CERT_FIELD",
                            details={"field": field}
                        )
    
    def _validate_compensation(self, tx: Transaction) -> None:
        """Validazione ASSIGN_COMPENSATION"""
        # Almeno 1 output compensato
        compensated_outputs = [out for out in tx.outputs if out.is_compensated]
        
        if not compensated_outputs:
            raise CompensationError(
                "ASSIGN_COMPENSATION must have at least one compensated output",
                code="NO_COMPENSATED_OUTPUT"
            )
        
        # Valida ogni output compensato
        for idx, output in enumerate(compensated_outputs):
            # MUST be certified
            if not output.is_certified:
                raise CompensationNotCertifiedError(
                    f"Compensated output {idx} must also be certified",
                    code="COMP_WITHOUT_CERT"
                )
            
            # Check project_id
            if not output.compensation_project_id:
                raise CompensationError(
                    f"Compensated output {idx} missing project_id",
                    code="MISSING_PROJECT_ID"
                )
            
            # Check metadata
            if not output.compensation_metadata:
                raise CompensationError(
                    f"Compensated output {idx} missing metadata",
                    code="MISSING_COMP_METADATA"
                )
    
    def _validate_burn(self, tx: Transaction) -> None:
        """Validazione BURN"""
        # Must have inputs
        if not tx.inputs:
            raise InvalidTransactionError(
                "BURN must have inputs",
                code="BURN_NO_INPUTS"
            )
        
        # BURN può avere 0 outputs (coin distrutte)
        # Oppure change output
    
    def _validate_signatures(self, tx: Transaction) -> None:
        """Validazione firme input"""
        if tx.is_coinbase():
            # COINBASE non ha firme
            return
        
        # Import qui per evitare circular import
        from carbon_chain.domain.keypairs import KeyPair
        from carbon_chain.domain.crypto_core import get_crypto_provider
        from carbon_chain.domain.addressing import public_key_to_address
        
        # Create signing message (tx senza firme)
        import json
        tx_dict = tx.to_dict(include_signatures=False)
        signing_message = json.dumps(tx_dict, sort_keys=True).encode('utf-8')
        
        # Verifica ogni input
        for idx, inp in enumerate(tx.inputs):
            if not inp.is_signed():
                raise InvalidSignatureError(
                    f"Input {idx} not signed",
                    code="INPUT_NOT_SIGNED",
                    details={"input_index": idx}
                )
            
            # Verifica firma
            try:
                provider = get_crypto_provider(self.config.crypto_algorithm)
                is_valid = provider.verify(
                    signing_message,
                    inp.signature,
                    inp.public_key
                )
                
                if not is_valid:
                    raise InvalidSignatureError(
                        f"Invalid signature for input {idx}",
                        code="SIGNATURE_INVALID",
                        details={"input_index": idx}
                    )
                
                # Verifica che public_key corrisponda a address UTXO
                utxo_key = UTXOKey(inp.prev_txid, inp.prev_output_index)
                utxo = self.utxo_set.get_utxo(utxo_key)
                
                if utxo:
                    # Deriva address da public key
                    derived_address = public_key_to_address(
                        inp.public_key,
                        testnet=self.config.is_testnet()
                    )
                    
                    if derived_address != utxo.address:
                        raise InvalidSignatureError(
                            f"Public key does not match UTXO address for input {idx}",
                            code="PUBKEY_ADDRESS_MISMATCH",
                            details={
                                "input_index": idx,
                                "expected_address": utxo.address[:16],
                                "derived_address": derived_address[:16]
                            }
                        )
            
            except Exception as e:
                if isinstance(e, InvalidSignatureError):
                    raise
                
                raise InvalidSignatureError(
                    f"Signature verification failed for input {idx}: {e}",
                    code="SIGNATURE_VERIFICATION_FAILED",
                    details={"input_index": idx, "error": str(e)}
                )
    
    def _validate_utxo_availability(
        self,
        tx: Transaction,
        mempool_utxos: Optional[Set[UTXOKey]] = None
    ) -> None:
        """Validazione disponibilità UTXO"""
        if tx.is_coinbase():
            return
        
        mempool_utxos = mempool_utxos or set()
        
        for idx, inp in enumerate(tx.inputs):
            utxo_key = UTXOKey(inp.prev_txid, inp.prev_output_index)
            
            # Check UTXO esiste
            if not self.utxo_set.contains(utxo_key):
                raise InvalidTransactionError(
                    f"Input {idx} references non-existent UTXO: {utxo_key}",
                    code="UTXO_NOT_FOUND",
                    details={"input_index": idx, "utxo_key": str(utxo_key)}
                )
            
            # Check non già speso in mempool
            if utxo_key in mempool_utxos:
                raise DoubleSpendError(
                    f"Input {idx} double-spend detected: {utxo_key}",
                    code="DOUBLE_SPEND_MEMPOOL",
                    details={"input_index": idx, "utxo_key": str(utxo_key)}
                )
            
            # Check UTXO spendibile
            output = self.utxo_set.get_utxo(utxo_key)
            if not output.is_spendable():
                raise InvalidTransactionError(
                    f"Input {idx} references non-spendable UTXO (compensated or burned)",
                    code="UTXO_NOT_SPENDABLE",
                    details={
                        "input_index": idx,
                        "is_compensated": output.is_compensated,
                        "is_burned": output.is_burned
                    }
                )
    
    def _validate_balance(self, tx: Transaction) -> None:
        """Validazione balance (input >= output)"""
        # Calcola total input
        total_input = 0
        for inp in tx.inputs:
            utxo_key = UTXOKey(inp.prev_txid, inp.prev_output_index)
            output = self.utxo_set.get_utxo(utxo_key)
            
            if output:
                total_input += output.amount
        
        # Calcola total output
        total_output = tx.total_output_amount()
        
        # Input >= Output (differenza = fee implicita)
        if total_input < total_output:
            raise InsufficientFundsError(
                f"Insufficient funds: input={total_input}, output={total_output}",
                code="INSUFFICIENT_FUNDS",
                details={
                    "input_amount": total_input,
                    "output_amount": total_output,
                    "deficit": total_output - total_input
                }
            )
        
        # Log fee se presente
        if total_input > total_output:
            fee = total_input - total_output
            logger.debug(
                f"Transaction includes fee",
                extra_data={"fee": fee}
            )


# ============================================================================
# BLOCK VALIDATION
# ============================================================================

class BlockValidator:
    """
    Validatore blocchi.
    
    Valida:
    - PoW
    - Merkle root
    - Timestamp
    - Tutte le transazioni
    - Block size
    """
    
    def __init__(
        self,
        config: ChainSettings,
        utxo_set: UTXOSet,
        tx_validator: TransactionValidator
    ):
        self.config = config
        self.utxo_set = utxo_set
        self.tx_validator = tx_validator
    
    def validate_block(
        self,
        block: Block,
        previous_block: Optional[Block] = None,
        check_pow: bool = True
    ) -> None:
        """
        Validazione completa blocco.
        
        Args:
            block: Block da validare
            previous_block: Blocco precedente (per continuity check)
            check_pow: Se True, verifica PoW
        
        Raises:
            InvalidBlockError: Se validazione fallisce
        
        Validation Steps:
            1. Header structure
            2. PoW (opzionale)
            3. Merkle root
            4. Timestamp
            5. Block size
            6. COINBASE subsidy
            7. Tutte le transazioni
        
        Examples:
            >>> validator = BlockValidator(config, utxo_set, tx_validator)
            >>> block = Block(header, transactions)
            >>> validator.validate_block(block)
        """
        with PerformanceLogger(logger, f"validate_block(height={block.header.height})"):
            
            # 1. Validazione header
            self._validate_header(block.header, previous_block)
            
            # 2. Validazione PoW
            if check_pow and not self.config.dev_mode:
                if not verify_block_pow(block.header):
                    raise InvalidPoWError(
                        f"Block {block.header.height} has invalid PoW",
                        code="INVALID_POW"
                    )
            
            # 3. Validazione merkle root
            self._validate_merkle_root(block)
            
            # 4. Validazione timestamp
            self._validate_timestamp(block.header, previous_block)
            
            # 5. Validazione size
            self._validate_block_size(block)
            
            # 6. Validazione COINBASE
            self._validate_coinbase_subsidy(block)
            
            # 7. Validazione transazioni
            self._validate_transactions(block)
            
            logger.info(
                f"Block validated successfully",
                extra_data={
                    "height": block.header.height,
                    "hash": block.compute_block_hash()[:16] + "...",
                    "tx_count": len(block.transactions)
                }
            )
    
    def _validate_header(
        self,
        header: BlockHeader,
        previous_block: Optional[Block]
    ) -> None:
        """Validazione header"""
        # Check previous hash
        if previous_block:
            expected_prev_hash = previous_block.compute_block_hash()
            
            if header.previous_hash != expected_prev_hash:
                raise InvalidBlockError(
                    f"Invalid previous_hash: expected {expected_prev_hash[:16]}, got {header.previous_hash[:16]}",
                    code="INVALID_PREV_HASH"
                )
            
            # Check height continuity
            expected_height = previous_block.header.height + 1
            if header.height != expected_height:
                raise InvalidBlockError(
                    f"Invalid height: expected {expected_height}, got {header.height}",
                    code="INVALID_HEIGHT"
                )
    
    def _validate_merkle_root(self, block: Block) -> None:
        """Validazione merkle root"""
        computed_merkle = block.compute_merkle_root()
        
        if computed_merkle != block.header.merkle_root:
            raise InvalidBlockError(
                f"Merkle root mismatch: expected {computed_merkle.hex()[:16]}, got {block.header.merkle_root.hex()[:16]}",
                code="MERKLE_ROOT_MISMATCH"
            )
    
    def _validate_timestamp(
        self,
        header: BlockHeader,
        previous_block: Optional[Block]
    ) -> None:
        """Validazione timestamp"""
        current_time = int(time.time())
        
        # Non troppo nel futuro
        if header.timestamp > current_time + MAX_FUTURE_BLOCK_TIME:
            raise InvalidBlockError(
                f"Block timestamp too far in future: {header.timestamp}",
                code="TIMESTAMP_FUTURE"
            )
        
        # Dopo blocco precedente
        if previous_block:
            if header.timestamp < previous_block.header.timestamp:
                raise InvalidBlockError(
                    f"Block timestamp {header.timestamp} before previous {previous_block.header.timestamp}",
                    code="TIMESTAMP_BEFORE_PREV"
                )
    
    def _validate_block_size(self, block: Block) -> None:
        """Validazione size"""
        import json
        block_size = len(json.dumps(block.to_dict()).encode('utf-8'))
        
        if block_size > MAX_BLOCK_SIZE:
            raise BlockSizeExceededError(
                f"Block size {block_size} exceeds max {MAX_BLOCK_SIZE}",
                code="BLOCK_TOO_LARGE"
            )
        
        # Check numero transazioni
        if len(block.transactions) > MAX_TXS_PER_BLOCK:
            raise InvalidBlockError(
                f"Block has {len(block.transactions)} transactions, max is {MAX_TXS_PER_BLOCK}",
                code="TOO_MANY_TXS"
            )
    
    def _validate_coinbase_subsidy(self, block: Block) -> None:
        """Validazione COINBASE subsidy"""
        coinbase = block.get_coinbase_transaction()
        
        # Calcola subsidy atteso
        expected_subsidy = get_block_subsidy(
            block.header.height,
            self.config.halving_interval,
            self.config.initial_subsidy
        )
        
        # Subsidy effettivo (output COINBASE)
        actual_subsidy = coinbase.total_output_amount()
        
        # Subsidy può essere <= expected (miner può donare)
        if actual_subsidy > expected_subsidy:
            raise InvalidBlockError(
                f"COINBASE subsidy {actual_subsidy} exceeds expected {expected_subsidy}",
                code="INVALID_SUBSIDY",
                details={
                    "actual": actual_subsidy,
                    "expected": expected_subsidy
                }
            )
    
    def _validate_transactions(self, block: Block) -> None:
        """Validazione tutte le transazioni"""
        # Track UTXO spesi nel blocco (double-spend check)
        spent_utxos: Set[UTXOKey] = set()
        
        for idx, tx in enumerate(block.transactions):
            # Valida transazione
            self.tx_validator.validate_transaction(
                tx,
                check_signatures=True,
                check_utxos=True,
                mempool_utxos=spent_utxos
            )
            
            # Aggiungi input a spent_utxos
            for inp in tx.inputs:
                utxo_key = UTXOKey(inp.prev_txid, inp.prev_output_index)
                spent_utxos.add(utxo_key)


# ============================================================================
# CERTIFICATE VALIDATION
# ============================================================================

class CertificateValidator:
    """
    Validatore certificati CO2.
    
    Valida:
    - Uniqueness (hash)
    - Capacity limits
    - Required fields
    """
    
    def __init__(self, config: ChainSettings):
        self.config = config
        # Index certificati già emessi (certificate_hash → txid)
        self.certificate_index: Dict[bytes, str] = {}
    
    def validate_certificate(
        self,
        cert_id: str,
        cert_hash: bytes,
        total_kg: int,
        issued_kg: int,
        metadata: Dict[str, Any]
    ) -> None:
        """
        Valida certificato CO2.
        
        Args:
            cert_id: Certificate ID
            cert_hash: Hash univoco
            total_kg: Capacità totale
            issued_kg: Kg emessi (questo tx)
            metadata: Metadata certificato
        
        Raises:
            CertificateError: Se validazione fallisce
        """
        # 1. Check uniqueness (solo se enforce)
        if self.config.enforce_cert_uniqueness:
            if cert_hash in self.certificate_index:
                existing_txid = self.certificate_index[cert_hash]
                raise CertificateDuplicateError(
                    f"Certificate hash {cert_hash.hex()[:16]} already exists in tx {existing_txid[:16]}",
                    code="CERT_DUPLICATE",
                    details={
                        "cert_id": cert_id,
                        "existing_txid": existing_txid[:16]
                    }
                )
        
        # 2. Check capacity
        if issued_kg > total_kg:
            raise CertificateError(
                f"Issued kg {issued_kg} exceeds total capacity {total_kg}",
                code="CERT_CAPACITY_EXCEEDED"
            )
        
        # 3. Check required fields
        for field in REQUIRED_CERT_FIELDS:
            if field not in metadata:
                raise CertificateError(
                    f"Missing required certificate field: {field}",
                    code="MISSING_CERT_FIELD",
                    details={"field": field}
                )
    
    def register_certificate(self, cert_hash: bytes, txid: str) -> None:
        """Registra certificato nell'index"""
        self.certificate_index[cert_hash] = txid
        
        logger.debug(
            f"Certificate registered",
            extra_data={
                "cert_hash": cert_hash.hex()[:16] + "...",
                "txid": txid[:16] + "..."
            }
        )


# ============================================================================
# EXPORT
# ============================================================================

__all__ = [
    "TransactionValidator",
    "BlockValidator",
    "CertificateValidator",
]
