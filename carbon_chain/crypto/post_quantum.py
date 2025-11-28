"""
CarbonChain - Post-Quantum Cryptography
=========================================
Quantum-resistant cryptographic algorithms.

Security Level: CRITICAL
Last Updated: 2025-11-27
Version: 1.0.0

Algorithms:
- Dilithium (Digital Signatures)
- Kyber (Key Encapsulation)
- Hybrid mode (ECDSA + Dilithium)

Note: Requires liboqs-python for full functionality.
"""

from __future__ import annotations
from typing import Tuple, Optional
from dataclasses import dataclass
import hashlib

# Internal imports
from carbon_chain.errors import CryptoError, NotImplementedError
from carbon_chain.logging_setup import get_logger


# ============================================================================
# MODULE LOGGER
# ============================================================================

logger = get_logger("crypto.post_quantum")


# ============================================================================
# POST-QUANTUM CONFIGURATION
# ============================================================================

@dataclass
class PQConfig:
    """
    Post-quantum crypto configuration.
    
    Attributes:
        algorithm: Algorithm name (dilithium2, dilithium3, dilithium5)
        hybrid_mode: Use hybrid ECDSA + PQ
        kem_algorithm: Key encapsulation algorithm (kyber512, kyber768, kyber1024)
    """
    
    algorithm: str = "dilithium3"
    hybrid_mode: bool = True
    kem_algorithm: str = "kyber768"


# ============================================================================
# DILITHIUM (Digital Signatures)
# ============================================================================

class DilithiumSigner:
    """
    Dilithium post-quantum digital signature scheme.
    
    NIST PQC standardized algorithm for digital signatures.
    Resistant to quantum attacks (Shor's algorithm).
    
    Security Levels:
    - Dilithium2: NIST Level 2 (~AES-128)
    - Dilithium3: NIST Level 3 (~AES-192) [Default]
    - Dilithium5: NIST Level 5 (~AES-256)
    
    Examples:
        >>> signer = DilithiumSigner.generate()
        >>> signature = signer.sign(message)
        >>> is_valid = signer.verify(message, signature)
    """
    
    def __init__(
        self,
        private_key: bytes,
        public_key: bytes,
        algorithm: str = "dilithium3"
    ):
        """
        Initialize Dilithium signer.
        
        Args:
            private_key: Private key bytes
            public_key: Public key bytes
            algorithm: Algorithm variant
        """
        self.private_key = private_key
        self.public_key = public_key
        self.algorithm = algorithm
        
        # Try to import liboqs
        self._oqs_available = False
        try:
            import oqs
            self._oqs = oqs
            self._oqs_available = True
            logger.info(f"liboqs available - using {algorithm}")
        except ImportError:
            logger.warning(
                "liboqs not available - using simulated post-quantum crypto. "
                "Install liboqs-python for production use."
            )
    
    @classmethod
    def generate(cls, algorithm: str = "dilithium3") -> DilithiumSigner:
        """
        Generate new Dilithium keypair.
        
        Args:
            algorithm: Algorithm variant (dilithium2, dilithium3, dilithium5)
        
        Returns:
            DilithiumSigner: New signer instance
        """
        signer = cls(b'', b'', algorithm)
        
        if signer._oqs_available:
            # Use liboqs
            sig = signer._oqs.Signature(algorithm)
            public_key = sig.generate_keypair()
            private_key = sig.export_secret_key()
            
            return cls(private_key, public_key, algorithm)
        else:
            # Simulated keypair (NOT SECURE - for testing only)
            private_key = hashlib.sha256(b"simulated_private_key").digest()
            public_key = hashlib.sha256(private_key + b"_public").digest()
            
            return cls(private_key, public_key, algorithm)
    
    def sign(self, message: bytes) -> bytes:
        """
        Sign message with Dilithium.
        
        Args:
            message: Message to sign
        
        Returns:
            bytes: Signature
        """
        if self._oqs_available:
            sig = self._oqs.Signature(self.algorithm, self.private_key)
            signature = sig.sign(message)
            return signature
        else:
            # Simulated signature (NOT SECURE)
            sig_data = hashlib.sha512(message + self.private_key).digest()
            return sig_data
    
    def verify(
        self,
        message: bytes,
        signature: bytes,
        public_key: Optional[bytes] = None
    ) -> bool:
        """
        Verify Dilithium signature.
        
        Args:
            message: Original message
            signature: Signature to verify
            public_key: Public key (optional, uses instance key if None)
        
        Returns:
            bool: True if valid
        """
        pk = public_key or self.public_key
        
        if self._oqs_available:
            sig = self._oqs.Signature(self.algorithm)
            return sig.verify(message, signature, pk)
        else:
            # Simulated verification (NOT SECURE)
            expected = hashlib.sha512(message + self.private_key).digest()
            return signature == expected
    
    def export_keys(self) -> Tuple[bytes, bytes]:
        """Export keypair"""
        return self.private_key, self.public_key
    
    def get_signature_size(self) -> int:
        """Get signature size for this algorithm"""
        sizes = {
            "dilithium2": 2420,
            "dilithium3": 3293,
            "dilithium5": 4595
        }
        return sizes.get(self.algorithm, 3293)


# ============================================================================
# KYBER (Key Encapsulation Mechanism)
# ============================================================================

class KyberKEM:
    """
    Kyber post-quantum key encapsulation mechanism.
    
    NIST PQC standardized algorithm for key exchange.
    
    Security Levels:
    - Kyber512: NIST Level 1 (~AES-128)
    - Kyber768: NIST Level 3 (~AES-192) [Default]
    - Kyber1024: NIST Level 5 (~AES-256)
    
    Examples:
        >>> # Server side
        >>> kem = KyberKEM.generate()
        >>> public_key = kem.public_key
        
        >>> # Client side
        >>> shared_secret, ciphertext = KyberKEM.encapsulate(public_key)
        
        >>> # Server side
        >>> shared_secret = kem.decapsulate(ciphertext)
    """
    
    def __init__(
        self,
        private_key: bytes,
        public_key: bytes,
        algorithm: str = "kyber768"
    ):
        """
        Initialize Kyber KEM.
        
        Args:
            private_key: Private key
            public_key: Public key
            algorithm: Algorithm variant
        """
        self.private_key = private_key
        self.public_key = public_key
        self.algorithm = algorithm
        
        # Try to import liboqs
        self._oqs_available = False
        try:
            import oqs
            self._oqs = oqs
            self._oqs_available = True
        except ImportError:
            logger.warning("liboqs not available - using simulated KEM")
    
    @classmethod
    def generate(cls, algorithm: str = "kyber768") -> KyberKEM:
        """
        Generate new Kyber keypair.
        
        Args:
            algorithm: Algorithm variant
        
        Returns:
            KyberKEM: New KEM instance
        """
        kem = cls(b'', b'', algorithm)
        
        if kem._oqs_available:
            kem_obj = kem._oqs.KeyEncapsulation(algorithm)
            public_key = kem_obj.generate_keypair()
            private_key = kem_obj.export_secret_key()
            
            return cls(private_key, public_key, algorithm)
        else:
            # Simulated keypair
            private_key = hashlib.sha256(b"simulated_kem_private").digest()
            public_key = hashlib.sha256(private_key + b"_public").digest()
            
            return cls(private_key, public_key, algorithm)
    
    @staticmethod
    def encapsulate(
        public_key: bytes,
        algorithm: str = "kyber768"
    ) -> Tuple[bytes, bytes]:
        """
        Encapsulate shared secret.
        
        Args:
            public_key: Recipient's public key
            algorithm: Algorithm variant
        
        Returns:
            Tuple: (shared_secret, ciphertext)
        """
        try:
            import oqs
            kem = oqs.KeyEncapsulation(algorithm)
            ciphertext, shared_secret = kem.encap_secret(public_key)
            return shared_secret, ciphertext
        except ImportError:
            # Simulated encapsulation
            shared_secret = hashlib.sha256(public_key + b"_shared").digest()
            ciphertext = hashlib.sha256(shared_secret + b"_cipher").digest()
            return shared_secret, ciphertext
    
    def decapsulate(self, ciphertext: bytes) -> bytes:
        """
        Decapsulate shared secret.
        
        Args:
            ciphertext: Ciphertext from encapsulation
        
        Returns:
            bytes: Shared secret
        """
        if self._oqs_available:
            kem = self._oqs.KeyEncapsulation(self.algorithm, self.private_key)
            shared_secret = kem.decap_secret(ciphertext)
            return shared_secret
        else:
            # Simulated decapsulation
            shared_secret = hashlib.sha256(self.public_key + b"_shared").digest()
            return shared_secret


# ============================================================================
# HYBRID CRYPTO (ECDSA + Dilithium)
# ============================================================================

class HybridSigner:
    """
    Hybrid cryptography: ECDSA + Dilithium.
    
    Provides both classical and post-quantum security.
    If one algorithm is broken, the other still protects.
    
    Examples:
        >>> signer = HybridSigner.generate()
        >>> signature = signer.sign(message)
        >>> is_valid = signer.verify(message, signature)
    """
    
    def __init__(
        self,
        ecdsa_private_key: bytes,
        ecdsa_public_key: bytes,
        dilithium_signer: DilithiumSigner
    ):
        """
        Initialize hybrid signer.
        
        Args:
            ecdsa_private_key: ECDSA private key
            ecdsa_public_key: ECDSA public key
            dilithium_signer: Dilithium signer instance
        """
        self.ecdsa_private_key = ecdsa_private_key
        self.ecdsa_public_key = ecdsa_public_key
        self.dilithium_signer = dilithium_signer
    
    @classmethod
    def generate(cls) -> HybridSigner:
        """
        Generate new hybrid keypair.
        
        Returns:
            HybridSigner: New hybrid signer
        """
        # Generate ECDSA keypair
        from carbon_chain.domain.crypto_core import generate_keypair
        ecdsa_sk, ecdsa_pk = generate_keypair()
        
        # Generate Dilithium keypair
        dilithium = DilithiumSigner.generate()
        
        return cls(ecdsa_sk, ecdsa_pk, dilithium)
    
    def sign(self, message: bytes) -> bytes:
        """
        Sign with both ECDSA and Dilithium.
        
        Args:
            message: Message to sign
        
        Returns:
            bytes: Combined signature
        """
        # ECDSA signature
        from carbon_chain.domain.crypto_core import sign_message
        ecdsa_sig = sign_message(message, self.ecdsa_private_key)
        
        # Dilithium signature
        dilithium_sig = self.dilithium_signer.sign(message)
        
        # Combine signatures
        combined = ecdsa_sig + b"||" + dilithium_sig
        
        return combined
    
    def verify(
        self,
        message: bytes,
        signature: bytes
    ) -> bool:
        """
        Verify hybrid signature.
        
        Args:
            message: Original message
            signature: Combined signature
        
        Returns:
            bool: True if both signatures valid
        """
        # Split signature
        parts = signature.split(b"||")
        if len(parts) != 2:
            return False
        
        ecdsa_sig, dilithium_sig = parts
        
        # Verify ECDSA
        from carbon_chain.domain.crypto_core import verify_signature
        ecdsa_valid = verify_signature(message, ecdsa_sig, self.ecdsa_public_key)
        
        # Verify Dilithium
        dilithium_valid = self.dilithium_signer.verify(message, dilithium_sig)
        
        # Both must be valid
        return ecdsa_valid and dilithium_valid


# ============================================================================
# POST-QUANTUM UTILITIES
# ============================================================================

def is_post_quantum_available() -> bool:
    """
    Check if liboqs is available.
    
    Returns:
        bool: True if liboqs installed
    """
    try:
        import oqs
        return True
    except ImportError:
        return False


def get_available_algorithms() -> dict:
    """
    Get available PQ algorithms.
    
    Returns:
        dict: Available algorithms by category
    """
    algorithms = {
        "signature": ["dilithium2", "dilithium3", "dilithium5"],
        "kem": ["kyber512", "kyber768", "kyber1024"]
    }
    
    if is_post_quantum_available():
        import oqs
        algorithms["signature_available"] = oqs.get_enabled_sig_mechanisms()
        algorithms["kem_available"] = oqs.get_enabled_kem_mechanisms()
    
    return algorithms


def benchmark_algorithm(algorithm: str, iterations: int = 100) -> dict:
    """
    Benchmark post-quantum algorithm.
    
    Args:
        algorithm: Algorithm name
        iterations: Number of iterations
    
    Returns:
        dict: Benchmark results
    """
    import time
    
    results = {
        "algorithm": algorithm,
        "iterations": iterations
    }
    
    if "dilithium" in algorithm:
        # Benchmark signature
        signer = DilithiumSigner.generate(algorithm)
        message = b"test_message_for_benchmark"
        
        # Sign timing
        start = time.time()
        for _ in range(iterations):
            signature = signer.sign(message)
        sign_time = time.time() - start
        
        # Verify timing
        start = time.time()
        for _ in range(iterations):
            signer.verify(message, signature)
        verify_time = time.time() - start
        
        results.update({
            "sign_time_ms": (sign_time / iterations) * 1000,
            "verify_time_ms": (verify_time / iterations) * 1000,
            "signature_size": len(signature)
        })
    
    elif "kyber" in algorithm:
        # Benchmark KEM
        kem = KyberKEM.generate(algorithm)
        
        # Encapsulation timing
        start = time.time()
        for _ in range(iterations):
            shared_secret, ciphertext = KyberKEM.encapsulate(kem.public_key, algorithm)
        encap_time = time.time() - start
        
        # Decapsulation timing
        start = time.time()
        for _ in range(iterations):
            kem.decapsulate(ciphertext)
        decap_time = time.time() - start
        
        results.update({
            "encap_time_ms": (encap_time / iterations) * 1000,
            "decap_time_ms": (decap_time / iterations) * 1000,
            "ciphertext_size": len(ciphertext)
        })
    
    return results


# ============================================================================
# EXPORT
# ============================================================================

__all__ = [
    "PQConfig",
    "DilithiumSigner",
    "KyberKEM",
    "HybridSigner",
    "is_post_quantum_available",
    "get_available_algorithms",
    "benchmark_algorithm",
]
