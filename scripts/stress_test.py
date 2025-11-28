#!/usr/bin/env python3
"""
CarbonChain - Stress Test
==========================
Performance and load testing for CarbonChain.
"""

import sys
import argparse
import time
import asyncio
from pathlib import Path
from typing import List
import statistics

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from carbon_chain.domain.blockchain import Blockchain
from carbon_chain.config import ChainSettings
from carbon_chain.services.wallet_service import WalletService
from carbon_chain.services.mining_service import MiningService
from carbon_chain.wallet.hd_wallet import HDWallet
from carbon_chain.logging_setup import get_logger

logger = get_logger("stress_test")


class StressTest:
    """Stress testing framework for CarbonChain"""
    
    def __init__(self, config: ChainSettings):
        self.config = config
        self.blockchain = Blockchain(config)
        self.wallet_service = WalletService(self.blockchain)
        self.mining_service = MiningService(self.blockchain, config)
        self.results = {}
    
    def test_block_mining(self, num_blocks: int = 100):
        """Test block mining performance"""
        logger.info(f"Testing block mining ({num_blocks} blocks)...")
        
        wallet = HDWallet.create(strength=128)
        address = wallet.get_address(0)
        
        times = []
        start_total = time.time()
        
        for i in range(num_blocks):
            start = time.time()
            
            block = self.mining_service.mine_block(address)
            self.blockchain.add_block(block)
            
            elapsed = time.time() - start
            times.append(elapsed)
            
            if (i + 1) % 10 == 0:
                avg = statistics.mean(times[-10:])
                logger.info(f"  Mined {i + 1}/{num_blocks} blocks (avg: {avg:.2f}s)")
        
        total_time = time.time() - start_total
        
        self.results['mining'] = {
            'blocks': num_blocks,
            'total_time': total_time,
            'avg_time': statistics.mean(times),
            'min_time': min(times),
            'max_time': max(times),
            'median_time': statistics.median(times),
            'blocks_per_second': num_blocks / total_time
        }
        
        logger.info(f"✅ Mining test completed")
        logger.info(f"   Total: {total_time:.2f}s")
        logger.info(f"   Average: {statistics.mean(times):.2f}s/block")
        logger.info(f"   Throughput: {num_blocks/total_time:.2f} blocks/s")
    
    def test_transaction_creation(self, num_transactions: int = 1000):
        """Test transaction creation performance"""
        logger.info(f"Testing transaction creation ({num_transactions} txs)...")
        
        # Setup: Mine initial blocks for funds
        wallet1 = HDWallet.create(strength=128)
        wallet2 = HDWallet.create(strength=128)
        addr1 = wallet1.get_address(0)
        addr2 = wallet2.get_address(0)
        
        logger.info("  Mining initial blocks for funding...")
        for _ in range(10):
            block = self.mining_service.mine_block(addr1)
            self.blockchain.add_block(block)
        
        # Create transactions
        times = []
        successful = 0
        failed = 0
        
        start_total = time.time()
        
        for i in range(num_transactions):
            start = time.time()
            
            try:
                tx = self.wallet_service.create_transaction(
                    from_address=addr1,
                    to_address=addr2,
                    amount=1 * 100_000_000,  # 1 CCO2
                    private_key=wallet1.get_private_key(0)
                )
                
                self.blockchain.mempool.add_transaction(tx)
                successful += 1
                
                elapsed = time.time() - start
                times.append(elapsed)
            
            except Exception as e:
                failed += 1
                logger.debug(f"Transaction {i} failed: {e}")
            
            if (i + 1) % 100 == 0:
                logger.info(f"  Created {i + 1}/{num_transactions} transactions")
        
        total_time = time.time() - start_total
        
        self.results['transactions'] = {
            'created': num_transactions,
            'successful': successful,
            'failed': failed,
            'total_time': total_time,
            'avg_time': statistics.mean(times) if times else 0,
            'txs_per_second': successful / total_time if total_time > 0 else 0
        }
        
        logger.info(f"✅ Transaction test completed")
        logger.info(f"   Successful: {successful}/{num_transactions}")
        logger.info(f"   Throughput: {successful/total_time:.2f} tx/s")
    
    def test_utxo_lookup(self, num_lookups: int = 10000):
        """Test UTXO lookup performance"""
        logger.info(f"Testing UTXO lookups ({num_lookups} lookups)...")
        
        # Create some addresses
        addresses = []
        for _ in range(100):
            wallet = HDWallet.create(strength=128)
            addresses.append(wallet.get_address(0))
        
        # Perform lookups
        times = []
        start_total = time.time()
        
        for i in range(num_lookups):
            addr = addresses[i % len(addresses)]
            
            start = time.time()
            balance = self.blockchain.utxo_set.get_balance(addr)
            elapsed = time.time() - start
            
            times.append(elapsed)
            
            if (i + 1) % 1000 == 0:
                logger.info(f"  Performed {i + 1}/{num_lookups} lookups")
        
        total_time = time.time() - start_total
        
        self.results['utxo_lookup'] = {
            'lookups': num_lookups,
            'total_time': total_time,
            'avg_time': statistics.mean(times),
            'lookups_per_second': num_lookups / total_time
        }
        
        logger.info(f"✅ UTXO lookup test completed")
        logger.info(f"   Throughput: {num_lookups/total_time:.2f} lookups/s")
    
    def test_block_validation(self, num_blocks: int = 100):
        """Test block validation performance"""
        logger.info(f"Testing block validation ({num_blocks} blocks)...")
        
        # Mine blocks first
        wallet = HDWallet.create(strength=128)
        address = wallet.get_address(0)
        
        blocks = []
        for _ in range(num_blocks):
            block = self.mining_service.mine_block(address)
            blocks.append(block)
        
        # Validate blocks
        times = []
        start_total = time.time()
        
        for i, block in enumerate(blocks):
            start = time.time()
            
            is_valid = self.blockchain.validate_block(block)
            
            elapsed = time.time() - start
            times.append(elapsed)
            
            if (i + 1) % 10 == 0:
                logger.info(f"  Validated {i + 1}/{num_blocks} blocks")
        
        total_time = time.time() - start_total
        
        self.results['validation'] = {
            'blocks': num_blocks,
            'total_time': total_time,
            'avg_time': statistics.mean(times),
            'blocks_per_second': num_blocks / total_time
        }
        
        logger.info(f"✅ Validation test completed")
        logger.info(f"   Throughput: {num_blocks/total_time:.2f} blocks/s")
    
    def test_concurrent_operations(self, num_threads: int = 10):
        """Test concurrent operations"""
        logger.info(f"Testing concurrent operations ({num_threads} threads)...")
        
        async def worker(worker_id: int, operations: int):
            """Worker coroutine"""
            wallet = HDWallet.create(strength=128)
            address = wallet.get_address(0)
            
            for i in range(operations):
                # Perform random operation
                if i % 3 == 0:
                    # Balance check
                    self.blockchain.utxo_set.get_balance(address)
                elif i % 3 == 1:
                    # Get UTXOs
                    self.blockchain.utxo_set.get_utxos(address)
                else:
                    # Get blockchain info
                    self.blockchain.get_height()
        
        async def run_concurrent():
            tasks = []
            for i in range(num_threads):
                task = asyncio.create_task(worker(i, 100))
                tasks.append(task)
            
            await asyncio.gather(*tasks)
        
        start = time.time()
        asyncio.run(run_concurrent())
        total_time = time.time() - start
        
        total_ops = num_threads * 100
        
        self.results['concurrent'] = {
            'threads': num_threads,
            'operations': total_ops,
            'total_time': total_time,
            'ops_per_second': total_ops / total_time
        }
        
        logger.info(f"✅ Concurrent test completed")
        logger.info(f"   Throughput: {total_ops/total_time:.2f} ops/s")
    
    def print_summary(self):
        """Print test summary"""
        print("\n" + "="*70)
        print("🧪 CARBONCHAIN STRESS TEST RESULTS")
        print("="*70)
        
        for test_name, results in self.results.items():
            print(f"\n{test_name.upper()}:")
            for key, value in results.items():
                if isinstance(value, float):
                    print(f"  {key}: {value:.4f}")
                else:
                    print(f"  {key}: {value}")
        
        print("\n" + "="*70)


def main():
    """Main stress test function"""
    parser = argparse.ArgumentParser(
        description='CarbonChain stress testing'
    )
    parser.add_argument(
        '--test',
        choices=['all', 'mining', 'transactions', 'utxo', 'validation', 'concurrent'],
        default='all',
        help='Test to run'
    )
    parser.add_argument(
        '--network',
        choices=['mainnet', 'testnet', 'regtest'],
        default='regtest',
        help='Network type'
    )
    parser.add_argument(
        '--blocks',
        type=int,
        default=100,
        help='Number of blocks for mining test'
    )
    parser.add_argument(
        '--transactions',
        type=int,
        default=1000,
        help='Number of transactions for tx test'
    )
    parser.add_argument(
        '--lookups',
        type=int,
        default=10000,
        help='Number of lookups for UTXO test'
    )
    parser.add_argument(
        '--threads',
        type=int,
        default=10,
        help='Number of threads for concurrent test'
    )
    
    args = parser.parse_args()
    
    # Create configuration
    config = ChainSettings(
        network=args.network,
        dev_mode=True,
        pow_difficulty_initial=1,  # Easy for testing
    )
    
    logger.info("Starting CarbonChain stress test...")
    logger.info(f"Network: {args.network}")
    
    # Create stress test instance
    tester = StressTest(config)
    
    # Run tests
    try:
        if args.test in ['all', 'mining']:
            tester.test_block_mining(args.blocks)
        
        if args.test in ['all', 'transactions']:
            tester.test_transaction_creation(args.transactions)
        
        if args.test in ['all', 'utxo']:
            tester.test_utxo_lookup(args.lookups)
        
        if args.test in ['all', 'validation']:
            tester.test_block_validation(args.blocks)
        
        if args.test in ['all', 'concurrent']:
            tester.test_concurrent_operations(args.threads)
        
        # Print summary
        tester.print_summary()
    
    except Exception as e:
        logger.error(f"Stress test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
