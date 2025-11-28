"""
CarbonChain - Core Constants
================================
Costanti immutabili del protocollo blockchain.

Security Level: CRITICAL
Last Updated: 2025-11-26
Version: 1.0.0

IMPORTANTE: Questo file è parte del core sigillato.
Modifiche non autorizzate invalideranno la firma digitale del sistema.
"""

from enum import IntEnum, Enum
from typing import Final
import hashlib

# ============================================================================
# IDENTIFICAZIONE PROGETTO
# ============================================================================

COIN_NAME: Final[str] = "CarbonChain"
COIN_TICKER: Final[str] = "CCO2"
COIN_SYMBOL: Final[str] = "₡"  # Simbolo Unicode custom

# Versione protocollo (semantic versioning)
PROTOCOL_VERSION: Final[int] = 1
SOFTWARE_VERSION: Final[str] = "1.0.0"

# Network magic bytes (identificazione pacchetti P2P)
NETWORK_MAGIC: Final[bytes] = b'CCO2'
TESTNET_MAGIC: Final[bytes] = b'TCCO'

# ============================================================================
# SISTEMA MONETARIO - DENOMINAZIONI SATOSHI
# ============================================================================

# Unità base: 1 Satoshi = 1 kg CO2
SATOSHI_PER_COIN: Final[int] = 100_000_000  # 100 milioni (come Bitcoin)

# Denominazioni leggibili
COIN_DECIMALS: Final[int] = 8  # Precisione decimale

# Funzioni helper per conversione
def coin_to_satoshi(amount_coin: float) -> int:
    """
    Converte CCO2 coin in Satoshi (unità base).
    
    Args:
        amount_coin: Quantità in CCO2 (es. 1.5 CCO2)
    
    Returns:
        int: Quantità in Satoshi (es. 150000000)
    
    Examples:
        >>> coin_to_satoshi(1.0)
        100000000
        >>> coin_to_satoshi(0.00001)  # 1 tonnellata CO2
        1000
    """
    return int(amount_coin * SATOSHI_PER_COIN)


def satoshi_to_coin(amount_satoshi: int) -> float:
    """
    Converte Satoshi in CCO2 coin.
    
    Args:
        amount_satoshi: Quantità in Satoshi (kg CO2)
    
    Returns:
        float: Quantità in CCO2 coin
    
    Examples:
        >>> satoshi_to_coin(100000000)
        1.0
        >>> satoshi_to_coin(1000)  # 1 tonnellata
        0.00001
    """
    return amount_satoshi / SATOSHI_PER_COIN


def format_amount(amount_satoshi: int, unit: str = "CCO2") -> str:
    """
    Formatta amount per display umano.
    
    Args:
        amount_satoshi: Quantità in Satoshi
        unit: Unità di misura ("CCO2", "kg", "t", "Mt")
    
    Returns:
        str: Amount formattato (es. "1.50000000 CCO2", "1,000 kg CO2")
    
    Examples:
        >>> format_amount(150000000, "CCO2")
        '1.50000000 CCO2'
        >>> format_amount(1000000, "t")
        '1,000 t CO2'
    """
    if unit == "CCO2":
        coin = satoshi_to_coin(amount_satoshi)
        return f"{coin:.{COIN_DECIMALS}f} {COIN_TICKER}"
    
    elif unit == "kg":
        return f"{amount_satoshi:,} kg CO2"
    
    elif unit == "t":
        tonnes = amount_satoshi / 1000
        return f"{tonnes:,.3f} t CO2"
    
    elif unit == "Mt":
        megatonnes = amount_satoshi / 1_000_000_000
        return f"{megatonnes:,.6f} Mt CO2"
    
    else:
        return str(amount_satoshi)


# ============================================================================
# SUPPLY ECONOMICS
# ============================================================================

# Supply massima: 1 Gigatonnellata CO2 = 1 miliardo kg = 10 CCO2
MAX_SUPPLY_SATOSHI: Final[int] = 1_000_000_000  # 1 miliardo kg
MAX_SUPPLY_COIN: Final[float] = satoshi_to_coin(MAX_SUPPLY_SATOSHI)  # 10 CCO2

# Subsidy iniziale per blocco (in Satoshi)
INITIAL_SUBSIDY_SATOSHI: Final[int] = coin_to_satoshi(0.5)  # 50 milioni Satoshi = 0.5 CCO2

# Halving interval (blocchi)
HALVING_INTERVAL: Final[int] = 210_000  # ~4 anni con 10 min/blocco

# Block time target (secondi)
BLOCK_TIME_TARGET: Final[int] = 600  # 10 minuti

# Difficulty adjustment interval
DIFFICULTY_ADJUSTMENT_INTERVAL: Final[int] = 2016  # ~2 settimane

# ============================================================================
# LIMITI TECNICI
# ============================================================================

# Dimensioni massime
MAX_BLOCK_SIZE: Final[int] = 4_000_000  # 4 MB
MAX_TX_SIZE: Final[int] = 1_000_000  # 1 MB
MAX_TXS_PER_BLOCK: Final[int] = 5_000
MAX_SCRIPT_SIZE: Final[int] = 10_000  # Script signature size

# Limiti temporali
MAX_FUTURE_BLOCK_TIME: Final[int] = 2 * 60 * 60  # 2 ore nel futuro
MEDIAN_TIME_SPAN: Final[int] = 11  # Blocchi per calcolo median time

# Limiti economici
MIN_TX_OUTPUT_SATOSHI: Final[int] = 1  # 1 kg CO2 minimo
MAX_TX_OUTPUT_SATOSHI: Final[int] = MAX_SUPPLY_SATOSHI

# Fee minima (opzionale, per ora zero per tx CO2)
MIN_FEE_SATOSHI: Final[int] = 0

# ============================================================================
# TIPI DI TRANSAZIONE
# ============================================================================

class TxType(IntEnum):
    """
    Enum per tipi di transazione.
    
    Valori:
        COINBASE (0): Mining reward (creazione coin)
        TRANSFER (1): Trasferimento standard
        ASSIGN_CERT (2): Assegnazione certificato CO2
        ASSIGN_COMPENSATION (3): Compensazione progetto
        BURN (4): Distruzione coin
    """
    COINBASE = 0
    TRANSFER = 1
    ASSIGN_CERT = 2
    ASSIGN_COMPENSATION = 3
    BURN = 4


class TxStatus(Enum):
    """Stato transazione"""
    PENDING = "pending"  # In mempool
    CONFIRMED = "confirmed"  # In blocco
    REJECTED = "rejected"  # Rifiutata


# ============================================================================
# STATI CERTIFICATI E PROGETTI
# ============================================================================

class CertificateState(Enum):
    """
    Stato di un certificato CO2.
    
    Stati:
        ACTIVE: Certificato valido, pronto per compensazione
        PARTIALLY_COMPENSATED: Parte del certificato usato
        FULLY_COMPENSATED: Certificato completamente utilizzato
        EXPIRED: Certificato scaduto (se expiry_date presente)
        REVOKED: Certificato revocato da issuer
    """
    ACTIVE = "active"
    PARTIALLY_COMPENSATED = "partially_compensated"
    FULLY_COMPENSATED = "fully_compensated"
    EXPIRED = "expired"
    REVOKED = "revoked"


class CompensationProjectStatus(Enum):
    """Stato progetto compensazione"""
    REGISTERED = "registered"  # Registrato ma non ancora attivo
    ACTIVE = "active"  # Accetta compensazioni
    COMPLETED = "completed"  # Obiettivo raggiunto
    ARCHIVED = "archived"  # Non più attivo


# ============================================================================
# CRITTOGRAFIA
# ============================================================================

# Algoritmo hash primario
HASH_ALGORITHM: Final[str] = "sha256"

# Versione indirizzo (Base58Check)
ADDRESS_VERSION_MAINNET: Final[bytes] = b'\x00'
ADDRESS_VERSION_TESTNET: Final[bytes] = b'\x6f'

# Curve crittografica (ECDSA)
SIGNATURE_CURVE: Final[str] = "secp256k1"

# Tipo firma (per future upgrade post-quantum)
SIGNATURE_TYPE: Final[str] = "ecdsa"  # ecdsa | dilithium | hybrid

# Key derivation (BIP32/44)
BIP44_COIN_TYPE: Final[int] = 2025  # Registered coin type per CCO2
BIP44_PATH_MAINNET: Final[str] = "m/44'/2025'/0'/0"
BIP44_PATH_TESTNET: Final[str] = "m/44'/2025'/1'/0"

# ============================================================================
# PROOF OF WORK
# ============================================================================

# Algoritmo PoW
POW_ALGORITHM: Final[str] = "scrypt"  # ASIC-resistant

# Parametri Scrypt
SCRYPT_N: Final[int] = 2**15  # 32768 (memory cost)
SCRYPT_R: Final[int] = 8  # Block size
SCRYPT_P: Final[int] = 1  # Parallelization

# Difficulty iniziale
INITIAL_DIFFICULTY: Final[int] = 4  # 4 byte zero leading

# Difficulty minima/massima
MIN_DIFFICULTY: Final[int] = 1
MAX_DIFFICULTY: Final[int] = 32  # 256 bit zero (impossibile)

# ============================================================================
# CERTIFICATI CO2 - STANDARD
# ============================================================================

# Standard di certificazione supportati
SUPPORTED_CERT_STANDARDS: Final[list[str]] = [
    "ISO 14064-1",  # GHG quantification
    "ISO 14064-2",  # GHG projects
    "ISO 14064-3",  # GHG validation
    "GHG Protocol",  # Corporate standard
    "Gold Standard",  # Voluntary carbon market
    "VCS",  # Verified Carbon Standard
    "CDM",  # Clean Development Mechanism
    "JI",  # Joint Implementation
]

# Campi obbligatori certificato
REQUIRED_CERT_FIELDS: Final[list[str]] = [
    "certificate_id",
    "total_kg",
    "location",
    "description",
    "issuer",
    "issue_date",
]

# Campi opzionali certificato
OPTIONAL_CERT_FIELDS: Final[list[str]] = [
    "expiry_date",
    "verification_url",
    "standards",
    "project_type",
    "methodology",
    "vintage_year",
]

# ============================================================================
# PROGETTI DI COMPENSAZIONE - CATEGORIE
# ============================================================================

PROJECT_TYPES: Final[list[str]] = [
    "reforestation",  # Riforestazione
    "afforestation",  # Nuove foreste
    "renewable_energy",  # Energia rinnovabile
    "solar",  # Solare
    "wind",  # Eolico
    "hydro",  # Idroelettrico
    "biomass",  # Biomassa
    "energy_efficiency",  # Efficienza energetica
    "methane_capture",  # Cattura metano
    "soil_carbon",  # Carbonio nel suolo
    "ocean_conservation",  # Conservazione oceani
    "blue_carbon",  # Carbonio blu (mangrovie, alghe)
    "carbon_capture",  # CCS/CCUS
    "direct_air_capture",  # DAC
    "industrial_process",  # Processi industriali
    "transportation",  # Trasporti sostenibili
    "circular_economy",  # Economia circolare
]

# Campi obbligatori progetto
REQUIRED_PROJECT_FIELDS: Final[list[str]] = [
    "project_id",
    "project_name",
    "location",
    "project_type",
    "organization",
]

# ============================================================================
# NETWORKING P2P
# ============================================================================

# Default ports
DEFAULT_P2P_PORT: Final[int] = 9000
DEFAULT_RPC_PORT: Final[int] = 9001
DEFAULT_API_PORT: Final[int] = 8000

# Protocol limits
MAX_PEERS: Final[int] = 128
MAX_PEER_MESSAGE_SIZE: Final[int] = 10_000_000  # 10 MB
PEER_TIMEOUT: Final[int] = 30  # secondi
PEER_HANDSHAKE_TIMEOUT: Final[int] = 10

# Sync parameters
MAX_BLOCKS_IN_FLIGHT: Final[int] = 100
BLOCK_DOWNLOAD_TIMEOUT: Final[int] = 60

# ============================================================================
# DATABASE E STORAGE
# ============================================================================

# Default paths
DEFAULT_DATA_DIR: Final[str] = "./data"
DEFAULT_DB_NAME: Final[str] = "carbonchain.db"
DEFAULT_WALLET_DIR: Final[str] = "./wallets"

# Database limits
MAX_DB_CACHE_MB: Final[int] = 1024  # 1 GB cache
DB_BATCH_SIZE: Final[int] = 1000

# ============================================================================
# GENESIS BLOCK
# ============================================================================

# Genesis timestamp (1 Jan 2026 00:00:00 UTC)
GENESIS_TIMESTAMP: Final[int] = 1735689600

# Genesis message
GENESIS_MESSAGE: Final[str] = (
    "CarbonChain Genesis Block - "
    "1 Coin = 1 kg CO2 - "
    "Transparency for a Sustainable Future"
)

# Genesis reward (primo blocco)
GENESIS_REWARD_SATOSHI: Final[int] = INITIAL_SUBSIDY_SATOSHI

# ============================================================================
# CHECKPOINTS (Anti-reorg protection)
# ============================================================================

# Checkpoints noti (block_height: block_hash)
# Da aggiornare dopo deployment
CHECKPOINTS: Final[dict[int, str]] = {
    0: "0000000000000000000000000000000000000000000000000000000000000000",  # Genesis
    # Aggiungere checkpoints dopo deployment
}

# ============================================================================
# RATE LIMITING
# ============================================================================

# API rate limits
API_RATE_LIMIT_PER_MINUTE: Final[int] = 60
API_RATE_LIMIT_PER_HOUR: Final[int] = 1000

# Mempool limits
MEMPOOL_MAX_SIZE: Final[int] = 10_000  # tx
MEMPOOL_MAX_SIZE_MB: Final[int] = 100  # MB
MEMPOOL_EXPIRY_HOURS: Final[int] = 24

# P2P rate limits
P2P_MAX_MESSAGES_PER_SECOND: Final[int] = 100
P2P_MAX_BANDWIDTH_MBPS: Final[int] = 10

# ============================================================================
# LOGGING E DEBUG
# ============================================================================

# Log levels
LOG_LEVELS: Final[list[str]] = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

# Log categories
LOG_CATEGORIES: Final[list[str]] = [
    "blockchain",
    "mining",
    "p2p",
    "api",
    "storage",
    "validation",
    "certificates",
    "compensation",
]

# ============================================================================
# FEATURE FLAGS
# ============================================================================

class FeatureFlags(Enum):
    """Feature flags per attivare/disattivare funzionalità"""
    POST_QUANTUM_CRYPTO = False  # Abilita crypto post-quantum
    STEALTH_ADDRESSES = False  # Abilita indirizzi stealth
    SMART_CONTRACTS = False  # Abilita smart contracts (futuro)
    SHARDING = False  # Abilita sharding (futuro)
    LIGHTNING_NETWORK = False  # Abilita layer 2 (futuro)


# ============================================================================
# CODE INTEGRITY - SIGNATURES
# ============================================================================

# Hash del core codebase (calcolato al build time)
# Usato per verificare integrità files
CORE_FILES_HASH: Final[str] = ""  # Da calcolare durante build

# Public key per verifiche firma (distribuita con binario)
CORE_PUBLIC_KEY: Final[str] = ""  # Da generare al release

# ============================================================================
# HELPERS E UTILITIES
# ============================================================================

def calculate_subsidy(height: int) -> int:
    """
    Calcola subsidy per blocco dato height (con halving).
    
    Args:
        height: Altezza blocco
    
    Returns:
        int: Subsidy in Satoshi
    
    Examples:
        >>> calculate_subsidy(0)  # Genesis
        50000000
        >>> calculate_subsidy(210000)  # Primo halving
        25000000
    """
    halvings = height // HALVING_INTERVAL
    
    # Se troppi halving, subsidy = 0
    if halvings >= 64:
        return 0
    
    subsidy = INITIAL_SUBSIDY_SATOSHI >> halvings
    return subsidy


def validate_amount(amount_satoshi: int) -> bool:
    """
    Valida che amount sia nel range consentito.
    
    Args:
        amount_satoshi: Quantità in Satoshi
    
    Returns:
        bool: True se valido
    """
    return MIN_TX_OUTPUT_SATOSHI <= amount_satoshi <= MAX_TX_OUTPUT_SATOSHI


def get_protocol_info() -> dict:
    """
    Ottieni info protocollo per handshake P2P.
    
    Returns:
        dict: Info protocollo
    """
    return {
        "coin_name": COIN_NAME,
        "coin_ticker": COIN_TICKER,
        "protocol_version": PROTOCOL_VERSION,
        "software_version": SOFTWARE_VERSION,
        "network_magic": NETWORK_MAGIC.hex(),
        "max_supply": MAX_SUPPLY_SATOSHI,
        "block_time": BLOCK_TIME_TARGET,
    }


# ============================================================================
# EXPORT ALL
# ============================================================================

__all__ = [
    # Core
    "COIN_NAME",
    "COIN_TICKER",
    "COIN_SYMBOL",
    "PROTOCOL_VERSION",
    "SOFTWARE_VERSION",
    
    # Denominazioni
    "SATOSHI_PER_COIN",
    "COIN_DECIMALS",
    "coin_to_satoshi",
    "satoshi_to_coin",
    "format_amount",
    
    # Supply
    "MAX_SUPPLY_SATOSHI",
    "MAX_SUPPLY_COIN",
    "INITIAL_SUBSIDY_SATOSHI",
    "HALVING_INTERVAL",
    "calculate_subsidy",
    
    # Enums
    "TxType",
    "TxStatus",
    "CertificateState",
    "CompensationProjectStatus",
    
    # Standards
    "SUPPORTED_CERT_STANDARDS",
    "PROJECT_TYPES",
    
    # Helpers
    "validate_amount",
    "get_protocol_info",
]
