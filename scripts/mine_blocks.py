#!/usr/bin/env python3
"""
CarbonChain - Mine Blocks Script
==================================
Script per minare N blocchi per testing.

Usage:
    python scripts/mine_blocks.py --count 10 --address "1YourAddress..."
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from carbon_chain.config import get_settings
from carbon_chain.domain.blockchain import Blockchain
from carbon_chain.domain.mempool import Mempool
from carbon_chain.storage.db import BlockchainDatabase
from carbon_chain.logging_setup import setup_logging, get_logger
import typer
from rich.console import Console
from rich.progress import Progress

app = typer.Typer()
console = Console()
logger = get_logger("mine_blocks")


@app.command()
def main(
    count: int = typer.Option(1, help="Number of blocks to mine"),
    address: str = typer.Option(..., help="Miner address for rewards"),
    data_dir: Path = typer.Option(Path("./data"), help="Data directory"),
    timeout: int = typer.Option(60, help="Timeout per block (seconds)")
):
    """Mine N blocks for testing"""
    
    config = get_settings()
    config.data_dir = data_dir
    
    setup_logging(log_level="INFO", log_to_file=False)
    
    # Initialize
    db_path = data_dir / "carbonchain.db"
    database = BlockchainDatabase(db_path, config)
    blockchain = Blockchain(config, storage=database)
    mempool = Mempool()
    
    console.print(f"[cyan]Mining {count} blocks...[/cyan]")
    console.print(f"[cyan]Miner address: {address}[/cyan]")
    console.print(f"[cyan]Current height: {blockchain.get_height()}[/cyan]\n")
    
    success_count = 0
    
    with Progress() as progress:
        task = progress.add_task("[cyan]Mining...", total=count)
        
        for i in range(count):
            # Get pending transactions
            transactions = mempool.get_transactions_for_mining(max_count=100)
            
            # Mine block
            block = blockchain.mine_block(
                miner_address=address,
                transactions=transactions,
                timeout_seconds=timeout
            )
            
            if block:
                blockchain.add_block(block)
                database.save_block(block)
                
                # Remove mined tx from mempool
                mempool.remove_transactions_in_block(block)
                
                success_count += 1
                
                console.print(
                    f"[green]✅ Block {block.header.height} mined! "
                    f"Hash: {block.compute_block_hash()[:16]}...[/green]"
                )
            else:
                console.print(f"[red]❌ Mining timeout for block {i+1}[/red]")
            
            progress.update(task, advance=1)
    
    console.print(f"\n[green]Mining complete: {success_count}/{count} blocks mined[/green]")
    console.print(f"[cyan]Final height: {blockchain.get_height()}[/cyan]")


if __name__ == "__main__":
    app()
