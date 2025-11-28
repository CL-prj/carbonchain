"""
CarbonChain - MultiSig Tests
==============================
Unit tests for multi-signature wallets.
"""

import pytest
from carbon_chain.wallet.multisig import (
    MultiSigConfig,
    MultiSigWallet,
    PSBT,
    PartialSignature
)
from carbon_chain.domain.crypto_core import generate_keypair


class TestMultiSigConfig:
    """Test MultiSigConfig"""
    
    def test_config_creation(self):
        """Test multisig config creation"""
        # Generate public keys
        pk1 = generate_keypair()[1]
        pk2 = generate_keypair()[1]
        pk3 = generate_keypair()[1]
        
        config = MultiSigConfig(
            m=2,
            n=3,
            public_keys=[pk1, pk2, pk3]
        )
        
        assert config.m == 2
        assert config.n == 3
        assert len(config.public_keys) == 3
        assert config.script_hash is not None
    
    def test_config_validation(self):
        """Test config validation"""
        pk1 = generate_keypair()[1]
        
        # M > N should fail
        with pytest.raises(Exception):
            MultiSigConfig(m=3, n=2, public_keys=[pk1, pk1])
        
        # Wrong number of public keys
        with pytest.raises(Exception):
            MultiSigConfig(m=2, n=3, public_keys=[pk1])
    
    def test_p2sh_address_generation(self):
        """Test P2SH address generation"""
        pk1 = generate_keypair()[1]
        pk2 = generate_keypair()[1]
        
        config = MultiSigConfig(m=2, n=2, public_keys=[pk1, pk2])
        address = config.get_address()
        
        assert address.startswith("3")  # P2SH addresses start with 3


class TestMultiSigWallet:
    """Test MultiSigWallet"""
    
    def test_wallet_creation(self):
        """Test wallet creation"""
        # Generate other public keys
        pk2 = generate_keypair()[1]
        pk3 = generate_keypair()[1]
        
        wallet = MultiSigWallet.create(
            m=2,
            n=3,
            my_index=0,
            other_public_keys=[pk2, pk3]
        )
        
        assert wallet.my_index == 0
        assert wallet.config.m == 2
        assert wallet.config.n == 3
    
    def test_psbt_creation(self):
        """Test PSBT creation"""
        pk2 = generate_keypair()[1]
        pk3 = generate_keypair()[1]
        
        wallet = MultiSigWallet.create(
            m=2, n=3, my_index=0,
            other_public_keys=[pk2, pk3]
        )
        
        tx_data = b"test_transaction_data"
        psbt = wallet.create_psbt(tx_data)
        
        assert psbt.transaction_data == tx_data
        assert not psbt.is_finalized


class TestPSBT:
    """Test PSBT (Partially Signed Bitcoin Transaction)"""
    
    def test_psbt_signing(self):
        """Test PSBT signature collection"""
        # Create 2-of-3 multisig
        sk1, pk1 = generate_keypair()
        sk2, pk2 = generate_keypair()
        sk3, pk3 = generate_keypair()
        
        config = MultiSigConfig(m=2, n=3, public_keys=[pk1, pk2, pk3])
        
        tx_data = b"test_transaction"
        psbt = PSBT(transaction_data=tx_data, multisig_config=config)
        
        # Add first signature
        success1 = psbt.add_signature(0, sk1, pk1)
        assert success1
        assert len(psbt.partial_signatures) == 1
        assert not psbt.is_finalized
        
        # Add second signature
        success2 = psbt.add_signature(1, sk2, pk2)
        assert success2
        assert len(psbt.partial_signatures) == 2
        assert psbt.is_finalized  # 2-of-3 complete
    
    def test_psbt_duplicate_signature(self):
        """Test duplicate signature rejection"""
        sk1, pk1 = generate_keypair()
        sk2, pk2 = generate_keypair()
        
        config = MultiSigConfig(m=2, n=2, public_keys=[pk1, pk2])
        psbt = PSBT(transaction_data=b"test", multisig_config=config)
        
        # First signature
        psbt.add_signature(0, sk1, pk1)
        
        # Duplicate should be rejected
        success = psbt.add_signature(0, sk1, pk1)
        assert not success
    
    def test_psbt_serialization(self):
        """Test PSBT serialization"""
        sk1, pk1 = generate_keypair()
        sk2, pk2 = generate_keypair()
        
        config = MultiSigConfig(m=2, n=2, public_keys=[pk1, pk2])
        psbt = PSBT(transaction_data=b"test", multisig_config=config)
        
        psbt.add_signature(0, sk1, pk1)
        
        # Serialize
        data = psbt.to_dict()
        
        # Deserialize
        psbt2 = PSBT.from_dict(data)
        
        assert psbt2.transaction_data == psbt.transaction_data
        assert len(psbt2.partial_signatures) == 1
