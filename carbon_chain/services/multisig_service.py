"""
CarbonChain - MultiSig Service
================================
Service layer per operazioni multi-signature.

Security Level: HIGH
Last Updated: 2025-11-27
Version: 1.0.0
"""

from typing import List, Dict, Optional
import json
from pathlib import Path

# Internal imports
from carbon_chain.wallet.multisig import (
    MultiSigWallet,
    MultiSigConfig,
    PSBT,
    PartialSignature
)
from carbon_chain.domain.blockchain import Blockchain
from carbon_chain.domain.models import Transaction
from carbon_chain.errors import WalletError, ValidationError
from carbon_chain.logging_setup import get_logger
from carbon_chain.config import ChainSettings


# ============================================================================
# MODULE LOGGER
# ============================================================================

logger = get_logger("services.multisig")


# ============================================================================
# MULTISIG SERVICE
# ============================================================================

class MultiSigService:
    """
    Service per gestione wallet multi-signature.
    
    Features:
    - Creazione wallet multisig
    - Gestione PSBT
    - Coordinamento firme
    - Storage configurazioni
    
    Attributes:
        blockchain: Blockchain instance
        config: Chain settings
        storage_dir: Directory storage wallet
    
    Examples:
        >>> service = MultiSigService(blockchain, config)
        >>> wallet = service.create_multisig_wallet(m=2, n=3, my_index=0)
        >>> psbt = service.create_transaction_psbt(wallet, tx_data)
    """
    
    def __init__(
        self,
        blockchain: Blockchain,
        config: ChainSettings,
        storage_dir: Optional[Path] = None
    ):
        """
        Initialize multisig service.
        
        Args:
            blockchain: Blockchain instance
            config: Chain configuration
            storage_dir: Storage directory for wallets
        """
        self.blockchain = blockchain
        self.config = config
        
        # Storage directory
        self.storage_dir = storage_dir or (config.wallet_dir / "multisig")
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info("MultiSig service initialized")
    
    # ========================================================================
    # WALLET CREATION
    # ========================================================================
    
    def create_multisig_wallet(
        self,
        m: int,
        n: int,
        my_index: int,
        other_public_keys: List[bytes],
        wallet_name: Optional[str] = None
    ) -> MultiSigWallet:
        """
        Crea nuovo wallet multi-signature.
        
        Args:
            m: Firme richieste
            n: Firme totali
            my_index: Indice di questo partecipante
            other_public_keys: Public keys altri partecipanti
            wallet_name: Nome wallet (optional)
        
        Returns:
            MultiSigWallet: Wallet creato
        
        Examples:
            >>> wallet = service.create_multisig_wallet(
            ...     m=2, n=3, my_index=0,
            ...     other_public_keys=[pk1, pk2]
            ... )
        """
        # Validate parameters
        if len(other_public_keys) != n - 1:
            raise ValidationError(
                f"Expected {n-1} other public keys, got {len(other_public_keys)}"
            )
        
        # Create wallet
        wallet = MultiSigWallet.create(
            m=m,
            n=n,
            my_index=my_index,
            other_public_keys=other_public_keys,
            config=self.config
        )
        
        # Save wallet
        if wallet_name:
            self.save_wallet(wallet, wallet_name)
        
        logger.info(
            f"Created {m}-of-{n} multisig wallet",
            extra_data={
                "address": wallet.get_address(),
                "my_index": my_index
            }
        )
        
        return wallet
    
    def import_multisig_wallet(
        self,
        config_dict: Dict,
        my_index: int,
        my_private_key: bytes,
        wallet_name: Optional[str] = None
    ) -> MultiSigWallet:
        """
        Importa wallet multisig da configurazione.
        
        Args:
            config_dict: MultiSigConfig serializzato
            my_index: Indice di questo partecipante
            my_private_key: Private key
            wallet_name: Nome wallet
        
        Returns:
            MultiSigWallet: Wallet importato
        """
        # Reconstruct config
        multisig_config = MultiSigConfig.from_dict(config_dict)
        
        # Get public key
        my_public_key = multisig_config.public_keys[my_index]
        
        # Create wallet
        wallet = MultiSigWallet(
            config=multisig_config,
            my_index=my_index,
            my_private_key=my_private_key,
            my_public_key=my_public_key
        )
        
        # Save wallet
        if wallet_name:
            self.save_wallet(wallet, wallet_name)
        
        logger.info(f"Imported multisig wallet: {wallet.get_address()}")
        
        return wallet
    
    # ========================================================================
    # PSBT MANAGEMENT
    # ========================================================================
    
    def create_transaction_psbt(
        self,
        wallet: MultiSigWallet,
        transaction: Transaction
    ) -> PSBT:
        """
        Crea PSBT per transazione.
        
        Args:
            wallet: MultiSig wallet
            transaction: Transaction da firmare
        
        Returns:
            PSBT: PSBT instance
        """
        # Serialize transaction
        tx_data = transaction.serialize()
        
        # Create PSBT
        psbt = wallet.create_psbt(tx_data)
        
        logger.info(
            f"Created PSBT for transaction",
            extra_data={"txid": transaction.compute_txid()[:16] + "..."}
        )
        
        return psbt
    
    def sign_psbt(
        self,
        wallet: MultiSigWallet,
        psbt: PSBT
    ) -> bool:
        """
        Firma PSBT con wallet.
        
        Args:
            wallet: MultiSig wallet
            psbt: PSBT da firmare
        
        Returns:
            bool: True se firma aggiunta
        """
        success = wallet.sign_psbt(psbt)
        
        if success:
            logger.info(
                f"Signed PSBT",
                extra_data={
                    "signer_index": wallet.my_index,
                    "signatures": f"{len(psbt.partial_signatures)}/{psbt.multisig_config.m}"
                }
            )
        
        return success
    
    def combine_psbts(
        self,
        psbts: List[PSBT]
    ) -> PSBT:
        """
        Combina multiple PSBT con firme parziali.
        
        Args:
            psbts: Lista PSBT da combinare
        
        Returns:
            PSBT: PSBT combinato
        
        Raises:
            ValidationError: Se PSBT incompatibili
        """
        if not psbts:
            raise ValidationError("No PSBTs provided")
        
        # Use first as base
        combined = psbts[0]
        
        # Combine signatures from others
        for psbt in psbts[1:]:
            # Validate same transaction
            if psbt.transaction_data != combined.transaction_data:
                raise ValidationError("PSBTs have different transaction data")
            
            # Add signatures not already present
            for sig in psbt.partial_signatures:
                if not any(s.signer_index == sig.signer_index 
                          for s in combined.partial_signatures):
                    combined.partial_signatures.append(sig)
        
        # Check if finalized
        if len(combined.partial_signatures) >= combined.multisig_config.m:
            combined.is_finalized = True
        
        logger.info(
            f"Combined PSBTs",
            extra_data={
                "total_signatures": len(combined.partial_signatures),
                "finalized": combined.is_finalized
            }
        )
        
        return combined
    
    def finalize_psbt(
        self,
        psbt: PSBT
    ) -> Optional[Transaction]:
        """
        Finalizza PSBT e crea transazione completa.
        
        Args:
            psbt: PSBT da finalizzare
        
        Returns:
            Transaction: Transazione completa, o None se non finalized
        """
        if not psbt.is_finalized:
            logger.warning("PSBT not finalized - insufficient signatures")
            return None
        
        # Verify all signatures
        if not psbt.verify_signatures():
            logger.error("PSBT signature verification failed")
            return None
        
        # Get finalized signatures
        signatures = psbt.get_finalized_signatures()
        
        # Deserialize transaction
        transaction = Transaction.deserialize(psbt.transaction_data)
        
        # Attach signatures to transaction
        # (In production: implement proper signature attachment)
        transaction.metadata["multisig_signatures"] = [sig.hex() for sig in signatures]
        
        logger.info(
            f"Finalized PSBT",
            extra_data={"txid": transaction.compute_txid()[:16] + "..."}
        )
        
        return transaction
    
    # ========================================================================
    # STORAGE
    # ========================================================================
    
    def save_wallet(
        self,
        wallet: MultiSigWallet,
        wallet_name: str
    ) -> Path:
        """
        Salva wallet su file.
        
        Args:
            wallet: Wallet da salvare
            wallet_name: Nome file
        
        Returns:
            Path: File path
        """
        file_path = self.storage_dir / f"{wallet_name}.json"
        
        wallet_data = {
            "config": wallet.config.to_dict(),
            "my_index": wallet.my_index,
            # NOTE: Private keys should be encrypted in production!
            "my_private_key": wallet.my_private_key.hex(),
            "my_public_key": wallet.my_public_key.hex()
        }
        
        file_path.write_text(json.dumps(wallet_data, indent=2))
        
        logger.info(f"Saved multisig wallet to {file_path}")
        
        return file_path
    
    def load_wallet(
        self,
        wallet_name: str
    ) -> MultiSigWallet:
        """
        Carica wallet da file.
        
        Args:
            wallet_name: Nome wallet
        
        Returns:
            MultiSigWallet: Wallet caricato
        """
        file_path = self.storage_dir / f"{wallet_name}.json"
        
        if not file_path.exists():
            raise WalletError(f"Wallet file not found: {file_path}")
        
        wallet_data = json.loads(file_path.read_text())
        
        # Reconstruct wallet
        config = MultiSigConfig.from_dict(wallet_data["config"])
        
        wallet = MultiSigWallet(
            config=config,
            my_index=wallet_data["my_index"],
            my_private_key=bytes.fromhex(wallet_data["my_private_key"]),
            my_public_key=bytes.fromhex(wallet_data["my_public_key"])
        )
        
        logger.info(f"Loaded multisig wallet from {file_path}")
        
        return wallet
    
    def list_wallets(self) -> List[str]:
        """
        Lista wallet salvati.
        
        Returns:
            List[str]: Nomi wallet
        """
        wallet_files = self.storage_dir.glob("*.json")
        return [f.stem for f in wallet_files]
    
    # ========================================================================
    # QUERIES
    # ========================================================================
    
    def get_balance(
        self,
        wallet: MultiSigWallet
    ) -> int:
        """
        Get balance del wallet multisig.
        
        Args:
            wallet: MultiSig wallet
        
        Returns:
            int: Balance in Satoshi
        """
        address = wallet.get_address()
        balance = self.blockchain.get_balance(address)
        
        return balance
    
    def get_utxos(
        self,
        wallet: MultiSigWallet
    ) -> List:
        """
        Get UTXOs del wallet multisig.
        
        Args:
            wallet: MultiSig wallet
        
        Returns:
            List: UTXOs
        """
        address = wallet.get_address()
        utxos = self.blockchain.get_utxos(address)
        
        return utxos


# ============================================================================
# EXPORT
# ============================================================================

__all__ = [
    "MultiSigService",
]
