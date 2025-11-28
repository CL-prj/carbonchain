#!/usr/bin/env python3
"""
CarbonChain - Check Balance Script
====================================
Script per controllare balance address.

Usage:
    python scripts/check_balance.py --address "1YourAddress..."
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from carbon_chain.config import get_settings
from carbon_chain.domain.blockchain import Blockchain
from carbon_chain.storage.db import BlockchainDatabase
from carbon_chain.constants import satoshi_to_coin
import typer
from rich.console import Console
from rich.table import Table

app = typer.Typer()
console = Console()


@app.command()
def main(
    address: str = typer.Option(..., "--address", "-a", help="Address to check"),
    data_dir: Path = typer.Option(Path("./data"), help="Data directory")
):
    """Check balance for address"""
    
    config = get_settings()
    config.data_dir = data_dir
    
    # Initialize
    db_path = data_dir / "carbonchain.db"
    database = BlockchainDatabase(db_path, config)
    blockchain = Blockchain(config, storage=database)
    
    # Get balance
    balance_detailed = blockchain.get_balance_detailed(address)
    utxos = blockchain.get_utxos(address)
    
    # Display table
    table = Table(title=f"Balance - {address[:32]}...")
    table.add_column("Type", style="cyan")
    table.add_column("Amount (Satoshi)", justify="right", style="green")
    table.add_column("Amount (CCO2)", justify="right", style="yellow")
    
    table.add_row(
        "Total",
        str(balance_detailed["total"]),
        f"{satoshi_to_coin(balance_detailed['total']):.8f}"
    )
    table.add_row(
        "Certified",
        str(balance_detailed["certified"]),
        f"{satoshi_to_coin(balance_detailed['certified']):.8f}"
    )
    table.add_row(
        "Compensated",
        str(balance_detailed["compensated"]),
        f"{satoshi_to_coin(balance_detailed['compensated']):.8f}"
    )
    table.add_row(
        "UTXO Count",
        str(len(utxos)),
        "-"
    )
    
    console.print(table)


if __name__ == "__main__":
    app()
