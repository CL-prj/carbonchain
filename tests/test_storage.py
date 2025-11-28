"""
CarbonChain - Storage Tests
=============================
Unit tests for database storage.
"""

import pytest
from carbon_chain.storage.db import BlockchainDatabase


class TestBlockchainDatabase:
    """Test BlockchainDatabase class"""
    
    def test_database_initialization(self, test_database):
        """Test database initializes correctly"""
        assert test_database is not None
        assert test_database.get_block_count() == 0
    
    def test_save_and_load_block(self, test_database, blockchain):
        """Test saving and loading blocks"""
        # Get genesis block
        genesis = blockchain.get_block(0)
        
        # Save to database
        test_database.save_block(genesis)
        
        # Load from database
        loaded = test_database.load_block(0)
        
        assert loaded is not None
        assert loaded.compute_block_hash() == genesis.compute_block_hash()
    
    def test_utxo_persistence(self, test_database, blockchain, wallet):
        """Test UTXO persistence"""
        # Mine block
        miner_address = wallet.get_address(0)
        block = blockchain.mine_block(
            miner_address=miner_address,
            transactions=[],
            timeout_seconds=30
        )
        
        if block:
            blockchain.add_block(block)
            
            # Save to database
            test_database.save_block(block)
            
            # Load UTXOs
            utxos = test_database.load_utxos()
            
            assert len(utxos) > 0
