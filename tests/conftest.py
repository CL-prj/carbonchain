"""
CarbonChain - Pytest Configuration
====================================
Fixtures e configurazione per testing.

Last Updated: 2025-11-27
Version: 1.0.0
"""

import pytest
from pathlib import Path
import tempfile
import shutil

# Internal imports
from carbon_chain.config import ChainSettings
from carbon_chain.domain.blockchain import Blockchain
from carbon_chain.domain.mempool import Mempool
from carbon_chain.wallet.hd_wallet import HDWallet
from carbon_chain.storage.db import BlockchainDatabase


# ============================================================================
# CONFIGURATION FIXTURES
# ============================================================================

@pytest.fixture
def test_config():
    """Test configuration"""
    config = ChainSettings()
    config.network = "regtest"
    config.pow_difficulty_initial = 1  # Easy mining per test
    config.dev_mode = True
    config.verify_signatures = False  # Speed up tests
    return config


@pytest.fixture
def temp_data_dir():
    """Temporary data directory"""
    temp_dir = Path(tempfile.mkdtemp())
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


# ============================================================================
# DATABASE FIXTURES
# ============================================================================

@pytest.fixture
def test_database(test_config, temp_data_dir):
    """Test database"""
    db_path = temp_data_dir / "test.db"
    db = BlockchainDatabase(db_path, test_config)
    yield db
    db.close()


# ============================================================================
# BLOCKCHAIN FIXTURES
# ============================================================================

@pytest.fixture
def blockchain(test_config, test_database):
    """Blockchain instance per test"""
    return Blockchain(test_config, storage=test_database)


@pytest.fixture
def mempool(test_config):
    """Mempool instance per test"""
    return Mempool(max_size_mb=10, max_count=100, expiry_hours=1)


# ============================================================================
# WALLET FIXTURES
# ============================================================================

@pytest.fixture
def wallet(test_config):
    """HD Wallet per test"""
    return HDWallet.create_new(strength=128, config=test_config)


@pytest.fixture
def funded_wallet(blockchain, wallet):
    """Wallet con fondi (dopo mining)"""
    # Mine blocco per funding
    miner_address = wallet.get_address(0)
    block = blockchain.mine_block(
        miner_address=miner_address,
        transactions=[],
        timeout_seconds=30
    )
    
    if block:
        blockchain.add_block(block)
    
    return wallet


# ============================================================================
# HELPER FIXTURES
# ============================================================================

@pytest.fixture
def sample_certificate_data():
    """Sample certificate data per test"""
    import time
    return {
        "certificate_id": "TEST-CERT-001",
        "total_kg": 10000,
        "location": "Test Location",
        "description": "Test certificate for unit testing",
        "issuer": "Test Issuer",
        "issue_date": int(time.time())
    }


@pytest.fixture
def sample_project_data():
    """Sample project data per test"""
    return {
        "project_id": "TEST-PROJ-001",
        "project_name": "Test Reforestation Project",
        "location": "Test Forest",
        "project_type": "reforestation",
        "organization": "Test Organization"
    }
