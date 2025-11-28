"""
CarbonChain - Compensation Service
====================================
Servizio gestione compensazioni CO2.

Security Level: CRITICAL
Last Updated: 2025-11-27
Version: 1.0.0

Features:
- Compensation transaction creation
- Project registration
- Tracking compensazioni
- Validation rules
"""

from typing import Dict, List, Optional
import time

# Internal imports
from carbon_chain.wallet.hd_wallet import HDWallet
from carbon_chain.domain.models import (
    Transaction,
    TxInput,
    TxOutput,
    UTXOKey,
)
from carbon_chain.domain.blockchain import Blockchain
from carbon_chain.constants import (
    TxType,
    PROJECT_TYPES,
)
from carbon_chain.errors import (
    CompensationError,
    CompensationNotCertifiedError,
    CompensationAlreadyUsedError,
)
from carbon_chain.logging_setup import get_logger, AuditLogger
from carbon_chain.config import ChainSettings


# ============================================================================
# MODULE LOGGER
# ============================================================================

logger = get_logger("compensation_service")
audit_logger = AuditLogger()


# ============================================================================
# COMPENSATION SERVICE
# ============================================================================

class CompensationService:
    """
    Servizio gestione compensazioni CO2.
    
    High-level API per:
    - Creazione transazioni compensazione
    - Tracking progetti
    - Validation rules
    
    Attributes:
        blockchain: Blockchain instance
        config: Chain configuration
    
    Examples:
        >>> service = CompensationService(blockchain, config)
        >>> tx = service.create_compensation_transaction(
        ...     wallet, address_index, project_data, 1000
        ... )
    """
    
    def __init__(self, blockchain: Blockchain, config: ChainSettings):
        self.blockchain = blockchain
        self.config = config
    
    # ========================================================================
    # COMPENSATION CREATION
    # ========================================================================
    
    def create_compensation_transaction(
        self,
        wallet: HDWallet,
        from_address_index: int,
        project_data: Dict,
        amount_kg: int,
        certificate_filter: Optional[str] = None,
        change_address_index: Optional[int] = None
    ) -> Transaction:
        """
        Crea transazione compensazione.
        
        Trasforma coin certificata in coin compensata (non più spendibile).
        
        Args:
            wallet: HD Wallet
            from_address_index: Indice address con coin certificati
            project_data: {
                "project_id": str,
                "project_name": str,
                "location": str,
                "project_type": str,
                "organization": str,
                "start_date": int,
                ... (altri campi)
            }
            amount_kg: Amount kg CO2 da compensare
            certificate_filter: Se specificato, usa solo questo certificato
            change_address_index: Change address index
        
        Returns:
            Transaction: Tx firmata ASSIGN_COMPENSATION
        
        Raises:
            CompensationError: Se validazione fallisce
            CompensationNotCertifiedError: Se coin non certificati
        
        Examples:
            >>> project_data = {
            ...     "project_id": "PROJ-REFORESTATION-2025",
            ...     "project_name": "Amazon Reforestation",
            ...     "location": "Amazon Basin, Brazil",
            ...     "project_type": "reforestation",
            ...     "organization": "Amazon Conservation Fund",
            ...     "start_date": int(time.time())
            ... }
            >>> tx = service.create_compensation_transaction(
            ...     wallet, 0, project_data, 1000
            ... )
        """
        # Validazione project data
        self._validate_project_data(project_data)
        
        from_address = wallet.get_address(from_address_index)
        
        # Select UTXO certificati (solo non compensati)
        selected_utxos = self._select_certified_utxos(
            from_address,
            amount_kg,
            certificate_filter
        )
        
        if not selected_utxos:
            raise CompensationNotCertifiedError(
                f"Insufficient certified coins: need {amount_kg} kg",
                code="INSUFFICIENT_CERTIFIED_COINS"
            )
        
        # Check tutti dalla stessa certificazione (se strict)
        if self.config.enforce_cert_uniqueness and len(selected_utxos) > 1:
            cert_ids = set(output.certificate_id for _, output in selected_utxos)
            if len(cert_ids) > 1 and certificate_filter is None:
                logger.warning(
                    f"Compensation mixing multiple certificates: {cert_ids}",
                    extra_data={"cert_ids": list(cert_ids)}
                )
        
        # Crea input
        inputs = []
        total_input = 0
        used_certificates = set()
        
        for utxo_key, output in selected_utxos:
            inp = TxInput(
                prev_txid=utxo_key.txid,
                prev_output_index=utxo_key.output_index
            )
            inputs.append(inp)
            total_input += output.amount
            used_certificates.add(output.certificate_id)
        
        # Crea output compensato
        # Prendi certificato dal primo UTXO
        first_output = selected_utxos[0][1]
        
        outputs = [
            TxOutput(
                amount=amount_kg,
                address=from_address,
                is_certified=True,
                is_compensated=True,
                certificate_id=first_output.certificate_id,
                certificate_hash=first_output.certificate_hash,
                certificate_total_kg=first_output.certificate_total_kg,
                certificate_metadata=first_output.certificate_metadata,
                compensation_project_id=project_data["project_id"],
                compensation_metadata=project_data
            )
        ]
        
        # Change (certificato, non compensato)
        change = total_input - amount_kg
        if change > 0:
            change_index = change_address_index if change_address_index is not None else from_address_index
            change_address = wallet.get_address(change_index)
            
            outputs.append(
                TxOutput(
                    amount=change,
                    address=change_address,
                    is_certified=True,
                    certificate_id=first_output.certificate_id,
                    certificate_hash=first_output.certificate_hash,
                    certificate_total_kg=first_output.certificate_total_kg,
                    certificate_metadata=first_output.certificate_metadata
                )
            )
        
        # Crea transazione
        tx = Transaction(
            tx_type=TxType.ASSIGN_COMPENSATION,
            inputs=inputs,
            outputs=outputs,
            timestamp=int(time.time()),
            metadata={
                "project_id": project_data["project_id"],
                "certificates_used": list(used_certificates),
                "action": "assign_compensation"
            }
        )
        
        # Firma
        signed_tx = wallet.sign_transaction(tx, from_address)
        
        # Audit log
        audit_logger.log_compensation(
            project_id=project_data["project_id"],
            amount_kg=amount_kg,
            cert_id=first_output.certificate_id,
            txid=signed_tx.compute_txid()
        )
        
        logger.info(
            "Compensation transaction created",
            extra_data={
                "txid": signed_tx.compute_txid()[:16] + "...",
                "project_id": project_data["project_id"],
                "amount_kg": amount_kg,
                "certificates": list(used_certificates)
            }
        )
        
        return signed_tx
    
    def _validate_project_data(self, project_data: Dict) -> None:
        """Valida project data"""
        required_fields = [
            "project_id",
            "project_name",
            "location",
            "project_type",
            "organization"
        ]
        
        for field in required_fields:
            if field not in project_data:
                raise CompensationError(
                    f"Missing required project field: {field}",
                    code="MISSING_PROJECT_FIELD",
                    details={"field": field}
                )
        
        # Validate project type
        if project_data["project_type"] not in PROJECT_TYPES:
            logger.warning(
                f"Unknown project type: {project_data['project_type']}",
                extra_data={
                    "project_type": project_data["project_type"],
                    "valid_types": PROJECT_TYPES
                }
            )
    
    def _select_certified_utxos(
        self,
        address: str,
        target_amount: int,
        certificate_filter: Optional[str] = None
    ) -> List:
        """
        Seleziona UTXO certificati per compensazione.
        
        Args:
            address: Address owner
            target_amount: Amount target
            certificate_filter: Se specificato, usa solo questo certificato
        
        Returns:
            List: Selected UTXO
        """
        all_utxos = self.blockchain.utxo_set.get_utxos_for_address(address)
        
        # Filtra certificati non compensati
        certified_utxos = [
            (key, output)
            for key, output in all_utxos
            if output.is_certified and not output.is_compensated
        ]
        
        # Filtra per certificato se richiesto
        if certificate_filter:
            certified_utxos = [
                (key, output)
                for key, output in certified_utxos
                if output.certificate_id == certificate_filter
            ]
        
        if not certified_utxos:
            return []
        
        # Check no already compensated (double check)
        if self.config.forbid_spending_compensated:
            for key, output in certified_utxos:
                if output.is_compensated:
                    raise CompensationAlreadyUsedError(
                        f"UTXO {key} already compensated",
                        code="UTXO_ALREADY_COMPENSATED"
                    )
        
        # Sort by amount
        sorted_utxos = sorted(
            certified_utxos,
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
    # PROJECT QUERIES
    # ========================================================================
    
    def get_project_info(self, project_id: str) -> Optional[Dict]:
        """
        Ottieni info progetto.
        
        Args:
            project_id: Project ID
        
        Returns:
            dict: Project info {
                "project_id": str,
                "project_name": str (from metadata),
                "total_kg_compensated": int,
                "certificates_used": list,
                "metadata": dict,
                "first_tx": str,
                "first_block": int
            }
        
        Examples:
            >>> info = service.get_project_info("PROJ-REFORESTATION-2025")
            >>> print(f"Compensated: {info['total_kg_compensated']} kg")
        """
        proj_info = self.blockchain.get_project_info(project_id)
        
        if not proj_info:
            return None
        
        # Aggiungi project_name da metadata
        metadata = proj_info.get("metadata", {})
        proj_info["project_name"] = metadata.get("project_name", project_id)
        
        return proj_info
    
    def list_projects(
        self,
        filter_type: Optional[str] = None
    ) -> List[Dict]:
        """
        Lista tutti i progetti.
        
        Args:
            filter_type: Filtra per project_type (None = tutti)
        
        Returns:
            List[dict]: Lista progetti
        
        Examples:
            >>> all_projects = service.list_projects()
            >>> reforestation = service.list_projects("reforestation")
        """
        all_projects = self.blockchain.list_projects()
        
        result = []
        for proj in all_projects:
            proj_info = self.get_project_info(proj["project_id"])
            
            if proj_info:
                # Filter by type se richiesto
                metadata = proj_info.get("metadata", {})
                proj_type = metadata.get("project_type")
                
                if filter_type is None or proj_type == filter_type:
                    result.append(proj_info)
        
        return result
    
    def get_project_statistics(self, project_id: str) -> Dict:
        """
        Ottieni statistiche progetto.
        
        Args:
            project_id: Project ID
        
        Returns:
            dict: {
                "project_id": str,
                "total_kg_compensated": int,
                "total_tonnes": float,
                "certificates_count": int,
                "certificates_list": list
            }
        """
        proj_info = self.get_project_info(project_id)
        
        if not proj_info:
            return {}
        
        total_kg = proj_info["total_kg_compensated"]
        certs = proj_info["certificates_used"]
        
        return {
            "project_id": project_id,
            "total_kg_compensated": total_kg,
            "total_tonnes": round(total_kg / 1000, 3),
            "certificates_count": len(certs),
            "certificates_list": certs
        }
    
    def get_global_compensation_statistics(self) -> Dict:
        """
        Ottieni statistiche compensazioni globali.
        
        Returns:
            dict: {
                "total_projects": int,
                "total_kg_compensated": int,
                "total_tonnes": float,
                "by_type": dict
            }
        """
        all_projects = self.list_projects()
        
        total_kg = sum(p["total_kg_compensated"] for p in all_projects)
        
        # Group by type
        by_type = {}
        for proj in all_projects:
            metadata = proj.get("metadata", {})
            proj_type = metadata.get("project_type", "unknown")
            
            if proj_type not in by_type:
                by_type[proj_type] = {
                    "count": 0,
                    "total_kg": 0
                }
            
            by_type[proj_type]["count"] += 1
            by_type[proj_type]["total_kg"] += proj["total_kg_compensated"]
        
        return {
            "total_projects": len(all_projects),
            "total_kg_compensated": total_kg,
            "total_tonnes": round(total_kg / 1000, 3),
            "by_type": by_type
        }


# ============================================================================
# EXPORT
# ============================================================================

__all__ = [
    "CompensationService",
]
