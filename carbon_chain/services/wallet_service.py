"""
CarbonChain - Wallet Service
==============================
Servizio high-level per gestione wallet e transazioni.

Security Level: HIGH
Last Updated: 2025-11-27
Version: 1.0.0

Features:
- Wallet creation/management
- Balance queries
- Transaction creation
- UTXO selection
- Change address management
"""

from typing import List, Dict, Optional, Tuple
import time

# Internal imports
from carbon_chain.wallet.hd_wallet import HDWallet
from carbon_chain.domain.models import (
    Transaction,
    TxInput,
    TxOutput,
    UTXOKey,
)
from carbon_chain.domain.blockchain import Blockchain
from carbon_chain.constants import (
    TxType,
    coin_to_satoshi,
    satoshi_to_coin,
    validate_amount,
)
from carbon_chain.errors import (
    WalletError,
    InsufficientFundsError,
)
from carbon_chain.logging_setup import get_logger
from carbon_chain.config import ChainSettings


# ============================================================================
# MODULE LOGGER
# ============================================================================

logger = get_logger("wallet_service")


# ============================================================================
# WALLET SERVICE
# ============================================================================

class WalletService:
    """
    Servizio gestione wallet.
    
    High-level API per:
    - Creazione/recovery wallet
    - Query balance
    - Creazione transazioni
    - UTXO selection
    
    Attributes:
        blockchain: Blockchain instance
        config: Chain configuration
    
    Examples:
        >>> service = WalletService(blockchain, config)
        >>> wallet = service.create_wallet()
        >>> balance = service.get_balance(wallet, 0)
    """
    
    def __init__(self, blockchain: Blockchain, config: ChainSettings):
        self.blockchain = blockchain
        self.config = config
    
    # ========================================================================
    # WALLET CREATION
    # ========================================================================
    
    def create_wallet(
        self,
        strength: int = 128,
        passphrase: str = ""
    ) -> HDWallet:
        """
        Crea nuovo wallet.
        
        Args:
            strength: Bit entropia (128=12 words, 256=24 words)
            passphrase: BIP39 passphrase opzionale
        
        Returns:
            HDWallet: Nuovo wallet
        
        Examples:
            >>> service = WalletService(blockchain, config)
            >>> wallet = service.create_wallet()
            >>> print(wallet.get_mnemonic())  # BACKUP!
        """
        wallet = HDWallet.create_new(
            strength=strength,
            config=self.config,
            passphrase=passphrase
        )
        
        logger.info(
            "Wallet created",
            extra_data={
                "word_count": len(wallet.mnemonic.split()),
                "first_address": wallet.get_address(0)[:16] + "..."
            }
        )
        
        return wallet
    
    def recover_wallet(
        self,
        mnemonic: str,
        passphrase: str = ""
    ) -> HDWallet:
        """
        Recupera wallet da mnemonic.
        
        Args:
            mnemonic: Seed phrase
            passphrase: BIP39 passphrase
        
        Returns:
            HDWallet: Wallet recuperato
        
        Examples:
            >>> mnemonic = "word1 word2 ... word12"
            >>> wallet = service.recover_wallet(mnemonic)
        """
        wallet = HDWallet.from_mnemonic(
            mnemonic,
            config=self.config,
            passphrase=passphrase
        )
        
        logger.info(
            "Wallet recovered from mnemonic",
            extra_data={
                "first_address": wallet.get_address(0)[:16] + "..."
            }
        )
        
        return wallet
    
    # ========================================================================
    # BALANCE QUERIES
    # ========================================================================
    
    def get_balance(
        self,
        wallet: HDWallet,
        address_index: int
    ) -> int:
        """
        Ottieni balance address.
        
        Args:
            wallet: HD Wallet
            address_index: Indice address
        
        Returns:
            int: Balance in Satoshi
        
        Examples:
            >>> balance = service.get_balance(wallet, 0)
            >>> print(f"{satoshi_to_coin(balance)} CCO2")
        """
        address = wallet.get_address(address_index)
        return self.blockchain.get_balance(address)
    
    def get_balance_detailed(
        self,
        wallet: HDWallet,
        address_index: int
    ) -> Dict[str, int]:
        """
        Ottieni balance dettagliato.
        
        Args:
            wallet: HD Wallet
            address_index: Indice address
        
        Returns:
            dict: {
                "total": int,
                "certified": int,
                "compensated": int
            }
        """
        address = wallet.get_address(address_index)
        return self.blockchain.get_balance_detailed(address)
    
    def get_total_balance(
        self,
        wallet: HDWallet,
        max_addresses: int = 20
    ) -> int:
        """
        Ottieni balance totale wallet (tutte le addresses).
        
        Args:
            wallet: HD Wallet
            max_addresses: Max addresses da controllare
        
        Returns:
            int: Balance totale in Satoshi
        
        Examples:
            >>> total = service.get_total_balance(wallet)
        """
        total = 0
        
        for index in range(max_addresses):
            address = wallet.get_address(index)
            balance = self.blockchain.get_balance(address)
            
            if balance > 0:
                total += balance
        
        return total
    
    def list_utxos(
        self,
        wallet: HDWallet,
        address_index: int
    ) -> List[Tuple[UTXOKey, TxOutput]]:
        """
        Lista UTXO per address.
        
        Args:
            wallet: HD Wallet
            address_index: Indice address
        
        Returns:
            List[Tuple[UTXOKey, TxOutput]]: Lista UTXO
        """
        address = wallet.get_address(address_index)
        return self.blockchain.get_utxos(address)
    
    # ========================================================================
    # TRANSACTION CREATION
    # ========================================================================
    
    def create_transfer(
        self,
        wallet: HDWallet,
        from_address_index: int,
        to_address: str,
        amount_satoshi: int,
        change_address_index: Optional[int] = None
    ) -> Transaction:
        """
        Crea transazione TRANSFER.
        
        Args:
            wallet: HD Wallet mittente
            from_address_index: Indice address mittente
            to_address: Address destinatario
            amount_satoshi: Amount da inviare (Satoshi)
            change_address_index: Indice change address (None = usa stesso)
        
        Returns:
            Transaction: Tx firmata
        
        Raises:
            InsufficientFundsError: Se fondi insufficienti
        
        Examples:
            >>> tx = service.create_transfer(
            ...     wallet,
            ...     from_address_index=0,
            ...     to_address="1Recipient...",
            ...     amount_satoshi=100000
            ... )
            >>> # Broadcast tx to mempool/network
        """
        # Validazione amount
        if not validate_amount(amount_satoshi):
            raise WalletError(
                f"Invalid amount: {amount_satoshi}",
                code="INVALID_AMOUNT"
            )
        
        from_address = wallet.get_address(from_address_index)
        
        # Select UTXO
        selected_utxos, total_input, change_amount = self._select_utxos(
            from_address,
            amount_satoshi
        )
        
        if not selected_utxos:
            raise InsufficientFundsError(
                f"Insufficient funds: need {amount_satoshi}, have {self.get_balance(wallet, from_address_index)}",
                code="INSUFFICIENT_FUNDS"
            )
        
        # Crea input
        inputs = []
        for utxo_key, _ in selected_utxos:
            inp = TxInput(
                prev_txid=utxo_key.txid,
                prev_output_index=utxo_key.output_index
            )
            inputs.append(inp)
        
        # Crea output
        outputs = [
            TxOutput(
                amount=amount_satoshi,
                address=to_address
            )
        ]
        
        # Aggiungi change se necessario
        if change_amount > 0:
            change_index = change_address_index if change_address_index is not None else from_address_index
            change_address = wallet.get_address(change_index)
            
            outputs.append(
                TxOutput(
                    amount=change_amount,
                    address=change_address
                )
            )
        
        # Crea transazione
        tx = Transaction(
            tx_type=TxType.TRANSFER,
            inputs=inputs,
            outputs=outputs,
            timestamp=int(time.time())
        )
        
        # Firma transazione
        signed_tx = wallet.sign_transaction(tx, from_address)
        
        logger.info(
            "Transfer transaction created",
            extra_data={
                "txid": signed_tx.compute_txid()[:16] + "...",
                "amount": amount_satoshi,
                "from": from_address[:16] + "...",
                "to": to_address[:16] + "..."
            }
        )
        
        return signed_tx
    
    def create_transfer_coin(
        self,
        wallet: HDWallet,
        from_address_index: int,
        to_address: str,
        amount_coin: float,
        change_address_index: Optional[int] = None
    ) -> Transaction:
        """
        Crea transfer (amount in CCO2 coin).
        
        Args:
            wallet: HD Wallet
            from_address_index: Indice from address
            to_address: To address
            amount_coin: Amount in CCO2 (es. 1.5)
            change_address_index: Change address index
        
        Returns:
            Transaction: Tx firmata
        
        Examples:
            >>> tx = service.create_transfer_coin(
            ...     wallet, 0, "1Recipient...", 1.5  # 1.5 CCO2
            ... )
        """
        amount_satoshi = coin_to_satoshi(amount_coin)
        
        return self.create_transfer(
            wallet,
            from_address_index,
            to_address,
            amount_satoshi,
            change_address_index
        )
    
    # ========================================================================
    # UTXO SELECTION
    # ========================================================================
    
    def _select_utxos(
        self,
        from_address: str,
        target_amount: int
    ) -> Tuple[List[Tuple[UTXOKey, TxOutput]], int, int]:
        """
        Seleziona UTXO per amount target.
        
        Strategy: Simple greedy (largest first)
        
        Args:
            from_address: Address mittente
            target_amount: Amount target (Satoshi)
        
        Returns:
            Tuple: (selected_utxos, total_input, change_amount)
        
        Algorithm:
            1. Ottieni tutti UTXO spendibili
            2. Ordina per amount (decrescente)
            3. Accumula fino a target + fee
            4. Calcola change
        """
        # Ottieni UTXO spendibili
        all_utxos = self.blockchain.utxo_set.get_spendable_utxos_for_address(from_address)
        
        if not all_utxos:
            return [], 0, 0
        
        # Sort by amount (decrescente)
        sorted_utxos = sorted(
            all_utxos,
            key=lambda x: x[1].amount,
            reverse=True
        )
        
        # Seleziona UTXO
        selected = []
        total = 0
        
        for utxo_key, output in sorted_utxos:
            selected.append((utxo_key, output))
            total += output.amount
            
            if total >= target_amount:
                break
        
        # Calcola change
        change = total - target_amount if total >= target_amount else 0
        
        return selected, total, change
    
    # ========================================================================
    # ADDRESS MANAGEMENT
    # ========================================================================
    
    def get_next_unused_address(
        self,
        wallet: HDWallet,
        max_check: int = 100
    ) -> Tuple[int, str]:
        """
        Trova prossimo address inutilizzato.
        
        Args:
            wallet: HD Wallet
            max_check: Max addresses da controllare
        
        Returns:
            Tuple[int, str]: (index, address)
        
        Examples:
            >>> index, address = service.get_next_unused_address(wallet)
        """
        for index in range(max_check):
            address = wallet.get_address(index)
            balance = self.blockchain.get_balance(address)
            utxos = self.blockchain.get_utxos(address)
            
            # Address inutilizzato se:
            # - Balance = 0
            # - No UTXO
            if balance == 0 and not utxos:
                return index, address
        
        # Se tutti usati, return next
        return max_check, wallet.get_address(max_check)
    
    def scan_wallet_addresses(
        self,
        wallet: HDWallet,
        max_addresses: int = 100
    ) -> List[Dict]:
        """
        Scansiona addresses wallet con balance/UTXO.
        
        Args:
            wallet: HD Wallet
            max_addresses: Max addresses da scansionare
        
        Returns:
            List[dict]: Lista {
                "index": int,
                "address": str,
                "balance": int,
                "utxo_count": int
            }
        
        Examples:
            >>> addresses = service.scan_wallet_addresses(wallet)
            >>> for addr_info in addresses:
            ...     print(f"{addr_info['index']}: {addr_info['balance']}")
        """
        result = []
        
        for index in range(max_addresses):
            address = wallet.get_address(index)
            balance = self.blockchain.get_balance(address)
            utxos = self.blockchain.get_utxos(address)
            
            if balance > 0 or utxos:
                result.append({
                    "index": index,
                    "address": address,
                    "balance": balance,
                    "balance_coin": satoshi_to_coin(balance),
                    "utxo_count": len(utxos)
                })
        
        return result
    
    # ========================================================================
    # TRANSACTION HISTORY
    # ========================================================================
    
    def get_transaction_history(
        self,
        wallet: HDWallet,
        address_index: int,
        max_blocks: Optional[int] = None
    ) -> List[Dict]:
        """
        Ottieni storico transazioni per address.
        
        Args:
            wallet: HD Wallet
            address_index: Indice address
            max_blocks: Max blocchi da scansionare (None = tutti)
        
        Returns:
            List[dict]: Lista transazioni {
                "txid": str,
                "block_height": int,
                "timestamp": int,
                "type": str,
                "amount": int,
                "direction": "in" | "out"
            }
        
        Examples:
            >>> history = service.get_transaction_history(wallet, 0)
            >>> for tx in history:
            ...     print(f"{tx['txid'][:16]}: {tx['amount']}")
        """
        address = wallet.get_address(address_index)
        history = []
        
        # Scan blockchain
        blocks_to_scan = self.blockchain.blocks[-max_blocks:] if max_blocks else self.blockchain.blocks
        
        for block in blocks_to_scan:
            for tx in block.transactions:
                # Check se tx coinvolge address
                
                # Input (spesa)
                for inp in tx.inputs:
                    utxo_key = UTXOKey(inp.prev_txid, inp.prev_output_index)
                    utxo = self.blockchain.utxo_set.get_utxo(utxo_key)
                    
                    # Note: UTXO potrebbe essere già speso
                    # Richiede lookup storico da storage
                
                # Output (ricezione)
                for idx, output in enumerate(tx.outputs):
                    if output.address == address:
                        history.append({
                            "txid": tx.compute_txid(),
                            "block_height": block.header.height,
                            "timestamp": block.header.timestamp,
                            "type": tx.tx_type.name,
                            "amount": output.amount,
                            "direction": "in",
                            "certified": output.is_certified,
                            "compensated": output.is_compensated
                        })
        
        return history


# ============================================================================
# EXPORT
# ============================================================================

__all__ = [
    "WalletService",
]
