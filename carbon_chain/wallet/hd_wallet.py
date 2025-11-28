"""
CarbonChain - HD Wallet (BIP39/BIP44)
=======================================
Hierarchical Deterministic Wallet con supporto mnemonic.

Security Level: CRITICAL
Last Updated: 2025-11-27
Version: 1.0.0

Features:
- BIP39 mnemonic generation (12/24 words)
- BIP44 key derivation (m/44'/2025'/0'/0/n)
- Address generation deterministica
- Wallet encryption/decryption
- Transaction signing

IMPORTANTE: Private keys e mnemonic DEVONO essere protetti.
"""

from typing import Optional, Tuple, List, Dict
import hashlib
import hmac
import secrets
import json
from dataclasses import dataclass

# Internal imports
from carbon_chain.domain.keypairs import KeyPair, generate_keypair_from_seed
from carbon_chain.domain.addressing import public_key_to_address
from carbon_chain.domain.crypto_core import (
    derive_key_pbkdf2,
    encrypt_data_aes_gcm,
    decrypt_data_aes_gcm,
    generate_random_bytes,
)
from carbon_chain.errors import (
    WalletError,
    InvalidMnemonicError,
    InvalidPasswordError,
    WalletLockedError,
)
from carbon_chain.logging_setup import get_logger
from carbon_chain.config import ChainSettings


# ============================================================================
# MODULE LOGGER
# ============================================================================

logger = get_logger("wallet")


# ============================================================================
# BIP39 WORDLIST (ENGLISH)
# ============================================================================

# BIP39 wordlist completa (2048 parole)
# Per brevità, qui solo subset - in produzione usare lista completa
BIP39_WORDLIST = [
    "abandon", "ability", "able", "about", "above", "absent", "absorb", "abstract",
    "absurd", "abuse", "access", "accident", "account", "accuse", "achieve", "acid",
    "acoustic", "acquire", "across", "act", "action", "actor", "actress", "actual",
    "adapt", "add", "addict", "address", "adjust", "admit", "adult", "advance",
    # ... (lista completa: 2048 parole)
    # Per demo, generiamo pattern prevedibile
]

# Generate full wordlist se necessario
if len(BIP39_WORDLIST) < 2048:
    # Pad con parole generate
    for i in range(len(BIP39_WORDLIST), 2048):
        BIP39_WORDLIST.append(f"word{i:04d}")


# ============================================================================
# HD WALLET
# ============================================================================

class HDWallet:
    """
    Hierarchical Deterministic Wallet.
    
    Implementa:
    - BIP39: Mnemonic seed phrases
    - BIP44: Key derivation paths
    - Address generation deterministica
    - Transaction signing
    
    BIP44 Path: m/44'/2025'/account'/change/address_index
    - 44': BIP44
    - 2025': CarbonChain coin type
    - account': Account number (default 0)
    - change: 0 = external, 1 = internal (change)
    - address_index: Indice address (0, 1, 2, ...)
    
    Attributes:
        mnemonic: Seed phrase (12/24 words)
        seed: Master seed (512-bit)
        master_key: Master private key
        config: Chain configuration
    
    Security:
        - Mnemonic DEVE essere backed up
        - Master key DEVE essere encrypted at rest
        - Derivation deterministica: stesso mnemonic → stesse chiavi
    
    Examples:
        >>> wallet = HDWallet.create_new()
        >>> print(wallet.mnemonic)  # BACKUP THIS!
        'word1 word2 ... word12'
        >>> address, _ = wallet.derive_address(0)
        >>> print(address)
        '1CarbonChain...'
    """
    
    def __init__(
        self,
        mnemonic: str,
        config: Optional[ChainSettings] = None,
        passphrase: str = ""
    ):
        """
        Inizializza HD Wallet da mnemonic.
        
        Args:
            mnemonic: Seed phrase (12 o 24 parole)
            config: Chain configuration (opzionale)
            passphrase: BIP39 passphrase opzionale (default "")
        
        Raises:
            InvalidMnemonicError: Se mnemonic invalido
        """
        from carbon_chain.config import get_settings
        
        self.config = config or get_settings()
        self.mnemonic = mnemonic
        self.passphrase = passphrase
        
        # Valida mnemonic
        if not self._validate_mnemonic(mnemonic):
            raise InvalidMnemonicError(
                "Invalid mnemonic phrase",
                code="INVALID_MNEMONIC"
            )
        
        # Deriva master seed (512-bit)
        self.seed = self._mnemonic_to_seed(mnemonic, passphrase)
        
        # Deriva master key
        self.master_private_key = self._derive_master_key(self.seed)
        
        # Cache addresses (index → (address, keypair))
        self._address_cache: Dict[int, Tuple[str, KeyPair]] = {}
        
        logger.info(
            "HD Wallet initialized",
            extra_data={
                "word_count": len(mnemonic.split()),
                "network": self.config.network
            }
        )
    
    @classmethod
    def create_new(
        cls,
        strength: int = 128,
        config: Optional[ChainSettings] = None,
        passphrase: str = ""
    ) -> "HDWallet":
        """
        Crea nuovo HD Wallet con mnemonic generato.
        
        Args:
            strength: Bit entropia (128=12 parole, 256=24 parole)
            config: Chain configuration
            passphrase: BIP39 passphrase opzionale
        
        Returns:
            HDWallet: Nuovo wallet
        
        Examples:
            >>> wallet = HDWallet.create_new(strength=128)  # 12 words
            >>> len(wallet.mnemonic.split())
            12
        """
        mnemonic = cls._generate_mnemonic(strength)
        return cls(mnemonic, config, passphrase)
    
    @classmethod
    def from_mnemonic(
        cls,
        mnemonic: str,
        config: Optional[ChainSettings] = None,
        passphrase: str = ""
    ) -> "HDWallet":
        """
        Recupera wallet da mnemonic esistente.
        
        Args:
            mnemonic: Seed phrase
            config: Chain configuration
            passphrase: BIP39 passphrase
        
        Returns:
            HDWallet: Wallet recuperato
        
        Examples:
            >>> mnemonic = "word1 word2 ... word12"
            >>> wallet = HDWallet.from_mnemonic(mnemonic)
        """
        return cls(mnemonic, config, passphrase)
    
    # ========================================================================
    # MNEMONIC GENERATION (BIP39)
    # ========================================================================
    
    @staticmethod
    def _generate_mnemonic(strength: int = 128) -> str:
        """
        Genera mnemonic BIP39.
        
        Args:
            strength: Bit entropia (128, 160, 192, 224, 256)
        
        Returns:
            str: Mnemonic phrase
        
        Algorithm:
            1. Genera entropia casuale
            2. Calcola checksum (SHA256)
            3. Concatena entropia + checksum
            4. Dividi in gruppi 11-bit
            5. Mappa su wordlist
        
        Examples:
            >>> mnemonic = HDWallet._generate_mnemonic(128)
            >>> len(mnemonic.split())
            12
        """
        if strength not in [128, 160, 192, 224, 256]:
            raise WalletError(
                f"Invalid strength: {strength}. Must be 128, 160, 192, 224, or 256",
                code="INVALID_STRENGTH"
            )
        
        # 1. Genera entropia
        entropy_bytes = secrets.token_bytes(strength // 8)
        
        # 2. Calcola checksum
        checksum_length = strength // 32
        checksum = hashlib.sha256(entropy_bytes).digest()
        checksum_bits = int.from_bytes(checksum, 'big') >> (256 - checksum_length)
        
        # 3. Concatena entropia + checksum
        entropy_int = int.from_bytes(entropy_bytes, 'big')
        combined = (entropy_int << checksum_length) | checksum_bits
        
        # 4. Dividi in gruppi 11-bit
        word_count = (strength + checksum_length) // 11
        words = []
        
        for _ in range(word_count):
            index = combined & 0x7FF  # 11 bit
            words.append(BIP39_WORDLIST[index])
            combined >>= 11
        
        words.reverse()
        
        return " ".join(words)
    
    @staticmethod
    def _validate_mnemonic(mnemonic: str) -> bool:
        """
        Valida mnemonic BIP39.
        
        Checks:
        - Numero parole corretto (12, 15, 18, 21, 24)
        - Tutte le parole nella wordlist
        - Checksum valido
        
        Args:
            mnemonic: Mnemonic da validare
        
        Returns:
            bool: True se valido
        """
        words = mnemonic.strip().split()
        
        # Check word count
        if len(words) not in [12, 15, 18, 21, 24]:
            return False
        
        # Check tutte le parole esistono
        for word in words:
            if word not in BIP39_WORDLIST:
                return False
        
        # TODO: Validate checksum (omesso per brevità)
        # In produzione: implementare validazione checksum completa
        
        return True
    
    @staticmethod
    def _mnemonic_to_seed(mnemonic: str, passphrase: str = "") -> bytes:
        """
        Converti mnemonic in seed 512-bit (BIP39).
        
        Algorithm:
            PBKDF2-HMAC-SHA512(
                password=mnemonic,
                salt="mnemonic" + passphrase,
                iterations=2048,
                dklen=64
            )
        
        Args:
            mnemonic: Seed phrase
            passphrase: Passphrase opzionale
        
        Returns:
            bytes: 512-bit seed
        """
        # Normalize mnemonic
        mnemonic_normalized = mnemonic.strip().lower()
        
        # Salt = "mnemonic" + passphrase
        salt = ("mnemonic" + passphrase).encode('utf-8')
        
        # PBKDF2
        seed = hashlib.pbkdf2_hmac(
            'sha512',
            mnemonic_normalized.encode('utf-8'),
            salt,
            iterations=2048,
            dklen=64
        )
        
        return seed
    
    @staticmethod
    def _derive_master_key(seed: bytes) -> bytes:
        """
        Deriva master private key da seed (BIP32).
        
        Algorithm:
            I = HMAC-SHA512(key="CarbonChain seed", data=seed)
            master_private_key = I[:32]
            master_chain_code = I[32:]
        
        Args:
            seed: Master seed (64 bytes)
        
        Returns:
            bytes: Master private key (32 bytes)
        """
        # HMAC-SHA512
        hmac_result = hmac.new(
            b"CarbonChain seed",
            seed,
            hashlib.sha512
        ).digest()
        
        master_private_key = hmac_result[:32]
        # master_chain_code = hmac_result[32:]  # Per BIP32 derivation
        
        return master_private_key
    
    # ========================================================================
    # ADDRESS DERIVATION (BIP44)
    # ========================================================================
    
    def derive_address(
        self,
        index: int,
        account: int = 0,
        change: int = 0
    ) -> Tuple[str, KeyPair]:
        """
        Deriva address per indice (BIP44 path).
        
        BIP44 Path: m/44'/2025'/account'/change/address_index
        
        Args:
            index: Address index (0, 1, 2, ...)
            account: Account number (default 0)
            change: 0 = external, 1 = internal change (default 0)
        
        Returns:
            Tuple[str, KeyPair]: (address, keypair)
        
        Examples:
            >>> wallet = HDWallet.create_new()
            >>> address, keypair = wallet.derive_address(0)
            >>> print(address)
            '1CarbonChain...'
        """
        cache_key = (account, change, index)
        
        # Check cache
        if cache_key in self._address_cache:
            return self._address_cache[cache_key]
        
        # Deriva child key (simplified BIP44)
        child_seed = self._derive_child_seed(
            self.master_private_key,
            account,
            change,
            index
        )
        
        # Genera keypair da child seed
        keypair = generate_keypair_from_seed(
            child_seed,
            algorithm=self.config.crypto_algorithm
        )
        
        # Deriva address
        address = public_key_to_address(
            keypair.public_key,
            testnet=self.config.is_testnet()
        )
        
        # Cache
        self._address_cache[cache_key] = (address, keypair)
        
        logger.debug(
            f"Address derived",
            extra_data={
                "index": index,
                "account": account,
                "change": change,
                "address": address[:16] + "..."
            }
        )
        
        return address, keypair
    
    def _derive_child_seed(
        self,
        master_key: bytes,
        account: int,
        change: int,
        index: int
    ) -> bytes:
        """
        Deriva child seed (simplified BIP32).
        
        Full BIP32 implementation richiede chain codes e hardened derivation.
        Questa è versione semplificata per demo.
        
        Args:
            master_key: Master private key
            account: Account index
            change: Change index
            index: Address index
        
        Returns:
            bytes: Child seed (32 bytes)
        """
        # Simplified derivation: hash master + path
        path_bytes = (
            account.to_bytes(4, 'big') +
            change.to_bytes(4, 'big') +
            index.to_bytes(4, 'big')
        )
        
        # HMAC derivation
        child_seed = hmac.new(
            master_key,
            path_bytes,
            hashlib.sha256
        ).digest()
        
        return child_seed
    
    def get_address(self, index: int) -> str:
        """
        Ottieni address per indice (shortcut).
        
        Args:
            index: Address index
        
        Returns:
            str: Address
        """
        address, _ = self.derive_address(index)
        return address
    
    def get_keypair(self, index: int) -> KeyPair:
        """
        Ottieni keypair per indice.
        
        Args:
            index: Address index
        
        Returns:
            KeyPair: Keypair per address
        """
        _, keypair = self.derive_address(index)
        return keypair
    
    def find_address_index(self, address: str, max_search: int = 1000) -> Optional[int]:
        """
        Trova indice address nel wallet.
        
        Args:
            address: Address da cercare
            max_search: Max indici da controllare
        
        Returns:
            int: Indice se trovato, None altrimenti
        
        Examples:
            >>> wallet = HDWallet.create_new()
            >>> addr, _ = wallet.derive_address(5)
            >>> wallet.find_address_index(addr)
            5
        """
        for index in range(max_search):
            derived_addr, _ = self.derive_address(index)
            if derived_addr == address:
                return index
        
        return None
    
    # ========================================================================
    # TRANSACTION SIGNING
    # ========================================================================
    
    def sign_transaction(
        self,
        tx,
        from_address: str
    ):
        """
        Firma transazione con keypair corretto.
        
        Args:
            tx: Transaction da firmare
            from_address: Address mittente
        
        Returns:
            Transaction: Tx firmata
        
        Raises:
            WalletError: Se address non trovato nel wallet
        
        Examples:
            >>> wallet = HDWallet.create_new()
            >>> addr = wallet.get_address(0)
            >>> tx = Transaction(...)
            >>> signed_tx = wallet.sign_transaction(tx, addr)
        """
        # Trova keypair per address
        address_index = self.find_address_index(from_address)
        
        if address_index is None:
            raise WalletError(
                f"Address {from_address} not found in wallet",
                code="ADDRESS_NOT_FOUND"
            )
        
        keypair = self.get_keypair(address_index)
        
        # Crea signing message
        tx_dict = tx.to_dict(include_signatures=False)
        signing_message = json.dumps(tx_dict, sort_keys=True).encode('utf-8')
        
        # Firma
        signature = keypair.sign(signing_message)
        
        # Aggiungi firma a input
        from dataclasses import replace
        
        signed_inputs = []
        for inp in tx.inputs:
            signed_inp = replace(
                inp,
                signature=signature,
                public_key=keypair.public_key
            )
            signed_inputs.append(signed_inp)
        
        # Crea tx firmata
        signed_tx = replace(tx, inputs=signed_inputs)
        
        logger.info(
            "Transaction signed",
            extra_data={
                "txid": tx.compute_txid()[:16] + "...",
                "from_address": from_address[:16] + "..."
            }
        )
        
        return signed_tx
    
    # ========================================================================
    # WALLET ENCRYPTION
    # ========================================================================
    
    def export_encrypted(self, password: str) -> Dict[str, str]:
        """
        Export wallet encrypted con password.
        
        Args:
            password: Password encryption
        
        Returns:
            dict: Wallet encrypted {
                "encrypted_mnemonic": str,
                "salt": str,
                "nonce": str,
                "network": str
            }
        
        Security:
            - Password → key derivation PBKDF2
            - Mnemonic criptato con AES-256-GCM
        
        Examples:
            >>> wallet = HDWallet.create_new()
            >>> encrypted = wallet.export_encrypted("strong_password")
            >>> # Save encrypted to file
        """
        if len(password) < 8:
            raise InvalidPasswordError(
                "Password too weak. Minimum 8 characters.",
                code="WEAK_PASSWORD"
            )
        
        # Generate salt
        salt = generate_random_bytes(16)
        
        # Deriva encryption key
        key = derive_key_pbkdf2(
            password=password.encode('utf-8'),
            salt=salt,
            iterations=100_000,
            key_length=32
        )
        
        # Encrypt mnemonic
        encrypted_mnemonic, nonce = encrypt_data_aes_gcm(
            plaintext=self.mnemonic.encode('utf-8'),
            key=key
        )
        
        logger.info("Wallet exported (encrypted)")
        
        return {
            "encrypted_mnemonic": encrypted_mnemonic.hex(),
            "salt": salt.hex(),
            "nonce": nonce.hex(),
            "network": self.config.network,
            "version": "1.0.0"
        }
    
    @classmethod
    def import_encrypted(
        cls,
        encrypted_data: Dict[str, str],
        password: str,
        config: Optional[ChainSettings] = None
    ) -> "HDWallet":
        """
        Import wallet da export encrypted.
        
        Args:
            encrypted_data: Dict da export_encrypted()
            password: Password decryption
            config: Chain configuration
        
        Returns:
            HDWallet: Wallet decriptato
        
        Raises:
            InvalidPasswordError: Se password errata
        
        Examples:
            >>> encrypted = {...}  # From export
            >>> wallet = HDWallet.import_encrypted(encrypted, "password")
        """
        from carbon_chain.config import get_settings
        
        config = config or get_settings()
        
        # Parse encrypted data
        encrypted_mnemonic = bytes.fromhex(encrypted_data["encrypted_mnemonic"])
        salt = bytes.fromhex(encrypted_data["salt"])
        nonce = bytes.fromhex(encrypted_data["nonce"])
        
        # Deriva key
        key = derive_key_pbkdf2(
            password=password.encode('utf-8'),
            salt=salt,
            iterations=100_000,
            key_length=32
        )
        
        # Decrypt mnemonic
        try:
            mnemonic_bytes = decrypt_data_aes_gcm(
                ciphertext=encrypted_mnemonic,
                key=key,
                nonce=nonce
            )
            mnemonic = mnemonic_bytes.decode('utf-8')
        except Exception:
            raise InvalidPasswordError(
                "Invalid password or corrupted wallet data",
                code="DECRYPTION_FAILED"
            )
        
        logger.info("Wallet imported (decrypted)")
        
        return cls(mnemonic, config)
    
    # ========================================================================
    # WALLET INFO
    # ========================================================================
    
    def get_mnemonic(self) -> str:
        """
        Ottieni mnemonic phrase.
        
        WARNING: MANTIENI SEGRETO!
        
        Returns:
            str: Mnemonic (12 o 24 parole)
        """
        logger.warning("⚠️ Mnemonic accessed - ensure secure handling!")
        return self.mnemonic
    
    def get_addresses(self, count: int = 10) -> List[str]:
        """
        Ottieni prime N addresses.
        
        Args:
            count: Numero addresses
        
        Returns:
            List[str]: Lista addresses
        
        Examples:
            >>> wallet = HDWallet.create_new()
            >>> addresses = wallet.get_addresses(5)
            >>> len(addresses)
            5
        """
        return [self.get_address(i) for i in range(count)]
    
    def __repr__(self) -> str:
        """Safe repr (no mnemonic)"""
        addr0 = self.get_address(0)
        return (
            f"HDWallet(network={self.config.network}, "
            f"address_0={addr0[:16]}...)"
        )


# ============================================================================
# EXPORT
# ============================================================================

__all__ = [
    "HDWallet",
]
