#!/usr/bin/env python3
"""
CarbonChain - Create Wallet Script
====================================
Script per creare e salvare wallet.

Usage:
    python scripts/create_wallet.py --output wallet.json --password "strong_password"
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from carbon_chain.wallet.hd_wallet import HDWallet
from carbon_chain.config import get_settings
import typer
from rich.console import Console
from rich.panel import Panel
import json

app = typer.Typer()
console = Console()


@app.command()
def main(
    output: Path = typer.Option(..., "--output", "-o", help="Output file path"),
    password: str = typer.Option(..., "--password", "-p", help="Encryption password", prompt=True, hide_input=True),
    strength: int = typer.Option(128, "--strength", "-s", help="Mnemonic strength (128=12 words, 256=24 words)")
):
    """Create new HD Wallet and save encrypted"""
    
    config = get_settings()
    
    # Create wallet
    wallet = HDWallet.create_new(strength=strength, config=config)
    
    # Display mnemonic
    console.print(Panel.fit(
        f"[yellow]⚠️  BACKUP YOUR MNEMONIC PHRASE![/yellow]\n\n"
        f"[bold]{wallet.get_mnemonic()}[/bold]\n\n"
        f"[red]Write this down and store it safely!\n"
        f"Anyone with this phrase can access your wallet.[/red]",
        title="Wallet Created",
        border_style="yellow"
    ))
    
    # Display addresses
    console.print("\n[cyan]First 5 addresses:[/cyan]")
    for i in range(5):
        addr = wallet.get_address(i)
        console.print(f"  [{i}] {addr}")
    
    # Encrypt and save
    encrypted = wallet.export_encrypted(password)
    
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(encrypted, indent=2))
    
    console.print(f"\n[green]✅ Wallet saved to {output}[/green]")
    console.print(f"[yellow]⚠️  Remember your password! Cannot be recovered if lost.[/yellow]")


if __name__ == "__main__":
    app()
