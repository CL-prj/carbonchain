"""
CarbonChain - Transaction Mempool
===================================
Pool transazioni pending per mining.

Security Level: HIGH
Last Updated: 2025-11-27
Version: 1.0.0

Features:
- Transaction queuing
- Priority ordering (fee-based)
- Size limits
- Expiry management
- Double-spend detection
- Thread-safe operations
"""

from typing import List, Dict, Set, Optional
from dataclasses import dataclass
import time
import threading
from collections import defaultdict

# Internal imports
from carbon_chain.domain.models import Transaction, UTXOKey
from carbon_chain.errors import (
    MempoolError,
    MempoolFullError,
    TransactionConflictError,
)
from carbon_chain.logging_setup import get_logger
from carbon_chain.constants import (
    MEMPOOL_MAX_SIZE_MB,
    MEMPOOL_EXPIRY_HOURS,
)


# ============================================================================
# MODULE LOGGER
# ============================================================================

logger = get_logger("mempool")


# ============================================================================
# MEMPOOL ENTRY
# ============================================================================

@dataclass
class MempoolEntry:
    """
    Entry nel mempool.
    
    Attributes:
        transaction: Transaction
        added_time: Timestamp aggiunta
        fee: Fee in Satoshi (input - output)
        size: Size in bytes
        priority: Priority score (fee/size)
    """
    
    transaction: Transaction
    added_time: int
    fee: int
    size: int
    priority: float
    
    def is_expired(self, expiry_hours: int) -> bool:
        """Check se entry è scaduta"""
        current_time = int(time.time())
        age_hours = (current_time - self.added_time) / 3600
        return age_hours > expiry_hours
    
    def __repr__(self) -> str:
        return (
            f"MempoolEntry(txid={self.transaction.compute_txid()[:16]}..., "
            f"fee={self.fee}, priority={self.priority:.2f})"
        )


# ============================================================================
# MEMPOOL
# ============================================================================

class Mempool:
    """
    Transaction mempool.
    
    Gestisce:
    - Queue transazioni pending
    - Priority ordering
    - Size/count limits
    - Expiry management
    - Conflict detection
    
    Thread Safety:
        - Protected da RLock
        - Safe per multi-threading
    
    Attributes:
        _entries: Mapping txid → MempoolEntry
        _spent_utxos: Set UTXO spesi in mempool
        max_size: Max size in bytes
        max_count: Max numero tx
        expiry_hours: Ore prima expiry
    
    Examples:
        >>> mempool = Mempool()
        >>> tx = Transaction(...)
        >>> mempool.add_transaction(tx)
        >>> pending = mempool.get_all_transactions()
        >>> len(pending)
        1
    """
    
    def __init__(
        self,
        max_size_mb: int = 100,
        max_count: int = 10_000,
        expiry_hours: int = 24
    ):
        """
        Inizializza mempool.
        
        Args:
            max_size_mb: Max size in MB
            max_count: Max numero transazioni
            expiry_hours: Ore prima expiry
        """
        # Storage
        self._entries: Dict[str, MempoolEntry] = {}
        
        # UTXO tracking (double-spend prevention)
        self._spent_utxos: Set[UTXOKey] = set()
        
        # Limits
        self.max_size = max_size_mb * 1024 * 1024  # MB to bytes
        self.max_count = max_count
        self.expiry_hours = expiry_hours
        
        # Current size
        self._current_size = 0
        
        # Thread safety
        self._lock = threading.RLock()
        
        logger.info(
            "Mempool initialized",
            extra_data={
                "max_size_mb": max_size_mb,
                "max_count": max_count,
                "expiry_hours": expiry_hours
            }
        )
    
    def add_transaction(
        self,
        tx: Transaction,
        fee: Optional[int] = None
    ) -> None:
        """
        Aggiungi transazione al mempool.
        
        Args:
            tx: Transaction da aggiungere
            fee: Fee in Satoshi (opzionale, calcolato se None)
        
        Raises:
            MempoolFullError: Se mempool pieno
            TransactionConflictError: Se double-spend
            MempoolError: Se errore generico
        
        Thread Safety:
            Atomic operation
        
        Examples:
            >>> mempool = Mempool()
            >>> tx = Transaction(...)
            >>> mempool.add_transaction(tx)
        """
        with self._lock:
            txid = tx.compute_txid()
            
            # Check se già presente
            if txid in self._entries:
                logger.debug(f"Transaction {txid[:16]} already in mempool")
                return
            
            # Check COINBASE (non permesso in mempool)
            if tx.is_coinbase():
                raise MempoolError(
                    "COINBASE transactions cannot be added to mempool",
                    code="COINBASE_IN_MEMPOOL"
                )
            
            # Check conflicts (double-spend)
            for inp in tx.inputs:
                utxo_key = UTXOKey(inp.prev_txid, inp.prev_output_index)
                
                if utxo_key in self._spent_utxos:
                    raise TransactionConflictError(
                        f"UTXO {utxo_key} already spent in mempool",
                        code="DOUBLE_SPEND_MEMPOOL",
                        details={"utxo_key": str(utxo_key)}
                    )
            
            # Calcola size
            import json
            tx_size = len(json.dumps(tx.to_dict()).encode('utf-8'))
            
            # Check limits
            if len(self._entries) >= self.max_count:
                raise MempoolFullError(
                    f"Mempool full: {len(self._entries)} transactions",
                    code="MEMPOOL_COUNT_LIMIT"
                )
            
            if self._current_size + tx_size > self.max_size:
                raise MempoolFullError(
                    f"Mempool size limit reached: {self._current_size} bytes",
                    code="MEMPOOL_SIZE_LIMIT"
                )
            
            # Calcola fee (se non fornito)
            if fee is None:
                fee = self._calculate_fee(tx)
            
            # Calcola priority (fee per byte)
            priority = fee / tx_size if tx_size > 0 else 0.0
            
            # Crea entry
            entry = MempoolEntry(
                transaction=tx,
                added_time=int(time.time()),
                fee=fee,
                size=tx_size,
                priority=priority
            )
            
            # Aggiungi
            self._entries[txid] = entry
            self._current_size += tx_size
            
            # Track UTXO spesi
            for inp in tx.inputs:
                utxo_key = UTXOKey(inp.prev_txid, inp.prev_output_index)
                self._spent_utxos.add(utxo_key)
            
            logger.info(
                f"Transaction added to mempool",
                extra_data={
                    "txid": txid[:16] + "...",
                    "fee": fee,
                    "size": tx_size,
                    "priority": round(priority, 2),
                    "mempool_size": len(self._entries)
                }
            )
    
    def remove_transaction(self, txid: str) -> Optional[Transaction]:
        """
        Rimuovi transazione dal mempool.
        
        Args:
            txid: Transaction ID
        
        Returns:
            Transaction: Tx rimossa, o None se non presente
        
        Thread Safety:
            Atomic operation
        
        Examples:
            >>> mempool = Mempool()
            >>> mempool.add_transaction(tx)
            >>> removed = mempool.remove_transaction(tx.compute_txid())
        """
        with self._lock:
            entry = self._entries.pop(txid, None)
            
            if not entry:
                return None
            
            # Update size
            self._current_size -= entry.size
            
            # Remove UTXO tracking
            for inp in entry.transaction.inputs:
                utxo_key = UTXOKey(inp.prev_txid, inp.prev_output_index)
                self._spent_utxos.discard(utxo_key)
            
            logger.debug(
                f"Transaction removed from mempool",
                extra_data={
                    "txid": txid[:16] + "...",
                    "mempool_size": len(self._entries)
                }
            )
            
            return entry.transaction
    
    def get_transaction(self, txid: str) -> Optional[Transaction]:
        """
        Ottieni transazione da mempool.
        
        Args:
            txid: Transaction ID
        
        Returns:
            Transaction: Tx se presente, None altrimenti
        """
        with self._lock:
            entry = self._entries.get(txid)
            return entry.transaction if entry else None
    
    def contains(self, txid: str) -> bool:
        """
        Check se transazione presente.
        
        Args:
            txid: Transaction ID
        
        Returns:
            bool: True se presente
        """
        with self._lock:
            return txid in self._entries
    
    def size(self) -> int:
        """
        Numero transazioni in mempool.
        
        Returns:
            int: Count
        """
        with self._lock:
            return len(self._entries)
    
    def is_empty(self) -> bool:
        """Check se mempool vuoto"""
        return self.size() == 0
    
    def get_all_transactions(self) -> List[Transaction]:
        """
        Ottieni tutte le transazioni (ordinato per priority).
        
        Returns:
            List[Transaction]: Lista tx (priority decrescente)
        
        Examples:
            >>> mempool = Mempool()
            >>> all_tx = mempool.get_all_transactions()
        """
        with self._lock:
            # Sort by priority (fee/byte descending)
            sorted_entries = sorted(
                self._entries.values(),
                key=lambda e: e.priority,
                reverse=True
            )
            
            return [entry.transaction for entry in sorted_entries]
    
    def get_transactions_for_mining(
        self,
        max_count: Optional[int] = None,
        max_size: Optional[int] = None
    ) -> List[Transaction]:
        """
        Ottieni transazioni per mining (best priority).
        
        Args:
            max_count: Max numero tx (None = no limit)
            max_size: Max size totale in bytes (None = no limit)
        
        Returns:
            List[Transaction]: Lista tx per mining
        
        Algorithm:
            1. Sort by priority (fee/byte)
            2. Select top N rispettando limiti
        
        Examples:
            >>> mempool = Mempool()
            >>> for_mining = mempool.get_transactions_for_mining(max_count=1000)
        """
        with self._lock:
            # Sort by priority
            sorted_entries = sorted(
                self._entries.values(),
                key=lambda e: e.priority,
                reverse=True
            )
            
            selected = []
            total_size = 0
            
            for entry in sorted_entries:
                # Check limits
                if max_count and len(selected) >= max_count:
                    break
                
                if max_size and total_size + entry.size > max_size:
                    break
                
                selected.append(entry.transaction)
                total_size += entry.size
            
            logger.debug(
                f"Selected transactions for mining",
                extra_data={
                    "count": len(selected),
                    "total_size": total_size
                }
            )
            
            return selected
    
    def remove_transactions_in_block(self, block) -> int:
        """
        Rimuovi transazioni presenti in blocco.
        
        Chiamato quando blocco viene minato/aggiunto.
        
        Args:
            block: Block con transazioni da rimuovere
        
        Returns:
            int: Numero tx rimosse
        
        Examples:
            >>> mempool = Mempool()
            >>> # ... aggiungi tx ...
            >>> removed = mempool.remove_transactions_in_block(block)
        """
        with self._lock:
            removed_count = 0
            
            for tx in block.transactions:
                if not tx.is_coinbase():  # Skip COINBASE
                    txid = tx.compute_txid()
                    if self.remove_transaction(txid):
                        removed_count += 1
            
            logger.info(
                f"Removed transactions from mempool (block mined)",
                extra_data={
                    "removed": removed_count,
                    "remaining": len(self._entries)
                }
            )
            
            return removed_count
    
    def cleanup_expired(self) -> int:
        """
        Rimuovi transazioni scadute.
        
        Returns:
            int: Numero tx rimosse
        
        Examples:
            >>> mempool = Mempool(expiry_hours=24)
            >>> # ... dopo 24h ...
            >>> expired = mempool.cleanup_expired()
        """
        with self._lock:
            expired_txids = []
            
            for txid, entry in self._entries.items():
                if entry.is_expired(self.expiry_hours):
                    expired_txids.append(txid)
            
            # Rimuovi expired
            for txid in expired_txids:
                self.remove_transaction(txid)
            
            if expired_txids:
                logger.info(
                    f"Removed expired transactions from mempool",
                    extra_data={"count": len(expired_txids)}
                )
            
            return len(expired_txids)
    
    def clear(self) -> None:
        """
        Svuota mempool (per testing).
        
        Warning:
            Operazione distruttiva
        """
        with self._lock:
            self._entries.clear()
            self._spent_utxos.clear()
            self._current_size = 0
            
            logger.warning("Mempool cleared")
    
    def get_statistics(self) -> Dict:
        """
        Ottieni statistiche mempool.
        
        Returns:
            dict: Statistiche
        
        Examples:
            >>> mempool = Mempool()
            >>> stats = mempool.get_statistics()
            >>> stats["count"]
            0
        """
        with self._lock:
            total_fees = sum(entry.fee for entry in self._entries.values())
            
            return {
                "count": len(self._entries),
                "size_bytes": self._current_size,
                "size_mb": round(self._current_size / (1024 * 1024), 2),
                "total_fees": total_fees,
                "avg_priority": round(
                    sum(e.priority for e in self._entries.values()) / len(self._entries)
                    if self._entries else 0.0,
                    2
                ),
            }
    
    def _calculate_fee(self, tx: Transaction) -> int:
        """
        Calcola fee transazione.
        
        Fee = total_input - total_output
        
        Args:
            tx: Transaction
        
        Returns:
            int: Fee in Satoshi (0 se non calcolabile)
        
        Note:
            Calcolo reale richiede UTXO set per lookup input amounts.
            Qui return 0 come placeholder.
        """
        # TODO: Richiede UTXO set per calcolo reale
        # Per ora assume fee = 0
        return 0
    
    def __len__(self) -> int:
        """Numero tx in mempool"""
        return self.size()
    
    def __repr__(self) -> str:
        """Safe repr"""
        return (
            f"Mempool(count={self.size()}, "
            f"size_mb={round(self._current_size / (1024*1024), 2)})"
        )


# ============================================================================
# EXPORT
# ============================================================================

__all__ = [
    "Mempool",
    "MempoolEntry",
]
