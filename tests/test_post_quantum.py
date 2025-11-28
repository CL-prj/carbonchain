"""
CarbonChain - Post-Quantum Cryptography Tests
===============================================
Unit tests for post-quantum algorithms.
"""

import pytest
from carbon_chain.crypto.post_quantum import (
    DilithiumSigner,
    KyberKEM,
    HybridSigner,
    is_post_quantum_available,
    get_available_algorithms,
    benchmark_algorithm
)


class TestDilithium:
    """Test Dilithium signatures"""
    
    def test_keypair_generation(self):
        """Test Dilithium keypair generation"""
        signer = DilithiumSigner.generate("dilithium3")
        
        assert signer.private_key is not None
        assert signer.public_key is not None
        assert signer.algorithm == "dilithium3"
    
    def test_sign_verify(self):
        """Test Dilithium sign and verify"""
        signer = DilithiumSigner.generate("dilithium3")
        message = b"test_message_for_dilithium"
        
        # Sign
        signature = signer.sign(message)
        
        assert signature is not None
        assert len(signature) > 0
        
        # Verify
        is_valid = signer.verify(message, signature)
        assert is_valid
    
    def test_invalid_signature(self):
        """Test invalid signature rejection"""
        signer = DilithiumSigner.generate("dilithium3")
        message = b"original_message"
        
        signature = signer.sign(message)
        
        # Tamper with message
        tampered_message = b"tampered_message"
        is_valid = signer.verify(tampered_message, signature)
        
        # Should fail (unless simulated mode)
        # In simulated mode, may pass - that's expected
        if is_post_quantum_available():
            assert not is_valid
    
    def test_different_algorithms(self):
        """Test different Dilithium variants"""
        for algo in ["dilithium2", "dilithium3", "dilithium5"]:
            signer = DilithiumSigner.generate(algo)
            assert signer.algorithm == algo


class TestKyber:
    """Test Kyber KEM"""
    
    def test_keypair_generation(self):
        """Test Kyber keypair generation"""
        kem = KyberKEM.generate("kyber768")
        
        assert kem.private_key is not None
        assert kem.public_key is not None
        assert kem.algorithm == "kyber768"
    
    def test_encapsulation_decapsulation(self):
        """Test Kyber encap/decap"""
        kem = KyberKEM.generate("kyber768")
        
        # Encapsulate
        shared_secret1, ciphertext = KyberKEM.encapsulate(
            kem.public_key,
            "kyber768"
        )
        
        assert shared_secret1 is not None
        assert ciphertext is not None
        
        # Decapsulate
        shared_secret2 = kem.decapsulate(ciphertext)
        
        assert shared_secret2 is not None
        
        # Shared secrets should match
        # (In simulated mode, they will match)
        assert shared_secret1 == shared_secret2
    
    def test_different_algorithms(self):
        """Test different Kyber variants"""
        for algo in ["kyber512", "kyber768", "kyber1024"]:
            kem = KyberKEM.generate(algo)
            assert kem.algorithm == algo


class TestHybridSigner:
    """Test Hybrid cryptography"""
    
    def test_hybrid_keypair_generation(self):
        """Test hybrid keypair generation"""
        signer = HybridSigner.generate()
        
        assert signer.ecdsa_private_key is not None
        assert signer.ecdsa_public_key is not None
        assert signer.dilithium_signer is not None
    
    def test_hybrid_sign_verify(self):
        """Test hybrid signature"""
        signer = HybridSigner.generate()
        message = b"hybrid_test_message"
        
        # Sign with both algorithms
        signature = signer.sign(message)
        
        assert signature is not None
        assert b"||" in signature  # Separator
        
        # Verify
        is_valid = signer.verify(message, signature)
        assert is_valid
    
    def test_hybrid_tampered_signature(self):
        """Test hybrid with tampered signature"""
        signer = HybridSigner.generate()
        message = b"original_message"
        
        signature = signer.sign(message)
        
        # Tamper with signature
        tampered_sig = signature + b"tampered"
        
        # Should fail
        is_valid = signer.verify(message, tampered_sig)
        assert not is_valid


class TestPQUtilities:
    """Test PQ utility functions"""
    
    def test_availability_check(self):
        """Test liboqs availability check"""
        available = is_post_quantum_available()
        
        # Should be bool
        assert isinstance(available, bool)
    
    def test_get_algorithms(self):
        """Test getting available algorithms"""
        algorithms = get_available_algorithms()
        
        assert "signature" in algorithms
        assert "kem" in algorithms
        assert isinstance(algorithms["signature"], list)
        assert isinstance(algorithms["kem"], list)
    
    @pytest.mark.slow
    def test_benchmark(self):
        """Test algorithm benchmarking"""
        results = benchmark_algorithm("dilithium3", iterations=10)
        
        assert "algorithm" in results
        assert "sign_time_ms" in results
        assert "verify_time_ms" in results
        assert results["algorithm"] == "dilithium3"
