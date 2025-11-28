"""
CarbonChain - Web Explorer
============================
Modern web interface for blockchain exploration.
"""

from carbon_chain.explorer.server import create_explorer_app, run_explorer

__all__ = [
    "create_explorer_app",
    "run_explorer",
]
