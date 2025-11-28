#!/usr/bin/env python3
"""
CarbonChain - Peer Info Script
================================
Script per visualizzare info peer connessi.

Usage:
    python scripts/peer_info.py --data-dir ./data
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import json
import typer
from rich.console import Console
from rich.table import Table
import time

app = typer.Typer()
console = Console()


@app.command()
def main(
    data_dir: Path = typer.Option(Path("./data"), "--data-dir", "-d", help="Data directory")
):
    """Show peer information"""
    
    peers_file = data_dir / "peers.json"
    
    if not peers_file.exists():
        console.print("[red]No peers file found.[/red]")
        console.print(f"[dim]Expected file: {peers_file}[/dim]")
        raise typer.Exit(1)
    
    try:
        # Load peers data
        with open(peers_file) as f:
            peers_data = json.load(f)
        
        if not peers_data:
            console.print("[yellow]No peers in database.[/yellow]")
            return
        
        # Create table
        table = Table(title=f"Known Peers ({len(peers_data)})")
        table.add_column("Peer ID", style="cyan")
        table.add_column("Address", style="green")
        table.add_column("Port", justify="right", style="blue")
        table.add_column("Height", justify="right", style="yellow")
        table.add_column("Version", justify="right", style="magenta")
        table.add_column("Last Seen", style="dim")
        table.add_column("Status", style="bold")
        
        # Current time
        current_time = int(time.time())
        
        # Add rows
        for peer_id, peer_info in peers_data.items():
            # Calculate last seen
            last_seen = peer_info.get("last_seen", 0)
            time_diff = current_time - last_seen
            
            if time_diff < 60:
                last_seen_str = f"{time_diff}s ago"
                status = "[green]●[/green] Online"
            elif time_diff < 3600:
                last_seen_str = f"{time_diff // 60}m ago"
                status = "[yellow]●[/yellow] Recent"
            elif time_diff < 86400:
                last_seen_str = f"{time_diff // 3600}h ago"
                status = "[yellow]●[/yellow] Idle"
            else:
                last_seen_str = f"{time_diff // 86400}d ago"
                status = "[red]●[/red] Offline"
            
            table.add_row(
                peer_id[:8] + "...",
                peer_info.get("address", "unknown"),
                str(peer_info.get("port", 0)),
                str(peer_info.get("start_height", 0)),
                str(peer_info.get("version", 1)),
                last_seen_str,
                status
            )
        
        console.print(table)
        
        # Statistics
        console.print(f"\n[cyan]Total peers: {len(peers_data)}[/cyan]")
        
        # Count online peers (seen in last 5 minutes)
        online_count = sum(
            1 for p in peers_data.values()
            if current_time - p.get("last_seen", 0) < 300
        )
        console.print(f"[green]Online: {online_count}[/green]")
    
    except json.JSONDecodeError:
        console.print("[red]Error: Invalid JSON in peers file[/red]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
