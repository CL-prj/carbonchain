"""
CarbonChain - Transaction Tests
=================================
Unit tests for transaction functionality.
"""

import pytest
from carbon_chain.domain.models import Transaction, TxInput, TxOutput
from carbon_chain.constants import TxType
from carbon_chain.errors import ValidationError
import time


class TestTransaction:
    """Test Transaction class"""
    
    def test_coinbase_creation(self):
        """Test COINBASE transaction creation"""
        tx = Transaction(
            tx_type=TxType.COINBASE,
            inputs=[],
            outputs=[TxOutput(amount=50000000, address="1TestAddr")],
            timestamp=int(time.time())
        )
        
        assert tx.is_coinbase()
        assert len(tx.inputs) == 0
        assert len(tx.outputs) == 1
    
    def test_transfer_creation(self):
        """Test TRANSFER transaction creation"""
        tx = Transaction(
            tx_type=TxType.TRANSFER,
            inputs=[TxInput("prev_txid", 0)],
            outputs=[TxOutput(amount=100, address="1RecipientAddr")],
            timestamp=int(time.time())
        )
        
        assert tx.is_transfer()
        assert len(tx.inputs) == 1
        assert len(tx.outputs) == 1
    
    def test_txid_computation(self):
        """Test transaction ID computation"""
        tx = Transaction(
            tx_type=TxType.TRANSFER,
            inputs=[TxInput("prev_txid", 0)],
            outputs=[TxOutput(amount=100, address="1Addr")],
            timestamp=1700000000
        )
        
        txid1 = tx.compute_txid()
        txid2 = tx.compute_txid()
        
        # Deterministic
        assert txid1 == txid2
        assert len(txid1) == 64  # SHA256 hex
    
    def test_transaction_serialization(self):
        """Test transaction serialization/deserialization"""
        tx = Transaction(
            tx_type=TxType.TRANSFER,
            inputs=[TxInput("prev_txid", 0)],
            outputs=[TxOutput(amount=100, address="1Addr")],
            timestamp=1700000000
        )
        
        # Serialize
        data = tx.to_dict()
        
        # Deserialize
        tx2 = Transaction.from_dict(data)
        
        assert tx.compute_txid() == tx2.compute_txid()
