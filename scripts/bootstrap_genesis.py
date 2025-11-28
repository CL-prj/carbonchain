#!/usr/bin/env python3
"""
CarbonChain - Genesis Block Bootstrap
======================================
Create and initialize genesis block for new network.
"""

import sys
import argparse
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from carbon_chain.domain.genesis import GenesisBlockCreator
from carbon_chain.config import ChainSettings
from carbon_chain.domain.blockchain import Blockchain
from carbon_chain.logging_setup import get_logger

logger = get_logger("bootstrap")


def main():
    """Bootstrap genesis block"""
    parser = argparse.ArgumentParser(
        description='Bootstrap CarbonChain genesis block'
    )
    parser.add_argument(
        '--network',
        choices=['mainnet', 'testnet', 'regtest'],
        default='mainnet',
        help='Network type'
    )
    parser.add_argument(
        '--data-dir',
        type=str,
        help='Custom data directory'
    )
    parser.add_argument(
        '--genesis-message',
        type=str,
        default='CarbonChain Genesis - Blockchain for CO2 Certification',
        help='Genesis block message'
    )
    parser.add_argument(
        '--reward-address',
        type=str,
        help='Initial reward address (for testnet/regtest)'
    )
    
    args = parser.parse_args()
    
    # Create configuration
    config = ChainSettings(
        network=args.network,
        data_dir=args.data_dir if args.data_dir else None
    )
    
    logger.info(f"Bootstrapping {args.network} genesis block...")
    logger.info(f"Data directory: {config.data_dir}")
    
    # Check if blockchain already exists
    if (Path(config.data_dir) / "blockchain.db").exists():
        response = input(
            "⚠️  Blockchain already exists. Overwrite? [y/N]: "
        )
        if response.lower() != 'y':
            logger.info("Bootstrap cancelled")
            return
    
    # Create genesis block
    try:
        creator = GenesisBlockCreator(config)
        
        genesis_params = {
            'message': args.genesis_message,
        }
        
        if args.reward_address and args.network != 'mainnet':
            genesis_params['reward_address'] = args.reward_address
        
        genesis_block = creator.create(**genesis_params)
        
        logger.info("✅ Genesis block created!")
        logger.info(f"   Hash: {genesis_block.compute_hash().hex()}")
        logger.info(f"   Timestamp: {genesis_block.header.timestamp}")
        logger.info(f"   Difficulty: {genesis_block.header.difficulty}")
        
        # Initialize blockchain
        blockchain = Blockchain(config)
        
        logger.info("✅ Blockchain initialized!")
        logger.info(f"   Height: {blockchain.get_height()}")
        logger.info(f"   Best block: {blockchain.get_best_block_hash().hex()}")
        
        print("\n" + "="*60)
        print("🌿 CARBONCHAIN GENESIS BLOCK CREATED")
        print("="*60)
        print(f"Network:    {args.network}")
        print(f"Data dir:   {config.data_dir}")
        print(f"Block hash: {genesis_block.compute_hash().hex()}")
        print("="*60)
        
    except Exception as e:
        logger.error(f"Failed to create genesis block: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
