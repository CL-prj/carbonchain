#!/usr/bin/env python3
"""
CarbonChain - Import Blockchain
================================
Import blockchain data from external source.
"""

import sys
import argparse
import json
from pathlib import Path
from tqdm import tqdm

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from carbon_chain.domain.blockchain import Blockchain
from carbon_chain.domain.models import Block, Transaction
from carbon_chain.config import ChainSettings
from carbon_chain.logging_setup import get_logger

logger = get_logger("import")


def import_from_json(blockchain: Blockchain, json_file: Path):
    """Import blockchain from JSON file"""
    logger.info(f"Importing from {json_file}...")
    
    with open(json_file, 'r') as f:
        data = json.load(f)
    
    blocks = data.get('blocks', [])
    
    logger.info(f"Found {len(blocks)} blocks to import")
    
    # Import blocks
    for block_data in tqdm(blocks, desc="Importing blocks"):
        try:
            # Deserialize block
            block = Block.from_dict(block_data)
            
            # Add to blockchain
            success = blockchain.add_block(block)
            
            if not success:
                logger.warning(f"Failed to add block {block.header.height}")
        
        except Exception as e:
            logger.error(f"Error importing block: {e}")
            continue
    
    logger.info(f"✅ Import completed. Height: {blockchain.get_height()}")


def import_from_raw(blockchain: Blockchain, raw_file: Path):
    """Import blockchain from raw binary file"""
    logger.info(f"Importing from {raw_file}...")
    
    with open(raw_file, 'rb') as f:
        data = f.read()
    
    # TODO: Implement raw binary import
    logger.warning("Raw binary import not yet implemented")


def main():
    """Main import function"""
    parser = argparse.ArgumentParser(
        description='Import CarbonChain blockchain data'
    )
    parser.add_argument(
        'input_file',
        type=str,
        help='Input file (JSON or raw binary)'
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
        '--format',
        choices=['json', 'raw'],
        default='json',
        help='Input file format'
    )
    parser.add_argument(
        '--verify',
        action='store_true',
        help='Verify blocks after import'
    )
    
    args = parser.parse_args()
    
    # Check input file exists
    input_file = Path(args.input_file)
    if not input_file.exists():
        logger.error(f"Input file not found: {input_file}")
        sys.exit(1)
    
    # Create configuration
    config = ChainSettings(
        network=args.network,
        data_dir=args.data_dir if args.data_dir else None
    )
    
    logger.info(f"Importing to {config.network} blockchain")
    logger.info(f"Data directory: {config.data_dir}")
    
    # Initialize blockchain
    blockchain = Blockchain(config)
    
    initial_height = blockchain.get_height()
    logger.info(f"Current blockchain height: {initial_height}")
    
    # Import based on format
    try:
        if args.format == 'json':
            import_from_json(blockchain, input_file)
        elif args.format == 'raw':
            import_from_raw(blockchain, input_file)
    
    except Exception as e:
        logger.error(f"Import failed: {e}")
        sys.exit(1)
    
    final_height = blockchain.get_height()
    blocks_imported = final_height - initial_height
    
    logger.info(f"✅ Import completed!")
    logger.info(f"   Blocks imported: {blocks_imported}")
    logger.info(f"   Final height: {final_height}")
    
    # Verify if requested
    if args.verify:
        logger.info("Verifying blockchain...")
        
        if blockchain.verify_chain():
            logger.info("✅ Blockchain verification passed")
        else:
            logger.error("❌ Blockchain verification failed")
            sys.exit(1)


if __name__ == '__main__':
    main()
