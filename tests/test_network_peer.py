"""
CarbonChain - Peer Tests
==========================
Unit tests for peer connections.
"""

import pytest
import asyncio
from carbon_chain.network.peer import Peer, PeerState, PeerInfo


class TestPeer:
    """Test Peer class"""
    
    def test_peer_creation(self):
        """Test peer instance creation"""
        peer = Peer("192.168.1.100", 9333)
        
        assert peer.info.address == "192.168.1.100"
        assert peer.info.port == 9333
        assert peer.state == PeerState.DISCONNECTED
    
    def test_peer_info_serialization(self):
        """Test PeerInfo serialization"""
        info = PeerInfo(
            address="192.168.1.100",
            port=9333,
            version=1,
            user_agent="Test/1.0",
            start_height=100
        )
        
        # Serialize
        data = info.to_dict()
        
        # Deserialize
        info2 = PeerInfo.from_dict(data)
        
        assert info.address == info2.address
        assert info.port == info2.port
        assert info.start_height == info2.start_height
    
    @pytest.mark.asyncio
    async def test_peer_connection_states(self):
        """Test peer state transitions"""
        peer = Peer("127.0.0.1", 9333)
        
        assert peer.state == PeerState.DISCONNECTED
        assert not peer.is_connected()
        assert not peer.is_ready()
    
    def test_peer_statistics(self):
        """Test peer statistics"""
        peer = Peer("192.168.1.100", 9333)
        
        stats = peer.get_statistics()
        
        assert "address" in stats
        assert "state" in stats
        assert "bytes_sent" in stats
        assert "bytes_received" in stats
