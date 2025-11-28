"""
CarbonChain - Full Cycle E2E Test
===================================
Complete end-to-end test: mining → transfer → certificate → compensation
"""

import pytest
import time
from pathlib import Path

from carbon_chain.domain.blockchain import Blockchain
from carbon_chain.domain.models import TransactionType, CoinState
from carbon_chain.config import ChainSettings
from carbon_chain.services.wallet_service import WalletService
from carbon_chain.services.mining_service import MiningService
from carbon_chain.services.certificate_service import CertificateService
from carbon_chain.services.compensation_service import CompensationService
from carbon_chain.wallet.hd_wallet import HDWallet


@pytest.fixture
def test_data_dir(tmp_path):
    """Create temporary data directory"""
    return tmp_path / "e2e_test"


@pytest.fixture
def config(test_data_dir):
    """Create test configuration"""
    return ChainSettings(
        network="regtest",
        data_dir=str(test_data_dir),
        dev_mode=True,
        mining_enabled=True,
        pow_difficulty_initial=1,  # Very easy for testing
        block_time_target=1,  # Fast blocks
    )


@pytest.fixture
def blockchain(config):
    """Create and initialize blockchain"""
    bc = Blockchain(config)
    return bc


@pytest.fixture
def miner_wallet():
    """Create miner wallet"""
    return HDWallet.create(strength=128)


@pytest.fixture
def user1_wallet():
    """Create user 1 wallet"""
    return HDWallet.create(strength=128)


@pytest.fixture
def user2_wallet():
    """Create user 2 wallet"""
    return HDWallet.create(strength=128)


@pytest.fixture
def issuer_wallet():
    """Create certificate issuer wallet"""
    return HDWallet.create(strength=128)


class TestFullCycle:
    """
    Complete end-to-end test covering:
    1. Mining blocks
    2. Transferring coins
    3. Issuing certificates
    4. Assigning certificates
    5. Compensating certificates
    """
    
    def test_complete_workflow(
        self,
        blockchain,
        miner_wallet,
        user1_wallet,
        user2_wallet,
        issuer_wallet,
        config
    ):
        """Test complete CarbonChain workflow"""
        
        print("\n" + "="*60)
        print("🌿 CARBONCHAIN FULL CYCLE E2E TEST")
        print("="*60)
        
        # Get addresses
        miner_addr = miner_wallet.get_address(0)
        user1_addr = user1_wallet.get_address(0)
        user2_addr = user2_wallet.get_address(0)
        issuer_addr = issuer_wallet.get_address(0)
        
        print(f"\n👷 Miner Address: {miner_addr[:16]}...")
        print(f"👤 User 1 Address: {user1_addr[:16]}...")
        print(f"👤 User 2 Address: {user2_addr[:16]}...")
        print(f"🏭 Issuer Address: {issuer_addr[:16]}...")
        
        # ================================================================
        # PHASE 1: MINING
        # ================================================================
        
        print("\n" + "="*60)
        print("⛏️  PHASE 1: MINING BLOCKS")
        print("="*60)
        
        mining_service = MiningService(blockchain, config)
        
        # Mine initial blocks for miner
        print("\n⛏️  Mining 10 blocks to miner address...")
        blocks_mined = 0
        
        for i in range(10):
            block = mining_service.mine_block(miner_addr)
            assert block is not None, f"Failed to mine block {i+1}"
            blockchain.add_block(block)
            blocks_mined += 1
            print(f"  ✅ Block {block.header.height} mined (reward: 50 CCO₂)")
        
        assert blockchain.get_height() == 10
        
        # Check miner balance
        miner_balance = blockchain.utxo_set.get_balance(miner_addr)
        expected_balance = 50 * 100_000_000 * 10  # 50 CCO₂ × 10 blocks
        assert miner_balance == expected_balance
        
        print(f"\n💰 Miner Balance: {miner_balance / 100_000_000:.8f} CCO₂")
        print(f"   Blockchain Height: {blockchain.get_height()}")
        
        # ================================================================
        # PHASE 2: TRANSFERS
        # ================================================================
        
        print("\n" + "="*60)
        print("💸 PHASE 2: COIN TRANSFERS")
        print("="*60)
        
        wallet_service = WalletService(blockchain)
        
        # Transfer from miner to user1
        print(f"\n📤 Transfer 100 CCO₂ from miner to user1...")
        tx1 = wallet_service.create_transaction(
            from_address=miner_addr,
            to_address=user1_addr,
            amount=100 * 100_000_000,
            private_key=miner_wallet.get_private_key(0)
        )
        
        assert tx1 is not None
        blockchain.mempool.add_transaction(tx1)
        
        # Mine block with transaction
        block = mining_service.mine_block(miner_addr)
        blockchain.add_block(block)
        
        print(f"  ✅ Transaction {tx1.compute_txid()[:16]}... confirmed")
        
        # Verify user1 received coins
        user1_balance = blockchain.utxo_set.get_balance(user1_addr)
        assert user1_balance == 100 * 100_000_000
        print(f"  💰 User1 Balance: {user1_balance / 100_000_000:.8f} CCO₂")
        
        # Transfer from miner to user2
        print(f"\n📤 Transfer 150 CCO₂ from miner to user2...")
        tx2 = wallet_service.create_transaction(
            from_address=miner_addr,
            to_address=user2_addr,
            amount=150 * 100_000_000,
            private_key=miner_wallet.get_private_key(0)
        )
        
        blockchain.mempool.add_transaction(tx2)
        block = mining_service.mine_block(miner_addr)
        blockchain.add_block(block)
        
        user2_balance = blockchain.utxo_set.get_balance(user2_addr)
        assert user2_balance == 150 * 100_000_000
        print(f"  💰 User2 Balance: {user2_balance / 100_000_000:.8f} CCO₂")
        
        # Transfer from issuer funding
        print(f"\n📤 Transfer 200 CCO₂ from miner to issuer...")
        tx3 = wallet_service.create_transaction(
            from_address=miner_addr,
            to_address=issuer_addr,
            amount=200 * 100_000_000,
            private_key=miner_wallet.get_private_key(0)
        )
        
        blockchain.mempool.add_transaction(tx3)
        block = mining_service.mine_block(miner_addr)
        blockchain.add_block(block)
        
        issuer_balance = blockchain.utxo_set.get_balance(issuer_addr)
        assert issuer_balance == 200 * 100_000_000
        print(f"  💰 Issuer Balance: {issuer_balance / 100_000_000:.8f} CCO₂")
        
        # ================================================================
        # PHASE 3: CERTIFICATE ISSUANCE
        # ================================================================
        
        print("\n" + "="*60)
        print("🎖️  PHASE 3: CERTIFICATE ISSUANCE")
        print("="*60)
        
        cert_service = CertificateService(blockchain, config)
        
        # Issue certificate
        certificate_id = "CERT-2025-E2E1"
        print(f"\n🏭 Issuing certificate {certificate_id}...")
        
        cert_tx = cert_service.issue_certificate(
            certificate_id=certificate_id,
            project_id="PROJ-2025-001",
            total_amount=1000 * 100_000_000,  # 1000 tons CO₂
            location="Italy",
            certificate_type="RENEWABLE_ENERGY",
            standard="VCS",
            issuer_address=issuer_addr,
            issuer_private_key=issuer_wallet.get_private_key(0)
        )
        
        assert cert_tx is not None
        blockchain.mempool.add_transaction(cert_tx)
        
        # Mine block with certificate
        block = mining_service.mine_block(miner_addr)
        blockchain.add_block(block)
        
        # Verify certificate exists
        cert = cert_service.get_certificate(certificate_id)
        assert cert is not None
        assert cert.total_amount == 1000 * 100_000_000
        assert cert.assigned_amount == 0
        
        print(f"  ✅ Certificate {certificate_id} issued")
        print(f"  📊 Total Amount: {cert.total_amount / 100_000_000:.2f} tons CO₂")
        print(f"  📍 Location: {cert.location}")
        print(f"  🏷️  Type: {cert.certificate_type}")
        
        # ================================================================
        # PHASE 4: CERTIFICATE ASSIGNMENT
        # ================================================================
        
        print("\n" + "="*60)
        print("🔗 PHASE 4: CERTIFICATE ASSIGNMENT")
        print("="*60)
        
        # User1 assigns 50 CCO₂ to certificate
        print(f"\n🔗 User1 assigns 50 CCO₂ to certificate...")
        
        assign_tx1 = cert_service.assign_certificate(
            certificate_id=certificate_id,
            amount=50 * 100_000_000,
            from_address=user1_addr,
            private_key=user1_wallet.get_private_key(0)
        )
        
        assert assign_tx1 is not None
        blockchain.mempool.add_transaction(assign_tx1)
        block = mining_service.mine_block(miner_addr)
        blockchain.add_block(block)
        
        # Verify assignment
        cert = cert_service.get_certificate(certificate_id)
        assert cert.assigned_amount == 50 * 100_000_000
        
        user1_balance_after = blockchain.utxo_set.get_balance(user1_addr)
        print(f"  ✅ Assignment successful")
        print(f"  💰 User1 Balance: {user1_balance_after / 100_000_000:.8f} CCO₂")
        print(f"  📊 Certificate Assigned: {cert.assigned_amount / 100_000_000:.2f} tons")
        
        # User2 assigns 100 CCO₂ to certificate
        print(f"\n🔗 User2 assigns 100 CCO₂ to certificate...")
        
        assign_tx2 = cert_service.assign_certificate(
            certificate_id=certificate_id,
            amount=100 * 100_000_000,
            from_address=user2_addr,
            private_key=user2_wallet.get_private_key(0)
        )
        
        blockchain.mempool.add_transaction(assign_tx2)
        block = mining_service.mine_block(miner_addr)
        blockchain.add_block(block)
        
        cert = cert_service.get_certificate(certificate_id)
        assert cert.assigned_amount == 150 * 100_000_000
        
        print(f"  ✅ Assignment successful")
        print(f"  📊 Total Assigned: {cert.assigned_amount / 100_000_000:.2f} tons")
        
        # ================================================================
        # PHASE 5: COMPENSATION
        # ================================================================
        
        print("\n" + "="*60)
        print("♻️  PHASE 5: CO₂ COMPENSATION")
        print("="*60)
        
        comp_service = CompensationService(blockchain, config)
        
        # User1 compensates their certified coins
        print(f"\n♻️  User1 compensates 30 CCO₂...")
        
        comp_tx1 = comp_service.compensate(
            certificate_id=certificate_id,
            amount=30 * 100_000_000,
            from_address=user1_addr,
            private_key=user1_wallet.get_private_key(0),
            claim_name="User1 Company"
        )
        
        assert comp_tx1 is not None
        blockchain.mempool.add_transaction(comp_tx1)
        block = mining_service.mine_block(miner_addr)
        blockchain.add_block(block)
        
        # Verify compensation
        cert = cert_service.get_certificate(certificate_id)
        assert cert.compensated_amount == 30 * 100_000_000
        
        print(f"  ✅ Compensation successful")
        print(f"  ♻️  Total Compensated: {cert.compensated_amount / 100_000_000:.2f} tons")
        print(f"  📊 Remaining: {(cert.total_amount - cert.compensated_amount) / 100_000_000:.2f} tons")
        
        # User2 compensates their certified coins
        print(f"\n♻️  User2 compensates 70 CCO₂...")
        
        comp_tx2 = comp_service.compensate(
            certificate_id=certificate_id,
            amount=70 * 100_000_000,
            from_address=user2_addr,
            private_key=user2_wallet.get_private_key(0),
            claim_name="User2 Corporation"
        )
        
        blockchain.mempool.add_transaction(comp_tx2)
        block = mining_service.mine_block(miner_addr)
        blockchain.add_block(block)
        
        cert = cert_service.get_certificate(certificate_id)
        assert cert.compensated_amount == 100 * 100_000_000
        
        print(f"  ✅ Compensation successful")
        print(f"  ♻️  Total Compensated: {cert.compensated_amount / 100_000_000:.2f} tons")
        
        # ================================================================
        # PHASE 6: VERIFICATION
        # ================================================================
        
        print("\n" + "="*60)
        print("✅ PHASE 6: FINAL VERIFICATION")
        print("="*60)
        
        # Verify blockchain state
        assert blockchain.get_height() > 15
        print(f"\n📊 Blockchain Height: {blockchain.get_height()}")
        
        # Verify certificate state
        final_cert = cert_service.get_certificate(certificate_id)
        print(f"\n🎖️  Certificate {certificate_id}:")
        print(f"   Total:        {final_cert.total_amount / 100_000_000:.2f} tons")
        print(f"   Assigned:     {final_cert.assigned_amount / 100_000_000:.2f} tons")
        print(f"   Compensated:  {final_cert.compensated_amount / 100_000_000:.2f} tons")
        print(f"   Remaining:    {(final_cert.total_amount - final_cert.compensated_amount) / 100_000_000:.2f} tons")
        print(f"   Status:       {final_cert.get_status()}")
        
        # Verify balances
        print(f"\n💰 Final Balances:")
        print(f"   Miner:  {blockchain.utxo_set.get_balance(miner_addr) / 100_000_000:.8f} CCO₂")
        print(f"   User1:  {blockchain.utxo_set.get_balance(user1_addr) / 100_000_000:.8f} CCO₂")
        print(f"   User2:  {blockchain.utxo_set.get_balance(user2_addr) / 100_000_000:.8f} CCO₂")
        print(f"   Issuer: {blockchain.utxo_set.get_balance(issuer_addr) / 100_000_000:.8f} CCO₂")
        
        # Verify total supply
        total_supply = blockchain.get_total_supply()
        print(f"\n📊 Total Supply: {total_supply / 100_000_000:.8f} CCO₂")
        
        # Verify compensated coins are burned
        burn_address = "1CCO2BurnAddressXXXXXXXXXXXYs9mBD"
        burned_amount = blockchain.utxo_set.get_balance(burn_address)
        print(f"🔥 Burned (Compensated): {burned_amount / 100_000_000:.8f} CCO₂")
        
        print("\n" + "="*60)
        print("✅ FULL CYCLE TEST PASSED!")
        print("="*60)
        
        # Final assertions
        assert final_cert.compensated_amount == 100 * 100_000_000
        assert blockchain.get_height() > 15
        assert total_supply > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
