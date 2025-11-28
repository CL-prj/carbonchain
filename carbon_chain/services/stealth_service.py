"""
CarbonChain - Stealth Address Service
=======================================
Service layer per stealth addresses.

Security Level: HIGH
Last Updated: 2025-11-27
Version: 1.0.0
"""

from typing import List, Dict, Optional
import json
from pathlib import Path

# Internal imports
from carbon_chain.wallet.stealth_address import (
    StealthWallet,
    StealthAddress,
    StealthPayment
)
from carbon_chain.domain.blockchain import Blockchain
from carbon_chain.domain.models import Transaction, TxOutput
from carbon_chain.errors import WalletError
from carbon_chain.logging_setup import get_logger
from carbon_chain.config import ChainSettings


# ============================================================================
# MODULE LOGGER
# ============================================================================

logger = get_logger("services.stealth")


# ============================================================================
# STEALTH SERVICE
# ============================================================================

class StealthService:
    """
    Service per gestione stealth addresses.
    
    Features:
    - Creazione stealth wallets
    - Payment generation
    - Payment detection & scanning
    - Spend key derivation
    
    Attributes:
        blockchain: Blockchain instance
        config: Chain settings
        storage_dir: Storage directory
    
    Examples:
        >>> service = StealthService(blockchain, config)
        >>> wallet = service.create_stealth_wallet()
        >>> payment = service.create_payment_to(receiver_address)
    """
    
    def __init__(
        self,
        blockchain: Blockchain,
        config: ChainSettings,
        storage_dir: Optional[Path] = None
    ):
        """
        Initialize stealth service.
        
        Args:
            blockchain: Blockchain instance
            config: Chain configuration
            storage_dir: Storage directory
        """
        self.blockchain = blockchain
        self.config = config
        
        # Storage directory
        self.storage_dir = storage_dir or (config.wallet_dir / "stealth")
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info("Stealth address service initialized")
    
    # ========================================================================
    # WALLET MANAGEMENT
    # ========================================================================
    
    def create_stealth_wallet(
        self,
        wallet_name: Optional[str] = None
    ) -> StealthWallet:
        """
        Crea nuovo stealth wallet.
        
        Args:
            wallet_name: Nome wallet (optional)
        
        Returns:
            StealthWallet: Wallet creato
        """
        wallet = StealthWallet.create()
        
        # Save wallet
        if wallet_name:
            self.save_wallet(wallet, wallet_name)
        
        logger.info(
            f"Created stealth wallet",
            extra_data={"address": wallet.get_address()}
        )
        
        return wallet
    
    def import_stealth_wallet(
        self,
        stealth_address: StealthAddress,
        scan_private_key: bytes,
        spend_private_key: bytes,
        wallet_name: Optional[str] = None
    ) -> StealthWallet:
        """
        Importa stealth wallet.
        
        Args:
            stealth_address: Stealth address
            scan_private_key: Scan private key
            spend_private_key: Spend private key
            wallet_name: Nome wallet
        
        Returns:
            StealthWallet: Wallet importato
        """
        wallet = StealthWallet(
            stealth_address=stealth_address,
            scan_private_key=scan_private_key,
            spend_private_key=spend_private_key
        )
        
        if wallet_name:
            self.save_wallet(wallet, wallet_name)
        
        logger.info(f"Imported stealth wallet: {wallet.get_address()}")
        
        return wallet
    
    # ========================================================================
    # PAYMENT CREATION
    # ========================================================================
    
    def create_payment_to(
        self,
        receiver_stealth_address: StealthAddress,
        amount: int,
        sender_wallet: Optional[any] = None
    ) -> StealthPayment:
        """
        Crea stealth payment.
        
        Args:
            receiver_stealth_address: Stealth address destinatario
            amount: Amount in Satoshi
            sender_wallet: Sender wallet (optional)
        
        Returns:
            StealthPayment: Payment info
        
        Examples:
            >>> payment = service.create_payment_to(receiver_addr, 1000)
            >>> # Send amount to payment.one_time_address
        """
        # Generate stealth payment
        payment = StealthWallet.create_payment_to(receiver_stealth_address)
        
        logger.info(
            f"Created stealth payment",
            extra_data={
                "one_time_address": payment.one_time_address,
                "amount": amount
            }
        )
        
        return payment
    
    def create_stealth_transaction(
        self,
        sender_wallet: any,
        receiver_stealth_address: StealthAddress,
        amount: int,
        from_address_index: int = 0
    ) -> tuple[Transaction, StealthPayment]:
        """
        Crea transazione completa con stealth payment.
        
        Args:
            sender_wallet: HD Wallet mittente
            receiver_stealth_address: Stealth address destinatario
            amount: Amount in Satoshi
            from_address_index: Address index mittente
        
        Returns:
            tuple: (Transaction, StealthPayment)
        """
        # Create stealth payment
        payment = self.create_payment_to(receiver_stealth_address, amount)
        
        # Create transaction to one-time address
        from carbon_chain.services.wallet_service import WalletService
        wallet_service = WalletService(self.blockchain, self.config)
        
        transaction = wallet_service.create_transfer(
            wallet=sender_wallet,
            from_address_index=from_address_index,
            to_address=payment.one_time_address,
            amount_satoshi=amount
        )
        
        # Attach stealth metadata
        transaction.metadata["stealth_payment"] = payment.to_dict()
        
        logger.info(
            f"Created stealth transaction",
            extra_data={"txid": transaction.compute_txid()[:16] + "..."}
        )
        
        return transaction, payment
    
    # ========================================================================
    # PAYMENT DETECTION
    # ========================================================================
    
    def scan_for_payments(
        self,
        wallet: StealthWallet,
        start_height: int = 0,
        end_height: Optional[int] = None
    ) -> List[tuple[Transaction, StealthPayment]]:
        """
        Scansiona blockchain per stealth payments.
        
        Args:
            wallet: Stealth wallet
            start_height: Start block height
            end_height: End block height (None = latest)
        
        Returns:
            List: Lista (Transaction, StealthPayment) trovati
        """
        if end_height is None:
            end_height = self.blockchain.get_height()
        
        found_payments = []
        
        # Scan blocks
        for height in range(start_height, end_height + 1):
            block = self.blockchain.get_block(height)
            
            if not block:
                continue
            
            # Scan transactions in block
            for tx in block.transactions:
                # Check if transaction has stealth metadata
                if "stealth_payment" not in tx.metadata:
                    continue
                
                # Reconstruct stealth payment
                payment_data = tx.metadata["stealth_payment"]
                payment = StealthPayment(
                    ephemeral_public_key=bytes.fromhex(payment_data["ephemeral_public_key"]),
                    one_time_address=payment_data["one_time_address"],
                    payment_id=bytes.fromhex(payment_data["payment_id"]) 
                        if payment_data.get("payment_id") else None
                )
                
                # Check if payment is for this wallet
                if wallet.is_payment_for_me(payment):
                    found_payments.append((tx, payment))
                    
                    logger.info(
                        f"Found stealth payment",
                        extra_data={
                            "height": height,
                            "txid": tx.compute_txid()[:16] + "..."
                        }
                    )
        
        logger.info(f"Scanned blocks {start_height}-{end_height}, found {len(found_payments)} payments")
        
        return found_payments
    
    def get_received_payments(
        self,
        wallet: StealthWallet
    ) -> List[Dict]:
        """
        Get tutti i payments ricevuti.
        
        Args:
            wallet: Stealth wallet
        
        Returns:
            List[Dict]: Lista payments con dettagli
        """
        payments = self.scan_for_payments(wallet)
        
        result = []
        for tx, payment in payments:
            # Find output amount
            output_amount = 0
            for output in tx.outputs:
                if output.address == payment.one_time_address:
                    output_amount = output.amount
                    break
            
            result.append({
                "txid": tx.compute_txid(),
                "timestamp": tx.timestamp,
                "one_time_address": payment.one_time_address,
                "amount": output_amount,
                "ephemeral_public_key": payment.ephemeral_public_key.hex()
            })
        
        return result
    
    # ========================================================================
    # SPENDING
    # ========================================================================
    
    def derive_spend_key_for_payment(
        self,
        wallet: StealthWallet,
        payment: StealthPayment
    ) -> bytes:
        """
        Deriva private key per spendere payment.
        
        Args:
            wallet: Stealth wallet
            payment: Stealth payment
        
        Returns:
            bytes: Private key per one-time address
        """
        spend_key = wallet.derive_spend_key(payment)
        
        logger.info(
            f"Derived spend key for payment",
            extra_data={"address": payment.one_time_address}
        )
        
        return spend_key
    
    # ========================================================================
    # STORAGE
    # ========================================================================
    
    def save_wallet(
        self,
        wallet: StealthWallet,
        wallet_name: str
    ) -> Path:
        """
        Salva stealth wallet su file.
        
        Args:
            wallet: Wallet da salvare
            wallet_name: Nome file
        
        Returns:
            Path: File path
        """
        file_path = self.storage_dir / f"{wallet_name}.json"
        
        wallet_data = {
            "stealth_address": wallet.stealth_address.to_dict(),
            # NOTE: Private keys should be encrypted in production!
            "scan_private_key": wallet.scan_private_key.hex(),
            "spend_private_key": wallet.spend_private_key.hex()
        }
        
        file_path.write_text(json.dumps(wallet_data, indent=2))
        
        logger.info(f"Saved stealth wallet to {file_path}")
        
        return file_path
    
    def load_wallet(
        self,
        wallet_name: str
    ) -> StealthWallet:
        """
        Carica stealth wallet da file.
        
        Args:
            wallet_name: Nome wallet
        
        Returns:
            StealthWallet: Wallet caricato
        """
        file_path = self.storage_dir / f"{wallet_name}.json"
        
        if not file_path.exists():
            raise WalletError(f"Wallet file not found: {file_path}")
        
        wallet_data = json.loads(file_path.read_text())
        
        # Reconstruct stealth address
        addr_data = wallet_data["stealth_address"]
        stealth_address = StealthAddress(
            scan_public_key=bytes.fromhex(addr_data["scan_public_key"]),
            spend_public_key=bytes.fromhex(addr_data["spend_public_key"]),
            encoded_address=addr_data["encoded_address"]
        )
        
        # Create wallet
        wallet = StealthWallet(
            stealth_address=stealth_address,
            scan_private_key=bytes.fromhex(wallet_data["scan_private_key"]),
            spend_private_key=bytes.fromhex(wallet_data["spend_private_key"])
        )
        
        logger.info(f"Loaded stealth wallet from {file_path}")
        
        return wallet
    
    def list_wallets(self) -> List[str]:
        """
        Lista stealth wallets salvati.
        
        Returns:
            List[str]: Nomi wallet
        """
        wallet_files = self.storage_dir.glob("*.json")
        return [f.stem for f in wallet_files]


# ============================================================================
# EXPORT
# ============================================================================

__all__ = [
    "StealthService",
]
