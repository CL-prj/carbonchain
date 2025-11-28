"""
CarbonChain - QR Code Generator
=================================
Generate QR codes for certificates, addresses, and transactions.
"""

from typing import Optional, Dict, Any
from pathlib import Path
import json
import base64
from io import BytesIO

from carbon_chain.logging_setup import get_logger
from carbon_chain.errors import ValidationError

logger = get_logger("qr.generator")

# Try to import qrcode (optional dependency)
try:
    import qrcode
    from qrcode.image.svg import SvgPathImage
    QRCODE_AVAILABLE = True
except ImportError:
    QRCODE_AVAILABLE = False
    logger.warning("qrcode library not available - QR generation will be limited")


# ============================================================================
# QR CODE GENERATOR
# ============================================================================

class QRCodeGenerator:
    """
    QR code generator for CarbonChain.
    
    Generates QR codes for:
    - Certificate verification
    - Payment addresses
    - Transaction details
    
    Examples:
        >>> generator = QRCodeGenerator()
        >>> qr_data = generator.generate_certificate_qr("CERT-2025-0001")
        >>> svg_content = qr_data["svg"]
    """
    
    def __init__(
        self,
        error_correction: str = "M",
        box_size: int = 10,
        border: int = 4
    ):
        """
        Initialize QR generator.
        
        Args:
            error_correction: Error correction level (L, M, Q, H)
            box_size: Size of each QR box in pixels
            border: Border size in boxes
        """
        if not QRCODE_AVAILABLE:
            logger.warning("QR code generation requires 'qrcode' package")
        
        self.error_correction = self._get_error_correction(error_correction)
        self.box_size = box_size
        self.border = border
    
    def _get_error_correction(self, level: str):
        """Get error correction constant"""
        if not QRCODE_AVAILABLE:
            return None
        
        levels = {
            "L": qrcode.constants.ERROR_CORRECT_L,
            "M": qrcode.constants.ERROR_CORRECT_M,
            "Q": qrcode.constants.ERROR_CORRECT_Q,
            "H": qrcode.constants.ERROR_CORRECT_H,
        }
        return levels.get(level.upper(), qrcode.constants.ERROR_CORRECT_M)
    
    def generate(
        self,
        data: str,
        format: str = "svg"
    ) -> Dict[str, Any]:
        """
        Generate QR code.
        
        Args:
            data: Data to encode
            format: Output format ('svg', 'png', 'base64')
        
        Returns:
            Dict: QR code data
        
        Raises:
            ValidationError: If qrcode not available
        """
        if not QRCODE_AVAILABLE:
            # Return fallback data URL
            return self._generate_fallback(data)
        
        # Create QR code
        qr = qrcode.QRCode(
            version=None,  # Auto-detect
            error_correction=self.error_correction,
            box_size=self.box_size,
            border=self.border,
        )
        
        qr.add_data(data)
        qr.make(fit=True)
        
        if format == "svg":
            return self._generate_svg(qr, data)
        elif format == "png":
            return self._generate_png(qr, data)
        elif format == "base64":
            return self._generate_base64(qr, data)
        else:
            raise ValidationError(f"Unsupported format: {format}")
    
    def _generate_svg(self, qr, data: str) -> Dict:
        """Generate SVG format"""
        img = qr.make_image(image_factory=SvgPathImage)
        
        # Convert to SVG string
        buffer = BytesIO()
        img.save(buffer)
        svg_content = buffer.getvalue().decode('utf-8')
        
        return {
            "format": "svg",
            "data": data,
            "svg": svg_content,
            "mime_type": "image/svg+xml"
        }
    
    def _generate_png(self, qr, data: str) -> Dict:
        """Generate PNG format"""
        img = qr.make_image(fill_color="black", back_color="white")
        
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        png_data = buffer.getvalue()
        
        return {
            "format": "png",
            "data": data,
            "png": png_data,
            "mime_type": "image/png"
        }
    
    def _generate_base64(self, qr, data: str) -> Dict:
        """Generate Base64 encoded PNG"""
        png_result = self._generate_png(qr, data)
        base64_data = base64.b64encode(png_result["png"]).decode('utf-8')
        
        return {
            "format": "base64",
            "data": data,
            "base64": base64_data,
            "data_url": f"data:image/png;base64,{base64_data}",
            "mime_type": "image/png"
        }
    
    def _generate_fallback(self, data: str) -> Dict:
        """Generate fallback when qrcode not available"""
        # Simple data URL with text
        fallback_svg = f'''
        <svg width="200" height="200" xmlns="http://www.w3.org/2000/svg">
            <rect width="200" height="200" fill="#f0f0f0"/>
            <text x="100" y="100" text-anchor="middle" font-size="12" fill="#333">
                QR Code
            </text>
            <text x="100" y="120" text-anchor="middle" font-size="10" fill="#666">
                (qrcode library required)
            </text>
        </svg>
        '''
        
        return {
            "format": "svg",
            "data": data,
            "svg": fallback_svg.strip(),
            "mime_type": "image/svg+xml",
            "fallback": True
        }


# ============================================================================
# CERTIFICATE QR
# ============================================================================

def generate_certificate_qr(
    certificate_id: str,
    base_url: str = "https://carbonchain.io/cert/",
    format: str = "svg"
) -> Dict[str, Any]:
    """
    Generate QR code for certificate verification.
    
    Args:
        certificate_id: Certificate ID
        base_url: Base URL for certificate page
        format: Output format
    
    Returns:
        Dict: QR code data with verification URL
    
    Examples:
        >>> qr = generate_certificate_qr("CERT-2025-0001")
        >>> print(qr["url"])
        'https://carbonchain.io/cert/CERT-2025-0001'
    """
    # Create verification URL
    url = f"{base_url}{certificate_id}"
    
    # Generate QR
    generator = QRCodeGenerator()
    qr_data = generator.generate(url, format=format)
    
    # Add metadata
    qr_data.update({
        "type": "certificate",
        "certificate_id": certificate_id,
        "url": url,
    })
    
    logger.info(f"Generated certificate QR for {certificate_id}")
    
    return qr_data


def generate_address_qr(
    address: str,
    amount: Optional[int] = None,
    label: Optional[str] = None,
    format: str = "svg"
) -> Dict[str, Any]:
    """
    Generate QR code for payment address.
    
    Uses BIP-21 URI format: carbonchain:<address>?amount=<amount>&label=<label>
    
    Args:
        address: Payment address
        amount: Amount in Satoshi (optional)
        label: Payment label (optional)
        format: Output format
    
    Returns:
        Dict: QR code data with payment URI
    
    Examples:
        >>> qr = generate_address_qr("1ABC...", amount=100000000)
        >>> print(qr["uri"])
        'carbonchain:1ABC...?amount=1.0'
    """
    # Build BIP-21 URI
    uri = f"carbonchain:{address}"
    
    params = []
    if amount is not None:
        # Convert Satoshi to CCO2
        amount_cco2 = amount / 100_000_000
        params.append(f"amount={amount_cco2}")
    
    if label:
        params.append(f"label={label}")
    
    if params:
        uri += "?" + "&".join(params)
    
    # Generate QR
    generator = QRCodeGenerator()
    qr_data = generator.generate(uri, format=format)
    
    # Add metadata
    qr_data.update({
        "type": "address",
        "address": address,
        "uri": uri,
    })
    
    if amount:
        qr_data["amount_satoshi"] = amount
        qr_data["amount_cco2"] = amount / 100_000_000
    
    if label:
        qr_data["label"] = label
    
    logger.info(f"Generated address QR for {address[:10]}...")
    
    return qr_data


def generate_transaction_qr(
    txid: str,
    base_url: str = "https://carbonchain.io/tx/",
    format: str = "svg"
) -> Dict[str, Any]:
    """
    Generate QR code for transaction details.
    
    Args:
        txid: Transaction ID
        base_url: Base URL for transaction explorer
        format: Output format
    
    Returns:
        Dict: QR code data with transaction URL
    """
    url = f"{base_url}{txid}"
    
    generator = QRCodeGenerator()
    qr_data = generator.generate(url, format=format)
    
    qr_data.update({
        "type": "transaction",
        "txid": txid,
        "url": url,
    })
    
    return qr_data


def generate_qr_code(
    data: str,
    qr_type: str = "generic",
    format: str = "svg",
    **kwargs
) -> Dict[str, Any]:
    """
    Generate generic QR code.
    
    Args:
        data: Data to encode
        qr_type: QR type (generic, certificate, address, transaction)
        format: Output format
        **kwargs: Additional parameters
    
    Returns:
        Dict: QR code data
    """
    if qr_type == "certificate":
        return generate_certificate_qr(data, format=format, **kwargs)
    elif qr_type == "address":
        return generate_address_qr(data, format=format, **kwargs)
    elif qr_type == "transaction":
        return generate_transaction_qr(data, format=format, **kwargs)
    else:
        generator = QRCodeGenerator()
        qr_data = generator.generate(data, format=format)
        qr_data["type"] = qr_type
        return qr_data


# ============================================================================
# EXPORT
# ============================================================================

__all__ = [
    "QRCodeGenerator",
    "generate_qr_code",
    "generate_certificate_qr",
    "generate_address_qr",
    "generate_transaction_qr",
]
