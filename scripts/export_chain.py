#!/usr/bin/env python3
"""
CarbonChain - Export Chain Script
===================================
Script per esportare blockchain in JSON.

Usage:
    python scripts/export_chain.py --output blockchain.json
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from carbon_chain.config import get_settings
from carbon_chain.domain.blockchain import Blockchain
from carbon_chain.storage.db import BlockchainDatabase
import typer
from rich.console import Console
import json

app = typer.Typer()
console = Console()


@app.command()
def main(
    output: Path = typer.Option(..., "--output", "-o", help="Output JSON file"),
    data_dir: Path = typer.Option(Path("./data"), help="Data directory"),
    start_height: int = typer.Option(0, help="Start height"),
    end_height: int = typer.Option(None, help="End height (None = latest)")
):
    """Export blockchain to JSON"""
    
    config = get_settings()
    config.data_dir = data_dir
    
    # Initialize
    db_path = data_dir / "carbonchain.db"
    database = BlockchainDatabase(db_path, config)
    blockchain = Blockchain(config, storage=database)
    
    if end_height is None:
        end_height = blockchain.get_height()
    
    console.print(f"[cyan]Exporting blocks {start_height} to {end_height}...[/cyan]")
    
    # Export blocks
    blocks_data = []
    for height in range(start_height, end_height + 1):
        block = blockchain.get_block(height)
        if block:
            blocks_data.append(block.to_dict())
    
    # Export data
    export_data = {
        "network": config.network,
        "start_height": start_height,
        "end_height": end_height,
        "block_count": len(blocks_data),
        "blocks": blocks_data
    }
    
    # Save
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(export_data, indent=2))
    
    console.print(f"[green]✅ Exported {len(blocks_data)} blocks to {output}[/green]")


if __name__ == "__main__":
    app()
