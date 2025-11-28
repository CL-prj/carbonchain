#!/usr/bin/env python3
"""
CarbonChain - MultiSig Demo
=============================
Demo script per multi-signature wallets.

Usage:
    python scripts/multisig_demo.py
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from carbon_chain.wallet.multisig import MultiSigWallet, PSBT
from carbon_chain.domain.crypto_core import generate_keypair
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()


def main():
    """Run multisig demo"""
    
    console.print(Panel.fit(
        "[cyan]CarbonChain - MultiSig Wallet Demo[/cyan]\n\n"
        "Demonstrating 2-of-3 multi-signature wallet",
        border_style="cyan"
    ))
    
    # ========================================================================
    # STEP 1: Create participants
    # ========================================================================
    
    console.print("\n[yellow]Step 1: Creating 3 participants for 2-of-3 multisig[/yellow]")
    
    # Generate keypairs for other participants
    _, pk2 = generate_keypair()
    _, pk3 = generate_keypair()
    
    # Create wallet for participant 1
    wallet1 = MultiSigWallet.create(
        m=2, n=3, my_index=0,
        other_public_keys=[pk2, pk3]
    )
    
    console.print(f"[green]✅ Created 2-of-3 multisig wallet[/green]")
    console.print(f"[cyan]Address: {wallet1.get_address()}[/cyan]")
    
    # Display info
    table = Table(title="MultiSig Configuration")
    table.add_column("Property", style="cyan")
    table.add_column("Value", style="green")
    
    table.add_row("Type", "2-of-3 MultiSig")
    table.add_row("Required Signatures", "2")
    table.add_row("Total Participants", "3")
    table.add_row("My Index", "0")
    table.add_row("Address", wallet1.get_address())
    
    console.print(table)
    
    # ========================================================================
    # STEP 2: Create PSBT
    # ========================================================================
    
    console.print("\n[yellow]Step 2: Creating Partially Signed Bitcoin Transaction (PSBT)[/yellow]")
    
    tx_data = b"example_transaction_data_to_sign"
    psbt = wallet1.create_psbt(tx_data)
    
    console.print(f"[green]✅ Created PSBT[/green]")
    console.print(f"Signatures collected: {len(psbt.partial_signatures)}/{psbt.multisig_config.m}")
    console.print(f"Finalized: {psbt.is_finalized}")
    
    # ========================================================================
    # STEP 3: Collect signatures
    # ========================================================================
    
    console.print("\n[yellow]Step 3: Collecting signatures from participants[/yellow]")
    
    # Participant 1 signs
    console.print("[cyan]Participant 1 signing...[/cyan]")
    success1 = wallet1.sign_psbt(psbt)
    console.print(f"[green]✅ Signature 1 added[/green]")
    console.print(f"Signatures: {len(psbt.partial_signatures)}/{psbt.multisig_config.m}")
    
    # Simulate participant 2 signing
    # (In real scenario, PSBT would be sent to participant 2)
    console.print("\n[cyan]Participant 2 signing...[/cyan]")
    
    # For demo, we'll manually add signature 2
    # In production, participant 2 would have their own wallet and sign
    sk2, _ = generate_keypair()  # Simulated
    try:
        # This would fail in real scenario without proper keys
        # Just demonstrating the flow
        console.print("[yellow]⚠️  Simulating signature 2...[/yellow]")
        psbt.partial_signatures.append(
            type('PartialSig', (), {
                'signer_index': 1,
                'public_key': pk2,
                'signature': b'simulated_signature',
                'timestamp': 0
            })()
        )
        psbt.is_finalized = len(psbt.partial_signatures) >= psbt.multisig_config.m
        console.print(f"[green]✅ Signature 2 added[/green]")
    except:
        pass
    
    console.print(f"Signatures: {len(psbt.partial_signatures)}/{psbt.multisig_config.m}")
    console.print(f"Finalized: {psbt.is_finalized}")
    
    # ========================================================================
    # STEP 4: Finalization
    # ========================================================================
    
    if psbt.is_finalized:
        console.print("\n[yellow]Step 4: PSBT Finalized![/yellow]")
        console.print("[green]✅ Transaction ready for broadcast[/green]")
        
        signatures = psbt.get_finalized_signatures()
        console.print(f"[cyan]Collected {len(signatures)} signatures[/cyan]")
    else:
        console.print("\n[yellow]Step 4: Waiting for more signatures...[/yellow]")
        console.print(f"[cyan]Need {psbt.multisig_config.m - len(psbt.partial_signatures)} more signature(s)[/cyan]")
    
    # ========================================================================
    # Summary
    # ========================================================================
    
    console.print("\n" + "="*60)
    console.print("[green]MultiSig Demo Complete![/green]")
    console.print("\n[cyan]Key Points:[/cyan]")
    console.print("• 2-of-3 multisig requires 2 signatures out of 3 participants")
    console.print("• PSBT allows incremental signature collection")
    console.print("• P2SH addresses provide standard compatibility")
    console.print("• Signatures are verified before finalization")


if __name__ == "__main__":
    main()
