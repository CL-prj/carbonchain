"""
CarbonChain - Project Service
===============================
Servizio gestione progetti compensazione.

Security Level: MEDIUM
Last Updated: 2025-11-27
Version: 1.0.0

Features:
- Project registration
- Project queries
- Statistics
"""

from typing import Dict, List, Optional

# Internal imports
from carbon_chain.domain.blockchain import Blockchain
from carbon_chain.constants import PROJECT_TYPES
from carbon_chain.errors import ValidationError
from carbon_chain.logging_setup import get_logger
from carbon_chain.config import ChainSettings


# ============================================================================
# MODULE LOGGER
# ============================================================================

logger = get_logger("project_service")


# ============================================================================
# PROJECT SERVICE
# ============================================================================

class ProjectService:
    """
    Servizio gestione progetti.
    
    Query e analytics per progetti compensazione.
    
    Attributes:
        blockchain: Blockchain instance
        config: Chain configuration
    
    Examples:
        >>> service = ProjectService(blockchain, config)
        >>> info = service.get_project_info("PROJ-001")
    """
    
    def __init__(self, blockchain: Blockchain, config: ChainSettings):
        self.blockchain = blockchain
        self.config = config
    
    # ========================================================================
    # PROJECT QUERIES
    # ========================================================================
    
    def get_project_info(self, project_id: str) -> Optional[Dict]:
        """
        Ottieni info progetto completo.
        
        Args:
            project_id: Project ID
        
        Returns:
            dict: Project info
        """
        return self.blockchain.get_project_info(project_id)
    
    def list_projects(
        self,
        filter_type: Optional[str] = None,
        min_kg: Optional[int] = None
    ) -> List[Dict]:
        """
        Lista progetti con filtri.
        
        Args:
            filter_type: Filtra per tipo
            min_kg: Kg compensati minimi
        
        Returns:
            List[dict]: Lista progetti
        """
        all_projects = self.blockchain.list_projects()
        
        result = []
        for proj in all_projects:
            # Filter by type
            if filter_type:
                metadata = proj.get("metadata", {})
                if metadata.get("project_type") != filter_type:
                    continue
            
            # Filter by min_kg
            if min_kg:
                if proj["total_kg_compensated"] < min_kg:
                    continue
            
            result.append(proj)
        
        return result
    
    def get_top_projects(self, limit: int = 10) -> List[Dict]:
        """
        Ottieni top progetti per kg compensati.
        
        Args:
            limit: Numero progetti
        
        Returns:
            List[dict]: Top progetti
        """
        all_projects = self.blockchain.list_projects()
        
        # Sort by total_kg_compensated
        sorted_projects = sorted(
            all_projects,
            key=lambda p: p["total_kg_compensated"],
            reverse=True
        )
        
        return sorted_projects[:limit]
    
    def get_projects_by_type(self) -> Dict[str, List[Dict]]:
        """
        Group progetti per tipo.
        
        Returns:
            dict: {project_type: [projects]}
        """
        all_projects = self.blockchain.list_projects()
        
        by_type = {}
        for proj in all_projects:
            metadata = proj.get("metadata", {})
            proj_type = metadata.get("project_type", "unknown")
            
            if proj_type not in by_type:
                by_type[proj_type] = []
            
            by_type[proj_type].append(proj)
        
        return by_type
    
    # ========================================================================
    # STATISTICS
    # ========================================================================
    
    def get_project_statistics(self, project_id: str) -> Dict:
        """Statistiche singolo progetto"""
        proj_info = self.get_project_info(project_id)
        
        if not proj_info:
            return {}
        
        metadata = proj_info.get("metadata", {})
        
        return {
            "project_id": project_id,
            "project_name": metadata.get("project_name", project_id),
            "total_kg_compensated": proj_info["total_kg_compensated"],
            "total_tonnes": round(proj_info["total_kg_compensated"] / 1000, 3),
            "certificates_used": len(proj_info["certificates_used"]),
            "location": metadata.get("location", "N/A"),
            "organization": metadata.get("organization", "N/A"),
            "project_type": metadata.get("project_type", "unknown")
        }
    
    def get_global_statistics(self) -> Dict:
        """Statistiche globali progetti"""
        all_projects = self.blockchain.list_projects()
        
        if not all_projects:
            return {
                "total_projects": 0,
                "total_kg_compensated": 0,
                "total_tonnes": 0,
                "by_type": {}
            }
        
        total_kg = sum(p["total_kg_compensated"] for p in all_projects)
        
        # By type
        by_type = {}
        for proj in all_projects:
            metadata = proj.get("metadata", {})
            proj_type = metadata.get("project_type", "unknown")
            
            if proj_type not in by_type:
                by_type[proj_type] = {
                    "count": 0,
                    "total_kg": 0,
                    "avg_kg": 0
                }
            
            by_type[proj_type]["count"] += 1
            by_type[proj_type]["total_kg"] += proj["total_kg_compensated"]
        
        # Calcola average
        for proj_type, stats in by_type.items():
            stats["avg_kg"] = stats["total_kg"] // stats["count"] if stats["count"] > 0 else 0
        
        return {
            "total_projects": len(all_projects),
            "total_kg_compensated": total_kg,
            "total_tonnes": round(total_kg / 1000, 3),
            "by_type": by_type
        }
    
    def validate_project_data(self, project_data: Dict) -> bool:
        """
        Valida project data.
        
        Args:
            project_data: Project data da validare
        
        Returns:
            bool: True se valido
        
        Raises:
            ValidationError: Se validazione fallisce
        """
        required = ["project_id", "project_name", "location", "project_type", "organization"]
        
        for field in required:
            if field not in project_data:
                raise ValidationError(
                    f"Missing required field: {field}",
                    code="MISSING_FIELD",
                    details={"field": field}
                )
        
        # Validate type
        if project_data["project_type"] not in PROJECT_TYPES:
            logger.warning(
                f"Unknown project type: {project_data['project_type']}",
                extra_data={"valid_types": PROJECT_TYPES}
            )
        
        return True


# ============================================================================
# EXPORT
# ============================================================================

__all__ = [
    "ProjectService",
]
