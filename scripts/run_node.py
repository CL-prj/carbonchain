#!/usr/bin/env python3
"""
CarbonChain - Run Node Script
===============================
Script per avviare un nodo completo.

Usage:
    python scripts/run_node.py --network mainnet --data-dir ./data
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from carbon_chain.config import ChainSettings, get_settings
from carbon_chain.domain.blockchain import Blockchain
from carbon_chain.domain.mempool import Mempool
from carbon_chain.storage.db import BlockchainDatabase
from carbon_chain.logging_setup import setup_logging, get_logger
import typer

app = typer.Typer()
logger = get_logger("run_node")


@app.command()
def main(
    network: str = typer.Option("mainnet", help="Network type"),
    data_dir: Path = typer.Option(Path("./data"), help="Data directory"),
    api_enabled: bool = typer.Option(True, help="Enable REST API"),
    api_port: int = typer.Option(8333, help="API port"),
    mining_enabled: bool = typer.Option(False, help="Enable mining"),
    miner_address: str = typer.Option("", help="Miner address for rewards")
):
    """Start CarbonChain node"""
    
    # Setup config
    config = get_settings()
    config.network = network
    config.data_dir = data_dir
    config.api_port = api_port
    
    # Setup logging
    setup_logging(
        log_level=config.log_level,
        log_to_file=config.log_to_file,
        log_dir=config.log_dir
    )
    
    logger.info(f"Starting CarbonChain node on {network}")
    
    # Initialize database
    db_path = data_dir / "carbonchain.db"
    database = BlockchainDatabase(db_path, config)
    
    # Initialize blockchain
    blockchain = Blockchain(config, storage=database)
    
    # Initialize mempool
    mempool = Mempool(
        max_size_mb=config.mempool_max_size_mb,
        max_count=config.mempool_max_size,
        expiry_hours=config.mempool_expiry_hours
    )
    
    logger.info(f"Blockchain initialized at height {blockchain.get_height()}")
    
    # Start API if enabled
    if api_enabled:
        from carbon_chain.api.rest_api import initialize_api
        import uvicorn
        
        api_app = initialize_api(blockchain, mempool, config)
        
        logger.info(f"Starting API server on port {api_port}")
        uvicorn.run(api_app, host="0.0.0.0", port=api_port)
    
    else:
        logger.info("Node running (API disabled)")
        
        # Keep running
        import time
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Node stopped by user")


if __name__ == "__main__":
    app()
