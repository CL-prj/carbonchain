"""
CarbonChain - UTXO Set Management
===================================
Gestione efficiente del set di UTXO (Unspent Transaction Outputs).

Security Level: CRITICAL
Last Updated: 2025-11-27
Version: 1.0.0

UTXO Set:
- Mantiene tutti gli output non spesi
- Index rapido per address
- Thread-safe operations
- Snapshot per rollback

Performance:
- O(1) lookup per UTXO key
- O(1) add/remove
- O(n) query per address (con index)
"""

from __future__ import annotations
from typing import Dict, List, Tuple, Set, Optional
from collections import defaultdict
from dataclasses import dataclass, field
import threading

# Internal imports
from carbon_chain.domain.models import (
    TxOutput,
    UTXOKey,
    Transaction,
)
from carbon_chain.errors import (
    UTXOError,
    UTXONotFoundError,
    UTXONotSpendableError,
)
from carbon_chain.logging_setup import get_logger
from carbon_chain.constants import validate_amount


# ============================================================================
# MODULE LOGGER
# ============================================================================

logger = get_logger("utxo")


# ============================================================================
# UTXO SET
# ============================================================================

class UTXOSet:
    """
    Set di UTXO (Unspent Transaction Outputs).
    
    Mantiene:
    - Mapping UTXOKey → TxOutput
    - Index address → UTXOKey (per query veloci)
    - Statistiche (total supply, certified amount, etc.)
    
    Thread Safety:
        - Protected da RLock per operazioni concorrenti
        - Safe per multi-threading
    
    Attributes:
        _utxos (dict): Mapping UTXOKey → TxOutput
        _address_index (dict): Index address → set[UTXOKey]
        _lock (RLock): Lock per thread-safety
    
    Examples:
        >>> utxo_set = UTXOSet()
        >>> key = UTXOKey("txid123", 0)
        >>> output = TxOutput(amount=100000, address="addr1")
        >>> utxo_set.add_utxo(key, output)
        >>> utxo_set.contains(key)
        True
    """
    
    def __init__(self):
        """Inizializza UTXO set vuoto"""
        # Main storage: UTXOKey → TxOutput
        self._utxos: Dict[UTXOKey, TxOutput] = {}
        
        # Address index: address → set di UTXOKey
        self._address_index: Dict[str, Set[UTXOKey]] = defaultdict(set)
        
        # Thread safety
        self._lock = threading.RLock()
        
        logger.debug("UTXOSet initialized")
    
    def add_utxo(self, utxo_key: UTXOKey, output: TxOutput) -> None:
        """
        Aggiungi UTXO al set.
        
        Args:
            utxo_key: Chiave UTXO (txid + index)
            output: Output da aggiungere
        
        Raises:
            UTXOError: Se UTXO già presente
        
        Thread Safety:
            Protected da lock
        
        Examples:
            >>> utxo_set = UTXOSet()
            >>> key = UTXOKey("tx1", 0)
            >>> output = TxOutput(100, "addr1")
            >>> utxo_set.add_utxo(key, output)
        """
        with self._lock:
            # Check duplicato
            if utxo_key in self._utxos:
                logger.warning(
                    f"UTXO already exists",
                    extra_data={"utxo_key": str(utxo_key)}
                )
                raise UTXOError(
                    f"UTXO {utxo_key} already exists in set",
                    code="UTXO_DUPLICATE"
                )
            
            # Aggiungi a main storage
            self._utxos[utxo_key] = output
            
            # Aggiorna address index
            self._address_index[output.address].add(utxo_key)
            
            logger.debug(
                f"UTXO added",
                extra_data={
                    "utxo_key": str(utxo_key),
                    "amount": output.amount,
                    "address": output.address[:16] + "...",
                    "total_utxos": len(self._utxos)
                }
            )
    
    def remove_utxo(self, utxo_key: UTXOKey) -> TxOutput:
        """
        Rimuovi UTXO dal set (quando speso).
        
        Args:
            utxo_key: Chiave UTXO da rimuovere
        
        Returns:
            TxOutput: Output rimosso
        
        Raises:
            UTXONotFoundError: Se UTXO non trovato
        
        Thread Safety:
            Protected da lock
        
        Examples:
            >>> utxo_set = UTXOSet()
            >>> key = UTXOKey("tx1", 0)
            >>> output = TxOutput(100, "addr1")
            >>> utxo_set.add_utxo(key, output)
            >>> removed = utxo_set.remove_utxo(key)
            >>> removed.amount
            100
        """
        with self._lock:
            # Check esistenza
            if utxo_key not in self._utxos:
                raise UTXONotFoundError(
                    f"UTXO {utxo_key} not found in set",
                    code="UTXO_NOT_FOUND"
                )
            
            # Rimuovi da main storage
            output = self._utxos.pop(utxo_key)
            
            # Rimuovi da address index
            self._address_index[output.address].discard(utxo_key)
            
            # Cleanup address index se vuoto
            if not self._address_index[output.address]:
                del self._address_index[output.address]
            
            logger.debug(
                f"UTXO removed",
                extra_data={
                    "utxo_key": str(utxo_key),
                    "amount": output.amount,
                    "total_utxos": len(self._utxos)
                }
            )
            
            return output
    
    def get_utxo(self, utxo_key: UTXOKey) -> Optional[TxOutput]:
        """
        Ottieni UTXO per chiave.
        
        Args:
            utxo_key: Chiave UTXO
        
        Returns:
            TxOutput: Output se presente, None altrimenti
        
        Thread Safety:
            Protected da lock
        
        Examples:
            >>> utxo_set = UTXOSet()
            >>> key = UTXOKey("tx1", 0)
            >>> utxo_set.get_utxo(key)  # None se non presente
            >>> utxo_set.add_utxo(key, TxOutput(100, "addr"))
            >>> utxo_set.get_utxo(key).amount
            100
        """
        with self._lock:
            return self._utxos.get(utxo_key)
    
    def contains(self, utxo_key: UTXOKey) -> bool:
        """
        Check se UTXO presente nel set.
        
        Args:
            utxo_key: Chiave UTXO
        
        Returns:
            bool: True se presente
        
        Examples:
            >>> utxo_set = UTXOSet()
            >>> key = UTXOKey("tx1", 0)
            >>> utxo_set.contains(key)
            False
        """
        with self._lock:
            return utxo_key in self._utxos
    
    def get_utxos_for_address(self, address: str) -> List[Tuple[UTXOKey, TxOutput]]:
        """
        Ottieni tutti gli UTXO per address.
        
        Args:
            address: Address da query
        
        Returns:
            List[Tuple[UTXOKey, TxOutput]]: Lista (key, output) pairs
        
        Performance:
            O(n) dove n = numero UTXO per address
        
        Examples:
            >>> utxo_set = UTXOSet()
            >>> utxo_set.add_utxo(UTXOKey("tx1", 0), TxOutput(100, "addr1"))
            >>> utxo_set.add_utxo(UTXOKey("tx2", 0), TxOutput(50, "addr1"))
            >>> utxos = utxo_set.get_utxos_for_address("addr1")
            >>> len(utxos)
            2
        """
        with self._lock:
            utxo_keys = self._address_index.get(address, set())
            
            result = []
            for utxo_key in utxo_keys:
                output = self._utxos.get(utxo_key)
                if output:
                    result.append((utxo_key, output))
            
            return result
    
    def get_spendable_utxos_for_address(
        self,
        address: str
    ) -> List[Tuple[UTXOKey, TxOutput]]:
        """
        Ottieni UTXO spendibili per address.
        
        Filtra:
        - is_compensated=False
        - is_burned=False
        
        Args:
            address: Address da query
        
        Returns:
            List[Tuple[UTXOKey, TxOutput]]: Solo UTXO spendibili
        
        Examples:
            >>> utxo_set = UTXOSet()
            >>> utxo_set.add_utxo(
            ...     UTXOKey("tx1", 0),
            ...     TxOutput(100, "addr1")
            ... )
            >>> spendable = utxo_set.get_spendable_utxos_for_address("addr1")
            >>> len(spendable)
            1
        """
        all_utxos = self.get_utxos_for_address(address)
        
        return [
            (key, output)
            for key, output in all_utxos
            if output.is_spendable()
        ]
    
    def get_balance(self, address: str) -> int:
        """
        Calcola balance totale per address (solo spendibili).
        
        Args:
            address: Address da query
        
        Returns:
            int: Balance in Satoshi
        
        Examples:
            >>> utxo_set = UTXOSet()
            >>> utxo_set.add_utxo(UTXOKey("tx1", 0), TxOutput(100, "addr1"))
            >>> utxo_set.add_utxo(UTXOKey("tx2", 0), TxOutput(50, "addr1"))
            >>> utxo_set.get_balance("addr1")
            150
        """
        spendable_utxos = self.get_spendable_utxos_for_address(address)
        
        return sum(output.amount for _, output in spendable_utxos)
    
    def get_certified_balance(self, address: str) -> int:
        """
        Calcola balance certificato (non ancora compensato).
        
        Args:
            address: Address da query
        
        Returns:
            int: Balance certificato in Satoshi
        
        Examples:
            >>> utxo_set = UTXOSet()
            >>> utxo_set.add_utxo(
            ...     UTXOKey("tx1", 0),
            ...     TxOutput(
            ...         100, "addr1",
            ...         is_certified=True,
            ...         certificate_id="C1",
            ...         certificate_hash=b'hash',
            ...         certificate_total_kg=100
            ...     )
            ... )
            >>> utxo_set.get_certified_balance("addr1")
            100
        """
        all_utxos = self.get_utxos_for_address(address)
        
        return sum(
            output.amount
            for _, output in all_utxos
            if output.is_certified and not output.is_compensated
        )
    
    def get_compensated_balance(self, address: str) -> int:
        """
        Calcola balance compensato (non spendibile).
        
        Args:
            address: Address da query
        
        Returns:
            int: Balance compensato in Satoshi
        """
        all_utxos = self.get_utxos_for_address(address)
        
        return sum(
            output.amount
            for _, output in all_utxos
            if output.is_compensated
        )
    
    def total_supply(self) -> int:
        """
        Calcola supply totale (somma tutti UTXO).
        
        Returns:
            int: Total supply in Satoshi
        
        Examples:
            >>> utxo_set = UTXOSet()
            >>> utxo_set.add_utxo(UTXOKey("tx1", 0), TxOutput(100, "addr1"))
            >>> utxo_set.add_utxo(UTXOKey("tx2", 0), TxOutput(50, "addr2"))
            >>> utxo_set.total_supply()
            150
        """
        with self._lock:
            return sum(output.amount for output in self._utxos.values())
    
    def total_certified(self) -> int:
        """
        Calcola totale certificato (non ancora compensato).
        
        Returns:
            int: Certified supply in Satoshi
        """
        with self._lock:
            return sum(
                output.amount
                for output in self._utxos.values()
                if output.is_certified and not output.is_compensated
            )
    
    def total_compensated(self) -> int:
        """
        Calcola totale compensato.
        
        Returns:
            int: Compensated supply in Satoshi
        """
        with self._lock:
            return sum(
                output.amount
                for output in self._utxos.values()
                if output.is_compensated
            )
    
    def utxo_count(self) -> int:
        """
        Numero totale UTXO nel set.
        
        Returns:
            int: Count
        """
        with self._lock:
            return len(self._utxos)
    
    def address_count(self) -> int:
        """
        Numero address unici con UTXO.
        
        Returns:
            int: Count
        """
        with self._lock:
            return len(self._address_index)
    
    def apply_transaction(self, tx: Transaction) -> None:
        """
        Applica transazione al UTXO set.
        
        Operations:
        1. Rimuovi input (UTXO spesi)
        2. Aggiungi output (nuovi UTXO)
        
        Args:
            tx: Transaction da applicare
        
        Raises:
            UTXONotFoundError: Se input non trovato
            UTXONotSpendableError: Se input non spendibile
        
        Thread Safety:
            Atomic operation (protected da lock)
        
        Examples:
            >>> utxo_set = UTXOSet()
            >>> # Setup UTXO precedente
            >>> utxo_set.add_utxo(UTXOKey("prev_tx", 0), TxOutput(100, "addr1"))
            >>> 
            >>> # Create transfer tx
            >>> from carbon_chain.domain.models import TxInput
            >>> tx = Transaction(
            ...     tx_type=TxType.TRANSFER,
            ...     inputs=[TxInput("prev_tx", 0)],
            ...     outputs=[TxOutput(50, "addr2")],
            ...     timestamp=1700000000
            ... )
            >>> utxo_set.apply_transaction(tx)
        """
        with self._lock:
            txid = tx.compute_txid()
            
            # Step 1: Rimuovi input (se non COINBASE)
            if not tx.is_coinbase():
                for inp in tx.inputs:
                    utxo_key = UTXOKey(inp.prev_txid, inp.prev_output_index)
                    
                    # Check esistenza
                    if not self.contains(utxo_key):
                        raise UTXONotFoundError(
                            f"Input UTXO {utxo_key} not found",
                            code="INPUT_UTXO_NOT_FOUND"
                        )
                    
                    # Check spendibile
                    output = self.get_utxo(utxo_key)
                    if not output.is_spendable():
                        raise UTXONotSpendableError(
                            f"Input UTXO {utxo_key} not spendable "
                            f"(compensated={output.is_compensated}, burned={output.is_burned})",
                            code="INPUT_NOT_SPENDABLE"
                        )
                    
                    # Rimuovi
                    self.remove_utxo(utxo_key)
            
            # Step 2: Aggiungi output (se non BURN)
            if not tx.is_burn():
                for idx, output in enumerate(tx.outputs):
                    utxo_key = UTXOKey(txid, idx)
                    self.add_utxo(utxo_key, output)
            
            logger.info(
                f"Transaction applied to UTXO set",
                extra_data={
                    "txid": txid[:16] + "...",
                    "type": tx.tx_type.name,
                    "inputs_removed": len(tx.inputs),
                    "outputs_added": len(tx.outputs),
                    "total_utxos": self.utxo_count()
                }
            )
    
    def rollback_transaction(self, tx: Transaction) -> None:
        """
        Rollback transazione (operazione inversa di apply).
        
        Operations:
        1. Rimuovi output aggiunti
        2. Re-aggiungi input spesi
        
        Args:
            tx: Transaction da rollback
        
        Note:
            Richiede accesso ai prev UTXO (da blockchain/storage)
            Implementazione completa richiede cache prev outputs
        
        Warning:
            Incompleto - richiede prev outputs per re-add input
        """
        with self._lock:
            txid = tx.compute_txid()
            
            # Step 1: Rimuovi output (inverso di add)
            if not tx.is_burn():
                for idx in range(len(tx.outputs)):
                    utxo_key = UTXOKey(txid, idx)
                    if self.contains(utxo_key):
                        self.remove_utxo(utxo_key)
            
            # Step 2: Re-aggiungi input (inverso di remove)
            # TODO: Richiede prev outputs storage
            # Per ora log warning
            if not tx.is_coinbase() and tx.inputs:
                logger.warning(
                    "Rollback transaction: re-adding inputs requires prev outputs data",
                    extra_data={"txid": txid[:16]}
                )
            
            logger.info(
                f"Transaction rolled back from UTXO set",
                extra_data={
                    "txid": txid[:16] + "...",
                    "total_utxos": self.utxo_count()
                }
            )
    
    def get_snapshot(self) -> UTXOSetSnapshot:
        """
        Crea snapshot del UTXO set corrente.
        
        Usato per:
        - Rollback
        - Testing
        - Checkpoints
        
        Returns:
            UTXOSetSnapshot: Snapshot immutabile
        
        Examples:
            >>> utxo_set = UTXOSet()
            >>> utxo_set.add_utxo(UTXOKey("tx1", 0), TxOutput(100, "addr1"))
            >>> snapshot = utxo_set.get_snapshot()
            >>> snapshot.utxo_count
            1
        """
        with self._lock:
            return UTXOSetSnapshot(
                utxos=dict(self._utxos),
                address_index=dict(self._address_index),
            )
    
    def restore_snapshot(self, snapshot: UTXOSetSnapshot) -> None:
        """
        Ripristina UTXO set da snapshot.
        
        Args:
            snapshot: Snapshot da ripristinare
        
        Warning:
            Operazione distruttiva - sovrascrive stato corrente
        
        Examples:
            >>> utxo_set = UTXOSet()
            >>> snapshot = utxo_set.get_snapshot()
            >>> # ... modifiche ...
            >>> utxo_set.restore_snapshot(snapshot)  # Ripristina stato
        """
        with self._lock:
            self._utxos = dict(snapshot.utxos)
            self._address_index = dict(snapshot.address_index)
            
            logger.info(
                f"UTXO set restored from snapshot",
                extra_data={"utxo_count": len(self._utxos)}
            )
    
    def clear(self) -> None:
        """
        Svuota UTXO set (per testing).
        
        Warning:
            Operazione distruttiva
        """
        with self._lock:
            self._utxos.clear()
            self._address_index.clear()
            
            logger.warning("UTXO set cleared")
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Ottieni statistiche UTXO set.
        
        Returns:
            dict: Statistiche complete
        
        Examples:
            >>> utxo_set = UTXOSet()
            >>> stats = utxo_set.get_statistics()
            >>> stats["total_utxos"]
            0
        """
        with self._lock:
            return {
                "total_utxos": self.utxo_count(),
                "total_addresses": self.address_count(),
                "total_supply": self.total_supply(),
                "total_certified": self.total_certified(),
                "total_compensated": self.total_compensated(),
                "spendable_supply": self.total_supply() - self.total_compensated(),
            }
    
    def __len__(self) -> int:
        """Numero UTXO nel set"""
        return self.utxo_count()
    
    def __repr__(self) -> str:
        """Safe repr"""
        return (
            f"UTXOSet(utxos={self.utxo_count()}, "
            f"addresses={self.address_count()}, "
            f"supply={self.total_supply()})"
        )


# ============================================================================
# UTXO SET SNAPSHOT
# ============================================================================

@dataclass(frozen=True)
class UTXOSetSnapshot:
    """
    Snapshot immutabile di UTXO set.
    
    Usato per:
    - Rollback blockchain
    - Testing
    - Checkpoints
    
    Attributes:
        utxos (dict): Copia UTXO mapping
        address_index (dict): Copia address index
    """
    
    utxos: Dict[UTXOKey, TxOutput]
    address_index: Dict[str, Set[UTXOKey]]
    
    @property
    def utxo_count(self) -> int:
        """Numero UTXO nello snapshot"""
        return len(self.utxos)
    
    @property
    def total_supply(self) -> int:
        """Total supply nello snapshot"""
        return sum(output.amount for output in self.utxos.values())
    
    def __repr__(self) -> str:
        return f"UTXOSetSnapshot(utxos={self.utxo_count}, supply={self.total_supply})"


# ============================================================================
# EXPORT
# ============================================================================

__all__ = [
    "UTXOSet",
    "UTXOSetSnapshot",
]
