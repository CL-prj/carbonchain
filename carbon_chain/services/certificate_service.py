"""
CarbonChain - Certificate Service
===================================
Servizio gestione certificati CO2.

Security Level: CRITICAL
Last Updated: 2025-11-27
Version: 1.0.0

Features:
- Certificate creation/assignment
- Certificate validation
- Capacity tracking
- Query API
"""

from typing import Dict, List, Optional
import time

# Internal imports
from carbon_chain.wallet.hd_wallet import HDWallet
from carbon_chain.domain.models import (
    Transaction,
    TxInput,
    TxOutput,
)
from carbon_chain.domain.blockchain import Blockchain
from carbon_chain.domain.crypto_core import compute_certificate_hash
from carbon_chain.constants import (
    TxType,
    CertificateState,
    REQUIRED_CERT_FIELDS,
)
from carbon_chain.errors import (
    CertificateError,
    CertificateDuplicateError,
    CertificateExhaustedError,
)
from carbon_chain.logging_setup import get_logger, AuditLogger
from carbon_chain.config import ChainSettings


# ============================================================================
# MODULE LOGGER
# ============================================================================

logger = get_logger("certificate_service")
audit_logger = AuditLogger()


# ============================================================================
# CERTIFICATE SERVICE
# ============================================================================

class CertificateService:
    """
    Servizio gestione certificati CO2.
    
    High-level API per:
    - Creazione certificati
    - Assignment a coin
    - Tracking capacità
    - Query certificati
    
    Attributes:
        blockchain: Blockchain instance
        config: Chain configuration
    
    Examples:
        >>> service = CertificateService(blockchain, config)
        >>> tx = service.create_certificate_assignment(wallet, address, cert_data, 100)
    """
    
    def __init__(self, blockchain: Blockchain, config: ChainSettings):
        self.blockchain = blockchain
        self.config = config
    
    # ========================================================================
    # CERTIFICATE CREATION
    # ========================================================================
    
    def create_certificate_assignment(
        self,
        wallet: HDWallet,
        from_address_index: int,
        certificate_data: Dict,
        amount_kg: int,
        change_address_index: Optional[int] = None
    ) -> Transaction:
        """
        Crea transazione assignment certificato.
        
        Trasforma coin standard in coin certificata.
        
        Args:
            wallet: HD Wallet
            from_address_index: Indice address con coin da certificare
            certificate_data: {
                "certificate_id": str,
                "total_kg": int,
                "location": str,
                "description": str,
                "issuer": str,
                "issue_date": int,
                ... (altri campi opzionali)
            }
            amount_kg: Amount kg CO2 da certificare (Satoshi)
            change_address_index: Change address index
        
        Returns:
            Transaction: Tx firmata ASSIGN_CERT
        
        Raises:
            CertificateError: Se certificato invalido
        
        Examples:
            >>> cert_data = {
            ...     "certificate_id": "CERT-2025-001",
            ...     "total_kg": 10000,
            ...     "location": "Solar Farm, Portugal",
            ...     "description": "10t CO2 avoided via solar energy",
            ...     "issuer": "GreenCorp",
            ...     "issue_date": int(time.time())
            ... }
            >>> tx = service.create_certificate_assignment(
            ...     wallet, 0, cert_data, 10000
            ... )
        """
        # Validazione certificate data
        self._validate_certificate_data(certificate_data)
        
        # Check amount non supera total
        if amount_kg > certificate_data["total_kg"]:
            raise CertificateError(
                f"Amount {amount_kg} exceeds certificate total_kg {certificate_data['total_kg']}",
                code="AMOUNT_EXCEEDS_TOTAL"
            )
        
        # Calcola certificate hash (deterministico)
        cert_hash = compute_certificate_hash(
            cert_id=certificate_data["certificate_id"],
            total_kg=certificate_data["total_kg"],
            location=certificate_data["location"],
            description=certificate_data["description"],
            timestamp=certificate_data["issue_date"],
            issuer=certificate_data.get("issuer", ""),
            extra_data=certificate_data
        )
        
        from_address = wallet.get_address(from_address_index)
        
        # Select UTXO (solo standard, no certificati)
        selected_utxos = self._select_standard_utxos(from_address, amount_kg)
        
        if not selected_utxos:
            raise CertificateError(
                f"Insufficient standard coins: need {amount_kg}",
                code="INSUFFICIENT_STANDARD_COINS"
            )
        
        # Crea input
        inputs = []
        total_input = 0
        
        for utxo_key, output in selected_utxos:
            inp = TxInput(
                prev_txid=utxo_key.txid,
                prev_output_index=utxo_key.output_index
            )
            inputs.append(inp)
            total_input += output.amount
        
        # Crea output certificato
        outputs = [
            TxOutput(
                amount=amount_kg,
                address=from_address,  # Mantieni stesso address
                is_certified=True,
                certificate_id=certificate_data["certificate_id"],
                certificate_hash=cert_hash,
                certificate_total_kg=certificate_data["total_kg"],
                certificate_metadata=certificate_data
            )
        ]
        
        # Change (standard)
        change = total_input - amount_kg
        if change > 0:
            change_index = change_address_index if change_address_index is not None else from_address_index
            change_address = wallet.get_address(change_index)
            
            outputs.append(
                TxOutput(
                    amount=change,
                    address=change_address
                )
            )
        
        # Crea transazione
        tx = Transaction(
            tx_type=TxType.ASSIGN_CERT,
            inputs=inputs,
            outputs=outputs,
            timestamp=int(time.time()),
            metadata={
                "certificate_id": certificate_data["certificate_id"],
                "action": "assign_certificate"
            }
        )
        
        # Firma
        signed_tx = wallet.sign_transaction(tx, from_address)
        
        # Audit log
        audit_logger.log_certificate_creation(
            cert_id=certificate_data["certificate_id"],
            total_kg=certificate_data["total_kg"],
            issuer=certificate_data.get("issuer", ""),
            txid=signed_tx.compute_txid()
        )
        
        logger.info(
            "Certificate assignment transaction created",
            extra_data={
                "txid": signed_tx.compute_txid()[:16] + "...",
                "cert_id": certificate_data["certificate_id"],
                "amount_kg": amount_kg
            }
        )
        
        return signed_tx
    
    def _validate_certificate_data(self, cert_data: Dict) -> None:
        """Valida certificate data"""
        # Check required fields
        for field in REQUIRED_CERT_FIELDS:
            if field not in cert_data:
                raise CertificateError(
                    f"Missing required certificate field: {field}",
                    code="MISSING_CERT_FIELD",
                    details={"field": field}
                )
        
        # Validate types
        if not isinstance(cert_data["total_kg"], int) or cert_data["total_kg"] <= 0:
            raise CertificateError(
                "total_kg must be positive integer",
                code="INVALID_TOTAL_KG"
            )
        
        if not isinstance(cert_data["certificate_id"], str) or not cert_data["certificate_id"]:
            raise CertificateError(
                "certificate_id must be non-empty string",
                code="INVALID_CERT_ID"
            )
    
    def _select_standard_utxos(
        self,
        address: str,
        target_amount: int
    ) -> List:
        """Seleziona UTXO standard (no certificati)"""
        all_utxos = self.blockchain.utxo_set.get_spendable_utxos_for_address(address)
        
        # Filtra solo standard
        standard_utxos = [
            (key, output)
            for key, output in all_utxos
            if not output.is_certified
        ]
        
        if not standard_utxos:
            return []
        
        # Sort by amount
        sorted_utxos = sorted(
            standard_utxos,
            key=lambda x: x[1].amount,
            reverse=True
        )
        
        # Select
        selected = []
        total = 0
        
        for utxo_key, output in sorted_utxos:
            selected.append((utxo_key, output))
            total += output.amount
            
            if total >= target_amount:
                break
        
        return selected if total >= target_amount else []
    
    # ========================================================================
    # CERTIFICATE QUERIES
    # ========================================================================
    
    def get_certificate_info(self, cert_id: str) -> Optional[Dict]:
        """
        Ottieni info certificato.
        
        Args:
            cert_id: Certificate ID
        
        Returns:
            dict: Certificate info {
                "certificate_id": str,
                "total_kg": int,
                "issued_kg": int,
                "compensated_kg": int,
                "remaining_kg": int,
                "state": str,
                "metadata": dict,
                "first_tx": str,
                "first_block": int
            }
        
        Examples:
            >>> info = service.get_certificate_info("CERT-2025-001")
            >>> print(f"Issued: {info['issued_kg']} kg")
        """
        cert_info = self.blockchain.get_certificate_info(cert_id)
        
        if not cert_info:
            return None
        
        # Calcola remaining e state
        issued = cert_info["issued_kg"]
        compensated = cert_info["compensated_kg"]
        total = cert_info["total_kg"]
        remaining = total - issued
        
        # Determina state
        if compensated >= issued:
            state = CertificateState.FULLY_COMPENSATED
        elif compensated > 0:
            state = CertificateState.PARTIALLY_COMPENSATED
        else:
            state = CertificateState.ACTIVE
        
        return {
            **cert_info,
            "remaining_kg": remaining,
            "state": state.value
        }
    
    def list_certificates(
        self,
        filter_state: Optional[CertificateState] = None
    ) -> List[Dict]:
        """
        Lista tutti i certificati.
        
        Args:
            filter_state: Filtra per state (None = tutti)
        
        Returns:
            List[dict]: Lista certificati
        
        Examples:
            >>> certs = service.list_certificates()
            >>> active = service.list_certificates(CertificateState.ACTIVE)
        """
        all_certs = self.blockchain.list_certificates()
        
        result = []
        for cert in all_certs:
            cert_info = self.get_certificate_info(cert["certificate_id"])
            
            if cert_info:
                # Filter by state se richiesto
                if filter_state is None or cert_info["state"] == filter_state.value:
                    result.append(cert_info)
        
        return result
    
    def get_certificate_utilization(self, cert_id: str) -> Dict:
        """
        Ottieni statistiche utilizzo certificato.
        
        Args:
            cert_id: Certificate ID
        
        Returns:
            dict: {
                "total_kg": int,
                "issued_kg": int,
                "compensated_kg": int,
                "utilization_pct": float,
                "compensation_pct": float
            }
        """
        cert_info = self.get_certificate_info(cert_id)
        
        if not cert_info:
            return {}
        
        total = cert_info["total_kg"]
        issued = cert_info["issued_kg"]
        compensated = cert_info["compensated_kg"]
        
        utilization_pct = (issued / total * 100) if total > 0 else 0
        compensation_pct = (compensated / issued * 100) if issued > 0 else 0
        
        return {
            "total_kg": total,
            "issued_kg": issued,
            "compensated_kg": compensated,
            "utilization_pct": round(utilization_pct, 2),
            "compensation_pct": round(compensation_pct, 2)
        }


# ============================================================================
# EXPORT
# ============================================================================

__all__ = [
    "CertificateService",
]
