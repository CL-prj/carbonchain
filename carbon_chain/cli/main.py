"""
CarbonChain - Command Line Interface
======================================
CLI completa per gestione nodo e operazioni.

Security Level: MEDIUM
Last Updated: 2025-11-27
Version: 1.0.0

Commands:
- node: Node management
- wallet: Wallet operations
- certificate: Certificate management
- compensation: Compensation operations
- mining: Mining control
- query: Blockchain queries
- network: P2P network operations (Phase 2)
"""

import typer
from typing import Optional
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import print as rprint
import time
import asyncio

# Internal imports
from carbon_chain.domain.blockchain import Blockchain
from carbon_chain.domain.mempool import Mempool
from carbon_chain.storage.db import BlockchainDatabase
from carbon_chain.wallet.hd_wallet import HDWallet
from carbon_chain.services.wallet_service import WalletService
from carbon_chain.services.certificate_service import CertificateService
from carbon_chain.services.compensation_service import CompensationService
from carbon_chain.services.mining_service import MiningService
from carbon_chain.config import ChainSettings, get_settings
from carbon_chain.constants import satoshi_to_coin, format_amount
from carbon_chain.logging_setup import setup_logging


# ============================================================================
# CLI APP
# ============================================================================

app = typer.Typer(
    name="carbonchain",
    help="CarbonChain - CO2 Blockchain CLI",
    add_completion=False
)

console = Console()


# ============================================================================
# GLOBAL STATE
# ============================================================================

class CLIState:
    """Global CLI state"""
    config: Optional[ChainSettings] = None
    blockchain: Optional[Blockchain] = None
    mempool: Optional[Mempool] = None
    database: Optional[BlockchainDatabase] = None
    wallet: Optional[HDWallet] = None


state = CLIState()


# ============================================================================
# NODE COMMANDS
# ============================================================================

node_app = typer.Typer(help="Node management commands")
app.add_typer(node_app, name="node")


@node_app.command("init")
def node_init(
    data_dir: Path = typer.Option(
        Path("./data"),
        "--data-dir",
        "-d",
        help="Data directory"
    ),
    network: str = typer.Option(
        "mainnet",
        "--network",
        "-n",
        help="Network (mainnet/testnet/regtest)"
    )
):
    """Initialize blockchain node"""
    try:
        # Setup config
        config = get_settings()
        config.data_dir = data_dir
        config.network = network
        
        # Setup logging
        setup_logging(
            log_level=config.log_level,
            log_to_file=config.log_to_file,
            log_dir=config.log_dir
        )
        
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
        
        # Store in state
        state.config = config
        state.blockchain = blockchain
        state.mempool = mempool
        state.database = database
        
        console.print(Panel.fit(
            f"[green]✅ Node initialized successfully![/green]\n\n"
            f"Network: [cyan]{network}[/cyan]\n"
            f"Data dir: [cyan]{data_dir}[/cyan]\n"
            f"Genesis hash: [cyan]{blockchain.blocks[0].compute_block_hash()[:16]}...[/cyan]\n"
            f"Height: [cyan]{blockchain.get_height()}[/cyan]",
            title="CarbonChain Node",
            border_style="green"
        ))
    
    except Exception as e:
        console.print(f"[red]Error initializing node: {e}[/red]")
        raise typer.Exit(1)


@node_app.command("info")
def node_info():
    """Show node information"""
    if not state.blockchain:
        console.print("[red]Node not initialized. Run 'carbonchain node init' first.[/red]")
        raise typer.Exit(1)
    
    stats = state.blockchain.get_statistics()
    
    table = Table(title="Node Information", show_header=False)
    table.add_column("Property", style="cyan")
    table.add_column("Value", style="green")
    
    table.add_row("Network", state.config.network)
    table.add_row("Height", str(state.blockchain.get_height()))
    table.add_row("Difficulty", str(state.blockchain.current_difficulty))
    table.add_row("Total Supply", f"{satoshi_to_coin(stats['supply']['total']):.8f} CCO2")
    table.add_row("UTXO Count", str(stats["utxo_count"]))
    table.add_row("Addresses", str(stats["address_count"]))
    table.add_row("Certificates", str(stats["certificates_count"]))
    table.add_row("Projects", str(stats["projects_count"]))
    
    console.print(table)


# ============================================================================
# WALLET COMMANDS
# ============================================================================

wallet_app = typer.Typer(help="Wallet management commands")
app.add_typer(wallet_app, name="wallet")


@wallet_app.command("create")
def wallet_create(
    strength: int = typer.Option(
        128,
        "--strength",
        "-s",
        help="Mnemonic strength (128=12 words, 256=24 words)"
    ),
    save: Optional[Path] = typer.Option(
        None,
        "--save",
        help="Save encrypted wallet to file"
    ),
    password: Optional[str] = typer.Option(
        None,
        "--password",
        "-p",
        help="Password for encryption",
        prompt=True,
        hide_input=True
    )
):
    """Create new wallet"""
    try:
        # Create wallet
        wallet = HDWallet.create_new(
            strength=strength,
            config=state.config or get_settings()
        )
        
        state.wallet = wallet
        
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
        
        # Save if requested
        if save and password:
            encrypted = wallet.export_encrypted(password)
            
            import json
            save.write_text(json.dumps(encrypted, indent=2))
            
            console.print(f"\n[green]✅ Wallet saved to {save}[/green]")
    
    except Exception as e:
        console.print(f"[red]Error creating wallet: {e}[/red]")
        raise typer.Exit(1)


@wallet_app.command("recover")
def wallet_recover(
    mnemonic: str = typer.Option(
        ...,
        "--mnemonic",
        "-m",
        help="Mnemonic phrase (12 or 24 words)",
        prompt=True
    )
):
    """Recover wallet from mnemonic"""
    try:
        wallet = HDWallet.from_mnemonic(
            mnemonic,
            config=state.config or get_settings()
        )
        
        state.wallet = wallet
        
        console.print(Panel.fit(
            f"[green]✅ Wallet recovered![/green]\n\n"
            f"First address: [cyan]{wallet.get_address(0)}[/cyan]",
            title="Wallet Recovered",
            border_style="green"
        ))
        
        # Display addresses
        console.print("\n[cyan]First 5 addresses:[/cyan]")
        for i in range(5):
            addr = wallet.get_address(i)
            console.print(f"  [{i}] {addr}")
    
    except Exception as e:
        console.print(f"[red]Error recovering wallet: {e}[/red]")
        raise typer.Exit(1)


@wallet_app.command("balance")
def wallet_balance(
    address_index: int = typer.Option(
        0,
        "--index",
        "-i",
        help="Address index"
    )
):
    """Show wallet balance"""
    if not state.wallet:
        console.print("[red]No wallet loaded. Create or recover a wallet first.[/red]")
        raise typer.Exit(1)
    
    if not state.blockchain:
        console.print("[red]Node not initialized.[/red]")
        raise typer.Exit(1)
    
    try:
        address = state.wallet.get_address(address_index)
        balance_detailed = state.blockchain.get_balance_detailed(address)
        utxos = state.blockchain.get_utxos(address)
        
        table = Table(title=f"Balance - Address [{address_index}]")
        table.add_column("Type", style="cyan")
        table.add_column("Amount", style="green", justify="right")
        
        table.add_row("Address", address)
        table.add_row("Total", f"{satoshi_to_coin(balance_detailed['total']):.8f} CCO2")
        table.add_row("Certified", f"{satoshi_to_coin(balance_detailed['certified']):.8f} CCO2")
        table.add_row("Compensated", f"{satoshi_to_coin(balance_detailed['compensated']):.8f} CCO2")
        table.add_row("UTXO Count", str(len(utxos)))
        
        console.print(table)
    
    except Exception as e:
        console.print(f"[red]Error querying balance: {e}[/red]")
        raise typer.Exit(1)


@wallet_app.command("transfer")
def wallet_transfer(
    to_address: str = typer.Option(..., "--to", help="Recipient address"),
    amount: float = typer.Option(..., "--amount", "-a", help="Amount in CCO2"),
    from_index: int = typer.Option(0, "--from", help="From address index")
):
    """Send CCO2 coins"""
    if not state.wallet or not state.blockchain or not state.mempool:
        console.print("[red]Node and wallet must be initialized.[/red]")
        raise typer.Exit(1)
    
    try:
        wallet_service = WalletService(state.blockchain, state.config)
        
        # Create transaction
        tx = wallet_service.create_transfer_coin(
            wallet=state.wallet,
            from_address_index=from_index,
            to_address=to_address,
            amount_coin=amount
        )
        
        # Add to mempool
        state.mempool.add_transaction(tx)
        
        txid = tx.compute_txid()
        
        console.print(Panel.fit(
            f"[green]✅ Transfer created![/green]\n\n"
            f"TXID: [cyan]{txid}[/cyan]\n"
            f"Amount: [yellow]{amount} CCO2[/yellow]\n"
            f"To: [cyan]{to_address[:32]}...[/cyan]\n"
            f"Status: [yellow]Pending[/yellow]",
            title="Transfer",
            border_style="green"
        ))
    
    except Exception as e:
        console.print(f"[red]Error creating transfer: {e}[/red]")
        raise typer.Exit(1)


# ============================================================================
# CERTIFICATE COMMANDS
# ============================================================================

cert_app = typer.Typer(help="Certificate management commands")
app.add_typer(cert_app, name="cert")


@cert_app.command("assign")
def cert_assign(
    cert_id: str = typer.Option(..., "--id", help="Certificate ID"),
    total_kg: int = typer.Option(..., "--total", help="Total capacity (kg)"),
    amount_kg: int = typer.Option(..., "--amount", help="Amount to assign (kg)"),
    location: str = typer.Option(..., "--location", help="Project location"),
    description: str = typer.Option(..., "--description", help="Description"),
    issuer: str = typer.Option("", "--issuer", help="Issuer organization"),
    from_index: int = typer.Option(0, "--from", help="From address index")
):
    """Assign certificate to coins"""
    if not state.wallet or not state.blockchain or not state.mempool:
        console.print("[red]Node and wallet must be initialized.[/red]")
        raise typer.Exit(1)
    
    try:
        cert_service = CertificateService(state.blockchain, state.config)
        
        cert_data = {
            "certificate_id": cert_id,
            "total_kg": total_kg,
            "location": location,
            "description": description,
            "issuer": issuer,
            "issue_date": int(time.time())
        }
        
        # Create transaction
        tx = cert_service.create_certificate_assignment(
            wallet=state.wallet,
            from_address_index=from_index,
            certificate_data=cert_data,
            amount_kg=amount_kg
        )
        
        # Add to mempool
        state.mempool.add_transaction(tx)
        
        txid = tx.compute_txid()
        
        console.print(Panel.fit(
            f"[green]✅ Certificate assigned![/green]\n\n"
            f"Certificate: [cyan]{cert_id}[/cyan]\n"
            f"Amount: [yellow]{amount_kg} kg CO2[/yellow]\n"
            f"TXID: [cyan]{txid}[/cyan]\n"
            f"Status: [yellow]Pending[/yellow]",
            title="Certificate Assignment",
            border_style="green"
        ))
    
    except Exception as e:
        console.print(f"[red]Error assigning certificate: {e}[/red]")
        raise typer.Exit(1)


@cert_app.command("list")
def cert_list():
    """List all certificates"""
    if not state.blockchain:
        console.print("[red]Node not initialized.[/red]")
        raise typer.Exit(1)
    
    try:
        cert_service = CertificateService(state.blockchain, state.config)
        certificates = cert_service.list_certificates()
        
        if not certificates:
            console.print("[yellow]No certificates found.[/yellow]")
            return
        
        table = Table(title=f"Certificates ({len(certificates)})")
        table.add_column("ID", style="cyan")
        table.add_column("Total (kg)", justify="right", style="green")
        table.add_column("Issued (kg)", justify="right", style="yellow")
        table.add_column("Compensated (kg)", justify="right", style="red")
        table.add_column("State", style="magenta")
        
        for cert in certificates:
            table.add_row(
                cert["certificate_id"][:32] + "...",
                str(cert["total_kg"]),
                str(cert["issued_kg"]),
                str(cert["compensated_kg"]),
                cert.get("state", "unknown")
            )
        
        console.print(table)
    
    except Exception as e:
        console.print(f"[red]Error listing certificates: {e}[/red]")
        raise typer.Exit(1)


# ============================================================================
# MINING COMMANDS
# ============================================================================

mining_app = typer.Typer(help="Mining commands")
app.add_typer(mining_app, name="mine")


@mining_app.command("start")
def mine_start(
    address_index: int = typer.Option(
        0,
        "--address",
        "-a",
        help="Miner address index"
    ),
    blocks: Optional[int] = typer.Option(
        None,
        "--blocks",
        "-b",
        help="Mine N blocks then stop (default: continuous)"
    )
):
    """Start mining"""
    if not state.wallet or not state.blockchain or not state.mempool:
        console.print("[red]Node and wallet must be initialized.[/red]")
        raise typer.Exit(1)
    
    try:
        miner_address = state.wallet.get_address(address_index)
        
        console.print(Panel.fit(
            f"[cyan]⛏️  Mining started...[/cyan]\n\n"
            f"Miner address: [green]{miner_address}[/green]\n"
            f"Difficulty: [yellow]{state.blockchain.current_difficulty}[/yellow]\n"
            f"Target: [yellow]{'Continuous' if blocks is None else f'{blocks} blocks'}[/yellow]",
            title="Mining",
            border_style="cyan"
        ))
        
        blocks_mined = 0
        
        while True:
            # Mine single block
            with console.status("[cyan]Mining block...[/cyan]"):
                block = state.blockchain.mine_block(
                    miner_address=miner_address,
                    transactions=state.mempool.get_transactions_for_mining(max_count=100),
                    timeout_seconds=60
                )
            
            if block:
                # Add to blockchain
                state.blockchain.add_block(block)
                
                # Remove tx from mempool
                state.mempool.remove_transactions_in_block(block)
                
                blocks_mined += 1
                
                console.print(
                    f"[green]✅ Block {block.header.height} mined! "
                    f"Hash: {block.compute_block_hash()[:16]}... "
                    f"Nonce: {block.header.nonce}[/green]"
                )
                
                # Check stop condition
                if blocks is not None and blocks_mined >= blocks:
                    break
            else:
                console.print("[yellow]Mining timeout. Retrying...[/yellow]")
        
        console.print(f"\n[green]Mining completed! Mined {blocks_mined} blocks.[/green]")
    
    except KeyboardInterrupt:
        console.print("\n[yellow]Mining stopped by user.[/yellow]")
    except Exception as e:
        console.print(f"[red]Mining error: {e}[/red]")
        raise typer.Exit(1)


# ============================================================================
# QUERY COMMANDS
# ============================================================================

query_app = typer.Typer(help="Blockchain query commands")
app.add_typer(query_app, name="query")


@query_app.command("block")
def query_block(
    height: int = typer.Argument(..., help="Block height")
):
    """Show block details"""
    if not state.blockchain:
        console.print("[red]Node not initialized.[/red]")
        raise typer.Exit(1)
    
    block = state.blockchain.get_block(height)
    
    if not block:
        console.print(f"[red]Block {height} not found.[/red]")
        raise typer.Exit(1)
    
    block_hash = block.compute_block_hash()
    
    console.print(Panel.fit(
        f"[cyan]Height:[/cyan] {block.header.height}\n"
        f"[cyan]Hash:[/cyan] {block_hash}\n"
        f"[cyan]Previous:[/cyan] {block.header.previous_hash}\n"
        f"[cyan]Timestamp:[/cyan] {block.header.timestamp}\n"
        f"[cyan]Difficulty:[/cyan] {block.header.difficulty}\n"
        f"[cyan]Nonce:[/cyan] {block.header.nonce}\n"
        f"[cyan]Transactions:[/cyan] {len(block.transactions)}",
        title=f"Block {height}",
        border_style="cyan"
    ))
    
    # Show transactions
    if len(block.transactions) > 0:
        table = Table(title="Transactions")
        table.add_column("TXID", style="cyan")
        table.add_column("Type", style="yellow")
        table.add_column("Outputs", justify="right", style="green")
        
        for tx in block.transactions[:10]:  # First 10
            table.add_row(
                tx.compute_txid()[:16] + "...",
                tx.tx_type.name,
                str(len(tx.outputs))
            )
        
        console.print(table)


@query_app.command("supply")
def query_supply():
    """Show supply statistics"""
    if not state.blockchain:
        console.print("[red]Node not initialized.[/red]")
        raise typer.Exit(1)
    
    supply_stats = state.blockchain.get_supply_statistics()
    
    table = Table(title="Supply Statistics")
    table.add_column("Type", style="cyan")
    table.add_column("Amount (Satoshi)", justify="right", style="green")
    table.add_column("Amount (CCO2)", justify="right", style="yellow")
    
    table.add_row(
        "Total Supply",
        str(supply_stats["total"]),
        f"{satoshi_to_coin(supply_stats['total']):.8f}"
    )
    table.add_row(
        "Certified",
        str(supply_stats["certified"]),
        f"{satoshi_to_coin(supply_stats['certified']):.8f}"
    )
    table.add_row(
        "Compensated",
        str(supply_stats["compensated"]),
        f"{satoshi_to_coin(supply_stats['compensated']):.8f}"
    )
    table.add_row(
        "Spendable",
        str(supply_stats["spendable"]),
        f"{satoshi_to_coin(supply_stats['spendable']):.8f}"
    )
    
    console.print(table)


# ============================================================================
# NETWORK COMMANDS (Phase 2)
# ============================================================================

network_app = typer.Typer(help="Network P2P commands")
app.add_typer(network_app, name="network")


@network_app.command("start")
def network_start(
    p2p_port: int = typer.Option(9333, "--port", "-p", help="P2P port"),
    max_peers: int = typer.Option(128, "--max-peers", help="Max peers")
):
    """Start P2P network node"""
    if not state.blockchain or not state.mempool:
        console.print("[red]Node not initialized. Run 'carbonchain node init' first.[/red]")
        raise typer.Exit(1)
    
    try:
        from carbon_chain.network.node import NetworkNode
        
        # Update config
        state.config.p2p_port = p2p_port
        state.config.p2p_max_peers = max_peers
        
        # Create network node
        node = NetworkNode(state.blockchain, state.mempool, state.config)
        
        async def run():
            await node.start()
            
            console.print(Panel.fit(
                f"[green]✅ Network node started![/green]\n\n"
                f"P2P Port: [cyan]{p2p_port}[/cyan]\n"
                f"Max Peers: [cyan]{max_peers}[/cyan]\n"
                f"Height: [cyan]{state.blockchain.get_height()}[/cyan]",
                title="Network Node",
                border_style="green"
            ))
            
            # Keep running
            try:
                while True:
                    await asyncio.sleep(1)
            except KeyboardInterrupt:
                console.print("\n[yellow]Stopping network...[/yellow]")
                await node.stop()
        
        asyncio.run(run())
    
    except Exception as e:
        console.print(f"[red]Error starting network: {e}[/red]")
        raise typer.Exit(1)


@network_app.command("peers")
def network_peers():
    """Show connected peers"""
    peers_file = (state.config.data_dir if state.config else Path("./data")) / "peers.json"
    
    if not peers_file.exists():
        console.print("[yellow]No peers file found.[/yellow]")
        return
    
    import json
    peers_data = json.loads(peers_file.read_text())
    
    if not peers_data:
        console.print("[yellow]No known peers.[/yellow]")
        return
    
    table = Table(title=f"Known Peers ({len(peers_data)})")
    table.add_column("Address", style="cyan")
    table.add_column("Port", justify="right", style="green")
    table.add_column("Height", justify="right", style="yellow")
    table.add_column("Last Seen", style="dim")
    
    for peer_id, peer_info in list(peers_data.items())[:20]:  # First 20
        last_seen = time.time() - peer_info.get("last_seen", 0)
        last_seen_str = f"{int(last_seen / 60)}m ago" if last_seen < 3600 else f"{int(last_seen / 3600)}h ago"
        
        table.add_row(
            peer_info["address"],
            str(peer_info["port"]),
            str(peer_info.get("start_height", "?")),
            last_seen_str
        )
    
    console.print(table)


@network_app.command("sync")
def network_sync():
    """Sync blockchain with network"""
    console.print("[yellow]Starting blockchain sync...[/yellow]")
    console.print("[dim]Note: Full sync requires running network node.[/dim]")
    
    # TODO: Implement standalone sync command
    console.print("[green]Use 'carbonchain network start' for full P2P sync.[/green]")


# ============================================================================
# MULTISIG COMMANDS (Phase 3)
# ============================================================================

multisig_app = typer.Typer(help="Multi-signature wallet commands")
app.add_typer(multisig_app, name="multisig")


@multisig_app.command("create")
def multisig_create(
    m: int = typer.Option(..., "--m", help="Required signatures"),
    n: int = typer.Option(..., "--n", help="Total participants"),
    my_index: int = typer.Option(..., "--index", help="My participant index (0 to N-1)"),
    wallet_name: str = typer.Option(..., "--name", help="Wallet name")
):
    """Create multi-signature wallet"""
    if not state.blockchain:
        console.print("[red]Node not initialized.[/red]")
        raise typer.Exit(1)
    
    try:
        from carbon_chain.services.multisig_service import MultiSigService
        from carbon_chain.domain.crypto_core import generate_keypair
        
        service = MultiSigService(state.blockchain, state.config)
        
        # For demo: generate other public keys
        # In production: collect from other participants
        other_public_keys = []
        for i in range(n - 1):
            _, pk = generate_keypair()
            other_public_keys.append(pk)
        
        wallet = service.create_multisig_wallet(
            m=m,
            n=n,
            my_index=my_index,
            other_public_keys=other_public_keys,
            wallet_name=wallet_name
        )
        
        console.print(Panel.fit(
            f"[green]✅ MultiSig wallet created![/green]\n\n"
            f"Type: [cyan]{m}-of-{n}[/cyan]\n"
            f"Address: [cyan]{wallet.get_address()}[/cyan]\n"
            f"My Index: [cyan]{my_index}[/cyan]\n"
            f"Script Hash: [dim]{wallet.config.script_hash[:32]}...[/dim]",
            title="MultiSig Wallet",
            border_style="green"
        ))
        
        console.print(f"\n[yellow]⚠️  Share public keys with other participants[/yellow]")
        console.print(f"[cyan]My Public Key: {wallet.my_public_key.hex()[:32]}...[/cyan]")
    
    except Exception as e:
        console.print(f"[red]Error creating multisig wallet: {e}[/red]")
        raise typer.Exit(1)


@multisig_app.command("list")
def multisig_list():
    """List multisig wallets"""
    if not state.blockchain:
        console.print("[red]Node not initialized.[/red]")
        raise typer.Exit(1)
    
    try:
        from carbon_chain.services.multisig_service import MultiSigService
        
        service = MultiSigService(state.blockchain, state.config)
        wallets = service.list_wallets()
        
        if not wallets:
            console.print("[yellow]No multisig wallets found.[/yellow]")
            return
        
        table = Table(title=f"MultiSig Wallets ({len(wallets)})")
        table.add_column("Name", style="cyan")
        
        for name in wallets:
            table.add_row(name)
        
        console.print(table)
    
    except Exception as e:
        console.print(f"[red]Error listing wallets: {e}[/red]")
        raise typer.Exit(1)


@multisig_app.command("balance")
def multisig_balance(
    wallet_name: str = typer.Option(..., "--name", help="Wallet name")
):
    """Check multisig wallet balance"""
    if not state.blockchain:
        console.print("[red]Node not initialized.[/red]")
        raise typer.Exit(1)
    
    try:
        from carbon_chain.services.multisig_service import MultiSigService
        
        service = MultiSigService(state.blockchain, state.config)
        wallet = service.load_wallet(wallet_name)
        balance = service.get_balance(wallet)
        
        table = Table(title=f"Balance - {wallet_name}")
        table.add_column("Property", style="cyan")
        table.add_column("Value", style="green")
        
        table.add_row("Address", wallet.get_address())
        table.add_row("Type", f"{wallet.config.m}-of-{wallet.config.n}")
        table.add_row("Balance", f"{satoshi_to_coin(balance):.8f} CCO2")
        table.add_row("Balance (Satoshi)", str(balance))
        
        console.print(table)
    
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


# ============================================================================
# STEALTH ADDRESS COMMANDS (Phase 3)
# ============================================================================

stealth_app = typer.Typer(help="Stealth address commands")
app.add_typer(stealth_app, name="stealth")


@stealth_app.command("create")
def stealth_create(
    wallet_name: str = typer.Option(..., "--name", help="Wallet name")
):
    """Create stealth address wallet"""
    if not state.blockchain:
        console.print("[red]Node not initialized.[/red]")
        raise typer.Exit(1)
    
    try:
        from carbon_chain.services.stealth_service import StealthService
        
        service = StealthService(state.blockchain, state.config)
        wallet = service.create_stealth_wallet(wallet_name)
        
        console.print(Panel.fit(
            f"[green]✅ Stealth wallet created![/green]\n\n"
            f"Address: [cyan]{wallet.get_address()}[/cyan]\n"
            f"Scan Key: [dim]{wallet.stealth_address.scan_public_key.hex()[:32]}...[/dim]\n"
            f"Spend Key: [dim]{wallet.stealth_address.spend_public_key.hex()[:32]}...[/dim]",
            title="Stealth Wallet",
            border_style="green"
        ))
        
        console.print(f"\n[yellow]⚠️  Share stealth address publicly[/yellow]")
        console.print(f"[yellow]⚠️  Keep private keys secret![/yellow]")
    
    except Exception as e:
        console.print(f"[red]Error creating stealth wallet: {e}[/red]")
        raise typer.Exit(1)


@stealth_app.command("list")
def stealth_list():
    """List stealth wallets"""
    if not state.blockchain:
        console.print("[red]Node not initialized.[/red]")
        raise typer.Exit(1)
    
    try:
        from carbon_chain.services.stealth_service import StealthService
        
        service = StealthService(state.blockchain, state.config)
        wallets = service.list_wallets()
        
        if not wallets:
            console.print("[yellow]No stealth wallets found.[/yellow]")
            return
        
        table = Table(title=f"Stealth Wallets ({len(wallets)})")
        table.add_column("Name", style="cyan")
        
        for name in wallets:
            table.add_row(name)
        
        console.print(table)
    
    except Exception as e:
        console.print(f"[red]Error listing wallets: {e}[/red]")
        raise typer.Exit(1)


@stealth_app.command("scan")
def stealth_scan(
    wallet_name: str = typer.Option(..., "--name", help="Wallet name"),
    start_height: int = typer.Option(0, "--start", help="Start block height"),
    end_height: Optional[int] = typer.Option(None, "--end", help="End block height")
):
    """Scan for stealth payments"""
    if not state.blockchain:
        console.print("[red]Node not initialized.[/red]")
        raise typer.Exit(1)
    
    try:
        from carbon_chain.services.stealth_service import StealthService
        
        service = StealthService(state.blockchain, state.config)
        wallet = service.load_wallet(wallet_name)
        
        console.print(f"[cyan]Scanning blocks {start_height} to {end_height or 'latest'}...[/cyan]")
        
        payments = service.scan_for_payments(wallet, start_height, end_height)
        
        if not payments:
            console.print("[yellow]No payments found.[/yellow]")
            return
        
        console.print(f"[green]Found {len(payments)} payment(s)![/green]\n")
        
        table = Table(title="Stealth Payments")
        table.add_column("TXID", style="cyan")
        table.add_column("One-Time Address", style="green")
        table.add_column("Block", justify="right", style="yellow")
        
        for tx, payment in payments[:10]:  # First 10
            block_height = "?"
            for height in range(start_height, (end_height or state.blockchain.get_height()) + 1):
                block = state.blockchain.get_block(height)
                if block and any(t.compute_txid() == tx.compute_txid() for t in block.transactions):
                    block_height = str(height)
                    break
            
            table.add_row(
                tx.compute_txid()[:16] + "...",
                payment.one_time_address[:32] + "...",
                block_height
            )
        
        console.print(table)
    
    except Exception as e:
        console.print(f"[red]Error scanning: {e}[/red]")
        raise typer.Exit(1)


@stealth_app.command("payments")
def stealth_payments(
    wallet_name: str = typer.Option(..., "--name", help="Wallet name")
):
    """Show received stealth payments"""
    if not state.blockchain:
        console.print("[red]Node not initialized.[/red]")
        raise typer.Exit(1)
    
    try:
        from carbon_chain.services.stealth_service import StealthService
        
        service = StealthService(state.blockchain, state.config)
        wallet = service.load_wallet(wallet_name)
        
        payments = service.get_received_payments(wallet)
        
        if not payments:
            console.print("[yellow]No payments received.[/yellow]")
            return
        
        console.print(f"[green]Received {len(payments)} payment(s)[/green]\n")
        
        table = Table(title="Received Payments")
        table.add_column("TXID", style="cyan")
        table.add_column("Amount (CCO2)", justify="right", style="green")
        table.add_column("Timestamp", style="dim")
        
        total = 0
        for payment in payments:
            import datetime
            dt = datetime.datetime.fromtimestamp(payment["timestamp"])
            
            table.add_row(
                payment["txid"][:16] + "...",
                f"{satoshi_to_coin(payment['amount']):.8f}",
                dt.strftime("%Y-%m-%d %H:%M")
            )
            total += payment["amount"]
        
        console.print(table)
        console.print(f"\n[cyan]Total Received: {satoshi_to_coin(total):.8f} CCO2[/cyan]")
    
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


# ============================================================================
# MULTISIG COMMANDS (Phase 3)
# ============================================================================

multisig_app = typer.Typer(help="Multi-signature wallet commands")
app.add_typer(multisig_app, name="multisig")


@multisig_app.command("create")
def multisig_create(
    m: int = typer.Option(..., "--m", help="Required signatures"),
    n: int = typer.Option(..., "--n", help="Total signatures"),
    my_index: int = typer.Option(0, "--my-index", help="My participant index"),
    wallet_name: str = typer.Option(..., "--name", help="Wallet name")
):
    """Create multi-signature wallet"""
    if not state.blockchain:
        console.print("[red]Node not initialized.[/red]")
        raise typer.Exit(1)
    
    try:
        from carbon_chain.services.multisig_service import MultiSigService
        from carbon_chain.domain.crypto_core import generate_keypair
        
        service = MultiSigService(state.blockchain, state.config)
        
        # Generate other public keys (for demo)
        other_pks = [generate_keypair()[1] for _ in range(n - 1)]
        
        wallet = service.create_multisig_wallet(
            m=m,
            n=n,
            my_index=my_index,
            other_public_keys=other_pks,
            wallet_name=wallet_name
        )
        
        console.print(Panel.fit(
            f"[green]✅ MultiSig wallet created![/green]\n\n"
            f"Type: [cyan]{m}-of-{n}[/cyan]\n"
            f"Address: [cyan]{wallet.get_address()}[/cyan]\n"
            f"My Index: [cyan]{my_index}[/cyan]",
            title="MultiSig Wallet",
            border_style="green"
        ))
    
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@multisig_app.command("list")
def multisig_list():
    """List multi-signature wallets"""
    if not state.blockchain:
        console.print("[red]Node not initialized.[/red]")
        raise typer.Exit(1)
    
    try:
        from carbon_chain.services.multisig_service import MultiSigService
        
        service = MultiSigService(state.blockchain, state.config)
        wallets = service.list_wallets()
        
        if not wallets:
            console.print("[yellow]No multisig wallets found.[/yellow]")
            return
        
        table = Table(title=f"MultiSig Wallets ({len(wallets)})")
        table.add_column("Name", style="cyan")
        
        for wallet_name in wallets:
            table.add_row(wallet_name)
        
        console.print(table)
    
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")


# ============================================================================
# STEALTH COMMANDS (Phase 3)
# ============================================================================

stealth_app = typer.Typer(help="Stealth address commands")
app.add_typer(stealth_app, name="stealth")


@stealth_app.command("create")
def stealth_create(
    wallet_name: str = typer.Option(..., "--name", help="Wallet name")
):
    """Create stealth wallet"""
    if not state.blockchain:
        console.print("[red]Node not initialized.[/red]")
        raise typer.Exit(1)
    
    try:
        from carbon_chain.services.stealth_service import StealthService
        
        service = StealthService(state.blockchain, state.config)
        wallet = service.create_stealth_wallet(wallet_name)
        
        console.print(Panel.fit(
            f"[green]✅ Stealth wallet created![/green]\n\n"
            f"Address: [cyan]{wallet.get_address()}[/cyan]\n"
            f"[yellow]⚠️  Share this address for private payments[/yellow]",
            title="Stealth Wallet",
            border_style="green"
        ))
    
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@stealth_app.command("scan")
def stealth_scan(
    wallet_name: str = typer.Option(..., "--name", help="Wallet name"),
    start_height: int = typer.Option(0, "--start", help="Start height")
):
    """Scan for stealth payments"""
    if not state.blockchain:
        console.print("[red]Node not initialized.[/red]")
        raise typer.Exit(1)
    
    try:
        from carbon_chain.services.stealth_service import StealthService
        
        service = StealthService(state.blockchain, state.config)
        wallet = service.load_wallet(wallet_name)
        
        console.print(f"[cyan]Scanning blockchain from height {start_height}...[/cyan]")
        
        payments = service.scan_for_payments(wallet, start_height)
        
        if not payments:
            console.print("[yellow]No payments found.[/yellow]")
            return
        
        console.print(f"[green]Found {len(payments)} payment(s)![/green]\n")
        
        table = Table(title="Stealth Payments")
        table.add_column("TXID", style="cyan")
        table.add_column("Address", style="green")
        
        for tx, payment in payments:
            table.add_row(
                tx.compute_txid()[:16] + "...",
                payment.one_time_address[:32] + "..."
            )
        
        console.print(table)
    
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")


# ============================================================================
# CONTRACT COMMANDS (Phase 3)
# ============================================================================

contract_app = typer.Typer(help="Smart contract commands")
app.add_typer(contract_app, name="contract")


@contract_app.command("timelock")
def contract_timelock(
    recipient: str = typer.Option(..., "--to", help="Recipient address"),
    amount: float = typer.Option(..., "--amount", help="Amount in CCO2"),
    unlock_time: int = typer.Option(..., "--unlock", help="Unlock timestamp")
):
    """Create timelock contract"""
    if not state.blockchain:
        console.print("[red]Node not initialized.[/red]")
        raise typer.Exit(1)
    
    try:
        from carbon_chain.contracts.simple_contract import TimelockContract
        from carbon_chain.constants import coin_to_satoshi
        import hashlib
        
        amount_sat = coin_to_satoshi(amount)
        contract_id = hashlib.sha256(f"{recipient}{amount}{unlock_time}".encode()).hexdigest()[:16]
        
        contract = TimelockContract(
            contract_id=contract_id,
            creator=state.wallet.get_address(0) if state.wallet else "unknown",
            conditions={
                "unlock_time": unlock_time,
                "recipient": recipient,
                "amount": amount_sat
            }
        )
        
        console.print(Panel.fit(
            f"[green]✅ Timelock contract created![/green]\n\n"
            f"Contract ID: [cyan]{contract_id}[/cyan]\n"
            f"Recipient: [cyan]{recipient[:32]}...[/cyan]\n"
            f"Amount: [yellow]{amount} CCO2[/yellow]\n"
            f"Unlock Time: [cyan]{unlock_time}[/cyan]",
            title="Timelock Contract",
            border_style="green"
        ))
    
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")


@contract_app.command("escrow")
def contract_escrow(
    seller: str = typer.Option(..., "--seller", help="Seller address"),
    amount: float = typer.Option(..., "--amount", help="Amount in CCO2"),
    timeout: int = typer.Option(..., "--timeout", help="Timeout timestamp")
):
    """Create escrow contract"""
    if not state.blockchain or not state.wallet:
        console.print("[red]Node and wallet must be initialized.[/red]")
        raise typer.Exit(1)
    
    try:
        from carbon_chain.contracts.simple_contract import EscrowContract
        from carbon_chain.constants import coin_to_satoshi
        import hashlib
        
        buyer = state.wallet.get_address(0)
        amount_sat = coin_to_satoshi(amount)
        contract_id = hashlib.sha256(f"{buyer}{seller}{amount}{timeout}".encode()).hexdigest()[:16]
        
        contract = EscrowContract(
            contract_id=contract_id,
            creator=buyer,
            conditions={
                "buyer": buyer,
                "seller": seller,
                "amount": amount_sat,
                "timeout": timeout
            }
        )
        
        console.print(Panel.fit(
            f"[green]✅ Escrow contract created![/green]\n\n"
            f"Contract ID: [cyan]{contract_id}[/cyan]\n"
            f"Buyer: [cyan]{buyer[:32]}...[/cyan]\n"
            f"Seller: [cyan]{seller[:32]}...[/cyan]\n"
            f"Amount: [yellow]{amount} CCO2[/yellow]\n"
            f"Timeout: [cyan]{timeout}[/cyan]",
            title="Escrow Contract",
            border_style="green"
        ))
    
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")


# ============================================================================
# POST-QUANTUM COMMANDS (Phase 3)
# ============================================================================

pq_app = typer.Typer(help="Post-quantum cryptography commands")
app.add_typer(pq_app, name="pq")


@pq_app.command("check")
def pq_check():
    """Check post-quantum crypto availability"""
    from carbon_chain.crypto.post_quantum import (
        is_post_quantum_available,
        get_available_algorithms
    )
    
    available = is_post_quantum_available()
    
    if available:
        console.print("[green]✅ Post-quantum cryptography available (liboqs)[/green]")
        
        algorithms = get_available_algorithms()
        
        console.print("\n[cyan]Available algorithms:[/cyan]")
        console.print(f"Signatures: {', '.join(algorithms['signature'])}")
        console.print(f"KEM: {', '.join(algorithms['kem'])}")
    else:
        console.print("[yellow]⚠️  Post-quantum cryptography not available[/yellow]")
        console.print("[dim]Install liboqs-python for full functionality[/dim]")


@pq_app.command("benchmark")
def pq_benchmark(
    algorithm: str = typer.Option("dilithium3", "--algo", help="Algorithm to benchmark"),
    iterations: int = typer.Option(100, "--iterations", help="Number of iterations")
):
    """Benchmark post-quantum algorithm"""
    from carbon_chain.crypto.post_quantum import benchmark_algorithm
    
    console.print(f"[cyan]Benchmarking {algorithm} ({iterations} iterations)...[/cyan]")
    
    results = benchmark_algorithm(algorithm, iterations)
    
    table = Table(title=f"Benchmark Results - {algorithm}")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")
    
    for key, value in results.items():
        if isinstance(value, float):
            table.add_row(key, f"{value:.3f}")
        else:
            table.add_row(key, str(value))
    
    console.print(table)


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

@app.callback()
def main(
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Verbose output"
    )
):
    """
    CarbonChain - CO2 Blockchain CLI
    
    Gestisci nodi, wallet, certificati e compensazioni CO2 on-chain.
    """
    if verbose:
        console.print("[dim]Verbose mode enabled[/dim]")


if __name__ == "__main__":
    app()


# ============================================================================
# EXPORT
# ============================================================================

__all__ = [
    "app",
]
