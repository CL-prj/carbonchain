"""
CarbonChain - API Package
==========================
REST API for blockchain interaction.
"""

from carbon_chain.api.rest_api import app, initialize_api

__all__ = [
    "app",
    "initialize_api",
]
