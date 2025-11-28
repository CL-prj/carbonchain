"""
CarbonChain - Blockchain Core
===============================
Classe principale blockchain con gestione completa chain state.

Security Level: CRITICAL
Last Updated: 2025-11-27
Version: 1.0.0

Features:
- Add/validate blocks
- UTXO set management
- Chain reorganization
- Mining support
- Query API (blocks, tx, balance)
- Certificate/project tracking
"""

from __future__ import annotations
from typing import Optional, List, Dict, Tuple, Set
from dataclasses import dataclass
import time
import threading

# Internal imports
from carbon_chain.domain.models import (
    Block,
    BlockHeader,
    Transaction,
    TxOutput,
    TxInput,
    UTXOKey,
)
from carbon_chain.domain.utxo import UTXOSet
from carbon_chain.domain.pow import (
    mine_block_header,
    calculate_next_difficulty,
    get_block_subsidy,
)
from carbon_chain.domain.validation import (
    TransactionValidator,
    BlockValidator,
    CertificateValidator,
)
from carbon_chain.domain.genesis import create_genesis_block
from carbon_chain.constants import (
    TxType,
    calculate_subsidy,
    satoshi_to_coin,
    HALVING_INTERVAL,
    BLOCK_TIME_TARGET,
    DIFFICULTY_ADJUSTMENT_INTERVAL,
)
from carbon_chain.errors import (
    BlockchainError,
    InvalidBlockError,
    GenesisError,
    ChainSyncError,
)
from carbon_chain.logging_setup import get_logger, PerformanceLogger, AuditLogger
from carbon_chain.config import ChainSettings


# ============================================================================
# MODULE LOGGER
# ============================================================================

logger = get_logger("blockchain")
audit_logger = AuditLogger()


# ============================================================================
# BLOCKCHAIN CLASS
# ============================================================================

class Blockchain:
    """
    Blockchain principale.
    
    Gestisce:
    - Chain state (blocks, UTXO set)
    - Block validation & addition
    - Mining
    - Query API
    - Certificate/project tracking
    
    Attributes:
        config: Chain configuration
        blocks: Lista blocchi (ordinata per height)
        utxo_set: Set UTXO correnti
        current_difficulty: Difficulty corrente
        total_supply: Supply totale in circolazione
    
    Thread Safety:
        - Protected da RLock per operazioni critiche
        - Safe per multi-threading
    
    Examples:
        >>> from carbon_chain.config import get_settings
        >>> config = get_settings()
        >>> blockchain = Blockchain(config)
        >>> blockchain.get_height()
        0  # Genesis block
    """
    
    def __init__(self, config: ChainSettings, storage=None):
        """
        Inizializza blockchain.
        
        Args:
            config: Chain configuration
            storage: Storage backend (opzionale)
        """
        self.config = config
        self.storage = storage
        
        # Chain state
        self.blocks: List[Block] = []
        self.utxo_set = UTXOSet()
        
        # Validators
        self.tx_validator = TransactionValidator(config, self.utxo_set)
        self.block_validator = BlockValidator(config, self.utxo_set, self.tx_validator)
        self.cert_validator = CertificateValidator(config)
        
        # Difficulty tracking
        self.current_difficulty = config.pow_difficulty_initial
        
        # Supply tracking
        self.total_supply = 0
        
        # Thread safety
        self._lock = threading.RLock()
        
        # Certificate tracking (cert_id → info)
        self._certificate_index: Dict[str, Dict] = {}
        
        # Project tracking (project_id → info)
        self._project_index: Dict[str, Dict] = {}
        
        # Initialize con genesis block
        self._initialize_with_genesis()
        
        logger.info(
            "Blockchain initialized",
            extra_data={
                "network": config.network,
                "genesis_hash": self.blocks[0].compute_block_hash()[:16] + "...",
                "difficulty": self.current_difficulty
            }
        )
    
    def _initialize_with_genesis(self) -> None:
        """Inizializza con genesis block"""
        try:
            genesis = create_genesis_block(self.config)
            
            # Add genesis (skip validation)
            self.add_block(genesis, skip_validation=True)
            
            logger.info(
                "Genesis block created",
                extra_data={
                    "height": 0,
                    "hash": genesis.compute_block_hash()[:16] + "...",
                    "subsidy": genesis.get_coinbase_transaction().total_output_amount()
                }
            )
        
        except Exception as e:
            raise GenesisError(f"Failed to create genesis block: {e}")
    
    # ========================================================================
    # BLOCK OPERATIONS
    # ========================================================================
    
    def add_block(self, block: Block, skip_validation: bool = False) -> None:
        """
        Aggiungi blocco alla chain.
        
        Args:
            block: Block da aggiungere
            skip_validation: Se True, skip validation (solo per genesis)
        
        Raises:
            InvalidBlockError: Se blocco invalido
            BlockchainError: Se errore aggiunta
        
        Thread Safety:
            Atomic operation (protected da lock)
        
        Examples:
            >>> blockchain = Blockchain(config)
            >>> # Mine nuovo blocco
            >>> new_block = blockchain.mine_block("miner_addr", [])
            >>> blockchain.add_block(new_block)
        """
        with self._lock:
            with PerformanceLogger(logger, f"add_block(height={block.header.height})"):
                
                # Validazione (se richiesta)
                if not skip_validation:
                    previous_block = self.blocks[-1] if self.blocks else None
                    
                    self.block_validator.validate_block(
                        block,
                        previous_block=previous_block,
                        check_pow=not self.config.dev_mode
                    )
                
                # Check height sequenziale
                expected_height = len(self.blocks)
                if block.header.height != expected_height:
                    raise InvalidBlockError(
                        f"Invalid block height: expected {expected_height}, got {block.header.height}",
                        code="HEIGHT_MISMATCH"
                    )
                
                # Applica transazioni a UTXO set
                for tx in block.transactions:
                    self.utxo_set.apply_transaction(tx)
                    
                    # Update certificate index
                    if tx.is_certificate_assignment():
                        self._update_certificate_index(tx, block.header.height)
                    
                    # Update project index
                    if tx.is_compensation():
                        self._update_project_index(tx, block.header.height)
                
                # Aggiungi blocco
                self.blocks.append(block)
                
                # Update supply
                self.total_supply = self.utxo_set.total_supply()
                
                # Update difficulty (se necessario)
                if self._should_adjust_difficulty():
                    self._adjust_difficulty()
                
                # Audit log
                audit_logger.log_block_added(
                    block.header.height,
                    block.compute_block_hash(),
                    len(block.transactions)
                )
                
                logger.info(
                    f"Block added to chain",
                    extra_data={
                        "height": block.header.height,
                        "hash": block.compute_block_hash()[:16] + "...",
                        "tx_count": len(block.transactions),
                        "supply": self.total_supply,
                        "utxos": self.utxo_set.utxo_count()
                    }
                )
    
    def get_block(self, height: int) -> Optional[Block]:
        """
        Ottieni blocco per height.
        
        Args:
            height: Block height (0 = genesis)
        
        Returns:
            Block: Blocco se presente, None altrimenti
        
        Examples:
            >>> blockchain = Blockchain(config)
            >>> genesis = blockchain.get_block(0)
            >>> genesis.header.height
            0
        """
        with self._lock:
            if 0 <= height < len(self.blocks):
                return self.blocks[height]
            return None
        
    def get_block_by_height(self, height: int) -> Optional[Block]:
        """
        Ottieni blocco per height (alias per get_block).
        
        Args:
            height: Block height
        
        Returns:
            Block: Blocco se presente
        """
        return self.get_block(height)
    
    def get_transaction(self, txid: str) -> Optional[Transaction]:
        """
        Trova transazione per TXID.
        
        Args:
            txid: Transaction ID (hex string o bytes)
        
        Returns:
            Transaction: Se trovata, None altrimenti
        
        Performance:
            O(n*m) - scansione lineare blocchi + transazioni
        
        Examples:
            >>> blockchain = Blockchain(config)
            >>> tx = blockchain.get_transaction("abc123...")
        """
        with self._lock:
            # Converti txid in string se bytes
            if isinstance(txid, bytes):
                txid = txid.hex()
            
            # Cerca in tutti i blocchi
            for block in self.blocks:
                for tx in block.transactions:
                    if tx.compute_txid() == txid:
                        return tx
            
            return None
    
    def get_total_supply(self) -> int:
        """
        Alias per get_supply() - compatibilità.
        
        Returns:
            int: Total supply in Satoshi
        """
        return self.get_supply()
    
    def get_latest_block(self) -> Optional[Block]:
        """
        Ottieni ultimo blocco.
        
        Returns:
            Block: Ultimo blocco, o None se chain vuota
        """
        with self._lock:
            return self.blocks[-1] if self.blocks else None
    
    def get_height(self) -> int:
        """
        Ottieni altezza chain.
        
        Returns:
            int: Height (0 = solo genesis)
        
        Examples:
            >>> blockchain = Blockchain(config)
            >>> blockchain.get_height()
            0
        """
        with self._lock:
            return len(self.blocks) - 1
    
    def get_block_by_hash(self, block_hash: str) -> Optional[Block]:
        """
        Ottieni blocco per hash.
        
        Args:
            block_hash: Block hash (64 hex)
        
        Returns:
            Block: Blocco se trovato
        
        Performance:
            O(n) - scansione lineare chain
        """
        with self._lock:
            for block in self.blocks:
                if block.compute_block_hash() == block_hash:
                    return block
            return None
    
    # ========================================================================
    # MINING
    # ========================================================================
    
    def mine_block(
        self,
        miner_address: str,
        transactions: List[Transaction],
        timeout_seconds: Optional[int] = None
    ) -> Optional[Block]:
        """
        Mina nuovo blocco.
        
        Steps:
            1. Valida transazioni
            2. Crea COINBASE
            3. Calcola merkle root
            4. Crea header
            5. Mine (trova nonce)
            6. Return blocco minato
        
        Args:
            miner_address: Address per reward
            transactions: Transazioni da includere (no COINBASE)
            timeout_seconds: Timeout mining (None = no limit)
        
        Returns:
            Block: Blocco minato, o None se timeout
        
        Examples:
            >>> blockchain = Blockchain(config)
            >>> block = blockchain.mine_block("miner_addr", [])
            >>> if block:
            ...     blockchain.add_block(block)
        """
        with self._lock:
            logger.info(
                "Mining started",
                extra_data={
                    "height": self.get_height() + 1,
                    "tx_count": len(transactions),
                    "difficulty": self.current_difficulty
                }
            )
            
            # 1. Valida transazioni
            valid_transactions = []
            for tx in transactions:
                try:
                    self.tx_validator.validate_transaction(tx)
                    valid_transactions.append(tx)
                except Exception as e:
                    logger.warning(
                        f"Transaction validation failed during mining",
                        extra_data={"txid": tx.compute_txid()[:16], "error": str(e)}
                    )
            
            # 2. Crea COINBASE
            subsidy = calculate_subsidy(self.get_height() + 1)
            
            coinbase = Transaction(
                tx_type=TxType.COINBASE,
                inputs=[],
                outputs=[TxOutput(amount=subsidy, address=miner_address)],
                timestamp=int(time.time()),
                metadata={"height": self.get_height() + 1}
            )
            
            # 3. Componi lista transazioni (COINBASE prima)
            all_transactions = [coinbase] + valid_transactions
            
            # 4. Crea header template
            previous_block = self.get_latest_block()
            previous_hash = previous_block.compute_block_hash() if previous_block else "0" * 64
            
            # Crea blocco temporaneo per merkle
            temp_block = Block(
                header=BlockHeader(
                    version=1,
                    previous_hash=previous_hash,
                    merkle_root=b'\x00' * 32,  # Temporaneo
                    timestamp=int(time.time()),
                    difficulty=self.current_difficulty,
                    nonce=0,
                    height=self.get_height() + 1
                ),
                transactions=all_transactions
            )
            
            # Calcola merkle root
            merkle_root = temp_block.compute_merkle_root()
            
            # 5. Crea header finale
            header_template = BlockHeader(
                version=1,
                previous_hash=previous_hash,
                merkle_root=merkle_root,
                timestamp=int(time.time()),
                difficulty=self.current_difficulty,
                nonce=0,
                height=self.get_height() + 1
            )
            
            # 6. Mine header (trova nonce)
            mined_header = mine_block_header(
                header_template,
                timeout_seconds=timeout_seconds
            )
            
            if not mined_header:
                logger.warning("Mining timeout or failed")
                return None
            
            # 7. Crea blocco finale
            mined_block = Block(
                header=mined_header,
                transactions=all_transactions
            )
            
            logger.info(
                "✅ Block mined successfully!",
                extra_data={
                    "height": mined_block.header.height,
                    "hash": mined_block.compute_block_hash()[:16] + "...",
                    "nonce": mined_header.nonce,
                    "tx_count": len(all_transactions)
                }
            )
            
            return mined_block
    
    def _should_adjust_difficulty(self) -> bool:
        """Check se è ora di adjust difficulty"""
        current_height = self.get_height()
        
        # Adjust ogni DIFFICULTY_ADJUSTMENT_INTERVAL blocchi
        return (current_height > 0 and 
                current_height % DIFFICULTY_ADJUSTMENT_INTERVAL == 0)
    
    def _adjust_difficulty(self) -> None:
        """Adjust difficulty basato su block time"""
        current_height = self.get_height()
        
        # Calcola tempo effettivo ultimi N blocchi
        start_height = current_height - DIFFICULTY_ADJUSTMENT_INTERVAL
        if start_height < 0:
            return
        
        start_block = self.get_block(start_height)
        end_block = self.get_block(current_height)
        
        if not start_block or not end_block:
            return
        
        actual_time = end_block.header.timestamp - start_block.header.timestamp
        target_time = DIFFICULTY_ADJUSTMENT_INTERVAL * BLOCK_TIME_TARGET
        
        # Calcola nuova difficulty
        new_difficulty = calculate_next_difficulty(
            previous_difficulty=self.current_difficulty,
            actual_time=actual_time,
            target_time=target_time,
            min_difficulty=1,
            max_difficulty=32
        )
        
        if new_difficulty != self.current_difficulty:
            logger.info(
                f"Difficulty adjusted",
                extra_data={
                    "old": self.current_difficulty,
                    "new": new_difficulty,
                    "actual_time": actual_time,
                    "target_time": target_time
                }
            )
            self.current_difficulty = new_difficulty
    
    # ========================================================================
    # QUERY API - BALANCES
    # ========================================================================
    
    def get_balance(self, address: str) -> int:
        """
        Ottieni balance address (solo spendibili).
        
        Args:
            address: Address da query
        
        Returns:
            int: Balance in Satoshi
        
        Examples:
            >>> blockchain = Blockchain(config)
            >>> balance = blockchain.get_balance("addr1")
            >>> balance  # In Satoshi
            0
        """
        return self.utxo_set.get_balance(address)
    
    def get_balance_detailed(self, address: str) -> Dict[str, int]:
        """
        Ottieni balance dettagliato.
        
        Args:
            address: Address da query
        
        Returns:
            dict: {
                "total": int,
                "certified": int,
                "compensated": int
            }
        
        Examples:
            >>> blockchain = Blockchain(config)
            >>> balance = blockchain.get_balance_detailed("addr1")
            >>> balance["total"]
            0
        """
        return {
            "total": self.utxo_set.get_balance(address),
            "certified": self.utxo_set.get_certified_balance(address),
            "compensated": self.utxo_set.get_compensated_balance(address)
        }
    
    def get_utxos(self, address: str) -> List[Tuple[UTXOKey, TxOutput]]:
        """
        Ottieni tutti gli UTXO per address.
        
        Args:
            address: Address da query
        
        Returns:
            List[Tuple[UTXOKey, TxOutput]]: Lista UTXO
        
        Examples:
            >>> blockchain = Blockchain(config)
            >>> utxos = blockchain.get_utxos("addr1")
            >>> len(utxos)
            0
        """
        return self.utxo_set.get_utxos_for_address(address)
    
    # ========================================================================
    # QUERY API - SUPPLY
    # ========================================================================
    
    def get_supply(self) -> int:
        """
        Ottieni supply totale.
        
        Returns:
            int: Supply in Satoshi
        
        Examples:
            >>> blockchain = Blockchain(config)
            >>> supply = blockchain.get_supply()
            >>> supply > 0  # Genesis subsidy
            True
        """
        return self.total_supply
    
    def get_supply_coin(self) -> float:
        """
        Ottieni supply in CCO2 coin.
        
        Returns:
            float: Supply in CCO2
        """
        return satoshi_to_coin(self.total_supply)
    
    def get_supply_statistics(self) -> Dict[str, int]:
        """
        Ottieni statistiche supply.
        
        Returns:
            dict: {
                "total": int,
                "certified": int,
                "compensated": int,
                "spendable": int
            }
        """
        return {
            "total": self.total_supply,
            "certified": self.utxo_set.total_certified(),
            "compensated": self.utxo_set.total_compensated(),
            "spendable": self.total_supply - self.utxo_set.total_compensated()
        }
    
    # ========================================================================
    # QUERY API - CERTIFICATES
    # ========================================================================
    
    def _update_certificate_index(self, tx: Transaction, block_height: int) -> None:
        """Update certificate index da transazione"""
        for output in tx.outputs:
            if not output.is_certified:
                continue
            
            cert_id = output.certificate_id
            
            if cert_id not in self._certificate_index:
                # Nuovo certificato
                self._certificate_index[cert_id] = {
                    "certificate_id": cert_id,
                    "certificate_hash": output.certificate_hash,
                    "total_kg": output.certificate_total_kg,
                    "issued_kg": 0,
                    "compensated_kg": 0,
                    "first_tx": tx.compute_txid(),
                    "first_block": block_height,
                    "metadata": output.certificate_metadata or {}
                }
            
            # Update issued/compensated
            cert_info = self._certificate_index[cert_id]
            cert_info["issued_kg"] += output.amount
            
            if output.is_compensated:
                cert_info["compensated_kg"] += output.amount
    
    def get_certificate_info(self, cert_id: str) -> Optional[Dict]:
        """
        Ottieni info certificato.
        
        Args:
            cert_id: Certificate ID
        
        Returns:
            dict: Certificate info, o None se non trovato
        
        Examples:
            >>> blockchain = Blockchain(config)
            >>> cert_info = blockchain.get_certificate_info("CERT-001")
            >>> if cert_info:
            ...     print(cert_info["total_kg"])
        """
        return self._certificate_index.get(cert_id)
    
    def list_certificates(self) -> List[Dict]:
        """
        Lista tutti i certificati.
        
        Returns:
            List[dict]: Lista certificati
        """
        return list(self._certificate_index.values())
    
    # ========================================================================
    # QUERY API - PROJECTS
    # ========================================================================
    
    def _update_project_index(self, tx: Transaction, block_height: int) -> None:
        """Update project index da transazione"""
        for output in tx.outputs:
            if not output.is_compensated:
                continue
            
            project_id = output.compensation_project_id
            
            if project_id not in self._project_index:
                # Nuovo progetto
                self._project_index[project_id] = {
                    "project_id": project_id,
                    "total_kg_compensated": 0,
                    "certificates_used": set(),
                    "first_tx": tx.compute_txid(),
                    "first_block": block_height,
                    "metadata": output.compensation_metadata or {}
                }
            
            # Update
            proj_info = self._project_index[project_id]
            proj_info["total_kg_compensated"] += output.amount
            proj_info["certificates_used"].add(output.certificate_id)
    
    def get_project_info(self, project_id: str) -> Optional[Dict]:
        """
        Ottieni info progetto compensazione.
        
        Args:
            project_id: Project ID
        
        Returns:
            dict: Project info, o None se non trovato
        """
        proj_info = self._project_index.get(project_id)
        
        if proj_info:
            # Convert set to list per serialization
            proj_info_copy = dict(proj_info)
            proj_info_copy["certificates_used"] = list(proj_info["certificates_used"])
            return proj_info_copy
        
        return None
    
    def list_projects(self) -> List[Dict]:
        """
        Lista tutti i progetti.
        
        Returns:
            List[dict]: Lista progetti
        """
        projects = []
        for proj_info in self._project_index.values():
            proj_copy = dict(proj_info)
            proj_copy["certificates_used"] = list(proj_info["certificates_used"])
            projects.append(proj_copy)
        
        return projects
    
    # ========================================================================
    # CHAIN STATISTICS
    # ========================================================================
    
    def get_statistics(self) -> Dict:
        """
        Ottieni statistiche complete blockchain.
        
        Returns:
            dict: Statistiche
        
        Examples:
            >>> blockchain = Blockchain(config)
            >>> stats = blockchain.get_statistics()
            >>> stats["height"]
            0
        """
        with self._lock:
            return {
                "height": self.get_height(),
                "total_blocks": len(self.blocks),
                "supply": self.get_supply_statistics(),
                "difficulty": self.current_difficulty,
                "utxo_count": self.utxo_set.utxo_count(),
                "address_count": self.utxo_set.address_count(),
                "certificates_count": len(self._certificate_index),
                "projects_count": len(self._project_index),
            }
    
    def __repr__(self) -> str:
        """Safe repr"""
        return (
            f"Blockchain(network={self.config.network}, "
            f"height={self.get_height()}, "
            f"supply={self.get_supply()})"
        )


# ============================================================================
# GENESIS BLOCK CREATION
# ============================================================================

def create_genesis_block(config: ChainSettings) -> Block:
    """
    Crea genesis block (blocco 0).
    
    Args:
        config: Chain configuration
    
    Returns:
        Block: Genesis block
    
    Examples:
        >>> from carbon_chain.config import get_settings
        >>> config = get_settings()
        >>> genesis = create_genesis_block(config)
        >>> genesis.header.height
        0
    """
    from carbon_chain.constants import GENESIS_TIMESTAMP, GENESIS_MESSAGE
    
    # Address genesis (creator o burn)
    genesis_address = config.genesis_address or "1CarbonChainGenesisXXXXXXXXXXXXXXXX"
    
    # COINBASE transaction
    coinbase = Transaction(
        tx_type=TxType.COINBASE,
        inputs=[],
        outputs=[
            TxOutput(
                amount=config.initial_subsidy,
                address=genesis_address
            )
        ],
        timestamp=GENESIS_TIMESTAMP,
        metadata={
            "genesis": True,
            "message": GENESIS_MESSAGE,
            "version": "1.0.0"
        }
    )
    
    # Calcola merkle root
    temp_block = Block(
        header=BlockHeader(
            version=1,
            previous_hash="0" * 64,
            merkle_root=b'\x00' * 32,
            timestamp=GENESIS_TIMESTAMP,
            difficulty=config.pow_difficulty_initial,
            nonce=0,
            height=0
        ),
        transactions=[coinbase]
    )
    
    merkle_root = temp_block.compute_merkle_root()
    
    # Header finale
    genesis_header = BlockHeader(
        version=1,
        previous_hash="0" * 64,
        merkle_root=merkle_root,
        timestamp=GENESIS_TIMESTAMP,
        difficulty=config.pow_difficulty_initial,
        nonce=0,  # Genesis nonce=0 (no PoW required)
        height=0
    )
    
    # Blocco genesis finale
    genesis_block = Block(
        header=genesis_header,
        transactions=[coinbase]
    )
    
    logger.info(
        "Genesis block created",
        extra_data={
            "hash": genesis_block.compute_block_hash()[:16] + "...",
            "subsidy": config.initial_subsidy,
            "timestamp": GENESIS_TIMESTAMP
        }
    )
    
    return genesis_block


# ============================================================================
# EXPORT
# ============================================================================

__all__ = [
    "Blockchain",
    "create_genesis_block",
]
