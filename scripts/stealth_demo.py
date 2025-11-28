#!/usr/bin/env python3
"""
CarbonChain - Stealth Address Demo
====================================
Demo script per stealth addresses.

Usage:
    python scripts/stealth_demo.py
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from carbon_chain.wallet.stealth_address import StealthWallet
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()


def main():
    """Run stealth address demo"""
    
    console.print(Panel.fit(
        "[cyan]CarbonChain - Stealth Address Demo[/cyan]\n\n"
        "Demonstrating privacy-enhanced payments",
        border_style="cyan"
    ))
    
    # ========================================================================
    # STEP 1: Create receiver wallet
    # ========================================================================
    
    console.print("\n[yellow]Step 1: Receiver creates stealth wallet[/yellow]")
    
    receiver = StealthWallet.create()
    
    console.print(f"[green]✅ Stealth wallet created[/green]")
    console.print(f"[cyan]Stealth Address: {receiver.get_address()}[/cyan]")
    
    # Display info
    table = Table(title="Stealth Wallet Info")
    table.add_column("Property", style="cyan")
    table.add_column("Value", style="green")
    
    table.add_row("Type", "Stealth Address")
    table.add_row("Scan Key", receiver.stealth_address.scan_public_key.hex()[:16] + "...")
    table.add_row("Spend Key", receiver.stealth_address.spend_public_key.hex()[:16] + "...")
    table.add_row("Address", receiver.get_address())
    
    console.print(table)
    
    console.print("\n[dim]Receiver shares stealth address publicly[/dim]")
    console.print("[dim]Private keys remain secret[/dim]")
    
    # ========================================================================
    # STEP 2: Sender creates payment
    # ========================================================================
    
    console.print("\n[yellow]Step 2: Sender creates stealth payment[/yellow]")
    
    payment = StealthWallet.create_payment_to(receiver.stealth_address)
    
    console.print(f"[green]✅ Stealth payment created[/green]")
    console.print(f"[cyan]One-time address: {payment.one_time_address}[/cyan]")
    console.print(f"[cyan]Ephemeral key: {payment.ephemeral_public_key.hex()[:32]}...[/cyan]")
    
    console.print("\n[dim]Sender sends funds to one-time address[/dim]")
    console.print("[dim]One-time address is unique per payment[/dim]")
    
    # ========================================================================
    # STEP 3: Receiver detects payment
    # ========================================================================
    
    console.print("\n[yellow]Step 3: Receiver scans for payments[/yellow]")
    
    is_mine = receiver.is_payment_for_me(payment)
    
    if is_mine:
        console.print(f"[green]✅ Payment detected![/green]")
        console.print("[cyan]Payment belongs to this wallet[/cyan]")
    else:
        console.print(f"[red]❌ Payment not for this wallet[/red]")
    
    # ========================================================================
    # STEP 4: Receiver derives spend key
    # ========================================================================
    
    if is_mine:
        console.print("\n[yellow]Step 4: Deriving spend key[/yellow]")
        
        spend_key = receiver.derive_spend_key(payment)
        
        console.print(f"[green]✅ Spend key derived[/green]")
        console.print(f"[cyan]Private key: {spend_key.hex()[:32]}...[/cyan]")
        console.print("[dim]Receiver can now spend funds from one-time address[/dim]")
    
    # ========================================================================
    # STEP 5: Privacy demonstration
    # ========================================================================
    
    console.print("\n[yellow]Step 5: Privacy demonstration[/yellow]")
    
    # Create another receiver
    other_receiver = StealthWallet.create()
    
    console.print("[cyan]Testing with different wallet...[/cyan]")
    is_other_mine = other_receiver.is_payment_for_me(payment)
    
    if not is_other_mine:
        console.print("[green]✅ Other wallet cannot detect payment[/green]")
        console.print("[dim]Privacy preserved - only intended recipient can detect payment[/dim]")
    
    # ========================================================================
    # Summary
    # ========================================================================
    
    console.print("\n" + "="*60)
    console.print("[green]Stealth Address Demo Complete![/green]")
    console.print("\n[cyan]Key Benefits:[/cyan]")
    console.print("• Each payment uses unique one-time address")
    console.print("• Sender and receiver identities protected")
    console.print("• Only receiver can detect payments (via scan key)")
    console.print("• Only receiver can spend (via derived private key)")
    console.print("• No address reuse = enhanced privacy")
    
    console.print("\n[cyan]Use Cases:[/cyan]")
    console.print("• Privacy-focused transactions")
    console.print("• Corporate sensitive payments")
    console.print("• Donations with privacy")
    console.print("• Regulatory compliance with privacy")


if __name__ == "__main__":
    main()
