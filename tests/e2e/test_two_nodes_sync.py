"""
CarbonChain - Two Nodes Sync E2E Test
======================================
Test blockchain synchronization between two nodes.
"""

import pytest
import time
import asyncio
from pathlib import Path

from carbon_chain.domain.blockchain import Blockchain
from carbon_chain.config import ChainSettings
from carbon_chain.network.node import P2PNode
from carbon_chain.services.mining_service import MiningService
from carbon_chain.wallet.hd_wallet import HDWallet


@pytest.fixture
def node1_config(tmp_path):
    """Configuration for node 1"""
    return ChainSettings(
        network="regtest",
        data_dir=str(tmp_path / "node1"),
        dev_mode=True,
        p2p_port=19333,
        api_port=18000,
        pow_difficulty_initial=1,
        block_time_target=1,
    )


@pytest.fixture
def node2_config(tmp_path):
    """Configuration for node 2"""
    return ChainSettings(
        network="regtest",
        data_dir=str(tmp_path / "node2"),
        dev_mode=True,
        p2p_port=19334,
        api_port=18001,
        pow_difficulty_initial=1,
        block_time_target=1,
    )


@pytest.fixture
def blockchain1(node1_config):
    """Blockchain for node 1"""
    return Blockchain(node1_config)


@pytest.fixture
def blockchain2(node2_config):
    """Blockchain for node 2"""
    return Blockchain(node2_config)


@pytest.fixture
def wallet1():
    """Wallet for node 1"""
    return HDWallet.create(strength=128)


@pytest.fixture
def wallet2():
    """Wallet for node 2"""
    return HDWallet.create(strength=128)


class TestTwoNodesSync:
    """
    Test blockchain synchronization between two nodes:
    1. Node 1 mines blocks
    2. Node 2 connects and syncs
    3. Node 2 mines blocks
    4. Node 1 syncs from Node 2
    5. Both nodes have same chain
    """
    
    @pytest.mark.asyncio
    async def test_initial_sync(
        self,
        blockchain1,
        blockchain2,
        node1_config,
        node2_config,
        wallet1,
        wallet2
    ):
        """Test initial blockchain synchronization"""
        
        print("\n" + "="*70)
        print("🌐 TWO NODES SYNCHRONIZATION TEST")
        print("="*70)
        
        # Get addresses
        addr1 = wallet1.get_address(0)
        addr2 = wallet2.get_address(0)
        
        print(f"\n🖥️  Node 1 Address: {addr1[:16]}...")
        print(f"🖥️  Node 2 Address: {addr2[:16]}...")
        
        # ================================================================
        # PHASE 1: NODE 1 MINES BLOCKS
        # ================================================================
        
        print("\n" + "="*70)
        print("⛏️  PHASE 1: NODE 1 MINES INITIAL BLOCKS")
        print("="*70)
        
        mining1 = MiningService(blockchain1, node1_config)
        
        print("\n⛏️  Node 1 mining 5 blocks...")
        for i in range(5):
            block = mining1.mine_block(addr1)
            assert block is not None
            blockchain1.add_block(block)
            print(f"  ✅ Block {block.header.height} mined by Node 1")
        
        node1_height = blockchain1.get_height()
        node1_balance = blockchain1.utxo_set.get_balance(addr1)
        
        print(f"\n📊 Node 1 Status:")
        print(f"   Height:  {node1_height}")
        print(f"   Balance: {node1_balance / 100_000_000:.8f} CCO₂")
        
        assert node1_height == 5
        assert node1_balance == 5 * 50 * 100_000_000
        
        # Node 2 should still be at genesis
        node2_height = blockchain2.get_height()
        print(f"\n📊 Node 2 Status (before sync):")
        print(f"   Height:  {node2_height}")
        
        assert node2_height == 0  # Genesis only
        
        # ================================================================
        # PHASE 2: START P2P NODES
        # ================================================================
        
        print("\n" + "="*70)
        print("🌐 PHASE 2: STARTING P2P NETWORK")
        print("="*70)
        
        # Create P2P nodes
        node1 = P2PNode(blockchain1, node1_config)
        node2 = P2PNode(blockchain2, node2_config)
        
        # Start nodes
        print("\n🚀 Starting Node 1...")
        await node1.start()
        print(f"  ✅ Node 1 listening on port {node1_config.p2p_port}")
        
        print("\n🚀 Starting Node 2...")
        await node2.start()
        print(f"  ✅ Node 2 listening on port {node2_config.p2p_port}")
        
        # ================================================================
        # PHASE 3: NODE 2 CONNECTS TO NODE 1
        # ================================================================
        
        print("\n" + "="*70)
        print("🔗 PHASE 3: NODES CONNECTING")
        print("="*70)
        
        # Node 2 connects to Node 1
        print(f"\n🔗 Node 2 connecting to Node 1...")
        await node2.connect_to_peer("127.0.0.1", node1_config.p2p_port)
        
        # Wait for connection
        await asyncio.sleep(1)
        
        # Verify connection
        assert len(node1.peer_manager.get_active_peers()) > 0
        assert len(node2.peer_manager.get_active_peers()) > 0
        
        print(f"  ✅ Nodes connected")
        print(f"  📡 Node 1 peers: {len(node1.peer_manager.get_active_peers())}")
        print(f"  📡 Node 2 peers: {len(node2.peer_manager.get_active_peers())}")
        
        # ================================================================
        # PHASE 4: BLOCKCHAIN SYNCHRONIZATION
        # ================================================================
        
        print("\n" + "="*70)
        print("🔄 PHASE 4: BLOCKCHAIN SYNC (Node 2 ← Node 1)")
        print("="*70)
        
        print("\n🔄 Node 2 requesting blocks from Node 1...")
        
        # Node 2 requests blocks
        await node2.sync_blockchain()
        
        # Wait for sync to complete
        max_wait = 10  # seconds
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            node2_height = blockchain2.get_height()
            
            if node2_height == node1_height:
                break
            
            print(f"  ⏳ Syncing... Node 2 height: {node2_height}/{node1_height}")
            await asyncio.sleep(0.5)
        
        # Verify sync completed
        node2_final_height = blockchain2.get_height()
        
        print(f"\n✅ Sync completed!")
        print(f"   Node 1 height: {blockchain1.get_height()}")
        print(f"   Node 2 height: {node2_final_height}")
        
        assert node2_final_height == node1_height
        
        # Verify blocks are identical
        print(f"\n🔍 Verifying block hashes match...")
        for height in range(1, node1_height + 1):
            block1 = blockchain1.get_block_by_height(height)
            block2 = blockchain2.get_block_by_height(height)
            
            hash1 = block1.compute_hash()
            hash2 = block2.compute_hash()
            
            assert hash1 == hash2, f"Block {height} hashes don't match"
            print(f"  ✅ Block {height}: {hash1.hex()[:16]}...")
        
        print(f"\n✅ All blocks verified identical")
        
        # ================================================================
        # PHASE 5: NODE 2 MINES NEW BLOCKS
        # ================================================================
        
        print("\n" + "="*70)
        print("⛏️  PHASE 5: NODE 2 MINES NEW BLOCKS")
        print("="*70)
        
        mining2 = MiningService(blockchain2, node2_config)
        
        print("\n⛏️  Node 2 mining 3 new blocks...")
        for i in range(3):
            block = mining2.mine_block(addr2)
            assert block is not None
            blockchain2.add_block(block)
            print(f"  ✅ Block {block.header.height} mined by Node 2")
            
            # Broadcast block to Node 1
            await node2.broadcast_block(block)
            await asyncio.sleep(0.5)
        
        # ================================================================
        # PHASE 6: NODE 1 SYNCS FROM NODE 2
        # ================================================================
        
        print("\n" + "="*70)
        print("🔄 PHASE 6: BLOCKCHAIN SYNC (Node 1 ← Node 2)")
        print("="*70)
        
        print("\n🔄 Node 1 syncing new blocks from Node 2...")
        
        # Wait for propagation
        max_wait = 10
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            node1_height = blockchain1.get_height()
            node2_height = blockchain2.get_height()
            
            if node1_height == node2_height:
                break
            
            print(f"  ⏳ Node 1 height: {node1_height}/{node2_height}")
            await asyncio.sleep(0.5)
        
        # Verify both nodes at same height
        final_node1_height = blockchain1.get_height()
        final_node2_height = blockchain2.get_height()
        
        print(f"\n✅ Sync completed!")
        print(f"   Node 1 height: {final_node1_height}")
        print(f"   Node 2 height: {final_node2_height}")
        
        assert final_node1_height == final_node2_height
        assert final_node1_height == 8  # 5 + 3
        
        # ================================================================
        # PHASE 7: VERIFY CONSISTENCY
        # ================================================================
        
        print("\n" + "="*70)
        print("✅ PHASE 7: FINAL CONSISTENCY CHECK")
        print("="*70)
        
        # Verify all blocks match
        print(f"\n🔍 Verifying complete blockchain consistency...")
        for height in range(1, final_node1_height + 1):
            block1 = blockchain1.get_block_by_height(height)
            block2 = blockchain2.get_block_by_height(height)
            
            hash1 = block1.compute_hash()
            hash2 = block2.compute_hash()
            
            assert hash1 == hash2
            print(f"  ✅ Block {height}: Identical")
        
        # Verify balances
        node1_balance = blockchain1.utxo_set.get_balance(addr1)
        node2_balance = blockchain2.utxo_set.get_balance(addr2)
        
        print(f"\n💰 Balances:")
        print(f"   Node 1 (mined 5): {node1_balance / 100_000_000:.8f} CCO₂")
        print(f"   Node 2 (mined 3): {node2_balance / 100_000_000:.8f} CCO₂")
        
        assert node1_balance == 5 * 50 * 100_000_000
        assert node2_balance == 3 * 50 * 100_000_000
        
        # Verify total supply matches on both nodes
        supply1 = blockchain1.get_total_supply()
        supply2 = blockchain2.get_total_supply()
        
        print(f"\n📊 Total Supply:")
        print(f"   Node 1: {supply1 / 100_000_000:.8f} CCO₂")
        print(f"   Node 2: {supply2 / 100_000_000:.8f} CCO₂")
        
        assert supply1 == supply2
        assert supply1 == 8 * 50 * 100_000_000  # 8 blocks × 50 CCO₂
        
        # ================================================================
        # CLEANUP
        # ================================================================
        
        print("\n🛑 Stopping nodes...")
        await node1.stop()
        await node2.stop()
        
        print("\n" + "="*70)
        print("✅ TWO NODES SYNC TEST PASSED!")
        print("="*70)
    
    @pytest.mark.asyncio
    async def test_transaction_propagation(
        self,
        blockchain1,
        blockchain2,
        node1_config,
        node2_config,
        wallet1,
        wallet2
    ):
        """Test transaction propagation between nodes"""
        
        print("\n" + "="*70)
        print("📡 TRANSACTION PROPAGATION TEST")
        print("="*70)
        
        # Setup: Mine initial blocks on node 1
        addr1 = wallet1.get_address(0)
        addr2 = wallet2.get_address(0)
        
        mining1 = MiningService(blockchain1, node1_config)
        
        print("\n⛏️  Mining initial blocks...")
        for i in range(5):
            block = mining1.mine_block(addr1)
            blockchain1.add_block(block)
        
        # Start nodes and connect
        node1 = P2PNode(blockchain1, node1_config)
        node2 = P2PNode(blockchain2, node2_config)
        
        await node1.start()
        await node2.start()
        await node2.connect_to_peer("127.0.0.1", node1_config.p2p_port)
        await asyncio.sleep(1)
        
        # Sync node 2
        await node2.sync_blockchain()
        await asyncio.sleep(2)
        
        # Create transaction on node 1
        print(f"\n📤 Creating transaction on Node 1...")
        from carbon_chain.services.wallet_service import WalletService
        
        wallet_service = WalletService(blockchain1)
        tx = wallet_service.create_transaction(
            from_address=addr1,
            to_address=addr2,
            amount=10 * 100_000_000,
            private_key=wallet1.get_private_key(0)
        )
        
        # Add to node 1 mempool
        blockchain1.mempool.add_transaction(tx)
        print(f"  ✅ Transaction added to Node 1 mempool")
        print(f"  📝 TXID: {tx.compute_txid().hex()[:16]}...")
        
        # Broadcast transaction
        await node1.broadcast_transaction(tx)
        print(f"  📡 Transaction broadcast to peers")
        
        # Wait for propagation
        await asyncio.sleep(1)
        
        # Verify transaction in node 2 mempool
        print(f"\n🔍 Checking Node 2 mempool...")
        node2_mempool_txs = blockchain2.mempool.get_all_transactions()
        
        tx_found = any(
            t.compute_txid() == tx.compute_txid()
            for t in node2_mempool_txs
        )
        
        assert tx_found, "Transaction not propagated to Node 2"
        print(f"  ✅ Transaction found in Node 2 mempool")
        
        # Cleanup
        await node1.stop()
        await node2.stop()
        
        print("\n✅ TRANSACTION PROPAGATION TEST PASSED!")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
