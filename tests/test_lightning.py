"""
CarbonChain - Lightning Network Tests
=======================================
Unit tests for Lightning Network layer.
"""

import pytest
import time
import hashlib
import secrets
from carbon_chain.layer2.lightning import (
    PaymentChannel,
    HTLC,
    ChannelManager,
    ChannelState,
    HTLCState
)


class TestPaymentChannel:
    """Test Payment channels"""
    
    def test_channel_creation(self):
        """Test channel creation"""
        channel = PaymentChannel.create(
            party_a="1Alice...",
            party_b="1Bob...",
            capacity=1000000
        )
        
        assert channel.party_a == "1Alice..."
        assert channel.party_b == "1Bob..."
        assert channel.capacity == 1000000
        assert channel.balance_a == 500000
        assert channel.balance_b == 500000
    
    def test_channel_transfer(self):
        """Test off-chain transfer"""
        channel = PaymentChannel.create(
            party_a="1Alice...",
            party_b="1Bob...",
            capacity=1000000
        )
        
        channel.state = ChannelState.OPEN
        
        # Alice sends to Bob
        success = channel.transfer(100000, "1Alice...")
        
        assert success
        assert channel.balance_a == 400000
        assert channel.balance_b == 600000
        assert channel.sequence == 1
    
    def test_channel_insufficient_balance(self):
        """Test transfer with insufficient balance"""
        channel = PaymentChannel.create(
            party_a="1Alice...",
            party_b="1Bob...",
            capacity=1000000
        )
        
        channel.state = ChannelState.OPEN
        
        # Try to transfer more than balance
        with pytest.raises(Exception):
            channel.transfer(600000, "1Alice...")
    
    def test_channel_bidirectional(self):
        """Test bidirectional transfers"""
        channel = PaymentChannel.create(
            party_a="1Alice...",
            party_b="1Bob...",
            capacity=1000000
        )
        
        channel.state = ChannelState.OPEN
        
        # Alice -> Bob
        channel.transfer(100000, "1Alice...")
        assert channel.balance_a == 400000
        assert channel.balance_b == 600000
        
        # Bob -> Alice
        channel.transfer(50000, "1Bob...")
        assert channel.balance_a == 450000
        assert channel.balance_b == 550000


class TestHTLC:
    """Test Hash Time-Locked Contracts"""
    
    def test_htlc_creation(self):
        """Test HTLC creation"""
        preimage = secrets.token_bytes(32)
        payment_hash = hashlib.sha256(preimage).digest()
        
        htlc = HTLC.create(
            amount=100000,
            payment_hash=payment_hash,
            expiry=int(time.time()) + 3600,
            sender="1Alice...",
            receiver="1Bob..."
        )
        
        assert htlc.amount == 100000
        assert htlc.state == HTLCState.PENDING
    
    def test_htlc_fulfill(self):
        """Test HTLC fulfillment"""
        preimage = secrets.token_bytes(32)
        payment_hash = hashlib.sha256(preimage).digest()
        
        htlc = HTLC.create(
            amount=100000,
            payment_hash=payment_hash,
            expiry=int(time.time()) + 3600,
            sender="1Alice...",
            receiver="1Bob..."
        )
        
        # Fulfill with correct preimage
        success = htlc.fulfill(preimage)
        
        assert success
        assert htlc.state == HTLCState.FULFILLED
        assert htlc.preimage == preimage
    
    def test_htlc_invalid_preimage(self):
        """Test HTLC with invalid preimage"""
        preimage = secrets.token_bytes(32)
        payment_hash = hashlib.sha256(preimage).digest()
        
        htlc = HTLC.create(
            amount=100000,
            payment_hash=payment_hash,
            expiry=int(time.time()) + 3600,
            sender="1Alice...",
            receiver="1Bob..."
        )
        
        # Try with wrong preimage
        wrong_preimage = secrets.token_bytes(32)
        
        with pytest.raises(Exception):
            htlc.fulfill(wrong_preimage)
    
    def test_htlc_expiry(self):
        """Test HTLC expiry"""
        preimage = secrets.token_bytes(32)
        payment_hash = hashlib.sha256(preimage).digest()
        
        # Already expired
        htlc = HTLC.create(
            amount=100000,
            payment_hash=payment_hash,
            expiry=int(time.time()) - 1,
            sender="1Alice...",
            receiver="1Bob..."
        )
        
        # Check expired
        is_expired = htlc.check_expired()
        assert is_expired
        assert htlc.state == HTLCState.EXPIRED


class TestChannelManager:
    """Test Channel manager"""
    
    def test_manager_open_channel(self):
        """Test opening channel through manager"""
        manager = ChannelManager()
        
        channel = manager.open_channel(
            party_a="1Alice...",
            party_b="1Bob...",
            capacity=1000000
        )
        
        assert channel is not None
        assert channel.channel_id in manager.channels
    
    def test_manager_transfer(self):
        """Test transfer through manager"""
        manager = ChannelManager()
        
        channel = manager.open_channel(
            party_a="1Alice...",
            party_b="1Bob...",
            capacity=1000000
        )
        
        channel.state = ChannelState.OPEN
        
        # Transfer
        success = manager.transfer(
            channel.channel_id,
            100000,
            "1Alice..."
        )
        
        assert success
    
    def test_manager_htlc(self):
        """Test HTLC through manager"""
        manager = ChannelManager()
        
        channel = manager.open_channel(
            party_a="1Alice...",
            party_b="1Bob...",
            capacity=1000000
        )
        
        preimage = secrets.token_bytes(32)
        payment_hash = hashlib.sha256(preimage).digest()
        
        # Create HTLC
        htlc = manager.create_htlc(
            channel_id=channel.channel_id,
            amount=100000,
            payment_hash=payment_hash,
            expiry=int(time.time()) + 3600,
            sender="1Alice...",
            receiver="1Bob..."
        )
        
        assert htlc is not None
        assert htlc.htlc_id in manager.htlcs
        
        # Fulfill HTLC
        success = manager.fulfill_htlc(htlc.htlc_id, preimage)
        assert success
    
    def test_manager_statistics(self):
        """Test manager statistics"""
        manager = ChannelManager()
        
        # Open some channels
        manager.open_channel("1Alice...", "1Bob...", 1000000)
        manager.open_channel("1Carol...", "1Dave...", 2000000)
        
        stats = manager.get_statistics()
        
        assert stats["total_channels"] == 2
        assert stats["total_capacity"] == 3000000
