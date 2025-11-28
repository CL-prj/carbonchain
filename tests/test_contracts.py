"""
CarbonChain - Smart Contracts Tests
=====================================
Unit tests for smart contracts.
"""

import pytest
import time
from carbon_chain.contracts.simple_contract import (
    TimelockContract,
    ConditionalContract,
    EscrowContract,
    ContractExecutor,
    ContractStatus
)


class TestTimelockContract:
    """Test Timelock contracts"""
    
    def test_timelock_creation(self):
        """Test timelock contract creation"""
        unlock_time = int(time.time()) + 3600  # 1 hour from now
        
        contract = TimelockContract(
            contract_id="LOCK001",
            creator="1Creator...",
            conditions={
                "unlock_time": unlock_time,
                "recipient": "1Recipient...",
                "amount": 1000000
            }
        )
        
        assert contract.contract_id == "LOCK001"
        assert contract.status == ContractStatus.PENDING
    
    def test_timelock_not_unlocked(self):
        """Test timelock before unlock time"""
        unlock_time = int(time.time()) + 3600
        
        contract = TimelockContract(
            contract_id="LOCK002",
            creator="1Creator...",
            conditions={
                "unlock_time": unlock_time,
                "recipient": "1Recipient...",
                "amount": 1000000
            }
        )
        
        context = {"current_time": int(time.time())}
        
        # Should not be unlocked yet
        assert not contract.check_conditions(context)
    
    def test_timelock_unlocked(self):
        """Test timelock after unlock time"""
        unlock_time = int(time.time()) - 3600  # 1 hour ago
        
        contract = TimelockContract(
            contract_id="LOCK003",
            creator="1Creator...",
            conditions={
                "unlock_time": unlock_time,
                "recipient": "1Recipient...",
                "amount": 1000000
            }
        )
        
        context = {"current_time": int(time.time())}
        
        # Should be unlocked
        assert contract.check_conditions(context)
    
    def test_timelock_execution(self):
        """Test timelock execution"""
        unlock_time = int(time.time()) - 1
        
        contract = TimelockContract(
            contract_id="LOCK004",
            creator="1Creator...",
            conditions={
                "unlock_time": unlock_time,
                "recipient": "1Recipient...",
                "amount": 1000000
            }
        )
        
        context = {"current_time": int(time.time())}
        
        # Execute
        tx = contract.execute(context)
        
        assert tx is not None
        assert contract.status == ContractStatus.EXECUTED
        assert len(tx.outputs) > 0
        assert tx.outputs[0].amount == 1000000


class TestConditionalContract:
    """Test Conditional contracts"""
    
    def test_balance_condition(self):
        """Test balance-based condition"""
        contract = ConditionalContract(
            contract_id="COND001",
            creator="1Creator...",
            conditions={
                "condition_type": "balance",
                "address": "1Target...",
                "threshold": 1000000,
                "action": "transfer",
                "recipient": "1Recipient...",
                "amount": 500000
            }
        )
        
        # Context with sufficient balance
        context = {
            "balances": {"1Target...": 2000000}
        }
        
        assert contract.check_conditions(context)
    
    def test_height_condition(self):
        """Test height-based condition"""
        contract = ConditionalContract(
            contract_id="COND002",
            creator="1Creator...",
            conditions={
                "condition_type": "height",
                "height": 1000,
                "action": "transfer",
                "recipient": "1Recipient...",
                "amount": 500000
            }
        )
        
        # Context with sufficient height
        context = {"height": 1500}
        
        assert contract.check_conditions(context)
        
        # Context with insufficient height
        context = {"height": 500}
        
        assert not contract.check_conditions(context)


class TestEscrowContract:
    """Test Escrow contracts"""
    
    def test_escrow_creation(self):
        """Test escrow contract creation"""
        contract = EscrowContract(
            contract_id="ESC001",
            creator="1Buyer...",
            conditions={
                "buyer": "1Buyer...",
                "seller": "1Seller...",
                "amount": 1000000,
                "timeout": int(time.time()) + 3600
            }
        )
        
        assert contract.contract_id == "ESC001"
        assert not contract.conditions["buyer_confirmed"]
        assert not contract.conditions["seller_confirmed"]
    
    def test_escrow_confirmations(self):
        """Test escrow confirmation process"""
        contract = EscrowContract(
            contract_id="ESC002",
            creator="1Buyer...",
            conditions={
                "buyer": "1Buyer...",
                "seller": "1Seller...",
                "amount": 1000000,
                "timeout": int(time.time()) + 3600
            }
        )
        
        # Buyer confirms
        contract.confirm_buyer()
        assert contract.conditions["buyer_confirmed"]
        
        # Not ready yet
        assert not contract.check_conditions({})
        
        # Seller confirms
        contract.confirm_seller()
        assert contract.conditions["seller_confirmed"]
        
        # Now ready
        assert contract.check_conditions({})
    
    def test_escrow_timeout_refund(self):
        """Test escrow timeout refund"""
        timeout = int(time.time()) - 3600  # Already expired
        
        contract = EscrowContract(
            contract_id="ESC003",
            creator="1Buyer...",
            conditions={
                "buyer": "1Buyer...",
                "seller": "1Seller...",
                "amount": 1000000,
                "timeout": timeout
            }
        )
        
        context = {"current_time": int(time.time())}
        
        # Execute (should refund to buyer)
        tx = contract.execute(context)
        
        assert tx is not None
        # Should send to buyer (timeout refund)
        assert tx.outputs[0].address == "1Buyer..."


class TestContractExecutor:
    """Test Contract executor"""
    
    def test_executor_registration(self, blockchain):
        """Test contract registration"""
        executor = ContractExecutor(blockchain)
        
        contract = TimelockContract(
            contract_id="EXEC001",
            creator="1Creator...",
            conditions={
                "unlock_time": int(time.time()) + 3600,
                "recipient": "1Recipient...",
                "amount": 1000000
            }
        )
        
        executor.register_contract(contract)
        
        assert contract.contract_id in executor.active_contracts
        assert contract.status == ContractStatus.ACTIVE
    
    def test_executor_execution(self, blockchain):
        """Test contract execution by executor"""
        executor = ContractExecutor(blockchain)
        
        # Create already-unlocked contract
        contract = TimelockContract(
            contract_id="EXEC002",
            creator="1Creator...",
            conditions={
                "unlock_time": int(time.time()) - 1,
                "recipient": "1Recipient...",
                "amount": 1000000
            }
        )
        
        executor.register_contract(contract)
        
        # Execute contracts
        txs = executor.execute_contracts()
        
        assert len(txs) > 0
        assert contract.contract_id not in executor.active_contracts
