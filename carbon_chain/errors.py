"""
CarbonChain - Custom Exceptions
=================================
Gerarchia completa di eccezioni per gestione errori granulare.

Security Level: HIGH
Last Updated: 2025-11-26
Version: 1.0.0
"""

from typing import Optional, Any


# ============================================================================
# BASE EXCEPTION
# ============================================================================

class CarbonChainException(Exception):
    """
    Eccezione base per tutte le eccezioni CarbonChain.
    
    Attributes:
        message (str): Messaggio errore
        code (str): Codice errore (es. "CERT_001")
        details (dict): Dettagli aggiuntivi
    """
    
    def __init__(
        self,
        message: str,
        code: Optional[str] = None,
        details: Optional[dict] = None
    ):
        self.message = message
        self.code = code or self.__class__.__name__
        self.details = details or {}
        
        super().__init__(self.message)
    
    def to_dict(self) -> dict:
        """Serializza eccezione per API/logging"""
        return {
            "error": self.code,
            "message": self.message,
            "details": self.details,
        }
    
    def __str__(self) -> str:
        if self.details:
            return f"[{self.code}] {self.message} | Details: {self.details}"
        return f"[{self.code}] {self.message}"


# ============================================================================
# CONFIGURATION ERRORS
# ============================================================================

class ConfigError(CarbonChainException):
    """Errore configurazione sistema"""
    pass


class InvalidConfigError(ConfigError):
    """Configurazione invalida"""
    pass


# ============================================================================
# BLOCKCHAIN ERRORS
# ============================================================================

class BlockchainError(CarbonChainException):
    """Errore generico blockchain"""
    pass


class GenesisError(BlockchainError):
    """Errore genesis block"""
    pass


class ChainSyncError(BlockchainError):
    """Errore sincronizzazione chain"""
    pass


# ============================================================================
# VALIDATION ERRORS
# ============================================================================

class ValidationError(CarbonChainException):
    """Errore validazione (base)"""
    pass


class BlockError(ValidationError):
    """Errore validazione blocco"""
    pass


class InvalidBlockError(BlockError):
    """Blocco invalido"""
    pass


class BlockSizeExceededError(BlockError):
    """Dimensione blocco superata"""
    pass


class TransactionError(ValidationError):
    """Errore transazione"""
    pass


class InvalidTransactionError(TransactionError):
    """Transazione invalida"""
    pass


class InsufficientFundsError(TransactionError):
    """Fondi insufficienti"""
    pass


class DoubleSpendError(TransactionError):
    """Tentativo double-spend"""
    pass


class InvalidSignatureError(TransactionError):
    """Firma invalida"""
    pass


class TxSizeExceededError(TransactionError):
    """Dimensione tx superata"""
    pass


# ============================================================================
# PROOF OF WORK ERRORS
# ============================================================================

class PoWError(ValidationError):
    """Errore Proof of Work"""
    pass


class InvalidPoWError(PoWError):
    """PoW non valido"""
    pass


class DifficultyError(PoWError):
    """Errore difficulty"""
    pass


# ============================================================================
# CERTIFICATE ERRORS
# ============================================================================

class CertificateError(ValidationError):
    """Errore certificato CO2"""
    pass


class InvalidCertificateError(CertificateError):
    """Certificato invalido"""
    pass


class CertificateDuplicateError(CertificateError):
    """Certificato duplicato (hash già usato)"""
    pass


class CertificateExhaustedError(CertificateError):
    """Certificato esaurito (kg superati)"""
    pass


class CertificateExpiredError(CertificateError):
    """Certificato scaduto"""
    pass


class CertificateRevokedError(CertificateError):
    """Certificato revocato"""
    pass


class MissingCertificateFieldError(CertificateError):
    """Campo obbligatorio certificato mancante"""
    pass


# ============================================================================
# COMPENSATION ERRORS
# ============================================================================

class CompensationError(ValidationError):
    """Errore compensazione"""
    pass


class InvalidCompensationError(CompensationError):
    """Compensazione invalida"""
    pass


class CompensationAlreadyUsedError(CompensationError):
    """Output già compensato (non riusabile)"""
    pass


class CompensationMixedProjectsError(CompensationError):
    """Mix di progetti nella stessa tx"""
    pass


class CompensationNotCertifiedError(CompensationError):
    """Tentativo compensazione con coin non certificati"""
    pass


# ============================================================================
# STORAGE ERRORS
# ============================================================================

class StorageError(CarbonChainException):
    """Errore storage/database"""
    pass


class DatabaseError(StorageError):
    """Errore database generico"""
    pass


class DatabaseConnectionError(DatabaseError):
    """Errore connessione database"""
    pass


class DatabaseCorruptionError(DatabaseError):
    """Database corrotto"""
    pass


class BlockNotFoundError(StorageError):
    """Blocco non trovato"""
    pass


class TransactionNotFoundError(StorageError):
    """Transazione non trovata"""
    pass


# ============================================================================
# WALLET ERRORS
# ============================================================================

class WalletError(CarbonChainException):
    """Errore wallet"""
    pass


class InvalidWalletError(WalletError):
    """Wallet invalido"""
    pass


class WalletLockedError(WalletError):
    """Wallet bloccato (richiede password)"""
    pass


class InvalidPasswordError(WalletError):
    """Password wallet errata"""
    pass


class KeyNotFoundError(WalletError):
    """Chiave non trovata in wallet"""
    pass


class InvalidAddressError(WalletError):
    """Indirizzo invalido"""
    pass


class InvalidMnemonicError(WalletError):
    """Mnemonic phrase invalida"""
    pass


# ============================================================================
# CRYPTOGRAPHY ERRORS
# ============================================================================

class CryptoError(CarbonChainException):
    """Errore crittografia"""
    pass


class InvalidKeyError(CryptoError):
    """Chiave crittografica invalida"""
    pass


class EncryptionError(CryptoError):
    """Errore encryption"""
    pass


class DecryptionError(CryptoError):
    """Errore decryption"""
    pass


class HashMismatchError(CryptoError):
    """Hash non corrisponde"""
    pass


# ============================================================================
# NETWORK/P2P ERRORS
# ============================================================================

class P2PError(CarbonChainException):
    """Errore networking P2P"""
    pass


class PeerError(P2PError):
    """Errore comunicazione peer"""
    pass


class PeerConnectionError(PeerError):
    """Errore connessione peer"""
    pass


class PeerTimeoutError(PeerError):
    """Timeout comunicazione peer"""
    pass


class InvalidMessageError(PeerError):
    """Messaggio P2P invalido"""
    pass


class SyncError(P2PError):
    """Errore sincronizzazione"""
    pass


class MaxPeersReachedError(P2PError):
    """Numero massimo peer raggiunto"""
    pass


# ============================================================================
# API ERRORS
# ============================================================================

class APIError(CarbonChainException):
    """Errore API REST"""
    pass


class InvalidRequestError(APIError):
    """Request API invalida"""
    pass


class RateLimitError(APIError):
    """Rate limit superato"""
    pass


class AuthenticationError(APIError):
    """Errore autenticazione"""
    pass


class AuthorizationError(APIError):
    """Errore autorizzazione"""
    pass


# ============================================================================
# MINING ERRORS
# ============================================================================

class MiningError(CarbonChainException):
    """Errore mining"""
    pass


class InvalidNonceError(MiningError):
    """Nonce invalido"""
    pass


class MiningTimeoutError(MiningError):
    """Timeout mining"""
    pass


# ============================================================================
# MEMPOOL ERRORS
# ============================================================================

class MempoolError(CarbonChainException):
    """Errore mempool"""
    pass


class MempoolFullError(MempoolError):
    """Mempool pieno"""
    pass


class TransactionConflictError(MempoolError):
    """Conflitto transazione in mempool"""
    pass


# ============================================================================
# QR CODE ERRORS
# ============================================================================

class QRCodeError(CarbonChainException):
    """Errore generazione QR code"""
    pass


class InvalidQRDataError(QRCodeError):
    """Dati QR invalidi"""
    pass


# ============================================================================
# UTXO ERRORS
# ============================================================================

class UTXOError(CarbonChainException):
    """Errore UTXO set"""
    pass


class UTXONotFoundError(UTXOError):
    """UTXO non trovato"""
    pass


class UTXONotSpendableError(UTXOError):
    """UTXO non spendibile"""
    pass


# ============================================================================
# SUPPLY ERRORS
# ============================================================================

class SupplyError(ValidationError):
    """Errore supply"""
    pass


class MaxSupplyExceededError(SupplyError):
    """Supply massima superata"""
    pass


class InvalidSubsidyError(SupplyError):
    """Subsidy invalido"""
    pass


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def format_validation_error(
    field: str,
    value: Any,
    expected: str,
    code: Optional[str] = None
) -> ValidationError:
    """
    Helper per creare ValidationError formattati.
    
    Args:
        field: Nome campo invalido
        value: Valore ricevuto
        expected: Valore/tipo atteso
        code: Codice errore custom
    
    Returns:
        ValidationError: Eccezione formattata
    
    Example:
        >>> raise format_validation_error("amount", -100, "positive integer")
    """
    return ValidationError(
        message=f"Invalid field '{field}': expected {expected}, got {value}",
        code=code or "VALIDATION_FAILED",
        details={"field": field, "value": value, "expected": expected}
    )


def format_certificate_error(
    cert_id: str,
    issue: str,
    code: Optional[str] = None
) -> CertificateError:
    """Helper per errori certificati"""
    return CertificateError(
        message=f"Certificate '{cert_id}': {issue}",
        code=code or "CERT_ERROR",
        details={"certificate_id": cert_id, "issue": issue}
    )


def format_compensation_error(
    project_id: str,
    issue: str,
    code: Optional[str] = None
) -> CompensationError:
    """Helper per errori compensazione"""
    return CompensationError(
        message=f"Compensation project '{project_id}': {issue}",
        code=code or "COMP_ERROR",
        details={"project_id": project_id, "issue": issue}
    )


# ============================================================================
# EXPORT ALL
# ============================================================================

__all__ = [
    # Base
    "CarbonChainException",
    
    # Config
    "ConfigError",
    "InvalidConfigError",
    
    # Blockchain
    "BlockchainError",
    "GenesisError",
    "ChainSyncError",
    
    # Validation
    "ValidationError",
    "BlockError",
    "InvalidBlockError",
    "BlockSizeExceededError",
    "TransactionError",
    "InvalidTransactionError",
    "InsufficientFundsError",
    "DoubleSpendError",
    "InvalidSignatureError",
    "TxSizeExceededError",
    
    # PoW
    "PoWError",
    "InvalidPoWError",
    "DifficultyError",
    
    # Certificates
    "CertificateError",
    "InvalidCertificateError",
    "CertificateDuplicateError",
    "CertificateExhaustedError",
    "CertificateExpiredError",
    "CertificateRevokedError",
    "MissingCertificateFieldError",
    
    # Compensation
    "CompensationError",
    "InvalidCompensationError",
    "CompensationAlreadyUsedError",
    "CompensationMixedProjectsError",
    "CompensationNotCertifiedError",
    
    # Storage
    "StorageError",
    "DatabaseError",
    "DatabaseConnectionError",
    "DatabaseCorruptionError",
    "BlockNotFoundError",
    "TransactionNotFoundError",
    
    # Wallet
    "WalletError",
    "InvalidWalletError",
    "WalletLockedError",
    "InvalidPasswordError",
    "KeyNotFoundError",
    "InvalidAddressError",
    "InvalidMnemonicError",
    
    # Crypto
    "CryptoError",
    "InvalidKeyError",
    "EncryptionError",
    "DecryptionError",
    "HashMismatchError",
    
    # P2P
    "P2PError",
    "PeerError",
    "PeerConnectionError",
    "PeerTimeoutError",
    "InvalidMessageError",
    "SyncError",
    "MaxPeersReachedError",
    
    # API
    "APIError",
    "InvalidRequestError",
    "RateLimitError",
    "AuthenticationError",
    "AuthorizationError",
    
    # Mining
    "MiningError",
    "InvalidNonceError",
    "MiningTimeoutError",
    
    # Mempool
    "MempoolError",
    "MempoolFullError",
    "TransactionConflictError",
    
    # QR
    "QRCodeError",
    "InvalidQRDataError",
    
    # UTXO
    "UTXOError",
    "UTXONotFoundError",
    "UTXONotSpendableError",
    
    # Supply
    "SupplyError",
    "MaxSupplyExceededError",
    "InvalidSubsidyError",
    
    # Helpers
    "format_validation_error",
    "format_certificate_error",
    "format_compensation_error",
]
