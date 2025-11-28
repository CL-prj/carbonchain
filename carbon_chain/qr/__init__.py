"""
CarbonChain - QR Code Generation
==================================
QR code generation for certificates and addresses.
"""

from carbon_chain.qr.generator import (
    QRCodeGenerator,
    generate_qr_code,
    generate_certificate_qr,
    generate_address_qr,
)
from carbon_chain.qr.templates import (
    QRTemplate,
    get_certificate_template,
    get_payment_template,
)

__all__ = [
    # Generator
    "QRCodeGenerator",
    "generate_qr_code",
    "generate_certificate_qr",
    "generate_address_qr",
    
    # Templates
    "QRTemplate",
    "get_certificate_template",
    "get_payment_template",
]
