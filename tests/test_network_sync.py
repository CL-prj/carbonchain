"""
CarbonChain - Sync Tests
=========================
Unit tests for blockchain synchronization.
"""

import pytest
from carbon_chain.network.sync import BlockchainSynchronizer, SyncState


class TestSyncState:
    """Test SyncState class"""
    
    def test_sync_state_creation(self):
        """Test sync state initialization"""
        state = SyncState()
        
        assert not state.is_syncing
        assert state.start_height == 0
        assert state.current_height == 0
        assert state.target_height == 0
    
    def test_progress_calculation(self):
        """Test progress percentage calculation"""
        state = SyncState(
            start_height=0,
            current_height=50,
            target_height=100
        )
        
        progress = state.get_progress_percentage()
        assert progress == 50.0
    
    def test_download_rate(self):
        """Test download rate calculation"""
        import time
        
        state = SyncState(
            blocks_downloaded=100,
            sync_start_time=time.time() - 10  # 10 seconds ago
        )
        
        rate = state.get_download_rate()
        assert rate > 0


class TestBlockchainSynchronizer:
    """Test BlockchainSynchronizer"""
    
    def test_synchronizer_creation(self, blockchain):
        """Test synchronizer initialization"""
        sync = BlockchainSynchronizer(blockchain)
        
        assert sync.blockchain == blockchain
        assert not sync.state.is_syncing
    
    def test_block_locator_creation(self, blockchain):
        """Test block locator creation"""
        sync = BlockchainSynchronizer(blockchain)
        
        locator = sync._create_block_locator()
        
        assert len(locator) > 0
        assert locator[-1] == blockchain.get_block(0).compute_block_hash()
    
    def test_sync_state_tracking(self, blockchain):
        """Test sync state tracking"""
        sync = BlockchainSynchronizer(blockchain)
        
        state = sync.get_sync_state()
        
        assert "is_syncing" in state
        assert "current_height" in state
        assert "progress_pct" in state
