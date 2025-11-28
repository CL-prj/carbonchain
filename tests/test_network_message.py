"""
CarbonChain - Network Message Tests
=====================================
Unit tests for P2P message protocol.
"""

import pytest
from carbon_chain.network.message import (
    Message,
    MessageType,
    MessageFactory,
    VersionMessage,
    PingMessage,
    InvMessage,
    InventoryType,
)
from carbon_chain.errors import InvalidMessageError


class TestMessage:
    """Test Message protocol"""
    
    def test_message_serialization(self):
        """Test message serialize/deserialize"""
        msg = Message(
            message_type=MessageType.PING,
            payload=b'test_payload'
        )
        
        # Serialize
        data = msg.serialize()
        
        assert len(data) >= Message.HEADER_SIZE
        
        # Deserialize
        msg2 = Message.deserialize(data)
        
        assert msg.message_type == msg2.message_type
        assert msg.payload == msg2.payload
    
    def test_ping_message(self):
        """Test PING message creation"""
        nonce = 123456789
        ping_msg = MessageFactory.create_ping(nonce)
        
        assert ping_msg.message_type == MessageType.PING
        
        # Deserialize payload
        ping = PingMessage.deserialize(ping_msg.payload)
        assert ping.nonce == nonce
    
    def test_version_message(self):
        """Test VERSION message"""
        version_msg = MessageFactory.create_version(
            version=1,
            services=0,
            addr_recv="192.168.1.1:9333",
            addr_from="192.168.1.2:9333",
            nonce=123,
            user_agent="Test/1.0",
            start_height=100
        )
        
        assert version_msg.message_type == MessageType.VERSION
        
        # Deserialize
        version = VersionMessage.deserialize(version_msg.payload)
        assert version.version == 1
        assert version.start_height == 100
    
    def test_inv_message(self):
        """Test INV message"""
        inventory = [
            (InventoryType.MSG_BLOCK, "abcd" * 16),
            (InventoryType.MSG_TX, "1234" * 16)
        ]
        
        inv_msg = MessageFactory.create_inv(inventory)
        
        assert inv_msg.message_type == MessageType.INV
        
        # Deserialize
        inv = InvMessage.deserialize(inv_msg.payload)
        assert len(inv.inventory) == 2
    
    def test_invalid_message(self):
        """Test invalid message rejection"""
        with pytest.raises(InvalidMessageError):
            Message.deserialize(b'invalid_data')
