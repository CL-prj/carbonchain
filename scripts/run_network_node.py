#!/usr/bin/env python3
"""
CarbonChain - Run Network Node Script
=======================================
Script per avviare nodo network completo con P2P.

Usage:
    python scripts/run_network_node.py --network mainnet --data-dir ./data
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import asyncio
from carbon_chain.config import get_settings
from carbon_chain.domain.blockchain import Blockchain
from carbon_chain.domain.mempool import Mempool
from carbon_chain.storage.db import BlockchainDatabase
from carbon_chain.network.node import NetworkNode
from carbon_chain.logging_setup import setup_logging, get_logger
import typer
from rich.console import Console

app = typer.Typer()
console = Console()
logger = get_logger("run_network_node")


@app.command()
def main(
    network: str = typer.Option("mainnet", help="Network type"),
    data_dir: Path = typer.Option(Path("./data"), help="Data directory"),
    p2p_port: int = typer.Option(9333, help="P2P port"),
    api_enabled: bool = typer.Option(False, help="Enable REST API"),
    api_port: int = typer.Option(8333, help="API port"),
    max_peers: int = typer.Option(128, help="Max peer connections")
):
    """Start CarbonChain network node with P2P"""
    
    # Setup config
    config = get_settings()
    config.network = network
    config.data_dir = data_dir
    config.p2p_port = p2p_port
    config.p2p_max_peers = max_peers
    
    # Setup logging
    setup_logging(
        log_level=config.log_level,
        log_to_file=config.log_to_file,
        log_dir=config.log_dir
    )
    
    console.print(f"[cyan]Starting CarbonChain network node on {network}[/cyan]")
    console.print(f"[cyan]P2P port: {p2p_port}[/cyan]")
    console.print(f"[cyan]Max peers: {max_peers}[/cyan]\n")
    
    # Initialize components
    db_path = data_dir / "carbonchain.db"
    database = BlockchainDatabase(db_path, config)
    blockchain = Blockchain(config, storage=database)
    mempool = Mempool(
        max_size_mb=config.mempool_max_size_mb,
        max_count=config.mempool_max_size,
        expiry_hours=config.mempool_expiry_hours
    )
    
    # Create network node
    node = NetworkNode(blockchain, mempool, config)
    
    async def run_node():
        try:
            # Start node
            await node.start()
            
            console.print("[green]✅ Network node started![/green]")
            console.print(f"[cyan]Blockchain height: {blockchain.get_height()}[/cyan]")
            console.print(f"[cyan]Connected peers: {node.peer_manager.get_peer_count()}[/cyan]\n")
            
            # Sync blockchain
            console.print("[yellow]Starting blockchain sync...[/yellow]")
            await node.sync_blockchain()
            
            # Keep running
            console.print("[green]Node running. Press Ctrl+C to stop.[/green]\n")
            while True:
                await asyncio.sleep(1)
        
        except KeyboardInterrupt:
            console.print("\n[yellow]Stopping node...[/yellow]")
        finally:
            await node.stop()
            console.print("[green]Node stopped.[/green]")
    
    # Run async
    asyncio.run(run_node())


if __name__ == "__main__":
    app()
