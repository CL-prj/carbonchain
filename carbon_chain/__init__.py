"""
CarbonChain - CO2 Compensation Blockchain
===========================================
Blockchain per tracciabilità e compensazione CO2.

Version: 1.0.0
Author: CarbonChain Team
License: MIT
"""

__version__ = "1.0.0"
__author__ = "CarbonChain Team"
__license__ = "MIT"

# Core imports
from carbon_chain.domain.blockchain import Blockchain
from carbon_chain.domain.mempool import Mempool
from carbon_chain.wallet.hd_wallet import HDWallet
from carbon_chain.config import ChainSettings, get_settings

# Services
from carbon_chain.services.wallet_service import WalletService
from carbon_chain.services.certificate_service import CertificateService
from carbon_chain.services.compensation_service import CompensationService
from carbon_chain.services.mining_service import MiningService

# Constants
from carbon_chain.constants import (
    TxType,
    satoshi_to_coin,
    coin_to_satoshi,
)

__all__ = [
    # Version
    "__version__",
    
    # Core
    "Blockchain",
    "Mempool",
    "HDWallet",
    "ChainSettings",
    "get_settings",
    
    # Services
    "WalletService",
    "CertificateService",
    "CompensationService",
    "MiningService",
    
    # Constants
    "TxType",
    "satoshi_to_coin",
    "coin_to_satoshi",
]
