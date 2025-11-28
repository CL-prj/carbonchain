"""
CarbonChain - Explorer Server
===============================
FastAPI server for web explorer with glassmorphism UI.
"""

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path
from typing import Optional
import uvicorn

from carbon_chain.domain.blockchain import Blockchain
from carbon_chain.config import ChainSettings
from carbon_chain.logging_setup import get_logger
from carbon_chain.version import get_version_string
from carbon_chain.constants import satoshi_to_coin

logger = get_logger("explorer.server")


# ============================================================================
# EXPLORER APP
# ============================================================================

def create_explorer_app(
    blockchain: Blockchain,
    config: ChainSettings
) -> FastAPI:
    """
    Create FastAPI explorer application.
    
    Args:
        blockchain: Blockchain instance
        config: Chain configuration
    
    Returns:
        FastAPI: Explorer app
    """
    app = FastAPI(
        title="CarbonChain Explorer",
        description="Modern blockchain explorer with glassmorphism design",
        version="1.0.0"
    )
    
    # Setup paths
    explorer_dir = Path(__file__).parent
    templates_dir = explorer_dir / "templates"
    static_dir = explorer_dir / "static"
    
    # Mount static files
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
    
    # Setup templates
    templates = Jinja2Templates(directory=str(templates_dir))
    
    # Store instances
    app.state.blockchain = blockchain
    app.state.config = config
    
    # ========================================================================
    # ROUTES - HOME
    # ========================================================================
    
    @app.get("/", response_class=HTMLResponse)
    async def home(request: Request):
        """Homepage with blockchain stats"""
        try:
            # Get blockchain stats
            height = blockchain.get_height()
            latest_blocks = []
            
            # Get last 10 blocks
            for i in range(max(0, height - 9), height + 1):
                block = blockchain.get_block_by_height(i)
                if block:
                    latest_blocks.append({
                        "height": i,
                        "hash": block.compute_hash()[:16] + "...",
                        "timestamp": block.header.timestamp,
                        "tx_count": len(block.transactions),
                    })
            
            latest_blocks.reverse()
            
            # Stats
            total_supply = blockchain.get_total_supply()
            
            context = {
                "request": request,
                "title": "CarbonChain Explorer",
                "height": height,
                "total_supply": satoshi_to_coin(total_supply),
                "latest_blocks": latest_blocks,
                "version": get_version_string(),
            }
            
            return templates.TemplateResponse("index.html", context)
        
        except Exception as e:
            logger.error(f"Homepage error: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    # ========================================================================
    # ROUTES - BLOCK
    # ========================================================================
    
    @app.get("/block/{identifier}", response_class=HTMLResponse)
    async def block_detail(request: Request, identifier: str):
        """Block detail page"""
        try:
            # Try as height first, then as hash
            try:
                height = int(identifier)
                block = blockchain.get_block_by_height(height)
            except ValueError:
                block = blockchain.get_block_by_hash(identifier)
            
            if not block:
                raise HTTPException(status_code=404, detail="Block not found")
            
            block_hash = block.compute_hash()
            
            # Format transactions
            transactions = []
            for tx in block.transactions:
                transactions.append({
                    "txid": tx.compute_txid(),
                    "type": tx.tx_type.value,
                    "inputs_count": len(tx.inputs),
                    "outputs_count": len(tx.outputs),
                    "total_output": sum(out.amount for out in tx.outputs),
                })
            
            context = {
                "request": request,
                "title": f"Block #{block.header.height}",
                "block": {
                    "height": block.header.height,
                    "hash": block_hash,
                    "prev_hash": block.header.previous_hash,
                    "merkle_root": block.header.merkle_root,
                    "timestamp": block.header.timestamp,
                    "nonce": block.header.nonce,
                    "difficulty": block.header.difficulty,
                },
                "transactions": transactions,
            }
            
            return templates.TemplateResponse("block.html", context)
        
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Block detail error: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    # ========================================================================
    # ROUTES - TRANSACTION
    # ========================================================================
    
    @app.get("/tx/{txid}", response_class=HTMLResponse)
    async def transaction_detail(request: Request, txid: str):
        """Transaction detail page"""
        try:
            # Find transaction
            tx = blockchain.get_transaction(txid)
            
            if not tx:
                raise HTTPException(status_code=404, detail="Transaction not found")
            
            # Format inputs
            inputs = []
            for inp in tx.inputs:
                inputs.append({
                    "prev_txid": inp.prev_txid if inp.prev_txid else "Coinbase",
                    "prev_index": inp.prev_index,
                })
            
            # Format outputs
            outputs = []
            for idx, out in enumerate(tx.outputs):
                outputs.append({
                    "index": idx,
                    "amount": satoshi_to_coin(out.amount),
                    "amount_satoshi": out.amount,
                    "address": out.address,
                })
            
            context = {
                "request": request,
                "title": f"Transaction {txid[:16]}...",
                "tx": {
                    "txid": txid,
                    "type": tx.tx_type.value,
                    "timestamp": tx.timestamp,
                    "inputs": inputs,
                    "outputs": outputs,
                    "metadata": tx.metadata,
                },
            }
            
            return templates.TemplateResponse("tx.html", context)
        
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Transaction detail error: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    # ========================================================================
    # ROUTES - ADDRESS/WALLET
    # ========================================================================
    
    @app.get("/address/{address}", response_class=HTMLResponse)
    async def address_detail(request: Request, address: str):
        """Address/wallet detail page"""
        try:
            # Get balance
            balance = blockchain.utxo_set.get_balance(address)
            
            # Get UTXOs
            utxos = blockchain.utxo_set.get_utxos(address)
            
            context = {
                "request": request,
                "title": f"Address {address[:16]}...",
                "address": address,
                "balance": satoshi_to_coin(balance),
                "utxo_count": len(utxos),
            }
            
            return templates.TemplateResponse("wallet.html", context)
        
        except Exception as e:
            logger.error(f"Address detail error: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    # ========================================================================
    # ROUTES - CERTIFICATE
    # ========================================================================
    
    @app.get("/certificate/{cert_id}", response_class=HTMLResponse)
    async def certificate_detail(request: Request, cert_id: str):
        """Certificate detail page"""
        try:
            # TODO: Get certificate from blockchain
            # For now, return placeholder
            
            context = {
                "request": request,
                "title": f"Certificate {cert_id}",
                "certificate": {
                    "id": cert_id,
                    "status": "active",
                    "total_amount": 1000000,
                    "compensated_amount": 500000,
                },
            }
            
            return templates.TemplateResponse("certificate.html", context)
        
        except Exception as e:
            logger.error(f"Certificate detail error: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    # ========================================================================
    # ROUTES - SEARCH
    # ========================================================================
    
    @app.get("/search")
    async def search(q: str):
        """Search for block, tx, address"""
        try:
            # Try as block height
            try:
                height = int(q)
                block = blockchain.get_block_by_height(height)
                if block:
                    return JSONResponse({
                        "type": "block",
                        "redirect": f"/block/{height}"
                    })
            except ValueError:
                pass
            
            # Try as block hash (64 hex chars)
            if len(q) == 64 and all(c in '0123456789abcdefABCDEF' for c in q):
                block = blockchain.get_block_by_hash(q)
                if block:
                    return JSONResponse({
                        "type": "block",
                        "redirect": f"/block/{q}"
                    })
                
                # Try as transaction
                tx = blockchain.get_transaction(q)
                if tx:
                    return JSONResponse({
                        "type": "transaction",
                        "redirect": f"/tx/{q}"
                    })
            
            # Try as address
            balance = blockchain.utxo_set.get_balance(q)
            if balance is not None:
                return JSONResponse({
                    "type": "address",
                    "redirect": f"/address/{q}"
                })
            
            return JSONResponse({
                "error": "Not found"
            }, status_code=404)
        
        except Exception as e:
            logger.error(f"Search error: {e}")
            return JSONResponse({
                "error": str(e)
            }, status_code=500)
    
    # ========================================================================
    # API ENDPOINTS
    # ========================================================================
    
    @app.get("/api/stats")
    async def api_stats():
        """Get blockchain statistics"""
        try:
            height = blockchain.get_height()
            total_supply = blockchain.get_total_supply()
            
            return JSONResponse({
                "height": height,
                "total_supply_satoshi": total_supply,
                "total_supply_cco2": satoshi_to_coin(total_supply),
                "version": get_version_string(),
            })
        except Exception as e:
            logger.error(f"Stats API error: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    return app


# ============================================================================
# RUN EXPLORER
# ============================================================================

def run_explorer(
    blockchain: Blockchain,
    config: ChainSettings,
    host: str = "0.0.0.0",
    port: int = 8080
):
    """
    Run explorer server.
    
    Args:
        blockchain: Blockchain instance
        config: Chain configuration
        host: Server host
        port: Server port
    """
    app = create_explorer_app(blockchain, config)
    
    logger.info(f"Starting CarbonChain Explorer on {host}:{port}")
    
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info"
    )


# ============================================================================
# EXPORT
# ============================================================================

__all__ = [
    "create_explorer_app",
    "run_explorer",
]

# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    import argparse
    import os
    
    parser = argparse.ArgumentParser(description='CarbonChain Explorer')
    parser.add_argument('--host', default='0.0.0.0', help='Host')
    parser.add_argument('--port', type=int, default=8080, help='Port')
    parser.add_argument('--network', default='regtest', help='Network')
    parser.add_argument('--data-dir', help='Data directory')
    
    args = parser.parse_args()
    
    if not args.data_dir:
        data_dir = os.path.join(os.getcwd(), 'data')
    else:
        data_dir = os.path.abspath(args.data_dir)
    
    # Crea directory se non esiste
    os.makedirs(data_dir, exist_ok=True)
    os.makedirs(os.path.join(os.getcwd(), 'logs'), exist_ok=True)
    
    # Initialize config
    config = ChainSettings(
        network=args.network,
        data_dir=data_dir  
    )
    
    logger.info(f"Initializing blockchain in {data_dir}")
    blockchain = Blockchain(config)
    
    # Create genesis if needed
    if blockchain.get_height() == -1:
        from carbon_chain.domain.genesis import create_genesis_block
        logger.info("Creating genesis block...")
        genesis = create_genesis_block(config)
        blockchain.add_block(genesis)
        logger.info(f"Genesis block created at height {genesis.header.height}")
    
    # Run
    print(f"\n🌿 CarbonChain Explorer")
    print(f"   URL: http://{args.host}:{args.port}")
    print(f"   Network: {args.network}")
    print(f"   Data dir: {data_dir}")
    print(f"   Blockchain height: {blockchain.get_height()}")
    print(f"\n   Press Ctrl+C to stop\n")
    
    try:
        run_explorer(blockchain, config, host=args.host, port=args.port)
    except KeyboardInterrupt:
        print("\n\n👋 Explorer stopped")