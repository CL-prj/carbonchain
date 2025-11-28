"""
CarbonChain - QR Templates
============================
HTML/SVG templates for QR code display.
"""

from typing import Dict, Any, Optional
from dataclasses import dataclass

from carbon_chain.logging_setup import get_logger

logger = get_logger("qr.templates")


# ============================================================================
# QR TEMPLATE
# ============================================================================

@dataclass
class QRTemplate:
    """
    QR code display template.
    
    Attributes:
        title: Template title
        description: Template description
        html: HTML template
        css: CSS styles
    """
    title: str
    description: str
    html: str
    css: str
    
    def render(self, qr_data: Dict[str, Any]) -> str:
        """
        Render template with QR data.
        
        Args:
            qr_data: QR code data from generator
        
        Returns:
            str: Rendered HTML
        """
        # Replace placeholders
        html = self.html
        
        for key, value in qr_data.items():
            placeholder = f"{{{{{key}}}}}"
            html = html.replace(placeholder, str(value))
        
        # Add CSS
        if self.css:
            html = f"<style>{self.css}</style>\n{html}"
        
        return html


# ============================================================================
# CERTIFICATE TEMPLATE
# ============================================================================

def get_certificate_template() -> QRTemplate:
    """
    Get template for certificate QR code.
    
    Returns:
        QRTemplate: Certificate template
    """
    html = """
    <div class="qr-certificate-card">
        <div class="qr-header">
            <h2>🌿 CO₂ Certificate</h2>
            <p class="cert-id">{{certificate_id}}</p>
        </div>
        
        <div class="qr-code-container">
            {{svg}}
        </div>
        
        <div class="qr-footer">
            <p class="scan-instruction">
                📱 Scan to verify certificate authenticity
            </p>
            <p class="url">
                <a href="{{url}}" target="_blank">{{url}}</a>
            </p>
        </div>
        
        <div class="qr-info">
            <p>✅ Verified on CarbonChain</p>
            <p>🔒 Immutable blockchain record</p>
        </div>
    </div>
    """
    
    css = """
    .qr-certificate-card {
        max-width: 400px;
        margin: 20px auto;
        padding: 30px;
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
        border-radius: 20px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.1);
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    }
    
    .qr-header {
        text-align: center;
        margin-bottom: 20px;
    }
    
    .qr-header h2 {
        margin: 0 0 10px 0;
        color: #2c3e50;
        font-size: 24px;
    }
    
    .cert-id {
        font-family: 'Courier New', monospace;
        font-size: 14px;
        color: #7f8c8d;
        margin: 5px 0;
    }
    
    .qr-code-container {
        background: white;
        padding: 20px;
        border-radius: 10px;
        margin: 20px 0;
        display: flex;
        justify-content: center;
        align-items: center;
    }
    
    .qr-code-container svg {
        max-width: 100%;
        height: auto;
    }
    
    .qr-footer {
        text-align: center;
        margin-top: 20px;
    }
    
    .scan-instruction {
        font-size: 14px;
        color: #34495e;
        margin: 10px 0;
    }
    
    .url {
        font-size: 12px;
        word-break: break-all;
    }
    
    .url a {
        color: #3498db;
        text-decoration: none;
    }
    
    .qr-info {
        margin-top: 20px;
        padding-top: 20px;
        border-top: 1px solid rgba(0,0,0,0.1);
        text-align: center;
    }
    
    .qr-info p {
        font-size: 12px;
        color: #27ae60;
        margin: 5px 0;
    }
    """
    
    return QRTemplate(
        title="Certificate QR Code",
        description="Scannable QR code for CO2 certificate verification",
        html=html,
        css=css
    )


# ============================================================================
# PAYMENT TEMPLATE
# ============================================================================

def get_payment_template() -> QRTemplate:
    """
    Get template for payment address QR code.
    
    Returns:
        QRTemplate: Payment template
    """
    html = """
    <div class="qr-payment-card">
        <div class="qr-header">
            <h2>💳 Payment Request</h2>
        </div>
        
        <div class="qr-code-container">
            {{svg}}
        </div>
        
        <div class="payment-details">
            <div class="detail-row">
                <span class="label">Address:</span>
                <span class="value address-value">{{address}}</span>
            </div>
            
            <div class="detail-row" style="display: {{#if amount_cco2}}block{{else}}none{{/if}}">
                <span class="label">Amount:</span>
                <span class="value amount-value">{{amount_cco2}} CCO₂</span>
            </div>
            
            <div class="detail-row" style="display: {{#if label}}block{{else}}none{{/if}}">
                <span class="label">Label:</span>
                <span class="value">{{label}}</span>
            </div>
        </div>
        
        <div class="qr-footer">
            <p class="scan-instruction">
                📱 Scan with CarbonChain wallet to pay
            </p>
        </div>
    </div>
    """
    
    css = """
    .qr-payment-card {
        max-width: 400px;
        margin: 20px auto;
        padding: 30px;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 20px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.2);
        color: white;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    }
    
    .qr-header h2 {
        margin: 0 0 20px 0;
        text-align: center;
        font-size: 24px;
    }
    
    .qr-code-container {
        background: white;
        padding: 20px;
        border-radius: 10px;
        margin: 20px 0;
        display: flex;
        justify-content: center;
        align-items: center;
    }
    
    .payment-details {
        background: rgba(255,255,255,0.1);
        padding: 15px;
        border-radius: 10px;
        margin: 20px 0;
    }
    
    .detail-row {
        display: flex;
        justify-content: space-between;
        margin: 10px 0;
        font-size: 14px;
    }
    
    .label {
        font-weight: 600;
    }
    
    .value {
        font-family: 'Courier New', monospace;
    }
    
    .address-value {
        word-break: break-all;
        text-align: right;
        max-width: 60%;
    }
    
    .amount-value {
        font-size: 18px;
        font-weight: bold;
    }
    
    .qr-footer {
        text-align: center;
        margin-top: 20px;
    }
    
    .scan-instruction {
        font-size: 14px;
        opacity: 0.9;
    }
    """
    
    return QRTemplate(
        title="Payment QR Code",
        description="Scannable QR code for CarbonChain payment",
        html=html,
        css=css
    )


# ============================================================================
# GENERIC TEMPLATE
# ============================================================================

def get_generic_template() -> QRTemplate:
    """
    Get generic QR code template.
    
    Returns:
        QRTemplate: Generic template
    """
    html = """
    <div class="qr-generic-card">
        <div class="qr-code-container">
            {{svg}}
        </div>
        <div class="qr-data">
            <p>{{data}}</p>
        </div>
    </div>
    """
    
    css = """
    .qr-generic-card {
        max-width: 300px;
        margin: 20px auto;
        padding: 20px;
        background: white;
        border-radius: 10px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        text-align: center;
    }
    
    .qr-code-container {
        margin: 10px 0;
    }
    
    .qr-data {
        margin-top: 15px;
        font-size: 12px;
        color: #666;
        word-break: break-all;
    }
    """
    
    return QRTemplate(
        title="QR Code",
        description="Generic QR code",
        html=html,
        css=css
    )


# ============================================================================
# TEMPLATE FACTORY
# ============================================================================

def get_template(template_type: str = "generic") -> QRTemplate:
    """
    Get QR template by type.
    
    Args:
        template_type: Template type (certificate, payment, generic)
    
    Returns:
        QRTemplate: Requested template
    """
    templates = {
        "certificate": get_certificate_template,
        "payment": get_payment_template,
        "address": get_payment_template,
        "generic": get_generic_template,
    }
    
    factory = templates.get(template_type, get_generic_template)
    return factory()


# ============================================================================
# EXPORT
# ============================================================================

__all__ = [
    "QRTemplate",
    "get_certificate_template",
    "get_payment_template",
    "get_generic_template",
    "get_template",
]
