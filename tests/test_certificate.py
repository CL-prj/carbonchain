"""
CarbonChain - Certificate Tests
=================================
Unit tests for certificate functionality.
"""

import pytest
from carbon_chain.services.certificate_service import CertificateService
from carbon_chain.errors import CertificateError


class TestCertificateService:
    """Test CertificateService"""
    
    def test_certificate_assignment(
        self,
        blockchain,
        mempool,
        funded_wallet,
        sample_certificate_data,
        test_config
    ):
        """Test certificate assignment to coins"""
        cert_service = CertificateService(blockchain, test_config)
        
        # Create certificate assignment
        tx = cert_service.create_certificate_assignment(
            wallet=funded_wallet,
            from_address_index=0,
            certificate_data=sample_certificate_data,
            amount_kg=5000
        )
        
        assert tx is not None
        assert tx.is_certificate_assignment()
        
        # Check certified output
        certified_outputs = [o for o in tx.outputs if o.is_certified]
        assert len(certified_outputs) > 0
        assert certified_outputs[0].certificate_id == sample_certificate_data["certificate_id"]
    
    def test_certificate_validation(
        self,
        blockchain,
        test_config,
        sample_certificate_data
    ):
        """Test certificate data validation"""
        cert_service = CertificateService(blockchain, test_config)
        
        # Missing required field
        invalid_cert = sample_certificate_data.copy()
        del invalid_cert["location"]
        
        with pytest.raises(CertificateError):
            cert_service._validate_certificate_data(invalid_cert)
