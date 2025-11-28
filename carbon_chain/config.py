"""
CarbonChain - Configuration Management
=======================================
Gestione centralizzata configurazione con Pydantic Settings.
Supporta environment variables, file .env, override runtime.

Security Level: HIGH
Last Updated: 2025-11-27
Version: 1.0.0

Features:
- Validazione automatica tipi
- Environment variables con prefisso CARBONCHAIN_
- File .env support
- Profile multipli (dev/test/prod)
- Secrets management
"""

import os
from pathlib import Path
from typing import Optional, List
from functools import lru_cache

from pydantic import Field, field_validator, ConfigDict
from pydantic_settings import BaseSettings, SettingsConfigDict

from carbon_chain.constants import (
    DEFAULT_P2P_PORT,
    DEFAULT_API_PORT,
    INITIAL_DIFFICULTY,
    INITIAL_SUBSIDY_SATOSHI,
    HALVING_INTERVAL,
    MAX_SUPPLY_SATOSHI,
    BLOCK_TIME_TARGET,
    GENESIS_TIMESTAMP,
    ADDRESS_VERSION_MAINNET,
    BIP44_PATH_MAINNET,
)


# ============================================================================
# MAIN CONFIGURATION CLASS
# ============================================================================

class ChainSettings(BaseSettings):
    """
    Configurazione principale CarbonChain.
    
    Supporta:
    - Caricamento da environment variables (CARBONCHAIN_*)
    - Caricamento da file .env
    - Override programmatici
    - Validazione automatica
    
    Example:
        # Da environment
        export CARBONCHAIN_NODE_NAME="MainNode"
        export CARBONCHAIN_P2P_PORT=9001
        
        # Da codice
        config = ChainSettings(node_name="TestNode")
        
        # Da .env file
        config = ChainSettings(_env_file=".env")
    """
    
    model_config = SettingsConfigDict(
        env_prefix='CARBONCHAIN_',
        env_file='.env',
        env_file_encoding='utf-8',
        case_sensitive=False,
        extra='ignore',  # Ignora variabili extra
    )
    
    # ========================================================================
    # NODE IDENTIFICATION
    # ========================================================================
    
    node_name: str = Field(
        default="CarbonChain-Node",
        description="Nome identificativo nodo"
    )
    
    node_id: Optional[str] = Field(
        default=None,
        description="UUID nodo (auto-generato se None)"
    )
    
    software_version: str = Field(
        default="1.0.0",
        description="Versione software"
    )
    
    # ========================================================================
    # NETWORK SETTINGS
    # ========================================================================
    
    network: str = Field(
        default="mainnet",
        description="Network type: mainnet, testnet, regtest"
    )
    
    p2p_port: int = Field(
        default=DEFAULT_P2P_PORT,
        ge=1024,
        le=65535,
        description="Porta P2P per peer connections"
    )
    
    api_port: int = Field(
        default=DEFAULT_API_PORT,
        ge=1024,
        le=65535,
        description="Porta API REST"
    )
    
    p2p_host: str = Field(
        default="0.0.0.0",
        description="Host P2P (0.0.0.0 = tutte interfacce)"
    )
    
    api_host: str = Field(
        default="0.0.0.0",
        description="Host API"
    )
    
    # ========================================================================
    # P2P NETWORKING (Phase 2)
    # ========================================================================
    
    # Max peer connections
    p2p_max_peers: int = Field(
        default=128,
        ge=1,
        le=1000,
        description="Numero massimo peer connessi"
    )
    
    # Max outbound connections
    p2p_max_outbound: int = Field(
        default=8,
        ge=1,
        le=100,
        description="Numero massimo connessioni outbound"
    )
    
    # Bootstrap nodes
    p2p_bootnodes: List[str] = Field(
        default_factory=list,
        description="Lista bootstrap nodes (host:port)"
    )
    
    # UPnP
    p2p_enable_upnp: bool = Field(
        default=True,
        description="Abilita UPnP per NAT traversal"
    )
    
    # External IP (auto-detect if empty)
    p2p_external_ip: Optional[str] = Field(
        default=None,
        description="IP pubblico (auto-detect se None)"
    )
    
    # Connection timeout
    p2p_connection_timeout: int = Field(
        default=30,
        ge=5,
        le=300,
        description="Timeout connessione P2P (secondi)"
    )
    
    # Keep-alive interval
    p2p_keepalive_interval: int = Field(
        default=60,
        ge=10,
        le=600,
        description="Intervallo PING keep-alive (secondi)"
    )
    
    # Peer timeout
    p2p_peer_timeout: int = Field(
        default=300,
        ge=60,
        le=3600,
        description="Timeout inattività peer (secondi)"
    )
    
    # ========================================================================
    # BLOCKCHAIN SYNCHRONIZATION (Phase 2)
    # ========================================================================
    
    # Sync batch size
    sync_batch_size: int = Field(
        default=500,
        ge=10,
        le=5000,
        description="Blocchi per sync batch"
    )
    
    # Max blocks in flight
    sync_max_blocks_in_flight: int = Field(
        default=100,
        ge=10,
        le=1000,
        description="Max blocchi in download simultaneo"
    )
    
    # Sync timeout
    sync_timeout_seconds: int = Field(
        default=60,
        ge=10,
        le=600,
        description="Timeout download blocco (secondi)"
    )
    
    # Auto-sync on startup
    sync_on_startup: bool = Field(
        default=True,
        description="Sincronizza automaticamente all'avvio"
    )
    
    # ========================================================================
    # BLOCKCHAIN PARAMETERS
    # ========================================================================
    
    pow_difficulty_initial: int = Field(
        default=INITIAL_DIFFICULTY,
        ge=1,
        le=32,
        description="Difficulty iniziale (leading zero bytes)"
    )
    
    pow_algorithm: str = Field(
        default="scrypt",
        description="Algoritmo PoW: scrypt, argon2id"
    )
    
    block_time_target: int = Field(
        default=BLOCK_TIME_TARGET,
        ge=60,
        le=3600,
        description="Target block time (secondi)"
    )
    
    difficulty_adjustment_interval: int = Field(
        default=2016,
        ge=1,
        description="Blocchi tra adjustment difficulty"
    )
    
    # ========================================================================
    # ECONOMICS
    # ========================================================================
    
    max_supply: int = Field(
        default=MAX_SUPPLY_SATOSHI,
        description="Supply massima (Satoshi)"
    )
    
    initial_subsidy: int = Field(
        default=INITIAL_SUBSIDY_SATOSHI,
        description="Subsidy iniziale per blocco (Satoshi)"
    )
    
    halving_interval: int = Field(
        default=HALVING_INTERVAL,
        ge=1,
        description="Blocchi tra halving"
    )
    
    genesis_timestamp: int = Field(
        default=GENESIS_TIMESTAMP,
        description="Timestamp genesis block"
    )
    
    genesis_address: Optional[str] = Field(
        default=None,
        description="Address per genesis reward (creator)"
    )
    
    # ========================================================================
    # MINING
    # ========================================================================
    
    mining_enabled: bool = Field(
        default=False,
        description="Abilita mining su questo nodo"
    )
    
    mining_threads: int = Field(
        default=1,
        ge=1,
        le=128,
        description="Thread per mining"
    )
    
    miner_address: Optional[str] = Field(
        default=None,
        description="Address per mining rewards"
    )
    
    mining_max_nonce: int = Field(
        default=2**32,
        description="Max nonce per tentativo mining"
    )
    
    # ========================================================================
    # STORAGE
    # ========================================================================
    
    data_dir: Path = Field(
        default=Path("./data"),
        description="Directory dati blockchain"
    )
    
    db_path: Optional[Path] = Field(
        default=None,
        description="Path database (auto: data_dir/carbonchain.db)"
    )
    
    wallet_dir: Path = Field(
        default=Path("./wallets"),
        description="Directory wallet"
    )
    
    db_cache_mb: int = Field(
        default=512,
        ge=64,
        le=8192,
        description="Cache size database (MB)"
    )
    
    enable_pruning: bool = Field(
        default=False,
        description="Abilita pruning vecchi blocchi"
    )
    
    pruning_keep_blocks: int = Field(
        default=100000,
        description="Blocchi da mantenere se pruning attivo"
    )
    
    # ========================================================================
    # MEMPOOL
    # ========================================================================
    
    mempool_max_size: int = Field(
        default=10000,
        ge=100,
        description="Max transazioni in mempool"
    )
    
    mempool_max_size_mb: int = Field(
        default=100,
        ge=10,
        description="Max dimensione mempool (MB)"
    )
    
    mempool_expiry_hours: int = Field(
        default=24,
        ge=1,
        description="Ore prima expiry tx in mempool"
    )
    
    # ========================================================================
    # VALIDATION & SECURITY
    # ========================================================================
    
    enforce_cert_uniqueness: bool = Field(
        default=True,
        description="Forza unicità certificate_hash"
    )
    
    forbid_spending_compensated: bool = Field(
        default=True,
        description="Impedisci spesa coin compensate"
    )
    
    block_validation_strict: bool = Field(
        default=True,
        description="Validazione blocchi strict mode"
    )
    
    verify_signatures: bool = Field(
        default=True,
        description="Verifica firme transazioni"
    )
    
    max_block_size: int = Field(
        default=4_000_000,
        ge=1_000_000,
        description="Dimensione massima blocco (bytes)"
    )
    
    max_tx_size: int = Field(
        default=1_000_000,
        ge=10_000,
        description="Dimensione massima transazione (bytes)"
    )
    
    # ========================================================================
    # CRYPTOGRAPHY
    # ========================================================================
    
    post_quantum_enabled: bool = Field(
        default=False,
        description="Abilita crittografia post-quantum"
    )
    
    crypto_algorithm: str = Field(
        default="ecdsa",
        description="Algoritmo crypto: ecdsa, dilithium, hybrid"
    )
    
    enable_stealth_addresses: bool = Field(
        default=False,
        description="Abilita stealth addresses"
    )
    
    # ========================================================================
    # API & EXPLORER
    # ========================================================================
    
    enable_api: bool = Field(
        default=True,
        description="Abilita API REST"
    )
    
    enable_explorer: bool = Field(
        default=True,
        description="Abilita web explorer"
    )
    
    explorer_port: int = Field(
        default=8080,
        ge=1024,
        le=65535,
        description="Porta web explorer"
    )
    
    api_rate_limit_per_minute: int = Field(
        default=60,
        ge=1,
        description="Rate limit API (requests/minute)"
    )
    
    api_enable_cors: bool = Field(
        default=True,
        description="Abilita CORS per API"
    )
    
    api_cors_origins: List[str] = Field(
        default_factory=lambda: ["*"],
        description="CORS allowed origins"
    )
    
    # ========================================================================
    # LOGGING
    # ========================================================================
    
    log_level: str = Field(
        default="INFO",
        description="Log level: DEBUG, INFO, WARNING, ERROR, CRITICAL"
    )
    
    log_to_file: bool = Field(
        default=True,
        description="Salva log su file"
    )
    
    log_dir: Path = Field(
        default=Path("./logs"),
        description="Directory log files"
    )
    
    log_format: str = Field(
        default="json",
        description="Formato log: json, text"
    )
    
    log_rotation_mb: int = Field(
        default=100,
        ge=1,
        description="Dimensione max file log prima rotation (MB)"
    )
    
    log_retention_days: int = Field(
        default=30,
        ge=1,
        description="Giorni retention log files"
    )
    
    # ========================================================================
    # DEVELOPMENT & DEBUG
    # ========================================================================
    
    dev_mode: bool = Field(
        default=False,
        description="Modalità sviluppo (disabilita security checks)"
    )
    
    testnet: bool = Field(
        default=False,
        description="Usa testnet invece di mainnet"
    )
    
    regtest: bool = Field(
        default=False,
        description="Regression test mode (mining istantaneo)"
    )
    
    enable_debug_api: bool = Field(
        default=False,
        description="Abilita endpoint API debug"
    )
    
    enable_profiling: bool = Field(
        default=False,
        description="Abilita profiling performance"
    )
    
    # ========================================================================
    # ADVANCED (Experimental)
    # ========================================================================
    
    enable_sharding: bool = Field(
        default=False,
        description="Abilita sharding (experimental)"
    )
    
    enable_lightning: bool = Field(
        default=False,
        description="Abilita Lightning Network layer (future)"
    )
    
    checkpoint_interval: int = Field(
        default=10000,
        ge=100,
        description="Blocchi tra checkpoints automatici"
    )
    
    # ========================================================================
    # VALIDATORS
    # ========================================================================
    
    @field_validator('log_level')
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Valida log level"""
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        v_upper = v.upper()
        if v_upper not in valid_levels:
            raise ValueError(f"Invalid log_level: {v}. Must be one of {valid_levels}")
        return v_upper
    
    @field_validator('pow_algorithm')
    @classmethod
    def validate_pow_algorithm(cls, v: str) -> str:
        """Valida algoritmo PoW"""
        valid_algos = ['scrypt', 'argon2id']
        v_lower = v.lower()
        if v_lower not in valid_algos:
            raise ValueError(f"Invalid pow_algorithm: {v}. Must be one of {valid_algos}")
        return v_lower
    
    @field_validator('crypto_algorithm')
    @classmethod
    def validate_crypto_algorithm(cls, v: str) -> str:
        """Valida algoritmo crypto"""
        valid_algos = ['ecdsa', 'dilithium', 'hybrid']
        v_lower = v.lower()
        if v_lower not in valid_algos:
            raise ValueError(f"Invalid crypto_algorithm: {v}. Must be one of {valid_algos}")
        return v_lower
    
    @field_validator('network')
    @classmethod
    def validate_network(cls, v: str) -> str:
        """Valida network type"""
        valid_networks = ['mainnet', 'testnet', 'regtest']
        v_lower = v.lower()
        if v_lower not in valid_networks:
            raise ValueError(f"Invalid network: {v}. Must be one of {valid_networks}")
        return v_lower
    
    @field_validator('p2p_bootnodes')
    @classmethod
    def validate_bootnodes(cls, v: List[str]) -> List[str]:
        """Valida formato bootnodes"""
        validated = []
        for node in v:
            if ':' not in node:
                raise ValueError(f"Invalid bootnode format: {node}. Expected host:port")
            
            host, port_str = node.rsplit(':', 1)
            try:
                port = int(port_str)
                if not (1 <= port <= 65535):
                    raise ValueError(f"Invalid port: {port}")
            except ValueError:
                raise ValueError(f"Invalid bootnode port: {port_str}")
            
            validated.append(f"{host}:{port}")
        
        return validated
    
    # ========================================================================
    # POST-INIT PROCESSING
    # ========================================================================
    
    def model_post_init(self, __context) -> None:
        """Post-initialization: setup paths, generate IDs"""
        
        # Auto-generate node_id se None
        if self.node_id is None:
            import uuid
            self.node_id = str(uuid.uuid4())
        
        # Setup db_path se None
        if self.db_path is None:
            self.db_path = self.data_dir / "carbonchain.db"
        
        # Crea directories se non esistono
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.wallet_dir.mkdir(parents=True, exist_ok=True)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Testnet/regtest adjustments
        if self.testnet:
            self.network = "testnet"
            if self.genesis_address is None:
                self.genesis_address = "testnet_genesis_address"
        
        if self.regtest:
            self.network = "regtest"
            self.pow_difficulty_initial = 1  # Mining facile
            self.block_time_target = 1  # 1 secondo
    
    # ========================================================================
    # HELPER METHODS
    # ========================================================================
    
    def is_mainnet(self) -> bool:
        """Check se mainnet"""
        return self.network == "mainnet"
    
    def is_testnet(self) -> bool:
        """Check se testnet"""
        return self.network == "testnet"
    
    def is_regtest(self) -> bool:
        """Check se regtest"""
        return self.network == "regtest"
    
    def get_address_version(self) -> bytes:
        """Ottieni address version per network"""
        if self.is_mainnet():
            return ADDRESS_VERSION_MAINNET
        else:
            return b'\x6f'  # Testnet version
    
    def get_bip44_path(self, account: int = 0) -> str:
        """Ottieni BIP44 path per network"""
        coin_type = 2025 if self.is_mainnet() else 1  # testnet = 1
        return f"m/44'/{coin_type}'/{account}'/0"
    
    def to_dict(self) -> dict:
        """Serializza config"""
        return self.model_dump()
    
    def to_json(self) -> str:
        """Serializza config in JSON"""
        return self.model_dump_json(indent=2)
    
    @classmethod
    def from_json(cls, json_str: str) -> "ChainSettings":
        """Carica config da JSON"""
        return cls.model_validate_json(json_str)
    
    @classmethod
    def from_file(cls, path: Path) -> "ChainSettings":
        """Carica config da file JSON"""
        return cls.model_validate_json(path.read_text())
    
    def save_to_file(self, path: Path) -> None:
        """Salva config su file"""
        path.write_text(self.to_json())
    
    def __repr__(self) -> str:
        return (
            f"ChainSettings("
            f"node_name={self.node_name}, "
            f"network={self.network}, "
            f"p2p_port={self.p2p_port}, "
            f"mining_enabled={self.mining_enabled})"
        )


# ============================================================================
# SINGLETON INSTANCE
# ============================================================================

# Global config instance (lazy-loaded)
_config_instance: Optional[ChainSettings] = None


@lru_cache(maxsize=1)
def get_settings() -> ChainSettings:
    """
    Ottieni singleton instance di ChainSettings.
    
    Cached per performance (chiamate multiple restituiscono stessa istanza).
    
    Returns:
        ChainSettings: Instance configurazione
    
    Example:
        >>> config = get_settings()
        >>> config.node_name
        'CarbonChain-Node'
    """
    global _config_instance
    
    if _config_instance is None:
        _config_instance = ChainSettings()
    
    return _config_instance


def reload_settings() -> ChainSettings:
    """
    Ricarica settings (invalida cache).
    
    Usare quando si cambiano environment variables runtime.
    
    Returns:
        ChainSettings: Nuova instance
    """
    global _config_instance
    
    # Clear cache
    get_settings.cache_clear()
    
    # Ricrea instance
    _config_instance = ChainSettings()
    
    return _config_instance


def override_settings(**kwargs) -> ChainSettings:
    """
    Override settings con valori custom.
    
    Utile per testing.
    
    Args:
        **kwargs: Parametri da override
    
    Returns:
        ChainSettings: Instance con override
    
    Example:
        >>> test_config = override_settings(
        ...     dev_mode=True,
        ...     mining_enabled=True
        ... )
    """
    return ChainSettings(**kwargs)


# ============================================================================
# PROFILE PRESETS
# ============================================================================

def get_development_config() -> ChainSettings:
    """
    Config preset per development.
    
    Features:
    - Dev mode enabled
    - Mining facile (difficulty 1)
    - Log DEBUG
    - API debug enabled
    """
    return ChainSettings(
        dev_mode=True,
        network="regtest",
        pow_difficulty_initial=1,
        block_time_target=1,
        log_level="DEBUG",
        enable_debug_api=True,
        mining_enabled=True,
        p2p_max_peers=10,
    )


def get_testnet_config() -> ChainSettings:
    """
    Config preset per testnet.
    
    Features:
    - Testnet network
    - Parametri realistici ma facilitati
    - Log INFO
    """
    return ChainSettings(
        network="testnet",
        testnet=True,
        pow_difficulty_initial=2,
        log_level="INFO",
    )


def get_production_config() -> ChainSettings:
    """
    Config preset per production (mainnet).
    
    Features:
    - Mainnet network
    - Security strict
    - Log WARNING
    - Tutti i controlli abilitati
    """
    return ChainSettings(
        network="mainnet",
        dev_mode=False,
        block_validation_strict=True,
        verify_signatures=True,
        enforce_cert_uniqueness=True,
        forbid_spending_compensated=True,
        log_level="WARNING",
        enable_debug_api=False,
    )


# ============================================================================
# CONFIGURATION VALIDATION
# ============================================================================

def validate_config(config: ChainSettings) -> tuple[bool, list[str]]:
    """
    Valida configurazione completa.
    
    Args:
        config: ChainSettings da validare
    
    Returns:
        tuple: (is_valid, errors_list)
    
    Example:
        >>> config = get_settings()
        >>> is_valid, errors = validate_config(config)
        >>> if not is_valid:
        ...     print(f"Config errors: {errors}")
    """
    errors = []
    
    # Check mining configuration
    if config.mining_enabled and not config.miner_address:
        errors.append("mining_enabled=True requires miner_address")
    
    # Check ports conflicts
    if config.p2p_port == config.api_port:
        errors.append("p2p_port and api_port cannot be the same")
    
    if config.api_port == config.explorer_port:
        errors.append("api_port and explorer_port cannot be the same")
    
    # Check directories writable
    for dir_path in [config.data_dir, config.wallet_dir, config.log_dir]:
        if not os.access(dir_path, os.W_OK):
            errors.append(f"Directory not writable: {dir_path}")
    
    # Check bootnodes reachable (warning only)
    if not config.p2p_bootnodes and config.network == "mainnet":
        errors.append("WARNING: No bootnodes configured for mainnet")
    
    # Check genesis address for mainnet
    if config.network == "mainnet" and not config.genesis_address:
        errors.append("genesis_address required for mainnet")
    
    # Check post-quantum crypto availability
    if config.post_quantum_enabled:
        try:
            import oqs
        except ImportError:
            errors.append("post_quantum_enabled=True requires liboqs-python")
    
    return (len(errors) == 0, errors)


# ============================================================================
# EXPORT
# ============================================================================

__all__ = [
    "ChainSettings",
    "get_settings",
    "reload_settings",
    "override_settings",
    "get_development_config",
    "get_testnet_config",
    "get_production_config",
    "validate_config",
]
