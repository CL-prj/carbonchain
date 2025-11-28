#!/usr/bin/env python3
"""
CarbonChain - Phase 3 Integration Test
========================================
Test script per tutte le feature Phase 3.

Usage:
    python scripts/test_phase3.py
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
import time

console = Console()


def test_multisig():
    """Test multi-signature wallets"""
    console.print("\n" + "="*60)
    console.print("[cyan]Testing Multi-Signature Wallets[/cyan]")
    console.print("="*60)
    
    try:
        from carbon_chain.wallet.multisig import MultiSigWallet
        from carbon_chain.domain.crypto_core import generate_keypair
        
        # Generate keypairs for participants
        _, pk2 = generate_keypair()
        _, pk3 = generate_keypair()
        
        # Create 2-of-3 multisig
        wallet = MultiSigWallet.create(
            m=2, n=3, my_index=0,
            other_public_keys=[pk2, pk3]
        )
        
        console.print(f"[green]✅ Created 2-of-3 multisig wallet[/green]")
        console.print(f"Address: {wallet.get_address()}")
        
        # Create PSBT
        tx_data = b"test_transaction_data"
        psbt = wallet.create_psbt(tx_data)
        
        # Sign
        wallet.sign_psbt(psbt)
        
        console.print(f"[green]✅ Signed PSBT ({len(psbt.partial_signatures)}/{psbt.multisig_config.m})[/green]")
        
        return True
    
    except Exception as e:
        console.print(f"[red]❌ MultiSig test failed: {e}[/red]")
        return False


def test_stealth():
    """Test stealth addresses"""
    console.print("\n" + "="*60)
    console.print("[cyan]Testing Stealth Addresses[/cyan]")
    console.print("="*60)
    
    try:
        from carbon_chain.wallet.stealth_address import StealthWallet
        
        # Create receiver wallet
        receiver = StealthWallet.create()
        console.print(f"[green]✅ Created stealth wallet[/green]")
        console.print(f"Address: {receiver.get_address()}")
        
        # Create payment
        payment = StealthWallet.create_payment_to(receiver.stealth_address)
        console.print(f"[green]✅ Created stealth payment[/green]")
        console.print(f"One-time address: {payment.one_time_address}")
        
        # Detect payment
        is_mine = receiver.is_payment_for_me(payment)
        console.print(f"[green]✅ Payment detection: {is_mine}[/green]")
        
        # Derive spend key
        if is_mine:
            spend_key = receiver.derive_spend_key(payment)
            console.print(f"[green]✅ Derived spend key[/green]")
        
        return True
    
    except Exception as e:
        console.print(f"[red]❌ Stealth test failed: {e}[/red]")
        return False


def test_post_quantum():
    """Test post-quantum cryptography"""
    console.print("\n" + "="*60)
    console.print("[cyan]Testing Post-Quantum Cryptography[/cyan]")
    console.print("="*60)
    
    try:
        from carbon_chain.crypto.post_quantum import (
            DilithiumSigner,
            KyberKEM,
            HybridSigner,
            is_post_quantum_available
        )
        
        # Check availability
        available = is_post_quantum_available()
        console.print(f"liboqs available: {available}")
        
        # Test Dilithium
        signer = DilithiumSigner.generate("dilithium3")
        message = b"test_message"
        signature = signer.sign(message)
        is_valid = signer.verify(message, signature)
        
        console.print(f"[green]✅ Dilithium signature: {is_valid}[/green]")
        
        # Test Kyber
        kem = KyberKEM.generate("kyber768")
        shared_secret1, ciphertext = KyberKEM.encapsulate(kem.public_key, "kyber768")
        shared_secret2 = kem.decapsulate(ciphertext)
        
        console.print(f"[green]✅ Kyber KEM: {shared_secret1 == shared_secret2}[/green]")
        
        # Test Hybrid
        hybrid = HybridSigner.generate()
        sig = hybrid.sign(message)
        is_valid = hybrid.verify(message, sig)
        
        console.print(f"[green]✅ Hybrid signature: {is_valid}[/green]")
        
        return True
    
    except Exception as e:
        console.print(f"[red]❌ Post-quantum test failed: {e}[/red]")
        return False


def test_contracts():
    """Test smart contracts"""
    console.print("\n" + "="*60)
    console.print("[cyan]Testing Smart Contracts[/cyan]")
    console.print("="*60)
    
    try:
        from carbon_chain.contracts.simple_contract import (
            TimelockContract,
            EscrowContract,
            ContractStatus
        )
        
        # Test Timelock
        unlock_time = int(time.time()) - 1  # Already unlocked
        timelock = TimelockContract(
            contract_id="TEST001",
            creator="1Creator...",
            conditions={
                "unlock_time": unlock_time,
                "recipient": "1Recipient...",
                "amount": 1000000
            }
        )
        
        context = {"current_time": int(time.time())}
        can_execute = timelock.check_conditions(context)
        
        console.print(f"[green]✅ Timelock contract: {can_execute}[/green]")
        
        # Test Escrow
        escrow = EscrowContract(
            contract_id="ESC001",
            creator="1Buyer...",
            conditions={
                "buyer": "1Buyer...",
                "seller": "1Seller...",
                "amount": 1000000,
                "timeout": int(time.time()) + 3600
            }
        )
        
        escrow.confirm_buyer()
        escrow.confirm_seller()
        
        can_execute = escrow.check_conditions({})
        
        console.print(f"[green]✅ Escrow contract: {can_execute}[/green]")
        
        return True
    
    except Exception as e:
        console.print(f"[red]❌ Contracts test failed: {e}[/red]")
        return False


def test_lightning():
    """Test Lightning Network"""
    console.print("\n" + "="*60)
    console.print("[cyan]Testing Lightning Network[/cyan]")
    console.print("="*60)
    
    try:
        from carbon_chain.layer2.lightning import (
            PaymentChannel,
            HTLC,
            ChannelManager,
            ChannelState
        )
        import hashlib
        import secrets
        
        # Test Payment Channel
        channel = PaymentChannel.create(
            party_a="1Alice...",
            party_b="1Bob...",
            capacity=1000000
        )
        
        channel.state = ChannelState.OPEN
        
        console.print(f"[green]✅ Created payment channel[/green]")
        console.print(f"Capacity: {channel.capacity} Satoshi")
        
        # Transfer
        channel.transfer(100000, "1Alice...")
        
        console.print(f"[green]✅ Off-chain transfer executed[/green]")
        console.print(f"Balance A: {channel.balance_a}, Balance B: {channel.balance_b}")
        
        # Test HTLC
        preimage = secrets.token_bytes(32)
        payment_hash = hashlib.sha256(preimage).digest()
        
        htlc = HTLC.create(
            amount=50000,
            payment_hash=payment_hash,
            expiry=int(time.time()) + 3600,
            sender="1Alice...",
            receiver="1Bob..."
        )
        
        htlc.fulfill(preimage)
        
        console.print(f"[green]✅ HTLC fulfilled[/green]")
        
        return True
    
    except Exception as e:
        console.print(f"[red]❌ Lightning test failed: {e}[/red]")
        return False


def main():
    """Run all Phase 3 tests"""
    
    console.print(Panel.fit(
        "[bold cyan]CarbonChain - Phase 3 Integration Test[/bold cyan]\n\n"
        "Testing all advanced features",
        border_style="cyan"
    ))
    
    results = {
        "Multi-Signature Wallets": test_multisig(),
        "Stealth Addresses": test_stealth(),
        "Post-Quantum Crypto": test_post_quantum(),
        "Smart Contracts": test_contracts(),
        "Lightning Network": test_lightning()
    }
    
    # Summary
    console.print("\n" + "="*60)
    console.print("[bold]Test Summary[/bold]")
    console.print("="*60)
    
    table = Table()
    table.add_column("Feature", style="cyan")
    table.add_column("Status", style="bold")
    
    for feature, passed in results.items():
        status = "[green]✅ PASSED[/green]" if passed else "[red]❌ FAILED[/red]"
        table.add_row(feature, status)
    
    console.print(table)
    
    # Overall result
    all_passed = all(results.values())
    
    if all_passed:
        console.print("\n[bold green]🎉 All Phase 3 tests passed![/bold green]")
    else:
        console.print("\n[bold yellow]⚠️  Some tests failed[/bold yellow]")
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
